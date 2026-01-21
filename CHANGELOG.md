# Changelog

All notable changes to the Lark Service project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🚀 Feature: Scheduled Tasks & Token UX Optimization (v0.4.0) (2026-01-22)

#### **APScheduler Integration**
- ✅ **定时任务框架**: 基于 APScheduler 实现灵活的定时任务调度
  - 支持固定间隔 (Interval) 和 Cron 表达式
  - 自动任务包装:日志记录、Prometheus 指标
  - 任务失败自动处理和重试
  - 优雅的启动和关闭机制

#### **Scheduled Tasks Implemented**
- ✅ **用户信息同步** (`sync_user_info_task`)
  - 每 6 小时自动同步所有活跃应用的用户信息
  - 从飞书 API 获取最新用户数据并更新本地数据库

- ✅ **Token 过期检查** (`check_token_expiry_task`)
  - 每天 2 次(9AM, 6PM)检查 Token 过期状态
  - 自动发送过期提醒通知给管理员
  - 支持多级警告:7天警告、3天严重警告、已过期

- ✅ **过期 Token 清理** (`cleanup_expired_tokens_task`)
  - 每天凌晨 3 点清理过期超过 7 天的 Token
  - 保持数据库整洁

- ✅ **健康检查** (`health_check_task`)
  - 每 5 分钟检查数据库连接
  - 监控系统关键组件状态

#### **Token Expiry UX Optimization**
- ✅ **Token 过期监控服务** (`TokenExpiryMonitor`)
  - 主动检测 Token 过期状态
  - 多级通知机制:
    * 7 天预警:普通提醒
    * 3 天严重警告:紧急通知
    * 已过期:关键告警
  - 防止重复通知(24小时内只发送一次)
  - 详细的续期指引和操作步骤
  - Prometheus 指标集成

#### **Prometheus Alerts**
- ✅ **告警规则配置** (`config/prometheus/alerts.yml`)
  - 高错误率告警 (>5% warning, >10% critical)
  - 慢响应时间告警 (P95 > 2s)
  - Token 过期告警(7天/3天/已过期)
  - 定时任务失败率告警
  - 服务实例下线告警
  - 数据库连接问题告警
  - 高内存使用告警
  - API 限流阈值告警

#### **Grafana Dashboards**
- ✅ **调度器监控面板** (`scheduler-monitoring.json`)
  - 定时任务执行率(成功/失败)
  - Token 过期天数仪表盘
  - 任务执行耗时(P95/P99)
  - 任务失败统计表

- ✅ **Token 过期监控面板** (`token-expiry-dashboard.json`)
  - Token 过期倒计时仪表盘
  - Token 状态表格(颜色编码)
  - Token 过期时间轴
  - 过期警告发送统计

#### **Testing**
- ✅ **Scheduler 单元测试**: 23 个测试用例,覆盖所有核心功能
  - 调度器初始化和生命周期
  - Interval 和 Cron 任务添加
  - 任务执行和异常处理
  - 指标收集验证
  - 多任务并发执行

- ✅ **Token Monitor 单元测试**: 13 个测试用例
  - 过期状态检测
  - 通知触发逻辑
  - 防重复通知
  - Prometheus 指标更新
  - 错误处理

#### **Integration**
- ✅ **Server 启动集成**
  - 调度器自动启动和注册所有任务
  - 优雅关闭:先停调度器再停服务器
  - 异常情况下确保调度器正确清理

#### **Configuration**
- ✅ **Docker Compose 更新**
  - 将 Prometheus 告警规则文件挂载到容器
  - 完整的监控和告警基础设施

**破坏性变更**: 无

**依赖更新**:
- 新增: `apscheduler==3.10.4`
- 新增: `tzlocal>=2.0` (apscheduler 依赖)

### 🚀 Feature: Production Infrastructure Enhancement (003-code-refactor-optimization Phase 2) (2026-01-22)

#### Added - Monitoring and Observability

- **Prometheus Integration** (`config/prometheus.yml`)
  - Metrics collection from lark-service on port 9090
  - 15-second scrape interval for real-time monitoring
  - 30-day data retention
  - Preconfigured scrape targets: lark-service, prometheus, rabbitmq
  - Alert rules configuration support

- **Grafana Dashboard** (`config/grafana/dashboards/lark-service.json`)
  - **API Requests Rate (QPS)**: Real-time request rate per endpoint and method
  - **API Response Time**: P95 and P99 latency percentiles
  - **Error Rate Gauge**: 5xx error rate with color-coded thresholds
  - **Rate Limiting Panel**: Track auth rate limit triggers
  - **Token Refresh Status**: Monitor token refresh success/retry metrics
  - Auto-refresh every 10 seconds
  - 6-hour default time range

- **Grafana Provisioning** (`config/grafana/provisioning/`)
  - Auto-configured Prometheus datasource
  - Dashboard auto-loading on startup
  - No manual Grafana setup required

#### Enhanced - Docker and Orchestration

- **Docker Compose Services** (`docker-compose.yml`)
  - **prometheus**: Metrics collection server (port 9091)
    - Resource limits: 0.5 CPU, 512MB memory
    - Persistent storage volume: `prometheus_data`
    - 30-day retention policy
  - **grafana**: Visualization dashboard (port 3000)
    - Default admin credentials configurable via env vars
    - Resource limits: 0.5 CPU, 512MB memory
    - Persistent storage volume: `grafana_data`
    - Provisioned datasources and dashboards
  - **lark-service**: Enhanced monitoring support
    - Exposed metrics endpoint on port 9090
    - Environment variables: `PROMETHEUS_ENABLED`, `METRICS_PORT`

- **Updated Dependencies**
  - Added `prometheus-client==0.21.1` to requirements.txt and requirements-prod.txt
  - Support for metric exposition and collection

#### Enhanced - CI/CD Pipeline

- **GitHub Actions Workflow** (`.github/workflows/ci-cd.yml`)
  - **Build Job**: Docker image build and validation
    - Docker Buildx setup for multi-platform support
    - Build cache optimization (GitHub Actions cache)
    - Image size verification (must be < 500MB)
    - Container health check testing
  - **Verify Job**: Enhanced test coverage reporting
    - Codecov integration for coverage upload
    - Coverage reports uploaded as artifacts
  - **Deploy Job**: Now depends on both verify and build jobs
    - Ensures Docker image passes all checks before deployment

- **Quality Gates**
  - ✅ Docker image size < 500MB (enforced in CI)
  - ✅ Container starts successfully
  - ✅ Health check endpoint responds within 10 seconds
  - ✅ All tests pass before build

#### Documentation

- **Updated Deployment Guide**
  - Monitoring setup instructions (Prometheus + Grafana)
  - Dashboard access and configuration
  - Metric endpoint documentation
  - Production deployment checklist

---

### 🚀 Feature: Application Management and Code Refactoring (003-code-refactor-optimization Phase 1) (2026-01-22)

#### Added - Core Application Management

- **BaseServiceClient** (`src/lark_service/core/base_service_client.py`)
  - Abstract base class for all service clients with unified `app_id` management
  - 5-layer `app_id` resolution priority:
    1. Method parameter (highest priority)
    2. Context manager (`use_app()`)
    3. Client-level default
    4. CredentialPool-level default
    5. Auto-detection (ApplicationManager)
  - `get_current_app_id()`: Get currently resolved app_id without raising errors
  - `list_available_apps()`: List all active applications from CredentialPool
  - `use_app(app_id)`: Context manager for temporary app switching
  - Thread-local context stack for safe nested context managers
  - Comprehensive error messages with available apps list

- **Enhanced CredentialPool** (`src/lark_service/core/credential_pool.py`)
  - `set_default_app_id(app_id)`: Set pool-level default app_id
  - `get_default_app_id()`: Get pool-level default with fallback to ApplicationManager
  - `list_app_ids()`: List all active application IDs
  - Factory methods for creating service clients:
    - `create_messaging_client(app_id=None)`
    - `create_contact_client(app_id=None)`
    - `create_clouddoc_client(app_id=None)`
    - `create_workspace_table_client(app_id=None)`

- **Enhanced ApplicationManager** (`src/lark_service/core/storage/sqlite_storage.py`)
  - `get_default_app_id()`: Intelligent default selection
    - Returns single app_id if only one active application exists
    - Returns None for multiple apps (requires explicit selection)
    - Supports auto-detection in single-app scenarios

#### Changed - Service Client Refactoring

- **MessagingClient** (`src/lark_service/messaging/client.py`)
  - Now inherits from `BaseServiceClient`
  - All 6 methods updated: `app_id` parameter moved from required first position to optional last position
  - Methods: `send_text_message`, `send_rich_text_message`, `send_image_message`, `send_file_message`, `send_card_message`, `send_batch_messages`
  - Internal `app_id` resolution via `_resolve_app_id()`
  - **Backward compatible**: Existing code continues to work

- **ContactClient** (`src/lark_service/contact/client.py`)
  - Now inherits from `BaseServiceClient`
  - All 9 methods updated with same pattern as MessagingClient
  - Methods: `get_user`, `get_user_by_email`, `get_user_by_mobile`, `get_user_by_user_id`, `batch_get_users`, `get_department`, `get_department_members`, `get_chat_group`, `get_chat_members`

- **DocClient** (`src/lark_service/clouddoc/client.py`)
  - Now inherits from `BaseServiceClient`
  - All 8 methods updated: `create_document`, `get_document`, `append_blocks`, `update_document_title`, `create_folder`, `move_document`, `delete_document`, `list_permissions`

- **WorkspaceTableClient** (`src/lark_service/apaas/client.py`)
  - Now inherits from `BaseServiceClient`
  - All 10 methods updated: `list_workspace_tables`, `list_fields`, `sql_query`, `query_records`, `create_record`, `update_record`, `delete_record`, `batch_create_records`, `batch_update_records`, `batch_delete_records`

#### Added - Documentation

- **Application Management Guide** (`docs/usage/app-management.md`, 850+ lines)
  - Complete guide to 5-layer app_id resolution priority
  - Scenario 1: Single-app auto-detection with examples
  - Scenario 2: Multi-app with client-level defaults
  - Scenario 3: Dynamic switching with `use_app()` context manager
  - Scenario 4: Method parameter override (highest priority)
  - Scenario 5: Nested context managers
  - Utility methods: `get_current_app_id()`, `list_available_apps()`
  - Error handling: ConfigError, app not found scenarios
  - Thread safety notes and best practices
  - All code examples include complete imports, real types, and return values

- **Advanced Usage Guide** (`docs/usage/advanced.md`, 450+ lines)
  - Multi-application management strategies
  - Dynamic app switching by business logic
  - Multi-service client coordination
  - Custom retry strategies
  - Batch operations optimization
  - Tiered error handling best practices
  - Logging configuration
  - Performance optimization (token caching, connection pool reuse)
  - Security best practices (environment variables, file permissions, token expiry handling)

- **Updated Service Guides**
  - `docs/usage/messaging.md`: Added application management section
  - `docs/usage/contact.md`: Added application management section
  - `docs/usage/clouddoc.md`: Added application management section
  - `docs/usage/apaas.md`: Added application management section
  - Each includes quick examples and links to detailed app-management.md

#### Added - Testing

- **BaseServiceClient Tests** (`tests/unit/core/test_base_service_client.py`)
  - 16 unit tests covering all functionality
  - Tests for all 5 resolution priority layers
  - Context manager tests (single, nested, exception cleanup)
  - Multi-client isolation tests

- **CredentialPool App Management Tests** (`tests/unit/core/test_credential_pool.py`)
  - `set_default_app_id` validation tests
  - `get_default_app_id` fallback tests
  - `list_app_ids` tests

- **ApplicationManager Tests** (`tests/unit/core/test_application_manager.py`)
  - `get_default_app_id` tests for single-app, multi-app, no-app scenarios
  - Active/inactive application filtering

- **Integration Tests** (`tests/integration/test_app_switching.py`)
  - 20 total integration tests (13 existing + 7 new)
  - `TestCloudDocClientSwitching`: 3 tests for DocClient app resolution
  - `TestWorkspaceTableClientSwitching`: 3 tests for WorkspaceTableClient
  - `TestMultiClientCoordination`: Multi-client isolation and shared pool tests
  - All tests verify 5-layer priority resolution
  - Tests cover context managers, nested contexts, method overrides

#### Technical Improvements

- **Code Reduction**: Single-app scenarios now require ~30% less code
- **100% Backward Compatible**: All existing tests pass without modification
- **Type Safety**: Full mypy compliance with no `type: ignore` comments
- **Code Quality**: All code passes ruff format, ruff check, bandit security checks
- **Test Coverage**: 123+ tests (90+ unit, 33 integration) covering new functionality

#### Breaking Changes

- **None** - This release is 100% backward compatible
- Existing code using explicit `app_id` parameters continues to work
- New optional `app_id` parameter added at end of method signatures (backward compatible)

#### Known Limitations

- `use_app()` context manager is designed for single-threaded use within a client instance
- Concurrent calls to `use_app()` on the same client from different threads are not supported
- Recommended: Each thread should use its own client instance or manage `app_id` explicitly
- Context stack is thread-local, ensuring thread safety for the stack itself

#### Migration Guide

**Before (explicit app_id required):**
```python
from lark_service.messaging.client import MessagingClient

client = MessagingClient(credential_pool)
client.send_text_message(app_id="cli_xxx", receiver_id="ou_xxx", content="Hello")
```

**After (single-app auto-detection):**
```python
from lark_service.messaging.client import MessagingClient

client = MessagingClient(credential_pool)  # Auto-detects app_id
client.send_text_message(receiver_id="ou_xxx", content="Hello")
```

**After (multi-app with factory method):**
```python
client = credential_pool.create_messaging_client(app_id="cli_xxx")
client.send_text_message(receiver_id="ou_xxx", content="Hello")
```

**After (multi-app with context manager):**
```python
client = credential_pool.create_messaging_client(app_id="cli_default")

# Temporarily switch to another app
with client.use_app("cli_temp"):
    client.send_text_message(receiver_id="ou_xxx", content="Temp app message")

# Back to default app
client.send_text_message(receiver_id="ou_yyy", content="Default app message")
```

---

### 🚀 Feature: WebSocket User Authorization - Phase 9 (2026-01-20)

#### Added - Monitoring and Configuration
- **Comprehensive Prometheus Metrics** (`src/lark_service/monitoring/websocket_metrics.py`)
  - Auth session metrics: `auth_session_total`, `auth_session_active`, `auth_session_expired_total`
  - Auth success/failure metrics: `auth_success_total`, `auth_failure_total` (with reason labels)
  - Auth performance: `auth_duration_seconds` histogram (p50, p95, p99)
  - Token metrics: `token_refresh_total`, `token_active_count`
  - Integrated into `AuthSessionManager` and `CardAuthHandler`

- **Enhanced Structured Logging** (`src/lark_service/utils/logger.py`)
  - Added `session_id` support to `ContextFilter`
  - Updated console and JSON log formats with session_id field
  - New `sanitize_log_data()` function for masking sensitive data
  - Auto-detects and masks: access_token, refresh_token, app_secret, authorization_code, password
  - Preserves token prefixes (e.g., "u-abc***") for debugging

- **Grafana Dashboard** (`docs/monitoring/grafana-dashboard.json`)
  - 8 monitoring panels: connection status, reconnect rate, auth sessions, success rate
  - Auth failure analysis by reason, duration p95, token refresh rate
  - Ready-to-import JSON for Grafana 9.5+

- **Prometheus Alert Rules** (`docs/monitoring/alert-rules.yaml`)
  - 4 alert groups: WebSocket, Authentication, Token, System
  - 10 production-ready alerts with thresholds:
    - WebSocket connection down (>5min), high reconnect rate (>0.1/sec)
    - Auth success rate low (<95%), failure rate high (>0.5/sec), duration high (p95 >15s)
    - Token refresh failures (>10%), no active tokens
    - Session cleanup issues, table growth monitoring

- **Environment Variables Documentation** (`.env.example`)
  - WebSocket configuration: max retries, heartbeat interval, fallback behavior
  - Auth configuration: card description, template ID, token refresh threshold, session expiry, rate limiting
  - User info sync: enable/disable, cron schedule
  - Monitoring: Prometheus port, JSON log format

#### Changed
- **AuthSessionManager** now tracks metrics for all session lifecycle operations
- **CardAuthHandler** records failure reasons for auth failure metrics

### 🚀 Feature: WebSocket User Authorization - Phase 3-8 (2026-01-20)

#### Added - Phase 3 WebSocket Client
- **WebSocket Client Implementation** (`src/lark_service/events/websocket_client.py`)
  - Connection lifecycle: `connect()`, `start()`, `disconnect()`
  - Exponential backoff reconnect (1s → 2s → 4s → 8s)
  - Heartbeat tracking and connection state updates
  - Event handler registration (P2CardActionTrigger)
  - Structured logging for connection state changes

- **WebSocket Metrics** (`src/lark_service/monitoring/websocket_metrics.py`)
  - `lark_service_websocket_connection_status`
  - `lark_service_websocket_reconnect_total`

- **Tests**
  - Unit tests for WebSocket client (`tests/unit/events/test_websocket_client.py`)
  - Integration lifecycle test (`tests/integration/test_websocket_lifecycle.py`)

#### Fixed - Testing Infrastructure
- **Circular import in utils package**
  - Converted validators to lazy imports in `src/lark_service/utils/__init__.py`
  - Prevented import cycle during WebSocket test collection

### 🚀 Feature: WebSocket User Authorization (2026-01-19)

#### Added - Phase 2 Foundational Infrastructure
- **WebSocket Authentication Configuration** (`src/lark_service/core/config.py`)
  - 10 new configuration parameters for WebSocket user authorization
  - All parameters have backward-compatible default values
  - Configurable: reconnect retries, heartbeat interval, fallback behavior, token refresh threshold, etc.

- **Auth Module** (`src/lark_service/auth/`)
  - 8 custom exception classes following PEP 8 naming conventions
    - `AuthError`, `AuthenticationRequiredError`, `TokenExpiredError`, `TokenRefreshFailedError`
    - `AuthSessionNotFoundError`, `AuthSessionExpiredError`, `AuthorizationRejectedError`, `AuthorizationCodeExpiredError`
  - 3 type definition classes with full type annotations
    - `AuthCardOptions`, `UserInfo`, `AuthSession`

- **Events Module** (`src/lark_service/events/`)
  - 2 WebSocket-related exception classes
    - `WebSocketError`, `WebSocketConnectionError`
  - 2 type definition classes for WebSocket configuration and status
    - `WebSocketConfig`, `WebSocketConnectionStatus`

- **Database Schema Extension**
  - Extended `user_auth_sessions` table with 5 new user info columns
    - `user_id`, `union_id`, `user_name`, `mobile`, `email`
  - Added 3 new indexes for query optimization
    - `idx_auth_session_user`, `idx_auth_session_token_expires`, `idx_auth_session_open_id`
  - Added 4 check constraints for data integrity
  - Migration: `20260119_2100_a8b9c0d1e2f3_extend_auth_session_for_websocket.py`

#### Fixed - Integration Tests
- **PostgreSQL Connection Issues** (18 ERROR fixes)
  - Updated all integration tests to use correct PostgreSQL username (`lark_user` instead of `lark`)
  - Fixed `CredentialPool` instantiation in `test_sheet_e2e.py`
  - Affected files: 9 integration test files
  - Test results improved from 613 passed to 631 passed

#### Documentation
- **Phase 2 Deliverables**
  - Data model design (`specs/002-websocket-user-auth/data-model.md`)
  - API contracts (WebSocket events + Auth session API)
  - 5-minute quickstart guide (`specs/002-websocket-user-auth/quickstart.md`)
  - Comprehensive test report (`specs/002-websocket-user-auth/PHASE2-TEST-REPORT.md`)
- **Updated Documentation**
  - `specs/002-websocket-user-auth/README.md` - Phase 2 completion status
  - `specs/002-websocket-user-auth/plan.md` - Implementation progress
  - `specs/002-websocket-user-auth/tasks.md` - Task completion tracking
  - `specs/002-websocket-user-auth/checklists/pre-implementation.md` - Quality validation

#### Quality Metrics
- ✅ Code format: 100% pass (ruff format)
- ✅ Code style: 100% pass (ruff check)
- ✅ Type checking: 100% pass (mypy, 7 new files)
- ✅ Unit tests: 631 passed (+18 from Phase 1)
- ✅ Database migration: Successfully applied
- ✅ Backward compatibility: All existing tests pass

#### Commits
- `abd2543` - feat(auth): implement Phase 2 foundational infrastructure
- `a2d765b` - fix(config): add default values for WebSocket auth parameters
- `24a62c9` - fix(tests): 修复集成测试中的 PostgreSQL 用户名和 CredentialPool 实例化问题
- `a77bc9c` - docs(002): 更新 Phase 2 文档,记录集成测试修复

### ✅ Production Readiness (2026-01-18)

#### Fixed - P1 Blocking Items
- **CHK158**: Added `requirements-prod.txt` with exact dependency version locking (72 dependencies)
  - Removed all editable installs (`-e` flags)
  - Ensures stable and reproducible production environment
- **CHK199**: Database migration rollback mechanism
  - Created comprehensive rollback documentation (`docs/database-migration-rollback.md`)
  - Added automated rollback test script (`scripts/test_migration_rollback.sh`)
  - Verified all Alembic migration scripts include `downgrade()` functions
  - Documented emergency rollback procedures (RTO: 15 minutes)
- **CHK200**: Database backup and recovery
  - Implemented automated backup script (`scripts/backup_database.sh`)
  - Implemented database restore script (`scripts/restore_database.sh`)
  - Updated deployment documentation with detailed backup/recovery procedures
  - Defined RPO: 1 hour, RTO: 4 hours

#### Added - Production Readiness
- **Production Readiness Evaluation**: Complete assessment of all 217 checklist items
  - Comprehensive evaluation summary report (`production-readiness-evaluation-summary.md`)
  - Production readiness score: 90/100 (ready for staging validation)
  - Identified 11 P2 important issues for future improvement
  - Identified 3 P3 optional improvements for later versions

#### Documentation
- Enhanced `docs/deployment.md` with §12 Backup and Recovery section
- Added `docs/database-migration-rollback.md` with complete rollback procedures
- Updated `CURRENT-STATUS.md` to reflect production readiness milestone
- Updated `QUICK-START-NEXT-CHAT.md` for next session guidance

## [0.1.0] - 2026-01-18

### ✨ Added

#### Core Features (US1 - Token Management)
- **Transparent Token Management**: Automatic acquisition, refresh, and persistence of Feishu access tokens
  - Support for `app_access_token`, `tenant_access_token`, and `user_access_token`
  - Lazy loading with automatic refresh before expiration (configurable threshold)
  - Multi-application isolation with separate token pools per `app_id`
  - PostgreSQL-based token persistence with encryption
  - Thread-safe and process-safe locking mechanism
- **CLI Tool**: Command-line interface for application configuration management
  - `lark-service-cli app add/list/show/update/delete/enable/disable`
  - SQLite-based configuration storage with Fernet encryption for secrets
- **Credential Pool**: Centralized credential management with retry logic
  - Exponential backoff retry strategy (configurable)
  - Rate limiting detection and handling
  - Token invalidation recovery

#### Messaging Service (US2)
- **Message Client**: Send various message types to users and groups
  - Text messages (`send_text_message`)
  - Rich text messages (`send_rich_text_message`)
  - Image messages (`send_image_message` with auto-upload)
  - File messages (`send_file_message` with auto-upload)
  - Interactive card messages (`send_card_message`)
  - Batch messaging (`send_batch_messages`)
- **Message Lifecycle**: Message management capabilities
  - Message recall (`recall_message`)
  - Message edit (`edit_message` for text messages)
  - Message reply (`reply_message`)
- **CardKit**: Interactive card builder and callback handling
  - Pre-built card templates (approval, notification, form)
  - Custom card builder with flexible layout
  - Callback signature verification
  - URL verification handler
  - Callback event routing
  - Card content update (proactive and responsive)
- **Media Uploader**: Upload images and files with validation
  - Size limits (20MB for images, 100MB for files)
  - Format validation
  - Automatic key extraction for messaging

#### CloudDoc Service (US3)
- **Doc Client**: Document operations with permission management
  - Get document metadata (`get_document`)
  - Permission management (`grant_permission`, `revoke_permission`, `list_permissions`)
- **Bitable Client**: Multi-dimensional table (Bitable) operations
  - Create records (`create_record`)
  - Query records with filters and pagination (`query_records`)
  - Update records (`update_record`)
  - Delete records (`delete_record`)
  - Batch operations (`batch_create/update_records`)
  - List fields and metadata (`list_fields`)
- **Sheet Client**: Spreadsheet operations
  - Read sheet data with range specification (`get_sheet_data`)
  - Update sheet data (`update_sheet_data`)
  - Format cells (style, font, color, alignment)
  - Merge cells and freeze panes
  - Set column width and row height

#### Contact Service (US4)
- **Contact Client**: User and department lookup
  - Get user by email/mobile/user_id (`get_user_by_email`, `get_user_by_mobile`, `get_user_by_id`)
  - Batch get users (`batch_get_users_by_id`)
  - Get department info (`get_department_by_id`)
  - List department users (`list_department_users`)
  - Search users and departments (`search_users`, `search_departments`)
- **Contact Cache**: PostgreSQL-based caching with TTL
  - Configurable TTL (default 24 hours)
  - Automatic cache invalidation on expiry
  - Application-level isolation (`app_id`)
  - Cache statistics and monitoring

#### aPaaS Data Space (US5)
- **Workspace Table Client**: Data space table operations
  - List workspace tables (`list_workspace_tables`)
  - List field definitions (`list_fields`)
  - Query records with filters (`query_records`)
  - Create/Update/Delete records (`create_record`, `update_record`, `delete_record`)
  - Batch operations with auto-chunking (`batch_create/update/delete_records`)
  - **SQL Commands API**: Powerful SQL query execution (`sql_query`)
    - Support for SELECT, INSERT, UPDATE, DELETE
    - Complex queries with WHERE, ORDER BY, LIMIT
    - Batch operations in single SQL statement
- **SQL Injection Protection**: Automatic value escaping (`_format_sql_value`)
  - Safe handling of strings, numbers, booleans, NULL, dates
  - Bandit security scan compliant
- **DataFrame Integration**: Pandas DataFrame batch synchronization
  - Automatic type inference and conversion
  - Auto-chunking (500 records per batch)
  - Support for incremental updates
- **Data Type Mapping**: Intelligent PostgreSQL ↔ FieldType conversion
  - 17 supported FieldType mappings
  - Automatic type detection and validation

### 🧪 Testing

#### Test Infrastructure
- **Test-Driven Development (TDD)**: All features developed test-first
  - Unit tests: 306 passed, 29 skipped
  - Contract tests: 100+ scenarios validated against OpenAPI specs
  - Integration tests: 35+ real API integration tests
- **End-to-End Tests**: Complete application flow validation
  - Application initialization → Token → Messaging → CloudDoc → Contact → aPaaS
  - Multi-app isolation and token persistence verification
  - Complete user journey from init to operations
- **Concurrency Tests**: High-load concurrent access validation
  - 100 concurrent token requests without bottleneck
  - Multi-app isolation under concurrency
  - Database connection pool stress testing
  - Stress test with 1000 concurrent requests
- **Failure Recovery Tests**: System resilience validation
  - Database disconnection/reconnection
  - Token invalidation and re-acquisition
  - API rate limiting and network timeout handling
  - Cascading failure recovery
  - Data corruption resilience

#### Test Coverage
- **Overall Coverage**: 49% (core modules > 90%)
  - `core/`: 98%
  - `messaging/`: 95%
  - `contact/`: 96%
  - `apaas/`: 100%
  - `clouddoc/`: 85%
  - `utils/`: 92%

### 🐳 Docker & Deployment

#### Docker Optimization
- **Multi-stage Build**: Separate builder and runtime stages
  - Builder stage: Compile dependencies (gcc, libpq-dev)
  - Runtime stage: Minimal image with only runtime dependencies (libpq5)
  - Final image size: ~320MB (< 500MB target, 36% reduction)
- **Domestic Mirror Sources**: Accelerated build for China regions
  - Debian mirrors: Aliyun
  - PyPI mirrors: Tsinghua University
  - Build time: 3-5 minutes (50% improvement from 10+ minutes)
- **Security Hardening**:
  - Non-root user (`lark`, UID 1000)
  - Minimal privileges
  - Health checks configured
  - No hardcoded secrets
- **Docker Compose V2**: Modern orchestration
  - Native resource limits (`cpus`, `mem_limit`, `mem_reservation`)
  - Service health checks
  - Log rotation (json-file driver, 50MB max, 5 files)
  - Updated service versions (PostgreSQL 16, RabbitMQ 3.13)
- **.dockerignore**: Optimized build context
  - Build context reduced: 50MB → 5MB (90% reduction)

#### CI/CD Pipeline
- **GitHub Actions Workflows**:
  - Code quality: Ruff linter + formatter
  - Type checking: Mypy (100% coverage on src/)
  - Security scanning: Bandit
  - Unit & contract tests with PostgreSQL + RabbitMQ services
  - Docker image build and size validation
  - Integration tests (optional, on main branch)
  - Automated release tagging

### 📚 Documentation

#### Core Documentation
- **README.md**: Project overview and quick start guide
- **architecture.md**: System architecture and design patterns
- **deployment.md**: Deployment guide and best practices
- **security-guide.md**: Security guidelines and threat model
- **testing-strategy.md**: Testing approach and coverage
- **docker-optimization-guide.md**: Docker optimization strategies (467 lines)
- **docker-migration-report.md**: Docker Compose V2 migration report (289 lines)

#### API Documentation
- **OpenAPI Contracts**: Complete API specifications (5 services)
  - `contracts/messaging.yaml`
  - `contracts/cardkit.yaml`
  - `contracts/clouddoc.yaml`
  - `contracts/contact.yaml`
  - `contracts/apaas.yaml`

#### Phase Reports
- **Phase 1-5 Completion Reports**: Detailed progress and handoff documentation
- **Phase 6 Readiness Checklists**: Pre-launch validation (85 checklist items)

### 🏗️ Architecture

#### Technology Stack
- **Language**: Python 3.12
- **SDK**: lark-oapi (official Feishu Open API SDK)
- **Database**: PostgreSQL 16 (token storage, caching)
- **Message Queue**: RabbitMQ 3.13 (async processing)
- **ORM**: SQLAlchemy 2.0
- **Encryption**: Fernet (symmetric encryption for secrets)
- **Validation**: Pydantic v2 (data models and validation)

#### Code Quality Tools
- **Linter**: Ruff (fast, comprehensive)
- **Type Checker**: Mypy (strict mode, 99%+ coverage)
- **Formatter**: Ruff format
- **Security Scanner**: Bandit
- **Pre-commit Hooks**: Automated quality checks before commits

#### Design Patterns
- **Domain-Driven Design (DDD)**: Clean layered architecture
  - Application Layer: CLI tools, API endpoints
  - Core/Domain Layer: Business logic, credential management
  - Data Layer: Storage services, models
- **Repository Pattern**: Abstract data access
- **Factory Pattern**: Client initialization
- **Strategy Pattern**: Retry and backoff logic
- **Observer Pattern**: Callback event handling

### ⚙️ Configuration

#### Environment Variables
- **Database**: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Message Queue**: `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`
- **Encryption**: `LARK_CONFIG_ENCRYPTION_KEY` (32-byte Fernet key)
- **Logging**: `LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Retry**: `MAX_RETRIES`, `RETRY_BACKOFF_BASE`
- **Token**: `TOKEN_REFRESH_THRESHOLD` (0.1 = refresh at 10% remaining lifetime)

#### Configuration Files
- **Application Config**: `applications.db` (SQLite, encrypted)
- **.env**: Environment-specific configuration (not in Git)
- **.env.example**: Template for environment variables
- **pyproject.toml**: Project metadata and tool configuration

### 📈 Performance

#### Benchmarks
- **Token Acquisition**: Average < 500ms per request
- **Concurrent Requests**: 100 concurrent tokens in < 10s (average < 100ms per request)
- **Cache Hit Rate**: > 90% for repeated lookups
- **Database Connection Pool**: Handles 200+ concurrent operations without errors

#### Scalability
- **Multi-application Support**: Isolated token pools per `app_id`
- **Horizontal Scaling**: Stateless design (tokens in PostgreSQL)
- **Connection Pooling**: Configurable pool size and overflow

### 🔒 Security

#### Implemented Security Measures
- **Credential Encryption**: Fernet encryption for `app_secret` in SQLite
- **Token Encryption**: PostgreSQL `pg_crypto` for token storage
- **SQL Injection Protection**: Parameterized queries and value escaping
- **Signature Verification**: Feishu callback signature validation
- **Non-root Containers**: Docker containers run as non-root user
- **Secret Management**: No hardcoded credentials, environment variable injection
- **Security Scanning**: Bandit scan in CI/CD pipeline

#### Compliance
- **Constitution Adherence**: 100% compliance with project constitution (v1.2.0)
  - Principle I: Python 3.12 + lark-oapi SDK
  - Principle II: Mypy 99%+ + Ruff + Docstrings
  - Principle III: DDD architecture, no circular dependencies
  - Principle IV: Standardized response structure
  - Principle V: Encryption + environment variables
  - Principle VI: Environment isolation
  - Principle VII: Zero trust (no hardcoded secrets)
  - Principle VIII: TDD (tests before code)
  - Principle IX: Code in English, docs in Chinese
  - Principle X: File operation closure
  - Principle XI: Conventional Commits + quality checks

### 📊 Project Statistics

- **Code Lines**: 10,000+ lines (excluding tests and docs)
- **Test Lines**: 8,000+ lines (unit + contract + integration)
- **Documentation**: 5,000+ lines (markdown docs + docstrings)
- **API Methods**: 50+ public API methods across 5 services
- **Test Scenarios**: 400+ test cases
- **Commits**: 30+ commits following Conventional Commits

## Known Limitations

### Deferred to v0.2.0

#### P2 Priority
- **SQL Builder**: Query builder class to reduce manual SQL construction
  - Workaround: Use `_format_sql_value()` for safe value escaping
- **MediaClient**: Document asset upload/download
  - Workaround: Use messaging media uploader for now

#### P3 Priority
- **DataFrame Sync Documentation**: Complete usage examples
- **SQL Performance Benchmarks**: SQL vs RESTful API comparison
- **CloudDoc Write Operations**: Some Placeholder methods (create_document, append_content, update_block)
  - Current: Read operations fully implemented

### Operational Considerations

#### Manual Setup Required
- **Database Initialization**: PostgreSQL tables must be created via Alembic migrations
- **Application Configuration**: First app must be added via CLI
- **Secret Management**: `LARK_CONFIG_ENCRYPTION_KEY` must be generated and stored securely

#### External Dependencies
- **Feishu API Availability**: Service depends on Feishu Open API uptime
- **Database Availability**: PostgreSQL required for token storage and caching
- **Message Queue**: RabbitMQ required for async card callback processing (future)

#### Rate Limiting
- **Feishu API Rate Limits**: Subject to Feishu's rate limiting policies
  - Automatic retry with exponential backoff implemented
  - Manual throttling may be needed for high-volume scenarios

## Upgrade Path

### From Development to v0.1.0
1. Pull latest code from `001-lark-service-core` branch
2. Run database migrations: `alembic upgrade head`
3. Update environment variables (see `.env.example`)
4. Rebuild Docker images: `docker compose build`
5. Run tests: `pytest tests/unit/ tests/contract/`
6. Deploy using `docker-compose.yml`

### Future Versions
- **v0.2.0**: SQL Builder, MediaClient, complete CloudDoc write operations
- **v0.3.0**: Advanced features (batch retry, webhook server, async task queue)
- **v1.0.0**: Production hardening, performance optimization, comprehensive monitoring

---

## Acknowledgments

- **Feishu Open Platform**: For comprehensive API documentation
- **lark-oapi SDK**: Official Python SDK for Feishu APIs
- **Open Source Community**: For excellent tools (Ruff, Mypy, SQLAlchemy, Pydantic)

## Support

For issues, questions, or contributions:
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: See `docs/` folder for detailed guides
- **Contributing**: Follow the development guidelines in `docs/development-guide.md`

---

**Project**: Lark Service 企业自建应用核心组件
**Status**: v0.1.0 Production Ready
**License**: Proprietary (Internal Use)
**Last Updated**: 2026-01-18
