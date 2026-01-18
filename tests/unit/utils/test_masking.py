"""Tests for sensitive data masking utilities."""

# Direct import to avoid circular import issues
from lark_service.utils import masking

mask_dict = masking.mask_dict
mask_email = masking.mask_email
mask_log_message = masking.mask_log_message
mask_mobile = masking.mask_mobile
mask_token = masking.mask_token
mask_user_id = masking.mask_user_id


class TestMaskEmail:
    """Test email masking."""

    def test_mask_normal_email(self) -> None:
        """Test masking normal email."""
        assert mask_email("john.doe@example.com") == "jo***@ex***.com"
        assert mask_email("alice@company.org") == "al***@co***.org"

    def test_mask_short_email(self) -> None:
        """Test masking short email."""
        # For username length <= 2, show only first char
        assert mask_email("a@b.com") == "a***@b***.com"
        # "ab" has length 2, so shows "a***"
        assert mask_email("ab@cd.com") == "a***@c***.com"

    def test_mask_long_email(self) -> None:
        """Test masking long email."""
        result = mask_email("verylongusername@verylongdomain.com")
        assert result.startswith("ve***@")
        assert result.endswith(".com")

    def test_mask_invalid_email(self) -> None:
        """Test masking invalid email."""
        assert mask_email("") == "***"
        # Invalid email without "@" returns "***"
        assert mask_email("notanemail") == "***"
        # Exception in parsing returns "***@***.***"
        assert mask_email("@") == "***@***.***"


class TestMaskMobile:
    """Test mobile number masking."""

    def test_mask_international_mobile(self) -> None:
        """Test masking international mobile."""
        assert mask_mobile("+8615680013621") == "+86****3621"
        assert mask_mobile("+1234567890") == "+12****7890"

    def test_mask_domestic_mobile(self) -> None:
        """Test masking domestic mobile."""
        assert mask_mobile("15680013621") == "156****3621"
        assert mask_mobile("13800138000") == "138****8000"

    def test_mask_short_mobile(self) -> None:
        """Test masking short mobile."""
        # Length 5: shows first 3 and last 2 (len <= 7 branch)
        assert mask_mobile("12345") == "123***45"
        # Length 3: shows first and last char
        assert mask_mobile("123") == "1***3"

    def test_mask_mobile_with_spaces(self) -> None:
        """Test masking mobile with spaces."""
        assert mask_mobile("+86 156 8001 3621") == "+86****3621"
        assert mask_mobile("156-8001-3621") == "156****3621"

    def test_mask_empty_mobile(self) -> None:
        """Test masking empty mobile."""
        assert mask_mobile("") == "***"


class TestMaskToken:
    """Test token masking."""

    def test_mask_normal_token(self) -> None:
        """Test masking normal token."""
        assert mask_token("t-abc123def456ghi789") == "t-ab***i789"
        # "cli_a1b2c3d4e5f6g7h8" has 20 chars, show_prefix=4, show_suffix=4
        assert mask_token("cli_a1b2c3d4e5f6g7h8") == "cli_***g7h8"

    def test_mask_short_token(self) -> None:
        """Test masking short token."""
        assert mask_token("abc") == "ab***"
        assert mask_token("a") == "a***"

    def test_mask_custom_lengths(self) -> None:
        """Test masking with custom lengths."""
        assert mask_token("abcdefghij", show_prefix=2, show_suffix=2) == "ab***ij"
        assert mask_token("abcdefghij", show_prefix=3, show_suffix=3) == "abc***hij"

    def test_mask_empty_token(self) -> None:
        """Test masking empty token."""
        assert mask_token("") == "***"


class TestMaskUserId:
    """Test user ID masking."""

    def test_mask_open_id(self) -> None:
        """Test masking open_id."""
        assert mask_user_id("ou_1234567890abcdefghij") == "ou_***ghij"
        assert mask_user_id("ou_abc") == "ou_***"

    def test_mask_union_id(self) -> None:
        """Test masking union_id."""
        assert mask_user_id("on_1234567890abcdefghij", "union_id") == "on_***ghij"

    def test_mask_chat_id(self) -> None:
        """Test masking chat_id."""
        assert mask_user_id("oc_1234567890abcdefghij") == "oc_***ghij"

    def test_mask_short_user_id(self) -> None:
        """Test masking short user ID."""
        assert mask_user_id("ou_123") == "ou_***"
        assert mask_user_id("abc") == "ab***"

    def test_mask_empty_user_id(self) -> None:
        """Test masking empty user ID."""
        assert mask_user_id("") == "***"


class TestMaskDict:
    """Test dictionary masking."""

    def test_mask_email_field(self) -> None:
        """Test masking email field."""
        data = {"email": "john@example.com", "name": "John"}
        masked = mask_dict(data)
        assert "***" in masked["email"]
        assert masked["name"] == "John"

    def test_mask_mobile_field(self) -> None:
        """Test masking mobile field."""
        data = {"mobile": "+8615680013621", "age": 30}
        masked = mask_dict(data)
        assert "***" in masked["mobile"]
        assert masked["age"] == 30

    def test_mask_token_field(self) -> None:
        """Test masking token field."""
        data = {"access_token": "t-abc123def456", "user_id": "123"}
        masked = mask_dict(data)
        assert "***" in masked["access_token"]
        assert masked["user_id"] == "123"

    def test_mask_multiple_fields(self) -> None:
        """Test masking multiple sensitive fields."""
        data = {
            "email": "john@example.com",
            "mobile": "15680013621",
            "token": "abc123",
            "name": "John",
        }
        masked = mask_dict(data)
        assert "***" in masked["email"]
        assert "***" in masked["mobile"]
        assert "***" in masked["token"]
        assert masked["name"] == "John"

    def test_mask_custom_keys(self) -> None:
        """Test masking with custom sensitive keys."""
        data = {"api_key": "secret123", "username": "john"}
        masked = mask_dict(data, sensitive_keys=["api_key"])
        assert "***" in masked["api_key"]
        assert masked["username"] == "john"


class TestMaskLogMessage:
    """Test log message masking."""

    def test_mask_email_in_message(self) -> None:
        """Test masking email in log message."""
        message = "User john.doe@example.com logged in"
        masked = mask_log_message(message)
        assert "jo***@ex***" in masked
        assert "logged in" in masked

    def test_mask_mobile_in_message(self) -> None:
        """Test masking mobile in log message."""
        message = "Contact: +8615680013621"
        masked = mask_log_message(message)
        assert "+86****3621" in masked

    def test_mask_token_in_message(self) -> None:
        """Test masking token in log message."""
        message = "Token: t-abc123def456ghi789"
        masked = mask_log_message(message)
        assert "t-ab***" in masked

    def test_mask_multiple_sensitive_data(self) -> None:
        """Test masking multiple sensitive data."""
        # Use a realistic token length (12+ chars after prefix) to match regex pattern
        message = "User john@example.com with token t-abc123def456ghi and mobile +8615680013621"
        masked = mask_log_message(message)
        assert "jo***@ex***" in masked
        # Token "t-abc123def456ghi" (17 chars) matches regex {12,}, gets masked
        assert "t-ab***" in masked
        assert "+86****3621" in masked

    def test_mask_no_sensitive_data(self) -> None:
        """Test message with no sensitive data."""
        message = "This is a normal log message"
        masked = mask_log_message(message)
        assert masked == message


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_mask_none_values(self) -> None:
        """Test masking None values."""
        assert mask_email("") == "***"
        assert mask_mobile("") == "***"
        assert mask_token("") == "***"
        assert mask_user_id("") == "***"

    def test_mask_very_long_values(self) -> None:
        """Test masking very long values."""
        long_email = "a" * 100 + "@" + "b" * 100 + ".com"
        result = mask_email(long_email)
        assert "***" in result
        assert len(result) < len(long_email)

    def test_mask_special_characters(self) -> None:
        """Test masking values with special characters."""
        assert "***" in mask_email("user+tag@example.com")
        assert "***" in mask_mobile("+86-156-8001-3621")

    def test_mask_dict_with_non_string_values(self) -> None:
        """Test masking dict with non-string values."""
        data = {
            "email": "john@example.com",
            "age": 30,
            "active": True,
            "balance": 100.50,
        }
        masked = mask_dict(data)
        assert "***" in masked["email"]
        assert masked["age"] == 30
        assert masked["active"] is True
        assert masked["balance"] == 100.50
