"""Integration tests for application switching functionality.

Tests the 5-layer app_id resolution priority and context-based switching.
"""

import pytest

from lark_service.core.base_service_client import BaseServiceClient
from lark_service.core.exceptions import ConfigError


class MockCredentialPool:
    """Mock CredentialPool for integration testing."""

    def __init__(self) -> None:
        self._default_app_id: str | None = None
        self._available_apps = [
            "cli_app1test123456789012345",
            "cli_app2test123456789012345",
            "cli_app3test123456789012345",
        ]

    def set_default_app_id(self, app_id: str) -> None:
        self._default_app_id = app_id

    def get_default_app_id(self) -> str | None:
        return self._default_app_id

    def list_app_ids(self) -> list[str]:
        return self._available_apps


class TestAppSwitching:
    """Integration tests for application switching."""

    def test_single_app_scenario_client_level_default(self) -> None:
        """Test single-app scenario with client-level default."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_app1test123456789012345")

        # Should use client-level default
        resolved = client._resolve_app_id()
        assert resolved == "cli_app1test123456789012345"

    def test_single_app_scenario_pool_level_default(self) -> None:
        """Test single-app scenario with pool-level default."""
        pool = MockCredentialPool()
        pool.set_default_app_id("cli_app1test123456789012345")
        client = BaseServiceClient(pool)

        # Should use pool-level default
        resolved = client._resolve_app_id()
        assert resolved == "cli_app1test123456789012345"

    def test_single_app_scenario_auto_detection(self) -> None:
        """Test single-app scenario with auto-detection (simulated)."""
        pool = MockCredentialPool()
        pool._available_apps = ["cli_single123456789012345"]
        # In real scenario, ApplicationManager.get_default_app_id() would return this

        client = BaseServiceClient(pool)

        # Without default, should fail (no auto-detection in base class)
        with pytest.raises(ConfigError):
            client._resolve_app_id()

    def test_multi_app_scenario_factory_methods(self) -> None:
        """Test multi-app scenario using different client instances."""
        pool = MockCredentialPool()

        client1 = BaseServiceClient(pool, app_id="cli_app1test123456789012345")
        client2 = BaseServiceClient(pool, app_id="cli_app2test123456789012345")

        # Each client uses its own default
        assert client1._resolve_app_id() == "cli_app1test123456789012345"
        assert client2._resolve_app_id() == "cli_app2test123456789012345"

    def test_multi_app_scenario_context_manager(self) -> None:
        """Test multi-app scenario using context manager."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_app1test123456789012345")

        # Default
        assert client._resolve_app_id() == "cli_app1test123456789012345"

        # Switch to app2
        with client.use_app("cli_app2test123456789012345"):
            assert client._resolve_app_id() == "cli_app2test123456789012345"

        # Back to app1
        assert client._resolve_app_id() == "cli_app1test123456789012345"

    def test_multi_app_scenario_nested_context(self) -> None:
        """Test multi-app scenario with nested context managers."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_app1test123456789012345")

        with client.use_app("cli_app2test123456789012345"):
            assert client._resolve_app_id() == "cli_app2test123456789012345"

            with client.use_app("cli_app3test123456789012345"):
                assert client._resolve_app_id() == "cli_app3test123456789012345"

            # Back to app2
            assert client._resolve_app_id() == "cli_app2test123456789012345"

        # Back to app1
        assert client._resolve_app_id() == "cli_app1test123456789012345"

    def test_multi_app_scenario_method_parameter_override(self) -> None:
        """Test multi-app scenario with method parameter override."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_app1test123456789012345")

        with client.use_app("cli_app2test123456789012345"):
            # Method parameter has highest priority
            resolved = client._resolve_app_id(app_id="cli_app3test123456789012345")
            assert resolved == "cli_app3test123456789012345"

            # Without parameter, uses context
            resolved = client._resolve_app_id()
            assert resolved == "cli_app2test123456789012345"

    def test_app_id_resolution_priority_all_layers(self) -> None:
        """Test complete app_id resolution priority (5 layers)."""
        pool = MockCredentialPool()
        pool.set_default_app_id("cli_pool_default1234567890")

        client = BaseServiceClient(pool, app_id="cli_client_default123456")

        # Layer 4: Pool default (lowest when others available)
        assert pool.get_default_app_id() == "cli_pool_default1234567890"

        # Layer 3: Client default
        assert client._resolve_app_id() == "cli_client_default123456"

        # Layer 2: Context manager
        with client.use_app("cli_context123456789012345"):
            assert client._resolve_app_id() == "cli_context123456789012345"

            # Layer 1: Method parameter (highest)
            resolved = client._resolve_app_id(app_id="cli_param12345678901234567")
            assert resolved == "cli_param12345678901234567"

    def test_app_id_resolution_error_handling(self) -> None:
        """Test error handling when no app_id is available."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        with pytest.raises(ConfigError) as exc_info:
            client._resolve_app_id()

        error_msg = str(exc_info.value)
        assert "Unable to determine app_id" in error_msg
        assert "Method parameter" in error_msg
        assert "Context manager" in error_msg
        assert "Client initialization" in error_msg
        assert "CredentialPool default" in error_msg
        assert "cli_app1test123456789012345" in error_msg  # Available apps listed

    def test_get_current_app_id_debugging(self) -> None:
        """Test get_current_app_id for debugging."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_app1test123456789012345")

        # Normal case
        assert client.get_current_app_id() == "cli_app1test123456789012345"

        # With context
        with client.use_app("cli_app2test123456789012345"):
            assert client.get_current_app_id() == "cli_app2test123456789012345"

        # No app_id available (returns None, doesn't raise)
        client2 = BaseServiceClient(pool)
        assert client2.get_current_app_id() is None

    def test_list_available_apps(self) -> None:
        """Test listing available applications."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool)

        apps = client.list_available_apps()
        assert len(apps) == 3
        assert "cli_app1test123456789012345" in apps
        assert "cli_app2test123456789012345" in apps
        assert "cli_app3test123456789012345" in apps

    def test_multiple_clients_isolation(self) -> None:
        """Test that multiple clients have independent context stacks."""
        pool = MockCredentialPool()
        client1 = BaseServiceClient(pool, app_id="cli_app1test123456789012345")
        client2 = BaseServiceClient(pool, app_id="cli_app2test123456789012345")

        with client1.use_app("cli_context1234567890123456"), client2.use_app(
            "cli_context2234567890123456"
        ):
            # Each client maintains its own context
            assert client1.get_current_app_id() == "cli_context1234567890123456"
            assert client2.get_current_app_id() == "cli_context2234567890123456"

        # Back to original defaults
        assert client1.get_current_app_id() == "cli_app1test123456789012345"
        assert client2.get_current_app_id() == "cli_app2test123456789012345"

    def test_context_manager_exception_cleanup(self) -> None:
        """Test that context manager cleans up even on exception."""
        pool = MockCredentialPool()
        client = BaseServiceClient(pool, app_id="cli_app1test123456789012345")

        try:
            with client.use_app("cli_temp12345678901234567"):
                assert client.get_current_app_id() == "cli_temp12345678901234567"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Context should be cleaned up
        assert client.get_current_app_id() == "cli_app1test123456789012345"
        assert len(client._context_app_stack) == 0
