"""
Standalone metrics server for exposing Prometheus metrics.

This server runs independently and exposes metrics on a dedicated port
(default 9091) for Prometheus to scrape. It also includes a mock data
generator for testing purposes.

Usage:
    python -m lark_service.monitoring.server

Environment Variables:
    METRICS_PORT: Port to expose metrics (default: 9091)
    METRICS_HOST: Host to bind to (default: 0.0.0.0)
"""

import json
import logging
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from lark_service.monitoring.metrics import metrics

logger = logging.getLogger(__name__)


class MockDataGenerator(threading.Thread):
    """Generate mock metrics data in a background thread."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.running = False
        self.collector = metrics

    def run(self) -> None:
        """Run the data generation loop."""
        self.running = True
        logger.info("🎭 Mock data generator started")
        iteration = 0

        while self.running:
            iteration += 1
            try:
                self._generate_http_metrics()
                self._generate_token_metrics()
                self._generate_api_metrics()

                if iteration % 30 == 0:
                    logger.info(f"✅ Generated {iteration} iterations of mock data")

                time.sleep(1)
            except Exception as e:
                logger.error(f"Error generating mock data: {e}")
                time.sleep(1)

    def stop(self) -> None:
        """Stop data generation."""
        self.running = False
        logger.info("⏹️  Mock data generator stopped")

    def _generate_http_metrics(self) -> None:
        """Generate HTTP request metrics."""
        methods = ["GET", "POST", "PUT", "DELETE"]
        endpoints = ["/api/v1/token", "/api/v1/users", "/api/v1/messages"]
        statuses = ["200", "201", "400", "500"]

        method = random.choice(methods)
        endpoint = random.choice(endpoints)
        status = random.choices(statuses, weights=[0.7, 0.2, 0.08, 0.02])[0]

        self.collector.http_requests_total.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()

        duration = random.uniform(0.01, 0.5)
        self.collector.http_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

    def _generate_token_metrics(self) -> None:
        """Generate token management metrics."""
        app_ids = ["app1", "app2", "app3"]
        token_types = ["tenant_access_token", "user_access_token"]

        app_id = random.choice(app_ids)
        token_type = random.choice(token_types)

        if random.random() < 0.8:
            self.collector.token_cache_hits_total.labels(app_id=app_id, token_type=token_type).inc()
        else:
            self.collector.token_cache_misses_total.labels(
                app_id=app_id, token_type=token_type
            ).inc()
            status = "success" if random.random() < 0.95 else "failure"
            self.collector.token_refresh_total.labels(
                app_id=app_id, token_type=token_type, status=status
            ).inc()

        _ = random.randint(5, 20)  # nosec B311 # active_count for future use
        # Note: active_tokens gauge not in current metrics implementation
        # self.collector.active_tokens.labels(app_id=app_id, token_type=token_type).set(active_count)

    def _generate_api_metrics(self) -> None:
        """Generate API call metrics."""
        services = ["messaging", "contact", "bitable", "document"]
        methods_list = ["send_message", "get_user", "create_record", "get_content"]

        service = random.choice(services)
        method = random.choice(methods_list)
        status = "success" if random.random() < 0.95 else "failure"

        self.collector.api_calls_total.labels(service=service, method=method, status=status).inc()

        duration = random.uniform(0.05, 2.0)
        self.collector.api_call_duration_seconds.labels(service=service, method=method).observe(
            duration
        )


_mock_data_generator: Any = None


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving Prometheus metrics."""

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET request."""
        if self.path == "/metrics":
            self.serve_metrics()
        elif self.path == "/health":
            self.serve_health()
        elif self.path == "/start-mock":
            self.start_mock_data()
        elif self.path == "/stop-mock":
            self.stop_mock_data()
        else:
            self.send_error(404, "Not Found")

    def serve_metrics(self) -> None:
        """Serve Prometheus metrics."""
        try:
            from lark_service.monitoring.metrics import metrics as collector

            metrics_data = collector.get_metrics()
            content_type = collector.content_type

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(metrics_data)))
            self.end_headers()
            self.wfile.write(metrics_data)

        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            self.send_error(500, "Internal Server Error")

    def serve_health(self) -> None:
        """Serve health check endpoint."""
        global _mock_data_generator
        mock_status = (
            "running" if _mock_data_generator and _mock_data_generator.running else "stopped"
        )
        response = json.dumps({"status": "healthy", "mock_data": mock_status}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def start_mock_data(self) -> None:
        """Start mock data generation."""
        global _mock_data_generator
        if _mock_data_generator and _mock_data_generator.running:
            response = json.dumps({"status": "already running"}).encode()
        else:
            _mock_data_generator = MockDataGenerator()
            _mock_data_generator.start()
            response = json.dumps({"status": "started"}).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def stop_mock_data(self) -> None:
        """Stop mock data generation."""
        global _mock_data_generator
        if _mock_data_generator and _mock_data_generator.running:
            _mock_data_generator.stop()
            response = json.dumps({"status": "stopped"}).encode()
        else:
            response = json.dumps({"status": "not running"}).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Override to use Python logging instead of stderr."""
        logger.info(format % args)


def run_metrics_server(host: str = "0.0.0.0", port: int = 9091) -> None:  # noqa: S104
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
    logger.info(f"Start mock data: http://{host}:{port}/start-mock")
    logger.info(f"Stop mock data: http://{host}:{port}/stop-mock")

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
