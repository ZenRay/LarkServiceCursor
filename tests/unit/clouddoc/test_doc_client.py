"""
Unit tests for DocClient.

Tests document operations including create, append, get, update, and permissions.
"""

from unittest.mock import Mock

import pytest

from lark_service.clouddoc.client import DocClient
from lark_service.clouddoc.models import ContentBlock
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, NotFoundError, PermissionDeniedError


class TestDocClientValidation:
    """Test DocClient validation logic."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    def test_create_document_empty_title(self, client):
        """Test create document fails with empty title."""
        with pytest.raises(InvalidParameterError, match="Invalid title length"):
            client.create_document(
                app_id="cli_test",
                title="",
            )

    def test_create_document_title_too_long(self, client):
        """Test create document fails with title exceeding 255 chars."""
        long_title = "x" * 256
        with pytest.raises(InvalidParameterError, match="Invalid title length"):
            client.create_document(
                app_id="cli_test",
                title=long_title,
            )

    def test_append_content_empty_blocks(self, client):
        """Test append content fails with empty blocks."""
        with pytest.raises(InvalidParameterError, match="Blocks cannot be empty"):
            client.append_content(
                app_id="cli_test",
                doc_id="doxcn123",
                blocks=[],
            )

    def test_append_content_too_many_blocks(self, client):
        """Test append content fails with more than 100 blocks."""
        blocks = [ContentBlock(block_type="paragraph", content=f"Block {i}") for i in range(101)]
        with pytest.raises(InvalidParameterError, match="Too many blocks"):
            client.append_content(
                app_id="cli_test",
                doc_id="doxcn123",
                blocks=blocks,
            )

    def test_grant_permission_invalid_member_type(self, client):
        """Test grant permission fails with invalid member type."""
        with pytest.raises(InvalidParameterError, match="Invalid member_type"):
            client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn123",
                member_type="invalid",
                member_id="ou_xxx",
                permission_type="read",
            )

    def test_grant_permission_invalid_permission_type(self, client):
        """Test grant permission fails with invalid permission type."""
        with pytest.raises(InvalidParameterError, match="Invalid permission_type"):
            client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn123",
                member_type="user",
                member_id="ou_xxx",
                permission_type="invalid",
            )


class TestDocClientOperations:
    """Test DocClient operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool with SDK client."""
        pool = Mock(spec=CredentialPool)

        # Mock SDK client
        mock_sdk_client = Mock()
        pool._get_sdk_client.return_value = mock_sdk_client

        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    def test_create_document_success(self, client, mock_credential_pool):
        """Test create document succeeds."""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.document.document_id = "doxcn123"
        mock_response.data.document.title = "Test Document"

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document.create.return_value = mock_response

        # Create document
        doc = client.create_document(
            app_id="cli_test",
            title="Test Document",
        )

        # Verify result
        assert doc.doc_id == "doxcn123"
        assert doc.title == "Test Document"

    def test_create_document_permission_denied(self, client, mock_credential_pool):
        """Test create document fails with permission denied."""
        # Mock permission denied response
        mock_response = Mock()
        mock_response.success.return_value = False
        mock_response.code = 403
        mock_response.msg = "Permission denied"

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document.create.return_value = mock_response

        # Should raise PermissionDeniedError
        with pytest.raises(PermissionDeniedError):
            client.create_document(
                app_id="cli_test",
                title="Test Document",
            )

    def test_get_document_content_success(self, client, mock_credential_pool):
        """Test get document content succeeds."""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.document.document_id = "doxcn123"
        mock_response.data.document.title = "Test Document"

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document.get.return_value = mock_response

        # Get document
        doc = client.get_document_content(
            app_id="cli_test",
            doc_id="doxcn123",
        )

        # Verify result
        assert doc.doc_id == "doxcn123"
        assert doc.title == "Test Document"

    def test_get_document_content_not_found(self, client, mock_credential_pool):
        """Test get document content fails when document not found."""
        # Mock not found response
        mock_response = Mock()
        mock_response.success.return_value = False
        mock_response.code = 404
        mock_response.msg = "Document not found"

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document.get.return_value = mock_response

        # Should raise NotFoundError
        with pytest.raises(NotFoundError, match="Document not found"):
            client.get_document_content(
                app_id="cli_test",
                doc_id="doxcn123",
            )

    def test_update_block_success(self, client, mock_credential_pool):
        """Test update block succeeds."""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document_block.update.return_value = mock_response

        # Update block
        block = ContentBlock(
            block_id="blk123",
            block_type="paragraph",
            content="Updated content",
        )
        result = client.update_block(
            app_id="cli_test",
            doc_id="doxcn123",
            block_id="blk123",
            block=block,
        )

        # Verify result
        assert result is True

    def test_update_block_not_found(self, client, mock_credential_pool):
        """Test update block fails when block not found."""
        # Mock not found response
        mock_response = Mock()
        mock_response.success.return_value = False
        mock_response.code = 404
        mock_response.msg = "Block not found"

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document_block.update.return_value = mock_response

        # Should raise NotFoundError
        block = ContentBlock(
            block_id="blk123",
            block_type="paragraph",
            content="Updated content",
        )
        with pytest.raises(NotFoundError, match="Block not found"):
            client.update_block(
                app_id="cli_test",
                doc_id="doxcn123",
                block_id="blk123",
                block=block,
            )


class TestDocClientPermissions:
    """Test DocClient permission operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    def test_grant_permission_valid_types(self, client):
        """Test grant permission with all valid types."""
        # Test all valid member types
        for member_type in ["user", "department", "group", "public"]:
            perm = client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn123",
                member_type=member_type,
                member_id="test_id" if member_type != "public" else "",
                permission_type="read",
            )
            assert perm.member_type == member_type
            assert perm.permission_type == "read"

        # Test all valid permission types
        for perm_type in ["read", "write", "comment", "manage"]:
            perm = client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn123",
                member_type="user",
                member_id="ou_xxx",
                permission_type=perm_type,
            )
            assert perm.permission_type == perm_type

    def test_revoke_permission_success(self, client):
        """Test revoke permission succeeds."""
        result = client.revoke_permission(
            app_id="cli_test",
            doc_id="doxcn123",
            permission_id="perm123",
        )
        assert result is True

    def test_list_permissions_success(self, client):
        """Test list permissions succeeds."""
        perms = client.list_permissions(
            app_id="cli_test",
            doc_id="doxcn123",
        )
        assert isinstance(perms, list)
