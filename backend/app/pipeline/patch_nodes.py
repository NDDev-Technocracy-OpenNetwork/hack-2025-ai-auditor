"""Patch generation pipeline node."""

import logging
from typing import Any

from app.schemas.pipeline import PipelineState
from app.schemas.prompts import Patch
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


async def propose_patches_node(state: PipelineState) -> PipelineState:
    """Generate improvement patches based on analysis results."""
    try:
        content = state.get_current_content()
        patches = []

        # Generate patches based on different analysis results

        # 1. Format fixes
        if not state.format_valid:
            format_patches = await _generate_format_patches(content, state.format_type)
            patches.extend(format_patches)

        # 2. Vocabulary improvements
        if state.vocab_changes:
            vocab_patches = _generate_vocab_patches(state.vocab_changes)
            patches.extend(vocab_patches)

        # 3. Contradiction fixes
        if state.contradictions:
            contradiction_patches = await _generate_contradiction_patches(
                content, state.contradictions
            )
            patches.extend(contradiction_patches)

        # 4. General quality improvements based on judge score
        if state.llm_judge_score and state.llm_judge_score < 8.0:
            quality_patches = await _generate_quality_patches(
                content, state.llm_judge_score, state.llm_judge_reasoning or ""
            )
            patches.extend(quality_patches)

        # 5. Semantic clarity improvements
        if state.entropy_score and state.entropy_score > 0.5:
            clarity_patches = await _generate_clarity_patches(
                content, state.entropy_score
            )
            patches.extend(clarity_patches)

        # Update state
        state.patches = patches

        safe_count = sum(1 for p in patches if p.type == "safe")
        risky_count = sum(1 for p in patches if p.type == "risky")

        logger.info(
            f"Generated {len(patches)} patches ({safe_count} safe, {risky_count} risky)"
        )

        return state

    except Exception as e:
        logger.error(f"Patch generation failed: {e}")
        state.add_error(f"Patch generation failed: {e}")
        return state


async def _generate_format_patches(content: str, format_type: str) -> list[Patch]:
    """Generate patches for format issues."""
    patches = []

    if format_type == "xml":
        # Basic XML fixes
        if "<" in content and not content.strip().startswith("<"):
            patches.append(
                Patch(
                    id="xml_root_wrap",
                    type="safe",
                    category="markup",
                    description="Wrap content in XML root element",
                    original=content[:100] + "..." if len(content) > 100 else content,
                    improved=f"<root>{content}</root>",
                    rationale="XML content should be wrapped in a root element",
                    confidence=0.9,
                )
            )

    elif format_type == "markdown":
        lines = content.split("\n")

        # Check for missing title
        if not any(line.strip().startswith("#") for line in lines[:3]):
            patches.append(
                Patch(
                    id="md_add_title",
                    type="safe",
                    category="markup",
                    description="Add markdown title",
                    original=lines[0][:50] + "..."
                    if lines and len(lines[0]) > 50
                    else (lines[0] if lines else ""),
                    improved=f"# Document Title\n\n{lines[0] if lines else ''}",
                    rationale="Markdown documents should have a clear title",
                    confidence=0.8,
                )
            )

    return patches


def _generate_vocab_patches(vocab_changes: list[str]) -> list[Patch]:
    """Convert vocabulary changes to patches."""
    patches = []

    for i, change in enumerate(vocab_changes):
        # Parse change description to extract details
        if "Replaced" in change and "with" in change:
            try:
                # Extract old and new terms
                parts = change.split("'")
                if len(parts) >= 4:
                    old_term = parts[1]
                    new_term = parts[3]

                    patches.append(
                        Patch(
                            id=f"vocab_{i}",
                            type="safe",
                            category="vocabulary",
                            description=f"Replace '{old_term}' with '{new_term}'",
                            original=old_term,
                            improved=new_term,
                            rationale="Vocabulary standardization for consistency",
                            confidence=0.9,
                        )
                    )
            except Exception:
                # If parsing fails, create a general patch
                patches.append(
                    Patch(
                        id=f"vocab_{i}",
                        type="safe",
                        category="vocabulary",
                        description=change,
                        original="[vocabulary improvement]",
                        improved="[improved vocabulary]",
                        rationale="Vocabulary improvement based on analysis",
                        confidence=0.7,
                    )
                )

    return patches


async def _generate_contradiction_patches(
    content: str, contradictions: list[dict[str, Any]]  # noqa: ARG001 - retained caller contract
) -> list[Patch]:
    """Generate patches to resolve contradictions."""
    patches = []

    llm = get_llm_service()

    for i, contradiction in enumerate(contradictions[:3]):  # Limit to 3 contradictions
        try:
            sentence1 = contradiction.get("sentence_1", "")
            sentence2 = contradiction.get("sentence_2", "")

            if not sentence1 or not sentence2:
                continue

            prompt = f"""These two statements contradict each other:

Statement 1: "{sentence1}"
Statement 2: "{sentence2}"

Provide a single, clear statement that resolves this contradiction by either:
1. Clarifying the relationship between the statements
2. Providing a unified statement that captures both intents
3. Prioritizing one over the other with clear reasoning

Respond with just the resolved statement (1-2 sentences max):"""

            resolution = await llm.ask("standard", prompt, max_tokens=150)

            patches.append(
                Patch(
                    id=f"contradiction_{i}",
                    type="risky",  # Contradiction resolution changes meaning
                    category="clarity",
                    description="Resolve contradiction between statements",
                    original=f"{sentence1} ... {sentence2}",
                    improved=resolution.strip(),
                    rationale=f"Resolves {contradiction.get('type', 'contradiction')}",
                    confidence=0.6,
                )
            )

        except Exception as e:
            logger.error(f"Failed to generate contradiction patch {i}: {e}")

    return patches


async def _generate_quality_patches(
    content: str, judge_score: float, reasoning: str
) -> list[Patch]:
    """Generate patches to improve overall quality."""
    patches = []

    try:
        llm = get_llm_service()

        prompt = f"""This prompt scored {judge_score:.1f}/10.0. Judge feedback: {reasoning}

Original prompt:
{content}

Suggest 2-3 specific improvements to increase the score. For each improvement, provide:
1. What to change (be specific about the text)
2. What to change it to
3. Why this improves the prompt

Focus on the biggest impact improvements. Be concise.

Format:
IMPROVEMENT 1:
Change: [specific text to change]
To: [replacement text]
Why: [brief reason]

IMPROVEMENT 2:
[etc.]"""

        response = await llm.ask("standard", prompt, max_tokens=400)

        # Parse improvements
        improvements = _parse_improvements(response)

        for i, improvement in enumerate(improvements):
            patches.append(
                Patch(
                    id=f"quality_{i}",
                    type="risky",  # Quality changes can alter meaning
                    category="clarity",
                    description=improvement.get("description", "Quality improvement"),
                    original=improvement.get("current", "")[:100],
                    improved=improvement.get("suggested", "")[:200],
                    rationale=improvement.get(
                        "reasoning", "Improves overall prompt quality"
                    ),
                    confidence=0.7,
                )
            )

    except Exception as e:
        logger.error(f"Failed to generate quality patches: {e}")

    return patches


async def _generate_clarity_patches(content: str, entropy: float) -> list[Patch]:
    """Generate patches to improve semantic clarity."""
    patches = []

    if entropy > 0.7:  # High entropy suggests ambiguity
        try:
            llm = get_llm_service()

            prompt = f"""This prompt has high semantic ambiguity (entropy: {entropy:.2f}). Make it more specific and clear.

Original: {content}

Rewrite to be more specific and unambiguous. Focus on:
1. Clearer instructions
2. More specific requirements
3. Reduced ambiguity

Provide the improved version:"""

            improved = await llm.ask("standard", prompt, max_tokens=len(content) + 200)

            patches.append(
                Patch(
                    id="clarity_overall",
                    type="risky",
                    category="clarity",
                    description="Improve overall clarity and reduce ambiguity",
                    original=content[:100] + "..." if len(content) > 100 else content,
                    improved=improved.strip()[:300] + "..."
                    if len(improved.strip()) > 300
                    else improved.strip(),
                    rationale=f"Reduces semantic ambiguity (entropy: {entropy:.2f})",
                    confidence=0.7,
                )
            )

        except Exception as e:
            logger.error(f"Failed to generate clarity patch: {e}")

    return patches


def _parse_improvements(text: str) -> list[dict[str, str]]:
    """Parse improvement suggestions from LLM response."""
    improvements = []

    import re

    # Try to extract improvements using pattern matching
    pattern = r"IMPROVEMENT \d+:(.*?)(?=IMPROVEMENT \d+:|$)"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        lines = [line.strip() for line in match.strip().split("\n") if line.strip()]

        improvement = {}
        current_key = None

        for line in lines:
            if line.lower().startswith("change:"):
                improvement["current"] = line[7:].strip()
                current_key = "current"
            elif line.lower().startswith("to:"):
                improvement["suggested"] = line[3:].strip()
                current_key = "suggested"
            elif line.lower().startswith("why:"):
                improvement["reasoning"] = line[4:].strip()
                current_key = "reasoning"
            elif current_key and not any(
                line.lower().startswith(prefix) for prefix in ["change:", "to:", "why:"]
            ):
                # Continue previous field
                improvement[current_key] += " " + line

        if improvement.get("current") and improvement.get("suggested"):
            improvement[
                "description"
            ] = f"Change '{improvement['current'][:30]}...' to improve quality"
            improvements.append(improvement)

    return improvements
