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

from lark_service.clouddoc.bitable.client import BitableClient
from lark_service.clouddoc.client import DocClient
from lark_service.clouddoc.models import ContentBlock, FilterCondition
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
    PermissionDeniedError,
)

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


@pytest.fixture
def bitable_client(credential_pool):
    """Create BitableClient for tests."""
    return BitableClient(credential_pool)


@pytest.fixture
def sheet_client(credential_pool):
    """Create SheetClient for tests."""
    from lark_service.clouddoc.sheet.client import SheetClient

    return SheetClient(credential_pool)


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
        # Note: title may be empty string if document has no title or requires additional permissions
        assert doc.title is not None  # Just verify it's not None
        print(f"✅ Document: '{doc.title}' ({doc.doc_id})")
        print(f"   Owner: {doc.owner_id}")
        print(f"   Created: {doc.create_time}")
        print(f"   Updated: {doc.update_time}")

    def test_get_document_not_found(self, doc_client, test_config):
        """Test get document raises NotFoundError for non-existent document."""
        with pytest.raises((NotFoundError, PermissionDeniedError, InvalidParameterError)):
            # Use a valid format but non-existent doc_id
            doc_client.get_document(
                app_id=test_config["app_id"],
                doc_id="NonExistentDocToken123456789",
            )

class TestBitableOperations:
    """Test Bitable operations - REMOVED old tests, see TestBitableCRUDOperations instead."""

    pass


class TestDocumentPermissions:
    """Test document permission management - REMOVED old test, see TestCloudDocPermissions instead."""

    pass


class TestSheetOperations:
    """Test Sheet operations - REMOVED old test, see TestSheetReadOperations and TestSheetWriteOperations instead."""

    pass


class TestDocumentWriteOperations:
    """Test document write operations."""

    def test_append_content_success(self, doc_client, test_config):
        """Test appending content blocks to document."""
        # Create content blocks
        blocks = [
            ContentBlock(
                block_type="paragraph",
                content="This is a test paragraph added by integration test.",
            ),
            ContentBlock(
                block_type="heading",
                content="Test Heading 1",
            ),
            ContentBlock(
                block_type="paragraph",
                content="Another paragraph after heading.",
            ),
        ]

        # Append content
        result = doc_client.append_content(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
            blocks=blocks,
        )

        # Verify success
        assert result is True
        print(f"✅ Successfully appended {len(blocks)} blocks to document")

    def test_append_content_empty_blocks(self, doc_client, test_config):
        """Test appending empty blocks raises error."""
        with pytest.raises(InvalidParameterError, match="Blocks cannot be empty"):
            doc_client.append_content(
                app_id=test_config["app_id"],
                doc_id=test_config["doc_token"],
                blocks=[],
            )

    def test_append_content_too_many_blocks(self, doc_client, test_config):
        """Test appending too many blocks raises error."""
        # Create 101 blocks (exceeds limit of 100)
        blocks = [ContentBlock(block_type="paragraph", content=f"Block {i}") for i in range(101)]

        with pytest.raises(InvalidParameterError, match="Too many blocks"):
            doc_client.append_content(
                app_id=test_config["app_id"],
                doc_id=test_config["doc_token"],
                blocks=blocks,
            )

    def test_append_content_various_block_types(self, doc_client, test_config):
        """Test appending various block types (excluding unsupported divider)."""
        # Note: Divider (block_type=11) is not supported by Feishu API
        blocks = [
            ContentBlock(block_type="heading", content="Heading Level 1"),
            ContentBlock(block_type="heading", content="Heading Level 2"),
            ContentBlock(block_type="heading", content="Heading Level 3"),
            ContentBlock(block_type="paragraph", content="Regular paragraph text."),
            ContentBlock(block_type="paragraph", content="Another paragraph."),
        ]

        result = doc_client.append_content(
            app_id=test_config["app_id"],
            doc_id=test_config["doc_token"],
            blocks=blocks,
        )

        assert result is True
        print(f"✅ Successfully appended {len(blocks)} blocks with various types")


class TestBitableQueryOperations:
    """Test Bitable query operations with real API."""

    def test_get_table_fields(self, bitable_client, test_config):
        """Test getting table fields."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")

        fields = bitable_client.get_table_fields(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id=table_id,
        )

        # Verify results
        assert isinstance(fields, list)
        assert len(fields) > 0

        # Check field structure
        first_field = fields[0]
        assert "field_id" in first_field
        assert "field_name" in first_field
        assert "type" in first_field
        assert "type_name" in first_field

        print(f"✅ Retrieved {len(fields)} fields from Bitable table")
        print(
            f"   First field: {first_field['field_name']} ({first_field['field_id']}) - {first_field['type_name']}"
        )

        # Print all fields for reference
        for field in fields:
            print(f"   - {field['field_name']}: {field['field_id']} ({field['type_name']})")

    def test_query_records_no_filter(self, bitable_client, test_config):
        """Test querying records without filter."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        # Get table ID from environment or use default
        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")

        records, next_token = bitable_client.query_records(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id=table_id,
            page_size=10,
        )

        # Verify results
        assert isinstance(records, list)
        print(f"✅ Retrieved {len(records)} records from Bitable")
        print(f"   Has more pages: {next_token is not None}")

        if records:
            print(f"   First record ID: {records[0].record_id}")
            print(f"   First record fields: {list(records[0].fields.keys())}")

    def test_query_records_with_structured_filter(self, bitable_client, test_config):
        """Test querying records with structured filter (using field_id)."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")

        # 1. Get table fields first
        fields = bitable_client.get_table_fields(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id=table_id,
        )

        # 2. Find the "文本" field
        text_field = next((f for f in fields if f["field_name"] == "文本"), None)
        if not text_field:
            pytest.skip("'文本' field not found in test table")

        field_name = text_field["field_name"]
        print(f"   Using field: {field_name} ({text_field['field_id']})")

        # 3. Create structured filter (使用 field_name)
        from lark_service.clouddoc.models import StructuredFilterCondition, StructuredFilterInfo

        filter_info = StructuredFilterInfo(
            conjunction="and",
            conditions=[
                StructuredFilterCondition(field_name=field_name, operator="is", value=["Active"])
            ],
        )

        # 4. Query records with filter
        records, next_token = bitable_client.query_records_structured(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id=table_id,
            filter_info=filter_info,
            page_size=10,
        )

        # Verify results
        assert isinstance(records, list)
        print(f"✅ Retrieved {len(records)} filtered records")
        print(f"   Filter: {text_field['field_name']} = 'Active'")

        if records:
            print(f"   First record: {records[0].fields.get(text_field['field_name'])}")

    def test_query_records_pagination(self, bitable_client, test_config):
        """Test pagination in query records."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")

        # First page
        records_page1, token1 = bitable_client.query_records(
            app_id=test_config["app_id"],
            app_token=test_config["bitable_token"],
            table_id=table_id,
            page_size=5,
        )

        print(f"✅ Page 1: {len(records_page1)} records")

        # If there's a next page, fetch it
        if token1:
            records_page2, token2 = bitable_client.query_records(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                page_size=5,
                page_token=token1,
            )

            print(f"✅ Page 2: {len(records_page2)} records")
            print(f"   Has more pages: {token2 is not None}")

            # Verify different pages
            if records_page1 and records_page2:
                assert records_page1[0].record_id != records_page2[0].record_id

    def test_query_records_invalid_page_size(self, bitable_client, test_config):
        """Test invalid page size raises error."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")

        # Test page_size too large
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            bitable_client.query_records(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                page_size=501,  # Exceeds max of 500
            )

        # Test page_size too small
        with pytest.raises(InvalidParameterError, match="Invalid page_size"):
            bitable_client.query_records(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                page_size=0,
            )

    def test_query_records_not_found(self, bitable_client, test_config):
        """Test querying non-existent table raises error."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        # Note: API returns APIError with "WrongTableId" for non-existent tables
        # This is expected behavior - the test verifies error handling works
        with pytest.raises((NotFoundError, InvalidParameterError, APIError)):
            bitable_client.query_records(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id="tbl_nonexistent_table_id",
                page_size=10,
            )


class TestBitableCRUDOperations:
    """Test Bitable CRUD operations with real API."""

    def test_create_update_delete_record(self, bitable_client, test_config):
        """Test complete CRUD workflow: create → update → delete."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")
        created_record_id = None

        try:
            # 1. 创建记录
            print("\n1️⃣ 测试创建记录...")
            record = bitable_client.create_record(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                fields={"文本": "测试记录 - CRUD Test"},
            )

            created_record_id = record.record_id
            assert record.record_id.startswith("rec")
            assert record.fields.get("文本") == "测试记录 - CRUD Test"
            print(f"   ✅ 创建成功: {record.record_id}")

            # 2. 更新记录
            print("\n2️⃣ 测试更新记录...")
            updated = bitable_client.update_record(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                record_id=created_record_id,
                fields={"文本": "测试记录 - 已更新"},
            )

            assert updated.record_id == created_record_id
            assert updated.fields.get("文本") == "测试记录 - 已更新"
            print(f"   ✅ 更新成功: {updated.record_id}")

            # 3. 删除记录
            print("\n3️⃣ 测试删除记录...")
            success = bitable_client.delete_record(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                record_id=created_record_id,
            )

            assert success is True
            print(f"   ✅ 删除成功: {created_record_id}")
            created_record_id = None  # 已删除
            print("\n🎉 CRUD 工作流测试通过！")

        except PermissionDeniedError as e:
            pytest.fail(
                f"权限不足: {e}\n请确保:\n"
                "1. 应用已添加 bitable:app 权限\n"
                "2. 应用已被添加为多维表格的协作者\n"
                "3. 应用具有'可编辑'权限"
            )

        finally:
            if created_record_id:
                try:
                    bitable_client.delete_record(
                        app_id=test_config["app_id"],
                        app_token=test_config["bitable_token"],
                        table_id=table_id,
                        record_id=created_record_id,
                    )
                    print(f"\n🧹 清理测试数据: {created_record_id}")
                except Exception:
                    pass

    def test_batch_create_records(self, bitable_client, test_config):
        """Test batch creating multiple records."""
        if not test_config.get("bitable_token"):
            pytest.skip("TEST_BITABLE_APP_TOKEN not configured")

        table_id = os.getenv("TEST_BITABLE_TABLE_ID", "tblEnSV2PfThFqBa")
        created_record_ids = []

        try:
            print("\n📦 测试批量创建记录...")
            records = bitable_client.batch_create_records(
                app_id=test_config["app_id"],
                app_token=test_config["bitable_token"],
                table_id=table_id,
                records=[
                    {"文本": "批量记录 1"},
                    {"文本": "批量记录 2"},
                    {"文本": "批量记录 3"},
                ],
            )

            assert len(records) == 3
            for i, record in enumerate(records, 1):
                assert record.record_id.startswith("rec")
                assert record.fields.get("文本") == f"批量记录 {i}"
                created_record_ids.append(record.record_id)
                print(f"   - 记录 {i}: {record.record_id}")

            print(f"   ✅ 批量创建成功: {len(records)} 条记录")

        except PermissionDeniedError as e:
            pytest.fail(
                f"权限不足: {e}\n请确保:\n"
                "1. 应用已添加 bitable:app 权限\n"
                "2. 应用已被添加为多维表格的协作者\n"
                "3. 应用具有'可编辑'权限"
            )

        finally:
            for record_id in created_record_ids:
                try:
                    bitable_client.delete_record(
                        app_id=test_config["app_id"],
                        app_token=test_config["bitable_token"],
                        table_id=table_id,
                        record_id=record_id,
                    )
                except Exception:
                    pass
            if created_record_ids:
                print(f"\n🧹 清理了 {len(created_record_ids)} 条测试数据")


class TestSheetReadOperations:
    """Test Sheet read operations with real API."""

    def test_get_sheet_info(self, sheet_client, test_config):
        """Test getting sheet information."""
        sheet_token = os.getenv("TEST_SHEET_TOKEN")
        if not sheet_token:
            pytest.skip("TEST_SHEET_TOKEN not configured")

        sheets = sheet_client.get_sheet_info(
            app_id=test_config["app_id"],
            spreadsheet_token=sheet_token,
        )

        # Verify results
        assert isinstance(sheets, list)
        assert len(sheets) > 0

        # Check sheet structure
        first_sheet = sheets[0]
        assert "sheet_id" in first_sheet
        assert "title" in first_sheet
        assert "index" in first_sheet

        print(f"✅ Retrieved {len(sheets)} sheets from spreadsheet")
        print(f"   First sheet: {first_sheet['title']} ({first_sheet['sheet_id']})")

        # Print all sheets for reference
        for sheet in sheets:
            row_info = f", {sheet.get('row_count', 'N/A')} rows" if sheet.get("row_count") else ""
            col_info = (
                f" x {sheet.get('column_count', 'N/A')} cols" if sheet.get("column_count") else ""
            )
            print(
                f"   - {sheet['title']}: {sheet['sheet_id']} (index: {sheet['index']}{row_info}{col_info})"
            )

    def test_get_sheet_data_success(self, sheet_client, test_config):
        """Test reading sheet data from specified range."""
        # Get sheet token and ID from environment
        sheet_token = os.getenv("TEST_SHEET_TOKEN")
        sheet_id = os.getenv("TEST_SHEET_ID", "sheet1")

        if not sheet_token:
            pytest.skip("TEST_SHEET_TOKEN not configured")

        # Read a small range
        data = sheet_client.get_sheet_data(
            app_id=test_config["app_id"],
            spreadsheet_token=sheet_token,
            sheet_id=sheet_id,
            range_str="A1:C5",
        )

        # Verify results
        assert isinstance(data, list)
        print(f"✅ Retrieved {len(data)} rows from sheet")

        if data and data[0]:
            print(f"   First row has {len(data[0])} cells")
            print(f"   First cell value: {data[0][0].value}")

    def test_get_sheet_data_empty_range(self, sheet_client, test_config):
        """Test reading empty range raises error."""
        sheet_token = os.getenv("TEST_SHEET_TOKEN")

        if not sheet_token:
            pytest.skip("TEST_SHEET_TOKEN not configured")

        with pytest.raises(InvalidParameterError, match="Range string cannot be empty"):
            sheet_client.get_sheet_data(
                app_id=test_config["app_id"],
                spreadsheet_token=sheet_token,
                sheet_id="sheet1",
                range_str="",
            )

    def test_get_sheet_data_not_found(self, sheet_client, test_config):
        """Test reading non-existent sheet raises error."""
        sheet_token = os.getenv("TEST_SHEET_TOKEN")
        if not sheet_token:
            pytest.skip("TEST_SHEET_TOKEN not configured")

        # Note: API returns APIError with "NOTEXIST" for non-existent sheets
        # This is expected behavior - the test verifies error handling works
        with pytest.raises((NotFoundError, InvalidParameterError, APIError)):
            sheet_client.get_sheet_data(
                app_id=test_config["app_id"],
                spreadsheet_token=sheet_token,
                sheet_id="nonexistent_sheet",
                range_str="A1:A1",
            )


class TestSheetWriteOperations:
    """Test Sheet write operations with real API."""

    def test_update_and_append_data(self, sheet_client, test_config):
        """Test updating and appending data to sheet."""
        sheet_token = os.getenv("TEST_SHEET_TOKEN")
        if not sheet_token:
            pytest.skip("TEST_SHEET_TOKEN not configured")

        # Get sheet info first
        sheets = sheet_client.get_sheet_info(
            app_id=test_config["app_id"],
            spreadsheet_token=sheet_token,
        )

        if not sheets:
            pytest.skip("No sheets found in spreadsheet")

        sheet_id = sheets[0]["sheet_id"]
        print(f"   Using sheet: {sheets[0]['title']} ({sheet_id})")

        try:
            # 1. 测试更新数据
            print("\n1️⃣ 测试更新数据...")
            success = sheet_client.update_sheet_data(
                app_id=test_config["app_id"],
                spreadsheet_token=sheet_token,
                sheet_id=sheet_id,
                range_str="A1:B2",
                values=[
                    ["测试标题1", "测试标题2"],
                    ["测试数据1", "测试数据2"],
                ],
            )

            assert success is True
            print("   ✅ 更新成功: A1:B2")

            # 2. 测试追加数据
            print("\n2️⃣ 测试追加数据...")
            success = sheet_client.append_data(
                app_id=test_config["app_id"],
                spreadsheet_token=sheet_token,
                sheet_id=sheet_id,
                range_str="A3:B3",
                values=[
                    ["追加数据1", "追加数据2"],
                ],
            )

            assert success is True
            print("   ✅ 追加成功: A3:B3")

            print("\n🎉 Sheet 写入操作测试通过！")

        except PermissionDeniedError as e:
            pytest.fail(
                f"权限不足: {e}\n请确保:\n"
                "1. 应用已添加 sheets:spreadsheet 权限\n"
                "2. 应用已被添加为电子表格的协作者\n"
                "3. 应用具有'可编辑'权限"
            )


class TestCloudDocPermissions:
    """Test CloudDoc permission management with real API."""

    def test_list_permissions(self, doc_client, test_config):
        """Test listing document permissions."""
        doc_token = test_config.get("doc_token")
        if not doc_token:
            pytest.skip("TEST_DOC_TOKEN not configured")

        # 注意：list_permissions API 需要新格式的 doc token (doxcn 开头)
        # 旧格式的 token 不支持此 API
        if not doc_token.startswith(("doxcn", "shtcn", "bascn", "wikicn")):
            pytest.skip("list_permissions requires new format doc token (doxcn/shtcn/bascn)")

        try:
            print("\n📋 测试列出文档权限...")
            permissions = doc_client.list_permissions(
                app_id=test_config["app_id"],
                doc_id=doc_token,
            )

            assert isinstance(permissions, list)
            print(f"   ✅ 获取到 {len(permissions)} 个权限")

            # 打印权限详情
            for i, perm in enumerate(permissions[:5], 1):  # 只显示前5个
                print(
                    f"   - 权限 {i}: {perm.member_type} ({perm.permission_type})"
                )

            print("\n🎉 列出权限测试通过！")

        except PermissionDeniedError as e:
            pytest.fail(
                f"权限不足: {e}\n请确保:\n"
                "1. 应用已添加 docx:document 权限\n"
                "2. 应用已被添加为文档协作者"
            )

    def test_update_block(self, doc_client, test_config):
        """Test updating document block."""
        doc_token = test_config.get("doc_token")
        if not doc_token:
            pytest.skip("TEST_DOC_TOKEN not configured")

        # 注意：这个测试需要知道一个有效的 block_id
        # 由于我们没有简单的方法获取 block_id，这里先跳过
        pytest.skip("需要有效的 block_id 才能测试")

        # 如果有 block_id，可以这样测试：
        # block = ContentBlock(
        #     block_type="paragraph",
        #     content="Updated content from integration test"
        # )
        #
        # success = doc_client.update_block(
        #     app_id=test_config["app_id"],
        #     doc_id=doc_token,
        #     block_id="block_xxx",
        #     block=block
        # )
        #
        # assert success is True


class TestErrorHandling:
    """Test error handling in CloudDoc operations."""

    def test_invalid_doc_id_format(self, doc_client, test_config):
        """Test invalid document ID format raises error."""
        with pytest.raises((InvalidParameterError, NotFoundError)):
            doc_client.get_document(
                app_id=test_config["app_id"],
                doc_id="invalid_doc_id",
            )

    def test_permission_denied(self, doc_client, test_config):
        """Test permission denied is handled correctly."""
        # Skip: requires a specific document without access permissions
        pytest.skip("Permission denied test requires environment-specific setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
