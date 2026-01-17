"""
Unit tests for WorkspaceTableClient.

Tests workspace table operations, record CRUD, batch operations, and parameter validation.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.apaas.models import FieldType
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import APIError, InvalidParameterError, ValidationError

# Valid test credentials
TEST_APP_ID = "cli_a1b2c3d4e5f6g7h8"
TEST_USER_TOKEN = "u-test1234567890abcdef"
TEST_WORKSPACE_ID = "ws_test001"
TEST_TABLE_ID = "test_table"
TEST_RECORD_ID = "rec_test001"


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
        with pytest.raises(ValidationError, match="workspace_id cannot be empty"):
            client.list_workspace_tables(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id="",
            )

    def test_list_fields_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test list fields fails with invalid table_id format."""
        # Empty table_id
        with pytest.raises(ValidationError, match="table_id cannot be empty"):
            client.list_fields(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id="",
            )

    def test_query_records_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test query records fails with invalid table_id format."""
        with pytest.raises(ValidationError, match="table_id cannot be empty"):
            client.query_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id="",
            )

    def test_query_records_invalid_page_size(self, client: WorkspaceTableClient) -> None:
        """Test query records fails with invalid page_size."""
        # page_size < 1
        with pytest.raises(ValidationError, match="page_size must be between 1 and 500"):
            client.query_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                page_size=0,
            )

        # page_size > 500
        with pytest.raises(ValidationError, match="page_size must be at most 500"):
            client.query_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                page_size=501,
            )

    def test_create_record_invalid_table_id(self, client: WorkspaceTableClient) -> None:
        """Test create record fails with invalid table_id format."""
        with pytest.raises(ValidationError, match="table_id cannot be empty"):
            client.create_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id="",
                fields={"Name": "Test"},
            )

    def test_create_record_empty_fields(self, client: WorkspaceTableClient) -> None:
        """Test create record fails with empty fields."""
        with pytest.raises(InvalidParameterError, match="fields cannot be empty"):
            client.create_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                fields={},
            )

    def test_update_record_invalid_record_id(self, client: WorkspaceTableClient) -> None:
        """Test update record fails with invalid record_id format."""
        # Empty record_id
        with pytest.raises(ValidationError, match="record_id cannot be empty"):
            client.update_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                record_id="",
                fields={"Status": "Active"},
            )

    def test_update_record_empty_fields(self, client: WorkspaceTableClient) -> None:
        """Test update record fails with empty fields."""
        with pytest.raises(InvalidParameterError, match="fields cannot be empty"):
            client.update_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                record_id=TEST_RECORD_ID,
                fields={},
            )

    def test_delete_record_invalid_record_id(self, client: WorkspaceTableClient) -> None:
        """Test delete record fails with invalid record_id format."""
        with pytest.raises(ValidationError, match="record_id cannot be empty"):
            client.delete_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                record_id="",
            )

    def test_batch_create_records_empty_records(self, client: WorkspaceTableClient) -> None:
        """Test batch create records fails with empty records list."""
        with pytest.raises(InvalidParameterError, match="records cannot be empty"):
            client.batch_create_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                records=[],
            )

    def test_batch_update_records_empty_records(self, client: WorkspaceTableClient) -> None:
        """Test batch update records fails with empty records list."""
        with pytest.raises(InvalidParameterError, match="records cannot be empty"):
            client.batch_update_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                records=[],
            )

    def test_batch_delete_records_empty_records(self, client: WorkspaceTableClient) -> None:
        """Test batch delete records fails with empty record_ids list."""
        with pytest.raises(InvalidParameterError, match="record_ids cannot be empty"):
            client.batch_delete_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                table_id=TEST_TABLE_ID,
                record_ids=[],
            )


class TestSQLValueFormatting:
    """Test SQL value formatting for different Python types."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    def test_format_none_value(self, client: WorkspaceTableClient) -> None:
        """Test formatting None value."""
        result = client._format_sql_value(None)
        assert result == "NULL"

    def test_format_boolean_values(self, client: WorkspaceTableClient) -> None:
        """Test formatting boolean values."""
        assert client._format_sql_value(True) == "TRUE"
        assert client._format_sql_value(False) == "FALSE"

    def test_format_numeric_values(self, client: WorkspaceTableClient) -> None:
        """Test formatting numeric values."""
        assert client._format_sql_value(42) == "42"
        assert client._format_sql_value(3.14) == "3.14"
        assert client._format_sql_value(-100) == "-100"
        assert client._format_sql_value(0.0) == "0.0"

    def test_format_string_values(self, client: WorkspaceTableClient) -> None:
        """Test formatting string values with proper escaping."""
        # Simple string
        assert client._format_sql_value("hello") == "'hello'"

        # String with single quote
        assert client._format_sql_value("it's") == "'it''s'"

        # String with multiple quotes
        assert client._format_sql_value("'test'") == "'''test'''"

        # Empty string
        assert client._format_sql_value("") == "''"

    def test_format_dict_values(self, client: WorkspaceTableClient) -> None:
        """Test formatting dictionary values (JSON serialization)."""
        # Simple dict
        result = client._format_sql_value({"id": "123", "name": "Test"})
        assert result.startswith("'")
        assert result.endswith("'")
        assert "123" in result
        assert "Test" in result

        # Dict with quotes
        result = client._format_sql_value({"text": "it's working"})
        assert "''" in result  # Escaped quotes

    def test_format_list_values(self, client: WorkspaceTableClient) -> None:
        """Test formatting list values (JSON serialization)."""
        result = client._format_sql_value([1, 2, 3])
        assert result.startswith("'")
        assert result.endswith("'")
        assert "[1, 2, 3]" in result or "[1,2,3]" in result

    def test_format_datetime_values(self, client: WorkspaceTableClient) -> None:
        """Test formatting datetime values."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = client._format_sql_value(dt)
        assert result.startswith("'")
        assert result.endswith("'")
        assert "2024-01-15" in result


class TestDataTypeMapping:
    """Test PostgreSQL data type to FieldType mapping."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    def test_map_text_types(self, client: WorkspaceTableClient) -> None:
        """Test mapping text types."""
        assert client._map_data_type_to_field_type("text") == FieldType.TEXT
        assert client._map_data_type_to_field_type("varchar") == FieldType.TEXT
        assert client._map_data_type_to_field_type("uuid") == FieldType.TEXT

    def test_map_numeric_types(self, client: WorkspaceTableClient) -> None:
        """Test mapping numeric types."""
        assert client._map_data_type_to_field_type("int4") == FieldType.NUMBER
        assert client._map_data_type_to_field_type("int8") == FieldType.NUMBER
        assert client._map_data_type_to_field_type("numeric") == FieldType.NUMBER
        assert client._map_data_type_to_field_type("float4") == FieldType.NUMBER
        assert client._map_data_type_to_field_type("float8") == FieldType.NUMBER

    def test_map_boolean_types(self, client: WorkspaceTableClient) -> None:
        """Test mapping boolean types."""
        assert client._map_data_type_to_field_type("bool") == FieldType.CHECKBOX

    def test_map_datetime_types(self, client: WorkspaceTableClient) -> None:
        """Test mapping datetime types."""
        assert client._map_data_type_to_field_type("date") == FieldType.DATE
        assert client._map_data_type_to_field_type("timestamp") == FieldType.DATETIME
        assert client._map_data_type_to_field_type("timestamptz") == FieldType.DATETIME

    def test_map_person_type(self, client: WorkspaceTableClient) -> None:
        """Test mapping person type."""
        assert client._map_data_type_to_field_type("user_profile") == FieldType.PERSON

    def test_map_unknown_type(self, client: WorkspaceTableClient) -> None:
        """Test mapping unknown types defaults to TEXT."""
        assert client._map_data_type_to_field_type("unknown_type") == FieldType.TEXT
        assert client._map_data_type_to_field_type("custom_type") == FieldType.TEXT
        # JSON types also default to TEXT
        assert client._map_data_type_to_field_type("json") == FieldType.TEXT
        assert client._map_data_type_to_field_type("jsonb") == FieldType.TEXT


class TestErrorHandling:
    """Test error handling and API error mapping."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    def test_handle_api_error_generic(self, client: WorkspaceTableClient) -> None:
        """Test handling generic API error."""
        result = {"code": 999999, "msg": "Unknown error occurred"}

        with pytest.raises(APIError, match="aPaaS API error \\(999999\\)"):
            client._handle_api_error(result, "test_method")

    def test_handle_api_error_with_code(self, client: WorkspaceTableClient) -> None:
        """Test error handling includes error code."""
        result = {"code": 500232002, "msg": "SQL execution failed"}

        with pytest.raises(APIError, match="aPaaS API error \\(500232002\\): SQL execution failed"):
            client._handle_api_error(result, "sql_query")


class TestBatchOperations:
    """Test batch operations and chunking logic."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_create_with_chunking(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch create automatically chunks large datasets."""
        # Mock SQL query to return IDs
        mock_sql_query.return_value = [{"id": str(i)} for i in range(100)]

        # Create 150 records (should be split into 2 chunks: 100 + 50)
        records = [{"name": f"User {i}"} for i in range(150)]

        result = client.batch_create_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
            table_id=TEST_TABLE_ID,
            records=records,
            batch_size=100,
        )

        # Should return list of IDs
        assert isinstance(result, list)
        # Two batches: 100 + 50, each returning 100 IDs from mock
        assert len(result) == 200  # 100 IDs from first batch + 100 IDs from second batch

        # SQL query should be called twice (2 chunks)
        assert mock_sql_query.call_count == 2

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_update_with_chunking(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch update automatically chunks large datasets."""
        # Mock SQL query
        mock_sql_query.return_value = []

        # Create 250 updates (should be split into chunks)
        updates = [(f"rec_{i}", {"status": "updated"}) for i in range(250)]

        result = client.batch_update_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
            table_id=TEST_TABLE_ID,
            records=updates,
            batch_size=100,
        )

        # Should return total count for updates
        assert result == 250

        # SQL query should be called 3 times (100 + 100 + 50)
        assert mock_sql_query.call_count == 3

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_delete_with_chunking(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch delete automatically chunks large datasets."""
        # Mock SQL query
        mock_sql_query.return_value = []

        # Create 300 record IDs (should be split into chunks)
        record_ids = [f"rec_{i}" for i in range(300)]

        result = client.batch_delete_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
            table_id=TEST_TABLE_ID,
            record_ids=record_ids,
            batch_size=150,
        )

        # Should return total count for deletes
        assert result == 300

        # SQL query should be called 2 times (150 + 150)
        assert mock_sql_query.call_count == 2
