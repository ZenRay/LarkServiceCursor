"""
Monitoring and metrics collection for Lark Service.

This module provides Prometheus metrics integration for monitoring application
performance, business metrics, and system health.
"""

from lark_service.monitoring.metrics import (
    MetricsCollector,
    get_metrics_collector,
    metrics_middleware,
)

__all__ = [
    "MetricsCollector",
    "get_metrics_collector",
    "metrics_middleware",
]
