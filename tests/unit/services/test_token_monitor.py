"""
Unit tests for the token expiry monitor.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from lark_service.services.token_monitor import TokenExpiryMonitor


class TestTokenExpiryMonitor:
    """Test cases for TokenExpiryMonitor."""

    @pytest.fixture
    def mock_messaging_client(self):
        """Create a mock messaging client."""
        return Mock()

    @pytest.fixture
    def monitor(self, mock_messaging_client):
        """Create a TokenExpiryMonitor instance."""
        return TokenExpiryMonitor(
            messaging_client=mock_messaging_client,
            warning_days=7,
            critical_days=3,
        )

    def test_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor is not None
        assert monitor.warning_days == 7
        assert monitor.critical_days == 3

    def test_no_notification_for_valid_token(self, monitor, mock_messaging_client):
        """Test that no notification is sent for tokens with > 7 days."""
        expires_at = datetime.utcnow() + timedelta(days=30)

        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

        # No message should be sent
        mock_messaging_client.send_text_message.assert_not_called()

    def test_warning_notification(self, monitor, mock_messaging_client):
        """Test warning notification for tokens expiring in 5 days."""
        expires_at = datetime.utcnow() + timedelta(days=5)

        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

        # Warning message should be sent
        mock_messaging_client.send_text_message.assert_called_once()
        call_args = mock_messaging_client.send_text_message.call_args
        assert call_args[1]["user_id"] == "user123"
        assert "⚠️" in call_args[1]["content"]
        # Days might be 4 or 5 depending on microseconds
        assert "days" in call_args[1]["content"]

    def test_critical_warning_notification(self, monitor, mock_messaging_client):
        """Test critical warning for tokens expiring in 2 days."""
        expires_at = datetime.utcnow() + timedelta(days=2)

        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

        # Critical message should be sent
        mock_messaging_client.send_text_message.assert_called_once()
        call_args = mock_messaging_client.send_text_message.call_args
        assert "🚨" in call_args[1]["content"]
        assert "URGENT" in call_args[1]["content"]

    def test_expired_notification(self, monitor, mock_messaging_client):
        """Test notification for expired tokens."""
        expires_at = datetime.utcnow() - timedelta(days=1)

        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

        # Expired message should be sent
        mock_messaging_client.send_text_message.assert_called_once()
        call_args = mock_messaging_client.send_text_message.call_args
        assert "❌" in call_args[1]["content"]
        assert "EXPIRED" in call_args[1]["content"]

    def test_no_duplicate_notifications(self, monitor, mock_messaging_client):
        """Test that duplicate notifications are not sent within 24 hours."""
        expires_at = datetime.utcnow() + timedelta(days=5)

        # First check
        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

        # Second check immediately after
        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

        # Only one notification should be sent
        assert mock_messaging_client.send_text_message.call_count == 1

    def test_get_expiry_status_valid(self, monitor):
        """Test getting status for a valid token."""
        expires_at = datetime.utcnow() + timedelta(days=30)

        status = monitor.get_expiry_status(expires_at)

        assert status["status"] == "valid"
        assert status["severity"] == "ok"
        # Days might be 29 or 30 depending on microseconds
        assert status["days_to_expiry"] >= 29
        assert status["days_to_expiry"] <= 30

    def test_get_expiry_status_warning(self, monitor):
        """Test getting status for a token in warning period."""
        expires_at = datetime.utcnow() + timedelta(days=5)

        status = monitor.get_expiry_status(expires_at)

        assert status["status"] == "expiring"
        assert status["severity"] == "warning"
        # Days might be 4 or 5 depending on microseconds
        assert status["days_to_expiry"] >= 4
        assert status["days_to_expiry"] <= 5

    def test_get_expiry_status_critical(self, monitor):
        """Test getting status for a token in critical period."""
        expires_at = datetime.utcnow() + timedelta(days=2)

        status = monitor.get_expiry_status(expires_at)

        assert status["status"] == "expiring_soon"
        assert status["severity"] == "critical"
        # Days might be 1 or 2 depending on microseconds
        assert status["days_to_expiry"] >= 1
        assert status["days_to_expiry"] <= 2

    def test_get_expiry_status_expired(self, monitor):
        """Test getting status for an expired token."""
        expires_at = datetime.utcnow() - timedelta(days=1)

        status = monitor.get_expiry_status(expires_at)

        assert status["status"] == "expired"
        assert status["severity"] == "critical"
        assert status["days_to_expiry"] < 0

    def test_notification_without_admin_user(self, monitor, mock_messaging_client):
        """Test that notification works when admin_user_id is None."""
        expires_at = datetime.utcnow() + timedelta(days=5)

        # Should not raise an error
        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id=None,
        )

    def test_messaging_client_failure(self, monitor, mock_messaging_client):
        """Test that messaging client failures are handled gracefully."""
        mock_messaging_client.send_text_message.side_effect = Exception("Network error")

        expires_at = datetime.utcnow() + timedelta(days=5)

        # Should not raise an error
        monitor.check_token_expiry(
            app_id="test_app",
            token_expires_at=expires_at,
            admin_user_id="user123",
        )

    def test_prometheus_metrics_update(self, monitor, mock_messaging_client):
        """Test that Prometheus metrics are updated."""
        expires_at = datetime.utcnow() + timedelta(days=5)

        with patch("lark_service.services.token_monitor.TOKEN_DAYS_TO_EXPIRY") as mock_gauge:
            monitor.check_token_expiry(
                app_id="test_app",
                token_expires_at=expires_at,
                admin_user_id="user123",
            )

            # Check that gauge was set
            mock_gauge.labels.assert_called_with(app_id="test_app")
