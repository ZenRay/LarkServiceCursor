"""
End-to-end integration tests for Sheet client.

These tests use real Lark API credentials from .env.test file.
They are skipped if the required environment variables are not set.

Required environment variables:
- TEST_APP_ID: Lark application ID
- TEST_APP_SECRET: Lark application secret
- TEST_SHEET_TOKEN: Sheet spreadsheet token (read permission)
- TEST_WRITABLE_SHEET_TOKEN: Sheet spreadsheet token (write permission, optional)

Note: Sheet operations are currently placeholder implementations.
These tests will be enabled once the real API implementation is complete.
"""

import os

import pytest
from cryptography.fernet import Fernet

from lark_service.clouddoc.sheet.client import SheetClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager

# Check if integration test environment is configured
INTEGRATION_TEST_ENABLED = all(
    [
        os.getenv("TEST_APP_ID"),
        os.getenv("TEST_APP_SECRET"),
        os.getenv("TEST_SHEET_TOKEN"),
    ]
)

pytestmark = pytest.mark.skipif(
    not INTEGRATION_TEST_ENABLED,
    reason="Integration test environment not configured (missing TEST_APP_ID, TEST_APP_SECRET, or TEST_SHEET_TOKEN)",
)


@pytest.fixture(scope="module")
def credential_pool(tmp_path_factory):
    """Create credential pool with real credentials."""
    # Create temp directory for config DB
    tmp_dir = tmp_path_factory.mktemp("sheet_integration_test")
    config_db_path = tmp_dir / "test_config.db"

    # Generate encryption key
    encryption_key = Fernet.generate_key()

    # Create config
    config = Config(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "lark_service"),
        postgres_user=os.getenv("POSTGRES_USER", "lark_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "lark_password_123"),
        rabbitmq_host=os.getenv("RABBITMQ_HOST", "localhost"),
        rabbitmq_port=int(os.getenv("RABBITMQ_PORT", "5672")),
        rabbitmq_user=os.getenv("RABBITMQ_USER", "lark"),
        rabbitmq_password=os.getenv("RABBITMQ_PASSWORD", "rabbitmq_password_123"),
        config_encryption_key=encryption_key,
        config_db_path=config_db_path,
        log_level="INFO",
        max_retries=3,
        retry_backoff_base=1.0,
        token_refresh_threshold=0.1,
    )

    # Build postgres URL
    postgres_url = (
        f"postgresql://{config.postgres_user}:{config.postgres_password}"
        f"@{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
    )

    # Get test app credentials
    app_id = os.getenv("TEST_APP_ID", "")
    app_secret = os.getenv("TEST_APP_SECRET", "")

    # Create application manager and add test app
    app_manager = ApplicationManager(config.config_db_path, encryption_key)
    app_manager.add_application(
        app_id=app_id,
        app_name="Sheet Integration Test App",
        app_secret=app_secret,
    )

    # Create token storage
    token_storage = TokenStorageService(postgres_url)

    # Create credential pool
    pool = CredentialPool(
        config=config,
        app_manager=app_manager,
        token_storage=token_storage,
    )

    yield pool

    # Cleanup
    app_manager.close()


@pytest.fixture(scope="module")
def sheet_client(credential_pool):
    """Create Sheet client instance."""
    return SheetClient(credential_pool)


@pytest.fixture(scope="module")
def test_app_id():
    """Get test app ID."""
    return os.getenv("TEST_APP_ID", "")


@pytest.fixture(scope="module")
def test_sheet_token():
    """Get test sheet spreadsheet token."""
    return os.getenv("TEST_SHEET_TOKEN", "")


@pytest.fixture(scope="module")
def test_writable_sheet_token():
    """Get writable sheet spreadsheet token (optional)."""
    return os.getenv("TEST_WRITABLE_SHEET_TOKEN", "")


@pytest.mark.skip(
    reason="Sheet operations are placeholder implementations - enable when real API is implemented"
)
class TestSheetReadOperations:
    """Test Sheet read operations with real API."""

    def test_get_sheet_data_basic(self, sheet_client, test_app_id, test_sheet_token):
        """Test basic sheet data retrieval."""
        data = sheet_client.get_sheet_data(
            app_id=test_app_id,
            spreadsheet_token=test_sheet_token,
            sheet_id="sheet1",  # Adjust based on your test sheet
            range_str="A1:C10",
        )

        assert isinstance(data, list)
        print(f"✅ Retrieved {len(data)} rows from sheet")

    def test_get_sheet_data_with_range(self, sheet_client, test_app_id, test_sheet_token):
        """Test sheet data retrieval with specific range."""
        data = sheet_client.get_sheet_data(
            app_id=test_app_id,
            spreadsheet_token=test_sheet_token,
            sheet_id="sheet1",
            range_str="A1:A5",  # Single column
        )

        assert isinstance(data, list)
        print(f"✅ Retrieved {len(data)} rows from range A1:A5")


@pytest.mark.skip(
    reason="Sheet operations are placeholder implementations - enable when real API is implemented"
)
@pytest.mark.skipif(
    not os.getenv("TEST_WRITABLE_SHEET_TOKEN"),
    reason="Write operations require TEST_WRITABLE_SHEET_TOKEN",
)
class TestSheetWriteOperations:
    """Test Sheet write operations with real API (requires write permission)."""

    def test_update_sheet_data(self, sheet_client, test_app_id, test_writable_sheet_token):
        """Test updating sheet data."""
        values = [
            ["Test", "Data", "123"],
            ["Row2", "Col2", "456"],
        ]

        result = sheet_client.update_sheet_data(
            app_id=test_app_id,
            spreadsheet_token=test_writable_sheet_token,
            sheet_id="sheet1",
            range_str="A1:C2",
            values=values,
        )

        assert result is True
        print("✅ Updated sheet data successfully")

    def test_format_cells(self, sheet_client, test_app_id, test_writable_sheet_token):
        """Test cell formatting."""
        result = sheet_client.format_cells(
            app_id=test_app_id,
            spreadsheet_token=test_writable_sheet_token,
            sheet_id="sheet1",
            range_str="A1:A1",
            font_size=14,
            bold=True,
            background_color="#EEEEEE",
        )

        assert result is True
        print("✅ Formatted cells successfully")

    def test_merge_cells(self, sheet_client, test_app_id, test_writable_sheet_token):
        """Test merging cells."""
        result = sheet_client.merge_cells(
            app_id=test_app_id,
            spreadsheet_token=test_writable_sheet_token,
            sheet_id="sheet1",
            range_str="A1:B1",
            merge_type="merge_all",
        )

        assert result is True
        print("✅ Merged cells successfully")

        # Unmerge for cleanup
        sheet_client.unmerge_cells(
            app_id=test_app_id,
            spreadsheet_token=test_writable_sheet_token,
            sheet_id="sheet1",
            range_str="A1:B1",
        )


class TestSheetValidation:
    """Test parameter validation (doesn't require real API calls)."""

    def test_empty_range(self, sheet_client, test_app_id, test_sheet_token):
        """Test that empty range raises error."""
        with pytest.raises(InvalidParameterError, match="Range string cannot be empty"):
            sheet_client.get_sheet_data(
                app_id=test_app_id,
                spreadsheet_token=test_sheet_token,
                sheet_id="sheet1",
                range_str="",
            )

    def test_empty_values(self, sheet_client, test_app_id, test_sheet_token):
        """Test that empty values raise error."""
        with pytest.raises(InvalidParameterError, match="Values cannot be empty"):
            sheet_client.update_sheet_data(
                app_id=test_app_id,
                spreadsheet_token=test_sheet_token,
                sheet_id="sheet1",
                range_str="A1:A1",
                values=[],
            )

    def test_invalid_font_size(self, sheet_client, test_app_id, test_sheet_token):
        """Test that invalid font size raises error."""
        with pytest.raises(InvalidParameterError, match="Invalid font_size"):
            sheet_client.format_cells(
                app_id=test_app_id,
                spreadsheet_token=test_sheet_token,
                sheet_id="sheet1",
                range_str="A1:A1",
                font_size=100,  # Exceeds max
            )
