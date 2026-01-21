"""Unit tests for ApplicationManager.

Tests the get_default_app_id() method added in T002.
"""

from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from lark_service.core.storage.sqlite_storage import ApplicationManager


@pytest.fixture
def mock_db_path(tmp_path):
    """Create temporary database path."""
    return tmp_path / "test_app_manager.db"


@pytest.fixture
def encryption_key():
    """Generate test encryption key."""
    return Fernet.generate_key()


@pytest.fixture
def app_manager(mock_db_path, encryption_key):
    """Create ApplicationManager instance."""
    manager = ApplicationManager(mock_db_path, encryption_key)
    yield manager
    manager.close()


class TestApplicationManagerDefaultAppId:
    """Test suite for ApplicationManager.get_default_app_id()."""

    def test_get_default_app_id_single_app_scenario(
        self,
        app_manager: ApplicationManager,
    ) -> None:
        """Test auto-selection when only one active app exists."""
        # Add single active application
        app_manager.add_application(
            app_id="cli_single123456789012345",
            app_name="Single App",
            app_secret="secret1234567890123456",
        )

        # Should auto-select the single app
        default_id = app_manager.get_default_app_id()
        assert default_id == "cli_single123456789012345"

    def test_get_default_app_id_multi_app_scenario(
        self,
        app_manager: ApplicationManager,
    ) -> None:
        """Test no auto-selection when multiple active apps exist."""
        # Add multiple active applications
        app_manager.add_application(
            app_id="cli_app1test1234567890123",
            app_name="App 1",
            app_secret="secret1234567890123456",
        )
        app_manager.add_application(
            app_id="cli_app2test1234567890123",
            app_name="App 2",
            app_secret="secret2234567890123456",
        )

        # Should return None (requires explicit selection)
        default_id = app_manager.get_default_app_id()
        assert default_id is None

    def test_get_default_app_id_no_apps(
        self,
        app_manager: ApplicationManager,
    ) -> None:
        """Test when no applications are configured."""
        default_id = app_manager.get_default_app_id()
        assert default_id is None

    def test_get_default_app_id_only_inactive_apps(
        self,
        app_manager: ApplicationManager,
    ) -> None:
        """Test when only inactive apps exist."""
        # Add app and deactivate it
        app_manager.add_application(
            app_id="cli_inactive12345678901234",
            app_name="Inactive App",
            app_secret="secret1234567890123456",
        )
        app_manager.update_application(
            app_id="cli_inactive12345678901234",
            status="inactive",
        )

        # Should return None (no active apps)
        default_id = app_manager.get_default_app_id()
        assert default_id is None

    def test_get_default_app_id_mixed_active_inactive(
        self,
        app_manager: ApplicationManager,
    ) -> None:
        """Test with mix of active and inactive apps."""
        # Add two apps
        app_manager.add_application(
            app_id="cli_active123456789012345",
            app_name="Active App",
            app_secret="secret1234567890123456",
        )
        app_manager.add_application(
            app_id="cli_inactive12345678901234",
            app_name="Inactive App 2",
            app_secret="secret2234567890123456",
        )

        # Deactivate second app
        app_manager.update_application(
            app_id="cli_inactive12345678901234",
            status="inactive",
        )

        # Should auto-select the only active app
        default_id = app_manager.get_default_app_id()
        assert default_id == "cli_active123456789012345"

    def test_get_default_app_id_error_handling(
        self,
        mock_db_path: Path,
        encryption_key: bytes,
    ) -> None:
        """Test error handling when database query fails."""
        app_manager = ApplicationManager(mock_db_path, encryption_key)

        # Simulate database error by closing engine
        app_manager.engine.dispose()

        # Should return None on error
        default_id = app_manager.get_default_app_id()
        assert default_id is None
