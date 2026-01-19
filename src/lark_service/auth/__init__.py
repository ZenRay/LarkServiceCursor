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
from .session_manager import AuthSessionManager
from .types import AuthCardOptions, AuthSession, UserInfo

__all__ = [
    "AuthError",
    "AuthenticationRequiredError",
    "AuthorizationCodeExpiredError",
    "AuthorizationRejectedError",
    "AuthSessionExpiredError",
    "AuthSessionNotFoundError",
    "TokenExpiredError",
    "TokenRefreshFailedError",
    "AuthSessionManager",
    "AuthCardOptions",
    "AuthSession",
    "UserInfo",
]
