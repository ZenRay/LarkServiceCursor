"""
Standalone metrics server for exposing Prometheus metrics.

This server runs independently and exposes metrics on a dedicated port
(default 9091) for Prometheus to scrape.

Usage:
    python -m lark_service.monitoring.server

Environment Variables:
    METRICS_PORT: Port to expose metrics (default: 9091)
    METRICS_HOST: Host to bind to (default: 0.0.0.0)
"""

import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from lark_service.monitoring.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving Prometheus metrics."""

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET request."""
        if self.path == "/metrics":
            self.serve_metrics()
        elif self.path == "/health":
            self.serve_health()
        else:
            self.send_error(404, "Not Found")

    def serve_metrics(self) -> None:
        """Serve Prometheus metrics."""
        try:
            collector = get_metrics_collector()
            metrics = collector.generate_metrics()
            content_type = collector.get_content_type()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(metrics)))
            self.end_headers()
            self.wfile.write(metrics)

        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            self.send_error(500, "Internal Server Error")

    def serve_health(self) -> None:
        """Serve health check endpoint."""
        response = b'{"status": "healthy"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Override to use Python logging instead of stderr."""
        logger.info(format % args)


def run_metrics_server(host: str = "0.0.0.0", port: int = 9091) -> None:
    """
    Run the metrics server.

    Args:
        host: Host to bind to
        port: Port to expose metrics
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, MetricsHandler)

    logger.info(f"Starting metrics server on {host}:{port}")
    logger.info(f"Metrics endpoint: http://{host}:{port}/metrics")
    logger.info(f"Health endpoint: http://{host}:{port}/health")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server...")
        httpd.shutdown()


def main() -> None:
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration from environment
    host = os.getenv("METRICS_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.getenv("METRICS_PORT", "9091"))

    # Run server
    run_metrics_server(host=host, port=port)


if __name__ == "__main__":
    main()
