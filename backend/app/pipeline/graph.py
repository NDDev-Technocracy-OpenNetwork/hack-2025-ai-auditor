"""LangGraph analysis pipeline assembly."""

import logging
from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph

from app.pipeline.contradiction_nodes import find_contradictions_node
from app.pipeline.entropy_nodes import semantic_entropy_node
from app.pipeline.format_nodes import ensure_format_node, lint_markup_node
from app.pipeline.judge_nodes import judge_score_node
from app.pipeline.language_nodes import (
    detect_language_node,
    maybe_translate_to_english_node,
)
from app.pipeline.patch_nodes import propose_patches_node
from app.pipeline.question_nodes import build_questions_node
from app.pipeline.vocab_nodes import vocab_unify_node
from app.schemas.pipeline import PipelineState

logger = logging.getLogger(__name__)


def create_analysis_graph() -> StateGraph:
    """Create the LangGraph analysis pipeline."""

    # Create the graph
    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("detect_language", detect_language_node)
    workflow.add_node("maybe_translate", maybe_translate_to_english_node)
    workflow.add_node("ensure_format", ensure_format_node)
    workflow.add_node("lint_markup", lint_markup_node)
    workflow.add_node("vocab_unify", vocab_unify_node)
    workflow.add_node("find_contradictions", find_contradictions_node)
    workflow.add_node("analyze_entropy", semantic_entropy_node)
    workflow.add_node("judge_score", judge_score_node)
    workflow.add_node("propose_patches", propose_patches_node)
    workflow.add_node("build_questions", build_questions_node)
    workflow.add_node("finalize", finalize_analysis_node)

    # Define the flow
    workflow.set_entry_point("detect_language")

    # Linear flow with some parallelization opportunities
    workflow.add_edge("detect_language", "maybe_translate")
    workflow.add_edge("maybe_translate", "ensure_format")
    workflow.add_edge("ensure_format", "lint_markup")
    workflow.add_edge("lint_markup", "vocab_unify")

    # Analysis branches (could be parallelized in future)
    workflow.add_edge("vocab_unify", "find_contradictions")
    workflow.add_edge("find_contradictions", "analyze_entropy")
    workflow.add_edge("analyze_entropy", "judge_score")

    # Final synthesis
    workflow.add_edge("judge_score", "propose_patches")
    workflow.add_edge("propose_patches", "build_questions")
    workflow.add_edge("build_questions", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


async def finalize_analysis_node(state: PipelineState) -> PipelineState:
    """Finalize the analysis and prepare the final state."""
    try:
        # Mark processing as completed
        state.processing_completed = datetime.utcnow()

        # Calculate processing time
        if state.processing_started:
            processing_time = (state.processing_completed - state.processing_started).total_seconds()
            logger.info(f"Analysis pipeline completed in {processing_time:.2f} seconds")

        # Log summary
        logger.info(
            f"Analysis complete - "
            f"Language: {state.detected_language}, "
            f"Translated: {state.translated}, "
            f"Format: {state.format_type} ({'valid' if state.format_valid else 'invalid'}), "
            f"Judge Score: {state.llm_judge_score:.1f}/10, "
            f"Patches: {len(state.patches)}, "
            f"Questions: {len(state.clarify_questions)}, "
            f"Errors: {len(state.errors)}"
        )

        return state

    except Exception as e:
        logger.error(f"Finalization failed: {e}")
        state.add_error(f"Finalization failed: {e}")
        return state


class AnalysisPipeline:
    """High-level analysis pipeline interface."""

    def __init__(self):
        self.graph = create_analysis_graph()

    async def analyze(self, prompt_content: str, format_type: str = "text") -> PipelineState:
        """Run the complete analysis pipeline on a prompt."""
        try:
            # Create initial state
            initial_state = PipelineState(
                prompt_content=prompt_content,
                format_type=format_type,
                processing_started=datetime.utcnow()
            )

            logger.info(f"Starting analysis pipeline for {len(prompt_content)} character prompt")

            # Run the pipeline
            result = await self.graph.ainvoke(initial_state)

            # Convert result back to PipelineState if needed
            if not isinstance(result, PipelineState):
                # LangGraph returns a dict-like object, convert it back
                final_state = PipelineState(**result)
            else:
                final_state = result

            return final_state

        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}")

            # Return state with error
            error_state = PipelineState(
                prompt_content=prompt_content,
                format_type=format_type,
                processing_started=datetime.utcnow(),
                processing_completed=datetime.utcnow()
            )
            error_state.add_error(f"Pipeline execution failed: {e}")

            return error_state

    async def analyze_with_context(
        self,
        prompt_content: str,
        format_type: str = "text",
        context: dict[str, Any] = None  # noqa: ARG002 - reserved public compatibility parameter
    ) -> PipelineState:
        """Run analysis with additional context."""

        # For now, context is not used but could be added to state
        # in future versions for things like:
        # - User preferences
        # - Domain-specific analysis
        # - Previous analysis results

        return await self.analyze(prompt_content, format_type)


# Global pipeline instance
_analysis_pipeline: AnalysisPipeline = None


def get_analysis_pipeline() -> AnalysisPipeline:
    """Get or create the global analysis pipeline instance."""
    global _analysis_pipeline
    if _analysis_pipeline is None:
        _analysis_pipeline = AnalysisPipeline()
    return _analysis_pipeline
