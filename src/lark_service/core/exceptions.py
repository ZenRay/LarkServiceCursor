"""Custom exceptions for Lark Service.

This module defines all custom exceptions used throughout the application.
"""

from typing import Any


class LarkServiceError(Exception):
    """Base exception for all Lark Service errors.

    All custom exceptions should inherit from this base class.

    Attributes
    ----------
        message: Error message
        details: Additional error details
        error_code: Optional error code for categorization
    """

    def __init__(
        self, message: str, details: dict[str, Any] | None = None, error_code: str | None = None
    ) -> None:
        """Initialize LarkServiceError.

        Parameters
        ----------
            message: Error message
            details: Additional error details
            error_code: Optional error code
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code


class ConfigError(LarkServiceError):
    """Configuration-related errors.

    Raised when configuration is missing, invalid, or cannot be loaded.

    Example
    ----------
        >>> raise ConfigError("Missing POSTGRES_HOST environment variable")
    """

    pass


class TokenAcquisitionError(LarkServiceError):
    """Token acquisition or refresh errors.

    Raised when token cannot be obtained or refreshed from Lark API.

    Example
    ----------
        >>> raise TokenAcquisitionError(
        ...     "Failed to acquire app_access_token",
        ...     details={"app_id": "cli_xxx", "status_code": 401}
        ... )
    """

    pass


class TokenExpiredError(LarkServiceError):
    """Token expiration errors.

    Raised when a token has expired and cannot be used.

    Example
    ----------
        >>> raise TokenExpiredError(
        ...     "Token expired",
        ...     details={"app_id": "cli_xxx", "expired_at": "2024-01-01T00:00:00"}
        ... )
    """

    pass


class APIError(LarkServiceError):
    """Lark API call errors.

    Raised when API calls fail due to network, authentication, or server errors.

    Attributes
    ----------
        status_code: HTTP status code
        response_body: API response body
        request_id: Lark API request ID for tracking
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize APIError.

        Parameters
        ----------
            message: Error message
            status_code: HTTP status code
            response_body: API response body
            request_id: Lark API request ID
            **kwargs: Additional arguments passed to LarkServiceError
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body or {}
        self.request_id = request_id


class RateLimitError(APIError):
    """API rate limit errors.

    Raised when API rate limit is exceeded.

    Attributes
    ----------
        retry_after: Seconds to wait before retrying
    """

    def __init__(self, message: str, retry_after: int | None = None, **kwargs: Any) -> None:
        """Initialize RateLimitError.

        Parameters
        ----------
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments passed to APIError
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationError(LarkServiceError):
    """Input validation errors.

    Raised when input parameters fail validation.

    Example
    ----------
        >>> raise ValidationError(
        ...     "Invalid app_id format",
        ...     details={"app_id": "invalid", "expected_pattern": "cli_[a-z0-9]{16}"}
        ... )
    """

    pass


class StorageError(LarkServiceError):
    """Database or storage errors.

    Raised when database operations fail.

    Example
    ----------
        >>> raise StorageError(
        ...     "Failed to save token to database",
        ...     details={"app_id": "cli_xxx", "error": "Connection timeout"}
        ... )
    """

    pass


class LockAcquisitionError(LarkServiceError):
    """Lock acquisition errors.

    Raised when unable to acquire a lock for token refresh.

    Attributes
    ----------
        lock_key: The lock key that failed to acquire
        timeout: Lock acquisition timeout in seconds
    """

    def __init__(
        self, message: str, lock_key: str | None = None, timeout: float | None = None, **kwargs: Any
    ) -> None:
        """Initialize LockAcquisitionError.

        Parameters
        ----------
            message: Error message
            lock_key: The lock key that failed to acquire
            timeout: Lock acquisition timeout in seconds
            **kwargs: Additional arguments passed to LarkServiceError
        """
        super().__init__(message, **kwargs)
        self.lock_key = lock_key
        self.timeout = timeout


class AuthenticationError(LarkServiceError):
    """User authentication errors.

    Raised when user authentication fails or session expires.

    Example
    ----------
        >>> raise AuthenticationError(
        ...     "Authentication session expired",
        ...     details={"session_id": "xxx", "expired_at": "2024-01-01T00:00:00"}
        ... )
    """

    pass


class InvalidParameterError(ValidationError):
    """Invalid parameter errors.

    Raised when input parameters are invalid (e.g., file size exceeds limit,
    unsupported file type, empty content).

    Example
    ----------
        >>> raise InvalidParameterError(
        ...     "File size exceeds maximum limit of 10MB",
        ...     details={"file_size": 12582912, "max_size": 10485760}
        ... )
    """

    pass


class RetryableError(APIError):
    """Retryable API errors.

    Raised when an API call fails but can be retried.

    Example
    ----------
        >>> raise RetryableError(
        ...     "Failed to upload image",
        ...     details={"code": 500, "msg": "Internal server error"}
        ... )
    """

    pass


class RequestTimeoutError(APIError):
    """Request timeout errors.

    Raised when an API request times out.

    Example
    ----------
        >>> raise RequestTimeoutError(
        ...     "Request timed out after 30 seconds",
        ...     details={"timeout": 30, "operation": "upload_image"}
        ... )
    """

    pass
