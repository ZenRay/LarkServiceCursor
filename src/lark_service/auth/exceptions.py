"""Exception classes for user authentication module.

This module defines custom exceptions for authentication and authorization errors.
"""


class AuthError(Exception):
    """Base exception for authentication errors.

    All authentication-related exceptions inherit from this class.

    Attributes
    ----------
        message: Error message describing the authentication failure
        session_id: Optional session ID for tracking
        user_id: Optional user ID for tracking

    Example
    ----------
        >>> raise AuthError("Authentication failed", session_id="sess_123")
    """

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initialize authentication error.

        Parameters
        ----------
            message: Error message
            session_id: Optional session ID for context
            user_id: Optional user ID for context
        """
        super().__init__(message)
        self.message = message
        self.session_id = session_id
        self.user_id = user_id


class AuthenticationRequiredError(AuthError):
    """User access token is required but not available.

    Raised when an API call requires user_access_token but the user
    has not completed authorization yet.

    Example
    ----------
        >>> raise AuthenticationRequiredError("User must authorize first", user_id="ou_xxx")
    """

    pass


class TokenExpiredError(AuthError):
    """User access token has expired and cannot be used.

    Raised when the stored token has passed its expiration time
    and automatic refresh has failed.

    Example
    ----------
        >>> raise TokenExpiredError("Token expired at 2026-01-19", session_id="sess_123")
    """

    pass


class TokenRefreshFailedError(AuthError):
    """Failed to refresh user access token.

    Raised when automatic token refresh encounters an error,
    such as network failure or invalid refresh token.

    Example
    ----------
        >>> raise TokenRefreshFailedError("Refresh token invalid", session_id="sess_123")
    """

    pass


class AuthSessionNotFoundError(AuthError):
    """Authorization session not found in database.

    Raised when querying for a session that doesn't exist
    or has been deleted.

    Example
    ----------
        >>> raise AuthSessionNotFoundError("Session not found", session_id="sess_123")
    """

    pass


class AuthSessionExpiredError(AuthError):
    """Authorization session has expired before completion.

    Raised when a session has exceeded its 10-minute validity
    period without the user completing authorization.

    Example
    ----------
        >>> raise AuthSessionExpiredError("Session expired", session_id="sess_123")
    """

    pass


class AuthorizationRejectedError(AuthError):
    """User explicitly rejected the authorization request.

    Raised when the user clicks the "Reject" button on
    the authorization card.

    Example
    ----------
        >>> raise AuthorizationRejectedError("User rejected authorization", user_id="ou_xxx")
    """

    pass


class AuthorizationCodeExpiredError(AuthError):
    """Authorization code has expired before token exchange.

    Raised when the temporary authorization code received from
    the card callback has exceeded its validity period (typically 10 minutes).

    Example
    ----------
        >>> raise AuthorizationCodeExpiredError("Authorization code expired", session_id="sess_123")
    """

    pass
