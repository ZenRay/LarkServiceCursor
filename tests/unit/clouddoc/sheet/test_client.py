"""
Unit tests for SheetClient.

Tests data operations, formatting, and layout management.
"""

from unittest.mock import Mock

import pytest

from lark_service.clouddoc.sheet.client import SheetClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError


class TestSheetClientValidation:
    """Test SheetClient validation logic."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create SheetClient instance."""
        return SheetClient(mock_credential_pool)

    def test_get_sheet_data_empty_range(self, client):
        """Test get sheet data fails with empty range."""
        with pytest.raises(InvalidParameterError, match="Range string cannot be empty"):
            client.get_sheet_data(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="",
            )

    def test_update_sheet_data_empty_range(self, client):
        """Test update sheet data fails with empty range."""
        with pytest.raises(InvalidParameterError, match="Range string cannot be empty"):
            client.update_sheet_data(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="",
                values=[["test"]],
            )

    def test_update_sheet_data_empty_values(self, client):
        """Test update sheet data fails with empty values."""
        with pytest.raises(InvalidParameterError, match="Values cannot be empty"):
            client.update_sheet_data(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                values=[],
            )

    def test_format_cells_invalid_font_size(self, client):
        """Test format cells fails with invalid font size."""
        # Test font_size < 8
        with pytest.raises(InvalidParameterError, match="Invalid font_size"):
            client.format_cells(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                font_size=7,
            )

        # Test font_size > 72
        with pytest.raises(InvalidParameterError, match="Invalid font_size"):
            client.format_cells(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                font_size=73,
            )

    def test_format_cells_invalid_align(self, client):
        """Test format cells fails with invalid alignment."""
        with pytest.raises(InvalidParameterError, match="Invalid align"):
            client.format_cells(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                align="invalid",
            )

    def test_format_cells_invalid_vertical_align(self, client):
        """Test format cells fails with invalid vertical alignment."""
        with pytest.raises(InvalidParameterError, match="Invalid vertical_align"):
            client.format_cells(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                vertical_align="invalid",
            )

    def test_merge_cells_invalid_merge_type(self, client):
        """Test merge cells fails with invalid merge type."""
        with pytest.raises(InvalidParameterError, match="Invalid merge_type"):
            client.merge_cells(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                merge_type="invalid",
            )

    def test_set_column_width_invalid_range(self, client):
        """Test set column width fails with invalid range."""
        # Test start_column < 0
        with pytest.raises(InvalidParameterError, match="Invalid column range"):
            client.set_column_width(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_column=-1,
                end_column=2,
                width=150,
            )

        # Test end_column < start_column
        with pytest.raises(InvalidParameterError, match="Invalid column range"):
            client.set_column_width(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_column=5,
                end_column=2,
                width=150,
            )

    def test_set_column_width_invalid_width(self, client):
        """Test set column width fails with invalid width."""
        # Test width < 20
        with pytest.raises(InvalidParameterError, match="Invalid width"):
            client.set_column_width(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_column=0,
                end_column=2,
                width=19,
            )

        # Test width > 1000
        with pytest.raises(InvalidParameterError, match="Invalid width"):
            client.set_column_width(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_column=0,
                end_column=2,
                width=1001,
            )

    def test_set_row_height_invalid_range(self, client):
        """Test set row height fails with invalid range."""
        # Test start_row < 0
        with pytest.raises(InvalidParameterError, match="Invalid row range"):
            client.set_row_height(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_row=-1,
                end_row=2,
                height=30,
            )

        # Test end_row < start_row
        with pytest.raises(InvalidParameterError, match="Invalid row range"):
            client.set_row_height(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_row=5,
                end_row=2,
                height=30,
            )

    def test_set_row_height_invalid_height(self, client):
        """Test set row height fails with invalid height."""
        # Test height < 20
        with pytest.raises(InvalidParameterError, match="Invalid height"):
            client.set_row_height(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_row=0,
                end_row=2,
                height=19,
            )

        # Test height > 500
        with pytest.raises(InvalidParameterError, match="Invalid height"):
            client.set_row_height(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                start_row=0,
                end_row=2,
                height=501,
            )

    def test_freeze_panes_invalid_row_count(self, client):
        """Test freeze panes fails with invalid row count."""
        # Test freeze_row_count < 0
        with pytest.raises(InvalidParameterError, match="Invalid freeze_row_count"):
            client.freeze_panes(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                freeze_row_count=-1,
            )

        # Test freeze_row_count > 100
        with pytest.raises(InvalidParameterError, match="Invalid freeze_row_count"):
            client.freeze_panes(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                freeze_row_count=101,
            )

    def test_freeze_panes_invalid_column_count(self, client):
        """Test freeze panes fails with invalid column count."""
        # Test freeze_column_count < 0
        with pytest.raises(InvalidParameterError, match="Invalid freeze_column_count"):
            client.freeze_panes(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                freeze_column_count=-1,
            )

        # Test freeze_column_count > 26
        with pytest.raises(InvalidParameterError, match="Invalid freeze_column_count"):
            client.freeze_panes(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                freeze_column_count=27,
            )


class TestSheetClientOperations:
    """Test SheetClient operations."""

    @pytest.fixture
    def mock_credential_pool(self):
        """Create mock credential pool."""
        pool = Mock(spec=CredentialPool)
        return pool

    @pytest.fixture
    def client(self, mock_credential_pool):
        """Create SheetClient instance."""
        return SheetClient(mock_credential_pool)

    def test_get_sheet_data_success(self, client):
        """Test get sheet data succeeds."""
        data = client.get_sheet_data(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            range_str="A1:B10",
        )

        assert isinstance(data, list)

    def test_update_sheet_data_success(self, client):
        """Test update sheet data succeeds."""
        values = [
            ["Name", "Age"],
            ["John", 30],
            ["Jane", 25],
        ]

        result = client.update_sheet_data(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            range_str="A1:B3",
            values=values,
        )

        assert result is True

    def test_format_cells_all_options(self, client):
        """Test format cells with all formatting options."""
        result = client.format_cells(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            range_str="A1:B2",
            font_size=14,
            font_color="#FF0000",
            background_color="#EEEEEE",
            bold=True,
            italic=False,
            underline=True,
            align="center",
            vertical_align="middle",
        )

        assert result is True

    def test_format_cells_partial_options(self, client):
        """Test format cells with partial options."""
        result = client.format_cells(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            range_str="A1:B2",
            bold=True,
            font_size=12,
        )

        assert result is True

    def test_merge_cells_all_types(self, client):
        """Test merge cells with all merge types."""
        merge_types = ["merge_all", "merge_rows", "merge_columns"]

        for merge_type in merge_types:
            result = client.merge_cells(
                app_id="cli_test",
                spreadsheet_token="shtcn123",
                sheet_id="sheet1",
                range_str="A1:B2",
                merge_type=merge_type,
            )
            assert result is True

    def test_unmerge_cells_success(self, client):
        """Test unmerge cells succeeds."""
        result = client.unmerge_cells(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            range_str="A1:B2",
        )

        assert result is True

    def test_set_column_width_success(self, client):
        """Test set column width succeeds."""
        result = client.set_column_width(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            start_column=0,
            end_column=2,
            width=150,
        )

        assert result is True

    def test_set_row_height_success(self, client):
        """Test set row height succeeds."""
        result = client.set_row_height(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            start_row=0,
            end_row=0,
            height=30,
        )

        assert result is True

    def test_freeze_panes_success(self, client):
        """Test freeze panes succeeds."""
        result = client.freeze_panes(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            freeze_row_count=1,
            freeze_column_count=1,
        )

        assert result is True

    def test_freeze_panes_rows_only(self, client):
        """Test freeze panes with rows only."""
        result = client.freeze_panes(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            freeze_row_count=2,
            freeze_column_count=0,
        )

        assert result is True

    def test_freeze_panes_columns_only(self, client):
        """Test freeze panes with columns only."""
        result = client.freeze_panes(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
            freeze_row_count=0,
            freeze_column_count=3,
        )

        assert result is True

    def test_unfreeze_panes_success(self, client):
        """Test unfreeze panes succeeds."""
        result = client.unfreeze_panes(
            app_id="cli_test",
            spreadsheet_token="shtcn123",
            sheet_id="sheet1",
        )

        assert result is True
