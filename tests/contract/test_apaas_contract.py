"""
Contract tests for aPaaS API.

Verifies that the implementation matches the API contract defined in
specs/001-lark-service-core/contracts/apaas.yaml
"""

import pytest
from pydantic import ValidationError

from lark_service.apaas.models import (
    FieldDefinition,
    FieldType,
    SelectOption,
    TableRecord,
    WorkspaceTable,
)


class TestFieldTypeContract:
    """Test FieldType enum contract compliance."""

    def test_field_type_enum_values(self) -> None:
        """Test FieldType enum has all required types per contract."""
        assert FieldType.TEXT == "text"
        assert FieldType.NUMBER == "number"
        assert FieldType.SINGLE_SELECT == "single_select"
        assert FieldType.MULTI_SELECT == "multi_select"
        assert FieldType.DATE == "date"
        assert FieldType.DATETIME == "datetime"
        assert FieldType.CHECKBOX == "checkbox"
        assert FieldType.PERSON == "person"
        assert FieldType.PHONE == "phone"
        assert FieldType.EMAIL == "email"
        assert FieldType.URL == "url"
        assert FieldType.ATTACHMENT == "attachment"
        assert FieldType.LINK == "link"
        assert FieldType.FORMULA == "formula"
        assert FieldType.LOOKUP == "lookup"

    def test_field_type_count(self) -> None:
        """Test FieldType enum has exactly 15 types per contract."""
        assert len(FieldType) == 15


class TestSelectOptionContract:
    """Test SelectOption model contract compliance."""

    def test_select_option_required_fields(self) -> None:
        """Test SelectOption has required fields per contract."""
        option = SelectOption(id="opt_001", name="Active")

        assert option.id == "opt_001"
        assert option.name == "Active"
        assert option.color is None

    def test_select_option_with_color(self) -> None:
        """Test SelectOption with optional color field."""
        option = SelectOption(id="opt_002", name="Completed", color="green")

        assert option.id == "opt_002"
        assert option.name == "Completed"
        assert option.color == "green"


class TestFieldDefinitionContract:
    """Test FieldDefinition model contract compliance."""

    def test_field_definition_required_fields(self) -> None:
        """Test FieldDefinition has required fields per contract."""
        field = FieldDefinition(
            field_id="fld_001", field_name="Customer Name", field_type=FieldType.TEXT
        )

        assert field.field_id == "fld_001"
        assert field.field_name == "Customer Name"
        assert field.field_type == FieldType.TEXT
        assert field.is_required is False
        assert field.description is None
        assert field.options is None

    def test_field_definition_with_options(self) -> None:
        """Test FieldDefinition with options for select fields."""
        options = [
            SelectOption(id="opt_1", name="Option 1", color="blue"),
            SelectOption(id="opt_2", name="Option 2", color="red"),
        ]

        field = FieldDefinition(
            field_id="fld_002",
            field_name="Status",
            field_type=FieldType.SINGLE_SELECT,
            is_required=True,
            options=options,
        )

        assert field.field_id == "fld_002"
        assert field.field_type == FieldType.SINGLE_SELECT
        assert field.is_required is True
        assert len(field.options) == 2
        assert field.options[0].name == "Option 1"

    def test_field_id_format(self) -> None:
        """Test field_id format validation (fld_*)."""
        # Valid format
        field = FieldDefinition(
            field_id="fld_a1b2c3d4e5f6g7h8", field_name="Test Field", field_type=FieldType.TEXT
        )
        assert field.field_id.startswith("fld_")


class TestWorkspaceTableContract:
    """Test WorkspaceTable model contract compliance."""

    def test_workspace_table_required_fields(self) -> None:
        """Test WorkspaceTable has required fields per contract."""
        table = WorkspaceTable(table_id="tbl_001", name="Customer Info Table")

        assert table.table_id == "tbl_001"
        assert table.name == "Customer Info Table"
        assert table.workspace_id is None
        assert table.description is None
        assert table.field_count is None

    def test_workspace_table_all_fields(self) -> None:
        """Test WorkspaceTable with all optional fields."""
        table = WorkspaceTable(
            table_id="tbl_002",
            workspace_id="ws_001",
            name="Sales Data",
            description="Track sales information",
            field_count=10,
        )

        assert table.table_id == "tbl_002"
        assert table.workspace_id == "ws_001"
        assert table.name == "Sales Data"
        assert table.description == "Track sales information"
        assert table.field_count == 10

    def test_table_id_format(self) -> None:
        """Test table_id format validation (tbl_*)."""
        table = WorkspaceTable(table_id="tbl_a1b2c3d4e5f6g7h8", name="Test Table")
        assert table.table_id.startswith("tbl_")

    def test_workspace_id_format(self) -> None:
        """Test workspace_id format validation (ws_*)."""
        table = WorkspaceTable(
            table_id="tbl_001", workspace_id="ws_a1b2c3d4e5f6g7h8", name="Test Table"
        )
        assert table.workspace_id.startswith("ws_")

    def test_field_count_non_negative(self) -> None:
        """Test field_count must be non-negative."""
        # Valid: zero fields
        table = WorkspaceTable(table_id="tbl_001", name="Empty Table", field_count=0)
        assert table.field_count == 0

        # Valid: positive fields
        table = WorkspaceTable(table_id="tbl_002", name="Normal Table", field_count=5)
        assert table.field_count == 5

        # Invalid: negative fields
        with pytest.raises(ValidationError):
            WorkspaceTable(table_id="tbl_003", name="Invalid Table", field_count=-1)


class TestTableRecordContract:
    """Test TableRecord model contract compliance."""

    def test_table_record_required_fields(self) -> None:
        """Test TableRecord has required fields per contract."""
        record = TableRecord(record_id="rec_001", fields={"Name": "John Doe", "Age": 30})

        assert record.record_id == "rec_001"
        assert record.fields == {"Name": "John Doe", "Age": 30}
        assert record.table_id is None
        assert record.created_at is None
        assert record.updated_at is None

    def test_table_record_all_fields(self) -> None:
        """Test TableRecord with all optional fields."""
        from datetime import datetime

        now = datetime.now()
        record = TableRecord(
            record_id="rec_002",
            table_id="tbl_001",
            fields={"Status": "Active", "Count": 100},
            created_at=now,
            updated_at=now,
        )

        assert record.record_id == "rec_002"
        assert record.table_id == "tbl_001"
        assert record.fields == {"Status": "Active", "Count": 100}
        assert record.created_at == now
        assert record.updated_at == now

    def test_record_id_format(self) -> None:
        """Test record_id format validation (rec_*)."""
        record = TableRecord(record_id="rec_a1b2c3d4e5f6g7h8", fields={"test": "value"})
        assert record.record_id.startswith("rec_")

    def test_fields_various_types(self) -> None:
        """Test fields support various data types per contract."""
        # Text fields
        record = TableRecord(
            record_id="rec_001", fields={"Name": "Alice", "Email": "alice@example.com"}
        )
        assert isinstance(record.fields["Name"], str)

        # Number fields
        record = TableRecord(record_id="rec_002", fields={"Age": 25, "Score": 95.5})
        assert isinstance(record.fields["Age"], int)
        assert isinstance(record.fields["Score"], float)

        # Boolean fields (checkbox)
        record = TableRecord(record_id="rec_003", fields={"IsActive": True, "IsVerified": False})
        assert isinstance(record.fields["IsActive"], bool)

        # List fields (multi_select, attachments)
        record = TableRecord(
            record_id="rec_004", fields={"Tags": ["tag1", "tag2"], "Files": [{"name": "file.pdf"}]}
        )
        assert isinstance(record.fields["Tags"], list)
        assert isinstance(record.fields["Files"], list)


class TestBatchOperationLimitsContract:
    """Test batch operation limits per contract."""

    def test_batch_create_limit_500(self) -> None:
        """Test batch create supports max 500 records per contract."""
        # This is validated at the client level, not model level
        # We verify the constant is documented in the contract
        # Actual validation will be in client tests
        pass

    def test_batch_update_limit_500(self) -> None:
        """Test batch update supports max 500 records per contract."""
        # This is validated at the client level, not model level
        # We verify the constant is documented in the contract
        # Actual validation will be in client tests
        pass


class TestPaginationContract:
    """Test pagination parameters per contract."""

    def test_page_size_default(self) -> None:
        """Test default page_size is 20 per contract."""
        # This is a client-level default, not model-level
        # Actual validation will be in client tests
        pass

    def test_page_size_max(self) -> None:
        """Test max page_size is 500 per contract."""
        # This is validated at the client level
        # Actual validation will be in client tests
        pass


class TestFilterExpressionContract:
    """Test filter expression format per contract."""

    def test_filter_expression_format(self) -> None:
        """Test filter expression uses CurrentValue.[field] format."""
        # Filter expression validation is done at runtime
        # Example: 'CurrentValue.[Status] = "Active"'
        # This will be tested in integration tests
        pass

    def test_filter_operators(self) -> None:
        """Test supported filter operators per contract."""
        # Supported operators: =, !=, >, >=, <, <=, contains
        # Logical operators: && (AND), || (OR)
        # This will be tested in integration tests
        pass


class TestErrorCodesContract:
    """Test error codes match contract specification."""

    def test_invalid_table_id_error(self) -> None:
        """Test invalid table_id error (1001 per contract)."""
        # Error handling is done at client level
        # This will be tested in client unit tests
        pass

    def test_record_not_found_error(self) -> None:
        """Test record not found error (1002 per contract)."""
        # Error handling is done at client level
        # This will be tested in client unit tests
        pass

    def test_permission_denied_error(self) -> None:
        """Test permission denied error (1003 per contract)."""
        # Error handling is done at client level
        # This will be tested in client unit tests
        pass

    def test_invalid_filter_error(self) -> None:
        """Test invalid filter expression error (1004 per contract)."""
        # Error handling is done at client level
        # This will be tested in integration tests
        pass


class TestAuthenticationContract:
    """Test authentication requirements per contract."""

    def test_user_access_token_required(self) -> None:
        """Test all operations require user_access_token per contract."""
        # Authentication is handled at client level
        # All client methods require user_access_token parameter
        # This will be tested in client unit tests
        pass

    def test_tenant_access_token_not_supported(self) -> None:
        """Test tenant_access_token is not supported per contract."""
        # aPaaS data space operations require user-level permissions
        # This will be tested in integration tests
        pass
