"""
Extended unit tests for WorkspaceTableClient - P1 Coverage Improvement.

This file focuses on testing core functionality that was previously untested:
- Workspace table listing with real data
- Field listing operations
- SQL query execution success paths
- Record query operations with pagination
- Record CRUD operations success paths
- Batch operations with large datasets
- Network error handling
- Response parsing edge cases

Target: Increase coverage from 49.24% to 62%
"""

from unittest.mock import Mock, patch

import pytest
import requests

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.apaas.models import FieldType, TableRecord, WorkspaceTable
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
    PermissionDeniedError,
)

# Valid test credentials
TEST_APP_ID = "cli_a1b2c3d4e5f6g7h8"
TEST_USER_TOKEN = "u-test1234567890abcdef"
TEST_WORKSPACE_ID = "ws_test001"
TEST_TABLE_ID = "test_table"
TEST_RECORD_ID = "rec_test001"


class TestWorkspaceTableOperations:
    """Test workspace table listing and field operations."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch("lark_service.apaas.client.requests.get")
    def test_list_workspace_tables_success(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test successful workspace table listing."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "name": "customers",
                        "description": "Customer records",
                        "columns": [
                            {"name": "id", "data_type": "uuid"},
                            {"name": "name", "data_type": "varchar"},
                        ],
                    },
                    {
                        "name": "orders",
                        "description": "Order records",
                        "columns": [
                            {"name": "id", "data_type": "uuid"},
                            {"name": "total", "data_type": "numeric"},
                        ],
                    },
                ]
            },
        }
        mock_get.return_value = mock_response

        tables = client.list_workspace_tables(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
        )

        assert len(tables) == 2
        assert isinstance(tables[0], WorkspaceTable)
        assert tables[0].name == "customers"
        assert tables[0].description == "Customer records"
        assert tables[0].field_count == 2
        assert tables[1].name == "orders"
        assert tables[1].field_count == 2

    @patch("lark_service.apaas.client.requests.get")
    def test_list_workspace_tables_empty(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test listing workspace with no tables."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"items": []},
        }
        mock_get.return_value = mock_response

        tables = client.list_workspace_tables(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
        )

        assert len(tables) == 0

    @patch("lark_service.apaas.client.requests.get")
    def test_list_workspace_tables_network_error(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test handling network error in list tables."""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(APIError, match="Failed to list workspace tables"):
            client.list_workspace_tables(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
            )

    @patch("lark_service.apaas.client.requests.get")
    def test_list_fields_success(self, mock_get: Mock, client: WorkspaceTableClient) -> None:
        """Test successful field listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "name": "customers",
                        "description": "Customer table",
                        "columns": [
                            {
                                "name": "id",
                                "data_type": "uuid",
                                "is_allow_null": False,
                                "description": "Primary key",
                            },
                            {
                                "name": "name",
                                "data_type": "varchar",
                                "is_allow_null": False,
                                "description": "Customer name",
                            },
                            {
                                "name": "email",
                                "data_type": "varchar",
                                "is_allow_null": True,
                                "description": "Email address",
                            },
                        ],
                    }
                ]
            },
        }
        mock_get.return_value = mock_response

        fields = client.list_fields(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id="customers",
            workspace_id=TEST_WORKSPACE_ID,
        )

        assert len(fields) == 3
        assert fields[0].field_name == "id"
        assert fields[0].field_type == FieldType.TEXT
        assert fields[0].is_required is True
        assert fields[1].field_name == "name"
        assert fields[1].is_required is True
        assert fields[2].field_name == "email"
        assert fields[2].is_required is False

    @patch("lark_service.apaas.client.requests.get")
    def test_list_fields_table_not_found(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test listing fields for non-existent table."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"items": []},  # No tables found
        }
        mock_get.return_value = mock_response

        with pytest.raises(NotFoundError, match="Table not found"):
            client.list_fields(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id="nonexistent_table",
                workspace_id=TEST_WORKSPACE_ID,
            )

    @patch("lark_service.apaas.client.requests.get")
    def test_list_fields_network_error(self, mock_get: Mock, client: WorkspaceTableClient) -> None:
        """Test handling network error in list fields."""
        mock_get.side_effect = requests.RequestException("Connection timeout")

        with pytest.raises(APIError, match="Failed to list table fields"):
            client.list_fields(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id=TEST_TABLE_ID,
                workspace_id=TEST_WORKSPACE_ID,
            )


class TestSQLQueryExecution:
    """Test SQL query execution."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch("lark_service.apaas.client.requests.post")
    def test_sql_query_success(self, mock_post: Mock, client: WorkspaceTableClient) -> None:
        """Test successful SQL query execution."""
        import json

        # Mock successful response
        records_data = [
            {"id": "1", "name": "Customer 1", "stage": "潜在客户"},
            {"id": "2", "name": "Customer 2", "stage": "成交客户"},
        ]
        records_json = json.dumps(records_data)
        result_json = json.dumps([records_json])

        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"result": result_json},
        }
        mock_post.return_value = mock_response

        results = client.sql_query(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
            sql="SELECT id, name, stage FROM customers LIMIT 10",
        )

        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[0]["name"] == "Customer 1"
        assert results[1]["stage"] == "成交客户"

    @patch("lark_service.apaas.client.requests.post")
    def test_sql_query_empty_result(self, mock_post: Mock, client: WorkspaceTableClient) -> None:
        """Test SQL query with empty result."""
        import json

        empty_records = json.dumps([])
        result_json = json.dumps([empty_records])

        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"result": result_json},
        }
        mock_post.return_value = mock_response

        results = client.sql_query(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            workspace_id=TEST_WORKSPACE_ID,
            sql="SELECT * FROM customers WHERE 1=0",
        )

        assert len(results) == 0

    @patch("lark_service.apaas.client.requests.post")
    def test_sql_query_api_error(self, mock_post: Mock, client: WorkspaceTableClient) -> None:
        """Test SQL query with API error."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 500232002,
            "msg": "SQL syntax error",
        }
        mock_post.return_value = mock_response

        with pytest.raises(APIError, match="aPaaS API error"):
            client.sql_query(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                sql="INVALID SQL",
            )

    @patch("lark_service.apaas.client.requests.post")
    def test_sql_query_network_error(self, mock_post: Mock, client: WorkspaceTableClient) -> None:
        """Test SQL query network error handling."""
        mock_post.side_effect = requests.RequestException("Timeout")

        with pytest.raises(APIError, match="Failed to execute SQL query"):
            client.sql_query(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                sql="SELECT * FROM customers",
            )

    @patch("lark_service.apaas.client.requests.post")
    def test_sql_query_parse_error(self, mock_post: Mock, client: WorkspaceTableClient) -> None:
        """Test SQL query response parsing error."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"result": "invalid json"},
        }
        mock_post.return_value = mock_response

        with pytest.raises(APIError, match="Failed to parse SQL response"):
            client.sql_query(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                workspace_id=TEST_WORKSPACE_ID,
                sql="SELECT * FROM customers",
            )


class TestRecordQueryOperations:
    """Test record query operations."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch("lark_service.apaas.client.requests.get")
    def test_query_records_success(self, mock_get: Mock, client: WorkspaceTableClient) -> None:
        """Test successful record query."""
        import json

        items = [
            {"id": "rec1", "name": "Record 1", "status": "active"},
            {"id": "rec2", "name": "Record 2", "status": "inactive"},
        ]
        items_json = json.dumps(items)

        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": items_json,
                "has_more": False,
                "page_token": None,
                "total": 2,
            },
        }
        mock_get.return_value = mock_response

        records, next_token, has_more = client.query_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            page_size=20,
        )

        assert len(records) == 2
        assert isinstance(records[0], TableRecord)
        assert records[0].record_id == "rec1"
        assert records[0].fields["name"] == "Record 1"
        assert records[1].fields["status"] == "inactive"
        assert next_token is None
        assert has_more is False

    @patch("lark_service.apaas.client.requests.get")
    def test_query_records_with_pagination(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test record query with pagination."""
        import json

        items = [{"id": f"rec{i}", "name": f"Record {i}"} for i in range(50)]
        items_json = json.dumps(items)

        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": items_json,
                "has_more": True,
                "page_token": "next_page_123",
                "total": 150,
            },
        }
        mock_get.return_value = mock_response

        records, next_token, has_more = client.query_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            page_size=50,
        )

        assert len(records) == 50
        assert has_more is True
        assert next_token == "next_page_123"

        # Query next page
        mock_response.json.return_value["data"]["page_token"] = None
        mock_response.json.return_value["data"]["has_more"] = False

        records2, next_token2, has_more2 = client.query_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            page_size=50,
            page_token=next_token,
        )

        assert has_more2 is False
        assert next_token2 is None

    @patch("lark_service.apaas.client.requests.get")
    def test_query_records_network_error(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test record query network error."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        with pytest.raises(APIError, match="Failed to query records"):
            client.query_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id=TEST_TABLE_ID,
                workspace_id=TEST_WORKSPACE_ID,
            )


class TestRecordCRUDOperations:
    """Test record create, update, delete operations."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_create_record_success(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test successful record creation."""
        # Mock SQL query to return created ID
        mock_sql_query.return_value = [{"id": "new_record_123"}]

        record_id = client.create_record(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            fields={
                "customer_id": "cust_001",
                "content": "Follow up call",
                "stage": "潜在客户",
            },
        )

        assert record_id == "new_record_123"
        mock_sql_query.assert_called_once()

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_create_record_no_id_returned(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test create record fails when no ID returned."""
        mock_sql_query.return_value = []

        with pytest.raises(APIError, match="no ID returned"):
            client.create_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id=TEST_TABLE_ID,
                workspace_id=TEST_WORKSPACE_ID,
                fields={"name": "Test"},
            )

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_update_record_success(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test successful record update."""
        mock_sql_query.return_value = []

        success = client.update_record(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            record_id=TEST_RECORD_ID,
            fields={
                "status": "completed",
                "content": "Updated content",
            },
        )

        assert success is True
        mock_sql_query.assert_called_once()

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_update_record_api_error(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test update record handles API error."""
        mock_sql_query.side_effect = APIError("SQL execution failed")

        with pytest.raises(APIError):
            client.update_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id=TEST_TABLE_ID,
                workspace_id=TEST_WORKSPACE_ID,
                record_id=TEST_RECORD_ID,
                fields={"status": "updated"},
            )

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_delete_record_success(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test successful record deletion."""
        mock_sql_query.return_value = []

        success = client.delete_record(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            record_id=TEST_RECORD_ID,
        )

        assert success is True
        mock_sql_query.assert_called_once()

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_delete_record_api_error(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test delete record handles API error."""
        mock_sql_query.side_effect = APIError("Record not found")

        with pytest.raises(APIError):
            client.delete_record(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id=TEST_TABLE_ID,
                workspace_id=TEST_WORKSPACE_ID,
                record_id=TEST_RECORD_ID,
            )


class TestBatchOperationsLargeDatasets:
    """Test batch operations with large datasets."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_create_single_batch(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch create with single batch."""
        # Mock SQL query to return IDs
        mock_sql_query.return_value = [{"id": f"rec_{i}"} for i in range(50)]

        records = [{"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(50)]

        result = client.batch_create_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            records=records,
            batch_size=100,
        )

        assert len(result) == 50
        assert mock_sql_query.call_count == 1

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_create_multiple_batches(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch create with multiple batches."""
        # Mock SQL query to return IDs
        mock_sql_query.return_value = [{"id": f"rec_{i}"} for i in range(100)]

        records = [{"name": f"User {i}"} for i in range(250)]

        result = client.batch_create_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            records=records,
            batch_size=100,
        )

        # 3 batches: 100 + 100 + 50, each returning 100 IDs from mock
        assert len(result) == 300
        assert mock_sql_query.call_count == 3

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_update_large_dataset(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch update with large dataset."""
        mock_sql_query.return_value = []

        updates = [(f"rec_{i}", {"status": "updated"}) for i in range(500)]

        result = client.batch_update_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            records=updates,
            batch_size=200,
        )

        assert result == 500
        # 3 batches: 200 + 200 + 100
        assert mock_sql_query.call_count == 3

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_delete_large_dataset(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch delete with large dataset."""
        mock_sql_query.return_value = []

        record_ids = [f"rec_{i}" for i in range(1000)]

        result = client.batch_delete_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            record_ids=record_ids,
            batch_size=300,
        )

        assert result == 1000
        # 4 batches: 300 + 300 + 300 + 100
        assert mock_sql_query.call_count == 4

    @patch.object(WorkspaceTableClient, "sql_query")
    def test_batch_create_error_in_batch(
        self, mock_sql_query: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test batch create handles error in one batch."""
        # First batch succeeds, second fails
        mock_sql_query.side_effect = [
            [{"id": f"rec_{i}"} for i in range(100)],
            APIError("Batch insert failed"),
        ]

        records = [{"name": f"User {i}"} for i in range(200)]

        with pytest.raises(APIError, match="Failed to create batch"):
            client.batch_create_records(
                app_id=TEST_APP_ID,
                user_access_token=TEST_USER_TOKEN,
                table_id=TEST_TABLE_ID,
                workspace_id=TEST_WORKSPACE_ID,
                records=records,
                batch_size=100,
            )


class TestAPIErrorMapping:
    """Test API error code mapping."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    def test_handle_permission_denied_error(self, client: WorkspaceTableClient) -> None:
        """Test handling permission denied error codes."""
        result = {"code": 99991400, "msg": "Authentication failed"}

        with pytest.raises(PermissionDeniedError, match="Permission denied"):
            client._handle_api_error(result, "test_method")

        result = {"code": 99991401, "msg": "Access token invalid"}

        with pytest.raises(PermissionDeniedError, match="Permission denied"):
            client._handle_api_error(result, "test_method")

        result = {"code": 99991663, "msg": "No permission"}

        with pytest.raises(PermissionDeniedError, match="Permission denied"):
            client._handle_api_error(result, "test_method")

    def test_handle_not_found_error(self, client: WorkspaceTableClient) -> None:
        """Test handling not found error codes."""
        result = {"code": 99991404, "msg": "Resource not found"}

        with pytest.raises(NotFoundError, match="Resource not found"):
            client._handle_api_error(result, "test_method")

        result = {"code": 230002, "msg": "Table not found"}

        with pytest.raises(NotFoundError, match="Resource not found"):
            client._handle_api_error(result, "test_method")

    def test_handle_invalid_parameter_error(self, client: WorkspaceTableClient) -> None:
        """Test handling invalid parameter error codes."""
        result = {"code": 99991402, "msg": "Invalid parameter"}

        with pytest.raises(InvalidParameterError, match="Invalid parameter"):
            client._handle_api_error(result, "test_method")

        result = {"code": 99991403, "msg": "Missing required parameter"}

        with pytest.raises(InvalidParameterError, match="Invalid parameter"):
            client._handle_api_error(result, "test_method")


class TestFilterExpressionWarning:
    """Test filter expression warning."""

    @pytest.fixture
    def mock_credential_pool(self) -> Mock:
        """Create mock credential pool."""
        return Mock(spec=CredentialPool)

    @pytest.fixture
    def client(self, mock_credential_pool: Mock) -> WorkspaceTableClient:
        """Create WorkspaceTableClient instance."""
        return WorkspaceTableClient(mock_credential_pool)

    @patch("lark_service.apaas.client.requests.get")
    def test_query_records_filter_expr_warning(
        self, mock_get: Mock, client: WorkspaceTableClient
    ) -> None:
        """Test that filter_expr logs a warning."""
        import json

        items_json = json.dumps([])
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": items_json,
                "has_more": False,
                "page_token": None,
                "total": 0,
            },
        }
        mock_get.return_value = mock_response

        # Should not raise, but will log warning
        records, _, _ = client.query_records(
            app_id=TEST_APP_ID,
            user_access_token=TEST_USER_TOKEN,
            table_id=TEST_TABLE_ID,
            workspace_id=TEST_WORKSPACE_ID,
            filter_expr="stage = '潜在客户'",  # This will be ignored with warning
        )

        assert len(records) == 0
