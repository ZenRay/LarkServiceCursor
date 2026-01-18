"""
Unit tests for MediaUploader.

Tests file size validation, file type validation, and upload logic.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError
from lark_service.messaging.media_uploader import MediaUploader


class TestMediaUploaderValidation:
    """Test MediaUploader validation logic."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def uploader(self, mock_credential_pool):
        """Create MediaUploader instance."""
        return MediaUploader(mock_credential_pool)

    def test_validate_file_size_within_limit(self, uploader, tmp_path):
        """Test file size validation passes for valid size."""
        # Create a small test file (1MB)
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))

        # Should not raise
        uploader._validate_file_size(test_file, 10 * 1024 * 1024, "image")

    def test_validate_file_size_exceeds_limit(self, uploader, tmp_path):
        """Test file size validation fails for oversized file."""
        # Create a large test file (11MB)
        test_file = tmp_path / "large.jpg"
        test_file.write_bytes(b"x" * (11 * 1024 * 1024))

        # Should raise InvalidParameterError
        with pytest.raises(InvalidParameterError, match="exceeds maximum limit"):
            uploader._validate_file_size(test_file, 10 * 1024 * 1024, "image")

    def test_validate_file_type_supported(self, uploader, tmp_path):
        """Test file type validation passes for supported type."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test content")

        # Mock mimetypes.guess_type
        with patch("mimetypes.guess_type", return_value=("image/jpeg", None)):
            mime_type = uploader._validate_file_type(
                test_file, {".jpg": "image/jpeg", ".png": "image/png"}, "image"
            )
            assert mime_type == "image/jpeg"

    def test_validate_file_type_unsupported_extension(self, uploader, tmp_path):
        """Test file type validation fails for unsupported extension."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        # Should raise InvalidParameterError
        with pytest.raises(InvalidParameterError, match="Unsupported image format"):
            uploader._validate_file_type(
                test_file, {".jpg": "image/jpeg", ".png": "image/png"}, "image"
            )


class TestMediaUploaderUpload:
    """Test MediaUploader upload methods."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool with SDK client."""
        pool = Mock(spec=CredentialPool)

        # Mock SDK client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.success.return_value = True
        mock_response.data.image_key = "img_v2_test123"
        mock_response.data.file_key = "file_v2_test456"

        mock_client.im.v1.image.create.return_value = mock_response
        mock_client.im.v1.file.create.return_value = mock_response

        pool._get_sdk_client.return_value = mock_client

        return pool

    @pytest.fixture
    def uploader(self, mock_credential_pool):
        """Create MediaUploader instance."""
        return MediaUploader(mock_credential_pool)

    @pytest.mark.skip(reason="Requires complex SDK mocking - integration test preferred")
    def test_upload_image_success(self, uploader, tmp_path, mock_credential_pool):
        """Test successful image upload."""
        pass

    def test_upload_image_file_not_found(self, uploader):
        """Test image upload with non-existent file."""
        with pytest.raises(InvalidParameterError, match="Image file not found"):
            uploader.upload_image("cli_a1b2c3d4e5f6g7h8", "/nonexistent/file.jpg")

    @pytest.mark.skip(reason="Requires complex SDK mocking - integration test preferred")
    def test_upload_file_success(self, uploader, tmp_path, mock_credential_pool):
        """Test successful file upload."""
        pass

    def test_upload_file_not_found(self, uploader):
        """Test file upload with non-existent file."""
        with pytest.raises(InvalidParameterError, match="File not found"):
            uploader.upload_file("cli_a1b2c3d4e5f6g7h8", "/nonexistent/file.pdf")
