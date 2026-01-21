# API Contract: ApplicationManager (Enhanced)

**Module**: `src/lark_service/core/application_manager.py`
**Type**: Concrete Class (Enhanced)
**Phase**: Phase 1 - Design
**Date**: 2026-01-21

## Overview

ApplicationManager 管理飞书应用配置的 CRUD 操作。本次重构新增:智能默认应用选择逻辑,支持自动确定默认 app_id。

## Enhanced Class Definition

```python
class ApplicationManager:
    """Manages Lark application configurations (CRUD operations)."""

    def __init__(self, db_path: str) -> None:
        """Initialize application manager with SQLite database."""
        ...

    # ========== NEW METHOD ==========

    def get_default_app_id(self) -> str | None:
        """
        Intelligently select default application ID.

        Strategy:
        - If only one active app exists → return it automatically
        - If multiple active apps exist → return first (by created_at)
        - If no active apps exist → return None

        Returns:
        ----------
            Default app_id if determinable, None otherwise

        Example:
        ----------
            >>> # Single app scenario
            >>> default = manager.get_default_app_id()
            >>> print(default)  # "app1"

            >>> # Multi-app scenario
            >>> default = manager.get_default_app_id()
            >>> print(default)  # "app1" (first by creation time)

            >>> # No active apps
            >>> default = manager.get_default_app_id()
            >>> print(default)  # None
        """
        ...

    # ========== EXISTING METHODS (unchanged) ==========

    def create_application(
        self,
        app_id: str,
        app_name: str,
        app_secret: str,
        description: str | None = None,
        created_by: str | None = None,
    ) -> Application:
        """Create new application configuration."""
        ...

    def get_application(self, app_id: str) -> Application | None:
        """Get application by app_id."""
        ...

    def list_applications(
        self, status: str | None = None
    ) -> list[Application]:
        """List applications with optional status filter."""
        ...

    def update_application(self, app_id: str, **kwargs) -> Application:
        """Update application configuration."""
        ...

    def delete_application(self, app_id: str) -> bool:
        """Delete application configuration."""
        ...
```

## New Method Contract

### get_default_app_id() -> str | None

**Purpose**: Intelligently select default app_id

**Parameters**: None

**Returns**:
- `str`: Default app_id if determinable
- `None`: If no active apps exist

**Selection Strategy**:

#### Strategy 1: Single Active App
```python
# Database state:
# [Application(app_id="app1", is_active=True, created_at="2024-01-01")]

default = manager.get_default_app_id()
# Returns: "app1"
# Logic: Only one active app → automatically selected
# Logging: DEBUG "Single active app found: app1"
```

#### Strategy 2: Multiple Active Apps
```python
# Database state:
# [
#   Application(app_id="app1", is_active=True, created_at="2024-01-01"),
#   Application(app_id="app2", is_active=True, created_at="2024-01-02"),
#   Application(app_id="app3", is_active=True, created_at="2024-01-03")
# ]

default = manager.get_default_app_id()
# Returns: "app1" (first by created_at)
# Logic: Multiple apps → select first (按创建时间排序)
# Logging: DEBUG "Multiple active apps found, using first: app1. Available: ['app1', 'app2', 'app3']"
```

#### Strategy 3: No Active Apps
```python
# Database state:
# [
#   Application(app_id="app1", is_active=False, status="disabled"),
#   Application(app_id="app2", is_active=False, status="deleted")
# ]
# OR
# []

default = manager.get_default_app_id()
# Returns: None
# Logic: No active apps → cannot determine default
# Logging: WARNING "No active applications found"
```

**Implementation Pseudocode**:
```python
def get_default_app_id(self) -> str | None:
    # Get all active apps
    apps = self.list_applications(status="active")

    # No active apps
    if not apps:
        logger.warning("No active applications found")
        return None

    # Single active app (90% expected case)
    if len(apps) == 1:
        logger.debug(f"Single active app found: {apps[0].app_id}")
        return apps[0].app_id

    # Multiple active apps (10% expected case)
    # Sort by created_at, return first
    apps.sort(key=lambda app: app.created_at)
    default = apps[0].app_id
    logger.debug(
        f"Multiple active apps found, using first: {default}. "
        f"Available: {[app.app_id for app in apps]}"
    )
    return default
```

**Logging Behavior**:

| Scenario | Level | Message Template |
|----------|-------|------------------|
| Single app | DEBUG | `"Single active app found: {app_id}"` |
| Multiple apps | DEBUG | `"Multiple active apps found, using first: {default}. Available: {all_app_ids}"` |
| No apps | WARNING | `"No active applications found"` |

**Performance**:
- Query: `SELECT * FROM applications WHERE status='active' ORDER BY created_at`
- Typical: < 10ms (SQLite, < 100 apps)
- Target: < 50ms (SQLite, < 1000 apps)

---

## Integration Points

### With CredentialPool

```python
class CredentialPool:
    def get_default_app_id(self) -> str | None:
        # 1. Check explicit default
        if self._default_app_id is not None:
            return self._default_app_id

        # 2. Delegate to ApplicationManager
        return self.app_manager.get_default_app_id()
```

**Delegation Flow**:
```
User calls pool.get_default_app_id()
    ↓
CredentialPool checks _default_app_id
    ↓ (if None)
CredentialPool delegates to ApplicationManager
    ↓
ApplicationManager.get_default_app_id()
    ↓
Returns app_id or None
```

---

## Usage Examples

### Example 1: Auto-detect Single App

```python
manager = ApplicationManager(db_path="apps.db")

# Add single app
manager.create_application(
    app_id="cli_xxx",
    app_name="My App",
    app_secret="secret_xxx"
)

# Auto-detect default
default = manager.get_default_app_id()
print(default)  # "cli_xxx"
# DEBUG: Single active app found: cli_xxx
```

### Example 2: Multiple Apps, Explicit Order

```python
manager = ApplicationManager(db_path="apps.db")

# Add apps in order
manager.create_application(
    app_id="app_prod",
    app_name="Production App",
    app_secret="secret_prod"
)
time.sleep(1)  # Ensure different created_at
manager.create_application(
    app_id="app_dev",
    app_name="Development App",
    app_secret="secret_dev"
)

# Returns first by creation time
default = manager.get_default_app_id()
print(default)  # "app_prod"
# DEBUG: Multiple active apps found, using first: app_prod. Available: ['app_prod', 'app_dev']
```

### Example 3: No Active Apps

```python
manager = ApplicationManager(db_path="apps.db")

# Add disabled app
manager.create_application(
    app_id="cli_xxx",
    app_name="My App",
    app_secret="secret_xxx"
)
manager.update_application("cli_xxx", status="disabled")

# Cannot determine default
default = manager.get_default_app_id()
print(default)  # None
# WARNING: No active applications found
```

---

## Testing Contract

### Unit Tests

**File**: `tests/unit/core/test_application_manager.py`

**New Required Tests**:
1. `test_get_default_app_id_single_active`
2. `test_get_default_app_id_multiple_active`
3. `test_get_default_app_id_no_active`
4. `test_get_default_app_id_sorted_by_created_at`
5. `test_get_default_app_id_ignores_inactive`

**Test Data Setup**:
```python
def test_get_default_app_id_multiple_active(manager):
    # Create apps in specific order
    app1 = manager.create_application(
        app_id="app1",
        app_name="App 1",
        app_secret="secret1"
    )
    time.sleep(0.01)
    app2 = manager.create_application(
        app_id="app2",
        app_name="App 2",
        app_secret="secret2"
    )

    # Should return app1 (first by created_at)
    default = manager.get_default_app_id()
    assert default == "app1"
```

---

## Database Schema (Reference)

**Table**: `applications`

```sql
CREATE TABLE applications (
    app_id VARCHAR(64) PRIMARY KEY,
    app_name VARCHAR(128) NOT NULL,
    app_secret TEXT NOT NULL,  -- Encrypted
    description TEXT,
    status VARCHAR(16) DEFAULT 'active',  -- 'active', 'disabled', 'deleted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64)
);

CREATE INDEX idx_apps_status ON applications(status);
CREATE INDEX idx_apps_created_at ON applications(created_at);
```

**Query for Default Selection**:
```sql
-- Get active apps sorted by creation time
SELECT * FROM applications
WHERE status = 'active'
ORDER BY created_at ASC;
```

---

## Backward Compatibility

### No Breaking Changes

- All existing methods unchanged ✅
- New method is additive ✅
- Existing code works without calling new method ✅

### Migration Path

**Before**:
```python
manager = ApplicationManager(db_path="apps.db")
app = manager.get_application("cli_xxx")
# Manual app selection
```

**After**:
```python
manager = ApplicationManager(db_path="apps.db")

# Option 1: Explicit (still works)
app = manager.get_application("cli_xxx")

# Option 2: Auto-detect (new)
default_id = manager.get_default_app_id()
if default_id:
    app = manager.get_application(default_id)
```

**Migration Path**: Zero-breaking (100% backward compatible)

---

## Performance Considerations

### Query Optimization

**Current Implementation**:
- Query: `SELECT * FROM applications WHERE status='active' ORDER BY created_at`
- Index: `idx_apps_status`, `idx_apps_created_at`
- Expected rows: < 100 (typical), < 1000 (max)

**Performance Targets**:
- Single app query: < 5ms
- Multiple apps query (< 100): < 10ms
- Multiple apps query (< 1000): < 50ms

### Caching Consideration

**Current**: No caching (query每次执行)

**Future Optimization** (if needed):
```python
class ApplicationManager:
    def __init__(self, db_path: str):
        self._cache_default_app_id: str | None = None
        self._cache_timestamp: float | None = None
        self._cache_ttl: int = 300  # 5 minutes

    def get_default_app_id(self) -> str | None:
        # Check cache
        if self._cache_timestamp and time.time() - self._cache_timestamp < self._cache_ttl:
            return self._cache_default_app_id

        # Query database
        default = self._query_default_app_id()

        # Update cache
        self._cache_default_app_id = default
        self._cache_timestamp = time.time()

        return default
```

**Note**: 当前实现不缓存,保持简单性。如性能成为瓶颈,可添加缓存。

---

## Error Handling

### No Errors Raised

This method never raises exceptions:
- Returns `str` if successful
- Returns `None` if no active apps
- Logs WARNING for empty result

**Design Rationale**:
- Defensive: Always safe to call
- Graceful: No apps is valid state (empty database)
- Informative: Logs provide debugging context

---

## Security Considerations

### No Sensitive Data Exposure

- Returns only `app_id` (not sensitive)
- Does NOT return `app_secret`
- Logs only `app_id` (safe)

### Active Status Validation

- Only returns apps with `status='active'`
- Ignores disabled/deleted apps
- Prevents use of deactivated credentials

---

**Contract Status**: ✅ Complete
**Implementation Status**: ⏳ Pending
**Last Updated**: 2026-01-21
