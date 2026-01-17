"""
Unit tests for WorkspaceTableClient.

Tests workspace table operations, record CRUD, batch operations, and parameter validation.
"""

from unittest.mock import Mock

import pytest

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError


class TestWorkspaceTableClientValidation:
    """Test WorkspaceTableClient parameter validation logic."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    def test_list_workspace_tables_invalid_workspace_id(self, client: WorkspaceTableClient) -> None:
        """Test list workspace tables fails with invalid workspace_id format."""
        # Empty workspace_id
        with pytest.raises(InvalidParameterError, match="Invalid workspace_id format"):
            client.list_workspace_tables(
                app_id="cli_test",
                user_access_token="u-xxx",
                workspace_id="",
            )

        # Missing ws_ prefix
        with pytest.raises(InvalidParameterError, match="Invalid workspace_id format"):
            client.list_workspace_tables(
                app_id="cli_test",
                user_access_token="u-xxx",
                workspace_id="invalid_id",
            )

    def test_list_fields_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test list fields fails with invalid table_id format."""
        # Empty table_id
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.list_fields(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="",
            )

        # Missing tbl_ prefix
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.list_fields(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="bad_id",
            )

    def test_query_records_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test query records fails with invalid table_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.query_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="invalid",
            )

    def test_query_records_invalid_page_size(self, client: WorkspaceTableClient) -> None:
        """Test query records fails with invalid page_size."""
        # page_size < 1
        with pytest.raises(InvalidParameterError, match="page_size must be between 1 and 500"):
            client.query_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                page_size=0,
            )

        # page_size > 500
        with pytest.raises(InvalidParameterError, match="page_size must be between 1 and 500"):
            client.query_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                page_size=501,
            )

    def test_create_record_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test create record fails with invalid table_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.create_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="bad_id",
                fields={"Name": "Test"},
            )

    def test_create_record_empty_fields(self, client: WorkspaceTableClient) -> None:
        """Test create record fails with empty fields."""
        with pytest.raises(InvalidParameterError, match="fields cannot be empty"):
            client.create_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                fields={},
            )

    def test_update_record_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test update record fails with invalid table_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.update_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="bad_id",
                record_id="rec_001",
                fields={"Status": "Active"},
            )

    def test_update_record_invalid_record_id(self, client: WorkspaceTableClient) -> None:
        """Test update record fails with invalid record_id format."""
        # Empty record_id
        with pytest.raises(InvalidParameterError, match="Invalid record_id format"):
            client.update_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                record_id="",
                fields={"Status": "Active"},
            )

        # Missing rec_ prefix
        with pytest.raises(InvalidParameterError, match="Invalid record_id format"):
            client.update_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                record_id="bad_rec",
                fields={"Status": "Active"},
            )

    def test_update_record_empty_fields(self, client: WorkspaceTableClient) -> None:
        """Test update record fails with empty fields."""
        with pytest.raises(InvalidParameterError, match="fields cannot be empty"):
            client.update_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                record_id="rec_001",
                fields={},
            )

    def test_delete_record_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test delete record fails with invalid table_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.delete_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="bad_id",
                record_id="rec_001",
            )

    def test_delete_record_invalid_record_id(self, client: WorkspaceTableClient) -> None:
        """Test delete record fails with invalid record_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid record_id format"):
            client.delete_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                record_id="invalid",
            )

    def test_batch_create_records_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test batch create records fails with invalid table_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.batch_create_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="bad_id",
                records=[{"Name": "Alice"}, {"Name": "Bob"}],
            )

    def test_batch_create_records_empty_records(self, client: WorkspaceTableClient) -> None:
        """Test batch create records fails with empty records list."""
        with pytest.raises(InvalidParameterError, match="records cannot be empty"):
            client.batch_create_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=[],
            )

    def test_batch_create_records_exceeds_limit(self, client: WorkspaceTableClient) -> None:
        """Test batch create records fails when exceeding 500 records limit."""
        # Create 501 records
        records = [{"Name": f"User{i}"} for i in range(501)]

        with pytest.raises(InvalidParameterError, match="Batch create supports max 500 records"):
            client.batch_create_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=records,
            )

    def test_batch_update_records_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test batch update records fails with invalid table_id format."""
        with pytest.raises(InvalidParameterError, match="Invalid table_id format"):
            client.batch_update_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="bad_id",
                records=[("rec_001", {"Status": "Active"})],
            )

    def test_batch_update_records_empty_records(self, client: WorkspaceTableClient) -> None:
        """Test batch update records fails with empty records list."""
        with pytest.raises(InvalidParameterError, match="records cannot be empty"):
            client.batch_update_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=[],
            )

    def test_batch_update_records_exceeds_limit(self, client: WorkspaceTableClient) -> None:
        """Test batch update records fails when exceeding 500 records limit."""
        # Create 501 update records
        records = [(f"rec_{i:03d}", {"Count": i}) for i in range(501)]

        with pytest.raises(InvalidParameterError, match="Batch update supports max 500 records"):
            client.batch_update_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=records,
            )

    def test_batch_update_records_invalid_record_id(self, client: WorkspaceTableClient) -> None:
        """Test batch update records fails with invalid record_id in batch."""
        records = [
            ("rec_001", {"Status": "Active"}),
            ("invalid_id", {"Status": "Inactive"}),  # Invalid record_id
        ]

        with pytest.raises(InvalidParameterError, match="Invalid record_id format: invalid_id"):
            client.batch_update_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=records,
            )


class TestWorkspaceTableClientPlaceholders:
    """Test WorkspaceTableClient placeholder methods (not yet implemented)."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_list_workspace_tables_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test list_workspace_tables raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="list_workspace_tables not yet implemented"):
            client.list_workspace_tables(
                app_id="cli_test",
                user_access_token="u-xxx",
                workspace_id="ws_001",
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_list_fields_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test list_fields raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="list_fields not yet implemented"):
            client.list_fields(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_query_records_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test query_records raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="query_records not yet implemented"):
            client.query_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_create_record_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test create_record raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="create_record not yet implemented"):
            client.create_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                fields={"Name": "Test User"},
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_update_record_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test update_record raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="update_record not yet implemented"):
            client.update_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                record_id="rec_001",
                fields={"Status": "Updated"},
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_delete_record_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test delete_record raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="delete_record not yet implemented"):
            client.delete_record(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                record_id="rec_001",
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_batch_create_records_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test batch_create_records raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="batch_create_records not yet implemented"):
            client.batch_create_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=[{"Name": "Alice"}, {"Name": "Bob"}],
            )

    @pytest.mark.skip(reason="Method not yet implemented (placeholder)")
    def test_batch_update_records_placeholder(self, client: WorkspaceTableClient) -> None:
        """Test batch_update_records raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="batch_update_records not yet implemented"):
            client.batch_update_records(
                app_id="cli_test",
                user_access_token="u-xxx",
                table_id="tbl_001",
                records=[("rec_001", {"Status": "Active"})],
            )
