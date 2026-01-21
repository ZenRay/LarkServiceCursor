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

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


class LarkServiceMetrics:
    """
    Lark Service Prometheus metrics collector.

    Provides comprehensive metrics for monitoring service health and performance.
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """
        Initialize metrics collector.

        Args:
            registry: Optional custom Prometheus registry. If None, uses default registry.
        """
        self.registry = registry or CollectorRegistry()

        # === HTTP Request Metrics ===
        self.http_requests_total = Counter(
            "lark_service_http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "lark_service_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry,
        )

        # === Token Management Metrics ===
        self.token_refresh_total = Counter(
            "lark_service_token_refresh_total",
            "Total number of token refresh attempts",
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

        self.token_expiry_seconds = Gauge(
            "lark_service_token_expiry_seconds",
            "Time until token expires (seconds)",
            ["app_id", "token_type"],
            registry=self.registry,
        )

        # === API Call Metrics ===
        self.api_calls_total = Counter(
            "lark_service_api_calls_total",
            "Total number of Lark API calls",
            ["api_name", "status"],
            registry=self.registry,
        )

        self.api_call_duration_seconds = Histogram(
            "lark_service_api_call_duration_seconds",
            "Lark API call duration in seconds",
            ["api_name"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        self.api_rate_limit_hits_total = Counter(
            "lark_service_api_rate_limit_hits_total",
            "Total number of API rate limit hits",
            ["api_name"],
            registry=self.registry,
        )

        self.api_retry_total = Counter(
            "lark_service_api_retry_total",
            "Total number of API retry attempts",
            ["api_name", "reason"],
            registry=self.registry,
        )

        # === Error Metrics ===
        self.errors_total = Counter(
            "lark_service_errors_total",
            "Total number of errors",
            ["error_type", "component"],
            registry=self.registry,
        )

        # === Business Metrics ===
        self.messages_sent_total = Counter(
            "lark_service_messages_sent_total",
            "Total number of messages sent",
            ["message_type", "status"],
            registry=self.registry,
        )

        self.documents_accessed_total = Counter(
            "lark_service_documents_accessed_total",
            "Total number of document accesses",
            ["doc_type", "operation"],
            registry=self.registry,
        )

        # === System Metrics ===
        self.active_connections = Gauge(
            "lark_service_active_connections",
            "Number of active connections",
            ["connection_type"],
            registry=self.registry,
        )

        self.pool_size = Gauge(
            "lark_service_pool_size",
            "Current size of connection pool",
            ["pool_type"],
            registry=self.registry,
        )

    # === HTTP Metrics Methods ===

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
    ) -> None:
        """
        Record HTTP request metrics.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

    def track_http_request(
        self,
        method: str,
        endpoint: str,
    ) -> Callable[..., Any]:
        """
        Context manager/decorator for tracking HTTP requests.

        Args:
            method: HTTP method
            endpoint: API endpoint

        Returns:
            Callable decorator that tracks request duration
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    status_code = getattr(result, "status_code", 200)
                    return result
                except Exception as e:
                    status_code = 500
                    raise e
                finally:
                    duration = time.time() - start_time
                    self.record_http_request(method, endpoint, status_code, duration)

            return wrapper

        return decorator

    # === Token Metrics Methods ===

    def record_token_refresh(
        self,
        app_id: str,
        token_type: str,
        status: str,
    ) -> None:
        """
        Record token refresh attempt.

        Args:
            app_id: Application ID
            token_type: Type of token (app_access_token, user_access_token, etc.)
            status: Refresh status (success, failure)
        """
        self.token_refresh_total.labels(
            app_id=app_id,
            token_type=token_type,
            status=status,
        ).inc()

    def record_token_cache_hit(self, app_id: str, token_type: str) -> None:
        """Record token cache hit."""
        self.token_cache_hits_total.labels(app_id=app_id, token_type=token_type).inc()

    def record_token_cache_miss(self, app_id: str, token_type: str) -> None:
        """Record token cache miss."""
        self.token_cache_misses_total.labels(app_id=app_id, token_type=token_type).inc()

    def set_token_expiry(self, app_id: str, token_type: str, seconds: float) -> None:
        """
        Set token expiry time.

        Args:
            app_id: Application ID
            token_type: Type of token
            seconds: Seconds until expiry
        """
        self.token_expiry_seconds.labels(app_id=app_id, token_type=token_type).set(seconds)

    # === API Metrics Methods ===

    def record_api_call(
        self,
        api_name: str,
        status: str,
        duration: float,
    ) -> None:
        """
        Record API call metrics.

        Args:
            api_name: Name of the API
            status: Call status (success, failure)
            duration: Call duration in seconds
        """
        self.api_calls_total.labels(api_name=api_name, status=status).inc()
        self.api_call_duration_seconds.labels(api_name=api_name).observe(duration)

    def record_api_rate_limit_hit(self, api_name: str) -> None:
        """Record API rate limit hit."""
        self.api_rate_limit_hits_total.labels(api_name=api_name).inc()

    def record_api_retry(self, api_name: str, reason: str) -> None:
        """
        Record API retry attempt.

        Args:
            api_name: Name of the API
            reason: Reason for retry (timeout, rate_limit, server_error)
        """
        self.api_retry_total.labels(api_name=api_name, reason=reason).inc()

    # === Error Metrics Methods ===

    def record_error(self, error_type: str, component: str) -> None:
        """
        Record error occurrence.

        Args:
            error_type: Type of error (ValidationError, NetworkError, etc.)
            component: Component where error occurred
        """
        self.errors_total.labels(error_type=error_type, component=component).inc()

    # === Business Metrics Methods ===

    def record_message_sent(self, message_type: str, status: str) -> None:
        """
        Record message sent.

        Args:
            message_type: Type of message (text, image, card, etc.)
            status: Send status (success, failure)
        """
        self.messages_sent_total.labels(message_type=message_type, status=status).inc()

    def record_document_access(self, doc_type: str, operation: str) -> None:
        """
        Record document access.

        Args:
            doc_type: Type of document (doc, sheet, bitable)
            operation: Operation performed (read, write, create, delete)
        """
        self.documents_accessed_total.labels(doc_type=doc_type, operation=operation).inc()

    # === System Metrics Methods ===

    def set_active_connections(self, connection_type: str, count: int) -> None:
        """Set number of active connections."""
        self.active_connections.labels(connection_type=connection_type).set(count)

    def set_pool_size(self, pool_type: str, size: int) -> None:
        """Set connection pool size."""
        self.pool_size.labels(pool_type=pool_type).set(size)

    # === Export Methods ===

    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus text format.

        Returns:
            Metrics data in Prometheus exposition format
        """
        result = generate_latest(self.registry)
        assert isinstance(result, bytes)
        return result

    @property
    def content_type(self) -> str:
        """Get content type for metrics response."""
        result = CONTENT_TYPE_LATEST
        assert isinstance(result, str)
        return result


# Global metrics instance
metrics = LarkServiceMetrics()
