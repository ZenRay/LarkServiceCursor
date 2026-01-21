"""Integration tests for CredentialPool.

Tests lazy loading, token refresh, database persistence, and multi-app isolation.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import AuthenticationError
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager


@contextmanager
def mock_token_fetch(credential_pool, token_value="mock_token", expires_in=7200):
    """Helper to mock token fetch methods."""

    def mock_fetch_app(app_id_param: str):
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        return token_value, expires_at

    def mock_fetch_tenant(app_id_param: str):
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        return token_value, expires_at

    with (
        patch.object(
            credential_pool, "_fetch_app_access_token", side_effect=mock_fetch_app
        ) as mock_app,
        patch.object(
            credential_pool, "_fetch_tenant_access_token", side_effect=mock_fetch_tenant
        ) as mock_tenant,
    ):
        yield mock_app, mock_tenant


@pytest.fixture
def encryption_key() -> bytes:
    """Generate encryption key for tests."""
    return Fernet.generate_key()


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Create test configuration."""
    config = Config(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="lark_service",
        postgres_user="lark_user",
        postgres_password="lark_password_123",
        rabbitmq_host="localhost",
        rabbitmq_port=5672,
        rabbitmq_user="lark",
        rabbitmq_password="rabbitmq_password_123",
        config_encryption_key=Fernet.generate_key(),
        config_db_path=tmp_path / "test_config.db",
        log_level="INFO",
        max_retries=3,
        retry_backoff_base=1.0,
        token_refresh_threshold=0.1,
    )
    return config


@pytest.fixture
def app_manager(test_config: Config, encryption_key: bytes) -> ApplicationManager:
    """Create ApplicationManager for tests."""
    manager = ApplicationManager(test_config.config_db_path, encryption_key)
    yield manager
    manager.close()


@pytest.fixture
def token_storage(test_config: Config) -> TokenStorageService:
    """Create TokenStorageService for tests."""
    service = TokenStorageService(test_config.get_postgres_url())
    yield service
    service.close()


@pytest.fixture
def credential_pool(
    test_config: Config,
    app_manager: ApplicationManager,
    token_storage: TokenStorageService,
    tmp_path: Path,
) -> CredentialPool:
    """Create CredentialPool for tests."""
    # Clear all tokens before each test
    from sqlalchemy import text

    with token_storage.engine.connect() as conn:
        conn.execute(text("DELETE FROM tokens"))
        conn.commit()

    pool = CredentialPool(
        config=test_config,
        app_manager=app_manager,
        token_storage=token_storage,
        lock_dir=tmp_path / "locks",
    )
    yield pool
    pool.close()


class TestCredentialPoolIntegration:
    """Integration tests for CredentialPool."""

    def test_lazy_loading(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        encryption_key: bytes,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that tokens are lazily loaded on first access."""
        # Add test application
        app_manager.add_application(
            app_id="cli_lazytest12345678",
            app_name="Lazy Test App",
            app_secret="test_secret_1234",
        )

        # Clear any existing tokens
        token_storage.delete_token("cli_lazytest12345678", "app_access_token")

        # Mock token fetch to avoid real API calls
        with mock_token_fetch(credential_pool, "mock_token_value") as (mock_app, _):
            # First call should fetch from API (lazy loading)
            token1 = credential_pool.get_token("cli_lazytest12345678", "app_access_token")
            assert token1 == "mock_token_value"
            assert mock_app.call_count == 1

            # Second call should use cached token (no API call)
            token2 = credential_pool.get_token("cli_lazytest12345678", "app_access_token")
            assert token2 == "mock_token_value"
            assert mock_app.call_count == 1  # Still 1, no new call

    def test_token_refresh_when_expired(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that expired tokens are automatically refreshed."""
        # Add test application
        app_manager.add_application(
            app_id="cli_refreshtest123456",
            app_name="Refresh Test App",
            app_secret="test_secret_4567",
        )

        # Store an expired token
        expired_time = datetime.now() - timedelta(hours=1)
        token_storage.set_token(
            app_id="cli_refreshtest123456",
            token_type="app_access_token",
            token_value="expired_token",
            expires_at=expired_time,
        )

        # Mock token fetch
        with mock_token_fetch(credential_pool, "new_fresh_token") as (mock_app, _):
            # Get token should trigger refresh
            token = credential_pool.get_token("cli_refreshtest123456", "app_access_token")
            assert token == "new_fresh_token"
            assert mock_app.call_count == 1

    def test_token_refresh_threshold(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
        test_config: Config,
    ) -> None:
        """Test that expired tokens trigger refresh."""
        # Add test application
        app_manager.add_application(
            app_id="cli_thresholdtest1234",
            app_name="Threshold Test App",
            app_secret="test_secret_7890",
        )

        # Store an expired token
        expired_time = datetime.now() - timedelta(seconds=1)
        token_storage.set_token(
            app_id="cli_thresholdtest1234",
            token_type="app_access_token",
            token_value="expired_token",
            expires_at=expired_time,
        )

        # Mock token fetch
        with mock_token_fetch(credential_pool, "refreshed_token") as (mock_app, _):
            # Get token should trigger refresh for expired token
            token = credential_pool.get_token("cli_thresholdtest1234", "app_access_token")
            assert token == "refreshed_token"
            assert mock_app.call_count == 1

    def test_database_persistence(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that tokens are persisted to database."""
        # Add test application
        app_manager.add_application(
            app_id="cli_persisttest123456",
            app_name="Persist Test App",
            app_secret="test_secret_abcd",
        )

        # Mock token fetch
        with mock_token_fetch(credential_pool, "persisted_token") as (mock_app, _):
            # Get token
            token = credential_pool.get_token("cli_persisttest123456", "app_access_token")
            assert token == "persisted_token"

        # Verify token is in database
        stored_token = token_storage.get_token("cli_persisttest123456", "app_access_token")
        assert stored_token is not None
        assert stored_token.token_value == "persisted_token"
        assert not stored_token.is_expired()

    def test_multi_app_isolation(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that different apps have isolated tokens."""
        # Add two test applications
        app_manager.add_application(
            app_id="cli_app1test123456789",
            app_name="App 1",
            app_secret="secret_app1_test1",
        )
        app_manager.add_application(
            app_id="cli_app2test123456789",
            app_name="App 2",
            app_secret="secret_app2_test2",
        )

        # Mock token fetch with different tokens for different apps
        call_count = [0]

        def mock_fetch_app(app_id_param: str):
            call_count[0] += 1
            token_value = "token_for_app1" if call_count[0] == 1 else "token_for_app2"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        with patch.object(credential_pool, "_fetch_app_access_token", side_effect=mock_fetch_app):
            # Get tokens for both apps
            token1 = credential_pool.get_token("cli_app1test123456789", "app_access_token")
            token2 = credential_pool.get_token("cli_app2test123456789", "app_access_token")

            # Tokens should be different
            assert token1 == "token_for_app1"
            assert token2 == "token_for_app2"

        # Verify both tokens are stored separately
        stored_token1 = token_storage.get_token("cli_app1test123456789", "app_access_token")
        stored_token2 = token_storage.get_token("cli_app2test123456789", "app_access_token")

        assert stored_token1 is not None
        assert stored_token2 is not None
        assert stored_token1.token_value != stored_token2.token_value

    def test_force_refresh(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
    ) -> None:
        """Test force refresh bypasses cache."""
        # Add test application
        app_manager.add_application(
            app_id="cli_forcetest12345678",
            app_name="Force Test App",
            app_secret="test_secret_defg",
        )

        # First get a token
        with mock_token_fetch(credential_pool, "initial_token") as (mock_app1, _):
            token1 = credential_pool.get_token("cli_forcetest12345678", "app_access_token")
            assert token1 == "initial_token"
            assert mock_app1.call_count == 1

        # Force refresh should fetch a new token even though the old one is still valid
        with mock_token_fetch(credential_pool, "force_refreshed_token") as (mock_app2, _):
            token2 = credential_pool.get_token(
                "cli_forcetest12345678",
                "app_access_token",
                force_refresh=True,
            )
            assert token2 == "force_refreshed_token"
            assert mock_app2.call_count == 1

    def test_invalid_app_id(self, credential_pool: CredentialPool) -> None:
        """Test error handling for non-existent app."""
        with pytest.raises(AuthenticationError, match="Application not found"):
            credential_pool.get_token("cli_nonexistent123456", "app_access_token")

    def test_inactive_app(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
    ) -> None:
        """Test error handling for inactive app."""
        # Add inactive application
        app_manager.add_application(
            app_id="cli_inactivetest12345",
            app_name="Inactive App",
            app_secret="test_secret_ghij",
        )
        app_manager.update_application("cli_inactivetest12345", status="inactive")

        with pytest.raises(AuthenticationError, match="not active"):
            credential_pool.get_token("cli_inactivetest12345", "app_access_token")

    def test_token_invalidation(
        self,
        credential_pool: CredentialPool,
        app_manager: ApplicationManager,
        token_storage: TokenStorageService,
    ) -> None:
        """Test manual token invalidation."""
        # Add test application
        app_manager.add_application(
            app_id="cli_invalidatetest123",
            app_name="Invalidate Test App",
            app_secret="test_secret_jklm",
        )

        # Store a token
        valid_expiry = datetime.now() + timedelta(hours=1)
        token_storage.set_token(
            app_id="cli_invalidatetest123",
            token_type="app_access_token",
            token_value="to_be_invalidated",
            expires_at=valid_expiry,
        )

        # Verify token exists
        token = token_storage.get_token("cli_invalidatetest123", "app_access_token")
        assert token is not None

        # Invalidate token
        credential_pool.invalidate_token("cli_invalidatetest123", "app_access_token")

        # Verify token is deleted
        token = token_storage.get_token("cli_invalidatetest123", "app_access_token")
        assert token is None
