"""Unit tests for Application model.

Tests encryption/decryption, status validation, and model behavior.
"""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from lark_service.core.models.application import Application


class TestApplicationModel:
    """Test Application model functionality."""

    @pytest.fixture
    def encryption_key(self) -> bytes:
        """Generate a test encryption key."""
        return Fernet.generate_key()

    @pytest.fixture
    def sample_app(self, encryption_key: bytes) -> Application:
        """Create a sample application for testing."""
        app = Application(
            app_id="cli_a1b2c3d4e5f6g7h8",
            app_name="Test Application",
            description="Test app for unit tests",
            status="active",
        )
        app.set_encrypted_secret("test_secret_123", encryption_key)
        return app

    def test_application_creation(self) -> None:
        """Test basic application creation."""
        app = Application(
            app_id="cli_test123456789",
            app_name="Test App",
            status="active",
        )
        assert app.app_id == "cli_test123456789"
        assert app.app_name == "Test App"
        assert app.status == "active"
        assert app.is_active() is True

    def test_is_active_status(self) -> None:
        """Test is_active() method with different statuses."""
        active_app = Application(app_id="cli_test1", app_name="Active", status="active")
        assert active_app.is_active() is True

        disabled_app = Application(app_id="cli_test2", app_name="Disabled", status="disabled")
        assert disabled_app.is_active() is False

    def test_encrypt_decrypt_secret(self, encryption_key: bytes) -> None:
        """Test secret encryption and decryption."""
        app = Application(
            app_id="cli_test123456789",
            app_name="Test App",
            status="active",
        )

        original_secret = "my_super_secret_key_123"
        app.set_encrypted_secret(original_secret, encryption_key)

        # Verify secret is encrypted (not plain text)
        assert app.app_secret != original_secret

        # Verify decryption works
        decrypted = app.get_decrypted_secret(encryption_key)
        assert decrypted == original_secret

    def test_decrypt_with_wrong_key(self, encryption_key: bytes) -> None:
        """Test decryption fails with wrong key."""
        app = Application(
            app_id="cli_test123456789",
            app_name="Test App",
            status="active",
        )
        app.set_encrypted_secret("secret", encryption_key)

        wrong_key = Fernet.generate_key()
        with pytest.raises(InvalidToken):
            app.get_decrypted_secret(wrong_key)

    def test_application_repr(self, sample_app: Application) -> None:
        """Test string representation."""
        repr_str = repr(sample_app)
        assert "Application" in repr_str
        assert sample_app.app_id in repr_str
        assert sample_app.app_name in repr_str
        assert sample_app.status in repr_str

    def test_timestamps_auto_set(self) -> None:
        """Test that timestamps are automatically set."""
        app = Application(
            app_id="cli_test123456789",
            app_name="Test App",
            status="active",
        )
        # Note: created_at and updated_at are set by SQLAlchemy when saved to DB
        # In pure Python, they won't be set until DB commit
        assert app.created_at is None  # Not yet saved to DB
        assert app.updated_at is None

    def test_permissions_field(self) -> None:
        """Test permissions field can store JSON string."""
        app = Application(
            app_id="cli_test123456789",
            app_name="Test App",
            status="active",
            permissions='["im:message", "contact:user.base:readonly"]',
        )
        assert app.permissions is not None
        assert "im:message" in app.permissions

    def test_created_by_field(self) -> None:
        """Test created_by field for audit trail."""
        app = Application(
            app_id="cli_test123456789",
            app_name="Test App",
            status="active",
            created_by="admin_user",
        )
        assert app.created_by == "admin_user"
