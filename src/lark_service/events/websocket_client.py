"""WebSocket client for receiving Feishu events.

Provides connection lifecycle management, event registration, reconnection,
and heartbeat tracking for the Feishu WebSocket client.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import lark_oapi as lark

from lark_service.events.exceptions import WebSocketConnectionError
from lark_service.events.types import WebSocketConfig, WebSocketConnectionStatus
from lark_service.monitoring.websocket_metrics import (
    websocket_connection_status,
    websocket_reconnect_total,
)
from lark_service.utils.logger import get_logger

logger = get_logger()


class LarkWebSocketClient:
    """Feishu WebSocket long connection client.

    Handles connection setup, reconnection, heartbeat, and event registration.
    """

    def __init__(
        self,
        config: WebSocketConfig,
        log_level: lark.LogLevel | None = None,
    ) -> None:
        """Initialize WebSocket client.

        Args:
            config: WebSocket client configuration
            log_level: SDK log level override (optional)
        """
        self.config = config
        self.log_level = log_level or lark.LogLevel.INFO
        self.status = WebSocketConnectionStatus()

        self._handlers: dict[str, Callable[..., object]] = {}
        self._ws_client: lark.ws.Client | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._shutdown_event = asyncio.Event()

    def register_handler(self, event_type: str, handler: Callable[..., object]) -> None:
        """Register event handler for specific event type."""
        if not event_type:
            raise ValueError("event_type cannot be empty")
        if not callable(handler):
            raise ValueError("handler must be callable")

        self._handlers[event_type] = handler
        logger.info(
            "WebSocket handler registered",
            extra={"app_id": self.config.app_id, "event_type": event_type},
        )

    def connect(self) -> None:
        """Establish WebSocket connection.

        Note: This is a blocking call that starts the WebSocket client.
        According to lark-oapi SDK, client.start() blocks until connection ends.
        """
        if self.status.is_connected:
            return

        try:
            event_handler = self._build_event_handler()
            self._ws_client = lark.ws.Client(
                self.config.app_id,
                self.config.app_secret,
                event_handler=event_handler,
                log_level=self.log_level,
            )

            logger.info(
                "Starting WebSocket connection (blocking call)...",
                extra={"app_id": self.config.app_id},
            )

            self.status.mark_connected()
            websocket_connection_status.labels(app_id=self.config.app_id).set(1)

            # This is a BLOCKING call - it will not return until connection ends
            self._ws_client.start()

        except Exception as exc:
            self.status.mark_disconnected(str(exc))
            websocket_connection_status.labels(app_id=self.config.app_id).set(0)
            logger.error(
                "WebSocket connection failed",
                extra={"app_id": self.config.app_id, "error": str(exc)},
            )
            raise WebSocketConnectionError(
                f"Failed to connect WebSocket: {exc}",
                app_id=self.config.app_id,
            ) from exc

    def start(self) -> None:
        """Start WebSocket client (blocking call).

        This method blocks until the connection is terminated.
        Use this in a separate thread or process if you need non-blocking behavior.
        """
        self.connect()

    def disconnect(self) -> None:
        """Gracefully shutdown WebSocket client.

        Note: The lark-oapi SDK's ws.Client doesn't provide a disconnect method.
        The connection is typically terminated by the SDK or by process termination.
        """
        self._shutdown_event.set()

        # Note: lark.ws.Client.start() is blocking and doesn't provide a stop() method
        # The connection is managed by the SDK internally
        # We just mark as disconnected and let the SDK handle cleanup

        self.status.mark_disconnected()
        websocket_connection_status.labels(app_id=self.config.app_id).set(0)
        logger.info(
            "WebSocket disconnect requested",
            extra={"app_id": self.config.app_id},
        )

    def _reconnect_with_backoff(self) -> None:
        """Reconnect with exponential backoff (1s → 2s → 4s → 8s).

        Note: Since connect() is blocking, this method should be called
        in a separate thread if non-blocking behavior is needed.
        """
        import time

        last_error: Exception | None = None

        for attempt in range(self.config.max_reconnect_retries):
            delay = min(2**attempt, 8)
            self.status.increment_reconnect()
            websocket_reconnect_total.labels(app_id=self.config.app_id, outcome="attempt").inc()
            logger.warning(
                "WebSocket reconnect attempt",
                extra={
                    "app_id": self.config.app_id,
                    "attempt": attempt + 1,
                    "delay": delay,
                },
            )
            time.sleep(delay)

            try:
                self.connect()
                websocket_reconnect_total.labels(app_id=self.config.app_id, outcome="success").inc()
                return
            except WebSocketConnectionError as exc:
                last_error = exc
                websocket_reconnect_total.labels(app_id=self.config.app_id, outcome="failure").inc()

        if self.config.fallback_to_http_callback:
            logger.error(
                "WebSocket reconnect failed; fallback enabled",
                extra={"app_id": self.config.app_id},
            )

        raise WebSocketConnectionError(
            "WebSocket reconnect failed after max retries",
            app_id=self.config.app_id,
        ) from last_error

    def _build_event_handler(self) -> lark.EventDispatcherHandler:
        builder = lark.EventDispatcherHandler.builder("", "")

        for event_type, handler in self._handlers.items():
            if event_type == "card.action.trigger":
                builder = builder.register_p2_card_action_trigger(handler)
            else:
                raise ValueError(f"Unsupported event_type: {event_type}")

        return builder.build()

    def _start_heartbeat(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            return
        self._shutdown_event.clear()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        while not self._shutdown_event.is_set():
            await asyncio.sleep(self.config.heartbeat_interval)
            if self._shutdown_event.is_set():
                break
            self.status.record_heartbeat()
            logger.debug(
                "WebSocket heartbeat",
                extra={
                    "app_id": self.config.app_id,
                    "heartbeat_count": self.status.heartbeat_count,
                },
            )

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.status.is_connected
