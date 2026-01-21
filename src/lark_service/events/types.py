"""Type definitions for WebSocket events module.

This module defines dataclasses and type aliases for WebSocket operations.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WebSocketConfig:
    """WebSocket client configuration.

    Contains all configuration parameters for WebSocket connection
    to Feishu platform.

    Attributes
    ----------
        app_id: Feishu application ID
        app_secret: Feishu application secret
        max_reconnect_retries: Maximum number of reconnection attempts
        heartbeat_interval: Heartbeat interval in seconds
        fallback_to_http_callback: Enable fallback to HTTP callback on failure
        token_refresh_threshold: Token refresh threshold (0.0-1.0)
        user_info_sync_enabled: Enable periodic user info synchronization
        user_info_sync_schedule: Cron schedule for user info sync
        auth_request_rate_limit: Maximum auth requests per user per minute

    Example
    ----------
        >>> config = WebSocketConfig(
        ...     app_id="cli_xxx",
        ...     app_secret="secret_xxx",
        ...     max_reconnect_retries=10,
        ...     heartbeat_interval=30
        ... )
    """

    app_id: str
    app_secret: str
    max_reconnect_retries: int = 10
    heartbeat_interval: int = 30
    fallback_to_http_callback: bool = True
    token_refresh_threshold: float = 0.8
    user_info_sync_enabled: bool = False
    user_info_sync_schedule: str = "0 2 * * *"
    auth_request_rate_limit: int = 5


@dataclass
class WebSocketConnectionStatus:
    """WebSocket connection status tracking.

    Tracks the current state and health of WebSocket connection.

    Attributes
    ----------
        is_connected: Current connection status
        last_connected_at: Timestamp of last successful connection
        last_disconnected_at: Timestamp of last disconnection
        reconnect_count: Number of reconnection attempts (resets on success)
        last_error: Last error message (if any)
        heartbeat_count: Total heartbeat count
        last_heartbeat_at: Timestamp of last heartbeat

    Example
    ----------
        >>> status = WebSocketConnectionStatus()
        >>> status.is_connected = True
        >>> status.last_connected_at = datetime.now()
    """

    is_connected: bool = False
    last_connected_at: datetime | None = None
    last_disconnected_at: datetime | None = None
    reconnect_count: int = 0
    last_error: str | None = None
    heartbeat_count: int = 0
    last_heartbeat_at: datetime | None = None

    def mark_connected(self) -> None:
        """Mark connection as established.

        Resets reconnect count and updates connection timestamp.

        Example
        ----------
            >>> status = WebSocketConnectionStatus()
            >>> status.mark_connected()
            >>> assert status.is_connected is True
            >>> assert status.reconnect_count == 0
        """
        self.is_connected = True
        self.last_connected_at = datetime.now()
        self.reconnect_count = 0
        self.last_error = None

    def mark_disconnected(self, error: str | None = None) -> None:
        """Mark connection as disconnected.

        Updates disconnection timestamp and error message.

        Parameters
        ----------
            error: Optional error message describing the disconnection

        Example
        ----------
            >>> status = WebSocketConnectionStatus()
            >>> status.mark_disconnected("Connection timeout")
            >>> assert status.is_connected is False
            >>> assert status.last_error == "Connection timeout"
        """
        self.is_connected = False
        self.last_disconnected_at = datetime.now()
        if error:
            self.last_error = error

    def increment_reconnect(self) -> None:
        """Increment reconnection attempt counter.

        Example
        ----------
            >>> status = WebSocketConnectionStatus()
            >>> status.increment_reconnect()
            >>> assert status.reconnect_count == 1
        """
        self.reconnect_count += 1

    def record_heartbeat(self) -> None:
        """Record a heartbeat event.

        Updates heartbeat counter and timestamp.

        Example
        ----------
            >>> status = WebSocketConnectionStatus()
            >>> status.record_heartbeat()
            >>> assert status.heartbeat_count == 1
            >>> assert status.last_heartbeat_at is not None
        """
        self.heartbeat_count += 1
        self.last_heartbeat_at = datetime.now()
