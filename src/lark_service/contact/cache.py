"""
Contact cache manager for user information.

This module provides caching functionality for user contact information
with PostgreSQL storage, 24-hour TTL, and app_id isolation.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from lark_service.contact.models import User
from lark_service.core.models.user_cache import Base, UserCache
from lark_service.utils.logger import get_logger

logger = get_logger()


class ContactCacheManager:
    """
    Manager for contact information caching.

    Provides methods to cache and retrieve user information from PostgreSQL
    with automatic expiration handling and app_id isolation.

    Attributes
    ----------
        engine : Engine
            SQLAlchemy database engine
        session_factory : sessionmaker
            Session factory for database operations

    Examples
    --------
        >>> manager = ContactCacheManager("postgresql://user:pass@localhost/db")
        >>> user = User(open_id="ou_xxx", name="John", email="john@example.com")
        >>> manager.cache_user("cli_test", user)
        >>> cached = manager.get_user_by_email("cli_test", "john@example.com")
        >>> print(cached.name)
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize ContactCacheManager.

        Parameters
        ----------
            database_url : str
                PostgreSQL database URL
        """
        # Add pool_pre_ping to handle stale connections
        # Add echo=False to reduce logging noise
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False,
        )
        self.session_factory = sessionmaker(bind=self.engine)

        # Create tables if not exist
        Base.metadata.create_all(self.engine)

    def __enter__(self) -> "ContactCacheManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Context manager exit - close all connections."""
        self.close()

    def close(self) -> None:
        """
        Close database connections and dispose of engine.

        Should be called when the cache manager is no longer needed
        to properly clean up database resources.

        Examples
        --------
            >>> manager = ContactCacheManager("sqlite:///:memory:")
            >>> # ... use manager ...
            >>> manager.close()
        """
        if hasattr(self, "engine"):
            self.engine.dispose()
            logger.debug("ContactCacheManager connections closed")

    def cache_user(self, app_id: str, user: User) -> UserCache:
        """
        Cache user information.

        If user already exists in cache, update the information and refresh TTL.

        Parameters
        ----------
            app_id : str
                Lark application ID
            user : User
                User information to cache

        Returns
        -------
            UserCache
                Cached user entry

        Examples
        --------
            >>> user = User(open_id="ou_xxx", name="John")
            >>> cached = manager.cache_user("cli_test", user)
        """
        with self.session_factory() as session:
            # Check if user already exists
            stmt = select(UserCache).where(
                UserCache.app_id == app_id, UserCache.open_id == user.open_id
            )
            existing = session.execute(stmt).scalar_one_or_none()

            now = datetime.now()
            expires_at = now + timedelta(hours=24)

            if existing:
                # Update existing entry
                existing.user_id = user.user_id
                existing.union_id = user.union_id
                existing.email = user.email
                existing.mobile = user.mobile
                existing.name = user.name
                existing.department_ids = (
                    ",".join(user.department_ids) if user.department_ids else None
                )
                existing.employee_no = user.employee_no
                existing.cached_at = now
                existing.expires_at = expires_at

                session.commit()
                session.refresh(existing)  # Refresh to load all attributes
                logger.info(f"Updated cache for user {user.open_id} in app {app_id}")

                # Make a detached copy with all attributes loaded
                session.expunge(existing)
                return existing
            else:
                # Create new entry
                cache_entry = UserCache(
                    app_id=app_id,
                    open_id=user.open_id,
                    user_id=user.user_id,
                    union_id=user.union_id,
                    email=user.email,
                    mobile=user.mobile,
                    name=user.name,
                    department_ids=",".join(user.department_ids) if user.department_ids else None,
                    employee_no=user.employee_no,
                    cached_at=now,
                    expires_at=expires_at,
                )
                session.add(cache_entry)
                session.commit()
                session.refresh(cache_entry)  # Refresh to load all attributes
                logger.info(f"Cached user {user.open_id} in app {app_id}")

                # Make a detached copy with all attributes loaded
                session.expunge(cache_entry)
                return cache_entry

    def get_user_by_open_id(self, app_id: str, open_id: str) -> User | None:
        """
        Get user from cache by open_id.

        Parameters
        ----------
            app_id : str
                Lark application ID
            open_id : str
                User's open_id

        Returns
        -------
            User | None
                User if found and not expired, None otherwise

        Examples
        --------
            >>> user = manager.get_user_by_open_id("cli_test", "ou_xxx")
        """
        with self.session_factory() as session:
            stmt = select(UserCache).where(UserCache.app_id == app_id, UserCache.open_id == open_id)
            cache_entry = session.execute(stmt).scalar_one_or_none()

            if cache_entry and not cache_entry.is_expired():
                logger.debug(f"Cache hit for open_id {open_id}")
                return self._to_user(cache_entry)

            if cache_entry:
                logger.debug(f"Cache expired for open_id {open_id}")
            else:
                logger.debug(f"Cache miss for open_id {open_id}")

            return None

    def get_user_by_email(self, app_id: str, email: str) -> User | None:
        """
        Get user from cache by email.

        Parameters
        ----------
            app_id : str
                Lark application ID
            email : str
                User's email address

        Returns
        -------
            User | None
                User if found and not expired, None otherwise

        Examples
        --------
            >>> user = manager.get_user_by_email("cli_test", "john@example.com")
        """
        with self.session_factory() as session:
            stmt = select(UserCache).where(UserCache.app_id == app_id, UserCache.email == email)
            cache_entry = session.execute(stmt).scalar_one_or_none()

            if cache_entry and not cache_entry.is_expired():
                logger.debug(f"Cache hit for email {email}")
                return self._to_user(cache_entry)

            if cache_entry:
                logger.debug(f"Cache expired for email {email}")
            else:
                logger.debug(f"Cache miss for email {email}")

            return None

    def get_user_by_mobile(self, app_id: str, mobile: str) -> User | None:
        """
        Get user from cache by mobile.

        Parameters
        ----------
            app_id : str
                Lark application ID
            mobile : str
                User's mobile number

        Returns
        -------
            User | None
                User if found and not expired, None otherwise

        Examples
        --------
            >>> user = manager.get_user_by_mobile("cli_test", "+86-13800138000")
        """
        with self.session_factory() as session:
            stmt = select(UserCache).where(UserCache.app_id == app_id, UserCache.mobile == mobile)
            cache_entry = session.execute(stmt).scalar_one_or_none()

            if cache_entry and not cache_entry.is_expired():
                logger.debug(f"Cache hit for mobile {mobile}")
                return self._to_user(cache_entry)

            if cache_entry:
                logger.debug(f"Cache expired for mobile {mobile}")
            else:
                logger.debug(f"Cache miss for mobile {mobile}")

            return None

    def get_user_by_user_id(self, app_id: str, user_id: str) -> User | None:
        """
        Get user from cache by user_id.

        Parameters
        ----------
            app_id : str
                Lark application ID
            user_id : str
                User's user_id

        Returns
        -------
            User | None
                User if found and not expired, None otherwise

        Examples
        --------
            >>> user = manager.get_user_by_user_id("cli_test", "4d7a3c6g")
        """
        with self.session_factory() as session:
            stmt = select(UserCache).where(UserCache.app_id == app_id, UserCache.user_id == user_id)
            cache_entry = session.execute(stmt).scalar_one_or_none()

            if cache_entry and not cache_entry.is_expired():
                logger.debug(f"Cache hit for user_id {user_id}")
                return self._to_user(cache_entry)

            if cache_entry:
                logger.debug(f"Cache expired for user_id {user_id}")
            else:
                logger.debug(f"Cache miss for user_id {user_id}")

            return None

    def invalidate_user(self, app_id: str, open_id: str) -> bool:
        """
        Invalidate (delete) user from cache.

        Parameters
        ----------
            app_id : str
                Lark application ID
            open_id : str
                User's open_id

        Returns
        -------
            bool
                True if user was found and deleted, False otherwise

        Examples
        --------
            >>> manager.invalidate_user("cli_test", "ou_xxx")
        """
        with self.session_factory() as session:
            stmt = select(UserCache).where(UserCache.app_id == app_id, UserCache.open_id == open_id)
            cache_entry = session.execute(stmt).scalar_one_or_none()

            if cache_entry:
                session.delete(cache_entry)
                session.commit()
                logger.info(f"Invalidated cache for user {open_id} in app {app_id}")
                return True

            return False

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns
        -------
            int
                Number of entries removed

        Examples
        --------
            >>> count = manager.cleanup_expired()
            >>> print(f"Removed {count} expired entries")
        """
        with self.session_factory() as session:
            now = datetime.now()
            stmt = select(UserCache).where(UserCache.expires_at <= now)
            expired_entries = session.execute(stmt).scalars().all()

            count = len(expired_entries)
            for entry in expired_entries:
                session.delete(entry)

            session.commit()
            logger.info(f"Cleaned up {count} expired cache entries")
            return count

    def get_cache_stats(self, app_id: str) -> dict[str, int]:
        """
        Get cache statistics for an app.

        Parameters
        ----------
            app_id : str
                Lark application ID

        Returns
        -------
            dict[str, int]
                Statistics with keys: total, active, expired

        Examples
        --------
            >>> stats = manager.get_cache_stats("cli_test")
            >>> print(f"Active: {stats['active']}, Expired: {stats['expired']}")
        """
        with self.session_factory() as session:
            now = datetime.now()

            # Total entries for this app
            total_stmt = select(UserCache).where(UserCache.app_id == app_id)
            total = len(session.execute(total_stmt).scalars().all())

            # Active (non-expired) entries
            active_stmt = select(UserCache).where(
                UserCache.app_id == app_id, UserCache.expires_at > now
            )
            active = len(session.execute(active_stmt).scalars().all())

            expired = total - active

            return {"total": total, "active": active, "expired": expired}

    def _to_user(self, cache_entry: UserCache) -> User | None:
        """
        Convert UserCache to User model.

        Parameters
        ----------
            cache_entry : UserCache
                Cache entry to convert

        Returns
        -------
            User | None
                User model, or None if required fields are missing
        """
        # Check required fields
        if not cache_entry.user_id or not cache_entry.union_id or not cache_entry.name:
            logger.warning(
                f"Cache entry missing required fields: user_id={cache_entry.user_id}, "
                f"union_id={cache_entry.union_id}, name={cache_entry.name}"
            )
            return None

        return User(
            open_id=cache_entry.open_id,
            user_id=cache_entry.user_id,
            union_id=cache_entry.union_id,
            name=cache_entry.name,
            avatar=None,
            email=cache_entry.email,
            mobile=cache_entry.mobile,
            department_ids=(
                cache_entry.department_ids.split(",") if cache_entry.department_ids else None
            ),
            employee_no=cache_entry.employee_no,
            job_title=None,
            status=None,
        )
