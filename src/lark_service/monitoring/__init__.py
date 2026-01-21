"""
Monitoring and metrics collection for Lark Service.

This module provides Prometheus metrics integration for monitoring application
performance, business metrics, and system health.
"""

from lark_service.monitoring.metrics import LarkServiceMetrics, metrics
from lark_service.monitoring.websocket_metrics import (
    auth_duration_seconds,
    auth_failure_total,
    auth_session_active,
    auth_session_expired_total,
    auth_session_total,
    auth_success_total,
    token_active_count,
    token_refresh_total,
    websocket_connection_status,
    websocket_reconnect_total,
)

__all__ = [
    "LarkServiceMetrics",
    "metrics",
    "websocket_connection_status",
    "websocket_reconnect_total",
    "auth_session_total",
    "auth_session_active",
    "auth_session_expired_total",
    "auth_success_total",
    "auth_failure_total",
    "auth_duration_seconds",
    "token_refresh_total",
    "token_active_count",
]
