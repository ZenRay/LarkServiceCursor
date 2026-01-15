"""Core modules for lark_service.

Provides:
- Configuration management
- Exception hierarchy
- Response models
- Token credential pool
- Retry strategy
- Lock management
- Storage services
"""

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    AuthenticationError,
    ConfigError,
    LarkServiceError,
    LockAcquisitionError,
    RateLimitError,
    StorageError,
    TokenAcquisitionError,
    TokenExpiredError,
    ValidationError,
)
from lark_service.core.lock_manager import RefreshLockContext, TokenRefreshLock
from lark_service.core.response import ErrorDetail, StandardResponse
from lark_service.core.retry import RetryStrategy, retry_on_error
from lark_service.core.storage import ApplicationManager, TokenStorageService

__all__ = [
    # Config
    "Config",
    # Exceptions
    "LarkServiceError",
    "ConfigError",
    "TokenAcquisitionError",
    "TokenExpiredError",
    "APIError",
    "RateLimitError",
    "ValidationError",
    "StorageError",
    "LockAcquisitionError",
    "AuthenticationError",
    # Response
    "StandardResponse",
    "ErrorDetail",
    # Credential Pool
    "CredentialPool",
    # Retry
    "RetryStrategy",
    "retry_on_error",
    # Lock Manager
    "TokenRefreshLock",
    "RefreshLockContext",
    # Storage
    "ApplicationManager",
    "TokenStorageService",
]
