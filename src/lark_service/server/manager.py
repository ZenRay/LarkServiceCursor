"""Callback server manager for optional server lifecycle control.

This module provides a manager for controlling the HTTP callback server
lifecycle, allowing it to be started only when needed.
"""

import os
import threading
from typing import Any

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.server.callback_server import CallbackServer
from lark_service.server.handlers.card_auth import create_card_auth_handler
from lark_service.utils.logger import get_logger

logger = get_logger()


class CallbackServerManager:
    """Manager for HTTP callback server lifecycle.

    Provides control over when the callback server is running, allowing
    it to be started only when card authorization or other callbacks are needed.

    Attributes
    ----------
        server: CallbackServer instance
        server_thread: Thread running the server
        is_running: Whether server is currently running

    Example
    ----------
        >>> # Initialize manager
        >>> manager = CallbackServerManager(
        ...     verification_token="v_xxx",
        ...     encrypt_key="encrypt_xxx",
        ...     host="0.0.0.0",
        ...     port=8080,
        ... )
        >>>
        >>> # Register handlers
        >>> manager.register_card_auth_handler(card_auth_handler)
        >>>
        >>> # Start server only when needed
        >>> if manager.should_start():
        ...     manager.start()
        >>>
        >>> # Stop server
        >>> manager.stop()
    """

    def __init__(
        self,
        verification_token: str,
        encrypt_key: str | None = None,
        host: str = "0.0.0.0",  # nosec B104
        port: int = 8080,
        auto_start: bool = False,
    ) -> None:
        """Initialize callback server manager.

        Parameters
        ----------
            verification_token: Lark verification token
            encrypt_key: Optional encryption key for signature verification
            host: Server host (defaults to env var or "0.0.0.0")
            port: Server port (defaults to env var or 8080)
            auto_start: Whether to auto-start server if enabled
        """
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.host = host if host != "0.0.0.0" else os.getenv("CALLBACK_SERVER_HOST", "0.0.0.0")  # nosec B104
        self.port = port if port != 8080 else int(os.getenv("CALLBACK_SERVER_PORT", "8080"))
        self.auto_start = auto_start

        self.server: CallbackServer | None = None
        self.server_thread: threading.Thread | None = None
        self._is_running = False

        # Check if server should be enabled
        self._enabled = self._check_enabled()

        logger.info(
            f"CallbackServerManager initialized (enabled={self._enabled})",
            extra={
                "enabled": self._enabled,
                "host": self.host,
                "port": self.port,
                "auto_start": self.auto_start,
            },
        )

    def _check_enabled(self) -> bool:
        """Check if callback server should be enabled.

        Reads CALLBACK_SERVER_ENABLED environment variable.

        Returns
        -------
            bool: Whether server is enabled
        """
        enabled_str = os.getenv("CALLBACK_SERVER_ENABLED", "false").lower()
        return enabled_str in ("true", "1", "yes", "on")

    def is_enabled(self) -> bool:
        """Check if callback server is enabled.

        Returns
        -------
            bool: Whether server is enabled via configuration
        """
        return self._enabled

    def is_running(self) -> bool:
        """Check if callback server is currently running.

        Returns
        -------
            bool: Whether server is running
        """
        return self._is_running

    def should_start(self) -> bool:
        """Check if server should be started.

        Returns
        -------
            bool: Whether server should be started (enabled and not running)
        """
        return self._enabled and not self._is_running

    def register_card_auth_handler(self, card_auth_handler: CardAuthHandler) -> None:
        """Register card authorization callback handler.

        Parameters
        ----------
            card_auth_handler: CardAuthHandler instance

        Example
        ----------
            >>> manager.register_card_auth_handler(card_auth_handler)
        """
        if not self.server:
            self.server = CallbackServer(
                host=self.host,
                port=self.port,
                verification_token=self.verification_token,
                encrypt_key=self.encrypt_key,
            )

        handler = create_card_auth_handler(card_auth_handler)
        self.server.register_handler("card_action_trigger", handler)
        logger.info("Card auth handler registered")

    def register_handler(self, callback_type: str, handler: Any) -> None:
        """Register a custom callback handler.

        Parameters
        ----------
            callback_type: Type of callback
            handler: Handler function

        Example
        ----------
            >>> async def custom_handler(data: dict) -> dict:
            ...     return {"status": "ok"}
            >>> manager.register_handler("custom_event", custom_handler)
        """
        if not self.server:
            self.server = CallbackServer(
                host=self.host,
                port=self.port,
                verification_token=self.verification_token,
                encrypt_key=self.encrypt_key,
            )

        self.server.register_handler(callback_type, handler)
        logger.info(f"Custom handler registered: {callback_type}")

    def start(self) -> None:
        """Start the callback server in a background thread.

        Only starts if server is enabled and not already running.

        Example
        ----------
            >>> if manager.should_start():
            ...     manager.start()
        """
        if not self._enabled:
            logger.info("Callback server is disabled, not starting")
            return

        if self._is_running:
            logger.warning("Callback server is already running")
            return

        if not self.server:
            raise RuntimeError(
                "No callback server initialized. Register at least one handler before starting."
            )

        logger.info(f"Starting callback server on {self.host}:{self.port}")

        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="CallbackServerThread",
        )
        self.server_thread.start()
        self._is_running = True

        logger.info(
            "Callback server started",
            extra={
                "host": self.host,
                "port": self.port,
                "thread_id": self.server_thread.ident,
            },
        )

    def _run_server(self) -> None:
        """Internal method to run server (called in thread)."""
        try:
            if self.server:
                self.server.start()
        except Exception as e:
            logger.error(f"Callback server error: {e}", exc_info=True)
            self._is_running = False

    def stop(self) -> None:
        """Stop the callback server.

        Example
        ----------
            >>> manager.stop()
        """
        if not self._is_running:
            logger.info("Callback server is not running")
            return

        logger.info("Stopping callback server...")

        if self.server:
            self.server.stop()

        if self.server_thread:
            self.server_thread.join(timeout=5)

        self._is_running = False
        logger.info("Callback server stopped")

    def get_status(self) -> dict[str, Any]:
        """Get callback server status.

        Returns
        -------
            dict: Status information

        Example
        ----------
            >>> status = manager.get_status()
            >>> print(status)
            {
                "enabled": True,
                "running": True,
                "host": "0.0.0.0",
                "port": 8080,
                "handlers": ["card_action_trigger"]
            }
        """
        return {
            "enabled": self._enabled,
            "running": self._is_running,
            "host": self.host,
            "port": self.port,
            "handlers": self.server.router.list_handlers() if self.server else [],
        }
