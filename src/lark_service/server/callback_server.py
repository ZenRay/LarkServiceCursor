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
        """Handle GET requests (health check and OAuth redirect)."""
        from urllib.parse import parse_qs, urlparse

        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        # Health check endpoint
        if path == "/" or path == "/health":
            self._send_json_response(
                200,
                {
                    "status": "ok",
                    "message": "Lark Callback Server is running",
                    "registered_handlers": self.router.list_handlers(),
                },
            )
            return

        # OAuth redirect callback endpoint
        if path == "/callback":
            # Extract authorization code and state from query parameters
            code = query_params.get("code", [None])[0]
            state = query_params.get("state", [None])[0]  # state = session_id

            logger.info(
                "Received OAuth redirect callback",
                extra={
                    "has_code": bool(code),
                    "session_id": state,
                },
            )

            if not code or not state:
                self._send_html_response(
                    400,
                    "<h1>授权失败</h1><p>缺少必需参数</p>",
                )
                return

            # Transform to callback format and route to handler
            try:
                callback_data = {
                    "type": "oauth_redirect",
                    "authorization_code": code,
                    "state": state,
                    "session_id": state,
                }

                # Route to handler
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    _ = loop.run_until_complete(self.router.route(callback_data))

                    # Send success HTML page
                    self._send_html_response(
                        200,
                        "<h1>授权成功！</h1><p>您可以关闭此页面，返回飞书查看授权状态。</p>",
                    )
                finally:
                    loop.close()

            except Exception as e:
                logger.error(f"Failed to process OAuth callback: {e}", exc_info=True)
                self._send_html_response(
                    500,
                    f"<h1>授权处理失败</h1><p>{str(e)}</p>",
                )
            return

        # 404 for other paths
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

    def _send_html_response(self, status_code: int, html: str) -> None:
        """Send HTML response.

        Parameters
        ----------
            status_code: HTTP status code
            html: HTML content to send
        """
        self.send_response(status_code)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html_page = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>飞书授权</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 1rem;
        }}
        p {{
            color: #666;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html}
    </div>
</body>
</html>
        """
        self.wfile.write(html_page.encode("utf-8"))

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
