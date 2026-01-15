"""User cache model for PostgreSQL.

This module defines the UserCache model for caching user information
from Lark Contact API with 24-hour TTL and app_id isolation.
"""

from datetime import datetime, timedelta

from sqlalchemy import Index, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for PostgreSQL database models."""

    pass


class UserCache(Base):
    """User information cache with TTL and app isolation.

    Caches user IDs and contact information from Lark API to reduce
    API calls. Each user is cached per app_id with 24-hour expiration.

    Attributes
    ----------
        id: Auto-increment primary key
        app_id: Lark application ID (for isolation)
        open_id: User's OpenID (unique per app)
        user_id: User's UserID (unique across organization)
        union_id: User's UnionID (unique across all apps)
        email: User's email address
        mobile: User's mobile number
        name: User's display name
        department_ids: JSON array of department IDs
        employee_no: Employee number
        cached_at: Cache creation timestamp
        expires_at: Cache expiration timestamp (24h after cached_at)

    Example
    ----------
        >>> user = UserCache(
        ...     app_id="cli_a1b2c3d4e5f6g7h8",
        ...     open_id="ou_xxx",
        ...     user_id="7g9h3c1d",
        ...     union_id="on_xxx",
        ...     email="user@example.com"
        ... )
        >>> user.is_expired()
        False
    """

    __tablename__ = "user_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    app_id: Mapped[str] = mapped_column(String(64))
    open_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str | None] = mapped_column(String(64), default=None)
    union_id: Mapped[str | None] = mapped_column(String(64), default=None)
    email: Mapped[str | None] = mapped_column(String(128), default=None)
    mobile: Mapped[str | None] = mapped_column(String(32), default=None)
    name: Mapped[str | None] = mapped_column(String(128), default=None)
    department_ids: Mapped[str | None] = mapped_column(String(512), default=None)
    employee_no: Mapped[str | None] = mapped_column(String(64), default=None)
    cached_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        UniqueConstraint("app_id", "open_id", name="uq_app_open_id"),
        Index("idx_user_cache_expires", "expires_at"),
        Index("idx_user_cache_user_id", "user_id"),
        Index("idx_user_cache_union_id", "union_id"),
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if cache entry has expired.

        Parameters
        ----------
            now: Current timestamp (defaults to datetime.now())

        Returns
        ----------
            True if cache is expired, False otherwise
        """
        if now is None:
            now = datetime.now()
        return self.expires_at <= now

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

    def refresh_expiration(self) -> None:
        """Refresh the expiration time to 24 hours from now."""
        now = datetime.now()
        self.cached_at = now
        self.expires_at = now + timedelta(hours=24)

    def __repr__(self) -> str:
        """Return string representation of UserCache."""
        return (
            f"<UserCache(id={self.id}, "
            f"app_id='{self.app_id}', "
            f"open_id='{self.open_id}', "
            f"user_id='{self.user_id}', "
            f"expires_at='{self.expires_at}')>"
        )
