# API Contract: CredentialPool (Enhanced)

**Module**: `src/lark_service/core/credential_pool.py`
**Type**: Concrete Class (Enhanced)
**Phase**: Phase 1 - Design
**Date**: 2026-01-21

## Overview

CredentialPool 管理飞书应用凭证和 SDK 客户端缓存。本次重构新增:默认 app_id 管理和工厂方法,支持简化的单应用场景和优雅的多应用场景。

## Enhanced Class Definition

```python
class CredentialPool:
    """Manages Lark application credentials and SDK clients."""

    def __init__(
        self,
        config: Config,
        app_manager: ApplicationManager,
        token_storage: TokenStorage,
        lock_dir: str,
    ) -> None:
        """Initialize credential pool."""
        self.config = config
        self.app_manager = app_manager
        self.token_storage = token_storage
        self._default_app_id: str | None = None  # ← NEW
        # ... existing initialization

    # ========== NEW METHODS ==========

    def set_default_app_id(self, app_id: str) -> None:
        """
        Set the default application ID for this pool.

        Args:
        ----------
            app_id: Application ID to set as default

        Raises:
        ----------
            ConfigError: If app_id does not exist or is not active

        Example:
        ----------
            >>> pool.set_default_app_id("cli_xxx")
            INFO: Default app_id set to: cli_xxx
        """
        ...

    def get_default_app_id(self) -> str | None:
        """
        Get the default application ID.

        Returns:
        ----------
            Default app_id if set, otherwise delegates to ApplicationManager

        Example:
        ----------
            >>> default = pool.get_default_app_id()
            >>> if default:
            ...     print(f"Using default app: {default}")
        """
        ...

    def list_app_ids(self) -> list[str]:
        """
        List all active application IDs.

        Returns:
        ----------
            List of active app_id strings

        Example:
        ----------
            >>> apps = pool.list_app_ids()
            >>> print(f"Available apps: {apps}")
        """
        ...

    # Factory Methods
    def create_messaging_client(
        self, app_id: str | None = None
    ) -> MessagingClient:
        """
        Factory method to create a MessagingClient bound to specific app.

        Args:
        ----------
            app_id: Application ID (optional, uses pool default if None)

        Returns:
        ----------
            MessagingClient instance configured with app_id

        Example:
        ----------
            >>> app1_client = pool.create_messaging_client("app1")
            >>> app2_client = pool.create_messaging_client("app2")
            >>> app1_client.send_text_message(...)  # Uses app1
            >>> app2_client.send_text_message(...)  # Uses app2
        """
        ...

    def create_contact_client(
        self, app_id: str | None = None
    ) -> ContactClient:
        """Factory method to create a ContactClient."""
        ...

    def create_clouddoc_client(
        self, app_id: str | None = None
    ) -> DocClient:
        """Factory method to create a CloudDocClient."""
        ...

    def create_apaas_client(
        self, app_id: str | None = None
    ) -> aPaaSClient:
        """Factory method to create an aPaaSClient."""
        ...

    # ========== EXISTING METHODS (unchanged) ==========

    def _get_sdk_client(self, app_id: str) -> lark.Client:
        """Get or create SDK client for app_id."""
        ...

    def get_tenant_token(self, app_id: str) -> str:
        """Get tenant access token."""
        ...

    # ... other existing methods
```

## New Method Contracts

### set_default_app_id(app_id: str) -> None

**Purpose**: Set pool-level default app_id

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| app_id | str | ✅ | - | Application ID to set as default |

**Returns**: None

**Raises**:
- `ConfigError`: If app_id does not exist
- `ConfigError`: If app_id is not active

**Validation Steps**:
1. Call `app_manager.get_application(app_id)`
2. Check if app exists
3. Check if `app.is_active() == True`
4. Set `self._default_app_id = app_id`

**Side Effects**:
- Logs INFO: `"Default app_id set to: {app_id}"`

**Example**:
```python
# Success case
pool.set_default_app_id("cli_xxx")
# INFO: Default app_id set to: cli_xxx

# Error case: app not found
try:
    pool.set_default_app_id("non_existent")
except ConfigError as e:
    print(e)  # "Application not found: non_existent\nAvailable apps: [...]]"

# Error case: app not active
try:
    pool.set_default_app_id("cli_disabled")
except ConfigError as e:
    print(e)  # "Application is not active: cli_disabled\nStatus: disabled"
```

---

### get_default_app_id() -> str | None

**Purpose**: Get pool-level default app_id

**Parameters**: None

**Returns**:
- `str`: Default app_id if set or determined by ApplicationManager
- `None`: If no default configured and no active apps

**Resolution Logic**:
1. If `self._default_app_id is not None` → return it
2. Else delegate to `app_manager.get_default_app_id()`

**Example**:
```python
# Case 1: Explicit default set
pool.set_default_app_id("cli_xxx")
default = pool.get_default_app_id()  # → "cli_xxx"

# Case 2: No explicit default, single app
# Database: [Application(app_id="app1", is_active=True)]
default = pool.get_default_app_id()  # → "app1"

# Case 3: No explicit default, multiple apps
# Database: [app1, app2] (按创建时间排序)
default = pool.get_default_app_id()  # → "app1"

# Case 4: No apps
# Database: []
default = pool.get_default_app_id()  # → None
```

---

### list_app_ids() -> list[str]

**Purpose**: List all active application IDs

**Parameters**: None

**Returns**: `list[str]` - Active app_id list

**Implementation**:
```python
apps = self.app_manager.list_applications(status="active")
return [app.app_id for app in apps]
```

**Example**:
```python
apps = pool.list_app_ids()
print(apps)  # ['app1', 'app2', 'app3']

# Check if specific app exists
if "app3" in pool.list_app_ids():
    pool.set_default_app_id("app3")
```

---

### create_messaging_client(app_id=None) -> MessagingClient

**Purpose**: Factory method to create MessagingClient bound to specific app

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| app_id | str \| None | ❌ | None | Application ID (uses pool default if None) |

**Returns**: `MessagingClient` - New instance configured with app_id

**Implementation**:
```python
return MessagingClient(credential_pool=self, app_id=app_id)
```

**Use Cases**:

#### Use Case 1: Multi-app scenario (recommended)
```python
# Create dedicated clients for each app
app1_client = pool.create_messaging_client("app1")
app2_client = pool.create_messaging_client("app2")

app1_client.send_text_message(...)  # Always uses app1
app2_client.send_text_message(...)  # Always uses app2

# Benefits:
# - Clear separation
# - No context confusion
# - Thread-safe (each client independent)
```

#### Use Case 2: Single app with explicit ID
```python
client = pool.create_messaging_client("cli_xxx")
client.send_text_message(...)  # Uses cli_xxx
```

#### Use Case 3: Use pool default
```python
pool.set_default_app_id("default_app")
client = pool.create_messaging_client()  # app_id=None
client.send_text_message(...)  # Uses default_app
```

**Example**:
```python
# Long-running multi-app service
app1_msg = pool.create_messaging_client("app1")
app1_contact = pool.create_contact_client("app1")

app2_msg = pool.create_messaging_client("app2")
app2_contact = pool.create_contact_client("app2")

# Each client bound to specific app
app1_msg.send_text_message(receiver_id="ou_xxx", text="From App1")
app2_msg.send_text_message(receiver_id="ou_yyy", text="From App2")
```

---

### create_contact_client(app_id=None) -> ContactClient

**Purpose**: Factory method to create ContactClient

**Same contract as** `create_messaging_client`, returns `ContactClient`

---

### create_clouddoc_client(app_id=None) -> DocClient

**Purpose**: Factory method to create CloudDocClient

**Same contract as** `create_messaging_client`, returns `DocClient`

---

### create_apaas_client(app_id=None) -> aPaaSClient

**Purpose**: Factory method to create aPaaSClient

**Same contract as** `create_messaging_client`, returns `aPaaSClient`

---

## Integration with ApplicationManager

```python
class CredentialPool:
    def get_default_app_id(self) -> str | None:
        if self._default_app_id is not None:
            return self._default_app_id

        # Delegate to ApplicationManager
        return self.app_manager.get_default_app_id()

    def list_app_ids(self) -> list[str]:
        # Delegate to ApplicationManager
        apps = self.app_manager.list_applications(status="active")
        return [app.app_id for app in apps]
```

## Integration with Service Clients

```python
# Before: Manual instantiation
client = MessagingClient(credential_pool=pool)
client.send_text_message(app_id="app1", ...)  # Must specify app_id

# After: Factory method (recommended for multi-app)
client = pool.create_messaging_client("app1")
client.send_text_message(...)  # No app_id needed
```

---

## Error Handling

### set_default_app_id() Errors

**Error 1: app_id not found**
```python
try:
    pool.set_default_app_id("non_existent")
except ConfigError as e:
    # Message: "Application not found: non_existent\nAvailable apps: ['app1', 'app2']"
    pass
```

**Error 2: app_id not active**
```python
try:
    pool.set_default_app_id("cli_disabled")
except ConfigError as e:
    # Message: "Application is not active: cli_disabled\nStatus: disabled"
    pass
```

---

## Testing Contract

### Unit Tests

**File**: `tests/unit/core/test_credential_pool.py`

**New Required Tests**:
1. `test_set_default_app_id_success`
2. `test_set_default_app_id_not_found`
3. `test_set_default_app_id_not_active`
4. `test_get_default_app_id_explicit`
5. `test_get_default_app_id_delegated`
6. `test_list_app_ids`
7. `test_create_messaging_client_with_app_id`
8. `test_create_messaging_client_without_app_id`
9. `test_create_contact_client`
10. `test_create_clouddoc_client`

### Integration Tests

**File**: `tests/integration/test_factory_methods.py`

**Required Tests**:
1. `test_factory_creates_isolated_clients`
2. `test_factory_clients_use_correct_app`
3. `test_factory_concurrent_clients`

---

## Backward Compatibility

### Existing API Unchanged

All existing methods remain unchanged:
- `_get_sdk_client(app_id)` ✅
- `get_tenant_token(app_id)` ✅
- `refresh_token(app_id)` ✅
- ... (all other methods) ✅

### New Methods Optional

New functionality is opt-in:
- Existing code works without calling new methods
- `_default_app_id` defaults to `None` (no behavior change)
- Factory methods are convenience, not required

**Migration Path**: Zero-breaking (100% backward compatible)

---

## Performance Guarantees

| Operation | Target | Typical |
|-----------|--------|---------|
| set_default_app_id() | < 10μs | 5μs |
| get_default_app_id() | < 5μs | 2μs |
| list_app_ids() | < 50μs | 20μs |
| create_*_client() | < 10μs | 5μs |

---

## Usage Examples

### Example 1: Single App Service

```python
# Setup
pool = CredentialPool(...)
pool.set_default_app_id("cli_xxx")

# All clients use default
msg_client = pool.create_messaging_client()
contact_client = pool.create_contact_client()

msg_client.send_text_message(...)  # Uses cli_xxx
contact_client.get_user_info(...)  # Uses cli_xxx
```

### Example 2: Multi-App Service

```python
# Setup
pool = CredentialPool(...)

# Create dedicated clients per app
app1_msg = pool.create_messaging_client("app1")
app1_contact = pool.create_contact_client("app1")

app2_msg = pool.create_messaging_client("app2")
app2_contact = pool.create_contact_client("app2")

# Clear separation, no confusion
app1_msg.send_text_message(...)  # Always app1
app2_msg.send_text_message(...)  # Always app2
```

### Example 3: Dynamic App Selection

```python
pool = CredentialPool(...)

def send_message_for_app(app_id: str, message: str):
    # Create temporary client
    client = pool.create_messaging_client(app_id)
    client.send_text_message(receiver_id="ou_xxx", text=message)

# Use different apps dynamically
send_message_for_app("app1", "Message from app1")
send_message_for_app("app2", "Message from app2")
```

---

**Contract Status**: ✅ Complete
**Implementation Status**: ⏳ Pending
**Last Updated**: 2026-01-21
