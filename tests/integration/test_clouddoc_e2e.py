"""
Integration tests for CloudDoc module.

Tests document operations, Bitable CRUD, and Sheet operations with real Feishu API.

Prerequisites:
- .env.test configured with TEST_APP_ID, TEST_APP_SECRET
- TEST_DOC_TOKEN: A test document you have write access to
- TEST_BITABLE_APP_TOKEN: A test Bitable you have write access to
- Valid Feishu app with docx:document scope
"""

import os

import pytest
from dotenv import load_dotenv

from lark_service.clouddoc.client import DocClient
from lark_service.clouddoc.models import ContentBlock
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import NotFoundError, PermissionDeniedError

# Load test environment variables
load_dotenv(".env.test")


@pytest.fixture(scope="module")
def test_config():
    """Load test configuration from .env.test."""
    config = {
        "app_id": os.getenv("TEST_APP_ID"),
        "app_secret": os.getenv("TEST_APP_SECRET"),
        "doc_token": os.getenv("TEST_DOC_TOKEN"),
        "bitable_token": os.getenv("TEST_BITABLE_APP_TOKEN"),
    }

    # Validate required config
    missing = [k for k, v in config.items() if not v]
    if missing:
        pytest.skip(f"Missing required config: {', '.join(missing)}")

    return config


@pytest.fixture(scope="module")
def credential_pool(test_config, tmp_path_factory):
    """Create credential pool for tests."""
    from pathlib import Path

    from cryptography.fernet import Fernet

    from lark_service.core.config import Config
    from lark_service.core.storage.postgres_storage import TokenStorageService
    from lark_service.core.storage.sqlite_storage import ApplicationManager

    # Create temp directory for config DB
    tmp_dir = tmp_path_factory.mktemp("integration_test")
    config_db_path = tmp_dir / "test_config.db"

    # Generate encryption key
    encryption_key = Fernet.generate_key()

    # Create config
    config = Config(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "lark_service"),
        postgres_user=os.getenv("POSTGRES_USER", "lark"),
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

    # Create application manager and add test app
    app_manager = ApplicationManager(config_db_path, encryption_key)
    app_manager.add_application(
        app_id=test_config["app_id"],
        app_name="Integration Test App",
        app_secret=test_config["app_secret"],
    )

    # Create database URL
    db_url = (
        f"postgresql://{config.postgres_user}:{config.postgres_password}"
        f"@{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
    )

    # Create token storage
    token_storage = TokenStorageService(
        postgres_url=db_url,
    )

    # Create credential pool
    pool = CredentialPool(
        config=config,
        app_manager=app_manager,
        token_storage=token_storage,
    )

    yield pool

    # Cleanup
    app_manager.close()
    if config_db_path.exists():
        config_db_path.unlink()


@pytest.fixture
def doc_client(credential_pool):
    """Create DocClient for tests."""
    return DocClient(credential_pool)


class TestDocumentOperations:
    """Test document read operations."""

    def test_get_document_success(self, doc_client, test_config):
        """Test get document returns valid document info."""
        doc = doc_client.get_document(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
        )

        # Verify document data
        assert doc is not None
        assert doc.doc_id == test_config["doc_token"]
        assert doc.title
        print(f"✅ Document: {doc.title} ({doc.doc_id})")

    def test_get_document_not_found(self, doc_client, test_config):
        """Test get document raises NotFoundError for non-existent document."""
        with pytest.raises((NotFoundError, PermissionDeniedError)):
            doc_client.get_document(
                app_id=test_config["app_id"],
                doc_id="doxcn_nonexistent_1234567890",
            )

    @pytest.mark.skip(reason="Requires write permission - may modify test document")
    def test_append_blocks_to_document(self, doc_client, test_config):
        """Test append content blocks to document."""
        # Create test blocks
        blocks = [
            ContentBlock(
                block_type="text",
                content="Integration test - text block",
            ),
            ContentBlock(
                block_type="heading",
                content="Integration Test Heading",
                attributes={"level": 2},
            ),
        ]

        # Append blocks
        result = doc_client.append_blocks(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
            blocks=blocks,
        )

        assert result is True
        print(f"✅ Appended {len(blocks)} blocks to document")


class TestBitableOperations:
    """Test Bitable operations."""

    @pytest.mark.skip(reason="Requires Bitable setup and write permission")
    def test_bitable_crud_operations(self, doc_client, test_config):
        """Test Bitable CRUD operations."""
        from lark_service.clouddoc.bitable.client import BitableClient

        bitable_client = BitableClient(doc_client.credential_pool)

        # Create a test record
        test_record = {
            "Name": "Integration Test Record",
            "Status": "Active",
            "Count": 42,
        }

        # Create record
        created = bitable_client.create_record(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id="tbl_test",  # Replace with actual table_id
            fields=test_record,
        )

        assert created is not None
        assert created.record_id
        print(f"✅ Created record: {created.record_id}")

        # Read record
        record = bitable_client.get_record(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id="tbl_test",
            record_id=created.record_id,
        )

        assert record is not None
        assert record.fields["Name"] == "Integration Test Record"
        print(f"✅ Read record: {record.fields}")

        # Update record
        updated = bitable_client.update_record(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id="tbl_test",
            record_id=created.record_id,
            fields={"Status": "Completed"},
        )

        assert updated is True
        print("✅ Updated record")

        # Delete record
        deleted = bitable_client.delete_record(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id="tbl_test",
            record_id=created.record_id,
        )

        assert deleted is True
        print("✅ Deleted record")

    @pytest.mark.skip(reason="Requires Bitable setup")
    def test_bitable_query_with_filter(self, doc_client, test_config):
        """Test Bitable query with filter conditions."""
        from lark_service.clouddoc.bitable.client import BitableClient
        from lark_service.clouddoc.models import FilterCondition, QueryFilter

        bitable_client = BitableClient(doc_client.credential_pool)

        # Create filter
        filter_obj = QueryFilter(
            conditions=[
                FilterCondition(
                    field_name="Status",
                    operator="eq",
                    value="Active",
                ),
            ],
            logic="and",
        )

        # Query records
        records, has_more = bitable_client.query_records(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id="tbl_test",
            filter=filter_obj,
            page_size=10,
        )

        assert isinstance(records, list)
        print(f"✅ Queried {len(records)} records with filter")


class TestDocumentPermissions:
    """Test document permission management."""

    @pytest.mark.skip(reason="Requires permission management scope")
    def test_grant_and_revoke_permission(self, doc_client, test_config):
        """Test grant and revoke document permissions."""
        test_user_id = "ou_test_user_1234567890abc"

        # Grant read permission
        granted = doc_client.grant_permission(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
            member_type="user",
            member_id=test_user_id,
            permission_type="read",
        )

        assert granted is True
        print(f"✅ Granted read permission to {test_user_id}")

        # List permissions
        permissions = doc_client.list_permissions(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
        )

        assert any(p.member_id == test_user_id for p in permissions)
        print(f"✅ Listed {len(permissions)} permissions")

        # Revoke permission
        revoked = doc_client.revoke_permission(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
            member_type="user",
            member_id=test_user_id,
        )

        assert revoked is True
        print(f"✅ Revoked permission from {test_user_id}")


class TestSheetOperations:
    """Test Sheet operations."""

    @pytest.mark.skip(reason="Requires Sheet setup and write permission")
    def test_sheet_read_write(self, doc_client, test_config):
        """Test Sheet read and write operations."""
        from lark_service.clouddoc.sheet.client import SheetClient
        from lark_service.clouddoc.models import SheetRange

        sheet_client = SheetClient(doc_client.credential_pool)

        # Define range
        range_obj = SheetRange(
            sheet_id="sheet_test",
            range_notation="A1:B2",
        )

        # Write data
        data = [
            ["Name", "Value"],
            ["Test", "123"],
        ]

        written = sheet_client.write_range(
            app_id=test_config["app_id"],
            spreadsheet_token="shtcn_test",
            range=range_obj,
            values=data,
        )

        assert written is True
        print("✅ Wrote data to sheet")

        # Read data
        read_data = sheet_client.read_range(
            app_id=test_config["app_id"],
            spreadsheet_token="shtcn_test",
            range=range_obj,
        )

        assert len(read_data) == 2
        assert read_data[0][0] == "Name"
        print(f"✅ Read {len(read_data)} rows from sheet")


class TestErrorHandling:
    """Test error handling in CloudDoc operations."""

    def test_invalid_doc_id_format(self, doc_client, test_config):
        """Test invalid document ID format raises error."""
        with pytest.raises(Exception):  # ValidationError or InvalidParameterError
            doc_client.get_document(
                app_id=test_config["app_id"],
                doc_id="invalid_doc_id",
            )

    def test_permission_denied(self, doc_client, test_config):
        """Test permission denied is handled correctly."""
        # Try to access a document without permission
        with pytest.raises((NotFoundError, PermissionDeniedError)):
            doc_client.get_document(
                app_id=test_config["app_id"],
                doc_id="doxcn_no_permission_123456",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
