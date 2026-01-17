"""
速率限制器单元测试。

测试各种限流策略的正确性和性能。
"""

import time
from threading import Thread

import pytest

from lark_service.core.rate_limiter import (
    FixedWindowRateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
    create_rate_limiter,
)


class TestFixedWindowRateLimiter:
    """固定窗口速率限制器测试"""

    def test_allows_requests_within_limit(self):
        """测试在限制内允许请求"""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        limiter = FixedWindowRateLimiter(config)

        # 发送10个请求，都应该被允许
        for _ in range(10):
            result = limiter.check_rate_limit("user1")
            assert result.allowed is True

    def test_blocks_requests_over_limit(self):
        """测试超过限制时阻止请求"""
        config = RateLimitConfig(max_requests=5, window_seconds=60)
        limiter = FixedWindowRateLimiter(config)

        # 发送5个请求
        for _ in range(5):
            limiter.check_rate_limit("user1")

        # 第6个请求应该被阻止
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    def test_resets_after_window(self):
        """测试窗口过期后重置"""
        config = RateLimitConfig(max_requests=2, window_seconds=1)
        limiter = FixedWindowRateLimiter(config)

        # 使用完配额
        limiter.check_rate_limit("user1")
        limiter.check_rate_limit("user1")

        # 第3个请求被阻止
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

        # 等待窗口过期
        time.sleep(1.1)

        # 现在应该允许新请求
        result = limiter.check_rate_limit("user1")
        assert result.allowed is True

    def test_isolates_different_keys(self):
        """测试不同key的隔离性"""
        config = RateLimitConfig(max_requests=3, window_seconds=60)
        limiter = FixedWindowRateLimiter(config)

        # user1使用完配额
        for _ in range(3):
            limiter.check_rate_limit("user1")

        # user2应该还有配额
        result = limiter.check_rate_limit("user2")
        assert result.allowed is True


class TestSlidingWindowRateLimiter:
    """滑动窗口速率限制器测试"""

    def test_allows_requests_within_limit(self):
        """测试在限制内允许请求"""
        config = RateLimitConfig(max_requests=10, window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)

        for i in range(10):
            result = limiter.check_rate_limit("user1")
            assert result.allowed is True

    def test_blocks_requests_over_limit(self):
        """测试超过限制时阻止请求"""
        config = RateLimitConfig(max_requests=5, window_seconds=2)
        limiter = SlidingWindowRateLimiter(config)

        # 发送5个请求
        for _ in range(5):
            result = limiter.check_rate_limit("user1")
            assert result.allowed is True

        # 第6个请求应该被阻止
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

    def test_sliding_window_behavior(self):
        """测试滑动窗口行为"""
        config = RateLimitConfig(max_requests=3, window_seconds=2)
        limiter = SlidingWindowRateLimiter(config)

        # T=0: 发送3个请求
        for _ in range(3):
            limiter.check_rate_limit("user1")

        # T=0: 第4个请求被阻止
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

        # T=1.5: 等待1.5秒（窗口部分过期）
        time.sleep(1.5)

        # T=1.5: 仍然被阻止（窗口内还有3个请求）
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

        # T=2.1: 等待到窗口完全过期
        time.sleep(0.6)

        # T=2.1: 现在应该允许
        result = limiter.check_rate_limit("user1")
        assert result.allowed is True


class TestTokenBucketRateLimiter:
    """令牌桶速率限制器测试"""

    def test_allows_burst_requests(self):
        """测试允许突发请求"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=10,
            burst_size=20,
        )
        limiter = TokenBucketRateLimiter(config)

        # 应该允许burst_size个突发请求
        for i in range(20):
            result = limiter.check_rate_limit("user1")
            assert result.allowed is True, f"Request {i} should be allowed"

        # 第21个请求应该被阻止
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

    def test_refills_tokens_over_time(self):
        """测试令牌随时间补充"""
        config = RateLimitConfig(
            max_requests=2,  # 每秒2个令牌
            window_seconds=1,
            burst_size=2,
        )
        limiter = TokenBucketRateLimiter(config)

        # 消耗所有令牌
        limiter.check_rate_limit("user1")
        limiter.check_rate_limit("user1")

        # 现在应该没有令牌
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

        # 等待0.5秒（应该补充1个令牌）
        time.sleep(0.6)

        # 现在应该有令牌了
        result = limiter.check_rate_limit("user1")
        assert result.allowed is True

    def test_smooth_rate_limiting(self):
        """测试平滑限流"""
        config = RateLimitConfig(
            max_requests=10,  # 每秒10个
            window_seconds=1,
            burst_size=5,
        )
        limiter = TokenBucketRateLimiter(config)

        # 快速消耗突发容量
        for _ in range(5):
            result = limiter.check_rate_limit("user1")
            assert result.allowed is True

        # 现在应该按稳定速率限流
        result = limiter.check_rate_limit("user1")
        assert result.allowed is False

        # 等待足够时间补充令牌
        time.sleep(0.15)  # 应该补充1.5个令牌
        result = limiter.check_rate_limit("user1")
        assert result.allowed is True


class TestRateLimiterFactory:
    """速率限制器工厂测试"""

    def test_creates_fixed_window_limiter(self):
        """测试创建固定窗口限制器"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            strategy=RateLimitStrategy.FIXED_WINDOW,
        )
        limiter = create_rate_limiter(config)
        assert isinstance(limiter, FixedWindowRateLimiter)

    def test_creates_sliding_window_limiter(self):
        """测试创建滑动窗口限制器"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
        )
        limiter = create_rate_limiter(config)
        assert isinstance(limiter, SlidingWindowRateLimiter)

    def test_creates_token_bucket_limiter(self):
        """测试创建令牌桶限制器"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
        )
        limiter = create_rate_limiter(config)
        assert isinstance(limiter, TokenBucketRateLimiter)

    def test_raises_on_invalid_strategy(self):
        """测试无效策略时抛出异常"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            strategy="invalid_strategy",  # type: ignore[arg-type]
        )
        with pytest.raises(ValueError):
            create_rate_limiter(config)


class TestConcurrency:
    """并发测试"""

    def test_thread_safety(self):
        """测试线程安全性"""
        config = RateLimitConfig(max_requests=100, window_seconds=10)
        limiter = SlidingWindowRateLimiter(config)

        allowed_count = []
        blocked_count = []

        def make_requests():
            """在线程中发送请求"""
            for _ in range(50):
                result = limiter.check_rate_limit("user1")
                if result.allowed:
                    allowed_count.append(1)
                else:
                    blocked_count.append(1)

        # 创建多个线程同时发送请求
        threads = [Thread(target=make_requests) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 应该只有100个请求被允许
        assert len(allowed_count) == 100
        assert len(blocked_count) == 100  # 4 threads * 50 requests - 100 allowed


class TestPerformance:
    """性能测试"""

    def test_high_throughput_check(self):
        """测试高吞吐量检查"""
        config = RateLimitConfig(max_requests=10000, window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)

        start = time.time()
        for _ in range(1000):
            limiter.check_rate_limit(f"user_{_ % 100}")
        elapsed = time.time() - start

        # 1000次检查应该在1秒内完成
        assert elapsed < 1.0
        print(f"\n1000次限流检查耗时: {elapsed:.4f}s ({1000/elapsed:.2f} ops/s)")
