"""HTTP server for handling Feishu callbacks.

This module provides a lightweight HTTP server using Python's standard library
http.server for receiving and processing Feishu callbacks without external
dependencies like FastAPI or Flask.
"""

import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from lark_service.cardkit.callback_handler import CallbackHandler as LarkCallbackHandler
from lark_service.server.callback_router import CallbackRouter
from lark_service.utils.logger import get_logger

logger = get_logger()


class CallbackRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Feishu callbacks.

    Handles incoming HTTP requests and routes them to the appropriate
    callback handlers through the CallbackRouter.
    """

    # Class variables set by CallbackServer
    router: CallbackRouter
    lark_callback_handler: LarkCallbackHandler

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests (health check endpoint)."""
        if self.path == "/" or self.path == "/health":
            self._send_json_response(
                200,
                {
                    "status": "ok",
                    "message": "Lark Callback Server is running",
                    "registered_handlers": self.router.list_handlers(),
                },
            )
        else:
            self._send_json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests (callback endpoints)."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(content_length).decode("utf-8")
            request_data = json.loads(request_body)

            # Extract headers for signature verification
            timestamp = self.headers.get("X-Lark-Request-Timestamp")
            nonce = self.headers.get("X-Lark-Request-Nonce")
            signature = self.headers.get("X-Lark-Signature")

            logger.info(
                "Received callback request",
                extra={
                    "path": self.path,
                    "type": request_data.get("type"),
                    "has_signature": bool(signature),
                },
            )

            # Route to appropriate handler
            response = self._handle_callback(request_data, timestamp, nonce, signature)

            self._send_json_response(200, response)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {e}")
            self._send_json_response(400, {"error": "Invalid JSON"})

        except Exception as e:
            logger.error(f"Error processing callback: {e}", exc_info=True)
            self._send_json_response(500, {"error": "Internal server error"})

    def _handle_callback(
        self,
        request_data: dict[str, Any],
        timestamp: str | None,
        nonce: str | None,
        signature: str | None,
    ) -> dict[str, Any]:
        """Handle callback logic with signature verification.

        Parameters
        ----------
            request_data: Callback data from Feishu
            timestamp: Request timestamp header
            nonce: Request nonce header
            signature: Request signature header

        Returns
        -------
            dict: Response to send back to Feishu
        """
        callback_type = request_data.get("type")

        # Handle URL verification (no signature verification needed)
        if callback_type == "url_verification":
            logger.info("Handling URL verification request")
            return self.lark_callback_handler.handle_url_verification(
                challenge=request_data.get("challenge", ""),
                token=request_data.get("token", ""),
            )

        # Verify signature for other callback types
        if signature and timestamp and nonce:
            body = json.dumps(request_data, separators=(",", ":"))
            if not self.lark_callback_handler.verify_signature(timestamp, nonce, body, signature):
                logger.warning("Signature verification failed")
                return {"error": "Invalid signature", "status": "error"}

        # Route to registered handler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(self.router.route(request_data))
            return response
        finally:
            loop.close()

    def _send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        """Send JSON response.

        Parameters
        ----------
            status_code: HTTP status code
            data: Response data to encode as JSON
        """
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Override to use our logger instead of stderr."""
        logger.info(format % args)


class CallbackServer:
    """HTTP callback server for Feishu.

    Provides a complete HTTP server for handling Feishu callbacks with
    signature verification, URL verification, and flexible callback routing.

    Attributes
    ----------
        host: Server host address
        port: Server port
        router: CallbackRouter instance for routing callbacks
        lark_callback_handler: LarkCallbackHandler for verification

    Example
    ----------
        >>> # Initialize server
        >>> server = CallbackServer(
        ...     host="0.0.0.0",
        ...     port=8080,
        ...     verification_token="v_xxx",
        ...     encrypt_key="encrypt_xxx",
        ... )
        >>>
        >>> # Register callback handlers
        >>> async def handle_card_auth(data: dict) -> dict:
        ...     return {"status": "ok"}
        >>> server.register_handler("card_action_trigger", handle_card_auth)
        >>>
        >>> # Start server
        >>> server.start()
    """

    def __init__(
        self,
        host: str,
        port: int,
        verification_token: str,
        encrypt_key: str | None = None,
    ) -> None:
        """Initialize callback server.

        Parameters
        ----------
            host: Server host address (e.g., "0.0.0.0")
            port: Server port (e.g., 8080)
            verification_token: Lark verification token
            encrypt_key: Optional encryption key for signature verification
        """
        self.host = host
        self.port = port

        # Initialize router and callback handler
        self.router = CallbackRouter()
        self.lark_callback_handler = LarkCallbackHandler(
            verification_token=verification_token,
            encrypt_key=encrypt_key,
        )

        # Set class variables for request handler
        CallbackRequestHandler.router = self.router
        CallbackRequestHandler.lark_callback_handler = self.lark_callback_handler

        self._httpd: HTTPServer | None = None

    def register_handler(
        self,
        callback_type: str,
        handler: Any,
    ) -> None:
        """Register a callback handler.

        Parameters
        ----------
            callback_type: Type of callback (e.g., "card_action_trigger")
            handler: Async handler function

        Example
        ----------
            >>> async def handle_card(data: dict) -> dict:
            ...     return {"status": "ok"}
            >>> server.register_handler("card_action_trigger", handle_card)
        """
        self.router.register(callback_type, handler)

    def start(self) -> None:
        """Start the HTTP server.

        Blocks until server is stopped (Ctrl+C or .stop()).

        Example
        ----------
            >>> server.start()  # Server runs until interrupted
        """
        server_address = (self.host, self.port)
        self._httpd = HTTPServer(server_address, CallbackRequestHandler)

        logger.info(
            f"Starting Lark Callback Server on {self.host}:{self.port}",
            extra={"host": self.host, "port": self.port},
        )
        logger.info(f"Callback endpoint: http://{self.host}:{self.port}/callback")
        logger.info(f"Health check: http://{self.host}:{self.port}/health")
        logger.info(f"Registered handlers: {', '.join(self.router.list_handlers()) or 'None'}")

        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            self.stop()

    def stop(self) -> None:
        """Stop the HTTP server.

        Example
        ----------
            >>> server.stop()
        """
        if self._httpd:
            self._httpd.shutdown()
            logger.info("Server stopped")
