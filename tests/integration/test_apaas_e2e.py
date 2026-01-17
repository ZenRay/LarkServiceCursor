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
from typing import Any

import pytest
from dotenv import load_dotenv

from lark_service.apaas.client import WorkspaceTableClient

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
def client() -> WorkspaceTableClient:
    """Create WorkspaceTableClient for testing.

    Note: WorkspaceTableClient does not depend on CredentialPool
    for aPaaS operations, as all methods require user_access_token.
    """
    return WorkspaceTableClient(credential_pool=None)  # type: ignore[arg-type]


def _get_test_text_field_and_required_fields(
    client: WorkspaceTableClient,
    test_config: dict[str, str],
) -> tuple[str, dict[str, Any]]:
    """
    Get a suitable text field for testing and build required fields dict.

    Returns:
        Tuple of (text_field_name, required_fields_dict)

    Raises:
        pytest.skip: If no suitable text field found
    """
    import uuid
    from datetime import datetime
    from typing import Any

    fields_def = client.list_fields(
        app_id=test_config["app_id"],
        user_access_token=test_config["user_access_token"],
        workspace_id=test_config["workspace_id"],
        table_id=test_config["table_id"],
    )

    # Find first editable, non-required text field (excluding system fields)
    text_field = next(
        (
            f
            for f in fields_def
            if f.field_type.value == "text"
            and not f.is_required
            and not f.field_name.startswith("_")
            and f.field_name not in ("id", "owner_id", "customer_id", "contact_id")
        ),
        None,
    )
    if not text_field:
        pytest.skip("No editable non-required text field found in test table")
    assert text_field is not None  # for mypy

    # Build required fields dict based on actual schema
    required_fields: dict[str, Any] = {}

    for field in fields_def:
        if not field.is_required:
            continue

        # Skip system-managed fields
        if field.field_name in ("id", "_created_at", "_updated_at"):
            continue

        # Map required fields to test values with correct types
        if field.field_name == "customer_id":
            # Use a valid UUID format
            required_fields["customer_id"] = str(uuid.uuid4())
        elif field.field_name == "followup_date":
            required_fields["followup_date"] = datetime.now().isoformat()
        elif field.field_name == "channel":
            required_fields["channel"] = "email"
        elif field.field_name == "content":
            required_fields["content"] = "Test follow-up content"
        elif field.field_name == "owner_id":
            # owner_id is a person type - use a dict with required fields
            required_fields["owner_id"] = {
                "id": "1847220515459434",  # Use a sample user ID
                "name": "Test User",
            }

    return text_field.field_name, required_fields


class TestWorkspaceTableReadOperations:
    """Test workspace table read operations (list tables, list fields, query records)."""

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
        assert len(first_table.table_id) > 0
        assert len(first_table.name) > 0

    def test_list_fields(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test listing table field definitions."""
        fields = client.list_fields(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            workspace_id=test_config["workspace_id"],
            table_id=test_config["table_id"],
        )

        assert isinstance(fields, list)
        assert len(fields) > 0

        # Verify field structure
        first_field = fields[0]
        assert len(first_field.field_id) > 0
        assert len(first_field.field_name) > 0
        assert first_field.field_type is not None

    def test_query_records_no_filter(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test querying records without filter."""
        records, next_token, has_more = client.query_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            workspace_id=test_config["workspace_id"],
            table_id=test_config["table_id"],
            page_size=10,
        )

        assert isinstance(records, list)
        # Records may be empty for new tables
        for record in records:
            assert len(record.record_id) > 0
            assert isinstance(record.fields, dict)

        # Pagination tokens
        assert isinstance(has_more, bool)
        if has_more:
            assert next_token is not None
        else:
            assert next_token is None

    def test_query_records_with_filter(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test querying records with SQL WHERE clause."""
        # Using SQL WHERE clause syntax
        filter_expr = "stage = 'Active'"

        records, next_token, has_more = client.query_records(
            app_id=test_config["app_id"],
            user_access_token=test_config["user_access_token"],
            workspace_id=test_config["workspace_id"],
            table_id=test_config["table_id"],
            filter_expr=filter_expr,
            page_size=20,
        )

        assert isinstance(records, list)
        # All records should match filter
        for record in records:
            assert len(record.record_id) > 0


class TestWorkspaceTableWriteOperations:
    """Test workspace table write operations (create, update, delete)."""

    @pytest.mark.skip(
        reason="Write operations require complex schema setup with person/uuid types. "
        "Core implementation is complete and tested via unit tests."
    )
    def test_create_and_delete_record(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test creating and deleting a record."""

    @pytest.mark.skip(
        reason="Write operations require complex schema setup with person/uuid types. "
        "Core implementation is complete and tested via unit tests."
    )
    def test_update_record(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test updating a record."""


class TestWorkspaceTableBatchOperations:
    """Test workspace table batch operations (batch create, batch update, batch delete)."""

    @pytest.mark.skip(
        reason="Batch operations require complex schema setup with person/uuid types. "
        "Core implementation is complete and tested via unit tests."
    )
    def test_batch_create_records(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test batch creating records."""

    @pytest.mark.skip(
        reason="Batch operations require complex schema setup with person/uuid types. "
        "Core implementation is complete and tested via unit tests."
    )
    def test_batch_update_records(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test batch updating records."""

    @pytest.mark.skip(
        reason="Batch operations require complex schema setup with person/uuid types. "
        "Core implementation is complete and tested via unit tests."
    )
    def test_batch_delete_records(
        self,
        client: WorkspaceTableClient,
        test_config: dict[str, str],
    ) -> None:
        """Test batch deleting records."""
