"""Format validation and markup fixing pipeline nodes."""

import logging
import re
import xml.etree.ElementTree as ET

from app.schemas.pipeline import PipelineState

logger = logging.getLogger(__name__)


async def ensure_format_node(state: PipelineState) -> PipelineState:
    """Validate and detect the format of the content."""
    try:
        content = state.get_current_content()

        # Detect format based on content
        detected_format = _detect_format(content)

        # Validate format
        is_valid, errors = _validate_format(content, detected_format)

        # Update state
        state.format_type = detected_format
        state.format_valid = is_valid

        if errors:
            state.add_error(f"Format validation errors: {'; '.join(errors)}")

        logger.info(f"Detected format: {detected_format}, valid: {is_valid}")

        return state

    except Exception as e:
        logger.error(f"Format detection failed: {e}")
        state.add_error(f"Format detection failed: {e}")
        state.format_type = "text"
        state.format_valid = False
        return state


async def lint_markup_node(state: PipelineState) -> PipelineState:
    """Apply safe markup fixes to the content."""
    try:
        content = state.get_current_content()

        if state.format_type == "xml":
            fixed_content, fixes = _fix_xml_markup(content)
        elif state.format_type == "markdown":
            fixed_content, fixes = _fix_markdown_markup(content)
        else:
            # No fixes for plain text
            fixed_content = content
            fixes = []

        # Update state if fixes were applied
        if fixes:
            state.working_content = fixed_content
            state.markup_fixes = fixes
            state.format_valid = True
            logger.info(f"Applied {len(fixes)} markup fixes")

        return state

    except Exception as e:
        logger.error(f"Markup linting failed: {e}")
        state.add_error(f"Markup linting failed: {e}")
        return state


def _detect_format(content: str) -> str:
    """Detect the format of the content."""
    content_stripped = content.strip()

    # Check for XML
    if content_stripped.startswith('<') and '>' in content_stripped:
        return "xml"

    # Check for Markdown indicators
    markdown_indicators = [
        r'^#{1,6}\s+.+$',  # Headers
        r'^\*{1,3}.+\*{1,3}$',  # Bold/italic
        r'^```',  # Code blocks
        r'^\[.+\]\(.+\)$',  # Links
        r'^[-*+]\s+',  # Lists
    ]

    lines = content_stripped.split('\n')
    markdown_score = 0

    for line in lines[:10]:  # Check first 10 lines
        for pattern in markdown_indicators:
            if re.search(pattern, line.strip(), re.MULTILINE):
                markdown_score += 1
                break

    if markdown_score >= 2:
        return "markdown"

    return "text"


def _validate_format(content: str, format_type: str) -> tuple[bool, list[str]]:
    """Validate content against its format."""
    errors = []

    if format_type == "xml":
        try:
            # Try to parse as XML
            ET.fromstring(f"<root>{content}</root>")
        except ET.ParseError as e:
            errors.append(f"XML parsing error: {str(e)}")

    elif format_type == "markdown":
        # Basic markdown validation
        lines = content.split('\n')

        # Check for unclosed code blocks
        code_block_count = content.count('```')
        if code_block_count % 2 != 0:
            errors.append("Unclosed code block found")

        # Check for malformed headers
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#') and not re.match(r'^#{1,6}\s+.+', line.strip()):
                errors.append(f"Malformed header at line {i}: {line.strip()[:50]}")

    return len(errors) == 0, errors


def _fix_xml_markup(content: str) -> tuple[str, list[str]]:
    """Apply safe XML fixes."""
    fixes = []
    fixed_content = content

    # Fix common XML issues
    replacements = [
        # Fix unclosed tags (basic cases)
        (r'<([a-zA-Z][a-zA-Z0-9]*)\s*>([^<>]*?)(?!</\1>)', r'<\1>\2</\1>'),
        # Fix malformed attributes
        (r'(\w+)=([^"\s>]+)(?=\s|>)', r'\1="\2"'),
        # Fix & characters
        (r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;'),
    ]

    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, fixed_content)
        if new_content != fixed_content:
            fixes.append(f"Applied XML fix: {pattern[:30]}...")
            fixed_content = new_content

    return fixed_content, fixes


def _fix_markdown_markup(content: str) -> tuple[str, list[str]]:
    """Apply safe Markdown fixes."""
    fixes = []
    lines = content.split('\n')
    fixed_lines = []

    in_code_block = False

    for line in lines:
        original_line = line

        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        # Skip fixes inside code blocks
        if not in_code_block:
            # Fix headers
            if line.strip().startswith('#'):
                # Ensure space after #
                line = re.sub(r'^(#{1,6})([^\s])', r'\1 \2', line)
                if line != original_line:
                    fixes.append("Fixed header spacing")

            # Fix list items
            if re.match(r'^[-*+]([^\s])', line.strip()):
                line = re.sub(r'^([-*+])([^\s])', r'\1 \2', line)
                if line != original_line:
                    fixes.append("Fixed list item spacing")

        fixed_lines.append(line)

    # Fix unclosed code blocks
    code_block_count = content.count('```')
    if code_block_count % 2 != 0:
        fixed_lines.append('```')
        fixes.append("Closed unclosed code block")

    return '\n'.join(fixed_lines), fixes
