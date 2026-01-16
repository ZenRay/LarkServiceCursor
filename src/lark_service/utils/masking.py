"""Sensitive data masking utilities.

Provides functions to mask sensitive information in logs and outputs:
- Email addresses
- Phone numbers
- Tokens and secrets
- User IDs
"""

import re
from typing import Any


def mask_email(email: str) -> str:
    """Mask email address for logging.

    Shows first 2 characters of username and domain.

    Args:
        email: Email address to mask

    Returns:
        Masked email address

    Examples:
        >>> mask_email("john.doe@example.com")
        'jo***@ex***.com'
        >>> mask_email("a@b.com")
        'a***@b***.com'
    """
    if not email or "@" not in email:
        return "***"

    try:
        username, domain = email.split("@", 1)

        # Mask username: show first 2 chars or first char if too short
        masked_username = username[0] + "***" if len(username) <= 2 else username[:2] + "***"

        # Mask domain: show first 2 chars before dot
        if "." in domain:
            domain_parts = domain.split(".", 1)
            if len(domain_parts[0]) <= 2:
                masked_domain = domain_parts[0][0] + "***." + domain_parts[1]
            else:
                masked_domain = domain_parts[0][:2] + "***." + domain_parts[1]
        else:
            masked_domain = domain[:2] + "***" if len(domain) > 2 else domain[0] + "***"

        return f"{masked_username}@{masked_domain}"
    except Exception:
        return "***@***.***"


def mask_mobile(mobile: str) -> str:
    """Mask mobile number for logging.

    Shows country code and last 4 digits.

    Args:
        mobile: Mobile number to mask

    Returns:
        Masked mobile number

    Examples:
        >>> mask_mobile("+8615680013621")
        '+86****3621'
        >>> mask_mobile("15680013621")
        '156****3621'
        >>> mask_mobile("12345")
        '1***5'
    """
    if not mobile:
        return "***"

    # Remove spaces and dashes
    clean_mobile = mobile.replace(" ", "").replace("-", "")

    if len(clean_mobile) <= 4:
        return clean_mobile[0] + "***" + (clean_mobile[-1] if len(clean_mobile) > 1 else "")

    # If starts with +, keep country code
    if clean_mobile.startswith("+"):
        if len(clean_mobile) <= 7:
            return clean_mobile[:3] + "***" + clean_mobile[-2:]
        return clean_mobile[:3] + "****" + clean_mobile[-4:]

    # Otherwise, show first 3 and last 4
    if len(clean_mobile) <= 7:
        return clean_mobile[:3] + "***" + clean_mobile[-2:]

    return clean_mobile[:3] + "****" + clean_mobile[-4:]


def mask_token(token: str, show_prefix: int = 4, show_suffix: int = 4) -> str:
    """Mask token or secret for logging.

    Shows prefix and suffix only.

    Args:
        token: Token to mask
        show_prefix: Number of prefix characters to show
        show_suffix: Number of suffix characters to show

    Returns:
        Masked token

    Examples:
        >>> mask_token("t-abc123def456ghi789")
        't-ab***i789'
        >>> mask_token("cli_a1b2c3d4e5f6g7h8")
        'cli_***7h8'
    """
    if not token:
        return "***"

    if len(token) <= show_prefix + show_suffix:
        return token[:2] + "***"

    return token[:show_prefix] + "***" + token[-show_suffix:]


def mask_user_id(user_id: str, id_type: str = "open_id") -> str:
    """Mask user ID for logging.

    Shows prefix and last 4 characters.

    Args:
        user_id: User ID to mask
        id_type: Type of ID (for determining prefix length)

    Returns:
        Masked user ID

    Examples:
        >>> mask_user_id("ou_1234567890abcdefghij")
        'ou_***ghij'
        >>> mask_user_id("on_1234567890abcdefghij", "union_id")
        'on_***ghij'
    """
    if not user_id:
        return "***"

    # Determine prefix length based on ID type
    prefix_len = 3 if user_id.startswith(("ou_", "on_", "oc_")) else 2

    if len(user_id) <= prefix_len + 4:
        return user_id[:prefix_len] + "***"

    return user_id[:prefix_len] + "***" + user_id[-4:]


def mask_dict(data: dict[str, Any], sensitive_keys: list[str] | None = None) -> dict[str, Any]:
    """Mask sensitive fields in a dictionary.

    Args:
        data: Dictionary to mask
        sensitive_keys: List of keys to mask (default: common sensitive keys)

    Returns:
        Dictionary with masked values

    Examples:
        >>> mask_dict({"email": "john@example.com", "name": "John"})
        {'email': 'jo***@ex***.com', 'name': 'John'}
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "email",
            "mobile",
            "phone",
            "token",
            "secret",
            "password",
            "access_token",
            "refresh_token",
            "app_secret",
            "api_key",
        ]

    masked = data.copy()

    for key, value in masked.items():
        if not isinstance(value, str):
            continue

        key_lower = key.lower()

        # Check if key matches sensitive patterns
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if "email" in key_lower:
                masked[key] = mask_email(value)
            elif "mobile" in key_lower or "phone" in key_lower:
                masked[key] = mask_mobile(value)
            elif "token" in key_lower or "secret" in key_lower or "key" in key_lower:
                masked[key] = mask_token(value)
            elif "password" in key_lower:
                masked[key] = "***"
            else:
                masked[key] = mask_token(value)

    return masked


def mask_log_message(message: str) -> str:
    """Mask sensitive information in log message.

    Automatically detects and masks:
    - Email addresses
    - Phone numbers (with +country code)
    - Tokens (t-*, cli_*, ou_*, etc.)

    Args:
        message: Log message to mask

    Returns:
        Masked log message

    Examples:
        >>> mask_log_message("User john@example.com logged in")
        'User jo***@ex***.com logged in'
        >>> mask_log_message("Token: t-abc123def456")
        'Token: t-ab***f456'
    """
    # Mask email addresses
    message = re.sub(
        r"\b([a-zA-Z0-9._%+-]{1,2})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]{1,2})[a-zA-Z0-9.-]*\.[a-zA-Z]{2,}\b",
        r"\1***@\2***",
        message,
    )

    # Mask phone numbers with country code
    message = re.sub(r"\+\d{1,3}\d{4,}\d{4}", lambda m: mask_mobile(m.group(0)), message)

    # Mask tokens (t-, cli_, ou_, on_, oc_)
    message = re.sub(
        r"\b(t-|cli_|ou_|on_|oc_)[a-zA-Z0-9]{12,}\b", lambda m: mask_token(m.group(0)), message
    )

    return message
