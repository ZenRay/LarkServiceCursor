"""Authentication session manager.

This module provides the AuthSessionManager class for managing user
authentication sessions, including creation, completion, token retrieval,
token refresh, and cleanup operations.
"""

import uuid
from datetime import UTC, datetime, timedelta

import requests
from sqlalchemy.orm import Session

from lark_service.auth.exceptions import (
    AuthenticationRequiredError,
    AuthSessionExpiredError,
    AuthSessionNotFoundError,
    TokenRefreshFailedError,
)
from lark_service.auth.types import UserInfo
from lark_service.core.models.auth_session import UserAuthSession
from lark_service.utils.logger import get_logger

logger = get_logger()


class AuthSessionManager:
    """Manager for user authentication sessions.

    Handles the lifecycle of authentication sessions including:
    - Creating new sessions with UUID generation
    - Completing sessions with token and user info storage
    - Retrieving active tokens for users
    - Cleaning up expired sessions

    Attributes
    ----------
        db: SQLAlchemy database session

    Example
    ----------
        >>> manager = AuthSessionManager(db_session)
        >>> session = manager.create_session(
        ...     app_id="cli_xxx",
        ...     user_id="ou_xxx",
        ...     auth_method="websocket_card"
        ... )
        >>> # User completes authorization...
        >>> manager.complete_session(
        ...     session_id=session.session_id,
        ...     user_access_token="u-token",
        ...     token_expires_at=datetime.now(UTC) + timedelta(days=7),
        ...     user_info=user_info
        ... )
    """

    def __init__(self, db: Session) -> None:
        """Initialize AuthSessionManager.

        Parameters
        ----------
            db: SQLAlchemy database session
        """
        self.db = db

    def create_session(
        self,
        app_id: str,
        user_id: str,
        auth_method: str = "websocket_card",
        session_expiry_minutes: int = 10,
    ) -> UserAuthSession:
        """Create new authentication session.

        Generates a new session with UUID identifier and sets expiration
        time to 10 minutes from now (configurable).

        Parameters
        ----------
            app_id: Feishu application ID
            user_id: Feishu user ID
            auth_method: Authentication method (default: websocket_card)
            session_expiry_minutes: Session expiry time in minutes (default: 10)

        Returns
        ----------
            UserAuthSession: Created session object

        Example
        ----------
            >>> session = manager.create_session(
            ...     app_id="cli_test123456789",
            ...     user_id="ou_test_user_123"
            ... )
            >>> print(session.state)
            'pending'
        """
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=session_expiry_minutes)

        session = UserAuthSession(
            session_id=session_id,
            app_id=app_id,
            user_id=user_id,
            state="pending",
            auth_method=auth_method,
            created_at=now.replace(tzinfo=None),  # SQLite doesn't support timezone-aware datetimes
            expires_at=expires_at.replace(tzinfo=None),
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def get_session(self, session_id: str) -> UserAuthSession | None:
        """Get session by session_id.

        Parameters
        ----------
            session_id: Session identifier

        Returns
        ----------
            UserAuthSession | None: Session object or None if not found

        Example
        ----------
            >>> session = manager.get_session("550e8400-e29b-41d4-a716-446655440000")
            >>> if session:
            ...     print(session.state)
        """
        return self.db.query(UserAuthSession).filter_by(session_id=session_id).first()

    def complete_session(
        self,
        session_id: str,
        user_access_token: str,
        token_expires_at: datetime,
        user_info: UserInfo,
    ) -> UserAuthSession:
        """Complete authentication session with token and user info.

        Updates session state to 'completed' and stores user access token
        and user information.

        Parameters
        ----------
            session_id: Session identifier
            user_access_token: User access token from Feishu
            token_expires_at: Token expiration timestamp
            user_info: User information from Feishu

        Returns
        ----------
            UserAuthSession: Updated session object

        Raises
        ----------
            AuthSessionNotFoundError: If session not found
            AuthSessionExpiredError: If session has expired

        Example
        ----------
            >>> user_info = UserInfo(
            ...     user_id="ou_xxx",
            ...     open_id="ou_xxx",
            ...     union_id="on_xxx",
            ...     name="Test User",
            ...     email="test@example.com"
            ... )
            >>> session = manager.complete_session(
            ...     session_id="sess_123",
            ...     user_access_token="u-token",
            ...     token_expires_at=datetime.now(UTC) + timedelta(days=7),
            ...     user_info=user_info
            ... )
        """
        session = self.get_session(session_id)

        if session is None:
            raise AuthSessionNotFoundError(
                f"Session not found: {session_id}",
                session_id=session_id,
            )

        # Check if session has expired
        now = datetime.now(UTC)
        if session.expires_at < now.replace(tzinfo=None):
            raise AuthSessionExpiredError(
                f"Session expired at {session.expires_at}",
                session_id=session_id,
            )

        # Update session with completion data
        session.state = "completed"
        session.user_access_token = user_access_token
        session.token_expires_at = token_expires_at.replace(tzinfo=None)
        session.open_id = user_info.open_id
        session.union_id = user_info.union_id
        session.user_name = user_info.user_name
        session.mobile = user_info.mobile
        session.email = user_info.email
        session.completed_at = now.replace(tzinfo=None)

        self.db.commit()
        self.db.refresh(session)

        return session

    def get_active_token(
        self,
        app_id: str,
        user_id: str,
        raise_if_missing: bool = True,
        auto_refresh: bool = False,
        app_secret: str | None = None,
    ) -> str | None:
        """Get active user access token for user.

        Retrieves the most recent non-expired token for the specified
        app_id and user_id combination.

        Parameters
        ----------
            app_id: Feishu application ID
            user_id: Feishu user ID
            raise_if_missing: If True, raise AuthenticationRequiredError when token not found (default: True)
            auto_refresh: If True, automatically refresh expiring tokens (default: False)
            app_secret: Application secret for token refresh (required if auto_refresh=True)

        Returns
        ----------
            str | None: Active token or None if not found (when raise_if_missing=False)

        Raises
        ----------
            AuthenticationRequiredError: If token not found or expired (when raise_if_missing=True)

        Example
        ----------
            >>> token = manager.get_active_token(
            ...     app_id="cli_test1234567890ab",
            ...     user_id="ou_test_user_123",
            ...     auto_refresh=True,
            ...     app_secret="secret"
            ... )
            >>> print("Token found:", token[:10] + "...")
        """
        now = datetime.now(UTC).replace(tzinfo=None)

        session = (
            self.db.query(UserAuthSession)
            .filter(
                UserAuthSession.app_id == app_id,
                UserAuthSession.user_id == user_id,
                UserAuthSession.state == "completed",
                UserAuthSession.token_expires_at > now,
            )
            .order_by(UserAuthSession.completed_at.desc())
            .first()
        )

        if session is None and raise_if_missing:
            raise AuthenticationRequiredError(
                f"No active token found for user {user_id} in app {app_id}. "
                "User needs to authorize the application.",
                user_id=user_id,
            )

        if session is None:
            return None

        # Check if token is expiring and auto-refresh if enabled
        if (
            auto_refresh
            and session.token_expires_at is not None
            and self._is_token_expiring(
                token_expires_at=session.token_expires_at,
                token_issued_at=session.created_at,
            )
        ):
            try:
                logger.info(
                    f"Token expiring for user {user_id}, attempting refresh",
                    extra={"app_id": app_id, "user_id": user_id},
                )
                return self.refresh_token(app_id=app_id, user_id=user_id, app_secret=app_secret)
            except TokenRefreshFailedError as e:
                logger.warning(
                    f"Token refresh failed for user {user_id}: {e}",
                    extra={"app_id": app_id, "user_id": user_id},
                )
                # Return existing token if refresh fails
                return session.user_access_token

        return session.user_access_token

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired pending sessions.

        Marks all pending sessions that have exceeded their expiration
        time as 'expired'.

        Returns
        ----------
            int: Number of sessions cleaned up

        Example
        ----------
            >>> count = manager.cleanup_expired_sessions()
            >>> print(f"Cleaned up {count} expired sessions")
        """
        now = datetime.now(UTC).replace(tzinfo=None)

        count = (
            self.db.query(UserAuthSession)
            .filter(
                UserAuthSession.state == "pending",
                UserAuthSession.expires_at < now,
            )
            .update({"state": "expired"})
        )

        self.db.commit()

        return count

    def _is_token_expiring(
        self,
        token_expires_at: datetime,
        token_issued_at: datetime | None = None,
        threshold: float = 0.1,
    ) -> bool:
        """Check if token is expiring soon.

        Determines if a token is within the expiry threshold (default 10%
        of its total lifetime remaining).

        Parameters
        ----------
            token_expires_at: Token expiration timestamp
            token_issued_at: Token issuance timestamp (optional, defaults to 7 days before expiry)
            threshold: Expiry threshold as fraction of total lifetime (default: 0.1 = 10%)

        Returns
        ----------
            bool: True if token is expiring soon, False otherwise

        Example
        ----------
            >>> now = datetime.now(UTC)
            >>> expires_at = now + timedelta(hours=1)
            >>> issued_at = now - timedelta(days=6, hours=23)
            >>> manager._is_token_expiring(expires_at, issued_at)
            True
        """
        now = datetime.now(UTC).replace(tzinfo=None)

        # Ensure all datetimes are naive (no timezone)
        if token_expires_at.tzinfo is not None:
            token_expires_at = token_expires_at.replace(tzinfo=None)

        if token_issued_at is None:
            token_issued_at = token_expires_at - timedelta(days=7)
        elif token_issued_at.tzinfo is not None:
            token_issued_at = token_issued_at.replace(tzinfo=None)

        # Calculate total lifetime and remaining time
        total_lifetime = (token_expires_at - token_issued_at).total_seconds()
        remaining_time = (token_expires_at - now).total_seconds()

        # Check if remaining time is less than threshold
        return remaining_time < (total_lifetime * threshold)

    def refresh_token(
        self,
        app_id: str,
        user_id: str,
        app_secret: str | None = None,
    ) -> str:
        """Refresh user access token.

        Calls Feishu API to refresh an expiring or expired token using
        the refresh token.

        Parameters
        ----------
            app_id: Feishu application ID
            user_id: Feishu user ID
            app_secret: Application secret for API authentication (optional)

        Returns
        ----------
            str: New access token

        Raises
        ----------
            AuthSessionNotFoundError: If session not found
            TokenRefreshFailedError: If refresh fails

        Example
        ----------
            >>> new_token = manager.refresh_token(
            ...     app_id="cli_test1234567890ab",
            ...     user_id="ou_test_user_123",
            ...     app_secret="secret"
            ... )
        """
        # Get session with refresh token
        session = (
            self.db.query(UserAuthSession)
            .filter(
                UserAuthSession.app_id == app_id,
                UserAuthSession.user_id == user_id,
                UserAuthSession.state == "completed",
            )
            .order_by(UserAuthSession.completed_at.desc())
            .first()
        )

        if session is None:
            raise AuthSessionNotFoundError(
                f"No session found for user {user_id} in app {app_id}",
                user_id=user_id,
            )

        refresh_token = getattr(session, "refresh_token", None)
        if refresh_token is None:
            raise TokenRefreshFailedError(
                "No refresh token available for session",
                session_id=session.session_id,
                user_id=user_id,
            )

        # Call Feishu token refresh API
        # Note: This is a placeholder - actual API endpoint may vary
        url = "https://open.feishu.cn/open-apis/authen/v1/refresh_access_token"
        headers = {"Content-Type": "application/json"}
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                raise TokenRefreshFailedError(
                    f"Token refresh failed: {result.get('msg', 'Unknown error')}",
                    session_id=session.session_id,
                    user_id=user_id,
                )

            # Update session with new token
            data = result.get("data", {})
            new_token: str = data.get("access_token", "")
            expires_in = data.get("expires_in", 7200)

            session.user_access_token = new_token
            session.token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
                seconds=expires_in
            )

            if "refresh_token" in data:
                session.refresh_token = data["refresh_token"]  # type: ignore[attr-defined]

            self.db.commit()
            self.db.refresh(session)

            logger.info(
                f"Successfully refreshed token for user {user_id}",
                extra={"app_id": app_id, "user_id": user_id},
            )

            return new_token

        except requests.RequestException as e:
            logger.error(f"Network error refreshing token: {e}")
            raise TokenRefreshFailedError(
                f"Failed to refresh token: {e}",
                session_id=session.session_id,
                user_id=user_id,
            ) from e

    def sync_user_info_batch(self, app_id: str) -> int:
        """Synchronize user information for all active sessions.

        Batch updates user information (name, email, mobile) for all
        users with active tokens in the specified app.

        Parameters
        ----------
            app_id: Feishu application ID

        Returns
        ----------
            int: Number of users updated

        Example
        ----------
            >>> count = manager.sync_user_info_batch(app_id="cli_test1234567890ab")
            >>> print(f"Updated {count} users")
        """
        now = datetime.now(UTC).replace(tzinfo=None)

        # Get all active sessions
        sessions = (
            self.db.query(UserAuthSession)
            .filter(
                UserAuthSession.app_id == app_id,
                UserAuthSession.state == "completed",
                UserAuthSession.token_expires_at > now,
            )
            .all()
        )

        updated_count = 0

        for session in sessions:
            try:
                # Call Feishu user info API
                url = f"https://open.feishu.cn/open-apis/contact/v3/users/{session.open_id}"
                headers = {
                    "Authorization": f"Bearer {session.user_access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.get(url, headers=headers, timeout=30)
                result = response.json()

                if result.get("code") == 0:
                    user_data = result.get("data", {}).get("user", {})

                    # Update user info
                    if "name" in user_data:
                        session.user_name = user_data["name"]
                    if "email" in user_data:
                        session.email = user_data["email"]
                    if "mobile" in user_data:
                        session.mobile = user_data["mobile"]

                    updated_count += 1

            except Exception as e:
                logger.warning(
                    f"Failed to sync user info for {session.user_id}: {e}",
                    extra={"app_id": app_id, "user_id": session.user_id},
                )
                continue

        self.db.commit()

        logger.info(
            f"Synced user info for {updated_count}/{len(sessions)} users",
            extra={"app_id": app_id, "updated": updated_count, "total": len(sessions)},
        )

        return updated_count
