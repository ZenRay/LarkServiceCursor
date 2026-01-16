"""
Unit tests for BitableClient.

Tests CRUD operations, batch operations, filters, and pagination.
"""

from unittest.mock import Mock

import pytest

from lark_service.clouddoc.bitable.client import BitableClient
from lark_service.clouddoc.models import FilterCondition
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError


class TestBitableClientValidation:
    """Test BitableClient validation logic."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create BitableClient instance."""
        return BitableClient(mock_credential_pool)

    def test_create_record_empty_fields(self, client):
        """Test create record fails with empty fields."""
        with pytest.raises(InvalidParameterError, match="Fields cannot be empty"):
            client.create_record(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                fields={},
            )

    def test_query_records_invalid_page_size(self, client):
        """Test query records fails with invalid page size."""
        # Test page_size < 1
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            client.query_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                page_size=0,
            )

        # Test page_size > 500
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            client.query_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                page_size=501,
            )

    def test_update_record_empty_fields(self, client):
        """Test update record fails with empty fields."""
        with pytest.raises(InvalidParameterError, match="Fields cannot be empty"):
            client.update_record(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                record_id="rec1234567890abcdefghij",
                fields={},
            )

    def test_batch_create_records_empty(self, client):
        """Test batch create fails with empty records."""
        with pytest.raises(InvalidParameterError, match="Records cannot be empty"):
            client.batch_create_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                records=[],
            )

    def test_batch_create_records_too_many(self, client):
        """Test batch create fails with more than 500 records."""
        records = [{"Name": f"User {i}"} for i in range(501)]
        with pytest.raises(InvalidParameterError, match="Too many records"):
            client.batch_create_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                records=records,
            )

    def test_batch_update_records_empty(self, client):
        """Test batch update fails with empty records."""
        with pytest.raises(InvalidParameterError, match="Records cannot be empty"):
            client.batch_update_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                records=[],
            )

    def test_batch_update_records_too_many(self, client):
        """Test batch update fails with more than 500 records."""
        records = [(f"rec{i}", {"Age": 30}) for i in range(501)]
        with pytest.raises(InvalidParameterError, match="Too many records"):
            client.batch_update_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                records=records,
            )

    def test_batch_delete_records_empty(self, client):
        """Test batch delete fails with empty record IDs."""
        with pytest.raises(InvalidParameterError, match="Record IDs cannot be empty"):
            client.batch_delete_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                record_ids=[],
            )

    def test_batch_delete_records_too_many(self, client):
        """Test batch delete fails with more than 500 record IDs."""
        record_ids = [f"rec{i}" for i in range(501)]
        with pytest.raises(InvalidParameterError, match="Too many record IDs"):
            client.batch_delete_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                record_ids=record_ids,
            )


class TestBitableClientOperations:
    """Test BitableClient CRUD operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create BitableClient instance."""
        return BitableClient(mock_credential_pool)

    def test_create_record_success(self, client):
        """Test create record succeeds."""
        fields = {"Name": "John Doe", "Age": 30, "Active": True}
        record = client.create_record(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            fields=fields,
        )

        assert record.record_id == "rec1234567890placeholder"
        assert record.fields == fields

    def test_query_records_with_filters(self, client):
        """Test query records with filter conditions."""
        filters = [
            FilterCondition(
                field_name="Age",
                operator="gte",
                value=18,
            ),
            FilterCondition(
                field_name="Active",
                operator="eq",
                value=True,
            ),
        ]

        records, next_token = client.query_records(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            filter_conditions=filters,
            page_size=50,
        )

        assert isinstance(records, list)
        assert next_token is None

    def test_query_records_pagination(self, client):
        """Test query records with pagination."""
        # First page
        records, next_token = client.query_records(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            page_size=100,
        )

        assert isinstance(records, list)

    def test_update_record_success(self, client):
        """Test update record succeeds."""
        fields = {"Age": 31}
        record = client.update_record(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            record_id="rec1234567890abcdefghij",
            fields=fields,
        )

        assert record.record_id == "rec1234567890abcdefghij"
        assert record.fields == fields

    def test_delete_record_success(self, client):
        """Test delete record succeeds."""
        result = client.delete_record(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            record_id="rec1234567890abcdefghij",
        )

        assert result is True

    def test_batch_create_records_success(self, client):
        """Test batch create records succeeds."""
        records = [
            {"Name": "John", "Age": 30},
            {"Name": "Jane", "Age": 25},
            {"Name": "Bob", "Age": 35},
        ]

        created = client.batch_create_records(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            records=records,
        )

        assert len(created) == 3
        for i, record in enumerate(created):
            assert record.record_id == f"rec1234567890placeholder{i}"
            assert record.fields == records[i]

    def test_batch_update_records_success(self, client):
        """Test batch update records succeeds."""
        updates = [
            ("rec1234567890abcdefghij", {"Age": 31}),
            ("rec4567890abcdefghijklmn", {"Age": 26}),
        ]

        updated = client.batch_update_records(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            records=updates,
        )

        assert len(updated) == 2
        for i, record in enumerate(updated):
            assert record.record_id == updates[i][0]
            assert record.fields == updates[i][1]

    def test_batch_delete_records_success(self, client):
        """Test batch delete records succeeds."""
        record_ids = ["rec1234567890abcdefghij", "rec4567890abcdefghijklmn", "rec7890abcdefghijklmnopq"]

        result = client.batch_delete_records(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            record_ids=record_ids,
        )

        assert result is True

    def test_list_fields_success(self, client):
        """Test list fields succeeds."""
        fields = client.list_fields(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
        )

        assert isinstance(fields, list)


class TestBitableClientFilters:
    """Test BitableClient filter functionality."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create BitableClient instance."""
        return BitableClient(mock_credential_pool)

    def test_filter_operators(self, client):
        """Test various filter operators."""
        operators = ["eq", "ne", "gt", "gte", "lt", "lte", "contains", "not_contains"]

        for operator in operators:
            filters = [
                FilterCondition(
                    field_name="Age",
                    operator=operator,
                    value=30,
                )
            ]

            # Should not raise
            records, _ = client.query_records(
                app_id="cli_test",
                app_token="bascn123",
                table_id="tbl123",
                filter_conditions=filters,
            )

    def test_multiple_filters(self, client):
        """Test multiple filter conditions."""
        filters = [
            FilterCondition(field_name="Age", operator="gte", value=18),
            FilterCondition(field_name="Age", operator="lt", value=65),
            FilterCondition(field_name="Active", operator="eq", value=True),
            FilterCondition(field_name="Department", operator="contains", value="Engineering"),
        ]

        records, _ = client.query_records(
            app_id="cli_test",
            app_token="bascn123",
            table_id="tbl123",
            filter_conditions=filters,
            page_size=50,
        )

        assert isinstance(records, list)
