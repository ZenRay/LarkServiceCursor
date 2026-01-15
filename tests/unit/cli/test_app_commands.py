"""Unit tests for CLI app commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from cryptography.fernet import Fernet

from lark_service.cli import main
from lark_service.core.storage.sqlite_storage import ApplicationManager


@pytest.fixture
def encryption_key() -> bytes:
    """Generate encryption key for tests."""
    return Fernet.generate_key()


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create temporary database path."""
    return tmp_path / "test_config.db"


@pytest.fixture
def mock_env(temp_db: Path, encryption_key: bytes, monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("LARK_CONFIG_DB_PATH", str(temp_db))
    monkeypatch.setenv("LARK_CONFIG_ENCRYPTION_KEY", encryption_key.decode())


@pytest.fixture
def cli_runner():
    """Create CLI runner."""
    return CliRunner()


class TestAppAdd:
    """Tests for app add command."""

    def test_add_app_success(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test successfully adding an application."""
        result = cli_runner.invoke(
            main,
            [
                "app",
                "add",
                "--app-id",
                "cli_test123456789012",
                "--app-name",
                "Test App",
                "--app-secret",
                "test_secret_1234567890",
            ],
        )

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()

        # Verify app was added
        manager = ApplicationManager(temp_db, encryption_key)
        app = manager.get_application("cli_test123456789012")
        assert app is not None
        assert app.app_name == "Test App"
        manager.close()

    def test_add_app_invalid_id(self, cli_runner, mock_env):
        """Test adding app with invalid ID."""
        result = cli_runner.invoke(
            main,
            [
                "app",
                "add",
                "--app-id",
                "invalid",
                "--app-name",
                "Test",
                "--app-secret",
                "test_secret_1234567890",
            ],
        )

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

    def test_add_app_short_secret(self, cli_runner, mock_env):
        """Test adding app with too short secret."""
        result = cli_runner.invoke(
            main,
            [
                "app",
                "add",
                "--app-id",
                "cli_test123456789012",
                "--app-name",
                "Test",
                "--app-secret",
                "short",
            ],
        )

        assert result.exit_code != 0


class TestAppList:
    """Tests for app list command."""

    def test_list_empty(self, cli_runner, mock_env):
        """Test listing when no apps exist."""
        result = cli_runner.invoke(main, ["app", "list"])

        assert result.exit_code == 0
        assert "no applications" in result.output.lower() or "0" in result.output

    def test_list_with_apps(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test listing apps."""
        # Add test apps
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App 1",
            "test_secret_1234567890",
        )
        manager.add_application(
            "cli_test223456789012",
            "Test App 2",
            "test_secret_2234567890",
        )
        manager.close()

        result = cli_runner.invoke(main, ["app", "list"])

        assert result.exit_code == 0
        assert "Test App 1" in result.output
        assert "Test App 2" in result.output

    def test_list_json_format(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test listing apps in JSON format."""
        # Add test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App",
            "test_secret_1234567890",
        )
        manager.close()

        result = cli_runner.invoke(main, ["app", "list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["app_name"] == "Test App"


class TestAppShow:
    """Tests for app show command."""

    def test_show_existing_app(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test showing existing app."""
        # Add test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App",
            "test_secret_1234567890",
        )
        manager.close()

        result = cli_runner.invoke(main, ["app", "show", "cli_test123456789012"])

        assert result.exit_code == 0
        assert "Test App" in result.output
        assert "cli_test123456789012" in result.output

    def test_show_nonexistent_app(self, cli_runner, mock_env):
        """Test showing non-existent app."""
        result = cli_runner.invoke(main, ["app", "show", "cli_nonexistent12345"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestAppUpdate:
    """Tests for app update command."""

    def test_update_app_name(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test updating app name."""
        # Add test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Old Name",
            "test_secret_1234567890",
        )
        manager.close()

        result = cli_runner.invoke(
            main,
            [
                "app",
                "update",
                "cli_test123456789012",
                "--app-name",
                "New Name",
            ],
        )

        assert result.exit_code == 0
        assert "updated" in result.output.lower()

        # Verify update
        manager = ApplicationManager(temp_db, encryption_key)
        app = manager.get_application("cli_test123456789012")
        assert app.app_name == "New Name"
        manager.close()


class TestAppDelete:
    """Tests for app delete command."""

    def test_delete_with_confirmation(
        self, cli_runner, mock_env, temp_db, encryption_key
    ):
        """Test deleting app with confirmation."""
        # Add test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App",
            "test_secret_1234567890",
        )
        manager.close()

        result = cli_runner.invoke(
            main,
            ["app", "delete", "cli_test123456789012"],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "deleted" in result.output.lower()

    def test_delete_with_force(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test deleting app with --force flag."""
        # Add test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App",
            "test_secret_1234567890",
        )
        manager.close()

        result = cli_runner.invoke(
            main,
            ["app", "delete", "cli_test123456789012", "--force"],
        )

        assert result.exit_code == 0


class TestAppEnableDisable:
    """Tests for app enable/disable commands."""

    def test_disable_app(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test disabling an app."""
        # Add test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App",
            "test_secret_1234567890",
        )
        manager.close()

        result = cli_runner.invoke(
            main,
            ["app", "disable", "cli_test123456789012"],
        )

        assert result.exit_code == 0
        assert "disabled" in result.output.lower()

    def test_enable_app(self, cli_runner, mock_env, temp_db, encryption_key):
        """Test enabling an app."""
        # Add and disable test app
        manager = ApplicationManager(temp_db, encryption_key)
        manager.add_application(
            "cli_test123456789012",
            "Test App",
            "test_secret_1234567890",
        )
        manager.update_application("cli_test123456789012", status="inactive")
        manager.close()

        result = cli_runner.invoke(
            main,
            ["app", "enable", "cli_test123456789012"],
        )

        assert result.exit_code == 0
        assert "enabled" in result.output.lower()
