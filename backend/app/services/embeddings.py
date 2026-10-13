"""Embeddings service for semantic analysis."""

import logging

import numpy as np
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self):
        self.client: OpenAI | None = None
        self.model = "text-embedding-3-small"  # Efficient embedding model

    def _ensure_client(self):
        """Lazy initialization of OpenAI client."""
        if self.client is None:
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.client = OpenAI(api_key=settings.openai_api_key)

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        try:
            self._ensure_client()

            # Clean and truncate text for embedding
            cleaned_text = text.strip()
            if len(cleaned_text) > 8000:  # Reasonable limit for embeddings
                cleaned_text = cleaned_text[:8000]

            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_text
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch."""
        try:
            self._ensure_client()

            # Clean texts and filter out empty ones
            cleaned_texts = []
            for text in texts:
                cleaned = text.strip()
                if not cleaned:  # Skip empty texts
                    cleaned = "empty text placeholder"  # Use placeholder for empty strings
                elif len(cleaned) > 8000:
                    cleaned = cleaned[:8000]
                cleaned_texts.append(cleaned)

            # Batch embed (OpenAI supports up to ~2048 texts per batch)
            batch_size = min(len(cleaned_texts), 100)  # Conservative batch size
            embeddings = []

            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i + batch_size]

                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            vec_a = np.array(a)
            vec_b = np.array(b)

            dot_product = np.dot(vec_a, vec_b)
            norm_a = np.linalg.norm(vec_a)
            norm_b = np.linalg.norm(vec_b)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            return float(dot_product / (norm_a * norm_b))

        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

    def calculate_semantic_entropy(self, embeddings: list[list[float]]) -> dict:
        """Calculate semantic entropy metrics from embeddings."""
        try:
            if len(embeddings) < 2:
                return {
                    "entropy": 0.0,
                    "spread": 0.0,
                    "clusters": 1,
                    "avg_similarity": 1.0
                }

            # Calculate pairwise similarities
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = self.cosine_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)

            avg_similarity = np.mean(similarities)
            similarity_std = np.std(similarities)

            # Simple entropy calculation based on similarity distribution
            # Higher spread = higher entropy
            entropy = float(similarity_std)

            # Spread is the range of similarities
            spread = float(np.max(similarities) - np.min(similarities))

            # Simple clustering: count distinct similarity ranges
            # This is a simplified approach - could use proper clustering later
            similarity_bins = np.histogram(similarities, bins=3)[0]
            clusters = int(np.count_nonzero(similarity_bins))

            return {
                "entropy": entropy,
                "spread": spread,
                "clusters": max(1, clusters),
                "avg_similarity": float(avg_similarity)
            }

        except Exception as e:
            logger.error(f"Failed to calculate semantic entropy: {e}")
            return {
                "entropy": 0.0,
                "spread": 0.0,
                "clusters": 1,
                "avg_similarity": 0.0
            }


# Global service instance
_embeddings_service: EmbeddingsService | None = None


def get_embeddings_service() -> EmbeddingsService:
    """Get or create the global embeddings service instance."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
