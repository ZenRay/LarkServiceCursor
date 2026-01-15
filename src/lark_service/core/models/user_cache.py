"""User cache model for PostgreSQL.

This module defines the UserCache model for caching user information
from Lark Contact API with 24-hour TTL and app_id isolation.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(String(64), nullable=False)
    open_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=True)
    union_id = Column(String(64), nullable=True)
    email = Column(String(128), nullable=True)
    mobile = Column(String(32), nullable=True)
    name = Column(String(128), nullable=True)
    department_ids = Column(String(512), nullable=True)  # JSON array as string
    employee_no = Column(String(64), nullable=True)
    cached_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("app_id", "open_id", name="uq_app_open_id"),
        Index("idx_user_cache_expires", "expires_at"),
        Index("idx_user_cache_user_id", "user_id"),
        Index("idx_user_cache_union_id", "union_id"),
    )

    def __init__(self, **kwargs: object) -> None:
        """Initialize UserCache with automatic expires_at calculation.

        If expires_at is not provided, it will be set to 24 hours from now.
        """
        super().__init__(**kwargs)
        if self.expires_at is None:
            if self.cached_at is not None:
                self.expires_at = self.cached_at + timedelta(hours=24)
            else:
                now = datetime.now()
                self.cached_at = now
                self.expires_at = now + timedelta(hours=24)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
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

    def get_remaining_seconds(self, now: Optional[datetime] = None) -> float:
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
