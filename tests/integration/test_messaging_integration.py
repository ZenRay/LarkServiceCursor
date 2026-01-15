"""
Integration tests for Messaging module.

Tests the integration between MessagingClient, MediaUploader, and CredentialPool.
These tests use mocks for external API calls but verify the internal integration.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError
from lark_service.messaging.client import MessagingClient
from lark_service.messaging.lifecycle import MessageLifecycleManager
from lark_service.messaging.media_uploader import MediaUploader


@pytest.fixture
def mock_credential_pool():
    """Create mock credential pool with SDK client."""
    pool = Mock(spec=CredentialPool)
    
    # Mock SDK client
    mock_client = MagicMock()
    
    # Mock message send response
    mock_send_response = MagicMock()
    mock_send_response.success.return_value = True
    mock_send_response.data.message_id = "om_test_message_123"
    mock_send_response.data.create_time = "1642512345"
    mock_client.im.v1.message.create.return_value = mock_send_response
    
    # Mock message delete response
    mock_delete_response = MagicMock()
    mock_delete_response.success.return_value = True
    mock_client.im.v1.message.delete.return_value = mock_delete_response
    
    # Mock message patch response
    mock_patch_response = MagicMock()
    mock_patch_response.success.return_value = True
    mock_client.im.v1.message.patch.return_value = mock_patch_response
    
    # Mock message reply response
    mock_reply_response = MagicMock()
    mock_reply_response.success.return_value = True
    mock_reply_response.data.message_id = "om_reply_message_456"
    mock_reply_response.data.create_time = "1642512400"
    mock_client.im.v1.message.reply.return_value = mock_reply_response
    
    # Mock image upload response
    mock_image_response = MagicMock()
    mock_image_response.success.return_value = True
    mock_image_response.data.image_key = "img_v2_test_abc123"
    mock_client.im.v1.image.create.return_value = mock_image_response
    
    # Mock file upload response
    mock_file_response = MagicMock()
    mock_file_response.success.return_value = True
    mock_file_response.data.file_key = "file_v2_test_xyz789"
    mock_client.im.v1.file.create.return_value = mock_file_response
    
    pool._get_sdk_client.return_value = mock_client
    
    return pool


@pytest.fixture
def messaging_client(mock_credential_pool):
    """Create MessagingClient with mocked dependencies."""
    return MessagingClient(mock_credential_pool)


@pytest.fixture
def lifecycle_manager(mock_credential_pool):
    """Create MessageLifecycleManager with mocked dependencies."""
    return MessageLifecycleManager(mock_credential_pool)


class TestMessagingClientIntegration:
    """Integration tests for MessagingClient."""

    def test_send_text_message_integration(self, messaging_client):
        """Test sending text message with full integration."""
        response = messaging_client.send_text_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            content="Hello, integration test!"
        )
        
        assert response["message_id"] == "om_test_message_123"
        assert response["msg_type"] == "text"
        assert response["receiver_id"] == "ou_test_user"

    def test_send_rich_text_message_integration(self, messaging_client):
        """Test sending rich text message with full integration."""
        content = {
            "zh_cn": {
                "title": "测试通知",
                "content": [
                    [{"tag": "text", "text": "这是一条测试消息"}]
                ]
            }
        }
        
        response = messaging_client.send_rich_text_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            content=content
        )
        
        assert response["message_id"] == "om_test_message_123"
        assert response["msg_type"] == "post"

    def test_send_image_message_with_key_integration(self, messaging_client):
        """Test sending image message with pre-uploaded key."""
        response = messaging_client.send_image_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            image_key="img_v2_existing_key"
        )
        
        assert response["message_id"] == "om_test_message_123"
        assert response["msg_type"] == "image"

    def test_send_file_message_with_key_integration(self, messaging_client):
        """Test sending file message with pre-uploaded key."""
        response = messaging_client.send_file_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            file_key="file_v2_existing_key"
        )
        
        assert response["message_id"] == "om_test_message_123"
        assert response["msg_type"] == "file"

    def test_send_card_message_integration(self, messaging_client):
        """Test sending card message with full integration."""
        card_content = {
            "header": {
                "title": {"tag": "plain_text", "content": "测试卡片"}
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": "卡片内容"}}
            ]
        }
        
        response = messaging_client.send_card_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            card_content=card_content
        )
        
        assert response["message_id"] == "om_test_message_123"
        assert response["msg_type"] == "interactive"

    def test_batch_send_messages_integration(self, messaging_client):
        """Test batch sending messages with full integration."""
        receiver_ids = ["ou_user1", "ou_user2", "ou_user3"]
        
        response = messaging_client.send_batch_messages(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_ids=receiver_ids,
            msg_type="text",
            content={"text": "批量消息"}
        )
        
        assert response.total == 3
        assert response.success == 3
        assert response.failed == 0
        assert len(response.results) == 3
        
        for result in response.results:
            assert result.status == "success"
            assert result.message_id == "om_test_message_123"

    def test_batch_send_with_partial_failure_integration(self, messaging_client, mock_credential_pool):
        """Test batch sending with some failures."""
        # Mock one failure
        mock_client = mock_credential_pool._get_sdk_client.return_value
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            response = MagicMock()
            if call_count[0] == 2:  # Second call fails
                response.success.return_value = False
                response.msg = "User not found"
                response.code = 40003
            else:
                response.success.return_value = True
                response.data.message_id = "om_test_message_123"
                response.data.create_time = "1642512345"
            return response
        
        mock_client.im.v1.message.create.side_effect = side_effect
        
        receiver_ids = ["ou_user1", "ou_user2", "ou_user3"]
        
        response = messaging_client.send_batch_messages(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_ids=receiver_ids,
            msg_type="text",
            content={"text": "批量消息"},
            continue_on_error=True
        )
        
        assert response.total == 3
        assert response.success == 2
        assert response.failed == 1
        
        # Check failed result
        failed_results = [r for r in response.results if r.status == "failed"]
        assert len(failed_results) == 1
        assert failed_results[0].receiver_id == "ou_user2"

    def test_send_empty_content_error(self, messaging_client):
        """Test sending message with empty content raises error."""
        with pytest.raises(InvalidParameterError, match="cannot be empty"):
            messaging_client.send_text_message(
                app_id="cli_a1b2c3d4e5f6g7h8",
                receiver_id="ou_test_user",
                content=""
            )

    def test_send_image_without_path_or_key_error(self, messaging_client):
        """Test sending image without path or key raises error."""
        with pytest.raises(InvalidParameterError, match="must be provided"):
            messaging_client.send_image_message(
                app_id="cli_a1b2c3d4e5f6g7h8",
                receiver_id="ou_test_user"
            )


class TestMessageLifecycleIntegration:
    """Integration tests for MessageLifecycleManager."""

    def test_recall_message_integration(self, lifecycle_manager):
        """Test recalling message with full integration."""
        result = lifecycle_manager.recall_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            message_id="om_test_message_123"
        )
        
        assert result["success"] is True
        assert result["message_id"] == "om_test_message_123"

    def test_edit_message_integration(self, lifecycle_manager):
        """Test editing message with full integration."""
        result = lifecycle_manager.edit_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            message_id="om_test_message_123",
            content="Updated content"
        )
        
        assert result["success"] is True
        assert result["message_id"] == "om_test_message_123"

    def test_reply_message_integration(self, lifecycle_manager):
        """Test replying to message with full integration."""
        result = lifecycle_manager.reply_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            message_id="om_test_message_123",
            msg_type="text",
            content={"text": "Reply content"}
        )
        
        assert result["reply_message_id"] == "om_reply_message_456"
        assert result["original_message_id"] == "om_test_message_123"
        assert result["msg_type"] == "text"

    def test_recall_empty_message_id_error(self, lifecycle_manager):
        """Test recalling with empty message ID raises error."""
        with pytest.raises(InvalidParameterError, match="cannot be empty"):
            lifecycle_manager.recall_message(
                app_id="cli_a1b2c3d4e5f6g7h8",
                message_id=""
            )

    def test_edit_empty_content_error(self, lifecycle_manager):
        """Test editing with empty content raises error."""
        with pytest.raises(InvalidParameterError, match="cannot be empty"):
            lifecycle_manager.edit_message(
                app_id="cli_a1b2c3d4e5f6g7h8",
                message_id="om_test_message_123",
                content=""
            )


class TestMediaUploaderIntegration:
    """Integration tests for MediaUploader."""

    @pytest.fixture
    def media_uploader(self, mock_credential_pool):
        """Create MediaUploader with mocked dependencies."""
        return MediaUploader(mock_credential_pool)

    def test_upload_image_file_not_found(self, media_uploader):
        """Test uploading non-existent image file."""
        with pytest.raises(InvalidParameterError, match="not found"):
            media_uploader.upload_image(
                app_id="cli_a1b2c3d4e5f6g7h8",
                image_path="/nonexistent/image.jpg"
            )

    def test_upload_file_not_found(self, media_uploader):
        """Test uploading non-existent file."""
        with pytest.raises(InvalidParameterError, match="not found"):
            media_uploader.upload_file(
                app_id="cli_a1b2c3d4e5f6g7h8",
                file_path="/nonexistent/file.pdf"
            )

    def test_validate_file_size_exceeds_limit(self, media_uploader, tmp_path):
        """Test file size validation with oversized file."""
        # Create a large file (11MB)
        large_file = tmp_path / "large.jpg"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))
        
        with pytest.raises(InvalidParameterError, match="exceeds maximum"):
            media_uploader._validate_file_size(
                large_file,
                10 * 1024 * 1024,
                "image"
            )

    def test_validate_unsupported_file_type(self, media_uploader, tmp_path):
        """Test file type validation with unsupported type."""
        # Create a text file
        text_file = tmp_path / "test.txt"
        text_file.write_text("test content")
        
        with pytest.raises(InvalidParameterError, match="Unsupported"):
            media_uploader._validate_file_type(
                text_file,
                {".jpg": "image/jpeg", ".png": "image/png"},
                "image"
            )


class TestEndToEndScenarios:
    """End-to-end integration tests for common scenarios."""

    def test_send_message_and_recall_scenario(self, messaging_client, lifecycle_manager):
        """Test complete scenario: send message then recall it."""
        # Step 1: Send message
        send_response = messaging_client.send_text_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            content="Test message"
        )
        message_id = send_response["message_id"]
        
        # Step 2: Recall message
        recall_response = lifecycle_manager.recall_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            message_id=message_id
        )
        
        assert recall_response["success"] is True
        assert recall_response["message_id"] == message_id

    def test_send_message_and_edit_scenario(self, messaging_client, lifecycle_manager):
        """Test complete scenario: send message then edit it."""
        # Step 1: Send message
        send_response = messaging_client.send_text_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            content="Original content"
        )
        message_id = send_response["message_id"]
        
        # Step 2: Edit message
        edit_response = lifecycle_manager.edit_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            message_id=message_id,
            content="Updated content"
        )
        
        assert edit_response["success"] is True
        assert edit_response["message_id"] == message_id

    def test_send_message_and_reply_scenario(self, messaging_client, lifecycle_manager):
        """Test complete scenario: send message then reply to it."""
        # Step 1: Send original message
        send_response = messaging_client.send_text_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_id="ou_test_user",
            content="Original message"
        )
        message_id = send_response["message_id"]
        
        # Step 2: Reply to message
        reply_response = lifecycle_manager.reply_message(
            app_id="cli_a1b2c3d4e5f6g7h8",
            message_id=message_id,
            msg_type="text",
            content={"text": "Reply to original"}
        )
        
        assert reply_response["original_message_id"] == message_id
        assert reply_response["reply_message_id"] == "om_reply_message_456"

    def test_batch_send_to_multiple_users_scenario(self, messaging_client):
        """Test complete scenario: batch send to multiple users."""
        receiver_ids = [f"ou_user{i}" for i in range(1, 11)]  # 10 users
        
        response = messaging_client.send_batch_messages(
            app_id="cli_a1b2c3d4e5f6g7h8",
            receiver_ids=receiver_ids,
            msg_type="text",
            content={"text": "Batch notification"}
        )
        
        assert response.total == 10
        assert response.success == 10
        assert response.failed == 0
        assert all(r.status == "success" for r in response.results)
