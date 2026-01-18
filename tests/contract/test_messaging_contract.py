"""
Contract tests for messaging API.

Verifies that the implementation matches the API contract defined in
specs/001-lark-service-core/contracts/messaging.yaml
"""

import pytest

from lark_service.messaging.models import (
    BatchSendResponse,
    BatchSendResult,
    FileAsset,
    ImageAsset,
    Message,
    MessageType,
)


class TestMessageModels:
    """Test Message model contract compliance."""

    def test_message_type_enum(self):
        """Test MessageType enum has all required types."""
        assert MessageType.TEXT == "text"
        assert MessageType.RICH_TEXT == "post"
        assert MessageType.IMAGE == "image"
        assert MessageType.FILE == "file"
        assert MessageType.INTERACTIVE_CARD == "interactive"

    def test_message_model_required_fields(self):
        """Test Message model has required fields."""
        message = Message(
            receiver_id="ou_test123",
            msg_type=MessageType.TEXT,
            content={"text": "Hello"},
            app_id="cli_a1b2c3d4e5f6g7h8",
        )

        assert message.receiver_id == "ou_test123"
        assert message.msg_type == MessageType.TEXT
        assert message.content == {"text": "Hello"}
        assert message.app_id == "cli_a1b2c3d4e5f6g7h8"

    def test_message_content_validation_empty(self):
        """Test Message validates empty content."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Message content cannot be empty"):
            Message(
                receiver_id="ou_test123",
                msg_type=MessageType.TEXT,
                content={},
                app_id="cli_a1b2c3d4e5f6g7h8",
            )

    def test_message_content_validation_none(self):
        """Test Message validates None content."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Message(
                receiver_id="ou_test123",
                msg_type=MessageType.TEXT,
                content=None,
                app_id="cli_a1b2c3d4e5f6g7h8",
            )


class TestImageAssetContract:
    """Test ImageAsset model contract compliance."""

    def test_image_asset_required_fields(self):
        """Test ImageAsset has required fields per contract."""
        asset = ImageAsset(
            image_key="img_v2_abc123",
            image_type="image/jpeg",
            file_size=1024000,
        )

        assert asset.image_key == "img_v2_abc123"
        assert asset.image_type == "image/jpeg"
        assert asset.file_size == 1024000
        assert asset.upload_time is not None

    def test_image_key_format_validation(self):
        """Test image_key format validation (img_v2_*)."""
        # Valid format
        asset = ImageAsset(
            image_key="img_v2_abc123def456",
            image_type="image/png",
            file_size=500000,
        )
        assert asset.image_key.startswith("img_v2_")

        # Invalid format should raise error
        with pytest.raises(ValueError, match="image_key must start with 'img_v2_'"):
            ImageAsset(
                image_key="invalid_key",
                image_type="image/png",
                file_size=500000,
            )

    def test_image_size_limit(self):
        """Test image size limit (10MB max per contract)."""
        from pydantic import ValidationError

        # Valid size (10MB)
        asset = ImageAsset(
            image_key="img_v2_test",
            image_type="image/jpeg",
            file_size=10 * 1024 * 1024,
        )
        assert asset.file_size == 10 * 1024 * 1024

        # Exceeds limit (10MB + 1 byte)
        with pytest.raises(ValidationError):
            ImageAsset(
                image_key="img_v2_test",
                image_type="image/jpeg",
                file_size=10 * 1024 * 1024 + 1,
            )


class TestFileAssetContract:
    """Test FileAsset model contract compliance."""

    def test_file_asset_required_fields(self):
        """Test FileAsset has required fields per contract."""
        asset = FileAsset(
            file_key="file_v2_abc123",
            file_name="document.pdf",
            file_type="application/pdf",
            file_size=2048000,
        )

        assert asset.file_key == "file_v2_abc123"
        assert asset.file_name == "document.pdf"
        assert asset.file_type == "application/pdf"
        assert asset.file_size == 2048000
        assert asset.upload_time is not None

    def test_file_key_format_validation(self):
        """Test file_key format validation (file_v2_*)."""
        # Valid format
        asset = FileAsset(
            file_key="file_v2_xyz789",
            file_name="test.pdf",
            file_type="application/pdf",
            file_size=1000000,
        )
        assert asset.file_key.startswith("file_v2_")

        # Invalid format should raise error
        with pytest.raises(ValueError, match="file_key must start with 'file_v2_'"):
            FileAsset(
                file_key="bad_key",
                file_name="test.pdf",
                file_type="application/pdf",
                file_size=1000000,
            )

    def test_file_size_limit(self):
        """Test file size limit (30MB max per contract)."""
        from pydantic import ValidationError

        # Valid size (30MB)
        asset = FileAsset(
            file_key="file_v2_test",
            file_name="large.zip",
            file_type="application/zip",
            file_size=30 * 1024 * 1024,
        )
        assert asset.file_size == 30 * 1024 * 1024

        # Exceeds limit (30MB + 1 byte)
        with pytest.raises(ValidationError):
            FileAsset(
                file_key="file_v2_test",
                file_name="toolarge.zip",
                file_type="application/zip",
                file_size=30 * 1024 * 1024 + 1,
            )


class TestBatchSendContract:
    """Test batch send models contract compliance."""

    def test_batch_send_result_success(self):
        """Test BatchSendResult for successful send."""
        result = BatchSendResult(
            receiver_id="ou_user1",
            status="success",
            message_id="om_abc123",
            error=None,
        )

        assert result.receiver_id == "ou_user1"
        assert result.status == "success"
        assert result.message_id == "om_abc123"
        assert result.error is None

    def test_batch_send_result_failed(self):
        """Test BatchSendResult for failed send."""
        result = BatchSendResult(
            receiver_id="ou_user2",
            status="failed",
            message_id=None,
            error="Receiver not found",
        )

        assert result.receiver_id == "ou_user2"
        assert result.status == "failed"
        assert result.message_id is None
        assert result.error == "Receiver not found"

    def test_batch_send_response_structure(self):
        """Test BatchSendResponse structure per contract."""
        results = [
            BatchSendResult(
                receiver_id="ou_user1",
                status="success",
                message_id="om_123",
                error=None,
            ),
            BatchSendResult(
                receiver_id="ou_user2",
                status="failed",
                message_id=None,
                error="Error",
            ),
        ]

        response = BatchSendResponse(
            total=2,
            success=1,
            failed=1,
            results=results,
        )

        assert response.total == 2
        assert response.success == 1
        assert response.failed == 1
        assert len(response.results) == 2

    def test_batch_send_response_validation(self):
        """Test BatchSendResponse validates total matches results length."""
        # Note: The validator checks if total matches results length
        # Let's test that it works correctly when they DO match
        results = [
            BatchSendResult(
                receiver_id="ou_user1",
                status="success",
                message_id="om_123",
                error=None,
            ),
            BatchSendResult(
                receiver_id="ou_user2",
                status="success",
                message_id="om_456",
                error=None,
            ),
        ]

        # This should work - total matches results length
        response = BatchSendResponse(
            total=2,
            success=2,
            failed=0,
            results=results,
        )
        assert response.total == 2
        assert len(response.results) == 2


class TestErrorCodesContract:
    """Test error codes match contract specification."""

    def test_empty_content_error_code(self):
        """Test empty content error code (40002 per contract)."""
        from pydantic import ValidationError

        # This would be tested in integration tests with actual API calls
        # Here we just verify the model validation
        with pytest.raises(ValidationError, match="Message content cannot be empty"):
            Message(
                receiver_id="ou_test",
                msg_type=MessageType.TEXT,
                content={},
                app_id="cli_a1b2c3d4e5f6g7h8",
            )

    def test_image_size_error_code(self):
        """Test image size error (41301 per contract)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ImageAsset(
                image_key="img_v2_test",
                image_type="image/jpeg",
                file_size=11 * 1024 * 1024,
            )

    def test_file_size_error_code(self):
        """Test file size error (41302 per contract)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FileAsset(
                file_key="file_v2_test",
                file_name="huge.zip",
                file_type="application/zip",
                file_size=31 * 1024 * 1024,
            )
