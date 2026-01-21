"""WebSocket events module for Lark Service.

This module provides WebSocket client for receiving real-time events from Feishu platform.
"""

from .exceptions import WebSocketConnectionError, WebSocketError
from .types import WebSocketConfig, WebSocketConnectionStatus

__all__ = [
    "WebSocketConnectionError",
    "WebSocketError",
    "WebSocketConfig",
    "WebSocketConnectionStatus",
]
