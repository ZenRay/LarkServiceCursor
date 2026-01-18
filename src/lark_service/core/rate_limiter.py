"""
Lark Service API Rate Limiting Middleware.

提供API速率限制功能，防止滥用和确保服务稳定性。
支持多种限流策略：固定窗口、滑动窗口、令牌桶。
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any

from lark_service.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimitStrategy(str, Enum):
    """速率限制策略"""

    FIXED_WINDOW = "fixed_window"  # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    TOKEN_BUCKET = "token_bucket"  # nosec B105 - 这是算法名称,不是密码


@dataclass
class RateLimitConfig:
    """速率限制配置"""

    max_requests: int  # 最大请求数
    window_seconds: int  # 时间窗口（秒）
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_size: int | None = None  # 突发大小（仅用于令牌桶）


@dataclass
class RateLimitResult:
    """速率限制结果"""

    allowed: bool  # 是否允许请求
    remaining: int  # 剩余配额
    reset_at: float  # 重置时间戳
    retry_after: int | None = None  # 建议重试时间（秒）


class RateLimiter:
    """速率限制器基类"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.lock = Lock()

    def check_rate_limit(self, key: str) -> RateLimitResult:
        """检查速率限制"""
        raise NotImplementedError


class FixedWindowRateLimiter(RateLimiter):
    """固定窗口速率限制器"""

    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self.windows: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "start_time": time.time()}
        )

    def check_rate_limit(self, key: str) -> RateLimitResult:
        """检查速率限制"""
        with self.lock:
            current_time = time.time()
            window = self.windows[key]

            # 检查是否需要重置窗口
            if current_time - window["start_time"] >= self.config.window_seconds:
                window["count"] = 0
                window["start_time"] = current_time

            # 检查是否超过限制
            if window["count"] >= self.config.max_requests:
                reset_at = window["start_time"] + self.config.window_seconds
                retry_after = int(reset_at - current_time) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )

            # 允许请求
            window["count"] += 1
            return RateLimitResult(
                allowed=True,
                remaining=self.config.max_requests - window["count"],
                reset_at=window["start_time"] + self.config.window_seconds,
            )


class SlidingWindowRateLimiter(RateLimiter):
    """滑动窗口速率限制器"""

    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def check_rate_limit(self, key: str) -> RateLimitResult:
        """检查速率限制"""
        with self.lock:
            current_time = time.time()
            window_start = current_time - self.config.window_seconds
            request_queue = self.requests[key]

            # 移除过期的请求记录
            while request_queue and request_queue[0] < window_start:
                request_queue.popleft()

            # 检查是否超过限制
            if len(request_queue) >= self.config.max_requests:
                oldest_request = request_queue[0]
                reset_at = oldest_request + self.config.window_seconds
                retry_after = int(reset_at - current_time) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )

            # 允许请求
            request_queue.append(current_time)
            return RateLimitResult(
                allowed=True,
                remaining=self.config.max_requests - len(request_queue),
                reset_at=current_time + self.config.window_seconds,
            )


class TokenBucketRateLimiter(RateLimiter):
    """令牌桶速率限制器"""

    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self.burst_size = config.burst_size or config.max_requests
        self.refill_rate = config.max_requests / config.window_seconds
        self.buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"tokens": self.burst_size, "last_refill": time.time()}
        )

    def check_rate_limit(self, key: str) -> RateLimitResult:
        """检查速率限制"""
        with self.lock:
            current_time = time.time()
            bucket = self.buckets[key]

            # 补充令牌
            elapsed = current_time - bucket["last_refill"]
            new_tokens = elapsed * self.refill_rate
            bucket["tokens"] = min(self.burst_size, bucket["tokens"] + new_tokens)
            bucket["last_refill"] = current_time

            # 检查是否有足够的令牌
            if bucket["tokens"] < 1:
                wait_time = (1 - bucket["tokens"]) / self.refill_rate
                retry_after = int(wait_time) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=current_time + wait_time,
                    retry_after=retry_after,
                )

            # 消费一个令牌
            bucket["tokens"] -= 1
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket["tokens"]),
                reset_at=current_time + (self.burst_size - bucket["tokens"]) / self.refill_rate,
            )


def create_rate_limiter(config: RateLimitConfig) -> RateLimiter:
    """创建速率限制器"""
    if config.strategy == RateLimitStrategy.FIXED_WINDOW:
        return FixedWindowRateLimiter(config)
    elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
        return SlidingWindowRateLimiter(config)
    elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
        return TokenBucketRateLimiter(config)
    else:
        raise ValueError(f"Unsupported rate limit strategy: {config.strategy}")


# 预定义的速率限制配置
RATE_LIMIT_CONFIGS = {
    # 基础限流（面向普通用户）
    "basic": RateLimitConfig(
        max_requests=60,  # 60次/分钟
        window_seconds=60,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    ),
    # 标准限流（面向付费用户）
    "standard": RateLimitConfig(
        max_requests=300,  # 300次/分钟
        window_seconds=60,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    ),
    # 高级限流（面向企业用户）
    "premium": RateLimitConfig(
        max_requests=1200,  # 1200次/分钟
        window_seconds=60,
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        burst_size=200,  # 允许突发200次
    ),
    # Token刷新限流
    "token_refresh": RateLimitConfig(
        max_requests=10,  # 10次/分钟
        window_seconds=60,
        strategy=RateLimitStrategy.FIXED_WINDOW,
    ),
    # API调用限流
    "api_call": RateLimitConfig(
        max_requests=100,  # 100次/分钟
        window_seconds=60,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
    ),
}


def rate_limit_middleware() -> Callable[[Any, Any], Any]:
    """
    创建速率限制中间件。

    用法（FastAPI）:
        from fastapi import FastAPI
        app = FastAPI()
        app.middleware("http")(rate_limit_middleware())
    """
    # 创建默认限制器
    limiter = create_rate_limiter(RATE_LIMIT_CONFIGS["standard"])

    async def middleware(request: Any, call_next: Any) -> Any:
        """中间件函数"""
        # 提取限流key（IP地址或用户ID）
        client_ip = request.client.host if hasattr(request, "client") else "unknown"
        user_id = request.headers.get("X-User-ID", client_ip)
        rate_limit_key = f"user:{user_id}"

        # 检查速率限制
        result = limiter.check_rate_limit(rate_limit_key)

        if not result.allowed:
            # 返回429 Too Many Requests
            from fastapi.responses import (
                JSONResponse,  # type: ignore[import-not-found,unused-ignore]
            )

            logger.warning(
                f"Rate limit exceeded for {rate_limit_key}",
                extra={
                    "rate_limit_key": rate_limit_key,
                    "retry_after": result.retry_after,
                },
            )

            return JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(limiter.config.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_at)),
                    "Retry-After": str(result.retry_after),
                },
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": result.retry_after,
                },
            )

        # 添加速率限制响应头
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter.config.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_at))

        return response

    return middleware
