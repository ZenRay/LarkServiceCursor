"""Authentication session manager.

This module provides the AuthSessionManager class for managing user
authentication sessions, including creation, completion, token retrieval,
and cleanup operations.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from lark_service.auth.exceptions import (
    AuthSessionExpiredError,
    AuthSessionNotFoundError,
)
from lark_service.auth.types import UserInfo
from lark_service.core.models.auth_session import UserAuthSession


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

    def get_active_token(self, app_id: str, user_id: str) -> str | None:
        """Get active user access token for user.

        Retrieves the most recent non-expired token for the specified
        app_id and user_id combination.

        Parameters
        ----------
            app_id: Feishu application ID
            user_id: Feishu user ID

        Returns
        ----------
            str | None: Active token or None if not found or expired

        Example
        ----------
            >>> token = manager.get_active_token(
            ...     app_id="cli_test123456789",
            ...     user_id="ou_test_user_123"
            ... )
            >>> if token:
            ...     print("Token found:", token[:10] + "...")
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

        return session.user_access_token if session else None

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
