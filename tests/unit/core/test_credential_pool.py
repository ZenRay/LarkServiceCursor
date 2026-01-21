"""Unit tests for CredentialPool.

Tests token management logic with mocked dependencies.
Focus on: multi-app isolation, auto-refresh, concurrent safety, retry mechanism.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from cryptography.fernet import Fernet

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    AuthenticationError,
    TokenAcquisitionError,
)
from lark_service.core.models.application import Application
from lark_service.core.models.token_storage import TokenStorage


@pytest.fixture
def mock_config() -> Config:
    """Create mock configuration."""
    return Config(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
        rabbitmq_host="localhost",
        rabbitmq_port=5672,
        rabbitmq_user="test_user",
        rabbitmq_password="test_pass",
        config_encryption_key=Fernet.generate_key(),
        config_db_path="/tmp/test_config.db",
        log_level="INFO",
        max_retries=3,
        retry_backoff_base=1.0,
        token_refresh_threshold=300,  # 5 minutes
    )


@pytest.fixture
def mock_app_manager() -> Mock:
    """Create mock ApplicationManager."""
    manager = Mock()
    manager.get_application.return_value = None
    manager.get_decrypted_secret.return_value = "test_secret"
    manager.close.return_value = None
    return manager


@pytest.fixture
def mock_token_storage() -> Mock:
    """Create mock TokenStorageService."""
    storage = Mock()
    storage.get_token.return_value = None
    storage.set_token.return_value = None
    storage.delete_token.return_value = True
    storage.close.return_value = None
    return storage


@pytest.fixture
def credential_pool(
    mock_config: Config,
    mock_app_manager: Mock,
    mock_token_storage: Mock,
    tmp_path: Path,
) -> CredentialPool:
    """Create CredentialPool with mocked dependencies."""
    return CredentialPool(
        config=mock_config,
        app_manager=mock_app_manager,
        token_storage=mock_token_storage,
        lock_dir=tmp_path / "locks",
    )


class TestCredentialPoolInitialization:
    """Test CredentialPool initialization."""

    def test_init_with_valid_config(
        self,
        mock_config: Config,
        mock_app_manager: Mock,
        mock_token_storage: Mock,
        tmp_path: Path,
    ) -> None:
        """Test successful initialization."""
        pool = CredentialPool(
            config=mock_config,
            app_manager=mock_app_manager,
            token_storage=mock_token_storage,
            lock_dir=tmp_path / "locks",
        )

        assert pool.config == mock_config
        assert pool.app_manager == mock_app_manager
        assert pool.token_storage == mock_token_storage
        assert pool.lock_manager is not None
        assert pool.retry_strategy is not None
        assert pool.sdk_clients == {}

    def test_init_creates_lock_manager(
        self,
        credential_pool: CredentialPool,
    ) -> None:
        """Test lock manager is created with correct timeout."""
        assert credential_pool.lock_manager is not None
        assert credential_pool.lock_manager.default_timeout == 30.0


class TestGetSDKClient:
    """Test _get_sdk_client method (FR-011: Multi-app isolation)."""

    def test_get_sdk_client_creates_new_client(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test SDK client creation for new app_id."""
        # Mock application
        mock_app = Mock(spec=Application)
        mock_app.app_id = "cli_test1234567890ab"
        mock_app.is_active.return_value = True
        mock_app_manager.get_application.return_value = mock_app
        mock_app_manager.get_decrypted_secret.return_value = "test_secret_123"

        # Get SDK client
        client = credential_pool._get_sdk_client("cli_test1234567890ab")

        assert client is not None
        assert "cli_test1234567890ab" in credential_pool.sdk_clients
        mock_app_manager.get_application.assert_called_once_with("cli_test1234567890ab")
        mock_app_manager.get_decrypted_secret.assert_called_once_with("cli_test1234567890ab")

    def test_get_sdk_client_caches_client(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test SDK client is cached and reused (FR-011)."""
        # Mock application
        mock_app = Mock(spec=Application)
        mock_app.app_id = "cli_test4567890abcd12"
        mock_app.is_active.return_value = True
        mock_app_manager.get_application.return_value = mock_app
        mock_app_manager.get_decrypted_secret.return_value = "test_secret_456"

        # First call - should create client
        client1 = credential_pool._get_sdk_client("cli_test4567890abcd12")

        # Second call - should return cached client
        client2 = credential_pool._get_sdk_client("cli_test4567890abcd12")

        assert client1 is client2
        # get_application should only be called once
        assert mock_app_manager.get_application.call_count == 1

    def test_get_sdk_client_app_not_found(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error when application not found."""
        mock_app_manager.get_application.return_value = None

        with pytest.raises(AuthenticationError, match="Application not found"):
            credential_pool._get_sdk_client("cli_nonexistent123456")

    def test_get_sdk_client_app_inactive(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error when application is inactive."""
        mock_app = Mock(spec=Application)
        mock_app.app_id = "cli_inactive123456789"
        mock_app.is_active.return_value = False
        mock_app.status = "inactive"
        mock_app_manager.get_application.return_value = mock_app

        with pytest.raises(AuthenticationError, match="not active"):
            credential_pool._get_sdk_client("cli_inactive123456789")

    def test_get_sdk_client_multi_app_isolation(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test different apps get different SDK clients (FR-011)."""

        def get_app_side_effect(app_id: str) -> Application:
            mock_app = Mock(spec=Application)
            mock_app.app_id = app_id
            mock_app.is_active.return_value = True
            return mock_app

        mock_app_manager.get_application.side_effect = get_app_side_effect

        # Get clients for two different apps
        client1 = credential_pool._get_sdk_client("cli_app1test1234567890")
        client2 = credential_pool._get_sdk_client("cli_app2test1234567890")

        assert client1 is not client2
        assert len(credential_pool.sdk_clients) == 2
        assert "cli_app1test1234567890" in credential_pool.sdk_clients
        assert "cli_app2test1234567890" in credential_pool.sdk_clients


class TestFetchAppAccessToken:
    """Test _fetch_app_access_token method."""

    def test_fetch_app_access_token_success(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test successful token fetch using direct HTTP request."""
        # Mock application
        mock_app = Mock(spec=Application)
        mock_app.app_id = "cli_test7890abcdef12"
        mock_app.is_active.return_value = True
        mock_app_manager.get_application.return_value = mock_app
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"

        # Mock requests.post response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "app_access_token": "t-test_token_123",
            "expire": 7200,
        }

        with patch("lark_service.core.credential_pool.requests.post") as mock_post:
            mock_post.return_value = mock_response

            token_value, expires_at = credential_pool._fetch_app_access_token(
                "cli_test7890abcdef12"
            )

            assert token_value == "t-test_token_123"
            assert isinstance(expires_at, datetime)
            # Token should expire in ~7200 seconds
            time_diff = (expires_at - datetime.now()).total_seconds()
            assert 7190 < time_diff < 7210

            # Verify the request was made correctly
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["app_id"] == "cli_test7890abcdef12"
            assert call_kwargs["json"]["app_secret"] == "test_secret"

    def test_fetch_app_access_token_api_error(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error handling for API failure using direct HTTP request."""
        # Mock application
        mock_app = Mock(spec=Application)
        mock_app.is_active.return_value = True
        mock_app_manager.get_application.return_value = mock_app
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"

        # Mock requests.post error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 99991663,
            "msg": "app access token invalid",
        }

        with patch("lark_service.core.credential_pool.requests.post") as mock_post:
            mock_post.return_value = mock_response

            with pytest.raises(TokenAcquisitionError, match="Failed to get app_access_token"):
                credential_pool._fetch_app_access_token("cli_errortest1234567")

    def test_fetch_app_access_token_exception(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error handling for unexpected exceptions."""
        mock_app = Mock(spec=Application)
        mock_app.is_active.return_value = True
        mock_app_manager.get_application.return_value = mock_app
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"

        with patch("lark_service.core.credential_pool.requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            with pytest.raises(TokenAcquisitionError, match="Failed to fetch app_access_token"):
                credential_pool._fetch_app_access_token("cli_exceptiontest123")


class TestFetchTenantAccessToken:
    """Test _fetch_tenant_access_token method."""

    @patch("lark_service.core.credential_pool.requests.post")
    def test_fetch_tenant_access_token_success(
        self,
        mock_post: Mock,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test successful tenant token fetch."""
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"

        # Mock requests.post response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "t-tenant_token_456",
            "expire": 7200,
        }
        mock_post.return_value = mock_response

        token_value, expires_at = credential_pool._fetch_tenant_access_token("cli_tenanttest123456")

        assert token_value == "t-tenant_token_456"
        assert isinstance(expires_at, datetime)
        mock_post.assert_called_once()
        # Verify request payload
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["app_id"] == "cli_tenanttest123456"
        assert call_kwargs["json"]["app_secret"] == "test_secret"

    @patch("lark_service.core.credential_pool.requests.post")
    def test_fetch_tenant_access_token_api_error(
        self,
        mock_post: Mock,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error handling for API failure."""
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"

        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 99991663,
            "msg": "tenant access token invalid",
        }
        mock_post.return_value = mock_response

        with pytest.raises(TokenAcquisitionError, match="Failed to get tenant_access_token"):
            credential_pool._fetch_tenant_access_token("cli_error12345678901")

    @patch("lark_service.core.credential_pool.requests.post")
    def test_fetch_tenant_access_token_network_error(
        self,
        mock_post: Mock,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error handling for network errors (FR-016: Retry)."""
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"
        mock_post.side_effect = requests.RequestException("Connection timeout")

        with pytest.raises(TokenAcquisitionError, match="Network error"):
            credential_pool._fetch_tenant_access_token("cli_networkerror1234")

    @patch("lark_service.core.credential_pool.requests.post")
    def test_fetch_tenant_access_token_invalid_response(
        self,
        mock_post: Mock,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
    ) -> None:
        """Test error handling for invalid response format."""
        mock_app_manager.get_decrypted_secret.return_value = "test_secret"

        # Mock malformed response (missing required field)
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            # Missing "tenant_access_token" and "expire"
        }
        mock_post.return_value = mock_response

        with pytest.raises(TokenAcquisitionError, match="Invalid response format"):
            credential_pool._fetch_tenant_access_token("cli_invalidresponse1")


class TestGetToken:
    """Test get_token method (FR-006: Automatic token management, FR-007: Proactive refresh)."""

    def test_get_token_from_cache_valid(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test getting valid token from cache."""
        # Mock cached token (valid, not near expiry)
        mock_token = Mock(spec=TokenStorage)
        mock_token.token_value = "cached_token_123"
        mock_token.is_expired.return_value = False
        mock_token.should_refresh.return_value = False
        mock_token.get_remaining_seconds.return_value = 3600
        mock_token_storage.get_token.return_value = mock_token

        token = credential_pool.get_token("cli_cachedtest123456", "app_access_token")

        assert token == "cached_token_123"
        mock_token_storage.get_token.assert_called_once_with(
            "cli_cachedtest123456", "app_access_token"
        )
        # Should not fetch new token
        mock_token_storage.set_token.assert_not_called()

    def test_get_token_proactive_refresh(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
        mock_app_manager: Mock,
    ) -> None:
        """Test proactive token refresh (FR-007)."""
        # Mock cached token (valid but near expiry)
        mock_token = Mock(spec=TokenStorage)
        mock_token.token_value = "old_token"
        mock_token.is_expired.return_value = False
        mock_token.should_refresh.return_value = True  # Near expiry
        mock_token.get_remaining_seconds.return_value = 200  # Less than threshold
        mock_token_storage.get_token.return_value = mock_token

        # Mock token fetch
        with patch.object(
            credential_pool, "_refresh_token_internal", return_value="new_refreshed_token"
        ) as mock_refresh:
            token = credential_pool.get_token("cli_refreshtest12345", "app_access_token")

            assert token == "new_refreshed_token"
            mock_refresh.assert_called_once_with(
                "cli_refreshtest12345", "app_access_token", force=False
            )

    def test_get_token_expired_triggers_refresh(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test expired token triggers refresh."""
        # Mock expired token
        mock_token = Mock(spec=TokenStorage)
        mock_token.is_expired.return_value = True
        mock_token_storage.get_token.return_value = mock_token

        with patch.object(
            credential_pool, "_refresh_token_internal", return_value="fresh_token"
        ) as mock_refresh:
            token = credential_pool.get_token("cli_expiredtest12345", "app_access_token")

            assert token == "fresh_token"
            mock_refresh.assert_called_once()

    def test_get_token_no_cache_fetches_new(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test fetching new token when no cache exists."""
        # No cached token
        mock_token_storage.get_token.return_value = None

        with patch.object(
            credential_pool, "_refresh_token_internal", return_value="new_token"
        ) as mock_refresh:
            token = credential_pool.get_token("cli_newtest123456789", "app_access_token")

            assert token == "new_token"
            mock_refresh.assert_called_once_with(
                "cli_newtest123456789", "app_access_token", force=False
            )

    def test_get_token_force_refresh(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test force_refresh bypasses cache."""
        # Mock valid cached token
        mock_token = Mock(spec=TokenStorage)
        mock_token.token_value = "cached_token"
        mock_token.is_expired.return_value = False
        mock_token.should_refresh.return_value = False
        mock_token_storage.get_token.return_value = mock_token

        with patch.object(
            credential_pool, "_refresh_token_internal", return_value="forced_new_token"
        ) as mock_refresh:
            token = credential_pool.get_token(
                "cli_forcetest1234567", "app_access_token", force_refresh=True
            )

            assert token == "forced_new_token"
            # force_refresh=True should bypass cache check
            mock_refresh.assert_called_once_with(
                "cli_forcetest1234567", "app_access_token", force=True
            )

    def test_get_token_invalid_token_type(
        self,
        credential_pool: CredentialPool,
    ) -> None:
        """Test error for invalid token_type."""
        with pytest.raises(ValueError, match="Invalid token_type"):
            credential_pool.get_token("cli_test1234567890ab", "invalid_token_type")

    def test_get_token_validates_app_id(
        self,
        credential_pool: CredentialPool,
    ) -> None:
        """Test app_id validation."""
        from lark_service.core.exceptions import ValidationError

        with pytest.raises(ValidationError, match="app_id"):
            credential_pool.get_token("", "app_access_token")


class TestRefreshTokenInternal:
    """Test _refresh_token_internal method (FR-008: Concurrent-safe refresh)."""

    def test_refresh_token_internal_with_lock(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
        mock_app_manager: Mock,
    ) -> None:
        """Test token refresh with lock (FR-008: Concurrent safety)."""
        # Mock token fetch
        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            return_value=("new_token_value", datetime.now() + timedelta(hours=2)),
        ) as mock_fetch:
            token = credential_pool._refresh_token_internal(
                "cli_locktest12345678", "app_access_token", force=True
            )

            assert token == "new_token_value"
            mock_fetch.assert_called_once_with("cli_locktest12345678")
            mock_token_storage.set_token.assert_called_once()

    def test_refresh_token_internal_double_check_lock(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test double-check locking optimization (FR-008)."""
        # Mock: Another process already refreshed the token
        mock_token = Mock(spec=TokenStorage)
        mock_token.token_value = "already_refreshed_token"
        mock_token.is_expired.return_value = False
        mock_token.should_refresh.return_value = False
        mock_token_storage.get_token.return_value = mock_token

        with patch.object(credential_pool, "_fetch_app_access_token") as mock_fetch:
            token = credential_pool._refresh_token_internal(
                "cli_doublecheck12345", "app_access_token", force=False
            )

            assert token == "already_refreshed_token"
            # Should not fetch because another process already refreshed
            mock_fetch.assert_not_called()

    def test_refresh_token_internal_with_retry(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
        mock_app_manager: Mock,
    ) -> None:
        """Test token refresh with retry strategy (FR-016: Intelligent retry)."""
        # Mock: First call fails, second succeeds
        call_count = [0]

        def fetch_side_effect(app_id: str) -> tuple[str, datetime]:
            call_count[0] += 1
            if call_count[0] == 1:
                raise TokenAcquisitionError("Temporary failure")
            return ("retry_success_token", datetime.now() + timedelta(hours=2))

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            side_effect=fetch_side_effect,
        ):
            token = credential_pool._refresh_token_internal(
                "cli_retrytest1234567", "app_access_token", force=True
            )

            assert token == "retry_success_token"
            # Retry strategy should have been used
            assert call_count[0] >= 1

    def test_refresh_token_internal_tenant_token(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test tenant_access_token refresh."""
        with patch.object(
            credential_pool,
            "_fetch_tenant_access_token",
            return_value=("tenant_token_123", datetime.now() + timedelta(hours=2)),
        ) as mock_fetch:
            token = credential_pool._refresh_token_internal(
                "cli_tenant123456789a", "tenant_access_token", force=True
            )

            assert token == "tenant_token_123"
            mock_fetch.assert_called_once_with("cli_tenant123456789a")


class TestRefreshToken:
    """Test refresh_token method."""

    def test_refresh_token_calls_internal_with_force(
        self,
        credential_pool: CredentialPool,
    ) -> None:
        """Test refresh_token always forces refresh."""
        with patch.object(
            credential_pool,
            "_refresh_token_internal",
            return_value="force_refreshed",
        ) as mock_internal:
            token = credential_pool.refresh_token("cli_test1234567890ab", "app_access_token")

            assert token == "force_refreshed"
            mock_internal.assert_called_once_with(
                "cli_test1234567890ab", "app_access_token", force=True
            )


class TestInvalidateToken:
    """Test invalidate_token method."""

    def test_invalidate_token_success(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test successful token invalidation."""
        mock_token_storage.delete_token.return_value = True

        credential_pool.invalidate_token("cli_test1234567890ab", "app_access_token")

        mock_token_storage.delete_token.assert_called_once_with(
            "cli_test1234567890ab", "app_access_token"
        )

    def test_invalidate_token_not_found(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test invalidation when token doesn't exist."""
        mock_token_storage.delete_token.return_value = False

        # Should not raise error
        credential_pool.invalidate_token("cli_nonexistent123456", "app_access_token")

        mock_token_storage.delete_token.assert_called_once()


class TestClose:
    """Test close method."""

    def test_close_closes_all_resources(
        self,
        credential_pool: CredentialPool,
        mock_app_manager: Mock,
        mock_token_storage: Mock,
    ) -> None:
        """Test close method calls close on all resources."""
        credential_pool.close()

        mock_app_manager.close.assert_called_once()
        mock_token_storage.close.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_concurrent_token_requests_same_app(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test concurrent requests for same app use locking (FR-008)."""
        # This test verifies lock is acquired
        mock_token_storage.get_token.return_value = None

        with patch.object(
            credential_pool,
            "_fetch_app_access_token",
            return_value=("concurrent_token", datetime.now() + timedelta(hours=2)),
        ):
            # Simulate concurrent calls
            token1 = credential_pool.get_token("cli_concurrent123456", "app_access_token")
            token2 = credential_pool.get_token("cli_concurrent123456", "app_access_token")

            # Both should get the same token value
            assert token1 == "concurrent_token"
            assert token2 == "concurrent_token"

    def test_token_expires_during_request(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test token expiring between cache check and use."""
        # Mock token that's just about to expire
        mock_token = Mock(spec=TokenStorage)
        mock_token.token_value = "about_to_expire"
        mock_token.is_expired.return_value = False
        mock_token.should_refresh.return_value = True
        mock_token.get_remaining_seconds.return_value = 1
        mock_token_storage.get_token.return_value = mock_token

        with patch.object(
            credential_pool,
            "_refresh_token_internal",
            return_value="refreshed_in_time",
        ) as mock_refresh:
            token = credential_pool.get_token("cli_expirerace123456", "app_access_token")

            assert token == "refreshed_in_time"
            mock_refresh.assert_called_once()

    def test_multiple_apps_isolated_tokens(
        self,
        credential_pool: CredentialPool,
        mock_token_storage: Mock,
    ) -> None:
        """Test multiple apps maintain isolated tokens (FR-011)."""

        def get_token_side_effect(app_id: str, token_type: str) -> None:
            return None  # No cache for any app

        mock_token_storage.get_token.side_effect = get_token_side_effect

        with patch.object(credential_pool, "_refresh_token_internal") as mock_refresh:
            mock_refresh.side_effect = [
                "token_for_app1",
                "token_for_app2",
                "token_for_app3",
            ]

            token1 = credential_pool.get_token("cli_app1test1234567890", "app_access_token")
            token2 = credential_pool.get_token("cli_app2test1234567890", "app_access_token")
            token3 = credential_pool.get_token("cli_app3test1234567890", "app_access_token")

            assert token1 == "token_for_app1"
            assert token2 == "token_for_app2"
            assert token3 == "token_for_app3"
            assert mock_refresh.call_count == 3
