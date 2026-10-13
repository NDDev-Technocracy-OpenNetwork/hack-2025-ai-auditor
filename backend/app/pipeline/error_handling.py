"""Error handling and retry logic for pipeline nodes."""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from app.schemas.pipeline import PipelineState

logger = logging.getLogger(__name__)

T = TypeVar('T')


def with_error_handling(
    node_name: str,
    max_retries: int = 2,
    retry_delay: float = 1.0,
    continue_on_error: bool = True
):
    """Decorator to add error handling and retry logic to pipeline nodes."""

    def decorator(func: Callable[[PipelineState], T]) -> Callable[[PipelineState], T]:
        @wraps(func)
        async def wrapper(state: PipelineState) -> PipelineState:
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(f"Running {node_name} (attempt {attempt + 1})")

                    # Run the node function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(state)
                    else:
                        result = func(state)

                    logger.debug(f"{node_name} completed successfully")
                    return result

                except Exception as e:
                    error_msg = f"{node_name} failed on attempt {attempt + 1}: {str(e)}"
                    logger.error(error_msg)

                    # Add error to state
                    state.add_error(error_msg)

                    # If this is the last attempt or we shouldn't continue on error
                    if attempt == max_retries:
                        if continue_on_error:
                            logger.warning(f"{node_name} failed all retries, continuing pipeline")
                            return state
                        else:
                            logger.error(f"{node_name} failed all retries, stopping pipeline")
                            raise

                    # Wait before retry
                    if retry_delay > 0:
                        await asyncio.sleep(retry_delay)

            return state

        return wrapper
    return decorator


class PipelineErrorHandler:
    """Centralized error handling for the analysis pipeline."""

    def __init__(self):
        self.error_counts = {}
        self.total_errors = 0

    def handle_node_error(
        self,
        node_name: str,
        error: Exception,
        state: PipelineState,
        attempt: int = 1
    ) -> bool:
        """
        Handle an error from a pipeline node.

        Returns:
            bool: True if the pipeline should continue, False if it should stop
        """
        error_msg = f"{node_name} error (attempt {attempt}): {str(error)}"

        # Log the error
        logger.error(error_msg)

        # Update error tracking
        if node_name not in self.error_counts:
            self.error_counts[node_name] = 0
        self.error_counts[node_name] += 1
        self.total_errors += 1

        # Add to state
        state.add_error(error_msg)

        # Determine if we should continue
        should_continue = self._should_continue_after_error(node_name, error)

        if should_continue:
            logger.warning(f"Continuing pipeline despite {node_name} error")
        else:
            logger.error(f"Stopping pipeline due to {node_name} error")

        return should_continue

    def _should_continue_after_error(self, node_name: str, error: Exception) -> bool:
        """Determine if the pipeline should continue after an error."""

        # Critical errors that should stop the pipeline
        critical_error_types = [
            ValueError,  # Invalid input
            TypeError,   # Type errors
        ]

        if type(error) in critical_error_types:
            return False

        # If too many errors for this node, stop
        if self.error_counts.get(node_name, 0) >= 3:
            return False

        # If too many total errors, stop
        return self.total_errors < 5

    def get_error_summary(self) -> dict:
        """Get a summary of all errors encountered."""
        return {
            "total_errors": self.total_errors,
            "errors_by_node": self.error_counts.copy(),
            "most_problematic_node": max(self.error_counts.items(), key=lambda x: x[1])[0] if self.error_counts else None
        }


# Global error handler instance
_pipeline_error_handler: PipelineErrorHandler | None = None


def get_pipeline_error_handler() -> PipelineErrorHandler:
    """Get or create the global pipeline error handler."""
    global _pipeline_error_handler
    if _pipeline_error_handler is None:
        _pipeline_error_handler = PipelineErrorHandler()
    return _pipeline_error_handler


def reset_error_handler():
    """Reset the global error handler (useful for testing)."""
    global _pipeline_error_handler
    _pipeline_error_handler = None


class CircuitBreaker:
    """Circuit breaker pattern for protecting against cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed, open, half-open

    async def call(self, func: Callable, *args, **kwargs):
        """Call a function with circuit breaker protection."""
        import time

        current_time = time.time()

        # Check if circuit should move from open to half-open
        if (self.state == "open" and
            current_time - self.last_failure_time > self.recovery_timeout):
            self.state = "half-open"
            logger.info("Circuit breaker moving to half-open state")

        # If circuit is open, fail fast
        if self.state == "open":
            raise Exception("Circuit breaker is open - failing fast")

        try:
            # Try to call the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - reset failure count if we were in half-open
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker reset to closed state")

            return result

        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = current_time

            # Check if we should open the circuit
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")

            raise e
