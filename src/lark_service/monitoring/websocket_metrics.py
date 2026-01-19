"""Prometheus metrics for WebSocket connection monitoring."""

from prometheus_client import Counter, Gauge

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
