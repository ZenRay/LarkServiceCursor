"""
Integration tests for aPaaS WorkspaceTable operations.

These tests require:
- Valid configuration in .env.apaas (separate from .env.test for security)
- Valid user_access_token (not tenant_access_token)
- Valid workspace_id and table_id for testing

Security Notes:
- aPaaS operations require user-level permissions (user_access_token)
- .env.apaas should NEVER be committed to version control
- Use .env.apaas.example as template
- Store actual credentials in secure location (password manager, vault)

Configuration:
Copy .env.apaas.example to .env.apaas and fill in:
- TEST_APAAS_APP_ID
- TEST_APAAS_APP_SECRET
- TEST_APAAS_USER_ACCESS_TOKEN
- TEST_APAAS_WORKSPACE_ID
- TEST_APAAS_TABLE_ID

Note: All tests are currently skipped as WorkspaceTableClient methods
are placeholder implementations (NotImplementedError).
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager

# Load aPaaS-specific environment variables
# Use .env.apaas for higher security (user-level tokens)
env_file = Path(__file__).parent.parent.parent / ".env.apaas"
if env_file.exists():
    load_dotenv(env_file)


@pytest.fixture(scope="module")
def test_config() -> dict[str, str]:
    """Load test configuration from .env.apaas environment variables."""
    config = {
        "app_id": os.getenv("TEST_APAAS_APP_ID", ""),
        "app_secret": os.getenv("TEST_APAAS_APP_SECRET", ""),
        "user_access_token": os.getenv("TEST_APAAS_USER_ACCESS_TOKEN", ""),
        "workspace_id": os.getenv("TEST_APAAS_WORKSPACE_ID", ""),
        "table_id": os.getenv("TEST_APAAS_TABLE_ID", ""),
    }

    # Skip all tests if configuration is missing
    if not all(config.values()):
        pytest.skip(
            "Missing aPaaS test configuration. "
            "Please copy .env.apaas.example to .env.apaas and configure: "
            "TEST_APAAS_APP_ID, TEST_APAAS_APP_SECRET, TEST_APAAS_USER_ACCESS_TOKEN, "
            "TEST_APAAS_WORKSPACE_ID, TEST_APAAS_TABLE_ID"
        )

    return config


@pytest.fixture(scope="module")
def credential_pool(test_config: dict[str, str]) -> CredentialPool:
    """Create credential pool for testing."""
    config = Config(
        encrypt_db_credentials=False,
        credential_db_url="sqlite:///:memory:",
        max_retries=3,
        retry_backoff_base=2.0,
        token_refresh_threshold=300,
    )

    app_manager = ApplicationManager(config)
    token_storage = TokenStorageService(config)

    pool = CredentialPool(
        config=config,
        app_manager=app_manager,
        token_storage=token_storage,
    )

    # Register test app
    pool.register_app(
        app_id=test_config["app_id"],
        app_secret=test_config["app_secret"],
    )

    return pool


@pytest.fixture(scope="module")
def client(credential_pool: CredentialPool) -> WorkspaceTableClient:
    """Create WorkspaceTableClient for testing."""
    return WorkspaceTableClient(credential_pool)


class TestWorkspaceTableReadOperations:
    """Test workspace table read operations (list tables, list fields, query records)."""

    @pytest.mark.skip(reason="WorkspaceTableClient.list_workspace_tables not yet implemented")
    def test_list_workspace_tables(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test listing workspace tables."""
        tables = client.list_workspace_tables(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            workspace_id=test_config["workspace_id"],
        )

        assert isinstance(tables, list)
        assert len(tables) > 0

        # Verify table structure
        first_table = tables[0]
        assert first_table.table_id.startswith("tbl_")
        assert len(first_table.name) > 0

    @pytest.mark.skip(reason="WorkspaceTableClient.list_fields not yet implemented")
    def test_list_fields(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test listing table field definitions."""
        fields = client.list_fields(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
        )

        assert isinstance(fields, list)
        assert len(fields) > 0

        # Verify field structure
        first_field = fields[0]
        assert first_field.field_id.startswith("fld_")
        assert len(first_field.field_name) > 0
        assert first_field.field_type is not None

    @pytest.mark.skip(reason="WorkspaceTableClient.query_records not yet implemented")
    def test_query_records_no_filter(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test querying records without filter."""
        records, next_token, has_more = client.query_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            page_size=10,
        )

        assert isinstance(records, list)
        # Records may be empty for new tables
        for record in records:
            assert record.record_id.startswith("rec_")
            assert isinstance(record.fields, dict)

        # Pagination tokens
        assert isinstance(has_more, bool)
        if has_more:
            assert next_token is not None
        else:
            assert next_token is None

    @pytest.mark.skip(reason="WorkspaceTableClient.query_records not yet implemented")
    def test_query_records_with_filter(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test querying records with filter expression."""
        # Example filter: Status = "Active"
        # Actual field name depends on test table schema
        filter_expr = 'CurrentValue.[Status] = "Active"'

        records, next_token, has_more = client.query_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            filter_expr=filter_expr,
            page_size=20,
        )

        assert isinstance(records, list)
        # All records should match filter
        for record in records:
            assert record.record_id.startswith("rec_")


class TestWorkspaceTableWriteOperations:
    """Test workspace table write operations (create, update, delete)."""

    @pytest.mark.skip(reason="WorkspaceTableClient.create_record not yet implemented")
    def test_create_and_delete_record(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test creating and deleting a record."""
        # First, get field definitions to create valid record
        fields_def = client.list_fields(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
        )

        # Use first text field for testing
        text_field = next((f for f in fields_def if f.field_type.value == "text"), None)
        if not text_field:
            pytest.skip("No text field found in test table")
        assert text_field is not None  # for mypy

        # Create record
        created_record = client.create_record(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            fields={text_field.field_name: "Integration Test Record"},
        )

        assert created_record.record_id.startswith("rec_")
        assert text_field.field_name in created_record.fields

        # Delete record
        client.delete_record(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            record_id=created_record.record_id,
        )

    @pytest.mark.skip(reason="WorkspaceTableClient.update_record not yet implemented")
    def test_update_record(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test updating a record."""
        # Create a record first
        fields_def = client.list_fields(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
        )

        text_field = next((f for f in fields_def if f.field_type.value == "text"), None)
        if not text_field:
            pytest.skip("No text field found in test table")
        assert text_field is not None  # for mypy

        created_record = client.create_record(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            fields={text_field.field_name: "Original Value"},
        )

        # Update the record
        updated_record = client.update_record(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            record_id=created_record.record_id,
            fields={text_field.field_name: "Updated Value"},
        )

        assert updated_record.record_id == created_record.record_id
        assert updated_record.fields[text_field.field_name] == "Updated Value"

        # Clean up
        client.delete_record(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            record_id=created_record.record_id,
        )


class TestWorkspaceTableBatchOperations:
    """Test workspace table batch operations (batch create, batch update)."""

    @pytest.mark.skip(reason="WorkspaceTableClient.batch_create_records not yet implemented")
    def test_batch_create_records(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test batch creating records."""
        fields_def = client.list_fields(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
        )

        text_field = next((f for f in fields_def if f.field_type.value == "text"), None)
        if not text_field:
            pytest.skip("No text field found in test table")
        assert text_field is not None  # for mypy

        # Batch create 5 records
        records_to_create = [{text_field.field_name: f"Batch Test {i}"} for i in range(5)]

        created_records = client.batch_create_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            records=records_to_create,
        )

        assert len(created_records) == 5
        for record in created_records:
            assert record.record_id.startswith("rec_")

        # Clean up
        for record in created_records:
            client.delete_record(
                app_id=test_config["app_id"],
                user_access_token=test_config["user_access_token"],
                table_id=test_config["table_id"],
                record_id=record.record_id,
            )

    @pytest.mark.skip(reason="WorkspaceTableClient.batch_update_records not yet implemented")
    def test_batch_update_records(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test batch updating records."""
        fields_def = client.list_fields(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
        )

        text_field = next((f for f in fields_def if f.field_type.value == "text"), None)
        if not text_field:
            pytest.skip("No text field found in test table")
        assert text_field is not None  # for mypy

        # Create records first
        records_to_create = [{text_field.field_name: f"Original {i}"} for i in range(3)]

        created_records = client.batch_create_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            records=records_to_create,
        )

        # Batch update
        updates = [
            (record.record_id, {text_field.field_name: f"Updated {i}"})
            for i, record in enumerate(created_records)
        ]

        updated_records = client.batch_update_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            table_id=test_config["table_id"],
            records=updates,
        )

        assert len(updated_records) == 3
        for i, record in enumerate(updated_records):
            assert record.fields[text_field.field_name] == f"Updated {i}"

        # Clean up
        for record in updated_records:
            client.delete_record(
                app_id=test_config["app_id"],
                user_access_token=test_config["user_access_token"],
                table_id=test_config["table_id"],
                record_id=record.record_id,
            )
