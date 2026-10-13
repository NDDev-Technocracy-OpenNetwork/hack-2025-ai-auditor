"""Clarification question generation pipeline node."""

import logging
from typing import Any

from app.schemas.pipeline import PipelineState
from app.schemas.prompts import ClarifyQuestion
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


async def build_questions_node(state: PipelineState) -> PipelineState:
    """Generate clarification questions based on analysis results."""
    try:
        content = state.get_current_content()
        questions = []

        # Generate questions based on different analysis issues

        # 1. Questions about contradictions
        if state.contradictions:
            contradiction_questions = await _generate_contradiction_questions(state.contradictions)
            questions.extend(contradiction_questions)

        # 2. Questions about ambiguity (high semantic entropy)
        if state.entropy_score and state.entropy_score > 0.5:
            ambiguity_questions = await _generate_ambiguity_questions(content, state.entropy_score)
            questions.extend(ambiguity_questions)

        # 3. Questions about missing details (low judge score)
        if state.llm_judge_score and state.llm_judge_score < 7.0:
            detail_questions = await _generate_detail_questions(content, state.llm_judge_score, state.llm_judge_reasoning or "")
            questions.extend(detail_questions)

        # 4. General clarification questions
        general_questions = await _generate_general_questions(content)
        questions.extend(general_questions)

        # Limit to most important questions
        questions = questions[:5]  # Max 5 questions

        # Update state
        state.clarify_questions = questions

        logger.info(f"Generated {len(questions)} clarification questions")

        return state

    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        state.add_error(f"Question generation failed: {e}")
        return state


async def _generate_contradiction_questions(contradictions: list[dict[str, Any]]) -> list[ClarifyQuestion]:
    """Generate questions to resolve contradictions."""
    questions = []

    llm = get_llm_service()

    for i, contradiction in enumerate(contradictions[:2]):  # Limit to 2 contradictions
        try:
            sentence1 = contradiction.get("sentence_1", "")
            sentence2 = contradiction.get("sentence_2", "")

            if not sentence1 or not sentence2:
                continue

            prompt = f"""These statements seem contradictory:

Statement 1: "{sentence1}"
Statement 2: "{sentence2}"

Generate a clarifying question to resolve this contradiction. The question should help determine the user's actual intent.

Provide just the question (one sentence):"""

            response = await llm.ask("cheap", prompt, max_tokens=100)
            question_text = response.strip().rstrip('?') + '?'

            questions.append(ClarifyQuestion(
                id=f"contradiction_{i}",
                question=question_text,
                category="contradiction",
                priority="high",
                context={
                    "contradiction_type": contradiction.get("type", "unknown"),
                    "sentence_1": sentence1[:100],
                    "sentence_2": sentence2[:100]
                }
            ))

        except Exception as e:
            logger.error(f"Failed to generate contradiction question {i}: {e}")

    return questions


async def _generate_ambiguity_questions(content: str, entropy: float) -> list[ClarifyQuestion]:
    """Generate questions about ambiguous parts."""
    questions = []

    try:
        llm = get_llm_service()

        prompt = f"""This prompt has high semantic ambiguity (entropy: {entropy:.2f}):

"{content}"

Generate 2 specific questions that would help clarify the most ambiguous aspects. Focus on the parts that could be interpreted in multiple ways.

Format:
1. [First question]
2. [Second question]"""

        response = await llm.ask("cheap", prompt, max_tokens=200)

        # Parse questions
        parsed_questions = _parse_numbered_questions(response)

        for i, question_text in enumerate(parsed_questions[:2]):
            questions.append(ClarifyQuestion(
                id=f"ambiguity_{i}",
                question=question_text,
                category="ambiguity",
                priority="medium",
                context={
                    "entropy_score": entropy,
                    "reason": "High semantic ambiguity detected"
                }
            ))

    except Exception as e:
        logger.error(f"Failed to generate ambiguity questions: {e}")

    return questions


async def _generate_detail_questions(content: str, judge_score: float, reasoning: str) -> list[ClarifyQuestion]:
    """Generate questions about missing details."""
    questions = []

    try:
        llm = get_llm_service()

        prompt = f"""This prompt scored {judge_score:.1f}/10. Judge feedback: {reasoning}

Prompt: "{content}"

Generate 1-2 questions that would help the user provide missing details or clarify unclear aspects. Focus on what would most improve the prompt quality.

Format:
1. [Question about missing details]
2. [Question about unclear aspects]"""

        response = await llm.ask("cheap", prompt, max_tokens=150)

        parsed_questions = _parse_numbered_questions(response)

        for i, question_text in enumerate(parsed_questions[:2]):
            questions.append(ClarifyQuestion(
                id=f"details_{i}",
                question=question_text,
                category="details",
                priority="medium" if judge_score > 5.0 else "high",
                context={
                    "judge_score": judge_score,
                    "judge_reasoning": reasoning[:100]
                }
            ))

    except Exception as e:
        logger.error(f"Failed to generate detail questions: {e}")

    return questions


async def _generate_general_questions(content: str) -> list[ClarifyQuestion]:
    """Generate general clarification questions."""
    questions = []

    try:
        llm = get_llm_service()

        prompt = f"""Analyze this prompt and generate 1-2 clarifying questions that would help improve it:

"{content}"

Focus on:
- Target audience or use case
- Expected output format
- Constraints or requirements
- Context or background needed

Generate practical questions that would lead to actionable improvements:"""

        response = await llm.ask("cheap", prompt, max_tokens=200)

        # Try to extract questions from response
        import re

        # Look for question patterns
        question_patterns = [
            r'\\?[^\\?]*\\?',  # Text ending with ?
            r'^[-*•]\\s*(.+\\?)$',  # Bullet points with questions
            r'^\\d+\\.\\s*(.+\\?)$',  # Numbered questions
        ]

        found_questions = []
        for pattern in question_patterns:
            matches = re.findall(pattern, response, re.MULTILINE)
            found_questions.extend(matches)

        # If no structured questions found, try to split by sentences
        if not found_questions:
            sentences = [s.strip() for s in response.split('.') if '?' in s]
            found_questions = [s + ('?' if not s.endswith('?') else '') for s in sentences]

        # Create question objects
        for i, question_text in enumerate(found_questions[:2]):
            question_text = question_text.strip()
            if len(question_text) > 10 and '?' in question_text:
                questions.append(ClarifyQuestion(
                    id=f"general_{i}",
                    question=question_text,
                    category="general",
                    priority="low",
                    context={"source": "general_analysis"}
                ))

    except Exception as e:
        logger.error(f"Failed to generate general questions: {e}")

    return questions


def _parse_numbered_questions(text: str) -> list[str]:
    """Parse numbered questions from text."""
    import re

    questions = []

    # Try numbered format first
    pattern = r'^\\s*\\d+\\.\\s*(.+)$'
    matches = re.findall(pattern, text, re.MULTILINE)

    if matches:
        for match in matches:
            question = match.strip()
            if not question.endswith('?'):
                question += '?'
            questions.append(question)
    else:
        # Try bullet points
        pattern = r'^\\s*[-*•]\\s*(.+)$'
        matches = re.findall(pattern, text, re.MULTILINE)

        for match in matches:
            question = match.strip()
            if '?' in question or any(word in question.lower() for word in ['what', 'how', 'when', 'where', 'why', 'which', 'who']):
                if not question.endswith('?'):
                    question += '?'
                questions.append(question)

    return questions
