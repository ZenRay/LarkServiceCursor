"""Unit tests for token refresh functionality.

Tests the automatic token refresh mechanism including expiry detection
and token renewal.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from lark_service.auth.exceptions import TokenRefreshFailedError
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.core.models.auth_session import UserAuthSession


class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def auth_manager(self, mock_db):
        """Create AuthSessionManager instance."""
        return AuthSessionManager(mock_db)

    def test_is_token_expiring_returns_true_when_less_than_threshold(self, auth_manager):
        """Test _is_token_expiring detects tokens nearing expiration.

        T065 [P] [US3] RED: Unit test for token expiry detection (<10% remaining)
        """
        # Arrange
        now = datetime.now(UTC)
        # Token expires in 1 hour, with 7-day total lifetime (10% = 16.8 hours)
        token_expires_at = now + timedelta(hours=1)
        token_issued_at = now - timedelta(days=7) + timedelta(hours=1)

        # Act
        is_expiring = auth_manager._is_token_expiring(
            token_expires_at=token_expires_at,
            token_issued_at=token_issued_at,
            threshold=0.1,
        )

        # Assert
        assert is_expiring is True

    def test_is_token_expiring_returns_false_when_above_threshold(self, auth_manager):
        """Test _is_token_expiring returns False for fresh tokens.

        T065 [P] [US3] RED: Unit test for token expiry detection (<10% remaining)
        """
        # Arrange
        now = datetime.now(UTC)
        # Token expires in 6 days, with 7-day total lifetime (>10%)
        token_expires_at = now + timedelta(days=6)
        token_issued_at = now - timedelta(days=1)

        # Act
        is_expiring = auth_manager._is_token_expiring(
            token_expires_at=token_expires_at,
            token_issued_at=token_issued_at,
            threshold=0.1,
        )

        # Assert
        assert is_expiring is False

    def test_refresh_token_success(self, auth_manager, mock_db):
        """Test refresh_token successfully refreshes an expiring token.

        T064 [P] [US3] RED: Unit test for refresh_token calling Feishu API
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        old_token = "u-old_token_abc123"
        new_token = "u-new_token_xyz789"
        refresh_token = "r-refresh_token_123"

        # Mock session with expiring token
        mock_session = Mock(spec=UserAuthSession)
        mock_session.user_access_token = old_token
        mock_session.refresh_token = refresh_token
        mock_session.token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            mock_session
        )

        # Mock Feishu API response
        with patch("lark_service.auth.session_manager.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "access_token": new_token,
                    "expires_in": 7200,
                    "refresh_token": "r-new_refresh_token",
                },
            }

            # Act
            result = auth_manager.refresh_token(app_id=app_id, user_id=user_id)

            # Assert
            assert result == new_token
            assert mock_session.user_access_token == new_token
            mock_post.assert_called_once()

    def test_refresh_token_failure_raises_error(self, auth_manager, mock_db):
        """Test refresh_token raises error when API call fails.

        T064 [P] [US3] RED: Unit test for refresh_token calling Feishu API
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        refresh_token = "r-refresh_token_123"

        # Mock session
        mock_session = Mock(spec=UserAuthSession)
        mock_session.refresh_token = refresh_token

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            mock_session
        )

        # Mock Feishu API error response
        with patch("lark_service.auth.session_manager.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "code": 99991400,
                "msg": "Invalid refresh token",
            }

            # Act & Assert
            with pytest.raises(TokenRefreshFailedError):
                auth_manager.refresh_token(app_id=app_id, user_id=user_id)

    def test_sync_user_info_batch_updates_multiple_users(self, auth_manager, mock_db):
        """Test sync_user_info_batch updates user information for multiple users.

        T066 [P] [US3] RED: Unit test for sync_user_info_batch async task
        """
        # Arrange
        app_id = "cli_test1234567890ab"

        # Mock multiple sessions
        mock_session1 = Mock(spec=UserAuthSession)
        mock_session1.user_id = "ou_user_001"
        mock_session1.open_id = "ou_user_001"
        mock_session1.user_access_token = "u-token1"

        mock_session2 = Mock(spec=UserAuthSession)
        mock_session2.user_id = "ou_user_002"
        mock_session2.open_id = "ou_user_002"
        mock_session2.user_access_token = "u-token2"

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_session1,
            mock_session2,
        ]

        # Mock Feishu user info API
        with patch("lark_service.auth.session_manager.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "user": {
                        "name": "Updated User",
                        "email": "updated@example.com",
                        "mobile": "+1234567890",
                    }
                },
            }

            # Act
            count = auth_manager.sync_user_info_batch(app_id=app_id)

            # Assert
            assert count == 2
            assert mock_get.call_count == 2
            mock_db.commit.assert_called()

    def test_get_active_token_with_auto_refresh(self, auth_manager, mock_db):
        """Test get_active_token automatically refreshes expiring tokens.

        T070 [US3] GREEN: Update AuthSessionManager.get_active_token() to auto-refresh
        """
        # Arrange
        app_id = "cli_test1234567890ab"
        user_id = "ou_test_user_123"
        old_token = "u-old_token_abc123"
        new_token = "u-new_token_xyz789"

        # Mock session with expiring token (but not yet expired)
        now = datetime.now(UTC)
        mock_session = Mock(spec=UserAuthSession)
        mock_session.user_access_token = old_token
        mock_session.refresh_token = "r-refresh_token"
        mock_session.token_expires_at = now + timedelta(hours=1)
        mock_session.created_at = now - timedelta(days=6, hours=23)  # Almost 7 days old

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
            mock_session
        )

        # Mock refresh API
        with patch("lark_service.auth.session_manager.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "access_token": new_token,
                    "expires_in": 7200,
                },
            }

            # Act
            token = auth_manager.get_active_token(app_id=app_id, user_id=user_id, auto_refresh=True)

            # Assert
            # Should return new token after refresh
            assert token == new_token
            mock_post.assert_called_once()
