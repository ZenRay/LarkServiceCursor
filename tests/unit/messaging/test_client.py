"""Unit tests for MessagingClient.

Tests message sending operations with mocked Lark SDK and media uploader.
Focus on: text/rich-text/image/file/card messages, batch sending, error handling.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lark_service.core.exceptions import InvalidParameterError, RetryableError
from lark_service.messaging.client import MessagingClient
from lark_service.messaging.models import ImageAsset

# === Mock Fixtures ===


@pytest.fixture
def mock_credential_pool() -> Mock:
    """Create mock CredentialPool."""
    pool = Mock()
    pool._get_sdk_client = Mock(return_value=Mock())
    return pool


@pytest.fixture
def mock_media_uploader() -> Mock:
    """Create mock MediaUploader."""
    uploader = Mock()
    # Mock upload_image returns ImageAsset-like object
    mock_asset = Mock(spec=ImageAsset)
    mock_asset.image_key = "img_v2_mock1234567890abcdef"
    uploader.upload_image.return_value = mock_asset

    # Mock upload_file returns FileAsset with file_key attribute
    mock_file_asset = Mock()
    mock_file_asset.file_key = "file_v2_mock1234567890abcdef"
    uploader.upload_file.return_value = mock_file_asset
    return uploader


@pytest.fixture
def mock_retry_strategy() -> Mock:
    """Create mock RetryStrategy."""
    strategy = Mock()

    # Mock execute method to directly call the function
    def execute_mock(func, *args, **kwargs):
        return func(*args, **kwargs)

    strategy.execute.side_effect = execute_mock
    return strategy


@pytest.fixture
def messaging_client(
    mock_credential_pool: Mock,
    mock_media_uploader: Mock,
    mock_retry_strategy: Mock,
) -> MessagingClient:
    """Create MessagingClient with mocked dependencies."""
    return MessagingClient(
        credential_pool=mock_credential_pool,
        media_uploader=mock_media_uploader,
        retry_strategy=mock_retry_strategy,
    )


# === Initialization Tests ===


class TestMessagingClientInitialization:
    """Test client initialization."""

    def test_init_with_all_params(
        self,
        mock_credential_pool: Mock,
        mock_media_uploader: Mock,
        mock_retry_strategy: Mock,
    ) -> None:
        """Test initialization with all parameters provided."""
        client = MessagingClient(
            credential_pool=mock_credential_pool,
            media_uploader=mock_media_uploader,
            retry_strategy=mock_retry_strategy,
        )

        assert client.credential_pool == mock_credential_pool
        assert client.media_uploader == mock_media_uploader
        assert client.retry_strategy == mock_retry_strategy

    def test_init_default_dependencies(self, mock_credential_pool: Mock) -> None:
        """Test initialization with default media_uploader and retry_strategy."""
        with (
            patch("lark_service.messaging.client.MediaUploader"),
            patch("lark_service.messaging.client.RetryStrategy"),
        ):
            client = MessagingClient(credential_pool=mock_credential_pool)

            assert client.credential_pool == mock_credential_pool
            assert client.media_uploader is not None
            assert client.retry_strategy is not None


# === send_text_message Tests ===


class TestSendTextMessage:
    """Test send_text_message method (US2.1: Text messaging)."""

    def test_send_text_message_success(self, messaging_client: MessagingClient) -> None:
        """Test successful text message send."""
        # Mock SDK response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_mock1234567890abcdef"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        result = messaging_client.send_text_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            content="Hello, World!",
        )

        assert result["message_id"] == "om_mock1234567890abcdef"
        mock_client.im.v1.message.create.assert_called_once()

    def test_send_text_message_empty_content(self, messaging_client: MessagingClient) -> None:
        """Test send_text_message with empty content raises error."""
        with pytest.raises(InvalidParameterError, match="Message content cannot be empty"):
            messaging_client.send_text_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
                content="",
            )

    def test_send_text_message_whitespace_only(self, messaging_client: MessagingClient) -> None:
        """Test send_text_message with whitespace-only content."""
        with pytest.raises(InvalidParameterError, match="Message content cannot be empty"):
            messaging_client.send_text_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
                content="   ",
            )

    def test_send_text_message_custom_receive_id_type(
        self, messaging_client: MessagingClient
    ) -> None:
        """Test send_text_message with custom receive_id_type."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_mock_chat_id"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        result = messaging_client.send_text_message(
            app_id="cli_test1234567890ab",
            receiver_id="oc_chatid12345678901",
            content="Hello, Chat!",
            receive_id_type="chat_id",
        )

        assert result["message_id"] == "om_mock_chat_id"


# === send_rich_text_message Tests ===


class TestSendRichTextMessage:
    """Test send_rich_text_message method."""

    def test_send_rich_text_message_success(self, messaging_client: MessagingClient) -> None:
        """Test successful rich text message send."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_rich_text_msg_123"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        rich_content = {
            "zh_cn": {
                "title": "通知",
                "content": [[{"tag": "text", "text": "重要提醒"}]],
            }
        }

        result = messaging_client.send_rich_text_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            content=rich_content,
        )

        assert result["message_id"] == "om_rich_text_msg_123"

    def test_send_rich_text_message_empty_content(self, messaging_client: MessagingClient) -> None:
        """Test send_rich_text_message with empty content."""
        with pytest.raises(InvalidParameterError, match="Rich text content cannot be empty"):
            messaging_client.send_rich_text_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
                content={},
            )


# === send_image_message Tests ===


class TestSendImageMessage:
    """Test send_image_message method (US2.2: Image messaging)."""

    def test_send_image_message_with_path(self, messaging_client: MessagingClient) -> None:
        """Test send_image_message with image_path (auto-upload)."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_image_msg_123"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        result = messaging_client.send_image_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            image_path="/tmp/test_image.jpg",
        )

        assert result["message_id"] == "om_image_msg_123"
        messaging_client.media_uploader.upload_image.assert_called_once_with(
            "cli_test1234567890ab", "/tmp/test_image.jpg"
        )

    def test_send_image_message_with_key(self, messaging_client: MessagingClient) -> None:
        """Test send_image_message with pre-uploaded image_key."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_image_msg_456"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        result = messaging_client.send_image_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            image_key="img_v2_existing_key_123",
        )

        assert result["message_id"] == "om_image_msg_456"
        # Should NOT call upload_image when image_key is provided
        messaging_client.media_uploader.upload_image.assert_not_called()

    def test_send_image_message_no_path_or_key(self, messaging_client: MessagingClient) -> None:
        """Test send_image_message with neither path nor key."""
        with pytest.raises(
            InvalidParameterError,
            match="Either image_path or image_key must be provided",
        ):
            messaging_client.send_image_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
            )


# === send_file_message Tests ===


class TestSendFileMessage:
    """Test send_file_message method (US2.3: File messaging)."""

    def test_send_file_message_with_path(self, messaging_client: MessagingClient) -> None:
        """Test send_file_message with file_path (auto-upload)."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_file_msg_123"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        result = messaging_client.send_file_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            file_path="/tmp/test_document.pdf",
        )

        assert result["message_id"] == "om_file_msg_123"
        messaging_client.media_uploader.upload_file.assert_called_once_with(
            "cli_test1234567890ab", "/tmp/test_document.pdf"
        )

    def test_send_file_message_with_key(self, messaging_client: MessagingClient) -> None:
        """Test send_file_message with pre-uploaded file_key."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_file_msg_456"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        result = messaging_client.send_file_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            file_key="file_v2_existing_key_789",
        )

        assert result["message_id"] == "om_file_msg_456"
        messaging_client.media_uploader.upload_file.assert_not_called()

    def test_send_file_message_no_path_or_key(self, messaging_client: MessagingClient) -> None:
        """Test send_file_message with neither path nor key."""
        with pytest.raises(
            InvalidParameterError,
            match="Either file_path or file_key must be provided",
        ):
            messaging_client.send_file_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
            )


# === send_card_message Tests ===


class TestSendCardMessage:
    """Test send_card_message method (US2.4: Interactive card messaging)."""

    def test_send_card_message_success(self, messaging_client: MessagingClient) -> None:
        """Test successful card message send."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_card_msg_123"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "卡片标题"}},
            "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "卡片内容"}}],
        }

        result = messaging_client.send_card_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            card_content=card_content,
        )

        assert result["message_id"] == "om_card_msg_123"

    def test_send_card_message_empty_content(self, messaging_client: MessagingClient) -> None:
        """Test send_card_message with empty card content."""
        with pytest.raises(InvalidParameterError, match="Card content cannot be empty"):
            messaging_client.send_card_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
                card_content={},
            )


# === send_batch_messages Tests ===


class TestSendBatchMessages:
    """Test send_batch_messages method (US2.6: Batch messaging)."""

    def test_send_batch_messages_all_success(self, messaging_client: MessagingClient) -> None:
        """Test batch send with all messages succeeding."""
        # Mock successful responses for all messages
        mock_response1 = Mock()
        mock_response1.success.return_value = True
        mock_response1.data = Mock()
        mock_response1.data.message_id = "om_batch_msg_1"

        mock_response2 = Mock()
        mock_response2.success.return_value = True
        mock_response2.data = Mock()
        mock_response2.data.message_id = "om_batch_msg_2"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.side_effect = [mock_response1, mock_response2]

        result = messaging_client.send_batch_messages(
            app_id="cli_test1234567890ab",
            receiver_ids=["ou_user1", "ou_user2"],
            msg_type="text",
            content={"text": "Batch message"},
        )

        assert result.total == 2
        assert result.success == 2
        assert result.failed == 0
        assert len(result.results) == 2
        assert result.results[0].status == "success"
        assert result.results[0].message_id == "om_batch_msg_1"

    def test_send_batch_messages_partial_failure(self, messaging_client: MessagingClient) -> None:
        """Test batch send with some messages failing."""
        # First succeeds, second fails
        mock_response_success = Mock()
        mock_response_success.success.return_value = True
        mock_response_success.data = Mock()
        mock_response_success.data.message_id = "om_batch_success"

        mock_response_fail = Mock()
        mock_response_fail.success.return_value = False
        mock_response_fail.code = 99991400
        mock_response_fail.msg = "Invalid receiver_id"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.side_effect = [
            mock_response_success,
            mock_response_fail,
        ]

        result = messaging_client.send_batch_messages(
            app_id="cli_test1234567890ab",
            receiver_ids=["ou_user1", "invalid"],
            msg_type="text",
            content={"text": "Batch message"},
        )

        assert result.total == 2
        assert result.success == 1
        assert result.failed == 1
        assert result.results[0].status == "success"
        assert result.results[1].status == "failed"
        assert "Invalid receiver_id" in result.results[1].error

    def test_send_batch_messages_empty_list(self, messaging_client: MessagingClient) -> None:
        """Test batch send with empty receiver list raises error."""
        with pytest.raises(InvalidParameterError, match="Receiver IDs list cannot be empty"):
            messaging_client.send_batch_messages(
                app_id="cli_test1234567890ab",
                receiver_ids=[],
                msg_type="text",
                content={"text": "Test"},
            )


# === _send_message Error Handling Tests ===


class TestSendMessageErrorHandling:
    """Test _send_message internal method error handling."""

    def test_send_message_api_failure(self, messaging_client: MessagingClient) -> None:
        """Test _send_message with API error response."""
        mock_response = Mock()
        mock_response.success.return_value = False
        mock_response.code = 99991400
        mock_response.msg = "Invalid parameter"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        with pytest.raises(RetryableError, match="Failed to send text message"):
            messaging_client.send_text_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
                content="Test message",
            )

    def test_send_message_exception(self, messaging_client: MessagingClient) -> None:
        """Test _send_message with SDK exception."""
        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            messaging_client.send_text_message(
                app_id="cli_test1234567890ab",
                receiver_id="ou_receiver123456789",
                content="Test message",
            )


# === Edge Cases ===


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_send_text_message_very_long_content(self, messaging_client: MessagingClient) -> None:
        """Test send_text_message with very long content."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_long_msg"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        long_content = "A" * 10000  # 10k characters

        result = messaging_client.send_text_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            content=long_content,
        )

        assert result["message_id"] == "om_long_msg"

    def test_send_image_message_with_pathlib_path(self, messaging_client: MessagingClient) -> None:
        """Test send_image_message with pathlib.Path object."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data = Mock()
        mock_response.data.message_id = "om_pathlib_img"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.return_value = mock_response

        image_path = Path("/tmp/test_image.png")

        result = messaging_client.send_image_message(
            app_id="cli_test1234567890ab",
            receiver_id="ou_receiver123456789",
            image_path=image_path,
        )

        assert result["message_id"] == "om_pathlib_img"
        messaging_client.media_uploader.upload_image.assert_called_once()

    def test_batch_send_handles_exception_in_single_message(
        self, messaging_client: MessagingClient
    ) -> None:
        """Test batch send continues when one message raises exception."""
        mock_response_success = Mock()
        mock_response_success.success.return_value = True
        mock_response_success.data = Mock()
        mock_response_success.data.message_id = "om_success"

        mock_client = messaging_client.credential_pool._get_sdk_client.return_value
        mock_client.im.v1.message.create.side_effect = [
            mock_response_success,
            Exception("Temporary network error"),
        ]

        result = messaging_client.send_batch_messages(
            app_id="cli_test1234567890ab",
            receiver_ids=["ou_user1", "ou_user2"],
            msg_type="text",
            content={"text": "Batch message"},
        )

        assert result.total == 2
        assert result.success == 1
        assert result.failed == 1
        assert result.results[0].status == "success"
        assert result.results[1].status == "failed"
        assert "network error" in result.results[1].error.lower()
