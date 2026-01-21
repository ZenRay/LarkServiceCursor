# Data Model: 代码重构与应用管理

**Feature**: 003-code-refactor-optimization
**Date**: 2026-01-21
**Phase**: Phase 1 - Design

## Overview

本文档定义了代码重构后的核心数据模型和实体关系。重构的核心目标是通过引入 BaseServiceClient 基类统一 app_id 管理逻辑,简化单应用场景,优雅支持多应用场景。

## Core Entities

### 1. BaseServiceClient (新增抽象基类)

**职责**: 提供所有服务客户端统一的 app_id 管理能力

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| credential_pool | CredentialPool | ✅ | - | 凭证池实例,用于获取 SDK 客户端 |
| _default_app_id | str \| None | ❌ | None | 客户端级默认 app_id |
| _context_app_stack | list[str] | ✅ | [] | 上下文栈,支持嵌套 use_app() |

**方法**:

#### _resolve_app_id(app_id: str | None = None) -> str

**职责**: 按优先级解析 app_id

**优先级**:
1. 方法参数 `app_id` (最高优先级)
2. 上下文栈顶元素 `_context_app_stack[-1]`
3. 客户端默认值 `_default_app_id`
4. CredentialPool 默认值 `credential_pool.get_default_app_id()`
5. 抛出 ConfigError (无法确定)

**返回**: 解析后的 app_id (str)

**异常**: ConfigError (当无法确定 app_id 时)

**示例**:
```python
# 场景 1: 方法参数最高优先级
client = MessagingClient(pool, app_id="client_default")
with client.use_app("context_app"):
    resolved = client._resolve_app_id(app_id="param_app")
    # resolved == "param_app"

# 场景 2: 上下文管理器优先级
client = MessagingClient(pool, app_id="client_default")
with client.use_app("context_app"):
    resolved = client._resolve_app_id()
    # resolved == "context_app"

# 场景 3: 客户端默认值优先级
client = MessagingClient(pool, app_id="client_default")
resolved = client._resolve_app_id()
# resolved == "client_default"

# 场景 4: CredentialPool 默认值优先级
pool.set_default_app_id("pool_default")
client = MessagingClient(pool)
resolved = client._resolve_app_id()
# resolved == "pool_default"

# 场景 5: 无法确定,抛出错误
client = MessagingClient(pool)  # 无任何默认值
try:
    resolved = client._resolve_app_id()
except ConfigError as e:
    # e.message 包含详细修复建议和可用 app_id 列表
    pass
```

#### get_current_app_id() -> str | None

**职责**: 获取当前使用的 app_id (不抛出异常)

**返回**:
- 成功: 当前 app_id (str)
- 失败: None

**说明**:
- 调用 `_resolve_app_id()`,捕获 ConfigError 并返回 None
- 用于调试和确认当前应用场景

#### list_available_apps() -> list[str]

**职责**: 列出所有可用的应用 ID

**返回**: 活跃应用 ID 列表 (list[str])

**说明**: 委托给 `credential_pool.list_app_ids()`

#### use_app(app_id: str) -> ContextManager

**职责**: 临时切换应用的上下文管理器

**参数**:
- app_id: 目标应用 ID

**行为**:
- 进入上下文: 将 app_id 压入 `_context_app_stack` 栈
- 退出上下文: 从栈中弹出,恢复到上一个 app_id

**异常**:
- AuthenticationError: 当 app_id 不存在时

**支持嵌套**:
- 内层上下文覆盖外层
- 退出内层后自动恢复外层

**线程安全警告**:
- ⚠️ 不支持多线程并发使用同一客户端实例
- 推荐并发场景: 使用工厂方法创建独立客户端或显式传递 app_id 参数

**示例**:
```python
client = MessagingClient(pool, app_id="app1")

# 单层上下文
with client.use_app("app2"):
    # 此处使用 app2
    client.send_text_message(receiver_id="ou_xxx", text="From App2")
# 自动恢复到 app1

# 嵌套上下文
with client.use_app("app2"):
    print(client.get_current_app_id())  # app2
    with client.use_app("app3"):
        print(client.get_current_app_id())  # app3
    print(client.get_current_app_id())  # app2 (自动恢复)
```

**状态转换**:

```
[初始状态: _context_app_stack = []]
    ↓ use_app("app2")
[上下文状态: _context_app_stack = ["app2"]]
    ↓ use_app("app3") (嵌套)
[嵌套状态: _context_app_stack = ["app2", "app3"]]
    ↓ exit inner context
[恢复状态: _context_app_stack = ["app2"]]
    ↓ exit outer context
[初始状态: _context_app_stack = []]
```

---

### 2. CredentialPool (重构增强)

**现有职责**: 管理飞书应用凭证,缓存 SDK 客户端

**新增能力**: 默认 app_id 管理 + 工厂方法

**新增属性**:

| 属性名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| _default_app_id | str \| None | ❌ | None | Pool 级默认 app_id |

**新增方法**:

#### set_default_app_id(app_id: str) -> None

**职责**: 设置默认应用 ID

**参数**:
- app_id: 应用 ID

**验证**:
- app_id 必须存在于 ApplicationManager 中
- app_id 对应的应用必须处于活跃状态

**异常**:
- ConfigError: 当 app_id 不存在或不活跃时

**副作用**: 记录 INFO 日志

#### get_default_app_id() -> str | None

**职责**: 获取默认 app_id

**返回逻辑**:
1. 如果 `_default_app_id` 已设置,直接返回
2. 否则委托给 `app_manager.get_default_app_id()`

**返回**:
- 成功: 默认 app_id (str)
- 失败: None

#### list_app_ids() -> list[str]

**职责**: 列出所有活跃的应用 ID

**返回**: 应用 ID 列表 (list[str])

**实现**:
```python
apps = self.app_manager.list_applications(status="active")
return [app.app_id for app in apps]
```

#### 工厂方法 (Factory Methods)

##### create_messaging_client(app_id: str | None = None) -> MessagingClient

**职责**: 创建绑定到特定应用的 MessagingClient

**参数**:
- app_id: 应用 ID (可选,默认使用 Pool 默认值)

**返回**: MessagingClient 实例

**示例**:
```python
app1_client = pool.create_messaging_client("app1")
app2_client = pool.create_messaging_client("app2")

app1_client.send_text_message(...)  # 使用 app1
app2_client.send_text_message(...)  # 使用 app2
```

##### create_contact_client(app_id: str | None = None) -> ContactClient

**职责**: 创建绑定到特定应用的 ContactClient

##### create_clouddoc_client(app_id: str | None = None) -> DocClient

**职责**: 创建绑定到特定应用的 DocClient

**说明**: 所有工厂方法遵循相同模式,返回预配置的客户端实例

---

### 3. ApplicationManager (重构增强)

**现有职责**: 管理应用配置 (CRUD)

**新增能力**: 智能默认应用选择

**新增方法**:

#### get_default_app_id() -> str | None

**职责**: 智能选择默认应用

**选择策略**:
1. 如果只有一个活跃应用 → 自动返回该应用 ID
2. 如果有多个活跃应用 → 返回第一个 (按创建时间排序)
3. 如果没有活跃应用 → 返回 None

**返回**:
- 成功: 默认 app_id (str)
- 失败: None

**日志记录**:
- 单应用场景: DEBUG 级别记录自动选择
- 多应用场景: DEBUG 级别记录选择第一个,并列出所有可用应用
- 无应用场景: WARNING 级别记录

**示例**:
```python
# 场景 1: 单应用
# 数据库: [Application(app_id="app1", is_active=True)]
default = manager.get_default_app_id()
# default == "app1"
# 日志: DEBUG "Single active app found: app1"

# 场景 2: 多应用
# 数据库: [
#   Application(app_id="app1", is_active=True, created_at="2024-01-01"),
#   Application(app_id="app2", is_active=True, created_at="2024-01-02")
# ]
default = manager.get_default_app_id()
# default == "app1" (按创建时间排序的第一个)
# 日志: DEBUG "Multiple active apps found, using first: app1. Available: ['app1', 'app2']"

# 场景 3: 无活跃应用
# 数据库: []
default = manager.get_default_app_id()
# default == None
# 日志: WARNING "No active applications found"
```

---

### 4. RateLimiter (新增功能实体)

**职责**: 用户请求限流,防止 API 滥用

**算法**: 滑动窗口算法

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| window_size | int | ✅ | 60 | 时间窗口大小 (秒) |
| max_requests | int | ✅ | 5 | 窗口内最大请求数 |
| _request_timestamps | dict[str, list[float]] | ✅ | {} | 用户请求时间戳记录 |

**方法**:

#### is_allowed(user_id: str) -> bool

**职责**: 检查用户是否允许发起请求

**参数**:
- user_id: 用户 ID

**返回**:
- True: 允许请求
- False: 超过限流阈值,拒绝请求

**算法**:
1. 获取用户的历史请求时间戳列表
2. 清理超出时间窗口的旧记录
3. 检查剩余记录数是否 < max_requests
4. 返回检查结果

#### record_request(user_id: str) -> None

**职责**: 记录用户请求时间戳

**参数**:
- user_id: 用户 ID

**副作用**:
- 在 `_request_timestamps[user_id]` 中添加当前时间戳
- 自动清理超出窗口的旧记录

**使用场景**:
```python
limiter = RateLimiter(window_size=60, max_requests=5)

# 检查并记录请求
if limiter.is_allowed(user_id):
    limiter.record_request(user_id)
    # 处理请求
else:
    # 返回 429 Too Many Requests
    raise RateLimitExceededError("请求过于频繁,请稍后重试")
```

**存储**:
- 当前使用内存存储 (dict)
- 服务重启后计数重置
- 生产环境可扩展为 Redis 存储

---

### 5. ScheduledTask (新增功能实体)

**职责**: 定时任务配置和调度

**属性**:

| 属性名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| task_name | str | ✅ | - | 任务名称 (唯一标识符) |
| schedule | str | ✅ | - | Cron 表达式或 APScheduler 调度策略 |
| handler | Callable | ✅ | - | 任务处理函数 |
| enabled | bool | ❌ | True | 是否启用此任务 |
| last_run | datetime \| None | ❌ | None | 上次执行时间 |
| next_run | datetime \| None | ❌ | None | 下次执行时间 |

**方法**:

#### execute() -> None

**职责**: 执行任务处理函数

**异常处理**:
- 捕获所有异常,记录错误日志
- 更新 last_run 时间戳
- 不中断调度器

#### is_due() -> bool

**职责**: 检查任务是否到期需要执行

**返回**:
- True: 任务到期
- False: 未到期或已禁用

**示例任务配置**:
```python
# 用户信息同步任务
sync_user_task = ScheduledTask(
    task_name="sync_user_info_batch",
    schedule="0 2 * * *",  # 每日凌晨 2 点
    handler=sync_user_info_batch_handler,
    enabled=True
)

# Token 刷新检查任务
token_refresh_task = ScheduledTask(
    task_name="check_token_expiry",
    schedule="interval",  # 每 10 分钟
    handler=check_token_expiry_handler,
    enabled=True
)
```

---

## Entity Relationships

```
┌─────────────────────┐
│ ApplicationManager  │
│                     │
│ + get_default_app_id()
│ + get_application() │
│ + list_applications()
└──────────┬──────────┘
           │ 1
           │ manages
           │ *
           ▼
    ┌──────────────┐
    │ Application  │ (现有实体)
    │              │
    │ - app_id     │
    │ - app_secret │
    │ - is_active  │
    └──────────────┘

┌─────────────────────────────┐
│ CredentialPool              │
│                             │
│ + set_default_app_id()      │
│ + get_default_app_id()      │
│ + list_app_ids()            │
│ + create_messaging_client() │
│ + create_contact_client()   │
└──────────┬──────────────────┘
           │ 1
           │ creates
           │ *
           ▼
┌──────────────────────────────┐
│ BaseServiceClient (抽象)     │
│                              │
│ - credential_pool            │
│ - _default_app_id            │
│ - _context_app_stack         │
│                              │
│ + _resolve_app_id()          │
│ + get_current_app_id()       │
│ + list_available_apps()      │
│ + use_app()                  │
└──────────┬───────────────────┘
           │
           │ inherits
           │
     ┌─────┴──────┬─────────────┬──────────────┐
     │            │             │              │
     ▼            ▼             ▼              ▼
┌─────────┐  ┌────────┐  ┌──────────┐  ┌──────────┐
│Messaging│  │Contact │  │ CloudDoc │  │  aPaaS   │
│ Client  │  │ Client │  │  Client  │  │  Client  │
└─────────┘  └────────┘  └──────────┘  └──────────┘

┌──────────────────┐
│ RateLimiter      │
│                  │
│ + is_allowed()   │
│ + record_request()
└──────────────────┘

┌──────────────────┐
│ ScheduledTask    │
│                  │
│ + execute()      │
│ + is_due()       │
└──────────────────┘
```

**关系说明**:
- ApplicationManager **管理** Application (1:N)
- CredentialPool **创建** BaseServiceClient 及其子类 (1:N)
- BaseServiceClient **被继承** 为各功能域客户端
- RateLimiter 和 ScheduledTask 为独立功能实体

---

## Data Validation Rules

### 1. app_id 验证

**规则**:
- 格式: 必须以 "cli_" 或 "cli" 开头
- 长度: 16-64 字符
- 字符集: 字母、数字、下划线

**验证点**:
- ApplicationManager.get_application() - 验证存在性
- CredentialPool.set_default_app_id() - 验证存在性和活跃状态
- BaseServiceClient.use_app() - 验证存在性

### 2. Rate Limiting 参数验证

**window_size**:
- 类型: int
- 范围: 1 ~ 3600 (秒)
- 默认值: 60

**max_requests**:
- 类型: int
- 范围: 1 ~ 1000
- 默认值: 5

### 3. ScheduledTask 验证

**task_name**:
- 唯一性: 系统范围内唯一
- 格式: snake_case

**schedule**:
- Cron 表达式: 标准 5 段式 (分 时 日 月 周)
- APScheduler 预设: "interval", "date", "cron"

**handler**:
- 必须是可调用对象 (Callable)
- 必须无参数或接受关键字参数

---

## State Transitions

### BaseServiceClient 上下文状态转换

```
[State: No Context]
    _context_app_stack = []
    current_app = _default_app_id or pool_default

    ↓ user calls use_app("app2")

[State: Single Context]
    _context_app_stack = ["app2"]
    current_app = "app2"

    ↓ user calls use_app("app3") (nested)

[State: Nested Context]
    _context_app_stack = ["app2", "app3"]
    current_app = "app3"

    ↓ inner context exits

[State: Single Context]
    _context_app_stack = ["app2"]
    current_app = "app2"

    ↓ outer context exits

[State: No Context]
    _context_app_stack = []
    current_app = _default_app_id or pool_default
```

### RateLimiter 状态转换

```
[State: Under Limit]
    request_count < max_requests
    is_allowed() → True

    ↓ user makes request

[State: Approaching Limit]
    request_count == max_requests - 1
    is_allowed() → True (last allowed)

    ↓ user makes another request

[State: Over Limit]
    request_count >= max_requests
    is_allowed() → False

    ↓ time passes, window slides

[State: Under Limit]
    old requests removed
    request_count < max_requests
    is_allowed() → True
```

---

## Performance Considerations

### 1. app_id 解析性能

**优化措施**:
- 优先级检查从高到低,短路求值
- 栈操作 O(1) 时间复杂度
- 日志记录使用 lazy formatting

**预期性能**:
- _resolve_app_id() < 1μs (无异常路径)
- use_app() 上下文进入/退出 < 5μs

### 2. RateLimiter 性能

**优化措施**:
- 使用 dict 存储,查找 O(1)
- 时间戳列表惰性清理 (仅在 is_allowed() 时)
- 避免全局锁,使用用户级隔离

**预期性能**:
- is_allowed() < 10μs (典型场景)
- record_request() < 5μs

**扩展性**:
- 当前内存实现支持 10K+ 用户
- Redis 实现支持 100K+ 用户 (生产环境扩展)

### 3. ScheduledTask 调度性能

**优化措施**:
- 使用 APScheduler 的高效调度器
- 任务执行异步化,不阻塞调度线程
- 错误不传播,保持调度器稳定

**预期性能**:
- 任务调度延迟 < 1s
- 支持 100+ 并发任务

---

## Migration Strategy

### 从现有代码迁移到新数据模型

**阶段 1: 向后兼容 (T+0)**
- 保留所有现有 API 签名
- app_id 参数设为可选,不移除
- 现有测试 100% 通过

**阶段 2: 新 API 引入 (T+1)**
- BaseServiceClient 基类就位
- 各客户端继承 BaseServiceClient
- 新测试覆盖新 API

**阶段 3: 文档更新 (T+2)**
- 示例代码更新为新 API
- 标记旧 API 为"不推荐但支持"
- 提供迁移指南

**阶段 4: 长期支持 (T+3+)**
- 新代码使用新 API
- 现有代码无需强制迁移
- 定期审查旧 API 使用情况

---

## Testing Strategy

### 1. BaseServiceClient 测试

**单元测试**:
- test_resolve_app_id_priority: 验证 5 层优先级
- test_use_app_nested: 验证嵌套上下文
- test_use_app_exception_handling: 验证异常处理
- test_get_current_app_id_no_exception: 验证不抛出异常
- test_list_available_apps: 验证应用列表

**集成测试**:
- test_app_switching_messaging_client: 验证消息客户端应用切换
- test_app_switching_contact_client: 验证通讯录客户端应用切换
- test_concurrent_clients_isolation: 验证多客户端隔离

### 2. RateLimiter 测试

**单元测试**:
- test_rate_limiter_allow: 验证允许请求
- test_rate_limiter_block: 验证拒绝请求
- test_rate_limiter_window_slide: 验证滑动窗口
- test_rate_limiter_boundary: 验证边界条件

**性能测试**:
- test_rate_limiter_throughput: 验证 10K+ 请求/秒吞吐量

### 3. ScheduledTask 测试

**单元测试**:
- test_task_execute: 验证任务执行
- test_task_exception_handling: 验证异常处理
- test_task_enabled_disabled: 验证启用/禁用

**集成测试**:
- test_task_scheduler_integration: 验证 APScheduler 集成

---

**Data Model Status**: ✅ Complete
**Last Updated**: 2026-01-21
