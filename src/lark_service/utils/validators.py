"""Input validation utilities.

Provides validators for:
- Application credentials (app_id, app_secret)
- User identifiers (open_id, user_id, union_id)
- Token formats
- URLs and file paths
- Common data types
"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lark_service.core.exceptions import ValidationError


def validate_app_id(app_id: str) -> str:
    """Validate Feishu application ID format.

    Args:
        app_id: Application ID to validate

    Returns:
        Validated app_id

    Raises:
        ValidationError: If app_id format is invalid

    Example:
        >>> validate_app_id("cli_a1b2c3d4e5f6")
        'cli_a1b2c3d4e5f6'
        >>> validate_app_id("invalid")
        Traceback (most recent call last):
        ...
        ValidationError: Invalid app_id format
    """
    if not app_id:
        raise ValidationError("app_id cannot be empty")

    # Feishu app_id format: cli_* or cli_*
    pattern = r"^cli_[a-zA-Z0-9]{16,32}$"
    if not re.match(pattern, app_id):
        raise ValidationError(
            f"Invalid app_id format: {app_id}. "
            "Expected format: cli_[16-32 alphanumeric characters]",
            details={"app_id": app_id, "pattern": pattern},
        )

    return app_id


def validate_app_secret(app_secret: str) -> str:
    """Validate Feishu application secret format.

    Args:
        app_secret: Application secret to validate

    Returns:
        Validated app_secret

    Raises:
        ValidationError: If app_secret format is invalid

    Example:
        >>> validate_app_secret("a1b2c3d4e5f6g7h8i9j0")
        'a1b2c3d4e5f6g7h8i9j0'
    """
    if not app_secret:
        raise ValidationError("app_secret cannot be empty")

    # Minimum length check
    if len(app_secret) < 16:
        raise ValidationError(
            f"app_secret too short: {len(app_secret)} characters. "
            "Minimum 16 characters required.",
            details={"length": len(app_secret), "min_length": 16},
        )

    # Maximum length check
    if len(app_secret) > 128:
        raise ValidationError(
            f"app_secret too long: {len(app_secret)} characters. "
            "Maximum 128 characters allowed.",
            details={"length": len(app_secret), "max_length": 128},
        )

    return app_secret


def validate_open_id(open_id: str) -> str:
    """Validate Feishu OpenID format.

    Args:
        open_id: OpenID to validate

    Returns:
        Validated open_id

    Raises:
        ValidationError: If open_id format is invalid

    Example:
        >>> validate_open_id("ou_1234567890abcdef")
        'ou_1234567890abcdef'
    """
    if not open_id:
        raise ValidationError("open_id cannot be empty")

    # Feishu open_id format: ou_*
    pattern = r"^ou_[a-zA-Z0-9]{16,32}$"
    if not re.match(pattern, open_id):
        raise ValidationError(
            f"Invalid open_id format: {open_id}. "
            "Expected format: ou_[16-32 alphanumeric characters]",
            details={"open_id": open_id, "pattern": pattern},
        )

    return open_id


def validate_user_id(user_id: str) -> str:
    """Validate Feishu User ID format.

    Args:
        user_id: User ID to validate

    Returns:
        Validated user_id

    Raises:
        ValidationError: If user_id format is invalid

    Example:
        >>> validate_user_id("1234567890")
        '1234567890'
    """
    if not user_id:
        raise ValidationError("user_id cannot be empty")

    # Feishu user_id is typically numeric or alphanumeric
    pattern = r"^[a-zA-Z0-9_-]{1,64}$"
    if not re.match(pattern, user_id):
        raise ValidationError(
            f"Invalid user_id format: {user_id}. "
            "Expected: 1-64 alphanumeric characters, underscores, or hyphens",
            details={"user_id": user_id, "pattern": pattern},
        )

    return user_id


def validate_union_id(union_id: str) -> str:
    """Validate Feishu Union ID format.

    Args:
        union_id: Union ID to validate

    Returns:
        Validated union_id

    Raises:
        ValidationError: If union_id format is invalid

    Example:
        >>> validate_union_id("on_1234567890abcdef")
        'on_1234567890abcdef'
    """
    if not union_id:
        raise ValidationError("union_id cannot be empty")

    # Feishu union_id format: on_*
    pattern = r"^on_[a-zA-Z0-9]{16,32}$"
    if not re.match(pattern, union_id):
        raise ValidationError(
            f"Invalid union_id format: {union_id}. "
            "Expected format: on_[16-32 alphanumeric characters]",
            details={"union_id": union_id, "pattern": pattern},
        )

    return union_id


def validate_chat_id(chat_id: str) -> str:
    """Validate Feishu Chat ID format.

    Args:
        chat_id: Chat ID to validate

    Returns:
        Validated chat_id

    Raises:
        ValidationError: If chat_id format is invalid

    Example:
        >>> validate_chat_id("oc_1234567890abcdef")
        'oc_1234567890abcdef'
    """
    if not chat_id:
        raise ValidationError("chat_id cannot be empty")

    # Feishu chat_id format: oc_*
    pattern = r"^oc_[a-zA-Z0-9]{16,32}$"
    if not re.match(pattern, chat_id):
        raise ValidationError(
            f"Invalid chat_id format: {chat_id}. "
            "Expected format: oc_[16-32 alphanumeric characters]",
            details={"chat_id": chat_id, "pattern": pattern},
        )

    return chat_id


def validate_token(token: str, token_type: str = "access_token") -> str:
    """Validate token format.

    Args:
        token: Token to validate
        token_type: Type of token (for error messages)

    Returns:
        Validated token

    Raises:
        ValidationError: If token format is invalid

    Example:
        >>> validate_token("t-abc123def456", "app_access_token")
        't-abc123def456'
    """
    if not token:
        raise ValidationError(f"{token_type} cannot be empty")

    # Minimum length check
    if len(token) < 10:
        raise ValidationError(
            f"{token_type} too short: {len(token)} characters. "
            "Minimum 10 characters required.",
            details={"token_type": token_type, "length": len(token)},
        )

    # Maximum length check
    if len(token) > 1024:
        raise ValidationError(
            f"{token_type} too long: {len(token)} characters. "
            "Maximum 1024 characters allowed.",
            details={"token_type": token_type, "length": len(token)},
        )

    return token


def validate_url(url: str, require_https: bool = True) -> str:
    """Validate URL format.

    Args:
        url: URL to validate
        require_https: Require HTTPS protocol

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL format is invalid

    Example:
        >>> validate_url("https://example.com/callback")
        'https://example.com/callback'
        >>> validate_url("http://example.com", require_https=True)
        Traceback (most recent call last):
        ...
        ValidationError: URL must use HTTPS protocol
    """
    if not url:
        raise ValidationError("URL cannot be empty")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(
            f"Invalid URL format: {url}",
            details={"url": url, "error": str(e)},
        ) from e

    if not parsed.scheme:
        raise ValidationError(
            f"URL missing protocol: {url}",
            details={"url": url},
        )

    if require_https and parsed.scheme != "https":
        raise ValidationError(
            f"URL must use HTTPS protocol: {url}",
            details={"url": url, "scheme": parsed.scheme},
        )

    if not parsed.netloc:
        raise ValidationError(
            f"URL missing domain: {url}",
            details={"url": url},
        )

    return url


def validate_file_path(path: str | Path, must_exist: bool = False) -> Path:
    """Validate file path.

    Args:
        path: File path to validate
        must_exist: Require file to exist

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid

    Example:
        >>> validate_file_path("/tmp/test.txt", must_exist=False)
        PosixPath('/tmp/test.txt')
    """
    if not path:
        raise ValidationError("File path cannot be empty")

    try:
        path_obj = Path(path)
    except Exception as e:
        raise ValidationError(
            f"Invalid file path: {path}",
            details={"path": str(path), "error": str(e)},
        ) from e

    if must_exist and not path_obj.exists():
        raise ValidationError(
            f"File does not exist: {path}",
            details={"path": str(path_obj)},
        )

    return path_obj


def validate_positive_int(value: Any, name: str = "value") -> int:
    """Validate positive integer.

    Args:
        value: Value to validate
        name: Name of value (for error messages)

    Returns:
        Validated integer

    Raises:
        ValidationError: If value is not a positive integer

    Example:
        >>> validate_positive_int(10, "timeout")
        10
        >>> validate_positive_int(-5, "timeout")
        Traceback (most recent call last):
        ...
        ValidationError: timeout must be positive
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"{name} must be an integer: {value}",
            details={"name": name, "value": value, "error": str(e)},
        ) from e

    if int_value <= 0:
        raise ValidationError(
            f"{name} must be positive: {int_value}",
            details={"name": name, "value": int_value},
        )

    return int_value


def validate_non_negative_float(value: Any, name: str = "value") -> float:
    """Validate non-negative float.

    Args:
        value: Value to validate
        name: Name of value (for error messages)

    Returns:
        Validated float

    Raises:
        ValidationError: If value is not a non-negative float

    Example:
        >>> validate_non_negative_float(3.14, "threshold")
        3.14
        >>> validate_non_negative_float(-1.5, "threshold")
        Traceback (most recent call last):
        ...
        ValidationError: threshold cannot be negative
    """
    try:
        float_value = float(value)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"{name} must be a number: {value}",
            details={"name": name, "value": value, "error": str(e)},
        ) from e

    if float_value < 0:
        raise ValidationError(
            f"{name} cannot be negative: {float_value}",
            details={"name": name, "value": float_value},
        )

    return float_value


def validate_enum(value: str, allowed_values: list[str], name: str = "value") -> str:
    """Validate enum value.

    Args:
        value: Value to validate
        allowed_values: List of allowed values
        name: Name of value (for error messages)

    Returns:
        Validated value

    Raises:
        ValidationError: If value is not in allowed values

    Example:
        >>> validate_enum("active", ["active", "inactive"], "status")
        'active'
        >>> validate_enum("deleted", ["active", "inactive"], "status")
        Traceback (most recent call last):
        ...
        ValidationError: Invalid status value
    """
    if value not in allowed_values:
        raise ValidationError(
            f"Invalid {name} value: {value}. "
            f"Allowed values: {', '.join(allowed_values)}",
            details={"name": name, "value": value, "allowed": allowed_values},
        )

    return value
