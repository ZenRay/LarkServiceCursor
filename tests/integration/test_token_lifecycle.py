"""Integration tests for Token lifecycle.

Tests the complete lifecycle: acquire → use → refresh → expire → re-acquire.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Create test configuration with short refresh threshold."""
    config = Config(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="lark_service",
        postgres_user="lark",
        postgres_password="lark_password_123",
        rabbitmq_host="localhost",
        rabbitmq_port=5672,
        rabbitmq_user="lark",
        rabbitmq_password="rabbitmq_password_123",
        config_encryption_key=Fernet.generate_key(),
        config_db_path=tmp_path / "test_config.db",
        log_level="INFO",
        max_retries=3,
        retry_backoff_base=0.1,  # Faster retries for testing
        token_refresh_threshold=0.5,  # 50% threshold for easier testing
    )
    return config


@pytest.fixture
def app_manager(test_config: Config) -> ApplicationManager:
    """Create ApplicationManager for tests."""
    manager = ApplicationManager(
        test_config.config_db_path,
        test_config.config_encryption_key,
    )
    # Add test application
    manager.add_application(
        app_id="cli_lifecycletest1234",
        app_name="Lifecycle Test App",
        app_secret="test_secret_lifecycle123",
    )
    yield manager
    manager.close()


@pytest.fixture
def token_storage(test_config: Config) -> TokenStorageService:
    """Create TokenStorageService for tests."""
    service = TokenStorageService(test_config.get_postgres_url())
    yield service
    # Cleanup
    service.delete_token("cli_lifecycletest1234", "app_access_token")
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


class TestTokenLifecycle:
    """Integration tests for complete token lifecycle."""

    def test_complete_lifecycle(
        self,
        credential_pool: CredentialPool,
        token_storage: TokenStorageService,
    ) -> None:
        """Test complete token lifecycle from acquisition to expiry."""
        app_id = "cli_lifecycletest1234"
        token_type = "app_access_token"

        # Mock token fetch method
        call_count = [0]

        def mock_fetch_token(app_id_param: str):
            call_count[0] += 1
            token_value = f"generated_token_v{call_count[0]}"
            expires_at = datetime.now() + timedelta(seconds=10)
            return token_value, expires_at

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=mock_fetch_token,
        ):

            # Step 1: Acquire token (first time)
            token1 = credential_pool.get_token(app_id, token_type)
            assert token1 == "generated_token_v1"
            assert call_count[0] == 1

            # Verify token is stored
            stored = token_storage.get_token(app_id, token_type)
            assert stored is not None
            assert stored.token_value == "generated_token_v1"
            assert not stored.is_expired()

            # Step 2: Use cached token (no API call)
            token2 = credential_pool.get_token(app_id, token_type)
            assert token2 == "generated_token_v1"
            assert call_count[0] == 1  # No new API call

            # Step 3: Wait for token to cross refresh threshold (50% of 10s = 5s)
            time.sleep(6)

            # Step 4: Get token should trigger proactive refresh
            token3 = credential_pool.get_token(app_id, token_type)
            assert token3 == "generated_token_v2"
            assert call_count[0] == 2  # New API call

            # Verify new token is stored
            stored = token_storage.get_token(app_id, token_type)
            assert stored is not None
            assert stored.token_value == "generated_token_v2"

            # Step 5: Wait for token to expire completely
            time.sleep(11)

            # Step 6: Get token should trigger re-acquisition
            token4 = credential_pool.get_token(app_id, token_type)
            assert token4 == "generated_token_v3"
            assert call_count[0] == 3  # Another API call

    def test_concurrent_generated_token_access(
        self,
        credential_pool: CredentialPool,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that concurrent access doesn't cause duplicate API calls."""
        import threading

        app_id = "cli_lifecycletest1234"
        token_type = "app_access_token"
        tokens = []

        # Mock token fetch method
        def mock_fetch_token(app_id_param: str):
            token_value = "concurrent_generated_token"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=mock_fetch_token,
        ):

            def get_token_thread():
                token = credential_pool.get_token(app_id, token_type)
                tokens.append(token)

            # Start multiple threads
            threads = [threading.Thread(target=get_token_thread) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All threads should get the same token
            assert len(tokens) == 5
            assert all(t == "concurrent_generated_token" for t in tokens)

            # Should only make one API call (lock prevents duplicates)
            assert credential_pool._fetch_app_access_token.call_count == 1

    def test_token_refresh_on_near_expiry(
        self,
        credential_pool: CredentialPool,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that tokens are refreshed when approaching expiry."""
        app_id = "cli_lifecycletest1234"
        token_type = "app_access_token"

        # Manually store a token that's near expiry
        # With 50% threshold, a 10-second token should refresh at 5 seconds remaining
        near_expiry = datetime.now() + timedelta(seconds=4)
        token_storage.set_token(
            app_id=app_id,
            token_type=token_type,
            token_value="near_expiry_token",
            expires_at=near_expiry,
        )

        # Mock token fetch method
        def mock_fetch_token(app_id_param: str):
            token_value = "refreshed_token"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=mock_fetch_token,
        ):
            # Get token should trigger refresh
            token = credential_pool.get_token(app_id, token_type)
            assert token == "refreshed_token"
            assert credential_pool._fetch_app_access_token.call_count == 1

    def test_expired_token_re_acquisition(
        self,
        credential_pool: CredentialPool,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that expired tokens are re-acquired."""
        app_id = "cli_lifecycletest1234"
        token_type = "app_access_token"

        # Manually store an expired token
        expired_time = datetime.now() - timedelta(hours=1)
        token_storage.set_token(
            app_id=app_id,
            token_type=token_type,
            token_value="expired_token",
            expires_at=expired_time,
        )

        # Verify token is expired
        stored = token_storage.get_token(app_id, token_type)
        assert stored is not None
        assert stored.is_expired()

        # Mock token fetch method
        def mock_fetch_token(app_id_param: str):
            token_value = "generated_new_token"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=mock_fetch_token,
        ):
            # Get token should re-acquire
            token = credential_pool.get_token(app_id, token_type)
            assert token == "generated_new_token"
            assert credential_pool._fetch_app_access_token.call_count == 1

        # Verify new token is stored
        stored = token_storage.get_token(app_id, token_type)
        assert stored is not None
        assert stored.token_value == "generated_new_token"
        assert not stored.is_expired()

    def test_token_types_independence(
        self,
        credential_pool: CredentialPool,
        token_storage: TokenStorageService,
    ) -> None:
        """Test that different token types are managed independently."""
        app_id = "cli_lifecycletest1234"

        # Mock token fetch methods
        def mock_fetch_generated_app_token(app_id_param: str):
            token_value = "generated_app_token"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        def mock_fetch_generated_tenant_token(app_id_param: str):
            token_value = "generated_tenant_token"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=mock_fetch_generated_app_token,
        ), patch.object(
            credential_pool,
            "_fetch_tenant_access_token",
            side_effect=mock_fetch_generated_tenant_token,
        ):
            # Get both types of tokens
            generated_app_token = credential_pool.get_token(app_id, "app_access_token")
            generated_tenant_token = credential_pool.get_token(app_id, "tenant_access_token")

            assert generated_app_token == "generated_app_token"
            assert generated_tenant_token == "generated_tenant_token"

        # Verify both tokens are stored separately
        stored_app = token_storage.get_token(app_id, "app_access_token")
        stored_tenant = token_storage.get_token(app_id, "tenant_access_token")

        assert stored_app is not None
        assert stored_tenant is not None
        assert stored_app.token_value != stored_tenant.token_value

    def test_manual_refresh(
        self,
        credential_pool: CredentialPool,
        token_storage: TokenStorageService,
    ) -> None:
        """Test manual token refresh."""
        app_id = "cli_lifecycletest1234"
        token_type = "app_access_token"

        # Mock token fetch method
        call_count = [0]

        def mock_fetch_token(app_id_param: str):
            call_count[0] += 1
            token_value = f"manual_generated_token_v{call_count[0]}"
            expires_at = datetime.now() + timedelta(seconds=7200)
            return token_value, expires_at

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=mock_fetch_token,
        ):
            # Initial acquisition
            token1 = credential_pool.get_token(app_id, token_type)
            assert token1 == "manual_generated_token_v1"
            assert call_count[0] == 1

            # Manual refresh
            token2 = credential_pool.refresh_token(app_id, token_type)
            assert token2 == "manual_generated_token_v2"
            assert call_count[0] == 2

            # Verify new token is stored
            stored = token_storage.get_token(app_id, token_type)
            assert stored is not None
            assert stored.token_value == "manual_generated_token_v2"
