"""
Main entry point for the Lark Service application.

This module allows the package to be executed with `python -m lark_service`.
For Docker deployment, this starts a simple HTTP health check server.
"""

import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: any) -> None:
        """Suppress default logging."""
        pass


def main() -> None:
    """Start health check server."""
    port = 8000
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Starting health check server on port {port}")
    logger.info("Lark Service is running (health check mode)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        server.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
