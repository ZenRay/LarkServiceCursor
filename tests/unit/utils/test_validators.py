"""Unit tests for validators module.

Tests input validation for various data types.
"""

import pytest

from lark_service.core.exceptions import ValidationError
from lark_service.utils import validators


class TestAppCredentialsValidation:
    """Test application credentials validation."""

    def test_validate_app_id_success(self) -> None:
        """Test valid app_id."""
        valid_ids = [
            "cli_a1b2c3d4e5f6g7h8",
            "cli_1234567890abcdef",
            "cli_ABCDEF1234567890abcdef12",
        ]
        for app_id in valid_ids:
            assert validators.validate_app_id(app_id) == app_id

    def test_validate_app_id_empty(self) -> None:
        """Test empty app_id."""
        with pytest.raises(ValidationError, match="app_id cannot be empty"):
            validators.validate_app_id("")

    def test_validate_app_id_invalid_format(self) -> None:
        """Test invalid app_id format."""
        invalid_ids = [
            "invalid",
            "app_123",
            "cli_",
            "cli_abc",  # Too short
        ]
        for app_id in invalid_ids:
            with pytest.raises(ValidationError, match="Invalid app_id format"):
                validators.validate_app_id(app_id)

    def test_validate_app_secret_success(self) -> None:
        """Test valid app_secret."""
        secret = "a1b2c3d4e5f6g7h8i9j0k1l2"
        assert validators.validate_app_secret(secret) == secret

    def test_validate_app_secret_empty(self) -> None:
        """Test empty app_secret."""
        with pytest.raises(ValidationError, match="app_secret cannot be empty"):
            validators.validate_app_secret("")

    def test_validate_app_secret_too_short(self) -> None:
        """Test app_secret too short."""
        with pytest.raises(ValidationError, match="app_secret too short"):
            validators.validate_app_secret("short")

    def test_validate_app_secret_too_long(self) -> None:
        """Test app_secret too long."""
        long_secret = "a" * 129
        with pytest.raises(ValidationError, match="app_secret too long"):
            validators.validate_app_secret(long_secret)


class TestUserIdentifierValidation:
    """Test user identifier validation."""

    def test_validate_open_id_success(self) -> None:
        """Test valid open_id."""
        valid_ids = [
            "ou_1234567890abcdef",
            "ou_ABCDEF1234567890",
            "ou_a1b2c3d4e5f6g7h8i9j0k1l2",
        ]
        for open_id in valid_ids:
            assert validators.validate_open_id(open_id) == open_id

    def test_validate_open_id_invalid(self) -> None:
        """Test invalid open_id."""
        with pytest.raises(ValidationError, match="Invalid open_id format"):
            validators.validate_open_id("invalid")

    def test_validate_user_id_success(self) -> None:
        """Test valid user_id."""
        valid_ids = ["1234567890", "user_123", "test-user"]
        for user_id in valid_ids:
            assert validators.validate_user_id(user_id) == user_id

    def test_validate_user_id_invalid(self) -> None:
        """Test invalid user_id."""
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validators.validate_user_id("invalid@user")

    def test_validate_union_id_success(self) -> None:
        """Test valid union_id."""
        union_id = "on_1234567890abcdef"
        assert validators.validate_union_id(union_id) == union_id

    def test_validate_union_id_invalid(self) -> None:
        """Test invalid union_id."""
        with pytest.raises(ValidationError, match="Invalid union_id format"):
            validators.validate_union_id("invalid")

    def test_validate_chat_id_success(self) -> None:
        """Test valid chat_id."""
        chat_id = "oc_1234567890abcdef"
        assert validators.validate_chat_id(chat_id) == chat_id

    def test_validate_chat_id_invalid(self) -> None:
        """Test invalid chat_id."""
        with pytest.raises(ValidationError, match="Invalid chat_id format"):
            validators.validate_chat_id("invalid")


class TestTokenValidation:
    """Test token validation."""

    def test_validate_token_success(self) -> None:
        """Test valid token."""
        token = "t-abc123def456ghi789"
        assert validators.validate_token(token) == token

    def test_validate_token_empty(self) -> None:
        """Test empty token."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validators.validate_token("")

    def test_validate_token_too_short(self) -> None:
        """Test token too short."""
        with pytest.raises(ValidationError, match="too short"):
            validators.validate_token("short")

    def test_validate_token_too_long(self) -> None:
        """Test token too long."""
        long_token = "t" * 1025
        with pytest.raises(ValidationError, match="too long"):
            validators.validate_token(long_token)


class TestUrlValidation:
    """Test URL validation."""

    def test_validate_url_https_success(self) -> None:
        """Test valid HTTPS URL."""
        url = "https://example.com/callback"
        assert validators.validate_url(url) == url

    def test_validate_url_http_with_flag(self) -> None:
        """Test HTTP URL with require_https=False."""
        url = "http://example.com"
        assert validators.validate_url(url, require_https=False) == url

    def test_validate_url_http_require_https(self) -> None:
        """Test HTTP URL with require_https=True."""
        with pytest.raises(ValidationError, match="must use HTTPS protocol"):
            validators.validate_url("http://example.com", require_https=True)

    def test_validate_url_empty(self) -> None:
        """Test empty URL."""
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            validators.validate_url("")

    def test_validate_url_missing_protocol(self) -> None:
        """Test URL missing protocol."""
        with pytest.raises(ValidationError, match="missing protocol"):
            validators.validate_url("example.com")

    def test_validate_url_missing_domain(self) -> None:
        """Test URL missing domain."""
        with pytest.raises(ValidationError, match="missing domain"):
            validators.validate_url("https://")


class TestFilePathValidation:
    """Test file path validation."""

    def test_validate_file_path_success(self, tmp_path) -> None:
        """Test valid file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        result = validators.validate_file_path(str(test_file), must_exist=True)
        assert result == test_file

    def test_validate_file_path_not_exist(self, tmp_path) -> None:
        """Test file path that doesn't exist."""
        test_file = tmp_path / "nonexistent.txt"
        with pytest.raises(ValidationError, match="File does not exist"):
            validators.validate_file_path(str(test_file), must_exist=True)

    def test_validate_file_path_no_exist_check(self, tmp_path) -> None:
        """Test file path without existence check."""
        test_file = tmp_path / "nonexistent.txt"
        result = validators.validate_file_path(str(test_file), must_exist=False)
        assert result == test_file


class TestNumericValidation:
    """Test numeric validation."""

    def test_validate_positive_int_success(self) -> None:
        """Test valid positive integer."""
        assert validators.validate_positive_int(10) == 10
        assert validators.validate_positive_int("5") == 5

    def test_validate_positive_int_zero(self) -> None:
        """Test zero value."""
        with pytest.raises(ValidationError, match="must be positive"):
            validators.validate_positive_int(0)

    def test_validate_positive_int_negative(self) -> None:
        """Test negative value."""
        with pytest.raises(ValidationError, match="must be positive"):
            validators.validate_positive_int(-5)

    def test_validate_positive_int_invalid_type(self) -> None:
        """Test invalid type."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validators.validate_positive_int("invalid")

    def test_validate_non_negative_float_success(self) -> None:
        """Test valid non-negative float."""
        assert validators.validate_non_negative_float(3.14) == 3.14
        assert validators.validate_non_negative_float(0.0) == 0.0
        assert validators.validate_non_negative_float("2.5") == 2.5

    def test_validate_non_negative_float_negative(self) -> None:
        """Test negative float."""
        with pytest.raises(ValidationError, match="cannot be negative"):
            validators.validate_non_negative_float(-1.5)

    def test_validate_non_negative_float_invalid_type(self) -> None:
        """Test invalid type."""
        with pytest.raises(ValidationError, match="must be a number"):
            validators.validate_non_negative_float("invalid")


class TestEnumValidation:
    """Test enum validation."""

    def test_validate_enum_success(self) -> None:
        """Test valid enum value."""
        allowed = ["active", "inactive", "pending"]
        assert validators.validate_enum("active", allowed) == "active"

    def test_validate_enum_invalid(self) -> None:
        """Test invalid enum value."""
        allowed = ["active", "inactive"]
        with pytest.raises(ValidationError, match="Invalid .* value"):
            validators.validate_enum("deleted", allowed)
