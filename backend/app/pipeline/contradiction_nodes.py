"""Contradiction detection pipeline node."""

import logging
import re
from typing import Any

from app.schemas.pipeline import PipelineState
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


async def find_contradictions_node(state: PipelineState) -> PipelineState:
    """Detect contradictions within the prompt content."""
    try:
        content = state.get_current_content()

        # Find intra-prompt contradictions
        contradictions = await _find_intra_prompt_contradictions(content)

        # Update state
        state.contradictions = contradictions

        if contradictions:
            logger.info(f"Found {len(contradictions)} potential contradictions")

        return state

    except Exception as e:
        logger.error(f"Contradiction detection failed: {e}")
        state.add_error(f"Contradiction detection failed: {e}")
        return state


async def _find_intra_prompt_contradictions(content: str) -> list[dict[str, Any]]:
    """Find contradictions within a single prompt."""

    # Split content into sentences for analysis
    sentences = _split_into_sentences(content)

    if len(sentences) < 2:
        return []

    contradictions = []

    # Check for obvious contradictions using patterns
    pattern_contradictions = _detect_pattern_contradictions(sentences)
    contradictions.extend(pattern_contradictions)

    # Use LLM for semantic contradiction detection on key sentence pairs
    if len(sentences) <= 10:  # Limit for performance
        semantic_contradictions = await _detect_semantic_contradictions(sentences)
        contradictions.extend(semantic_contradictions)

    return contradictions


def _split_into_sentences(content: str) -> list[str]:
    """Split content into sentences."""
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+', content)

    # Clean and filter sentences
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 10:  # Filter out very short fragments
            cleaned_sentences.append(sentence)

    return cleaned_sentences


def _detect_pattern_contradictions(sentences: list[str]) -> list[dict[str, Any]]:
    """Detect contradictions using pattern matching."""
    contradictions = []

    # Define contradiction patterns
    contradiction_patterns = [
        # Direct negations
        {
            "positive": [r"\\bmust\\b", r"\\brequired\\b", r"\\bmandatory\\b", r"\\bshould\\b"],
            "negative": [r"\\bmust not\\b", r"\\bshould not\\b", r"\\bforbidden\\b", r"\\bprohibited\\b"],
            "type": "intra"
        },
        {
            "positive": [r"\\balways\\b", r"\\bever\\b", r"\\binvariably\\b"],
            "negative": [r"\\bnever\\b", r"\\bnot ever\\b", r"\\bunder no circumstances\\b"],
            "type": "intra"
        },
        {
            "positive": [r"\\ball\\b", r"\\bevery\\b", r"\\beach\\b"],
            "negative": [r"\\bnone\\b", r"\\bno\\b(?=\\s+\\w)", r"\\bnot any\\b"],
            "type": "intra"
        },
        {
            "positive": [r"\\binclude\\b", r"\\badd\\b", r"\\bcontain\\b"],
            "negative": [r"\\bexclude\\b", r"\\bremove\\b", r"\\bomit\\b"],
            "type": "intra"
        }
    ]

    for i, sentence1 in enumerate(sentences):
        for j, sentence2 in enumerate(sentences[i+1:], i+1):

            for pattern_group in contradiction_patterns:
                positive_matches = any(
                    re.search(pattern, sentence1, re.IGNORECASE)
                    for pattern in pattern_group["positive"]
                )
                negative_matches = any(
                    re.search(pattern, sentence2, re.IGNORECASE)
                    for pattern in pattern_group["negative"]
                )

                # Check both directions
                if (positive_matches and negative_matches) or \
                   (any(re.search(p, sentence2, re.IGNORECASE) for p in pattern_group["positive"]) and
                    any(re.search(n, sentence1, re.IGNORECASE) for n in pattern_group["negative"])):

                    contradictions.append({
                        "type": pattern_group["type"],
                        "severity": "medium",
                        "sentence_1": sentence1.strip(),
                        "sentence_2": sentence2.strip(),
                        "position_1": i,
                        "position_2": j,
                        "description": f"Pattern-based {pattern_group['type'].replace('_', ' ')}"
                    })

    return contradictions


async def _detect_semantic_contradictions(sentences: list[str]) -> list[dict[str, Any]]:
    """Use LLM to detect semantic contradictions."""
    contradictions = []

    try:
        llm = get_llm_service()

        # Check pairs of sentences for contradictions
        for i in range(len(sentences)):
            for j in range(i + 1, min(i + 3, len(sentences))):  # Check next 2 sentences only
                sentence1 = sentences[i].strip()
                sentence2 = sentences[j].strip()

                if len(sentence1) < 20 or len(sentence2) < 20:
                    continue

                prompt = f"""Analyze these two statements for logical contradictions or conflicts:

Statement 1: "{sentence1}"
Statement 2: "{sentence2}"

Are these statements contradictory or conflicting? Respond with:
- "YES" if they contradict each other
- "NO" if they are consistent
- "MAYBE" if there's potential conflict but not definitive

If YES or MAYBE, provide a brief explanation (max 50 words).

Format: YES/NO/MAYBE: [explanation if needed]"""

                response = await llm.ask("cheap", prompt, max_tokens=100)

                response = response.strip().upper()

                if response.startswith("YES"):
                    explanation = response[4:].strip(" :")
                    contradictions.append({
                        "type": "intra",
                        "severity": "high",
                        "sentence_1": sentence1,
                        "sentence_2": sentence2,
                        "position_1": i,
                        "position_2": j,
                        "description": f"Semantic contradiction: {explanation}"
                    })
                elif response.startswith("MAYBE"):
                    explanation = response[6:].strip(" :")
                    contradictions.append({
                        "type": "intra",
                        "severity": "low",
                        "sentence_1": sentence1,
                        "sentence_2": sentence2,
                        "position_1": i,
                        "position_2": j,
                        "description": f"Potential conflict: {explanation}"
                    })

    except Exception as e:
        logger.error(f"Semantic contradiction detection failed: {e}")

    return contradictions


def _calculate_contradiction_score(contradictions: list[dict[str, Any]]) -> float:
    """Calculate overall contradiction score."""
    if not contradictions:
        return 0.0

    severity_weights = {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.3
    }

    total_score = sum(severity_weights.get(c.get("severity", "low"), 0.3) for c in contradictions)

    # Normalize by number of contradictions (diminishing returns)
    normalized_score = min(1.0, total_score / (1 + len(contradictions) * 0.1))

    return normalized_score
