"""
Unit tests for ContactCacheManager.

Tests TTL expiration, lazy loading refresh, app_id isolation, and cache operations.
"""

from datetime import datetime, timedelta

import pytest

from lark_service.contact.cache import ContactCacheManager
from lark_service.contact.models import User


class TestContactCacheManager:
    """Test ContactCacheManager operations."""

    @pytest.fixture
    def cache_manager(self):
        """Create ContactCacheManager with in-memory SQLite."""
        manager = ContactCacheManager("sqlite:///:memory:")
        yield manager
        # Cleanup after test
        manager.close()

    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        return User(
            open_id="ou_1234567890abcdefghij",
            user_id="12345678",
            union_id="on_1234567890abcdefghij",
            email="test@example.com",
            mobile="13800138000",
            name="Test User",
            department_ids=["dept1", "dept2"],
            employee_no="EMP001",
        )

    def test_cache_user_new(self, cache_manager, sample_user):
        """Test caching a new user."""
        cached = cache_manager.cache_user("cli_test1234567890ab", sample_user)

        assert cached.app_id == "cli_test1234567890ab"
        assert cached.open_id == sample_user.open_id
        assert cached.email == sample_user.email
        assert cached.name == sample_user.name
        assert not cached.is_expired()

    def test_cache_user_update_existing(self, cache_manager, sample_user):
        """Test updating an existing cached user."""
        # Cache initial user
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        # Update user info
        updated_user = User(
            open_id=sample_user.open_id,
            user_id=sample_user.user_id,
            union_id=sample_user.union_id,
            name="Updated User",
            email="updated@example.com",
            mobile="13900139000",
        )

        # Cache updated user
        cached = cache_manager.cache_user("cli_test1234567890ab", updated_user)

        assert cached.email == "updated@example.com"
        assert cached.name == "Updated User"
        assert cached.mobile == "13900139000"

    def test_get_user_by_open_id_hit(self, cache_manager, sample_user):
        """Test cache hit when getting user by open_id."""
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", sample_user.open_id)

        assert user is not None
        assert user.open_id == sample_user.open_id
        assert user.email == sample_user.email

    def test_get_user_by_open_id_miss(self, cache_manager):
        """Test cache miss when getting user by open_id."""
        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", "ou_nonexistent")

        assert user is None

    def test_get_user_by_email_hit(self, cache_manager, sample_user):
        """Test cache hit when getting user by email."""
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        user = cache_manager.get_user_by_email("cli_test1234567890ab", sample_user.email)

        assert user is not None
        assert user.email == sample_user.email
        assert user.open_id == sample_user.open_id

    def test_get_user_by_email_miss(self, cache_manager):
        """Test cache miss when getting user by email."""
        user = cache_manager.get_user_by_email("cli_test1234567890ab", "nonexistent@example.com")

        assert user is None

    def test_get_user_by_mobile_hit(self, cache_manager, sample_user):
        """Test cache hit when getting user by mobile."""
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        user = cache_manager.get_user_by_mobile("cli_test1234567890ab", sample_user.mobile)

        assert user is not None
        assert user.mobile == sample_user.mobile
        assert user.open_id == sample_user.open_id

    def test_get_user_by_mobile_miss(self, cache_manager):
        """Test cache miss when getting user by mobile."""
        user = cache_manager.get_user_by_mobile("cli_test1234567890ab", "10000000000")

        assert user is None

    def test_get_user_by_user_id_hit(self, cache_manager, sample_user):
        """Test cache hit when getting user by user_id."""
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        user = cache_manager.get_user_by_user_id("cli_test1234567890ab", sample_user.user_id)

        assert user is not None
        assert user.user_id == sample_user.user_id
        assert user.open_id == sample_user.open_id

    def test_get_user_by_user_id_miss(self, cache_manager):
        """Test cache miss when getting user by user_id."""
        user = cache_manager.get_user_by_user_id("cli_test1234567890ab", "nonexistent_id")

        assert user is None

    def test_ttl_expiration(self, cache_manager, sample_user):
        """Test that expired cache entries are not returned."""
        # Cache user
        cached = cache_manager.cache_user("cli_test1234567890ab", sample_user)

        # Manually set expiration to past
        with cache_manager.session_factory() as session:
            cached.expires_at = datetime.now() - timedelta(hours=1)
            session.add(cached)
            session.commit()

        # Should return None for expired entry
        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", sample_user.open_id)
        assert user is None

    def test_app_id_isolation(self, cache_manager, sample_user):
        """Test that cache entries are isolated by app_id."""
        # Cache user for app1
        cache_manager.cache_user("cli_app1test123456789", sample_user)

        # Try to get user with different app_id
        user = cache_manager.get_user_by_open_id("cli_app2test123456789", sample_user.open_id)

        assert user is None

        # Get user with correct app_id
        user = cache_manager.get_user_by_open_id("cli_app1test123456789", sample_user.open_id)

        assert user is not None

    def test_invalidate_user_success(self, cache_manager, sample_user):
        """Test invalidating a cached user."""
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        # Verify user is cached
        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", sample_user.open_id)
        assert user is not None

        # Invalidate user
        result = cache_manager.invalidate_user("cli_test1234567890ab", sample_user.open_id)
        assert result is True

        # Verify user is no longer cached
        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", sample_user.open_id)
        assert user is None

    def test_invalidate_user_not_found(self, cache_manager):
        """Test invalidating a non-existent user."""
        result = cache_manager.invalidate_user("cli_test1234567890ab", "ou_nonexistent")
        assert result is False

    def test_cleanup_expired(self, cache_manager, sample_user):
        """Test cleaning up expired cache entries."""
        # Cache multiple users
        user1 = sample_user
        user2 = User(
            open_id="ou_2234567890abcdefghij",
            user_id="22345678",
            union_id="on_2234567890abcdefghij",
            name="Test User 2",
            email="test2@example.com",
        )

        cache_manager.cache_user("cli_test1234567890ab", user1)
        cache_manager.cache_user("cli_test1234567890ab", user2)

        # Manually expire one user
        with cache_manager.session_factory() as session:
            from sqlalchemy import select

            from lark_service.core.models.user_cache import UserCache

            stmt = select(UserCache).where(UserCache.open_id == user1.open_id)
            cached = session.execute(stmt).scalar_one()
            cached.expires_at = datetime.now() - timedelta(hours=1)
            session.commit()

        # Cleanup expired entries
        count = cache_manager.cleanup_expired()

        assert count == 1

        # Verify expired user is gone
        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", user1.open_id)
        assert user is None

        # Verify non-expired user still exists
        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", user2.open_id)
        assert user is not None

    def test_get_cache_stats(self, cache_manager, sample_user):
        """Test getting cache statistics."""
        # Cache multiple users
        user1 = sample_user
        user2 = User(
            open_id="ou_2234567890abcdefghij",
            user_id="22345678",
            union_id="on_2234567890abcdefghij",
            name="Test User 2",
            email="test2@example.com",
        )
        user3 = User(
            open_id="ou_3234567890abcdefghij",
            user_id="32345678",
            union_id="on_3234567890abcdefghij",
            name="Test User 3",
            email="test3@example.com",
        )

        cache_manager.cache_user("cli_test1234567890ab", user1)
        cache_manager.cache_user("cli_test1234567890ab", user2)
        cache_manager.cache_user("cli_test1234567890ab", user3)

        # Manually expire one user
        with cache_manager.session_factory() as session:
            from sqlalchemy import select

            from lark_service.core.models.user_cache import UserCache

            stmt = select(UserCache).where(UserCache.open_id == user1.open_id)
            cached = session.execute(stmt).scalar_one()
            cached.expires_at = datetime.now() - timedelta(hours=1)
            session.commit()

        # Get stats
        stats = cache_manager.get_cache_stats("cli_test1234567890ab")

        assert stats["total"] == 3
        assert stats["active"] == 2
        assert stats["expired"] == 1

    def test_get_cache_stats_empty(self, cache_manager):
        """Test getting cache statistics for empty cache."""
        stats = cache_manager.get_cache_stats("cli_test1234567890ab")

        assert stats["total"] == 0
        assert stats["active"] == 0
        assert stats["expired"] == 0

    def test_cache_user_with_minimal_info(self, cache_manager):
        """Test caching user with minimal information."""
        user = User(
            open_id="ou_4234567890abcdefghij",
            user_id="42345678",
            union_id="on_4234567890abcdefghij",
            name="Minimal User",
        )

        cached = cache_manager.cache_user("cli_test1234567890ab", user)

        assert cached.open_id == "ou_4234567890abcdefghij"
        assert cached.user_id == "42345678"
        assert cached.email is None
        assert cached.mobile is None
        assert cached.name == "Minimal User"

    def test_cache_refresh_ttl_on_update(self, cache_manager, sample_user):
        """Test that TTL is refreshed when updating cached user."""
        # Cache user
        cached1 = cache_manager.cache_user("cli_test1234567890ab", sample_user)
        original_expires_at = cached1.expires_at

        # Wait a bit (simulate time passing)
        import time

        time.sleep(0.1)

        # Update user (should refresh TTL)
        cached2 = cache_manager.cache_user("cli_test1234567890ab", sample_user)

        # TTL should be refreshed (expires_at should be later)
        assert cached2.expires_at > original_expires_at

    def test_department_ids_serialization(self, cache_manager, sample_user):
        """Test that department_ids are properly serialized."""
        cache_manager.cache_user("cli_test1234567890ab", sample_user)

        user = cache_manager.get_user_by_open_id("cli_test1234567890ab", sample_user.open_id)

        assert user is not None
        assert user.department_ids == ["dept1", "dept2"]

    def test_department_ids_none(self, cache_manager):
        """Test caching user with no department_ids."""
        user = User(
            open_id="ou_5234567890abcdefghij",
            user_id="52345678",
            union_id="on_5234567890abcdefghij",
            name="No Dept User",
            department_ids=None,
        )

        cache_manager.cache_user("cli_test1234567890ab", user)

        cached_user = cache_manager.get_user_by_open_id("cli_test1234567890ab", user.open_id)

        assert cached_user is not None
        assert cached_user.department_ids is None

    def test_context_manager(self):
        """Test ContactCacheManager as context manager."""
        user = User(
            open_id="ou_6234567890abcdefghij",
            user_id="62345678",
            union_id="on_6234567890abcdefghij",
            name="Context User",
        )

        # Use as context manager
        with ContactCacheManager("sqlite:///:memory:") as manager:
            manager.cache_user("cli_test1234567890ab", user)
            cached = manager.get_user_by_open_id("cli_test1234567890ab", user.open_id)
            assert cached is not None
            assert cached.name == "Context User"

        # After context exit, connections should be closed

    def test_explicit_close(self):
        """Test explicit close method."""
        manager = ContactCacheManager("sqlite:///:memory:")

        user = User(
            open_id="ou_7234567890abcdefghij",
            user_id="72345678",
            union_id="on_7234567890abcdefghij",
            name="Close User",
        )

        manager.cache_user("cli_test1234567890ab", user)
        cached = manager.get_user_by_open_id("cli_test1234567890ab", user.open_id)
        assert cached is not None

        # Explicitly close
        manager.close()

        # Multiple close calls should be safe
        manager.close()
