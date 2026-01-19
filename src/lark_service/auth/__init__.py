"""User authentication module for Lark Service.

This module provides WebSocket-based user authorization using interactive cards.
"""

from .exceptions import (
    AuthenticationRequiredError,
    AuthError,
    AuthorizationCodeExpiredError,
    AuthorizationRejectedError,
    AuthSessionExpiredError,
    AuthSessionNotFoundError,
    TokenExpiredError,
    TokenRefreshFailedError,
)
from .types import AuthCardOptions, UserInfo

__all__ = [
    "AuthError",
    "AuthenticationRequiredError",
    "AuthorizationCodeExpiredError",
    "AuthorizationRejectedError",
    "AuthSessionExpiredError",
    "AuthSessionNotFoundError",
    "TokenExpiredError",
    "TokenRefreshFailedError",
    "AuthCardOptions",
    "UserInfo",
]
