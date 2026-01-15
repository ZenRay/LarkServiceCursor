"""Unit tests for configuration loader.

Tests environment variable loading, validation, and URL generation.
"""

import os
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from lark_service.core.config import Config


class TestConfig:
    """Test configuration loading and validation."""

    @pytest.fixture
    def valid_env_vars(self) -> dict[str, str]:
        """Set up valid environment variables for testing."""
        encryption_key = Fernet.generate_key().decode()
        env_vars = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test_db",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_PORT": "5672",
            "RABBITMQ_USER": "test_rabbit",
            "RABBITMQ_PASSWORD": "rabbit_password",
            "LARK_CONFIG_ENCRYPTION_KEY": encryption_key,
            "LOG_LEVEL": "DEBUG",
            "MAX_RETRIES": "5",
            "TOKEN_REFRESH_THRESHOLD": "0.2",
        }
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        return env_vars

    @pytest.fixture(autouse=True)
    def cleanup_env(self) -> None:
        """Clean up environment variables after each test."""
        yield
        # Clean up
        env_keys = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "RABBITMQ_HOST",
            "RABBITMQ_PORT",
            "RABBITMQ_USER",
            "RABBITMQ_PASSWORD",
            "LARK_CONFIG_ENCRYPTION_KEY",
            "LOG_LEVEL",
            "MAX_RETRIES",
            "TOKEN_REFRESH_THRESHOLD",
            "LARK_APP_ID",
            "LARK_APP_SECRET",
        ]
        for key in env_keys:
            os.environ.pop(key, None)

    def test_load_from_env_success(self, valid_env_vars: dict[str, str]) -> None:
        """Test successful configuration loading."""
        config = Config.load_from_env()

        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5432
        assert config.postgres_db == "test_db"
        assert config.postgres_user == "test_user"
        assert config.postgres_password == "test_password"
        assert config.rabbitmq_host == "localhost"
        assert config.rabbitmq_port == 5672
        assert config.log_level == "DEBUG"
        assert config.max_retries == 5
        assert config.token_refresh_threshold == 0.2

    def test_load_from_env_missing_required_var(self, tmp_path: Path) -> None:
        """Test error when required variable is missing."""
        # Clear all environment variables first
        for key in ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", 
                    "POSTGRES_PASSWORD", "LARK_CONFIG_ENCRYPTION_KEY"]:
            os.environ.pop(key, None)
        
        # Set only some variables
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["POSTGRES_DB"] = "test_db"
        # Missing POSTGRES_USER, POSTGRES_PASSWORD, LARK_CONFIG_ENCRYPTION_KEY

        # Create an empty .env file to prevent loading from project root
        empty_env = tmp_path / "empty.env"
        empty_env.write_text("")
        
        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config.load_from_env(env_file=empty_env)

    def test_load_from_env_invalid_encryption_key(self) -> None:
        """Test error with invalid encryption key."""
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["POSTGRES_DB"] = "test_db"
        os.environ["POSTGRES_USER"] = "user"
        os.environ["POSTGRES_PASSWORD"] = "pass"
        os.environ["LARK_CONFIG_ENCRYPTION_KEY"] = "invalid_key"

        with pytest.raises(ValueError, match="Invalid LARK_CONFIG_ENCRYPTION_KEY"):
            Config.load_from_env()

    def test_load_from_env_invalid_threshold(self, valid_env_vars: dict[str, str]) -> None:
        """Test error with invalid token refresh threshold."""
        os.environ["TOKEN_REFRESH_THRESHOLD"] = "1.5"  # > 1.0

        with pytest.raises(ValueError, match="TOKEN_REFRESH_THRESHOLD must be between"):
            Config.load_from_env()

    def test_get_postgres_url(self, valid_env_vars: dict[str, str]) -> None:
        """Test PostgreSQL URL generation."""
        config = Config.load_from_env()
        url = config.get_postgres_url()

        assert url == "postgresql://test_user:test_password@localhost:5432/test_db"
        assert "test_user" in url
        assert "test_password" in url

    def test_get_rabbitmq_url(self, valid_env_vars: dict[str, str]) -> None:
        """Test RabbitMQ URL generation."""
        config = Config.load_from_env()
        url = config.get_rabbitmq_url()

        assert url == "amqp://test_rabbit:rabbit_password@localhost:5672/"
        assert "test_rabbit" in url
        assert "rabbit_password" in url

    def test_default_values(self) -> None:
        """Test default values are used when optional vars not set."""
        # Set only required variables
        encryption_key = Fernet.generate_key().decode()
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["POSTGRES_DB"] = "test_db"
        os.environ["POSTGRES_USER"] = "user"
        os.environ["POSTGRES_PASSWORD"] = "pass"
        os.environ["LARK_CONFIG_ENCRYPTION_KEY"] = encryption_key

        config = Config.load_from_env()

        # Check defaults
        assert config.postgres_port == 5432  # Default
        assert config.rabbitmq_host == "localhost"  # Default
        assert config.rabbitmq_port == 5672  # Default
        assert config.log_level == "INFO"  # Default
        assert config.max_retries == 3  # Default
        assert config.token_refresh_threshold == 0.1  # Default
