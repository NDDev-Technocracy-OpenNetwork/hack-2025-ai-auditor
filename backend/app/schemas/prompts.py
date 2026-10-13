from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PromptInput(BaseModel):
    """Input prompt for analysis."""

    content: str = Field(..., description="The prompt text to analyze")
    format_type: Literal["auto", "xml", "markdown"] = Field(
        default="auto", description="Expected format of the prompt"
    )
    language: str | None = Field(
        default=None,
        description="Language of the prompt (auto-detected if not provided)",
    )
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metadata about the prompt"
    )


class MetricScore(BaseModel):
    """Individual metric score."""

    score: float = Field(..., ge=0, le=10, description="Score from 0-10")
    rationale: str = Field(..., description="Brief explanation of the score")
    details: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metric-specific details"
    )


class SemanticEntropy(BaseModel):
    """Semantic entropy analysis results."""

    entropy: float = Field(..., description="Entropy score")
    spread: float = Field(..., description="Response variation measure")
    clusters: int = Field(..., description="Number of distinct response clusters")
    samples: list[str] = Field(..., description="Sample responses used for analysis")


class Contradiction(BaseModel):
    """Detected contradiction."""

    type: Literal["intra", "inter"] = Field(..., description="Contradiction type")
    description: str = Field(..., description="Description of the contradiction")
    severity: Literal["low", "medium", "high"] = Field(
        ..., description="Severity level"
    )
    locations: list[str] = Field(..., description="Where contradictions were found")


class Patch(BaseModel):
    """Improvement suggestion for the prompt."""

    id: str = Field(..., description="Unique patch identifier")
    type: Literal["safe", "risky"] = Field(..., description="Patch risk level")
    category: Literal["markup", "vocabulary", "structure", "clarity"] = Field(
        ..., description="Type of improvement"
    )
    description: str = Field(..., description="What this patch does")
    original: str = Field(..., description="Original text to replace")
    improved: str = Field(..., description="Improved text")
    rationale: str = Field(..., description="Why this improvement helps")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in this patch")


class ClarifyQuestion(BaseModel):
    """Clarification question for ambiguous prompts."""

    id: str = Field(..., description="Question identifier")
    question: str = Field(..., description="The clarification question")
    category: str = Field(..., description="What aspect needs clarification")
    priority: Literal["low", "medium", "high"] = Field(
        ..., description="Question priority"
    )


class ClarifyAnswer(BaseModel):
    """Answer to a clarification question."""

    question_id: str = Field(..., description="ID of the question being answered")
    answer: str = Field(..., description="The answer provided")


class MetricReport(BaseModel):
    """Comprehensive analysis report."""

    # Basic info
    prompt_id: str = Field(..., description="Unique identifier for this analysis")
    original_prompt: str = Field(..., description="The original prompt text")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Language and format
    detected_language: str = Field(..., description="Auto-detected language")
    translated: bool = Field(default=False, description="Whether prompt was translated")
    format_valid: bool = Field(..., description="Whether markup format is valid")

    # Core metrics
    judge_score: MetricScore = Field(..., description="LLM-as-judge evaluation")
    semantic_entropy: SemanticEntropy = Field(
        ..., description="Response consistency analysis"
    )
    contradictions: list[Contradiction] = Field(default_factory=list)

    # Additional metrics
    length_chars: int = Field(..., description="Character count")
    length_words: int = Field(..., description="Word count")
    complexity_score: float = Field(
        ..., ge=0, le=10, description="Vocabulary complexity"
    )

    # Improvement suggestions
    patches: list[Patch] = Field(default_factory=list)
    clarify_questions: list[ClarifyQuestion] = Field(default_factory=list)

    # Summary
    overall_score: float = Field(..., ge=0, le=10, description="Overall quality score")
    improvement_priority: Literal["low", "medium", "high"] = Field(
        ..., description="How urgently this prompt needs improvement"
    )


class PromptImproved(BaseModel):
    """Final improved prompt after applying patches."""

    original_prompt: str = Field(..., description="The original prompt")
    improved_prompt: str = Field(..., description="The improved prompt")
    applied_patches: list[str] = Field(
        ..., description="IDs of patches that were applied"
    )
    improvement_summary: str = Field(..., description="Summary of changes made")
    quality_gain: float = Field(..., description="Estimated quality improvement")


class AnalyzeRequest(BaseModel):
    """Request to analyze a prompt."""

    prompt: PromptInput
    include_entropy: bool = Field(
        default=True, description="Include semantic entropy analysis"
    )
    include_clarify: bool = Field(
        default=True, description="Include clarification questions"
    )
    include_patches: bool = Field(
        default=True, description="Include improvement patches"
    )


class AnalyzeResponse(BaseModel):
    """Response from prompt analysis."""

    report: MetricReport
    patches: list[Patch]
    questions: list[ClarifyQuestion]


class ApplyPatchesRequest(BaseModel):
    """Request to apply specific patches."""

    prompt_id: str = Field(..., description="ID of the analyzed prompt")
    patch_ids: list[str] = Field(..., description="IDs of patches to apply")
    apply_safe_all: bool = Field(default=False, description="Apply all safe patches")


class ClarifyRequest(BaseModel):
    """Request to process clarification answers."""

    prompt_id: str = Field(..., description="ID of the prompt being clarified")
    answers: list[ClarifyAnswer] = Field(
        ..., description="Answers to clarification questions"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    message: str
    version: str
    environment: str
    openai_configured: bool = Field(
        ..., description="Whether OpenAI is properly configured"
    )
