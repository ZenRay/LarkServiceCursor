"""
End-to-end integration tests for Bitable client.

These tests use real Lark API credentials from .env.test file.
They are skipped if the required environment variables are not set.

Required environment variables:
- TEST_APP_ID: Lark application ID
- TEST_APP_SECRET: Lark application secret
- TEST_BITABLE_APP_TOKEN: Bitable app token (read permission)
- TEST_WRITABLE_BITABLE_TOKEN: Bitable app token (write permission, optional)
"""

import os

import pytest

from lark_service.clouddoc.bitable.client import BitableClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError

# Check if integration test environment is configured
INTEGRATION_TEST_ENABLED = all(
    [
        os.getenv("TEST_APP_ID"),
        os.getenv("TEST_APP_SECRET"),
        os.getenv("TEST_BITABLE_APP_TOKEN"),
    ]
)

pytestmark = pytest.mark.skipif(
    not INTEGRATION_TEST_ENABLED,
    reason="Integration test environment not configured (missing TEST_APP_ID, TEST_APP_SECRET, or TEST_BITABLE_APP_TOKEN)",
)


@pytest.fixture(scope="module")
def credential_pool(tmp_path_factory):
    """Create credential pool with real credentials."""
    from cryptography.fernet import Fernet

    from lark_service.core.config import Config
    from lark_service.core.storage.postgres_storage import TokenStorageService
    from lark_service.core.storage.sqlite_storage import ApplicationManager

    # Create temp directory for config DB
    tmp_dir = tmp_path_factory.mktemp("bitable_integration_test")
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
        rabbitmq_host=os.getenv("POSTGRES_HOST", "localhost"),
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

    # Get test credentials
    app_id = os.getenv("TEST_APP_ID", "")
    app_secret = os.getenv("TEST_APP_SECRET", "")

    # Create application manager and add test app
    app_manager = ApplicationManager(config_db_path, encryption_key)
    app_manager.add_application(
        app_id=app_id,
        app_name="Bitable Integration Test App",
        app_secret=app_secret,
    )

    # Create token storage
    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    token_storage = TokenStorageService(postgres_url=db_url)

    # Create credential pool
    pool = CredentialPool(config, app_manager, token_storage)

    return pool


@pytest.fixture(scope="module")
def bitable_client(credential_pool):
    """Create Bitable client instance."""
    return BitableClient(credential_pool)


@pytest.fixture(scope="module")
def test_app_id():
    """Get test app ID."""
    return os.getenv("TEST_APP_ID", "")


@pytest.fixture(scope="module")
def test_bitable_token():
    """Get test bitable app token."""
    return os.getenv("TEST_BITABLE_APP_TOKEN", "")


@pytest.fixture(scope="module")
def test_bitable_table_id():
    """Get test bitable table ID."""
    return os.getenv("TEST_BITABLE_TABLE_ID", "")


@pytest.fixture(scope="module")
def test_writable_bitable_token(test_bitable_token):
    """Get writable bitable app token (optional).

    If TEST_WRITABLE_BITABLE_TOKEN is not set, use TEST_BITABLE_APP_TOKEN
    (assuming the app has write permissions configured).
    """
    return os.getenv("TEST_WRITABLE_BITABLE_TOKEN", test_bitable_token)


class TestBitableReadOperations:
    """Test Bitable read operations with real API."""

    def test_query_records_basic(
        self, bitable_client, test_app_id, test_bitable_token, test_bitable_table_id
    ):
        """Test basic record query."""
        if not test_bitable_table_id:
            pytest.skip("TEST_BITABLE_TABLE_ID not configured")

        records, next_token = bitable_client.query_records(
            app_id=test_app_id,
            app_token=test_bitable_token,
            table_id=test_bitable_table_id,
            page_size=10,
        )

        assert isinstance(records, list)
        # Records might be empty, that's OK
        print(f"\n✅ Query returned {len(records)} records")
        if records:
            print(f"   First record fields: {list(records[0].fields.keys())}")

    def test_query_records_with_pagination(
        self, bitable_client, test_app_id, test_bitable_token, test_bitable_table_id
    ):
        """Test record query with pagination."""
        if not test_bitable_table_id:
            pytest.skip("TEST_BITABLE_TABLE_ID not configured")

        # Query first page
        records, next_token = bitable_client.query_records(
            app_id=test_app_id,
            app_token=test_bitable_token,
            table_id=test_bitable_table_id,
            page_size=5,
        )

        assert isinstance(records, list)
        print(f"\n✅ First page returned {len(records)} records")

        if next_token:
            # Query second page
            records2, next_token2 = bitable_client.query_records(
                app_id=test_app_id,
                app_token=test_bitable_token,
                table_id=test_bitable_table_id,
                page_size=5,
                page_token=next_token,
            )
            assert isinstance(records2, list)
            print(f"   Second page returned {len(records2)} records")


@pytest.mark.skipif(
    not os.getenv("TEST_WRITABLE_BITABLE_TOKEN") and not os.getenv("TEST_BITABLE_APP_TOKEN"),
    reason="Write operations require TEST_WRITABLE_BITABLE_TOKEN or TEST_BITABLE_APP_TOKEN with write permission",
)
class TestBitableWriteOperations:
    """Test Bitable write operations with real API (requires write permission)."""

    def test_create_and_delete_record(
        self, bitable_client, test_app_id, test_writable_bitable_token, test_bitable_table_id
    ):
        """Test creating and deleting a record."""
        if not test_bitable_table_id:
            pytest.skip("TEST_BITABLE_TABLE_ID not configured")

        # First, get the table fields to know what fields we can use
        fields_list = bitable_client.list_fields(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
        )

        print(f"\n📋 Available fields: {[f.field_name for f in fields_list]}")

        if not fields_list:
            pytest.skip("No fields available in the table")

        # Use the first text field for testing
        test_field = fields_list[0]
        fields = {
            test_field.field_name: "Integration Test Record",
        }

        record = bitable_client.create_record(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
            fields=fields,
        )

        assert record.record_id
        print(f"✅ Created record: {record.record_id}")

        # Clean up: delete the test record
        result = bitable_client.delete_record(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
            record_id=record.record_id,
        )

        assert result is True
        print(f"✅ Deleted record: {record.record_id}")

    def test_update_record(
        self, bitable_client, test_app_id, test_writable_bitable_token, test_bitable_table_id
    ):
        """Test updating a record."""
        if not test_bitable_table_id:
            pytest.skip("TEST_BITABLE_TABLE_ID not configured")

        # First, get the table fields
        fields_list = bitable_client.list_fields(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
        )

        if not fields_list:
            pytest.skip("No fields available in the table")

        # Create a test record first
        test_field = fields_list[0]
        fields = {
            test_field.field_name: "Test Record for Update",
        }

        record = bitable_client.create_record(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
            fields=fields,
        )

        print(f"\n📝 Created test record: {record.record_id}")

        # Update the record
        updated_fields = {
            test_field.field_name: "Updated by Integration Test",
        }
        updated_record = bitable_client.update_record(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
            record_id=record.record_id,
            fields=updated_fields,
        )

        assert updated_record.record_id == record.record_id
        print(f"✅ Updated record: {updated_record.record_id}")

        # Clean up: delete the test record
        bitable_client.delete_record(
            app_id=test_app_id,
            app_token=test_writable_bitable_token,
            table_id=test_bitable_table_id,
            record_id=record.record_id,
        )
        print("✅ Cleaned up test record")


class TestBitableValidation:
    """Test parameter validation (doesn't require real API calls)."""

    def test_invalid_page_size(
        self, bitable_client, test_app_id, test_bitable_token, test_bitable_table_id
    ):
        """Test that invalid page size raises error."""
        if not test_bitable_table_id:
            pytest.skip("TEST_BITABLE_TABLE_ID not configured")

        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            bitable_client.query_records(
                app_id=test_app_id,
                app_token=test_bitable_token,
                table_id=test_bitable_table_id,
                page_size=501,  # Exceeds max
            )
        print("\n✅ Invalid page size correctly rejected")

    def test_empty_fields(
        self, bitable_client, test_app_id, test_bitable_token, test_bitable_table_id
    ):
        """Test that empty fields raise error."""
        if not test_bitable_table_id:
            pytest.skip("TEST_BITABLE_TABLE_ID not configured")

        with pytest.raises(InvalidParameterError, match="Fields cannot be empty"):
            bitable_client.create_record(
                app_id=test_app_id,
                app_token=test_bitable_token,
                table_id=test_bitable_table_id,
                fields={},
            )
        print("\n✅ Empty fields correctly rejected")
