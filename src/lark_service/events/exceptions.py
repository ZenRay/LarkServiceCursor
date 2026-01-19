"""Exception classes for WebSocket events module.

This module defines custom exceptions for WebSocket connection errors.
"""


class WebSocketError(Exception):
    """Base exception for WebSocket errors.

    All WebSocket-related exceptions inherit from this class.

    Attributes
    ----------
        message: Error message describing the WebSocket failure
        app_id: Optional app ID for tracking

    Example
    ----------
        >>> raise WebSocketError("WebSocket failed", app_id="cli_xxx")
    """

    def __init__(
        self,
        message: str,
        app_id: str | None = None,
    ) -> None:
        """Initialize WebSocket error.

        Parameters
        ----------
            message: Error message
            app_id: Optional app ID for context
        """
        super().__init__(message)
        self.message = message
        self.app_id = app_id


class WebSocketConnectionError(WebSocketError):
    """WebSocket connection failed.

    Raised when unable to establish or maintain WebSocket
    connection to Feishu platform.

    Example
    ----------
        >>> raise WebSocketConnectionError("Connection failed after 10 retries", app_id="cli_xxx")
    """

    pass
