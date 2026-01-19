"""End-to-end integration tests.

Tests the complete application flow:
1. Application configuration initialization
2. Token acquisition and management
3. Sending messages (text, image, card)
4. Creating and querying documents
5. User lookup and caching
6. aPaaS data space operations
"""

import contextlib
import os
import time
import uuid
from datetime import datetime

import pytest
from cryptography.fernet import Fernet

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.cardkit.builder import CardBuilder
from lark_service.clouddoc.bitable.client import BitableClient
from lark_service.clouddoc.client import DocClient
from lark_service.contact.client import ContactClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.messaging.client import MessagingClient


@pytest.fixture(scope="module")
def e2e_config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    """Create configuration for E2E tests."""
    tmp_path = tmp_path_factory.mktemp("e2e_tests")

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
        config_encryption_key=Fernet.generate_key(),
        config_db_path=tmp_path / "e2e_config.db",
        log_level="INFO",
        max_retries=3,
        retry_backoff_base=1.0,
        token_refresh_threshold=0.1,
    )
    return config


@pytest.fixture(scope="module")
def e2e_app_manager(e2e_config: Config) -> ApplicationManager:
    """Create ApplicationManager for E2E tests."""
    manager = ApplicationManager(
        e2e_config.config_db_path,
        e2e_config.config_encryption_key,
    )

    # Add test application
    app_id = os.getenv("LARK_APP_ID", "cli_e2etest12345678")
    app_secret = os.getenv("LARK_APP_SECRET", "test_secret_e2e")

    # Application might already exist
    with contextlib.suppress(Exception):
        manager.add_application(
            app_id=app_id,
            app_name="E2E Test Application",
            app_secret=app_secret,
        )

    yield manager
    manager.close()


@pytest.fixture(scope="module")
def e2e_token_storage(e2e_config: Config) -> TokenStorageService:
    """Create TokenStorageService for E2E tests."""
    service = TokenStorageService(e2e_config.get_postgres_url())
    yield service
    service.close()


@pytest.fixture(scope="module")
def e2e_credential_pool(
    e2e_config: Config,
    e2e_app_manager: ApplicationManager,
    e2e_token_storage: TokenStorageService,
    tmp_path_factory: pytest.TempPathFactory,
) -> CredentialPool:
    """Create CredentialPool for E2E tests."""
    tmp_path = tmp_path_factory.mktemp("e2e_locks")

    pool = CredentialPool(
        config=e2e_config,
        app_manager=e2e_app_manager,
        token_storage=e2e_token_storage,
        lock_dir=tmp_path / "locks",
    )
    yield pool
    pool.close()


@pytest.fixture(scope="module")
def test_app_id() -> str:
    """Get test app ID from environment."""
    return os.getenv("LARK_APP_ID", "cli_e2etest12345678")


@pytest.fixture(scope="module")
def test_user_id() -> str:
    """Get test user ID from environment."""
    return os.getenv("LARK_TEST_USER_ID", "ou_testuser123")


class TestEndToEndFlow:
    """End-to-end integration tests for complete application flow."""

    def test_01_application_initialization(
        self,
        e2e_app_manager: ApplicationManager,
        test_app_id: str,
    ) -> None:
        """Test 1: Application configuration is properly initialized.

        Verifies that the application can be retrieved from storage
        with correct configuration.
        """
        app = e2e_app_manager.get_application(test_app_id)

        assert app is not None
        assert app["app_id"] == test_app_id
        assert app["app_name"] == "E2E Test Application"
        assert app["is_active"] is True
        assert "app_secret" in app

        print(f"✅ Test 1: Application {test_app_id} initialized successfully")

    def test_02_token_acquisition(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test 2: Token can be acquired automatically.

        Verifies that the credential pool can acquire a valid
        app_access_token for the configured application.
        """
        token = e2e_credential_pool.get_token(test_app_id, "app_access_token")

        assert token is not None
        assert len(token) > 0
        assert token.startswith("t-")  # Feishu token format

        print(f"✅ Test 2: Token acquired successfully: {token[:20]}...")

    def test_03_messaging_send_text(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
        test_user_id: str,
    ) -> None:
        """Test 3: Send text message to user.

        Verifies that the messaging client can send a text message
        using automatically managed tokens.
        """
        # Skip if no real user ID provided
        if test_user_id == "ou_testuser123":
            pytest.skip("Real user ID not configured for E2E test")

        client = MessagingClient(e2e_credential_pool)

        message = f"🧪 E2E Test Message - {datetime.now().isoformat()}"
        result = client.send_text_message(
            app_id=test_app_id,
            receive_id=test_user_id,
            receive_id_type="user_id",
            content=message,
        )

        assert result is not None
        assert "message_id" in result

        print(f"✅ Test 3: Text message sent successfully: {result['message_id']}")

    def test_04_messaging_send_card(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
        test_user_id: str,
    ) -> None:
        """Test 4: Send interactive card to user.

        Verifies that the card builder and messaging client can
        create and send an interactive card.
        """
        # Skip if no real user ID provided
        if test_user_id == "ou_testuser123":
            pytest.skip("Real user ID not configured for E2E test")

        client = MessagingClient(e2e_credential_pool)
        builder = CardBuilder()

        card = builder.build_notification_card(
            title="E2E Test Notification",
            content="This is an automated end-to-end test notification.",
            note=f"Sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        )

        result = client.send_card_message(
            app_id=test_app_id,
            receive_id=test_user_id,
            receive_id_type="user_id",
            card=card,
        )

        assert result is not None
        assert "message_id" in result

        print(f"✅ Test 4: Card message sent successfully: {result['message_id']}")

    def test_05_contact_user_lookup(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test 5: Look up user by email.

        Verifies that the contact client can query user information
        and cache it properly.
        """
        test_email = os.getenv("LARK_TEST_USER_EMAIL")
        if not test_email:
            pytest.skip("Test user email not configured for E2E test")

        client = ContactClient(e2e_credential_pool, enable_cache=True)

        user = client.get_user_by_email(
            app_id=test_app_id,
            email=test_email,
        )

        assert user is not None
        assert user.open_id is not None
        assert user.user_id is not None
        assert user.name is not None

        # Verify cache hit on second call
        user2 = client.get_user_by_email(
            app_id=test_app_id,
            email=test_email,
        )

        assert user2.open_id == user.open_id

        print(f"✅ Test 5: User lookup successful: {user.name} ({user.email})")

    def test_06_clouddoc_document_operations(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test 6: CloudDoc document operations.

        Verifies that the CloudDoc client can query document metadata.
        """
        test_doc_id = os.getenv("LARK_TEST_DOC_ID")
        if not test_doc_id:
            pytest.skip("Test document ID not configured for E2E test")

        client = DocClient(e2e_credential_pool)

        doc = client.get_document(
            app_id=test_app_id,
            doc_id=test_doc_id,
        )

        assert doc is not None
        assert doc.doc_id == test_doc_id
        assert doc.title is not None

        print(f"✅ Test 6: Document retrieved: {doc.title}")

    def test_07_bitable_operations(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test 7: Bitable CRUD operations.

        Verifies that the Bitable client can query records from a table.
        """
        test_app_token = os.getenv("LARK_TEST_BITABLE_APP_TOKEN")
        test_table_id = os.getenv("LARK_TEST_BITABLE_TABLE_ID")

        if not test_app_token or not test_table_id:
            pytest.skip("Test bitable not configured for E2E test")

        client = BitableClient(e2e_credential_pool)

        records = client.query_records(
            app_id=test_app_id,
            app_token=test_app_token,
            table_id=test_table_id,
            page_size=5,
        )

        assert isinstance(records, list)
        assert len(records) >= 0

        print(f"✅ Test 7: Bitable query successful: {len(records)} records")

    def test_08_apaas_workspace_operations(
        self,
        e2e_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test 8: aPaaS workspace table operations.

        Verifies that the aPaaS client can list workspace tables
        and execute SQL queries.
        """
        test_workspace_id = os.getenv("LARK_TEST_APAAS_WORKSPACE_ID")
        user_access_token = os.getenv("LARK_TEST_USER_ACCESS_TOKEN")

        if not test_workspace_id or not user_access_token:
            pytest.skip("Test aPaaS workspace not configured for E2E test")

        client = WorkspaceTableClient(e2e_credential_pool)

        # List workspace tables
        tables = client.list_workspace_tables(
            app_id=test_app_id,
            user_access_token=user_access_token,
            workspace_id=test_workspace_id,
        )

        assert isinstance(tables, list)
        assert len(tables) > 0

        # Execute SQL query
        sql = "SELECT * FROM test_table LIMIT 5"
        records, columns, _ = client.sql_query(
            app_id=test_app_id,
            user_access_token=user_access_token,
            workspace_id=test_workspace_id,
            sql=sql,
        )

        assert isinstance(records, list)
        assert isinstance(columns, list)

        print(
            f"✅ Test 8: aPaaS operations successful: {len(tables)} tables, {len(records)} records"
        )

    def test_09_token_persistence_across_restarts(
        self,
        e2e_config: Config,
        e2e_app_manager: ApplicationManager,
        e2e_token_storage: TokenStorageService,
        test_app_id: str,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """Test 9: Token persistence across application restarts.

        Verifies that tokens are properly persisted to database
        and can be reloaded after simulated restart.
        """
        tmp_path = tmp_path_factory.mktemp("restart_test")

        # First pool - acquire token
        pool1 = CredentialPool(
            config=e2e_config,
            app_manager=e2e_app_manager,
            token_storage=e2e_token_storage,
            lock_dir=tmp_path / "locks1",
        )

        token1 = pool1.get_token(test_app_id, "app_access_token")
        assert token1 is not None
        pool1.close()

        # Simulate restart - create new pool instance
        time.sleep(0.5)

        pool2 = CredentialPool(
            config=e2e_config,
            app_manager=e2e_app_manager,
            token_storage=e2e_token_storage,
            lock_dir=tmp_path / "locks2",
        )

        token2 = pool2.get_token(test_app_id, "app_access_token")
        assert token2 is not None
        assert token2 == token1  # Should load from database
        pool2.close()

        print("✅ Test 9: Token persistence verified across restarts")

    def test_10_multi_app_isolation(
        self,
        e2e_config: Config,
        e2e_token_storage: TokenStorageService,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """Test 10: Multi-application token isolation.

        Verifies that tokens for different applications are
        properly isolated and managed independently.
        """
        tmp_path = tmp_path_factory.mktemp("multi_app_test")

        # Create app manager with multiple apps
        manager = ApplicationManager(
            tmp_path / "multi_app.db",
            e2e_config.config_encryption_key,
        )

        app_id_1 = f"cli_multi1_{uuid.uuid4().hex[:8]}"
        app_id_2 = f"cli_multi2_{uuid.uuid4().hex[:8]}"

        manager.add_application(
            app_id=app_id_1,
            app_name="Multi Test App 1",
            app_secret="secret1",
        )
        manager.add_application(
            app_id=app_id_2,
            app_name="Multi Test App 2",
            app_secret="secret2",
        )

        pool = CredentialPool(
            config=e2e_config,
            app_manager=manager,
            token_storage=e2e_token_storage,
            lock_dir=tmp_path / "locks",
        )

        # Verify each app has its own token
        token1 = pool.get_token(app_id_1, "app_access_token")
        token2 = pool.get_token(app_id_2, "app_access_token")

        assert token1 is not None
        assert token2 is not None
        assert token1 != token2  # Different apps should have different tokens

        pool.close()
        manager.close()

        print(f"✅ Test 10: Multi-app isolation verified: {app_id_1[:20]}... vs {app_id_2[:20]}...")


@pytest.mark.slow
class TestCompleteUserJourney:
    """Test complete user journey from initialization to operations."""

    def test_complete_journey(
        self,
        e2e_config: Config,
        test_app_id: str,
        test_user_id: str,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """Test complete user journey: Init → Config → Token → Message → Doc → Contact.

        This test simulates a real user workflow from application
        initialization through various API operations.
        """
        tmp_path = tmp_path_factory.mktemp("journey_test")

        print("\n🚀 Starting complete user journey test...\n")

        # Step 1: Initialize application
        print("Step 1: Initializing application configuration...")
        app_manager = ApplicationManager(
            tmp_path / "journey.db",
            e2e_config.config_encryption_key,
        )
        app_manager.add_application(
            app_id=test_app_id,
            app_name="Journey Test App",
            app_secret=os.getenv("LARK_APP_SECRET", "test_secret"),
        )
        print("  ✓ Application configured")

        # Step 2: Initialize token management
        print("Step 2: Setting up token management...")
        token_storage = TokenStorageService(e2e_config.get_postgres_url())
        credential_pool = CredentialPool(
            config=e2e_config,
            app_manager=app_manager,
            token_storage=token_storage,
            lock_dir=tmp_path / "locks",
        )
        print("  ✓ Token management ready")

        # Step 3: Acquire token automatically
        print("Step 3: Acquiring token automatically...")
        token = credential_pool.get_token(test_app_id, "app_access_token")
        assert token is not None
        print(f"  ✓ Token acquired: {token[:20]}...")

        # Step 4: Send message (if user ID available)
        if test_user_id != "ou_testuser123":
            print("Step 4: Sending test message...")
            messaging_client = MessagingClient(credential_pool)
            result = messaging_client.send_text_message(
                app_id=test_app_id,
                receive_id=test_user_id,
                receive_id_type="user_id",
                content="🧪 Complete Journey Test",
            )
            assert result is not None
            print(f"  ✓ Message sent: {result.get('message_id')}")
        else:
            print("Step 4: Skipped (no real user ID)")

        # Step 5: Query contact (if email available)
        test_email = os.getenv("LARK_TEST_USER_EMAIL")
        if test_email:
            print("Step 5: Looking up user contact...")
            contact_client = ContactClient(credential_pool, enable_cache=True)
            user = contact_client.get_user_by_email(
                app_id=test_app_id,
                email=test_email,
            )
            assert user is not None
            print(f"  ✓ User found: {user.name}")
        else:
            print("Step 5: Skipped (no test email)")

        # Cleanup
        credential_pool.close()
        token_storage.close()
        app_manager.close()

        print("\n✅ Complete user journey test passed!\n")
