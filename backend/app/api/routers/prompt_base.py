"""Prompt-base API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.prompts import (
    PromptCreate,
    PromptRead,
    PromptRelationCreate,
    PromptRelationRead,
    PromptUpdate,
)
from app.services.prompt_base import get_prompt_base_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prompt-base", tags=["prompt-base"])


@router.post("/add", response_model=PromptRead)
async def add_prompt(prompt_data: PromptCreate):
    """
    Add a new prompt to the prompt-base.

    Creates a new prompt with the provided content and metadata.
    Validates the prompt structure and stores it in the database.
    """
    try:
        service = get_prompt_base_service()
        prompt = await service.create_prompt(prompt_data)

        logger.info(f"Added prompt to prompt-base: {prompt.id}")
        return prompt

    except ValueError as e:
        logger.warning(f"Invalid prompt data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add prompt: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to add prompt to prompt-base"
        )


@router.post("/check")
async def check_prompt_conflicts(prompt_data: PromptCreate):
    """
    Check a prompt for conflicts with existing prompts in the prompt-base.

    Analyzes the prompt against existing prompts to detect:
    - Content conflicts or contradictions
    - Dependency relationships
    - Override relationships

    Returns conflict analysis and suggested relations.
    """
    try:
        service = get_prompt_base_service()

        # TODO: Implement conflict detection logic
        # For now, return basic analysis
        conflicts = []
        suggestions = []

        # Simple keyword-based conflict detection (placeholder)
        existing_prompts = await service.search_prompts(
            query=prompt_data.name[:50],  # Search by name prefix
            limit=10,
        )

        if existing_prompts:
            conflicts.append(
                {
                    "type": "potential_duplicate",
                    "severity": "medium",
                    "message": f"Found {len(existing_prompts)} similar prompts",
                    "related_prompts": [p.id for p in existing_prompts[:3]],
                }
            )

            suggestions.append(
                {
                    "action": "review_existing",
                    "message": "Consider reviewing existing similar prompts before adding",
                    "prompt_ids": [p.id for p in existing_prompts[:3]],
                }
            )

        return {
            "conflicts": conflicts,
            "suggestions": suggestions,
            "analysis": {
                "total_existing_prompts": len(existing_prompts),
                "conflict_score": 0.3 if existing_prompts else 0.0,
                "recommendation": "safe_to_add"
                if len(existing_prompts) < 3
                else "review_recommended",
            },
        }

    except Exception as e:
        logger.error(f"Failed to check prompt conflicts: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to analyze prompt conflicts"
        )


@router.get("/prompts", response_model=list[PromptRead])
async def list_prompts(
    skip: int = Query(0, ge=0, description="Number of prompts to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of prompts to return"
    ),
    tags: str | None = Query(
        None, description="Comma-separated list of tags to filter by"
    ),
    language: str | None = Query(None, description="Language code to filter by"),
    format_type: str | None = Query(None, description="Format type to filter by"),
):
    """
    List prompts in the prompt-base with optional filtering.

    Supports pagination and filtering by tags, language, and format type.
    """
    try:
        service = get_prompt_base_service()

        # Parse tags
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        prompts = await service.list_prompts(
            skip=skip,
            limit=limit,
            tags=tag_list,
            language=language,
            format_type=format_type,
        )

        return prompts

    except Exception as e:
        logger.error(f"Failed to list prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve prompts")


@router.get("/prompts/{prompt_id}", response_model=PromptRead)
async def get_prompt(prompt_id: str):
    """Get a specific prompt by ID."""
    try:
        service = get_prompt_base_service()
        prompt = await service.get_prompt(prompt_id)

        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")

        return prompt

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve prompt")


@router.put("/prompts/{prompt_id}", response_model=PromptRead)
async def update_prompt(prompt_id: str, update_data: PromptUpdate):
    """Update an existing prompt."""
    try:
        service = get_prompt_base_service()
        prompt = await service.update_prompt(prompt_id, update_data)

        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")

        logger.info(f"Updated prompt: {prompt_id}")
        return prompt

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update prompt")


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt from the prompt-base."""
    try:
        service = get_prompt_base_service()
        deleted = await service.delete_prompt(prompt_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")

        logger.info(f"Deleted prompt: {prompt_id}")
        return {"message": f"Prompt {prompt_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete prompt")


@router.get("/search", response_model=list[PromptRead])
async def search_prompts(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
):
    """Search prompts by content, name, or description."""
    try:
        service = get_prompt_base_service()
        prompts = await service.search_prompts(query=q, limit=limit)

        return prompts

    except Exception as e:
        logger.error(f"Failed to search prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to search prompts")


@router.post("/relations", response_model=PromptRelationRead)
async def create_relation(relation_data: PromptRelationCreate):
    """Create a relationship between two prompts."""
    try:
        service = get_prompt_base_service()
        relation = await service.create_relation(relation_data)

        logger.info(f"Created relation: {relation.id}")
        return relation

    except ValueError as e:
        logger.warning(f"Invalid relation data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create relation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create prompt relation")


@router.get("/prompts/{prompt_id}/relations", response_model=list[PromptRelationRead])
async def get_prompt_relations(prompt_id: str):
    """Get all relationships for a specific prompt."""
    try:
        service = get_prompt_base_service()
        relations = await service.get_prompt_relations(prompt_id)

        return relations

    except Exception as e:
        logger.error(f"Failed to get relations for prompt {prompt_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve prompt relations"
        )


@router.delete("/relations/{relation_id}")
async def delete_relation(relation_id: str):
    """Delete a prompt relationship."""
    try:
        service = get_prompt_base_service()
        deleted = await service.delete_relation(relation_id)

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Relation {relation_id} not found"
            )

        logger.info(f"Deleted relation: {relation_id}")
        return {"message": f"Relation {relation_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete relation {relation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete relation")
