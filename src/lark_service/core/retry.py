"""Retry strategy with exponential backoff.

Provides retry logic for API calls with rate limit handling.
"""

import time
from collections.abc import Callable
from typing import Any, TypeVar

from lark_service.core.exceptions import APIError, RateLimitError
from lark_service.utils.logger import get_logger

logger = get_logger()

T = TypeVar("T")


class RetryStrategy:
    """Retry strategy with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
        max_delay: Maximum delay between retries (seconds)
        rate_limit_delay: Delay when rate limited (seconds)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        rate_limit_delay: float = 30.0,
    ) -> None:
        """Initialize RetryStrategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            rate_limit_delay: Delay when rate limited (seconds)

        Example:
            >>> strategy = RetryStrategy(max_retries=3, base_delay=1.0)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.rate_limit_delay = rate_limit_delay

        logger.debug(
            "RetryStrategy initialized",
            extra={
                "max_retries": max_retries,
                "base_delay": base_delay,
                "max_delay": max_delay,
                "rate_limit_delay": rate_limit_delay,
            },
        )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt using exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds

        Example:
            >>> strategy = RetryStrategy(base_delay=1.0)
            >>> strategy.calculate_delay(0)  # 1s
            1.0
            >>> strategy.calculate_delay(1)  # 2s
            2.0
            >>> strategy.calculate_delay(2)  # 4s
            4.0
        """
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)

    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries fail

        Example:
            >>> strategy = RetryStrategy(max_retries=3)
            >>> def api_call():
            ...     # Make API call
            ...     return "success"
            >>> result = strategy.execute(api_call)
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        "Retry succeeded",
                        extra={"attempt": attempt, "function": func.__name__},
                    )
                return result

            except RateLimitError as e:
                last_exception = e
                retry_after = e.retry_after or self.rate_limit_delay

                logger.warning(
                    "Rate limited, waiting before retry",
                    extra={
                        "attempt": attempt,
                        "retry_after": retry_after,
                        "function": func.__name__,
                        "error": str(e),
                    },
                )

                if attempt < self.max_retries:
                    time.sleep(retry_after)
                    continue
                else:
                    logger.error(
                        "Max retries exceeded after rate limit",
                        extra={
                            "attempts": attempt + 1,
                            "function": func.__name__,
                        },
                    )
                    raise

            except APIError as e:
                last_exception = e

                # Don't retry on certain errors
                if e.status_code and e.status_code in [400, 401, 403, 404]:
                    logger.error(
                        "Non-retryable API error",
                        extra={
                            "status_code": e.status_code,
                            "function": func.__name__,
                            "error": str(e),
                        },
                    )
                    raise

                delay = self.calculate_delay(attempt)

                logger.warning(
                    "API error, retrying",
                    extra={
                        "attempt": attempt,
                        "delay": delay,
                        "function": func.__name__,
                        "error": str(e),
                    },
                )

                if attempt < self.max_retries:
                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        "Max retries exceeded",
                        extra={
                            "attempts": attempt + 1,
                            "function": func.__name__,
                        },
                    )
                    raise

            except Exception as e:
                last_exception = e
                delay = self.calculate_delay(attempt)

                logger.warning(
                    "Unexpected error, retrying",
                    extra={
                        "attempt": attempt,
                        "delay": delay,
                        "function": func.__name__,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if attempt < self.max_retries:
                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        "Max retries exceeded",
                        extra={
                            "attempts": attempt + 1,
                            "function": func.__name__,
                        },
                    )
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")


def retry_on_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    rate_limit_delay: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
        max_delay: Maximum delay between retries (seconds)
        rate_limit_delay: Delay when rate limited (seconds)

    Returns:
        Decorator function

    Example:
        >>> @retry_on_error(max_retries=3, base_delay=1.0)
        ... def api_call():
        ...     # Make API call
        ...     return "success"
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            strategy = RetryStrategy(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                rate_limit_delay=rate_limit_delay,
            )
            return strategy.execute(func, *args, **kwargs)
        return wrapper
    return decorator
