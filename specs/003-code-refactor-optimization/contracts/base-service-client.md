# API Contract: BaseServiceClient

**Module**: `src/lark_service/core/base_service_client.py`
**Type**: Abstract Base Class
**Phase**: Phase 1 - Design
**Date**: 2026-01-21

## Overview

BaseServiceClient 是所有服务客户端的抽象基类,提供统一的 `app_id` 管理能力。所有功能域客户端(MessagingClient, ContactClient, CloudDocClient, aPaaSClient)必须继承此基类。

## Class Definition

```python
from abc import ABC
from contextlib import contextmanager
from typing import ContextManager

from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import ConfigError, AuthenticationError


class BaseServiceClient(ABC):
    """Base class for all service clients with unified app_id management."""

    def __init__(
        self,
        credential_pool: CredentialPool,
        app_id: str | None = None,
    ) -> None:
        """
        Initialize the base service client.

        Args:
        ----------
            credential_pool: CredentialPool instance for SDK client access
            app_id: Optional default app_id for this client instance

        Example:
        ----------
            >>> pool = CredentialPool(...)
            >>> client = MessagingClient(pool, app_id="cli_xxx")
        """
        ...

    def _resolve_app_id(self, app_id: str | None = None) -> str:
        """
        Resolve app_id with priority: param > context > client default > pool default.

        Args:
        ----------
            app_id: Optional app_id to override default resolution

        Returns:
        ----------
            Resolved app_id string

        Raises:
        ----------
            ConfigError: When app_id cannot be determined. Error message includes:
                - Current attempted app_id (if any)
                - Available app_id list
                - Three configuration methods with example code
                - Clear fix suggestions

        Example:
        ----------
            >>> resolved = self._resolve_app_id(app_id="cli_xxx")
            >>> resolved = self._resolve_app_id()  # Use default resolution
        """
        ...

    def get_current_app_id(self) -> str | None:
        """
        Get the currently used app_id without raising exceptions.

        Returns:
        ----------
            Current app_id if determinable, None otherwise

        Example:
        ----------
            >>> current = client.get_current_app_id()
            >>> if current:
            ...     print(f"Using app: {current}")
            ... else:
            ...     print("No default app configured")
        """
        ...

    def list_available_apps(self) -> list[str]:
        """
        List all available (active) application IDs.

        Returns:
        ----------
            List of active app_id strings

        Example:
        ----------
            >>> apps = client.list_available_apps()
            >>> print(f"Available apps: {apps}")
            ['app1', 'app2', 'app3']
        """
        ...

    @contextmanager
    def use_app(self, app_id: str) -> ContextManager[None]:
        """
        Context manager to temporarily switch application.

        Supports nested usage. Inner context overrides outer context.
        On exit, automatically restores the previous app_id.

        ⚠️ WARNING: Not thread-safe for concurrent use of same client instance.
        For concurrent scenarios:
        - Option 1: Create dedicated client instances (recommended)
        - Option 2: Use explicit app_id parameters in methods

        Args:
        ----------
            app_id: Target application ID to switch to

        Raises:
        ----------
            AuthenticationError: If app_id does not exist

        Example:
        ----------
            >>> client = MessagingClient(pool, app_id="app1")
            >>> with client.use_app("app2"):
            ...     client.send_text_message(...)  # Uses app2
            >>> client.send_text_message(...)  # Back to app1

            >>> # Nested contexts
            >>> with client.use_app("app2"):
            ...     with client.use_app("app3"):
            ...         ...  # Uses app3
            ...     ...  # Uses app2
        """
        ...
```

## Method Contracts

### \_\_init\_\_(credential_pool, app_id=None)

**Purpose**: Initialize the base service client with optional default app_id

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| credential_pool | CredentialPool | ✅ | - | Credential pool instance |
| app_id | str \| None | ❌ | None | Client-level default app_id |

**Returns**: None

**Side Effects**:
- Sets `self.credential_pool`
- Sets `self._default_app_id`
- Initializes `self._context_app_stack = []`

**Example**:
```python
# Single app scenario
client = MessagingClient(pool, app_id="cli_xxx")

# Multi-app scenario (use factory or explicit params)
client = MessagingClient(pool)
```

---

### _resolve_app_id(app_id=None) -> str

**Purpose**: Resolve app_id with 5-level priority

**Priority Order**:
1. Method parameter `app_id`
2. Context stack top `_context_app_stack[-1]`
3. Client default `_default_app_id`
4. Pool default `credential_pool.get_default_app_id()`
5. Raise ConfigError

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| app_id | str \| None | ❌ | None | Override app_id |

**Returns**: `str` - Resolved app_id

**Raises**:
- `ConfigError`: When app_id cannot be determined

**Error Message Format**:
```
Cannot determine app_id. Please specify app_id via:
1. Method parameter: client.send_message(app_id='cli_xxx', ...)
2. Client initialization: MessagingClient(pool, app_id='cli_xxx')
3. CredentialPool default: pool.set_default_app_id('cli_xxx')
Available apps: ['app1', 'app2', 'app3']
```

**Logging**:
- DEBUG level logs for each priority level hit

**Performance**: < 1μs (typical case, no exception)

**Example**:
```python
# Priority 1: Method parameter
resolved = self._resolve_app_id(app_id="param_app")  # → "param_app"

# Priority 2: Context manager
with self.use_app("context_app"):
    resolved = self._resolve_app_id()  # → "context_app"

# Priority 3: Client default
client = MessagingClient(pool, app_id="client_app")
resolved = client._resolve_app_id()  # → "client_app"

# Priority 4: Pool default
pool.set_default_app_id("pool_app")
client = MessagingClient(pool)
resolved = client._resolve_app_id()  # → "pool_app"

# Priority 5: Error
client = MessagingClient(pool)  # No defaults
try:
    resolved = client._resolve_app_id()
except ConfigError as e:
    print(e)  # Detailed fix suggestions
```

---

### get_current_app_id() -> str | None

**Purpose**: Get current app_id without raising exceptions (for debugging)

**Parameters**: None

**Returns**:
- `str`: Current app_id if determinable
- `None`: If app_id cannot be determined

**Raises**: None (never raises exceptions)

**Implementation**:
```python
try:
    return self._resolve_app_id()
except ConfigError:
    return None
```

**Use Cases**:
- Debugging: Check which app is currently active
- Conditional logic: Verify app before operations
- Logging: Include app context in logs

**Example**:
```python
current = client.get_current_app_id()
if current:
    logger.info(f"Operating on app: {current}")
else:
    logger.warning("No default app configured")

# Conditional operations
if client.get_current_app_id() == "production_app":
    # Extra validation for production
    pass
```

---

### list_available_apps() -> list[str]

**Purpose**: List all active application IDs

**Parameters**: None

**Returns**: `list[str]` - List of active app_id strings

**Implementation**: Delegates to `credential_pool.list_app_ids()`

**Example**:
```python
apps = client.list_available_apps()
print(f"Available apps: {apps}")
# Output: ['app1', 'app2', 'app3']

# Check if specific app exists
if "app3" in client.list_available_apps():
    with client.use_app("app3"):
        client.send_text_message(...)
```

---

### use_app(app_id) -> ContextManager[None]

**Purpose**: Temporarily switch application context

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| app_id | str | ✅ | - | Target application ID |

**Returns**: `ContextManager[None]`

**Raises**:
- `AuthenticationError`: If app_id does not exist

**Behavior**:
- **Enter**: Push app_id to `_context_app_stack`
- **Exit**: Pop app_id from stack

**Thread Safety**: ⚠️ **NOT thread-safe**

**Concurrent Alternatives**:
```python
# ❌ NOT thread-safe
client = MessagingClient(pool)
with ThreadPoolExecutor() as executor:
    executor.submit(lambda: client.use_app("app1"))
    executor.submit(lambda: client.use_app("app2"))

# ✅ Thread-safe alternative 1: Dedicated clients
def send_with_dedicated_client(app_id):
    client = pool.create_messaging_client(app_id)
    client.send_text_message(...)

# ✅ Thread-safe alternative 2: Explicit parameters
client = MessagingClient(pool)
def send_explicit(app_id):
    client.send_text_message(app_id=app_id, ...)
```

**Nesting Support**:
```python
client = MessagingClient(pool, app_id="app1")

with client.use_app("app2"):
    print(client.get_current_app_id())  # app2

    with client.use_app("app3"):
        print(client.get_current_app_id())  # app3

    print(client.get_current_app_id())  # app2 (restored)

print(client.get_current_app_id())  # app1 (restored)
```

**State Transitions**:
```
[Initial: stack=[]]
    ↓ use_app("app2")
[Context: stack=["app2"]]
    ↓ use_app("app3") nested
[Nested: stack=["app2", "app3"]]
    ↓ exit inner
[Context: stack=["app2"]]
    ↓ exit outer
[Initial: stack=[]]
```

**Logging**:
- DEBUG level on context enter: `"Switched to app_id: app2 (stack depth: 1)"`
- DEBUG level on context exit: `"Restored from app_id: app2 (stack depth: 0)"`

---

## Integration Points

### With CredentialPool

```python
class BaseServiceClient:
    def __init__(self, credential_pool: CredentialPool, ...):
        self.credential_pool = credential_pool

    def _resolve_app_id(self, ...):
        # Use pool default as fallback
        pool_default = self.credential_pool.get_default_app_id()

    def list_available_apps(self):
        # Delegate to pool
        return self.credential_pool.list_app_ids()
```

### With Service Clients

All service clients inherit BaseServiceClient:

```python
class MessagingClient(BaseServiceClient):
    def send_text_message(
        self,
        receiver_id: str,
        text: str,
        app_id: str | None = None  # ← Optional parameter
    ) -> dict[str, Any]:
        # Resolve app_id using inherited method
        resolved_app_id = self._resolve_app_id(app_id)

        # Get SDK client
        client = self.credential_pool._get_sdk_client(resolved_app_id)

        # Call Lark API
        ...
```

---

## Error Handling

### ConfigError

**Scenario**: app_id cannot be determined

**Error Message Template**:
```
Cannot determine app_id. Please specify app_id via:
1. Method parameter: client.send_message(app_id='cli_xxx', ...)
2. Client initialization: MessagingClient(pool, app_id='cli_xxx')
3. CredentialPool default: pool.set_default_app_id('cli_xxx')
Available apps: {available_app_list}
```

**User Action**: Choose one of three configuration methods

### AuthenticationError

**Scenario**: app_id does not exist

**Error Message Template**:
```
Application not found: {app_id}
Available apps: {available_app_list}
```

**User Action**: Check app_id spelling or configure new application

---

## Testing Contract

### Unit Tests

**File**: `tests/unit/core/test_base_service_client.py`

**Required Tests**:
1. `test_resolve_app_id_method_parameter_priority`
2. `test_resolve_app_id_context_priority`
3. `test_resolve_app_id_client_default_priority`
4. `test_resolve_app_id_pool_default_priority`
5. `test_resolve_app_id_raises_config_error`
6. `test_get_current_app_id_returns_none_on_error`
7. `test_use_app_single_context`
8. `test_use_app_nested_contexts`
9. `test_use_app_raises_authentication_error`
10. `test_list_available_apps`

### Integration Tests

**File**: `tests/integration/test_app_switching.py`

**Required Tests**:
1. `test_messaging_client_app_switching`
2. `test_contact_client_app_switching`
3. `test_concurrent_clients_isolation`

---

## Backward Compatibility

### Existing API Preservation

**Before Refactoring**:
```python
client = MessagingClient(credential_pool)
client.send_text_message(
    app_id="cli_xxx",  # ← Required parameter
    receiver_id="ou_yyy",
    text="Hello"
)
```

**After Refactoring**:
```python
# Option 1: Still works (backward compatible)
client = MessagingClient(credential_pool)
client.send_text_message(
    app_id="cli_xxx",  # ← Now optional but still supported
    receiver_id="ou_yyy",
    text="Hello"
)

# Option 2: New simplified API
client = MessagingClient(credential_pool, app_id="cli_xxx")
client.send_text_message(
    receiver_id="ou_yyy",
    text="Hello"  # ← No app_id needed
)
```

**Migration Path**: Zero-breaking (100% backward compatible)

---

## Performance Guarantees

| Operation | Target | Typical |
|-----------|--------|---------|
| _resolve_app_id() (no error) | < 1μs | 0.5μs |
| get_current_app_id() | < 2μs | 1μs |
| list_available_apps() | < 10μs | 5μs |
| use_app() enter/exit | < 5μs | 2μs |

---

## Security Considerations

### No Sensitive Data in Logs

- app_id is logged (not sensitive)
- app_secret is NEVER logged
- Token values are NEVER logged

### Thread Safety Warning

- Documented in docstring
- Documented in spec.md
- Documented in quickstart.md
- Example code provided for concurrent scenarios

---

**Contract Status**: ✅ Complete
**Implementation Status**: ⏳ Pending
**Last Updated**: 2026-01-21
