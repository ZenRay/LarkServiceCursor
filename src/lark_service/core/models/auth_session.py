"""User authentication session model for PostgreSQL.

This module defines the UserAuthSession model for managing OAuth2
authentication sessions with 10-minute timeout.
"""

from datetime import UTC, datetime

from sqlalchemy import Index, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for PostgreSQL database models."""

    pass


class UserAuthSession(Base):
    """User authentication session tracking.

    Manages user authentication sessions for obtaining user_access_token.
    Sessions expire after 10 minutes of inactivity.
    Supports WebSocket-based authorization with user information storage.

    Attributes
    ----------
        id: Auto-increment primary key
        session_id: Unique session identifier (UUID)
        app_id: Lark application ID
        user_id: Feishu user ID (enterprise unique)
        state: OAuth2 state parameter or session state (pending/completed/expired)
        auth_method: Authentication method (websocket_card/oauth/http_callback)
        redirect_uri: OAuth2 redirect URI (optional)
        open_id: User's OpenID (set after successful auth)
        union_id: User's UnionID (cross-app unique, optional)
        user_name: User's display name (optional)
        mobile: User's mobile number (encrypted, optional)
        email: User's email address (optional)
        user_access_token: User access token (encrypted, set after successful auth)
        token_expires_at: Token expiration timestamp
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp (10 min from creation)
        completed_at: Session completion timestamp

    Example
    ----------
        >>> session = UserAuthSession(
        ...     session_id="550e8400-e29b-41d4-a716-446655440000",
        ...     app_id="cli_a1b2c3d4e5f6g7h8",
        ...     user_id="ou_test_user_123",
        ...     state="pending",
        ...     auth_method="websocket_card"
        ... )
        >>> session.is_expired()
        False
        >>> session.is_completed()
        False
    """

    __tablename__ = "user_auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True)
    app_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str | None] = mapped_column(String(64), default=None)
    state: Mapped[str] = mapped_column(String(128))
    auth_method: Mapped[str] = mapped_column(String(32))
    redirect_uri: Mapped[str | None] = mapped_column(String(512), default=None)
    open_id: Mapped[str | None] = mapped_column(String(64), default=None)
    union_id: Mapped[str | None] = mapped_column(String(64), default=None)
    user_name: Mapped[str | None] = mapped_column(String(128), default=None)
    mobile: Mapped[str | None] = mapped_column(String(32), default=None)
    email: Mapped[str | None] = mapped_column(String(128), default=None)
    user_access_token: Mapped[str | None] = mapped_column(String(512), default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index("idx_auth_session_state", "state"),
        Index("idx_auth_session_expires", "expires_at"),
        Index("idx_auth_session_user", "app_id", "user_id"),
        Index("idx_auth_session_token_expires", "token_expires_at"),
        Index("idx_auth_session_created", "created_at"),
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if session has expired.

        Parameters
        ----------
            now: Current timestamp (defaults to datetime.now(UTC))

        Returns
        ----------
            True if session is expired, False otherwise
        """
        if now is None:
            now = datetime.now(UTC)
        return self.expires_at <= now

    def is_completed(self) -> bool:
        """Check if authentication session is completed.

        Returns
        ----------
            True if session has user_access_token, False otherwise
        """
        return self.user_access_token is not None and self.completed_at is not None

    def complete(self, open_id: str, user_access_token: str, token_expires_at: datetime) -> None:
        """Mark session as completed with authentication results.

        Parameters
        ----------
            open_id: User's OpenID
            user_access_token: User access token
            token_expires_at: Token expiration timestamp
        """
        self.open_id = open_id
        self.user_access_token = user_access_token
        self.token_expires_at = token_expires_at
        self.completed_at = datetime.now(UTC)

    def get_remaining_seconds(self, now: datetime | None = None) -> float:
        """Get remaining seconds until session expiration.

        Parameters
        ----------
            now: Current timestamp (defaults to datetime.now(UTC))

        Returns
        ----------
            Remaining seconds (negative if expired)
        """
        if now is None:
            now = datetime.now(UTC)
        return (self.expires_at - now).total_seconds()

    def __repr__(self) -> str:
        """Return string representation of UserAuthSession."""
        return (
            f"<UserAuthSession(id={self.id}, "
            f"session_id='{self.session_id}', "
            f"app_id='{self.app_id}', "
            f"auth_method='{self.auth_method}', "
            f"completed={self.is_completed()})>"
        )
