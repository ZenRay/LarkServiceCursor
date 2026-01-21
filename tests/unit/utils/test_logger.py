"""Unit tests for logger module.

Tests structured logging with context support.
"""

import logging
from pathlib import Path
from typing import Any

from lark_service.utils.logger import (
    LoggerContextManager,
    clear_request_context,
    get_logger,
    set_request_context,
    setup_logger,
)


class TestLoggerSetup:
    """Test logger setup and configuration."""

    def test_setup_logger_default(self) -> None:
        """Test default logger setup."""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logger_with_level(self) -> None:
        """Test logger setup with custom level."""
        logger = setup_logger("test_logger_debug", level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_setup_logger_with_file(self, tmp_path: Path) -> None:
        """Test logger setup with file handler."""
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_logger_file", log_file=log_file)

        # Check file handler exists
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert log_file.exists()

    def test_setup_logger_json_format(self) -> None:
        """Test logger setup with JSON format."""
        logger = setup_logger("test_logger_json", json_format=True)
        assert len(logger.handlers) > 0

    def test_get_logger(self) -> None:
        """Test getting existing logger."""
        setup_logger("test_get_logger")
        logger = get_logger("test_get_logger")
        assert logger.name == "test_get_logger"


class TestRequestContext:
    """Test request context management."""

    def test_set_request_context(self) -> None:
        """Test setting request context."""
        logger = setup_logger("lark_service")
        set_request_context(request_id="req-123", app_id="cli_abc1234567890def")

        # Verify context is set
        for filter_obj in logger.filters:
            if hasattr(filter_obj, "request_id"):
                assert filter_obj.request_id == "req-123"
                assert filter_obj.app_id == "cli_abc1234567890def"

        # Clean up
        clear_request_context()

    def test_clear_request_context(self) -> None:
        """Test clearing request context."""
        logger = setup_logger("lark_service")
        set_request_context(request_id="req-123", app_id="cli_abc1234567890def")
        clear_request_context()

        # Verify context is cleared
        for filter_obj in logger.filters:
            if hasattr(filter_obj, "request_id"):
                assert filter_obj.request_id is None
                assert filter_obj.app_id is None

    def test_context_manager(self) -> None:
        """Test LoggerContextManager."""
        logger = setup_logger("lark_service")

        with LoggerContextManager(request_id="req-456", app_id="cli_def1234567890abc"):
            # Context should be set
            for filter_obj in logger.filters:
                if hasattr(filter_obj, "request_id"):
                    assert filter_obj.request_id == "req-456"
                    assert filter_obj.app_id == "cli_def1234567890abc"

        # Context should be cleared after exiting
        for filter_obj in logger.filters:
            if hasattr(filter_obj, "request_id"):
                assert filter_obj.request_id is None
                assert filter_obj.app_id is None


class TestLogging:
    """Test actual logging functionality."""

    def test_log_with_context(self, tmp_path: Path, caplog: Any) -> None:
        """Test logging with request context."""
        log_file = tmp_path / "test_context.log"
        logger = setup_logger("lark_service", log_file=log_file)

        with LoggerContextManager(request_id="req-789", app_id="cli_ghi1234567890abc"):
            logger.info("Test message")

        # Check log file contains context
        log_content = log_file.read_text()
        assert "req-789" in log_content
        assert "cli_ghi1234567890abc" in log_content

    def test_log_without_context(self, tmp_path: Path) -> None:
        """Test logging without request context."""
        log_file = tmp_path / "test_no_context.log"
        logger = setup_logger("test_log_no_context", log_file=log_file)

        logger.info("Test message without context")

        # Check log file contains N/A for missing context
        log_content = log_file.read_text()
        assert "N/A" in log_content

    def test_log_levels(self, tmp_path: Path) -> None:
        """Test different log levels."""
        log_file = tmp_path / "test_levels.log"
        logger = setup_logger("test_levels", level="DEBUG", log_file=log_file)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        log_content = log_file.read_text()
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content
        assert "Critical message" in log_content
