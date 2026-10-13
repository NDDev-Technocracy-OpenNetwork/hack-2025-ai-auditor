"""Semantic entropy analysis pipeline node."""

import asyncio
import logging

from app.core.config import settings
from app.schemas.pipeline import PipelineState
from app.services.embeddings import get_embeddings_service
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)


async def semantic_entropy_node(state: PipelineState) -> PipelineState:
    """Analyze semantic entropy through sampling and embedding analysis."""
    try:
        content = state.get_current_content()

        # Generate semantic samples
        samples = await _generate_semantic_samples(content, settings.entropy_n)
        state.semantic_samples = samples

        # Generate embeddings for samples
        embeddings_service = get_embeddings_service()

        # Run sync embedding generation in executor
        import asyncio
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, embeddings_service.embed_texts, samples)
        state.semantic_embeddings = embeddings

        # Calculate entropy metrics
        entropy_metrics = embeddings_service.calculate_semantic_entropy(embeddings)

        state.entropy_score = entropy_metrics["entropy"]
        state.entropy_spread = entropy_metrics["spread"]
        state.entropy_clusters = entropy_metrics["clusters"]

        logger.info(f"Calculated semantic entropy: {entropy_metrics['entropy']:.3f}, "
                   f"spread: {entropy_metrics['spread']:.3f}, "
                   f"clusters: {entropy_metrics['clusters']}")

        return state

    except Exception as e:
        logger.error(f"Semantic entropy analysis failed: {e}")
        state.add_error(f"Semantic entropy analysis failed: {e}")
        # Set default values
        state.entropy_score = 0.0
        state.entropy_spread = 0.0
        state.entropy_clusters = 1
        return state


async def _generate_semantic_samples(content: str, n_samples: int) -> list[str]:
    """Generate n different interpretations/responses to the prompt."""
    try:
        llm = get_llm_service()

        # Create sampling prompt
        sampling_prompt = f"""Given this prompt/instruction, generate {n_samples} different but valid interpretations or responses. Each should capture the essence but vary in approach, focus, or specific details.

Original prompt:
{content}

Generate {n_samples} variations that are semantically related but show different possible interpretations. Each variation should be 50-200 words.

Format as numbered list:
1. [First variation]
2. [Second variation]
...
"""

        # Generate samples
        response = await llm.ask("cheap", sampling_prompt, max_tokens=n_samples * 100 + 200)

        # Parse the response into individual samples
        samples = _parse_numbered_list(response)

        # If parsing failed, generate samples one by one
        if len(samples) < n_samples // 2:
            samples = await _generate_samples_individually(content, n_samples)

        # Ensure we have enough samples
        while len(samples) < n_samples:
            samples.append(content)  # Use original as fallback

        return samples[:n_samples]

    except Exception as e:
        logger.error(f"Sample generation failed: {e}")
        # Fallback: return original content multiple times
        return [content] * n_samples


async def _generate_samples_individually(content: str, n_samples: int) -> list[str]:
    """Generate samples one by one if batch generation fails."""
    samples = []

    prompts = [
        f"Rephrase this instruction with different wording but same meaning:\\n{content}",
        f"Interpret this prompt from a different angle:\\n{content}",
        f"Provide an alternative formulation of this request:\\n{content}",
        f"Express this same concept using different terminology:\\n{content}",
        f"Rewrite this prompt with more specific details:\\n{content}",
        f"Generalize this instruction to be broader:\\n{content}",
        f"Simplify this prompt while keeping the core intent:\\n{content}",
        f"Make this instruction more formal:\\n{content}",
    ]

    llm = get_llm_service()

    # Generate samples concurrently
    tasks = []
    for i in range(min(n_samples, len(prompts))):
        task = llm.ask("cheap", prompts[i], max_tokens=200)
        tasks.append(task)

    try:
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for response in responses:
            if isinstance(response, str):
                samples.append(response.strip())
            else:
                logger.warning(f"Sample generation failed: {response}")

    except Exception as e:
        logger.error(f"Individual sample generation failed: {e}")

    # Fill remaining with variations of the original
    while len(samples) < n_samples:
        samples.append(content)

    return samples


def _parse_numbered_list(text: str) -> list[str]:
    """Parse a numbered list from LLM response."""
    import re

    samples = []

    # Try to match numbered items
    pattern = r'^\\s*\\d+\\.\\s*(.+?)(?=^\\s*\\d+\\.|$)'
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)

    for match in matches:
        sample = match.strip()
        if len(sample) > 20:  # Filter out very short samples
            samples.append(sample)

    # If numbered parsing failed, try other formats
    if not samples:
        # Try bullet points
        pattern = r'^\\s*[-*]\\s*(.+?)(?=^\\s*[-*]|$)'
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)

        for match in matches:
            sample = match.strip()
            if len(sample) > 20:
                samples.append(sample)

    # If still no samples, split by paragraphs
    if not samples:
        paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
        samples = [p for p in paragraphs if len(p) > 20]

    return samples
