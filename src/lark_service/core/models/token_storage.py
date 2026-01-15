"""Token storage model for PostgreSQL.

This module defines the TokenStorage model for persisting access tokens
with encryption and expiration management.
"""

from datetime import datetime

from sqlalchemy import Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for PostgreSQL database models."""

    pass


class TokenStorage(Base):
    """Persistent token storage with encryption.

    Stores access tokens for multiple applications with automatic expiration
    tracking. Each (app_id, token_type) combination is unique.

    Attributes
    ----------
        id: Auto-increment primary key
        app_id: Lark application ID
        token_type: Type of token (app_access_token/tenant_access_token/user_access_token)
        token_value: Encrypted token value (using pg_crypto)
        expires_at: Token expiration timestamp
        created_at: Record creation timestamp
        updated_at: Record last update timestamp

    Example
    ----------
        >>> token = TokenStorage(
        ...     app_id="cli_a1b2c3d4e5f6g7h8",
        ...     token_type="app_access_token",
        ...     token_value="encrypted_token_value",
        ...     expires_at=datetime.now() + timedelta(hours=2)
        ... )
        >>> token.is_expired()
        False
        >>> token.should_refresh(threshold=0.1)
        False
    """

    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    app_id: Mapped[str] = mapped_column(String(64))
    token_type: Mapped[str] = mapped_column(String(32))
    token_value: Mapped[str] = mapped_column(Text)  # Encrypted
    expires_at: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("app_id", "token_type", name="uq_app_token_type"),
        Index("idx_tokens_expires", "expires_at"),
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if token has expired.

        Parameters
        ----------
            now: Current timestamp (defaults to datetime.now())

        Returns
        ----------
            True if token is expired, False otherwise
        """
        if now is None:
            now = datetime.now()
        return self.expires_at <= now

    def should_refresh(self, threshold: float = 0.1, now: datetime | None = None) -> bool:
        """Check if token should be refreshed based on remaining lifetime.

        Parameters
        ----------
            threshold: Refresh threshold as fraction of total lifetime (default 0.1 = 10%)
            now: Current timestamp (defaults to datetime.now())

        Returns
        ----------
            True if token should be refreshed, False otherwise

        Example
        ----------
            >>> # Token created at 10:00, expires at 12:00 (2 hour lifetime)
            >>> # At 11:48 (12 minutes remaining = 10% of lifetime)
            >>> token.should_refresh(threshold=0.1)
            True
        """
        if now is None:
            now = datetime.now()

        if self.is_expired(now):
            return True

        # Calculate total lifetime and remaining time
        total_lifetime = (self.expires_at - self.created_at).total_seconds()
        remaining_time = (self.expires_at - now).total_seconds()

        # Refresh if remaining time is less than threshold percentage
        return remaining_time < (total_lifetime * threshold)

    def get_remaining_seconds(self, now: datetime | None = None) -> float:
        """Get remaining seconds until expiration.

        Parameters
        ----------
            now: Current timestamp (defaults to datetime.now())

        Returns
        ----------
            Remaining seconds (negative if expired)
        """
        if now is None:
            now = datetime.now()
        return (self.expires_at - now).total_seconds()

    def __repr__(self) -> str:
        """Return string representation of TokenStorage."""
        return (
            f"<TokenStorage(id={self.id}, "
            f"app_id='{self.app_id}', "
            f"token_type='{self.token_type}', "
            f"expires_at='{self.expires_at}')>"
        )
