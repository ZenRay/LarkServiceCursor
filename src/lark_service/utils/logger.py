"""Structured logging system with context support.

Provides centralized logging with:
- Structured JSON logging for production
- Human-readable console logging for development
- Request ID tracking
- Performance metrics
- Log rotation
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pythonjsonlogger import jsonlogger


class ContextFilter(logging.Filter):
    """Add contextual information to log records.
    
    Attributes:
        request_id: Current request ID for tracing
        app_id: Current application ID
    """

    def __init__(self) -> None:
        """Initialize ContextFilter."""
        super().__init__()
        self.request_id: str | None = None
        self.app_id: str | None = None

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context fields to log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            Always True to allow all records
        """
        record.request_id = self.request_id or "N/A"  # type: ignore[attr-defined]
        record.app_id = self.app_id or "N/A"  # type: ignore[attr-defined]
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields.
    
    Adds timestamp, level, and context information to JSON logs.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record.
        
        Args:
            log_record: Dictionary to add fields to
            record: Original log record
            message_dict: Message dictionary from log call
        """
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add level name
        log_record["level"] = record.levelname
        
        # Add logger name
        log_record["logger"] = record.name
        
        # Add context fields if available
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "app_id"):
            log_record["app_id"] = record.app_id


def setup_logger(
    name: str = "lark_service",
    level: str = "INFO",
    log_file: Path | None = None,
    json_format: bool = False,
) -> logging.Logger:
    """Setup and configure logger.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        json_format: Use JSON format for structured logging
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = setup_logger("my_app", level="DEBUG")
        >>> logger.info("Application started", extra={"version": "1.0.0"})
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Add context filter
    context_filter = ContextFilter()
    logger.addFilter(context_filter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    if json_format:
        # JSON format for production
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s"
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - [%(levelname)s] - "
            "[req:%(request_id)s] [app:%(app_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = "lark_service") -> logging.Logger:
    """Get existing logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
        
    Example:
        >>> logger = get_logger()
        >>> logger.info("Processing request")
    """
    return logging.getLogger(name)


def set_request_context(request_id: str | None = None, app_id: str | None = None) -> None:
    """Set request context for logging.

    Args:
        request_id: Request ID for tracing
        app_id: Application ID

    Example:
        >>> set_request_context(request_id="req-12345", app_id="cli_abc123")
        >>> logger = get_logger()
        >>> logger.info("Request started")  # Will include request_id and app_id
    """
    logger = logging.getLogger("lark_service")
    for filter_obj in logger.filters:
        if isinstance(filter_obj, ContextFilter):
            if request_id is not None:
                filter_obj.request_id = request_id
            if app_id is not None:
                filter_obj.app_id = app_id


def clear_request_context() -> None:
    """Clear request context.
    
    Example:
        >>> clear_request_context()
    """
    logger = logging.getLogger("lark_service")
    for filter_obj in logger.filters:
        if isinstance(filter_obj, ContextFilter):
            filter_obj.request_id = None
            filter_obj.app_id = None


class LoggerContextManager:
    """Context manager for request logging.
    
    Automatically sets and clears request context.
    
    Example:
        >>> with LoggerContextManager(request_id="req-123", app_id="cli_abc"):
        ...     logger = get_logger()
        ...     logger.info("Processing")
    """

    def __init__(self, request_id: str | None = None, app_id: str | None = None) -> None:
        """Initialize context manager.
        
        Args:
            request_id: Request ID for tracing
            app_id: Application ID
        """
        self.request_id = request_id
        self.app_id = app_id

    def __enter__(self) -> "LoggerContextManager":
        """Enter context and set request context.
        
        Returns:
            Self for context manager protocol
        """
        set_request_context(self.request_id, self.app_id)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit context and clear request context.
        
        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        clear_request_context()
