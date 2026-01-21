"""
Main entry point for the Lark Service application.

This module can be executed with `python -m lark_service` and supports:
1. Scheduler service (定时任务)
2. Monitoring metrics server (Prometheus 指标)
3. Health check endpoint
"""

import logging
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from lark_service.monitoring.metrics import metrics
from lark_service.scheduler.scheduler import SchedulerService
from lark_service.scheduler.tasks import register_scheduled_tasks
from lark_service.utils.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# Global references for graceful shutdown
scheduler_service: SchedulerService | None = None
metrics_server: HTTPServer | None = None
metrics_thread: threading.Thread | None = None


def signal_handler(signum: Any, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown()
    sys.exit(0)


def shutdown() -> None:
    """Shutdown all services."""
    global scheduler_service, metrics_server

    if scheduler_service:
        logger.info("Stopping scheduler...")
        try:
            scheduler_service.shutdown(wait=True)
            logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    if metrics_server:
        logger.info("Stopping metrics server...")
        try:
            metrics_server.shutdown()
            logger.info("Metrics server stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping metrics server: {e}")


class MetricsHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Prometheus metrics and health checks."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path == "/health":
            self._serve_health()
        else:
            self.send_error(404)

    def _serve_metrics(self) -> None:
        """Serve Prometheus metrics."""
        try:
            metrics_data = metrics.get_metrics()
            self.send_response(200)
            self.send_header("Content-Type", metrics.content_type)
            self.end_headers()
            self.wfile.write(metrics_data)
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            self.send_error(500)

    def _serve_health(self) -> None:
        """Serve health check."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Suppress default logging."""
        pass


def start_metrics_server_thread(port: int) -> None:
    """Start metrics server in a separate thread."""
    global metrics_server

    try:
        metrics_server = HTTPServer(("0.0.0.0", port), MetricsHandler)  # nosec B104
        logger.info(f"Metrics server thread started on port {port}")
        metrics_server.serve_forever()
    except Exception as e:
        logger.error(f"Metrics server error: {e}")


def main() -> None:
    """Start the Lark Service application."""
    global scheduler_service, metrics_server, metrics_thread

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        logger.info("=" * 70)
        logger.info("  Starting Lark Service")
        logger.info("=" * 70)

        # Check environment
        env = os.getenv("ENVIRONMENT", "development")
        logger.info(f"Environment: {env}")

        # Start Prometheus metrics server in a separate thread
        metrics_port = int(os.getenv("METRICS_PORT", "9090"))
        prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"

        if prometheus_enabled:
            logger.info(f"Starting Prometheus metrics server on port {metrics_port}...")
            metrics_thread = threading.Thread(
                target=start_metrics_server_thread, args=(metrics_port,), daemon=True
            )
            metrics_thread.start()
            time.sleep(0.5)  # Give it time to start
            logger.info(f"✅ Metrics server started: http://0.0.0.0:{metrics_port}/metrics")
        else:
            logger.info("⏭️  Prometheus metrics disabled")

        # Initialize and start scheduler
        scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

        if scheduler_enabled:
            logger.info("Initializing scheduler...")
            scheduler_service = SchedulerService()
            register_scheduled_tasks(scheduler_service)
            scheduler_service.start()
            logger.info("✅ Scheduler started successfully")
        else:
            logger.info("⏭️  Scheduler disabled")

        # Log service status
        logger.info("=" * 70)
        logger.info("  Lark Service is running")
        logger.info("=" * 70)
        if prometheus_enabled:
            logger.info(f"  📊 Metrics: http://0.0.0.0:{metrics_port}/metrics")
            logger.info(f"  ❤️  Health: http://0.0.0.0:{metrics_port}/health")
        logger.info(f"  📅 Scheduler: {'Running' if scheduler_enabled else 'Disabled'}")
        logger.info("=" * 70)
        logger.info("Press Ctrl+C to stop...")

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down gracefully...")
        shutdown()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        shutdown()
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    main()
