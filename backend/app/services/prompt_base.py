"""Prompt-base service for managing prompts and relationships."""

import logging
import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.database import SessionLocal
from app.models.prompts import (
    Prompt,
    PromptCreate,
    PromptRead,
    PromptRelation,
    PromptRelationCreate,
    PromptRelationRead,
    PromptUpdate,
)

logger = logging.getLogger(__name__)


class PromptBaseService:
    """Service for managing prompts in the prompt-base."""

    def __init__(self):
        pass

    async def create_prompt(self, prompt_data: PromptCreate) -> PromptRead:
        """Create a new prompt in the prompt-base."""
        try:
            with SessionLocal() as session:
                # Create new prompt
                prompt = Prompt(id=str(uuid.uuid4()), **prompt_data.model_dump())

                session.add(prompt)
                session.commit()
                session.refresh(prompt)

                logger.info(f"Created new prompt: {prompt.id}")
                return PromptRead.model_validate(prompt)

        except IntegrityError as e:
            logger.error(f"Failed to create prompt: {e}")
            raise ValueError(f"Failed to create prompt: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating prompt: {e}")
            raise

    async def get_prompt(self, prompt_id: str) -> PromptRead | None:
        """Get a prompt by ID."""
        try:
            with SessionLocal() as session:
                statement = select(Prompt).where(Prompt.id == prompt_id)
                prompt = session.exec(statement).first()

                if prompt:
                    return PromptRead.model_validate(prompt)
                return None

        except Exception as e:
            logger.error(f"Error retrieving prompt {prompt_id}: {e}")
            raise

    async def update_prompt(
        self, prompt_id: str, update_data: PromptUpdate
    ) -> PromptRead | None:
        """Update an existing prompt."""
        try:
            with SessionLocal() as session:
                statement = select(Prompt).where(Prompt.id == prompt_id)
                prompt = session.exec(statement).first()

                if not prompt:
                    return None

                # Update fields
                update_dict = update_data.model_dump(exclude_unset=True)
                for field, value in update_dict.items():
                    setattr(prompt, field, value)

                prompt.updated_at = datetime.utcnow()
                session.add(prompt)
                session.commit()
                session.refresh(prompt)

                logger.info(f"Updated prompt: {prompt_id}")
                return PromptRead.model_validate(prompt)

        except Exception as e:
            logger.error(f"Error updating prompt {prompt_id}: {e}")
            raise

    async def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt."""
        try:
            with SessionLocal() as session:
                statement = select(Prompt).where(Prompt.id == prompt_id)
                prompt = session.exec(statement).first()

                if not prompt:
                    return False

                session.delete(prompt)
                session.commit()

                logger.info(f"Deleted prompt: {prompt_id}")
                return True

        except Exception as e:
            logger.error(f"Error deleting prompt {prompt_id}: {e}")
            raise

    async def list_prompts(
        self,
        skip: int = 0,
        limit: int = 100,
        tags: list[str] | None = None,
        language: str | None = None,
        format_type: str | None = None,
    ) -> list[PromptRead]:
        """List prompts with optional filtering."""
        try:
            with SessionLocal() as session:
                statement = select(Prompt)

                # Apply filters
                if language:
                    statement = statement.where(Prompt.language == language)
                if format_type:
                    statement = statement.where(Prompt.format_type == format_type)

                # Add pagination
                statement = statement.offset(skip).limit(limit)

                # Order by creation date (newest first)
                statement = statement.order_by(Prompt.created_at.desc())

                prompts = session.exec(statement).all()

                result = []
                for prompt in prompts:
                    # Filter by tags if specified
                    if tags:
                        prompt_tags = prompt.tags or []
                        if not any(tag in prompt_tags for tag in tags):
                            continue

                    result.append(PromptRead.model_validate(prompt))

                return result

        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            raise

    async def search_prompts(self, query: str, limit: int = 50) -> list[PromptRead]:
        """Search prompts by content or name."""
        try:
            with SessionLocal() as session:
                # Simple text search - can be enhanced with full-text search later
                statement = (
                    select(Prompt)
                    .where(
                        (Prompt.name.ilike(f"%{query}%"))
                        | (Prompt.content.ilike(f"%{query}%"))
                        | (Prompt.description.ilike(f"%{query}%"))
                    )
                    .limit(limit)
                    .order_by(Prompt.created_at.desc())
                )

                prompts = session.exec(statement).all()
                return [PromptRead.model_validate(prompt) for prompt in prompts]

        except Exception as e:
            logger.error(f"Error searching prompts: {e}")
            raise

    async def create_relation(
        self, relation_data: PromptRelationCreate
    ) -> PromptRelationRead:
        """Create a relationship between two prompts."""
        try:
            with SessionLocal() as session:
                # Verify both prompts exist
                source = session.exec(
                    select(Prompt).where(Prompt.id == relation_data.source_id)
                ).first()
                target = session.exec(
                    select(Prompt).where(Prompt.id == relation_data.target_id)
                ).first()

                if not source:
                    raise ValueError(
                        f"Source prompt {relation_data.source_id} not found"
                    )
                if not target:
                    raise ValueError(
                        f"Target prompt {relation_data.target_id} not found"
                    )

                # Create relation
                relation = PromptRelation(
                    id=str(uuid.uuid4()), **relation_data.model_dump()
                )

                session.add(relation)
                session.commit()
                session.refresh(relation)

                logger.info(
                    f"Created relation: {relation.id} ({relation.relation_type})"
                )
                return PromptRelationRead.model_validate(relation)

        except IntegrityError as e:
            logger.error(f"Failed to create relation: {e}")
            raise ValueError(f"Failed to create relation: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating relation: {e}")
            raise

    async def get_prompt_relations(self, prompt_id: str) -> list[PromptRelationRead]:
        """Get all relations for a prompt (both incoming and outgoing)."""
        try:
            with SessionLocal() as session:
                # Get outgoing relations
                outgoing = session.exec(
                    select(PromptRelation).where(PromptRelation.source_id == prompt_id)
                ).all()

                # Get incoming relations
                incoming = session.exec(
                    select(PromptRelation).where(PromptRelation.target_id == prompt_id)
                ).all()

                all_relations = outgoing + incoming
                return [PromptRelationRead.model_validate(rel) for rel in all_relations]

        except Exception as e:
            logger.error(f"Error getting relations for prompt {prompt_id}: {e}")
            raise

    async def delete_relation(self, relation_id: str) -> bool:
        """Delete a prompt relation."""
        try:
            with SessionLocal() as session:
                statement = select(PromptRelation).where(
                    PromptRelation.id == relation_id
                )
                relation = session.exec(statement).first()

                if not relation:
                    return False

                session.delete(relation)
                session.commit()

                logger.info(f"Deleted relation: {relation_id}")
                return True

        except Exception as e:
            logger.error(f"Error deleting relation {relation_id}: {e}")
            raise


# Global service instance
_prompt_base_service: PromptBaseService | None = None


def get_prompt_base_service() -> PromptBaseService:
    """Get or create the global prompt-base service instance."""
    global _prompt_base_service
    if _prompt_base_service is None:
        _prompt_base_service = PromptBaseService()
    return _prompt_base_service
