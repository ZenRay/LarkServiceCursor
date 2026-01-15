"""Unit tests for TokenStorage model.

Tests expiration checking, refresh logic, and unique constraints.
"""

from datetime import datetime, timedelta

import pytest

from lark_service.core.models.token_storage import TokenStorage


class TestTokenStorageModel:
    """Test TokenStorage model functionality."""

    @pytest.fixture
    def sample_token(self) -> TokenStorage:
        """Create a sample token for testing."""
        now = datetime.now()
        return TokenStorage(
            app_id="cli_a1b2c3d4e5f6g7h8",
            token_type="app_access_token",
            token_value="encrypted_token_value",
            expires_at=now + timedelta(hours=2),
            created_at=now,
        )

    def test_token_creation(self) -> None:
        """Test basic token creation."""
        token = TokenStorage(
            app_id="cli_test123456789",
            token_type="app_access_token",
            token_value="test_token",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert token.app_id == "cli_test123456789"
        assert token.token_type == "app_access_token"
        assert token.token_value == "test_token"

    def test_is_expired_not_expired(self, sample_token: TokenStorage) -> None:
        """Test is_expired() returns False for valid token."""
        assert sample_token.is_expired() is False

    def test_is_expired_expired_token(self) -> None:
        """Test is_expired() returns True for expired token."""
        token = TokenStorage(
            app_id="cli_test",
            token_type="app_access_token",
            token_value="test",
            expires_at=datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
        )
        assert token.is_expired() is True

    def test_is_expired_with_custom_now(self, sample_token: TokenStorage) -> None:
        """Test is_expired() with custom timestamp."""
        future_time = sample_token.expires_at + timedelta(minutes=1)
        assert sample_token.is_expired(now=future_time) is True

    def test_should_refresh_not_needed(self, sample_token: TokenStorage) -> None:
        """Test should_refresh() returns False when plenty of time remains."""
        # Token has 2 hours lifetime, just created
        # With 10% threshold, should refresh when < 12 minutes remain
        assert sample_token.should_refresh(threshold=0.1) is False

    def test_should_refresh_needed(self) -> None:
        """Test should_refresh() returns True when near expiration."""
        now = datetime.now()
        # Token created 1h50m ago, expires in 10 minutes (2h total lifetime)
        # 10 minutes = 8.3% of 2 hours, less than 10% threshold
        token = TokenStorage(
            app_id="cli_test",
            token_type="app_access_token",
            token_value="test",
            created_at=now - timedelta(hours=1, minutes=50),
            expires_at=now + timedelta(minutes=10),
        )
        assert token.should_refresh(threshold=0.1) is True

    def test_should_refresh_expired_token(self) -> None:
        """Test should_refresh() returns True for expired token."""
        token = TokenStorage(
            app_id="cli_test",
            token_type="app_access_token",
            token_value="test",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert token.should_refresh() is True

    def test_get_remaining_seconds_positive(self, sample_token: TokenStorage) -> None:
        """Test get_remaining_seconds() returns positive value for valid token."""
        remaining = sample_token.get_remaining_seconds()
        assert remaining > 0
        # Should be close to 2 hours (7200 seconds)
        assert 7000 < remaining < 7300

    def test_get_remaining_seconds_negative(self) -> None:
        """Test get_remaining_seconds() returns negative value for expired token."""
        token = TokenStorage(
            app_id="cli_test",
            token_type="app_access_token",
            token_value="test",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        remaining = token.get_remaining_seconds()
        assert remaining < 0

    def test_token_repr(self, sample_token: TokenStorage) -> None:
        """Test string representation."""
        repr_str = repr(sample_token)
        assert "TokenStorage" in repr_str
        assert sample_token.app_id in repr_str
        assert sample_token.token_type in repr_str

    def test_different_token_types(self) -> None:
        """Test creating tokens with different types."""
        types = ["app_access_token", "tenant_access_token", "user_access_token"]
        for token_type in types:
            token = TokenStorage(
                app_id="cli_test",
                token_type=token_type,
                token_value="test",
                expires_at=datetime.now() + timedelta(hours=1),
            )
            assert token.token_type == token_type
