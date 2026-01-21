"""Prometheus metrics for WebSocket connection and auth monitoring."""

from prometheus_client import Counter, Gauge, Histogram

# WebSocket connection metrics
websocket_connection_status = Gauge(
    "lark_service_websocket_connection_status",
    "WebSocket connection status (1=connected, 0=disconnected)",
    ["app_id"],
)

websocket_reconnect_total = Counter(
    "lark_service_websocket_reconnect_total",
    "Total WebSocket reconnection attempts",
    ["app_id", "outcome"],
)

# Auth session metrics
auth_session_total = Counter(
    "lark_service_auth_session_total",
    "Total auth sessions created",
    ["app_id", "auth_method"],
)

auth_session_active = Gauge(
    "lark_service_auth_session_active",
    "Number of active auth sessions",
    ["app_id"],
)

auth_session_expired_total = Counter(
    "lark_service_auth_session_expired_total",
    "Total expired auth sessions cleaned up",
    ["app_id"],
)

# Auth success/failure metrics
auth_success_total = Counter(
    "lark_service_auth_success_total",
    "Total successful auth completions",
    ["app_id", "auth_method"],
)

auth_failure_total = Counter(
    "lark_service_auth_failure_total",
    "Total auth failures",
    ["app_id", "auth_method", "reason"],
)

auth_duration_seconds = Histogram(
    "lark_service_auth_duration_seconds",
    "Auth completion duration in seconds",
    ["app_id", "auth_method"],
    buckets=(1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0),
)

# Token metrics
token_refresh_total = Counter(
    "lark_service_token_refresh_total",
    "Total token refresh attempts",
    ["app_id", "outcome"],
)

token_active_count = Gauge(
    "lark_service_token_active_count",
    "Number of active (non-expired) tokens",
    ["app_id"],
)
