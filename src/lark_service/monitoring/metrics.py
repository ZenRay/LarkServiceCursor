"""
Prometheus metrics collection for Lark Service.

Provides comprehensive metrics for:
- HTTP request latency and throughput
- Token management operations
- API call statistics
- Error rates and types
- Business metrics
"""

import time
from collections.abc import Callable
from typing import Any

from prometheus_client import (  # type: ignore[import-not-found]
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


class MetricsCollector:
    """
    Centralized metrics collector for Lark Service.

    Collects and exposes Prometheus metrics for monitoring application
    performance and business operations.
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """
        Initialize metrics collector.

        Args:
            registry: Prometheus registry. If None, uses default registry.
        """
        self.registry = registry or CollectorRegistry()

        # HTTP Metrics
        self.http_requests_total = Counter(
            "lark_service_http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "lark_service_http_request_duration_seconds",
            "HTTP request latency in seconds",
            ["method", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry,
        )

        # Token Management Metrics
        self.token_refreshes_total = Counter(
            "lark_service_token_refreshes_total",
            "Total number of token refreshes",
            ["app_id", "token_type", "status"],
            registry=self.registry,
        )

        self.token_cache_hits_total = Counter(
            "lark_service_token_cache_hits_total",
            "Total number of token cache hits",
            ["app_id", "token_type"],
            registry=self.registry,
        )

        self.token_cache_misses_total = Counter(
            "lark_service_token_cache_misses_total",
            "Total number of token cache misses",
            ["app_id", "token_type"],
            registry=self.registry,
        )

        self.active_tokens = Gauge(
            "lark_service_active_tokens",
            "Number of active tokens in cache",
            ["app_id", "token_type"],
            registry=self.registry,
        )

        # API Call Metrics
        self.api_calls_total = Counter(
            "lark_service_api_calls_total",
            "Total number of Lark API calls",
            ["service", "method", "status"],
            registry=self.registry,
        )

        self.api_call_duration_seconds = Histogram(
            "lark_service_api_call_duration_seconds",
            "Lark API call latency in seconds",
            ["service", "method"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry,
        )

        self.api_errors_total = Counter(
            "lark_service_api_errors_total",
            "Total number of API errors",
            ["service", "method", "error_code"],
            registry=self.registry,
        )

        # Retry Metrics
        self.retry_attempts_total = Counter(
            "lark_service_retry_attempts_total",
            "Total number of retry attempts",
            ["operation", "attempt"],
            registry=self.registry,
        )

        # Database Metrics
        self.db_operations_total = Counter(
            "lark_service_db_operations_total",
            "Total number of database operations",
            ["operation", "table", "status"],
            registry=self.registry,
        )

        self.db_connection_pool_size = Gauge(
            "lark_service_db_connection_pool_size",
            "Database connection pool size",
            registry=self.registry,
        )

        self.db_connection_pool_available = Gauge(
            "lark_service_db_connection_pool_available",
            "Available connections in pool",
            registry=self.registry,
        )

        # Cache Metrics (Redis/Memory)
        self.cache_operations_total = Counter(
            "lark_service_cache_operations_total",
            "Total number of cache operations",
            ["operation", "cache_type", "status"],
            registry=self.registry,
        )

        # Message Queue Metrics
        self.mq_messages_published_total = Counter(
            "lark_service_mq_messages_published_total",
            "Total number of messages published",
            ["queue", "status"],
            registry=self.registry,
        )

        self.mq_messages_consumed_total = Counter(
            "lark_service_mq_messages_consumed_total",
            "Total number of messages consumed",
            ["queue", "status"],
            registry=self.registry,
        )

        # Business Metrics
        self.messages_sent_total = Counter(
            "lark_service_messages_sent_total",
            "Total number of messages sent",
            ["message_type", "status"],
            registry=self.registry,
        )

        self.documents_created_total = Counter(
            "lark_service_documents_created_total",
            "Total number of documents created",
            ["doc_type", "status"],
            registry=self.registry,
        )

        self.user_queries_total = Counter(
            "lark_service_user_queries_total",
            "Total number of user queries",
            ["query_type", "status"],
            registry=self.registry,
        )

    def record_http_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """
        Record HTTP request metrics.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status: HTTP status code
            duration: Request duration in seconds
        """
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    def record_token_refresh(self, app_id: str, token_type: str, success: bool) -> None:
        """
        Record token refresh operation.

        Args:
            app_id: Application ID
            token_type: Type of token (tenant_access_token, etc.)
            success: Whether refresh was successful
        """
        status = "success" if success else "failure"
        self.token_refreshes_total.labels(app_id=app_id, token_type=token_type, status=status).inc()

    def record_token_cache_hit(self, app_id: str, token_type: str) -> None:
        """Record token cache hit."""
        self.token_cache_hits_total.labels(app_id=app_id, token_type=token_type).inc()

    def record_token_cache_miss(self, app_id: str, token_type: str) -> None:
        """Record token cache miss."""
        self.token_cache_misses_total.labels(app_id=app_id, token_type=token_type).inc()

    def set_active_tokens(self, app_id: str, token_type: str, count: int) -> None:
        """Set the number of active tokens."""
        self.active_tokens.labels(app_id=app_id, token_type=token_type).set(count)

    def record_api_call(self, service: str, method: str, status: str, duration: float) -> None:
        """
        Record Lark API call metrics.

        Args:
            service: Service name (messaging, clouddoc, etc.)
            method: API method name
            status: Call status (success, error, timeout)
            duration: Call duration in seconds
        """
        self.api_calls_total.labels(service=service, method=method, status=status).inc()
        self.api_call_duration_seconds.labels(service=service, method=method).observe(duration)

    def record_api_error(self, service: str, method: str, error_code: str | int) -> None:
        """Record API error."""
        self.api_errors_total.labels(
            service=service, method=method, error_code=str(error_code)
        ).inc()

    def record_retry_attempt(self, operation: str, attempt: int) -> None:
        """Record retry attempt."""
        self.retry_attempts_total.labels(operation=operation, attempt=str(attempt)).inc()

    def record_db_operation(self, operation: str, table: str, success: bool) -> None:
        """Record database operation."""
        status = "success" if success else "failure"
        self.db_operations_total.labels(operation=operation, table=table, status=status).inc()

    def generate_metrics(self) -> bytes:
        """
        Generate Prometheus metrics in text format.

        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry)  # type: ignore[no-any-return]

    def get_content_type(self) -> str:
        """
        Get the content type for metrics response.

        Returns:
            Content-Type header value
        """
        return CONTENT_TYPE_LATEST  # type: ignore[no-any-return]


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def metrics_middleware() -> Callable[[Any, Any], Any]:
    """
    Create metrics middleware for FastAPI/Starlette.

    Returns:
        Middleware function
    """
    collector = get_metrics_collector()

    async def middleware(request: Any, call_next: Any) -> Any:
        """Process request and record metrics."""
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        collector.record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration,
        )

        return response

    return middleware
