"""Language detection and translation pipeline nodes."""

import logging
import re

from app.pipeline.error_handling import with_error_handling
from app.schemas.pipeline import (
    PipelineState,
)
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


@with_error_handling("detect_language", max_retries=2, continue_on_error=True)
async def detect_language_node(state: PipelineState) -> PipelineState:
    """Detect the language of the prompt content."""
    try:
        llm = get_llm_service()

        # Extract first 500 chars for language detection
        sample_text = state.prompt_content[:500]

        prompt = f"""Detect the language of this text. Respond with just the language code (en, ru, es, fr, de, etc.) and confidence (0.0-1.0).

Text: "{sample_text}"

Response format: language_code:confidence (e.g., "en:0.95" or "ru:0.87")"""

        response = await llm.ask("cheap", prompt, max_tokens=10)

        # Parse response
        try:
            parts = response.strip().split(':')
            language = parts[0].strip().lower()
            confidence = float(parts[1].strip())
        except (IndexError, ValueError):
            # Fallback: simple heuristic detection
            language, confidence = _simple_language_detection(sample_text)

        # Update state
        state.detected_language = language

        logger.info(f"Detected language: {language} (confidence: {confidence:.2f})")

        return state

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        state.add_error(f"Language detection failed: {e}")
        # Default to English
        state.detected_language = "en"
        return state


@with_error_handling("maybe_translate", max_retries=1, continue_on_error=True)
async def maybe_translate_to_english_node(state: PipelineState) -> PipelineState:
    """Translate content to English if needed."""
    try:
        # Skip if already English or no language detected
        if not state.detected_language or state.detected_language == "en":
            logger.info("No translation needed (already English or unknown language)")
            return state

        llm = get_llm_service()

        prompt = f"""Translate the following text from {state.detected_language} to English.
Preserve the original structure, formatting, and technical terms as much as possible.
Return only the translated text without any additional commentary.

Text to translate:
{state.prompt_content}"""

        translated = await llm.ask("standard", prompt, max_tokens=len(state.prompt_content) + 500)

        # Update state
        state.translated = True
        state.translated_content = translated.strip()

        logger.info(f"Translated text from {state.detected_language} to English")

        return state

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        state.add_error(f"Translation failed: {e}")
        # Continue with original content
        return state


def _simple_language_detection(text: str) -> tuple[str, float]:
    """Simple heuristic language detection as fallback."""
    text_lower = text.lower()

    # Count characteristic patterns
    cyrillic_chars = len(re.findall(r'[а-яё]', text_lower))
    latin_chars = len(re.findall(r'[a-z]', text_lower))

    total_letters = cyrillic_chars + latin_chars

    if total_letters == 0:
        return "en", 0.5  # Default to English

    if cyrillic_chars > latin_chars:
        confidence = min(0.95, cyrillic_chars / total_letters + 0.1)
        return "ru", confidence
    else:
        # Check for common English words
        english_indicators = ['the', 'and', 'you', 'that', 'this', 'with', 'for', 'are', 'from']
        english_count = sum(1 for word in english_indicators if word in text_lower.split())

        if english_count >= 2:
            return "en", min(0.95, 0.7 + english_count * 0.05)
        else:
            return "en", 0.6  # Default confidence
