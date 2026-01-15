"""Unit tests for retry strategy.

Tests exponential backoff, max retries, and rate limit handling.
"""

import time

import pytest

from lark_service.core.exceptions import APIError, RateLimitError
from lark_service.core.retry import RetryStrategy, retry_on_error


class TestRetryStrategy:
    """Test RetryStrategy functionality."""

    def test_strategy_initialization(self) -> None:
        """Test retry strategy initialization."""
        strategy = RetryStrategy(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            rate_limit_delay=60.0,
        )
        assert strategy.max_retries == 5
        assert strategy.base_delay == 2.0
        assert strategy.max_delay == 120.0
        assert strategy.rate_limit_delay == 60.0

    def test_calculate_delay_exponential_backoff(self) -> None:
        """Test exponential backoff calculation."""
        strategy = RetryStrategy(base_delay=1.0, max_delay=60.0)

        # Test exponential growth: 1s, 2s, 4s, 8s, ...
        assert strategy.calculate_delay(0) == 1.0
        assert strategy.calculate_delay(1) == 2.0
        assert strategy.calculate_delay(2) == 4.0
        assert strategy.calculate_delay(3) == 8.0
        assert strategy.calculate_delay(4) == 16.0

    def test_calculate_delay_max_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        strategy = RetryStrategy(base_delay=1.0, max_delay=10.0)

        # After enough attempts, delay should be capped
        assert strategy.calculate_delay(10) == 10.0  # Would be 1024 without cap
        assert strategy.calculate_delay(20) == 10.0

    def test_execute_success_first_try(self) -> None:
        """Test successful execution on first try."""
        strategy = RetryStrategy(max_retries=3)
        call_count = [0]

        def successful_func() -> str:
            call_count[0] += 1
            return "success"

        result = strategy.execute(successful_func)
        assert result == "success"
        assert call_count[0] == 1

    def test_execute_success_after_retries(self) -> None:
        """Test successful execution after retries."""
        strategy = RetryStrategy(max_retries=3, base_delay=0.1)
        call_count = [0]

        def eventually_successful() -> str:
            call_count[0] += 1
            if call_count[0] < 3:
                raise APIError("Temporary error", status_code=500)
            return "success"

        start_time = time.time()
        result = strategy.execute(eventually_successful)
        elapsed = time.time() - start_time

        assert result == "success"
        assert call_count[0] == 3
        # Should have delays: 0.1s + 0.2s = 0.3s minimum
        assert elapsed >= 0.3

    def test_execute_max_retries_exceeded(self) -> None:
        """Test that exception is raised after max retries."""
        strategy = RetryStrategy(max_retries=2, base_delay=0.05)
        call_count = [0]

        def always_fails() -> str:
            call_count[0] += 1
            raise APIError("Persistent error", status_code=500)

        with pytest.raises(APIError, match="Persistent error"):
            strategy.execute(always_fails)

        # Should try: initial + 2 retries = 3 times
        assert call_count[0] == 3

    def test_execute_non_retryable_error(self) -> None:
        """Test that non-retryable errors fail immediately."""
        strategy = RetryStrategy(max_retries=3)
        call_count = [0]

        def non_retryable_error() -> str:
            call_count[0] += 1
            raise APIError("Not found", status_code=404)

        with pytest.raises(APIError, match="Not found"):
            strategy.execute(non_retryable_error)

        # Should only try once (no retries for 404)
        assert call_count[0] == 1

    def test_execute_rate_limit_handling(self) -> None:
        """Test rate limit error handling."""
        strategy = RetryStrategy(max_retries=2, rate_limit_delay=0.2)
        call_count = [0]

        def rate_limited_then_success() -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RateLimitError("Rate limited", retry_after=0.2)
            return "success"

        start_time = time.time()
        result = strategy.execute(rate_limited_then_success)
        elapsed = time.time() - start_time

        assert result == "success"
        assert call_count[0] == 2
        # Should wait at least retry_after time
        assert elapsed >= 0.2

    def test_execute_rate_limit_with_custom_retry_after(self) -> None:
        """Test rate limit with custom retry_after."""
        strategy = RetryStrategy(max_retries=2, rate_limit_delay=1.0)
        call_count = [0]

        def rate_limited_custom() -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RateLimitError("Rate limited", retry_after=0.15)
            return "success"

        start_time = time.time()
        result = strategy.execute(rate_limited_custom)
        elapsed = time.time() - start_time

        assert result == "success"
        # Should use custom retry_after (0.15s) not default (1.0s)
        assert 0.15 <= elapsed < 0.5

    def test_execute_multiple_rate_limits(self) -> None:
        """Test handling multiple rate limit errors."""
        strategy = RetryStrategy(max_retries=3, rate_limit_delay=0.1)
        call_count = [0]

        def multiple_rate_limits() -> str:
            call_count[0] += 1
            if call_count[0] <= 2:
                raise RateLimitError("Rate limited", retry_after=0.1)
            return "success"

        result = strategy.execute(multiple_rate_limits)
        assert result == "success"
        assert call_count[0] == 3

    def test_execute_rate_limit_max_retries(self) -> None:
        """Test rate limit exceeding max retries."""
        strategy = RetryStrategy(max_retries=1, rate_limit_delay=0.05)
        call_count = [0]

        def always_rate_limited() -> str:
            call_count[0] += 1
            raise RateLimitError("Always rate limited", retry_after=0.05)

        with pytest.raises(RateLimitError, match="Always rate limited"):
            strategy.execute(always_rate_limited)

        # Should try: initial + 1 retry = 2 times
        assert call_count[0] == 2

    def test_execute_with_args_and_kwargs(self) -> None:
        """Test execute with function arguments."""
        strategy = RetryStrategy(max_retries=1)

        def func_with_args(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        result = strategy.execute(func_with_args, 1, 2, c=3)
        assert result == 6


class TestRetryDecorator:
    """Test retry_on_error decorator."""

    def test_decorator_basic(self) -> None:
        """Test basic decorator usage."""
        call_count = [0]

        @retry_on_error(max_retries=2, base_delay=0.05)
        def decorated_func() -> str:
            call_count[0] += 1
            if call_count[0] < 2:
                raise APIError("Temporary error", status_code=500)
            return "success"

        result = decorated_func()
        assert result == "success"
        assert call_count[0] == 2

    def test_decorator_with_parameters(self) -> None:
        """Test decorator with function parameters."""
        @retry_on_error(max_retries=1, base_delay=0.05)
        def add(a: int, b: int) -> int:
            return a + b

        result = add(3, 4)
        assert result == 7

    def test_decorator_preserves_exceptions(self) -> None:
        """Test that decorator preserves exceptions."""
        @retry_on_error(max_retries=1, base_delay=0.05)
        def always_fails() -> str:
            raise APIError("Persistent error", status_code=500)

        with pytest.raises(APIError, match="Persistent error"):
            always_fails()

    def test_decorator_custom_config(self) -> None:
        """Test decorator with custom configuration."""
        call_count = [0]

        @retry_on_error(
            max_retries=5,
            base_delay=0.05,
            max_delay=10.0,
            rate_limit_delay=0.1,
        )
        def custom_config_func() -> str:
            call_count[0] += 1
            if call_count[0] < 3:
                raise APIError("Error", status_code=500)
            return "success"

        result = custom_config_func()
        assert result == "success"
        assert call_count[0] == 3
