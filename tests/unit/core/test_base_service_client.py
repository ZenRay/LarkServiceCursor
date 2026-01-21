"""Unit tests for BaseServiceClient."""

import pytest

from lark_service.core.base_service_client import BaseServiceClient
from lark_service.core.exceptions import ConfigError


class MockCredentialPool:
    """Mock CredentialPool for testing."""

    def __init__(self) -> None:
        self._default_app_id: str | None = None
        self._available_apps = ["cli_app1", "cli_app2", "cli_app3"]

    def set_default_app_id(self, app_id: str) -> None:
        self._default_app_id = app_id

    def get_default_app_id(self) -> str | None:
        return self._default_app_id

    def list_app_ids(self) -> list[str]:
        return self._available_apps


class TestBaseServiceClient:
    """Test suite for BaseServiceClient."""

    def test_init_with_default_app_id(self) -> None:
        """Test initialization with explicit default app_id."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_default")

        assert client.credential_pool is pool
        assert client._default_app_id == "cli_default"
        assert client._context_app_stack == []

    def test_init_without_default_app_id(self) -> None:
        """Test initialization without default app_id."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        assert client.credential_pool is pool
        assert client._default_app_id is None
        assert client._context_app_stack == []

    def test_resolve_app_id_priority_1_method_parameter(self) -> None:
        """Test app_id resolution priority 1: method parameter."""
        pool = MockCredentialPool()
        pool.set_default_app_id("cli_pool_default")
        client = BaseServiceClient(pool, app_id="cli_client_default")

        # Push context to stack
        client._context_app_stack.append("cli_context")

        # Method parameter should have highest priority
        resolved = client._resolve_app_id(app_id="cli_param")
        assert resolved == "cli_param"

    def test_resolve_app_id_priority_2_context_stack(self) -> None:
        """Test app_id resolution priority 2: context stack."""
        pool = MockCredentialPool()
        pool.set_default_app_id("cli_pool_default")
        client = BaseServiceClient(pool, app_id="cli_client_default")

        # Push context to stack
        client._context_app_stack.append("cli_context")

        # Context should override client and pool defaults
        resolved = client._resolve_app_id()
        assert resolved == "cli_context"

    def test_resolve_app_id_priority_3_client_default(self) -> None:
        """Test app_id resolution priority 3: client-level default."""
        pool = MockCredentialPool()
        pool.set_default_app_id("cli_pool_default")
        client = BaseServiceClient(pool, app_id="cli_client_default")

        # Client default should override pool default
        resolved = client._resolve_app_id()
        assert resolved == "cli_client_default"

    def test_resolve_app_id_priority_4_pool_default(self) -> None:
        """Test app_id resolution priority 4: pool-level default."""
        pool = MockCredentialPool()
        pool.set_default_app_id("cli_pool_default")
        client = BaseServiceClient(pool)

        # Pool default should be used when no other sources
        resolved = client._resolve_app_id()
        assert resolved == "cli_pool_default"

    def test_resolve_app_id_priority_5_raises_config_error(self) -> None:
        """Test app_id resolution priority 5: raise ConfigError."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        # No app_id available from any source - should raise ConfigError
        with pytest.raises(ConfigError) as exc_info:
            client._resolve_app_id()

        error_msg = str(exc_info.value)
        assert "Unable to determine app_id" in error_msg
        assert "Method parameter" in error_msg
        assert "Context manager" in error_msg
        assert "Client initialization" in error_msg
        assert "CredentialPool default" in error_msg
        assert "cli_app1" in error_msg  # Available apps listed

    def test_resolve_app_id_no_apps_configured(self) -> None:
        """Test ConfigError message when no apps are configured."""
        pool = MockCredentialPool()
        pool._available_apps = []  # No apps configured
        client = BaseServiceClient(pool)

        with pytest.raises(ConfigError) as exc_info:
            client._resolve_app_id()

        error_msg = str(exc_info.value)
        assert "No applications configured" in error_msg

    def test_get_current_app_id_with_default(self) -> None:
        """Test get_current_app_id returns resolved app_id."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_default")

        current = client.get_current_app_id()
        assert current == "cli_default"

    def test_get_current_app_id_returns_none_when_unavailable(self) -> None:
        """Test get_current_app_id returns None when no app_id available."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        current = client.get_current_app_id()
        assert current is None

    def test_list_available_apps(self) -> None:
        """Test listing available applications."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        apps = client.list_available_apps()
        assert apps == ["cli_app1", "cli_app2", "cli_app3"]

    def test_use_app_context_manager_single_level(self) -> None:
        """Test use_app context manager for single-level switching."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_default")

        # Before context
        assert client.get_current_app_id() == "cli_default"

        # Inside context
        with client.use_app("cli_temp"):
            assert client.get_current_app_id() == "cli_temp"

        # After context
        assert client.get_current_app_id() == "cli_default"

    def test_use_app_context_manager_nested(self) -> None:
        """Test use_app context manager with nested calls."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_default")

        assert client.get_current_app_id() == "cli_default"

        with client.use_app("cli_level1"):
            assert client.get_current_app_id() == "cli_level1"

            with client.use_app("cli_level2"):
                assert client.get_current_app_id() == "cli_level2"

                with client.use_app("cli_level3"):
                    assert client.get_current_app_id() == "cli_level3"

                assert client.get_current_app_id() == "cli_level2"

            assert client.get_current_app_id() == "cli_level1"

        assert client.get_current_app_id() == "cli_default"

    def test_use_app_context_manager_stack_cleanup_on_exception(self) -> None:
        """Test use_app cleans up stack even when exception occurs."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_default")

        try:
            with client.use_app("cli_temp"):
                assert client.get_current_app_id() == "cli_temp"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Stack should be cleaned up
        assert client.get_current_app_id() == "cli_default"
        assert client._context_app_stack == []

    def test_use_app_method_parameter_overrides_context(self) -> None:
        """Test that method parameter overrides context manager."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        with client.use_app("cli_context"):
            # Method parameter should override context
            resolved = client._resolve_app_id(app_id="cli_override")
            assert resolved == "cli_override"

            # Without parameter, context is used
            resolved = client._resolve_app_id()
            assert resolved == "cli_context"

    def test_multiple_clients_independent_context_stacks(self) -> None:
        """Test that multiple clients have independent context stacks."""
        pool = MockCredentialPool()
        client1 = BaseServiceClient(pool, app_id="cli_client1")
        client2 = BaseServiceClient(pool, app_id="cli_client2")

        with client1.use_app("cli_context1"), client2.use_app("cli_context2"):
            assert client1.get_current_app_id() == "cli_context1"
            assert client2.get_current_app_id() == "cli_context2"

        assert client1.get_current_app_id() == "cli_client1"
        assert client2.get_current_app_id() == "cli_client2"
