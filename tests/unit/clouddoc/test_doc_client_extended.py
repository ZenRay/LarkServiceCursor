"""
Extended tests for DocClient - adding coverage for uncovered methods.

Focus on: create, append, update, get operations and permission management.
"""

from unittest.mock import Mock
import pytest

from lark_service.clouddoc.client import DocClient
from lark_service.clouddoc.models import ContentBlock, Document
from lark_service.core.exceptions import InvalidParameterError, APIError


@pytest.fixture
def mock_credential_pool():
    """Create mock credential pool with SDK client."""
    pool = Mock()
    mock_client = Mock()
    mock_client.docx.v1.document.create.return_value = Mock(success=lambda: True, data=Mock(document=Mock(document_id="doc_123", title="Test")))
    mock_client.docx.v1.document.get.return_value = Mock(success=lambda: True, data=Mock(document=Mock(title="Doc", document_id="doc_123")))
    pool._get_sdk_client.return_value = mock_client
    pool.get_token.return_value = Mock(token_value="mock_token")
    return pool


@pytest.fixture
def doc_client(mock_credential_pool):
    """Create DocClient instance."""
    return DocClient(mock_credential_pool)


class TestDocClientCreateDocument:
    """Test create_document method."""

    def test_create_document_success(self, doc_client, mock_credential_pool):
        """Test successful document creation."""
        doc = doc_client.create_document(
            app_id="cli_test1234567890ab",
            title="Test Document",
        )

        assert doc is not None
        mock_credential_pool._get_sdk_client.assert_called()

    def test_create_document_with_folder(self, doc_client):
        """Test document creation in specific folder."""
        doc = doc_client.create_document(
            app_id="cli_test1234567890ab",
            title="Test",
            folder_token="fldcn1234567890ab",
        )

        assert doc is not None

    def test_create_document_invalid_title(self, doc_client):
        """Test create with invalid title."""
        with pytest.raises(InvalidParameterError):
            doc_client.create_document(
                app_id="cli_test1234567890ab",
                title="",
            )


class TestDocClientGetDocument:
    """Test get_document method."""

    def test_get_document_success(self, doc_client):
        """Test successful document retrieval."""
        doc = doc_client.get_document(
            app_id="cli_test1234567890ab",
            doc_id="doxcn1234567890abcdef",
        )

        assert doc is not None

    def test_get_document_invalid_id(self, doc_client):
        """Test get with invalid doc_id."""
        with pytest.raises(InvalidParameterError):
            doc_client.get_document(
                app_id="cli_test1234567890ab",
                doc_id="",
            )


class TestDocClientAppendContent:
    """Test append_content method."""

    def test_append_content_success(self, doc_client, mock_credential_pool):
        """Test successful content append."""
        # Mock API response
        mock_client = mock_credential_pool._get_sdk_client.return_value
        mock_response = Mock()
        mock_response.code = 0
        mock_response.msg = "success"

        import requests
        with pytest.mock.patch.object(requests, 'post', return_value=Mock(json=lambda: mock_response, status_code=200)):
            blocks = [ContentBlock(block_type="paragraph", content="Test content")]

            result = doc_client.append_content(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
                blocks=blocks,
            )

            assert result is not None

    def test_append_content_empty_blocks(self, doc_client):
        """Test append with empty blocks."""
        with pytest.raises(InvalidParameterError):
            doc_client.append_content(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
                blocks=[],
            )


class TestDocClientUpdateBlock:
    """Test update_block method."""

    def test_update_block_success(self, doc_client, mock_credential_pool):
        """Test successful block update."""
        import requests
        mock_response = Mock()
        mock_response.code = 0

        with pytest.mock.patch.object(requests, 'patch', return_value=Mock(json=lambda: mock_response, status_code=200)):
            result = doc_client.update_block(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
                block_id="block_123",
                content="Updated content",
            )

            assert result is not None

    def test_update_block_empty_content(self, doc_client):
        """Test update with empty content."""
        with pytest.raises(InvalidParameterError):
            doc_client.update_block(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
                block_id="block_123",
                content="",
            )


class TestDocClientPermissions:
    """Test permission management methods."""

    def test_grant_permission_success(self, doc_client, mock_credential_pool):
        """Test successful permission grant."""
        import requests
        mock_response = Mock()
        mock_response.code = 0

        with pytest.mock.patch.object(requests, 'post', return_value=Mock(json=lambda: mock_response, status_code=200)):
            result = doc_client.grant_permission(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
                member_type="user",
                member_id="ou_test123456789012",
                permission_type="read",
            )

            assert result is not None

    def test_revoke_permission_success(self, doc_client, mock_credential_pool):
        """Test successful permission revoke."""
        import requests
        mock_response = Mock()
        mock_response.code = 0

        with pytest.mock.patch.object(requests, 'delete', return_value=Mock(json=lambda: mock_response, status_code=200)):
            result = doc_client.revoke_permission(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
                member_type="user",
                member_id="ou_test123456789012",
            )

            assert result is not None

    def test_list_permissions_success(self, doc_client, mock_credential_pool):
        """Test successful permissions listing."""
        import requests
        mock_response = Mock()
        mock_response.code = 0
        mock_response.data = {"permissions": []}

        with pytest.mock.patch.object(requests, 'get', return_value=Mock(json=lambda: mock_response, status_code=200)):
            result = doc_client.list_permissions(
                app_id="cli_test1234567890ab",
                doc_id="doxcn1234567890abcdef",
            )

            assert result is not None
