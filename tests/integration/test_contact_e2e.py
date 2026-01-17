"""
Integration tests for Contact module.

Tests user queries, caching, and department queries with real Feishu API.

Prerequisites:
- .env.test configured with TEST_APP_ID, TEST_APP_SECRET, TEST_USER_EMAIL
- PostgreSQL running (for cache)
- Valid Feishu app with contact:user.email:readonly scope
"""

import os
from datetime import timedelta
from typing import Any

import pytest
from dotenv import load_dotenv

from lark_service.contact.cache import ContactCacheManager
from lark_service.contact.client import ContactClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import NotFoundError

# Load test environment variables
load_dotenv(".env.test")


@pytest.fixture(scope="module")
def test_config() -> Any:
    """Load test configuration from .env.test."""
    config = {
        "app_id": os.getenv("TEST_APP_ID"),
        "app_secret": os.getenv("TEST_APP_SECRET"),
        "user_email": os.getenv("TEST_USER_EMAIL"),
        "user_mobile": os.getenv("TEST_USER_MOBILE"),
        "db_url": (
            f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
            f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        ),
    }

    # Validate required config
    missing = [k for k, v in config.items() if not v and k != "user_mobile"]
    if missing:
        pytest.skip(f"Missing required config: {', '.join(missing)}")

    return config


@pytest.fixture(scope="module")
def credential_pool(test_config: Any, tmp_path_factory: Any) -> Any:
    """Create credential pool for tests."""
    from cryptography.fernet import Fernet

    from lark_service.core.config import Config
    from lark_service.core.storage.postgres_storage import TokenStorageService
    from lark_service.core.storage.sqlite_storage import ApplicationManager

    # Create temp directory for config DB
    tmp_dir = tmp_path_factory.mktemp("integration_test")
    config_db_path = tmp_dir / "test_config.db"

    # Generate encryption key
    encryption_key = Fernet.generate_key()

    # Create config
    config = Config(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "lark_service"),
        postgres_user=os.getenv("POSTGRES_USER", "lark"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "lark_password_123"),
        rabbitmq_host=os.getenv("RABBITMQ_HOST", "localhost"),
        rabbitmq_port=int(os.getenv("RABBITMQ_PORT", "5672")),
        rabbitmq_user=os.getenv("RABBITMQ_USER", "lark"),
        rabbitmq_password=os.getenv("RABBITMQ_PASSWORD", "rabbitmq_password_123"),
        config_encryption_key=encryption_key,
        config_db_path=config_db_path,
        log_level="INFO",
        max_retries=3,
        retry_backoff_base=1.0,
        token_refresh_threshold=0.1,
    )

    # Create application manager and add test app
    app_manager = ApplicationManager(config_db_path, encryption_key)
    app_manager.add_application(
        app_id=test_config["app_id"],
        app_name="Integration Test App",
        app_secret=test_config["app_secret"],
    )

    # Create token storage
    token_storage = TokenStorageService(
        postgres_url=test_config["db_url"],
    )

    # Create credential pool
    pool = CredentialPool(
        config=config,
        app_manager=app_manager,
        token_storage=token_storage,
    )

    yield pool

    # Cleanup
    app_manager.close()
    if config_db_path.exists():
        config_db_path.unlink()


@pytest.fixture(scope="module")
def cache_manager(test_config: Any) -> Any:
    """Create cache manager for tests."""
    manager = ContactCacheManager(database_url=test_config["db_url"])

    # Clear test data before tests
    with manager.session_factory() as session:
        from lark_service.core.models.user_cache import UserCache

        session.query(UserCache).filter(UserCache.app_id == test_config["app_id"]).delete()
        session.commit()

    yield manager

    # Cleanup after tests
    with manager.session_factory() as session:
        session.query(UserCache).filter(UserCache.app_id == test_config["app_id"]).delete()
        session.commit()


@pytest.fixture
def client_without_cache(credential_pool: Any) -> Any:
    """Create ContactClient without cache."""
    return ContactClient(credential_pool, enable_cache=False)


@pytest.fixture
def client_with_cache(credential_pool: Any, cache_manager: Any) -> Any:
    """Create ContactClient with cache enabled."""
    return ContactClient(
        credential_pool,
        cache_manager=cache_manager,
        enable_cache=True,
        cache_ttl=timedelta(hours=24),
    )


class TestContactWithoutCache:
    """Test Contact client without cache (direct API calls)."""

    def test_get_user_by_email_success(
        self: Any, client_without_cache: Any, test_config: Any
    ) -> None:
        """Test get user by email returns valid user."""
        if not test_config["user_email"]:
            pytest.skip("TEST_USER_EMAIL not configured")

        user = client_without_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )

        # Verify user data
        assert user is not None
        assert user.open_id
        assert user.user_id
        assert user.union_id
        assert user.name
        assert user.email == test_config["user_email"]

        print(f"✅ Found user: {user.name} ({user.open_id})")

    def test_get_user_by_email_not_found(
        self: Any, client_without_cache: Any, test_config: Any
    ) -> None:
        """Test get user by email raises NotFoundError for non-existent user."""
        with pytest.raises(NotFoundError, match="User not found"):
            client_without_cache.get_user_by_email(
                app_id=test_config["app_id"],
                email="nonexistent_user_12345@example.com",
            )

    @pytest.mark.skipif(
        not os.getenv("TEST_USER_MOBILE"),
        reason="TEST_USER_MOBILE not configured",
    )
    def test_get_user_by_mobile_success(
        self: Any, client_without_cache: Any, test_config: Any
    ) -> None:
        """Test get user by mobile returns valid user."""
        user = client_without_cache.get_user_by_mobile(
            app_id=test_config["app_id"],
            mobile=test_config["user_mobile"],
        )

        # Verify user data
        assert user is not None
        assert user.open_id
        assert user.mobile == test_config["user_mobile"]

        print(f"✅ Found user by mobile: {user.name} ({user.mobile})")


class TestContactWithCache:
    """Test Contact client with cache enabled."""

    def test_cache_miss_then_hit(
        self: Any, client_with_cache: Any, cache_manager: Any, test_config: Any
    ) -> None:
        """Test cache miss on first call, then cache hit on second call."""
        if not test_config["user_email"]:
            pytest.skip("TEST_USER_EMAIL not configured")

        # First get user to have something to invalidate
        # (We need open_id for invalidation)
        temp_user = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )

        # Clear cache to ensure miss
        cache_manager.invalidate_user(
            test_config["app_id"],
            temp_user.open_id,
        )

        # First call - cache miss, API call
        user1 = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )
        assert user1 is not None
        print(f"✅ First call (cache miss): {user1.name}")

        # Verify user is now in cache
        cached_user = cache_manager.get_user_by_email(
            test_config["app_id"],
            test_config["user_email"],
        )
        assert cached_user is not None
        assert cached_user.union_id == user1.union_id

        # Second call - cache hit, no API call
        user2 = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )
        assert user2 is not None
        assert user2.union_id == user1.union_id
        print(f"✅ Second call (cache hit): {user2.name}")

        # Verify cache statistics
        stats = cache_manager.get_cache_stats(test_config["app_id"])
        assert stats["total"] >= 1
        assert stats["active"] >= 1
        print(f"✅ Cache stats: total={stats['total']}, active={stats['active']}")

    def test_cache_by_different_identifiers(
        self: Any, client_with_cache: Any, cache_manager: Any, test_config: Any
    ) -> None:
        """Test cache works with different identifiers (email, mobile, user_id)."""
        if not test_config["user_email"]:
            pytest.skip("TEST_USER_EMAIL not configured")

        # Clear cache by querying first to get open_id
        temp_user = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )
        cache_manager.invalidate_user(test_config["app_id"], temp_user.open_id)

        # Query by email - cache miss
        user_by_email = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )
        print(f"✅ Queried by email: {user_by_email.name}")

        # Query by user_id - should hit cache (same union_id)
        user_by_id = client_with_cache.get_user_by_user_id(
            app_id=test_config["app_id"],
            user_id=user_by_email.user_id,
        )
        assert user_by_id.union_id == user_by_email.union_id
        print(f"✅ Queried by user_id (cache hit): {user_by_id.name}")

        # If mobile is available, query by mobile
        if test_config["user_mobile"] and user_by_email.mobile:
            user_by_mobile = client_with_cache.get_user_by_mobile(
                app_id=test_config["app_id"],
                mobile=user_by_email.mobile,
            )
            assert user_by_mobile.union_id == user_by_email.union_id
            print(f"✅ Queried by mobile (cache hit): {user_by_mobile.name}")

    def test_cache_invalidation(
        self: Any, client_with_cache: Any, cache_manager: Any, test_config: Any
    ) -> None:
        """Test cache invalidation works correctly."""
        if not test_config["user_email"]:
            pytest.skip("TEST_USER_EMAIL not configured")

        # Populate cache
        user = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )
        print(f"✅ User cached: {user.name}")

        # Verify in cache
        cached = cache_manager.get_user_by_email(
            test_config["app_id"],
            test_config["user_email"],
        )
        assert cached is not None

        # Invalidate cache (use open_id, not union_id)
        success = cache_manager.invalidate_user(
            test_config["app_id"],
            user.open_id,
        )
        assert success
        print("✅ Cache invalidated successfully")

        # Verify cache is empty
        cached_after = cache_manager.get_user_by_email(
            test_config["app_id"],
            test_config["user_email"],
        )
        assert cached_after is None
        print("✅ Cache successfully invalidated")

    def test_cache_app_isolation(self: Any, cache_manager: Any, test_config: Any) -> None:
        """Test cache is isolated by app_id."""
        from lark_service.contact.models import User

        # Create test users for different apps (use valid ID formats)
        user1 = User(
            open_id="ou_1234567890abcdefghij",
            user_id="12345678",
            union_id="on_1234567890abcdefghij",
            name="Test User 1",
            email="test1@example.com",
        )

        user2 = User(
            open_id="ou_abcdefghij1234567890",  # Different open_id
            user_id="12345678",  # Same user_id
            union_id="on_1234567890abcdefghij",  # Same union_id
            name="Test User 1",
            email="test1@example.com",
        )

        # Cache for app1
        cache_manager.cache_user("app1_test", user1)

        # Cache for app2 (same user, different app)
        cache_manager.cache_user("app2_test", user2)

        # Verify app1 gets correct open_id
        cached1 = cache_manager.get_user_by_email("app1_test", "test1@example.com")
        assert cached1 is not None
        assert cached1.open_id == "ou_1234567890abcdefghij"

        # Verify app2 gets correct open_id
        cached2 = cache_manager.get_user_by_email("app2_test", "test1@example.com")
        assert cached2 is not None
        assert cached2.open_id == "ou_abcdefghij1234567890"

        print("✅ Cache app_id isolation verified")

        # Cleanup
        cache_manager.invalidate_user("app1_test", user1.open_id)
        cache_manager.invalidate_user("app2_test", user2.open_id)


class TestContactBatchOperations:
    """Test batch operations with cache."""

    @pytest.mark.skipif(
        not os.getenv("TEST_USER_EMAIL"),
        reason="TEST_USER_EMAIL not configured",
    )
    def test_batch_get_users_with_cache(
        self: Any, client_with_cache: Any, cache_manager: Any, test_config: Any
    ) -> None:
        """Test batch get users with cache optimization."""
        from lark_service.contact.models import BatchUserQuery

        # Clear cache (get user first to have open_id)
        temp_user = client_with_cache.get_user_by_email(
            app_id=test_config["app_id"],
            email=test_config["user_email"],
        )
        cache_manager.invalidate_user(test_config["app_id"], temp_user.open_id)

        # Create batch queries
        queries = [
            BatchUserQuery(emails=[test_config["user_email"]]),
            BatchUserQuery(emails=["nonexistent@example.com"]),
        ]

        # First call - cache miss
        response1 = client_with_cache.batch_get_users(
            app_id=test_config["app_id"],
            queries=queries,
        )
        assert response1.total >= 1
        print(f"✅ First batch call: {response1.total} users found")

        # Second call - cache hit for existing user
        response2 = client_with_cache.batch_get_users(
            app_id=test_config["app_id"],
            queries=queries,
        )
        assert response2.total >= 1
        assert response2.total == response1.total
        print(f"✅ Second batch call (with cache): {response2.total} users found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
