import logging
from typing import Literal

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

ModelTier = Literal["cheap", "standard", "premium"]


class OpenAIService:
    """OpenAI service with tier-based model selection for cost optimization."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.models = {
            "cheap": settings.openai_model_cheap,
            "standard": settings.openai_model_standard,
            "premium": settings.openai_model_premium,
        }

    async def ask(self, model_tier: ModelTier, prompt: str, **kwargs) -> str:
        """
        Send a prompt to OpenAI using specified model tier.

        Args:
            model_tier: Model tier to use (cheap/standard/premium)
            prompt: The prompt to send
            **kwargs: Additional parameters for OpenAI API

        Returns:
            Response text from the model
        """
        model = self.models[model_tier]

        # Convert max_tokens to max_completion_tokens for gpt-5 models
        if "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            result = response.choices[0].message.content

            logger.info(
                "OpenAI request completed",
                extra={
                    "model": model,
                    "tier": model_tier,
                    "prompt_length": len(prompt),
                    "response_length": len(result) if result else 0,
                }
            )

            return result or ""

        except Exception as e:
            logger.error(
                f"OpenAI request failed: {str(e)}",
                extra={
                    "model": model,
                    "tier": model_tier,
                    "error": str(e),
                    "prompt_length": len(prompt),
                }
            )
            raise

    async def sample_for_entropy(self, prompt: str, n: int = None) -> list[str]:
        """
        Generate multiple responses for semantic entropy analysis.
        Uses cheap model for cost efficiency.

        Args:
            prompt: The prompt to sample responses for
            n: Number of samples (defaults to settings.entropy_n)

        Returns:
            List of response strings
        """
        n = n or settings.entropy_n

        try:
            # Use cheap model for cost efficiency
            # Note: max_completion_tokens conversion handled in ask() method
            response = self.client.chat.completions.create(
                model=self.models["cheap"],
                messages=[{"role": "user", "content": prompt}],
                n=n  # Generate multiple responses in one request
            )

            results = [choice.message.content or "" for choice in response.choices]

            logger.info(
                "Entropy sampling completed",
                extra={
                    "model": self.models["cheap"],
                    "samples": n,
                    "prompt_length": len(prompt),
                    "avg_response_length": sum(len(r) for r in results) / len(results),
                }
            )

            return results

        except Exception as e:
            logger.error(
                f"Entropy sampling failed: {str(e)}",
                extra={
                    "error": str(e),
                    "samples": n,
                    "prompt_length": len(prompt),
                }
            )
            raise

    async def judge_prompt(self, prompt: str, rubric: str = None) -> str:
        """
        Evaluate prompt quality using premium model for accuracy.

        Args:
            prompt: The prompt to evaluate
            rubric: Evaluation rubric (optional)

        Returns:
            JSON string with evaluation scores and rationale
        """
        default_rubric = """
        Evaluate this prompt on the following criteria (1-10 scale):
        1. Clarity: How clear and unambiguous is the prompt?
        2. Specificity: How specific are the requirements?
        3. Completeness: Are all necessary details provided?
        4. Consistency: Are there any contradictions?
        5. Feasibility: Is the request achievable?

        Return JSON format:
        {
            "clarity": <score>,
            "specificity": <score>,
            "completeness": <score>,
            "consistency": <score>,
            "feasibility": <score>,
            "overall": <average_score>,
            "rationale": "<brief explanation>"
        }
        """

        evaluation_prompt = f"""
        {rubric or default_rubric}

        Prompt to evaluate:
        {prompt}
        """

        return await self.ask("premium", evaluation_prompt)

    async def clarify_prompt(self, prompt: str) -> str:
        """
        Generate clarification questions for ambiguous prompts.
        Uses standard model for balanced cost/quality.

        Args:
            prompt: The prompt that needs clarification

        Returns:
            List of clarification questions
        """
        clarify_prompt = f"""
        Analyze this prompt and identify what information is missing or ambiguous.
        Generate 3-5 specific clarification questions that would help improve the prompt.

        Return as JSON:
        {{
            "questions": [
                "What specific format should the output be in?",
                "What is the target audience for this content?"
            ],
            "ambiguities": [
                "The term 'good quality' is subjective",
                "No specific length requirements given"
            ]
        }}

        Prompt to analyze:
        {prompt}
        """

        return await self.ask("standard", clarify_prompt)


# Global service instance - lazy initialization
llm_service = None

def get_llm_service() -> OpenAIService:
    """Get or create the global LLM service instance."""
    global llm_service
    if llm_service is None:
        llm_service = OpenAIService()
    return llm_service
