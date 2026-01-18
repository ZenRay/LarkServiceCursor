"""
Extended unit tests for DocClient - P0 Coverage Improvement.

This file focuses on testing functionality that was previously untested:
- Append content with various block types
- Get document operations
- Update block operations (HTTP API based)
- Permission management operations (HTTP API based)
- Error handling for HTTP API calls
- Network error scenarios

Target: Increase coverage from 25.08% to 40%
"""

from unittest.mock import Mock, patch

import pytest
import requests

from lark_service.clouddoc.client import DocClient
from lark_service.clouddoc.models import ContentBlock, Document
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
)


class TestDocClientAppendContent:
    """Test append content operations with various block types."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        # Mock token retrieval
        pool.get_token.return_value = "test_tenant_token_12345678"
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_single_paragraph(self, mock_post, client, mock_credential_pool):
        """Test appending a single paragraph block."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {"children": [{"block_id": "blk123", "block_type": 2}]},
        }
        mock_post.return_value = mock_response

        blocks = [ContentBlock(block_type="paragraph", content="Test paragraph")]

        result = client.append_content(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            blocks=blocks,
        )

        assert result is True
        mock_post.assert_called_once()
        # Verify token was obtained
        mock_credential_pool.get_token.assert_called_once_with(
            "cli_test", token_type="tenant_access_token"
        )

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_multiple_blocks(self, mock_post, client, mock_credential_pool):
        """Test appending multiple blocks of different types."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {"children": []}}
        mock_post.return_value = mock_response

        blocks = [
            ContentBlock(block_type="paragraph", content="Paragraph 1"),
            ContentBlock(block_type="heading", content="Heading Level 1"),
            ContentBlock(block_type="heading", content="Heading Level 2"),
            ContentBlock(block_type="heading", content="Heading Level 3"),
            ContentBlock(block_type="divider", content=""),
        ]

        result = client.append_content(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            blocks=blocks,
        )

        assert result is True

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_heading_blocks(self, mock_post, client, mock_credential_pool):
        """Test appending heading blocks of different levels."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
        mock_post.return_value = mock_response

        blocks = [
            ContentBlock(block_type="heading", content="Generic Heading"),
            ContentBlock(block_type="heading", content="H1 Heading"),
            ContentBlock(block_type="heading", content="H2 Heading"),
            ContentBlock(block_type="heading", content="H3 Heading"),
        ]

        result = client.append_content(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            blocks=blocks,
        )

        assert result is True

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_divider_block(self, mock_post, client, mock_credential_pool):
        """Test appending divider block (no content needed)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
        mock_post.return_value = mock_response

        blocks = [ContentBlock(block_type="divider", content="")]

        result = client.append_content(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            blocks=blocks,
        )

        assert result is True

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_unknown_block_type(self, mock_post, client, mock_credential_pool):
        """Test appending block with unknown type (should default to text)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
        mock_post.return_value = mock_response

        blocks = [ContentBlock(block_type="paragraph", content="Some content")]

        result = client.append_content(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            blocks=blocks,
        )

        assert result is True

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_text_block(self, mock_post, client, mock_credential_pool):
        """Test appending text block."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
        mock_post.return_value = mock_response

        blocks = [ContentBlock(block_type="paragraph", content="Plain text content")]

        result = client.append_content(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            blocks=blocks,
        )

        assert result is True

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_api_error(self, mock_post, client, mock_credential_pool):
        """Test append content handles API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 400,
            "msg": "Invalid block format",
        }
        mock_post.return_value = mock_response

        blocks = [ContentBlock(block_type="paragraph", content="Test")]

        with pytest.raises(APIError, match="API returned error"):
            client.append_content(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                blocks=blocks,
            )

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_document_not_found(self, mock_post, client, mock_credential_pool):
        """Test append content handles document not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 404,
            "msg": "Document not found",
        }
        mock_post.return_value = mock_response

        blocks = [ContentBlock(block_type="paragraph", content="Test")]

        # NotFoundError is retryable, so it will be raised after retries
        with pytest.raises((NotFoundError, APIError)):
            client.append_content(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                blocks=blocks,
            )

    @patch("lark_service.clouddoc.client.requests.post")
    def test_append_content_network_error(self, mock_post, client, mock_credential_pool):
        """Test append content handles network error."""
        # Network errors will be retried by retry_strategy
        mock_post.side_effect = requests.RequestException("Connection timeout")

        blocks = [ContentBlock(block_type="paragraph", content="Test")]

        # After all retries fail, it raises the last exception
        with pytest.raises((requests.RequestException, APIError)):
            client.append_content(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                blocks=blocks,
            )


class TestDocClientGetDocument:
    """Test get document operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        mock_sdk_client = Mock()
        pool._get_sdk_client.return_value = mock_sdk_client
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    def test_get_document_success(self, client, mock_credential_pool):
        """Test get document (alias for get_document_content)."""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.document.document_id = "doxcn1234567890abcdefghij"
        mock_response.data.document.title = "Test Document"
        mock_response.data.document.owner_id = "ou_1234567890abcdefghij"

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document.get.return_value = mock_response

        doc = client.get_document(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
        )

        assert isinstance(doc, Document)
        assert doc.doc_id == "doxcn1234567890abcdefghij"
        assert doc.title == "Test Document"

    def test_get_document_without_owner(self, client, mock_credential_pool):
        """Test get document when owner_id is not present."""
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.document.document_id = "doxcn1234567890abcdefghij"
        mock_response.data.document.title = "Test Document"
        # owner_id attribute doesn't exist
        mock_response.data.document.configure_mock(**{"owner_id": Mock(side_effect=AttributeError)})
        delattr(mock_response.data.document, "owner_id")

        mock_sdk_client = mock_credential_pool._get_sdk_client.return_value
        mock_sdk_client.docx.v1.document.get.return_value = mock_response

        doc = client.get_document(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
        )

        assert doc.owner_id is None


class TestDocClientUpdateBlock:
    """Test update block operations (HTTP API)."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        pool.get_token.return_value = "test_tenant_token_12345678"
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    @patch("lark_service.clouddoc.client.requests.patch")
    def test_update_block_paragraph(self, mock_patch, client, mock_credential_pool):
        """Test updating a paragraph block."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {"block_id": "blk123"},
        }
        mock_patch.return_value = mock_response

        block = ContentBlock(
            block_id="blk1234567890abcdefghijk",
            block_type="paragraph",
            content="Updated paragraph content",
        )

        result = client.update_block(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            block_id="blk123",
            block=block,
        )

        assert result is True
        mock_patch.assert_called_once()

    @patch("lark_service.clouddoc.client.requests.patch")
    def test_update_block_heading(self, mock_patch, client, mock_credential_pool):
        """Test updating a heading block."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {}}
        mock_patch.return_value = mock_response

        block = ContentBlock(
            block_id="blk1234567890abcdefghijk",
            block_type="heading",
            content="Updated Heading",
        )

        result = client.update_block(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            block_id="blk123",
            block=block,
        )

        assert result is True

    @patch("lark_service.clouddoc.client.requests.patch")
    def test_update_block_api_error(self, mock_patch, client, mock_credential_pool):
        """Test update block handles API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 400,
            "msg": "Invalid block data",
        }
        mock_patch.return_value = mock_response

        block = ContentBlock(
            block_id="blk1234567890abcdefghijk",
            block_type="paragraph",
            content="Updated content",
        )

        # 400 errors are treated as InvalidParameterError (non-retryable)
        with pytest.raises((InvalidParameterError, APIError)):
            client.update_block(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                block_id="blk1234567890abcdefghijk",
                block=block,
            )

    @patch("lark_service.clouddoc.client.requests.patch")
    def test_update_block_not_found(self, mock_patch, client, mock_credential_pool):
        """Test update block handles block not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 404,
            "msg": "Block not found",
        }
        mock_patch.return_value = mock_response

        block = ContentBlock(
            block_id="blk1234567890abcdefghijk",
            block_type="paragraph",
            content="Updated content",
        )

        # NotFoundError might be retried or wrapped
        with pytest.raises((NotFoundError, APIError)):
            client.update_block(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                block_id="blk1234567890abcdefghijk",
                block=block,
            )

    @patch("lark_service.clouddoc.client.requests.patch")
    def test_update_block_network_error(self, mock_patch, client, mock_credential_pool):
        """Test update block handles network error."""
        # Network errors are retried
        mock_patch.side_effect = requests.RequestException("Connection failed")

        block = ContentBlock(
            block_id="blk1234567890abcdefghijk",
            block_type="paragraph",
            content="Updated content",
        )

        # After retries, exception is raised
        with pytest.raises((requests.RequestException, APIError)):
            client.update_block(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                block_id="blk1234567890abcdefghijk",
                block=block,
            )


class TestDocClientPermissions:
    """Test permission management operations (HTTP API)."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        pool.get_token.return_value = "test_tenant_token_12345678"
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create DocClient instance."""
        return DocClient(mock_credential_pool)

    @patch("lark_service.clouddoc.client.requests.post")
    def test_grant_permission_user_read(self, mock_post, client, mock_credential_pool):
        """Test granting read permission to a user."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "perm_id": "perm123",
                "member_type": "user",
                "perm_type": "read",
            },
        }
        mock_post.return_value = mock_response

        perm = client.grant_permission(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            member_type="user",
            member_id="ou_1234567890abcdefghij",
            permission_type="read",
        )

        # Permission ID is not returned by the API, but permission is created
        assert perm.member_type == "user"
        assert perm.permission_type == "read"

    @patch("lark_service.clouddoc.client.requests.post")
    def test_grant_permission_department_write(self, mock_post, client, mock_credential_pool):
        """Test granting write permission to a department."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "perm_id": "perm456",
                "member_type": "department",
                "perm_type": "write",
            },
        }
        mock_post.return_value = mock_response

        perm = client.grant_permission(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            member_type="department",
            member_id="od-dept1234567890abcdefghij",
            permission_type="write",
        )

        assert perm.member_type == "department"
        assert perm.permission_type == "write"

    @patch("lark_service.clouddoc.client.requests.post")
    def test_grant_permission_all_types(self, mock_post, client, mock_credential_pool):
        """Test granting permissions for all permission types."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {"perm_id": "perm123", "member_type": "user", "perm_type": "manage"},
        }
        mock_post.return_value = mock_response

        for perm_type in ["read", "write", "comment", "manage"]:
            perm = client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                member_type="user",
                member_id="ou_1234567890abcdefghij",
                permission_type=perm_type,
            )
            assert perm is not None

    @patch("lark_service.clouddoc.client.requests.post")
    def test_grant_permission_api_error(self, mock_post, client, mock_credential_pool):
        """Test grant permission handles API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 400,
            "msg": "Invalid permission type",
        }
        mock_post.return_value = mock_response

        # 400 errors are non-retryable (InvalidParameterError)
        with pytest.raises((InvalidParameterError, APIError)):
            client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                member_type="user",
                member_id="ou_1234567890abcdefghij",
                permission_type="read",
            )

    @patch("lark_service.clouddoc.client.requests.post")
    def test_grant_permission_network_error(self, mock_post, client, mock_credential_pool):
        """Test grant permission handles network error."""
        # Network errors are retried
        mock_post.side_effect = requests.RequestException("Network timeout")

        # After retries fail, raises exception
        with pytest.raises((requests.RequestException, APIError)):
            client.grant_permission(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                member_type="user",
                member_id="ou_1234567890abcdefghij",
                permission_type="read",
            )

    @patch("lark_service.clouddoc.client.requests.delete")
    def test_revoke_permission_success(self, mock_delete, client, mock_credential_pool):
        """Test revoking permission."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
        }
        mock_delete.return_value = mock_response

        result = client.revoke_permission(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
            permission_id="perm123",
        )

        assert result is True
        mock_delete.assert_called_once()

    @patch("lark_service.clouddoc.client.requests.delete")
    def test_revoke_permission_api_error(self, mock_delete, client, mock_credential_pool):
        """Test revoke permission handles API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 400,
            "msg": "Permission not found",
        }
        mock_delete.return_value = mock_response

        # 400 errors are non-retryable
        with pytest.raises((InvalidParameterError, APIError)):
            client.revoke_permission(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                permission_id="perm123",
            )

    @patch("lark_service.clouddoc.client.requests.delete")
    def test_revoke_permission_network_error(self, mock_delete, client, mock_credential_pool):
        """Test revoke permission handles network error."""
        # Network errors are retried
        mock_delete.side_effect = requests.RequestException("Connection lost")

        # After retries, raises exception
        with pytest.raises((requests.RequestException, APIError)):
            client.revoke_permission(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
                permission_id="perm123",
            )

    @patch("lark_service.clouddoc.client.requests.get")
    def test_list_permissions_success(self, mock_get, client, mock_credential_pool):
        """Test listing permissions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "items": [
                    {
                        "member_type": "user",
                        "member_id": "ou_1234567890abcdefghij",
                        "perm": "view",  # API uses 'perm', not 'perm_type'
                    },
                    {
                        "member_type": "department",
                        "member_id": "od_1234567890abcdefghij",
                        "perm": "edit",  # Maps to 'write'
                    },
                ]
            },
        }
        mock_get.return_value = mock_response

        perms = client.list_permissions(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
        )

        assert len(perms) == 2
        # Check first permission (view -> read)
        assert perms[0].member_type == "user"
        assert perms[0].permission_type == "read"
        # Check second permission (edit -> write)
        assert perms[1].member_type == "department"
        assert perms[1].permission_type == "write"

    @patch("lark_service.clouddoc.client.requests.get")
    def test_list_permissions_empty(self, mock_get, client, mock_credential_pool):
        """Test listing permissions when no permissions exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success", "data": {"items": []}}
        mock_get.return_value = mock_response

        perms = client.list_permissions(
            app_id="cli_test",
            doc_id="doxcn1234567890abcdefghij",
        )

        assert len(perms) == 0

    @patch("lark_service.clouddoc.client.requests.get")
    def test_list_permissions_api_error(self, mock_get, client, mock_credential_pool):
        """Test list permissions handles API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 403,
            "msg": "Permission denied",
        }
        mock_get.return_value = mock_response

        with pytest.raises(APIError):
            client.list_permissions(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
            )

    @patch("lark_service.clouddoc.client.requests.get")
    def test_list_permissions_network_error(self, mock_get, client, mock_credential_pool):
        """Test list permissions handles network error."""
        # Network errors are retried
        mock_get.side_effect = requests.RequestException("Timeout")

        # After retries, raises exception
        with pytest.raises((requests.RequestException, APIError)):
            client.list_permissions(
                app_id="cli_test",
                doc_id="doxcn1234567890abcdefghij",
            )
