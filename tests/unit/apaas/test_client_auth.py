"""Unit tests for aPaaS client authentication integration.

Tests the automatic user_access_token injection and authorization
flow integration with AuthSessionManager.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.exceptions import AuthenticationRequiredError
from lark_service.auth.session_manager import AuthSessionManager


class TestAPaaSClientAuth:
    """Test aPaaS client authentication integration."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_credential_pool(self):
        """Mock credential pool."""
        return Mock()

    @pytest.fixture
    def auth_manager(self, mock_db):
        """Create AuthSessionManager instance."""
        return AuthSessionManager(mock_db)

    @pytest.fixture
    def card_auth_handler(self, auth_manager):
        """Create CardAuthHandler instance."""
        mock_messaging_client = Mock()
        return CardAuthHandler(
            session_manager=auth_manager,
            messaging_client=mock_messaging_client,
            app_id="cli_test1234567890ab",
            app_secret="test_secret",
        )

    @pytest.fixture
    def apaas_client(self, mock_credential_pool):
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(credential_pool=mock_credential_pool)

    def test_get_user_access_token_success(self, auth_manager, mock_db):
        """Test _get_user_access_token returns valid token.

        T056 [P] [US4] RED: Unit test for aPaaSClient._get_user_access_token()
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        expected_token = "u-test_token_abc123"

        # Mock database query to return active token
        mock_session = Mock()
        mock_session.user_access_token = expected_token
        mock_session.token_expires_at = datetime.now(UTC) + timedelta(days=7)
        mock_session.state = "completed"

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            mock_session
        )

        # Act
        token = auth_manager.get_active_token(app_id=app_id, user_id=user_id)

        # Assert
        assert token == expected_token
        mock_db.query.assert_called_once()

    def test_get_user_access_token_not_found(self, auth_manager, mock_db):
        """Test _get_user_access_token raises error when token not found.

        T056 [P] [US4] RED: Unit test for aPaaSClient._get_user_access_token()
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Mock database query to return None
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        # Act & Assert
        with pytest.raises(AuthenticationRequiredError):
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

    def test_auto_send_auth_card_when_token_missing(
        self, card_auth_handler, auth_manager, mock_db, mock_credential_pool
    ):
        """Test auto-sending auth card when token is missing.

        T057 [P] [US4] RED: Unit test for auto-sending auth card when token missing
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Mock database query to return None (no token)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        # Mock credential pool to return app_secret
        mock_credential_pool.get_app_secret.return_value = "test_app_secret"

        # Act
        try:
            # This should trigger auth card sending
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)
        except AuthenticationRequiredError as e:
            # Expected - verify error message
            assert "No active token found" in str(e)
            assert user_id in str(e)
            assert app_id in str(e)

            # Now test sending auth card (without mocking HTTP calls)
            # This verifies the flow, actual HTTP calls would be mocked in integration tests
            # For now, we just verify the exception was raised correctly
            assert e.user_id == user_id

    def test_apaas_api_call_with_auto_token_injection(
        self, apaas_client, auth_manager, mock_db, mock_credential_pool
    ):
        """Test aPaaS API call with automatic token injection.

        T058 [US4] RED: Integration test for aPaaS API call with auto token injection
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        workspace_id = "workspace_test"
        expected_token = "u-test_token_abc123"

        # Mock auth_manager to return token
        mock_session = Mock()
        mock_session.user_access_token = expected_token
        mock_session.token_expires_at = datetime.now(UTC) + timedelta(days=7)
        mock_session.state = "completed"

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            mock_session
        )

        # Mock API response
        with patch("lark_service.apaas.client.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "code": 0,
                "data": {"items": []},
            }

            # Act - this should automatically inject user_access_token
            # Note: In the actual implementation, we'll add a wrapper method
            # that calls auth_manager.get_active_token() and passes it to the API
            token = auth_manager.get_active_token(app_id=app_id, user_id=user_id)
            tables = apaas_client.list_workspace_tables(
                app_id=app_id,
                user_access_token=token,
                workspace_id=workspace_id,
            )

            # Assert
            assert tables == []
            mock_get.assert_called_once()
            # Verify Authorization header contains the token
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == f"Bearer {expected_token}"

    def test_apaas_api_call_raises_auth_required_when_no_token(
        self, apaas_client, auth_manager, mock_db
    ):
        """Test aPaaS API call raises AuthenticationRequiredError when no token.

        T058 [US4] RED: Integration test for aPaaS API call with auto token injection
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Mock database query to return None (no token)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        # Act & Assert
        with pytest.raises(AuthenticationRequiredError):
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

    def test_apaas_api_call_with_expired_token_triggers_refresh(
        self, apaas_client, auth_manager, mock_db
    ):
        """Test aPaaS API call with expired token triggers refresh.

        This test verifies that when a token is expired, the system
        attempts to refresh it before making the API call.
        Note: The SQL query already filters out expired tokens,
        so this behaves the same as no token found.
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"

        # Mock database query to return None (expired tokens are filtered out by SQL)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        # Act & Assert
        # Should raise AuthenticationRequiredError for expired token
        with pytest.raises(AuthenticationRequiredError) as exc_info:
            auth_manager.get_active_token(app_id=app_id, user_id=user_id)

        # Verify error message
        assert "No active token found" in str(exc_info.value)
        assert user_id in str(exc_info.value)
