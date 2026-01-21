"""Utility modules for lark_service.

Provides:
- Logging: Structured logging with context support
- Validators: Input validation utilities
- Masking: Sensitive data masking utilities
"""

from typing import Any

from lark_service.utils.logger import (
    LoggerContextManager,
    clear_request_context,
    get_logger,
    set_request_context,
    setup_logger,
)

__all__ = [
    # Logger
    "setup_logger",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "LoggerContextManager",
    # Masking (imported lazily to avoid circular imports)
    "mask_email",
    "mask_mobile",
    "mask_token",
    "mask_user_id",
    "mask_dict",
    "mask_log_message",
    # Validators
    "validate_app_id",
    "validate_app_secret",
    "validate_open_id",
    "validate_user_id",
    "validate_union_id",
    "validate_chat_id",
    "validate_token",
    "validate_url",
    "validate_file_path",
    "validate_positive_int",
    "validate_non_negative_float",
    "validate_non_negative_int",
    "validate_non_empty_string",
    "validate_enum",
]


def __getattr__(name: str) -> Any:
    """Lazy import to avoid circular imports."""
    if name in [
        "mask_email",
        "mask_mobile",
        "mask_token",
        "mask_user_id",
        "mask_dict",
        "mask_log_message",
    ]:
        from lark_service.utils import masking

        return getattr(masking, name)
    if name in [
        "validate_app_id",
        "validate_app_secret",
        "validate_chat_id",
        "validate_enum",
        "validate_file_path",
        "validate_non_empty_string",
        "validate_non_negative_float",
        "validate_non_negative_int",
        "validate_open_id",
        "validate_positive_int",
        "validate_token",
        "validate_union_id",
        "validate_url",
        "validate_user_id",
    ]:
        from lark_service.utils import validators

        return getattr(validators, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
