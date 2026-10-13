"""Vocabulary unification pipeline node."""

import logging
import re
from collections import Counter

from app.schemas.pipeline import PipelineState

logger = logging.getLogger(__name__)


async def vocab_unify_node(state: PipelineState) -> PipelineState:
    """Apply safe lexical replacements to unify vocabulary."""
    try:
        content = state.get_current_content()

        # Apply vocabulary unification
        unified_content, changes = _unify_vocabulary(content)

        # Update state if changes were made
        if changes:
            state.working_content = unified_content
            state.vocab_unified = True
            state.vocab_changes = changes
            logger.info(f"Applied {len(changes)} vocabulary unifications")

        return state

    except Exception as e:
        logger.error(f"Vocabulary unification failed: {e}")
        state.add_error(f"Vocabulary unification failed: {e}")
        return state


def _unify_vocabulary(content: str) -> tuple[str, list[str]]:
    """Apply safe vocabulary unifications."""
    changes = []
    unified_content = content

    # Define safe vocabulary unifications
    # These are conservative replacements that shouldn't change meaning
    unifications = {
        # Common contractions expansion
        "can't": "cannot",
        "won't": "will not",
        "don't": "do not",
        "doesn't": "does not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
        "shouldn't": "should not",
        "wouldn't": "would not",
        "couldn't": "could not",

        # Spelling standardizations (US English)
        "colour": "color",
        "flavour": "flavor",
        "behaviour": "behavior",
        "centre": "center",
        "metre": "meter",
        "theatre": "theater",
        "realise": "realize",
        "organise": "organize",
        "analyse": "analyze",

        # Technical term standardizations
        "e-mail": "email",
        "web site": "website",
        "web-site": "website",
        "log in": "login",
        "log-in": "login",
        "set up": "setup",
        "set-up": "setup",

        # Common redundancies
        "in order to": "to",
        "due to the fact that": "because",
        "at this point in time": "now",
        "for the purpose of": "to",
        "with regard to": "regarding",
        "as a matter of fact": "actually",

        # Formal vs informal consistency
        "it's": "it is",
        "you're": "you are",
        "we're": "we are",
        "they're": "they are",
        "there's": "there is",
    }

    # Apply word-level replacements
    for old_term, new_term in unifications.items():
        # Use word boundaries to avoid partial matches
        pattern = r'\\b' + re.escape(old_term) + r'\\b'

        new_content = re.sub(pattern, new_term, unified_content, flags=re.IGNORECASE)

        if new_content != unified_content:
            count = len(re.findall(pattern, unified_content, flags=re.IGNORECASE))
            changes.append(f"Replaced '{old_term}' with '{new_term}' ({count} times)")
            unified_content = new_content

    # Apply phrase-level improvements
    phrase_improvements = [
        # Reduce redundant phrases
        (r'\\bvery unique\\b', 'unique'),
        (r'\\bmore better\\b', 'better'),
        (r'\\bfree gift\\b', 'gift'),
        (r'\\bfuture plans\\b', 'plans'),
        (r'\\bpast history\\b', 'history'),
        (r'\\bunexpected surprise\\b', 'surprise'),

        # Simplify complex constructions
        (r'\\bin the event that\\b', 'if'),
        (r'\\bprior to\\b', 'before'),
        (r'\\bsubsequent to\\b', 'after'),
        (r'\\bduring the course of\\b', 'during'),
        (r'\\bin the vicinity of\\b', 'near'),

        # Fix common verbose expressions
        (r'\\ba large number of\\b', 'many'),
        (r'\\ba small number of\\b', 'few'),
        (r'\\bthe majority of\\b', 'most'),
        (r'\\bin spite of the fact that\\b', 'although'),
    ]

    for pattern, replacement in phrase_improvements:
        new_content = re.sub(pattern, replacement, unified_content, flags=re.IGNORECASE)

        if new_content != unified_content:
            changes.append(f"Simplified phrase: '{pattern}' → '{replacement}'")
            unified_content = new_content

    return unified_content, changes


def _analyze_vocabulary_complexity(content: str) -> dict[str, float]:
    """Analyze vocabulary complexity metrics."""
    words = re.findall(r'\\b\\w+\\b', content.lower())

    if not words:
        return {"complexity": 0.0, "diversity": 0.0, "avg_length": 0.0}

    # Calculate metrics
    word_count = len(words)
    unique_words = len(set(words))
    diversity = unique_words / word_count if word_count > 0 else 0.0

    avg_length = sum(len(word) for word in words) / word_count

    # Simple complexity based on word length and frequency
    word_frequencies = Counter(words)
    complexity = sum(len(word) * freq for word, freq in word_frequencies.items()) / word_count

    return {
        "complexity": complexity,
        "diversity": diversity,
        "avg_length": avg_length,
        "unique_words": unique_words,
        "total_words": word_count
    }
