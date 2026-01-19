"""Concurrency integration tests.

Tests concurrent API calls to verify:
1. Token refresh does not become a bottleneck
2. Lock mechanism works correctly under high concurrency
3. Database connection pool handles concurrent access
4. No race conditions in token management
"""

import concurrent.futures
import contextlib
import os
import time
from threading import Lock
from typing import Any

import pytest
from cryptography.fernet import Fernet

from lark_service.contact.client import ContactClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.messaging.client import MessagingClient


@pytest.fixture(scope="module")
def concurrency_config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    """Create configuration for concurrency tests."""
    tmp_path = tmp_path_factory.mktemp("concurrency_tests")

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
        config_db_path=tmp_path / "concurrency_config.db",
        log_level="WARNING",  # Reduce log noise during concurrent tests
        max_retries=3,
        retry_backoff_base=0.5,
        token_refresh_threshold=0.1,
    )
    return config


@pytest.fixture(scope="module")
def concurrency_app_manager(concurrency_config: Config) -> ApplicationManager:
    """Create ApplicationManager for concurrency tests."""
    manager = ApplicationManager(
        concurrency_config.config_db_path,
        concurrency_config.config_encryption_key,
    )

    app_id = os.getenv("LARK_APP_ID", "cli_conctest123")
    app_secret = os.getenv("LARK_APP_SECRET", "test_secret_conc")

    with contextlib.suppress(Exception):
        manager.add_application(
            app_id=app_id,
            app_name="Concurrency Test App",
            app_secret=app_secret,
        )

    yield manager
    manager.close()


@pytest.fixture(scope="module")
def concurrency_token_storage(concurrency_config: Config) -> TokenStorageService:
    """Create TokenStorageService for concurrency tests."""
    service = TokenStorageService(concurrency_config.get_postgres_url())
    yield service
    service.close()


@pytest.fixture(scope="module")
def concurrency_credential_pool(
    concurrency_config: Config,
    concurrency_app_manager: ApplicationManager,
    concurrency_token_storage: TokenStorageService,
    tmp_path_factory: pytest.TempPathFactory,
) -> CredentialPool:
    """Create CredentialPool for concurrency tests."""
    tmp_path = tmp_path_factory.mktemp("concurrency_locks")

    pool = CredentialPool(
        config=concurrency_config,
        app_manager=concurrency_app_manager,
        token_storage=concurrency_token_storage,
        lock_dir=tmp_path / "locks",
    )
    yield pool
    pool.close()


@pytest.fixture(scope="module")
def test_app_id() -> str:
    """Get test app ID from environment."""
    return os.getenv("LARK_APP_ID", "cli_conctest123")


class TestConcurrentTokenAccess:
    """Test concurrent token access and refresh."""

    def test_concurrent_token_get_no_bottleneck(
        self,
        concurrency_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test concurrent token acquisition does not create bottleneck.

        Verifies that 100 concurrent requests for the same token
        can be handled efficiently without excessive waiting.
        """
        num_workers = 100
        results: list[tuple[str, float]] = []
        results_lock = Lock()

        def get_token_timed() -> None:
            """Get token and measure time."""
            start = time.time()
            token = concurrency_credential_pool.get_token(test_app_id, "app_access_token")
            elapsed = time.time() - start

            with results_lock:
                results.append((token, elapsed))

        # Execute concurrent token requests
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(get_token_timed) for _ in range(num_workers)]
            concurrent.futures.wait(futures)

        total_time = time.time() - start_time

        # Verify results
        assert len(results) == num_workers

        # All tokens should be the same (single app)
        tokens = [r[0] for r in results]
        assert len(set(tokens)) == 1
        assert all(t is not None for t in tokens)

        # Performance verification
        avg_time = sum(r[1] for r in results) / len(results)
        max_time = max(r[1] for r in results)

        # Most requests should be fast (< 100ms) due to caching
        fast_requests = sum(1 for r in results if r[1] < 0.1)
        fast_ratio = fast_requests / num_workers

        print("\n📊 Concurrency Performance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time per request: {avg_time * 1000:.1f}ms")
        print(f"  Max time per request: {max_time * 1000:.1f}ms")
        print(f"  Fast requests (< 100ms): {fast_requests}/{num_workers} ({fast_ratio * 100:.1f}%)")

        # Assertions
        assert total_time < 10.0, "Total time should be < 10s for 100 requests"
        assert avg_time < 0.5, "Average time should be < 500ms per request"
        assert fast_ratio > 0.9, "At least 90% of requests should be fast (< 100ms)"

        print("✅ Test passed: No token refresh bottleneck detected")

    def test_concurrent_multi_app_isolation(
        self,
        concurrency_config: Config,
        concurrency_token_storage: TokenStorageService,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        """Test concurrent access to multiple applications.

        Verifies that tokens for different applications can be
        acquired concurrently without interference.
        """
        tmp_path = tmp_path_factory.mktemp("multi_app_concurrency")

        # Create app manager with 5 test apps
        manager = ApplicationManager(
            tmp_path / "multi_app.db",
            concurrency_config.config_encryption_key,
        )

        app_ids = [f"cli_conc_app{i}" for i in range(5)]
        for app_id in app_ids:
            manager.add_application(
                app_id=app_id,
                app_name=f"Concurrency Test App {app_id}",
                app_secret=f"secret_{app_id}",
            )

        pool = CredentialPool(
            config=concurrency_config,
            app_manager=manager,
            token_storage=concurrency_token_storage,
            lock_dir=tmp_path / "locks",
        )

        results: list[tuple[str, str]] = []
        results_lock = Lock()

        def get_token_for_app(app_id: str) -> None:
            """Get token for specific app."""
            for _ in range(20):  # 20 requests per app = 100 total
                token = pool.get_token(app_id, "app_access_token")
                with results_lock:
                    results.append((app_id, token))

        # Execute concurrent requests across multiple apps
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(get_token_for_app, app_id) for app_id in app_ids]
            concurrent.futures.wait(futures)

        # Verify results
        assert len(results) == 100  # 5 apps * 20 requests each

        # Group by app_id
        tokens_by_app: dict[str, list[str]] = {}
        for app_id, token in results:
            if app_id not in tokens_by_app:
                tokens_by_app[app_id] = []
            tokens_by_app[app_id].append(token)

        # Verify isolation
        assert len(tokens_by_app) == 5
        for app_id in app_ids:
            assert app_id in tokens_by_app
            assert len(tokens_by_app[app_id]) == 20
            # All tokens for same app should be identical
            assert len(set(tokens_by_app[app_id])) == 1

        # Verify tokens are different across apps
        unique_tokens = {tokens_by_app[app_id][0] for app_id in app_ids}
        assert len(unique_tokens) == 5

        pool.close()
        manager.close()

        print("✅ Test passed: Multi-app isolation verified under concurrency")

    def test_concurrent_database_access(
        self,
        concurrency_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test database connection pool under concurrent load.

        Verifies that the PostgreSQL connection pool can handle
        concurrent token storage operations without errors.
        """
        num_operations = 200
        errors: list[Exception] = []
        errors_lock = Lock()

        def perform_token_operation() -> None:
            """Perform token get/refresh operation."""
            try:
                # This will trigger database read/write operations
                token = concurrency_credential_pool.get_token(test_app_id, "app_access_token")
                assert token is not None
            except Exception as e:
                with errors_lock:
                    errors.append(e)

        # Execute concurrent database operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(perform_token_operation) for _ in range(num_operations)]
            concurrent.futures.wait(futures)

        # Verify no database errors
        if errors:
            print("❌ Database errors detected:")
            for i, error in enumerate(errors[:5], 1):  # Show first 5
                print(f"  {i}. {type(error).__name__}: {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")

        assert len(errors) == 0, f"Database errors occurred: {len(errors)} errors"

        print(f"✅ Test passed: {num_operations} concurrent database operations successful")


@pytest.mark.slow
class TestConcurrentAPIOperations:
    """Test concurrent API operations across different services."""

    def test_concurrent_messaging_operations(
        self,
        concurrency_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test concurrent messaging API calls.

        Verifies that multiple messaging operations can execute
        concurrently without token management issues.
        """
        test_user_id = os.getenv("LARK_TEST_USER_ID", "ou_testuser123")
        if test_user_id == "ou_testuser123":
            pytest.skip("Real user ID not configured for concurrency test")

        client = MessagingClient(concurrency_credential_pool)

        num_messages = 50
        results: list[dict[str, Any] | None] = []
        errors: list[Exception] = []
        results_lock = Lock()

        def send_message(index: int) -> None:
            """Send a message concurrently."""
            try:
                result = client.send_text_message(
                    app_id=test_app_id,
                    receive_id=test_user_id,
                    receive_id_type="user_id",
                    content=f"Concurrent test message #{index}",
                )
                with results_lock:
                    results.append(result)
            except Exception as e:
                with results_lock:
                    errors.append(e)

        # Execute concurrent messaging
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_message, i) for i in range(num_messages)]
            concurrent.futures.wait(futures)

        total_time = time.time() - start_time

        # Verify results
        print("\n📊 Concurrent Messaging Performance:")
        print(f"  Total messages: {num_messages}")
        print(f"  Successful: {len(results)}")
        print(f"  Errors: {len(errors)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time per message: {(total_time / num_messages) * 1000:.1f}ms")

        assert len(results) > 0, "At least some messages should succeed"
        assert len(errors) < num_messages * 0.1, "Error rate should be < 10%"

        print("✅ Test passed: Concurrent messaging operations successful")

    def test_concurrent_contact_lookups(
        self,
        concurrency_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Test concurrent contact lookup operations.

        Verifies that contact service caching works correctly
        under concurrent load.
        """
        test_email = os.getenv("LARK_TEST_USER_EMAIL")
        if not test_email:
            pytest.skip("Test email not configured for concurrency test")

        client = ContactClient(concurrency_credential_pool, enable_cache=True)

        num_lookups = 100
        results: list[Any] = []
        errors: list[Exception] = []
        results_lock = Lock()

        def lookup_user() -> None:
            """Look up user concurrently."""
            try:
                user = client.get_user_by_email(
                    app_id=test_app_id,
                    email=test_email,
                )
                with results_lock:
                    results.append(user)
            except Exception as e:
                with results_lock:
                    errors.append(e)

        # Execute concurrent lookups
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(lookup_user) for _ in range(num_lookups)]
            concurrent.futures.wait(futures)

        total_time = time.time() - start_time

        # Verify results
        print("\n📊 Concurrent Contact Lookup Performance:")
        print(f"  Total lookups: {num_lookups}")
        print(f"  Successful: {len(results)}")
        print(f"  Errors: {len(errors)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time per lookup: {(total_time / num_lookups) * 1000:.1f}ms")

        assert len(results) == num_lookups, "All lookups should succeed"
        assert len(errors) == 0, "No errors should occur"

        # Verify cache effectiveness (all results should be same user)
        if results:
            first_user = results[0]
            assert all(u.open_id == first_user.open_id for u in results)

        # Most lookups should be fast due to caching
        assert total_time < 5.0, "Total time should be < 5s for 100 cached lookups"

        print("✅ Test passed: Concurrent contact lookups with caching successful")


@pytest.mark.stress
class TestStressScenarios:
    """Stress test scenarios for extreme concurrency."""

    def test_stress_1000_concurrent_requests(
        self,
        concurrency_credential_pool: CredentialPool,
        test_app_id: str,
    ) -> None:
        """Stress test with 1000 concurrent token requests.

        This is a stress test to verify system stability
        under extreme concurrent load.
        """
        num_requests = 1000
        results: list[str | None] = []
        errors: list[Exception] = []
        results_lock = Lock()

        def get_token() -> None:
            """Get token."""
            try:
                token = concurrency_credential_pool.get_token(test_app_id, "app_access_token")
                with results_lock:
                    results.append(token)
            except Exception as e:
                with results_lock:
                    errors.append(e)

        # Execute stress test
        print(f"\n🔥 Stress test: {num_requests} concurrent requests...")
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(get_token) for _ in range(num_requests)]
            concurrent.futures.wait(futures)

        total_time = time.time() - start_time

        # Results
        success_rate = len(results) / num_requests * 100
        error_rate = len(errors) / num_requests * 100

        print("\n📊 Stress Test Results:")
        print(f"  Total requests: {num_requests}")
        print(f"  Successful: {len(results)} ({success_rate:.1f}%)")
        print(f"  Errors: {len(errors)} ({error_rate:.1f}%)")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {num_requests / total_time:.1f} req/s")

        # Verify acceptable performance
        assert success_rate >= 95.0, f"Success rate should be >= 95%, got {success_rate:.1f}%"
        assert total_time < 30.0, f"Total time should be < 30s, got {total_time:.2f}s"

        print("✅ Stress test passed: System stable under 1000 concurrent requests")
