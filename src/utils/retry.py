"""Retry decorator with exponential backoff."""

import asyncio
import functools
import random
import time
from typing import Any, Callable, Optional, TypeVar

from .logging import get_logger


T = TypeVar("T")


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delays
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger()
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryError(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            last_exception=e,
                        ) from e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

            # Should never reach here, but satisfy type checker
            raise RetryError(
                f"Function {func.__name__} failed after {max_attempts} attempts",
                last_exception=last_exception,
            )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger()
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryError(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            last_exception=e,
                        ) from e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)

            # Should never reach here, but satisfy type checker
            raise RetryError(
                f"Function {func.__name__} failed after {max_attempts} attempts",
                last_exception=last_exception,
            )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def retry_api_call(
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Specialized retry decorator for API calls.

    Uses settings appropriate for API rate limiting and transient errors.
    """
    return retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        exceptions=(Exception,),  # Catch all for API errors
    )


__all__ = ["retry", "retry_api_call", "RetryError"]
