# Feature Specification: 代码重构与最终产品优化

**Feature Branch**: `003-code-refactor-optimization`
**Created**: 2026-01-21
**Status**: Draft
**Input**: 基于 @specs/pending-tasks-checklist.md 我们需要完成一个最终产品的工作。此外还需要做好计划：1. 代码重构的问题,credentials 中已经有 app id 等应用信息,还有需要在每个服务等任务调用中显示传入 app_id 之类的信息吗？等等相关的问题,你可以先看看代码在整理出一个重构和优化方案。2. 在一个新分支 003 上处理以上的问题

## 概述

本规范旨在完成 LarkService 项目的最终产品交付,包括代码重构、架构优化和待完成任务的收尾工作。当前项目已完成两个主要规范(001-lark-service-core 和 002-websocket-user-auth),现需要通过系统性重构和优化,使项目达到生产级交付标准。

## 现状分析

### 当前架构模式

**CredentialPool 设计**:
- CredentialPool 持有 ApplicationManager,可访问所有应用配置信息(app_id, app_secret)
- CredentialPool 内部缓存 SDK 客户端(`sdk_clients: dict[app_id, lark.Client]`)
- 每次 API 调用时,服务客户端需要显式传递 app_id 参数

**服务客户端模式**:
```python
# 现有模式
class MessagingClient:
    def __init__(self, credential_pool: CredentialPool):
        self.credential_pool = credential_pool

    def send_text_message(self, app_id: str, receiver_id: str, text: str):
        client = self.credential_pool._get_sdk_client(app_id)
        # 使用 client 发送消息
```

**问题识别**:

1. **app_id 重复传递**: 每次 API 调用都需要传递 app_id,但 CredentialPool 已经知道所有可用的 app_id
2. **默认应用场景未考虑**: 大多数应用场景只使用单一 app_id,但仍需每次显式传递
3. **多应用场景支持不足**: 虽然架构支持多应用,但实际使用不够优雅
4. **职责划分不清晰**: CredentialPool 既管理凭证,又暴露 SDK 客户端,服务客户端直接访问底层 SDK

### 待完成任务汇总

**001 规范 P1/P2 任务** (来自 pending-tasks-checklist.md):
- [ ] T078: 优化 Dockerfile (多阶段构建)
- [ ] T079: 创建生产环境 docker-compose.yml
- [ ] T080: 完善 GitHub Actions CI/CD
- [ ] T084: 创建完整 CHANGELOG.md

**002 规范 P1/P2 任务**:
- [ ] T055: 添加 API 限流 (5 requests/minute/user)
- [ ] T072: 实现 aPaaS 客户端重试逻辑
- [ ] T073: 添加用户信息同步定时任务
- [ ] T074: 实现 Token 过期 UX
- [ ] T079: 集成测试 Token 刷新
- [ ] T083: 真实飞书账号手动测试

## User Scenarios & Testing

### User Story 1 - 简化单应用使用场景 (Priority: P1)

**场景描述**: 对于只使用单一飞书应用的开发者(90%的使用场景),应该能够在初始化时指定默认 app_id,后续 API 调用无需重复传递。

**Why this priority**: 这是最常见的使用场景,简化后可显著提升开发体验,减少 90% 的 app_id 参数传递。

**Independent Test**: 初始化服务客户端时指定 app_id,发送消息时无需再次传递 app_id,系统自动使用默认值。

**Acceptance Scenarios**:

1. **Given** 开发者只有一个飞书应用, **When** 初始化 MessagingClient 时指定 app_id, **Then** 发送消息时无需再传递 app_id
2. **Given** 系统配置了默认 app_id, **When** 未显式指定 app_id, **Then** 自动使用默认 app_id
3. **Given** 开发者显式传递 app_id, **When** 调用 API 方法, **Then** 使用显式传递的 app_id(覆盖默认值)

---

### User Story 2 - 优雅支持多应用场景 (Priority: P1)

**场景描述**: 对于需要管理多个飞书应用的企业用户(10%的场景),应该能够灵活切换应用上下文,或为特定请求指定应用。

**Why this priority**: 多应用支持是架构核心优势,需要保持灵活性,同时不牺牲单应用场景的简洁性。

**Independent Test**: 创建多个应用上下文的服务客户端,或在单个客户端中切换应用,验证 Token 隔离和 API 调用正确性。

**Acceptance Scenarios**:

1. **Given** 系统配置了多个应用, **When** 为不同应用创建独立客户端实例, **Then** 每个客户端使用各自的 app_id 和 Token
2. **Given** 单个客户端实例, **When** 调用 API 时显式传递不同 app_id, **Then** 系统自动切换应用上下文
3. **Given** 多个应用并发调用, **When** Token 需要刷新, **Then** 不同应用的 Token 刷新互不干扰
4. **Given** 开发者需要确认当前应用, **When** 调用 get_current_app_id(), **Then** 返回当前使用的 app_id 或 None
5. **Given** 开发者需要查看可用应用, **When** 调用 list_available_apps(), **Then** 返回所有已配置的活跃 app_id 列表
6. **Given** 单客户端实例需要频繁切换应用, **When** 使用 use_app() 上下文管理器, **Then** 在上下文内自动使用指定应用,退出后恢复原应用
7. **Given** 多应用场景推荐实践, **When** 使用 CredentialPool.create_messaging_client(app_id), **Then** 创建绑定到独立应用的客户端实例

---

### User Story 3 - 完成生产部署配置 (Priority: P1)

**场景描述**: DevOps 工程师需要将 LarkService 部署到生产环境,需要生产级的 Docker 配置、CI/CD 流程和监控告警。

**Why this priority**: 这是 001 和 002 规范的收尾工作,阻塞生产部署。

**Independent Test**: 使用生产 docker-compose 部署服务,运行健康检查,验证 CI/CD 流程完整性。

**Acceptance Scenarios**:

1. **Given** 生产 docker-compose.yml 配置, **When** 执行 docker-compose up, **Then** 所有服务正常启动并通过健康检查
2. **Given** GitHub Actions CI/CD 配置, **When** 推送代码到主分支, **Then** 自动执行 lint/test/build/deploy 流程
3. **Given** 生产环境运行, **When** 服务异常, **Then** 监控系统触发告警并记录详细日志

---

### User Story 4 - 实现 API 限流和重试机制 (Priority: P2)

**场景描述**: 系统需要防止 API 滥用,并在遇到临时故障时自动重试。

**Why this priority**: 生产环境必备的稳定性和安全性保障。

**Independent Test**: 快速连续调用 API 触发限流,或模拟网络故障验证自动重试。

**Acceptance Scenarios**:

1. **Given** 用户授权请求限流规则(5 requests/minute/user), **When** 用户超过限制, **Then** 返回 429 错误并提示稍后重试
2. **Given** aPaaS API 调用返回 401, **When** 系统检测到 Token 过期, **Then** 自动刷新 Token 并重试请求
3. **Given** API 调用遇到临时网络错误, **When** 重试策略生效, **Then** 最多重试 3 次,使用指数退避

---

### User Story 5 - 完善监控和运维能力 (Priority: P2)

**场景描述**: 运维团队需要完整的日志、监控指标和故障排查工具。

**Why this priority**: 保障生产环境可观测性和可维护性。

**Independent Test**: 查看 Grafana 仪表板,触发告警规则,使用健康检查工具验证服务状态。

**Acceptance Scenarios**:

1. **Given** 生产环境运行, **When** 查看 Grafana 仪表板, **Then** 显示实时性能指标(QPS, 响应时间, 错误率)
2. **Given** Token 即将过期, **When** 监控系统检测, **Then** 自动刷新并记录刷新事件
3. **Given** 系统异常, **When** 运维人员使用健康检查工具, **Then** 快速定位故障组件

---

### User Story 6 - Token 生命周期 UX 优化 (Priority: P3)

**场景描述**: 当用户的 Token 过期时,系统应该主动引导用户重新授权,而不是返回难以理解的错误。

**Why this priority**: 提升用户体验,但不阻塞核心功能。

**Independent Test**: 模拟 Token 过期场景,验证系统自动发送友好的授权卡片。

**Acceptance Scenarios**:

1. **Given** 用户 Token 已过期, **When** 系统检测到过期, **Then** 自动发送新的授权卡片,附带友好提示
2. **Given** 授权卡片发送成功, **When** 用户点击授权, **Then** 流程与首次授权一致
3. **Given** 用户长时间未响应, **When** 系统再次需要 Token, **Then** 不重复发送授权卡片(防骚扰)

---

### Edge Cases

- **app_id 未配置**: 当调用 API 时既未指定默认 app_id,也未显式传递 app_id → 抛出 ConfigError,提供详细的修复建议和可用应用列表
- **app_id 不存在**: 传递的 app_id 在数据库中不存在 → 抛出 AuthenticationError 并列出可用应用
- **多应用并发 Token 刷新**: 同时刷新多个应用的 Token 时 → 锁机制正确隔离,不互相阻塞
- **应用切换竞态条件**: 多线程同时调用同一客户端实例切换应用 → **方案 B**: 明确文档说明不支持并发切换,推荐为每个应用创建独立客户端实例(避免线程本地存储的复杂性)
- **嵌套上下文管理器**: use_app() 嵌套使用 → 内层覆盖外层,退出内层后正确恢复外层 app_id
- **限流边界**: 用户在限流窗口边界发起请求 → 计数准确,不出现误判
- **Docker 资源不足**: 容器内存或 CPU 不足 → 健康检查失败,触发重启或告警
- **数据库连接池耗尽**: 并发请求超过连接池上限 → 排队等待或快速失败,记录错误日志
- **Token 刷新失败**: 飞书 API 不可用导致刷新失败 → 使用缓存 Token 继续服务(如未过期),记录告警
- **app_id 解析失败的错误提示**: 错误消息必须包含当前尝试的 app_id、可用 app_id 列表、三种配置方式的示例代码

## Requirements

### Functional Requirements

#### 代码重构

- **FR-001**: CredentialPool MUST 支持设置默认 app_id,所有服务客户端可继承此默认值
- **FR-002**: 服务客户端(MessagingClient, ContactClient, CloudDocClient 等)MUST 支持在初始化时指定 app_id,作为该实例的默认 app_id
- **FR-003**: API 方法的 app_id 参数 MUST 变为可选参数,优先级: 方法参数 > 客户端默认值 > CredentialPool 默认值
- **FR-004**: 当无法确定 app_id 时,系统 MUST 抛出 ConfigError 异常,并提供清晰的错误消息和修复建议
- **FR-005**: ApplicationManager MUST 提供 get_default_app_id() 方法,返回配置中的默认应用或第一个活跃应用
- **FR-006**: 重构后的 API MUST 保持向后兼容,现有代码无需修改即可运行
- **FR-030**: 所有服务客户端 MUST 提供 get_current_app_id() 方法,返回当前使用的 app_id(无法确定时返回 None,不抛出异常)
- **FR-031**: 所有服务客户端 MUST 提供 list_available_apps() 方法,返回所有已配置的活跃应用列表
- **FR-032**: 所有服务客户端 MUST 在日志中记录当前使用的 app_id,便于调试和故障排查
- **FR-033**: CredentialPool MUST 提供工厂方法 create_messaging_client(app_id), create_contact_client(app_id) 等,用于创建绑定到特定应用的客户端实例(推荐用于多应用场景)
- **FR-034**: 服务客户端 SHOULD 支持 use_app(app_id) 上下文管理器,用于临时切换应用,退出上下文后自动恢复原 app_id
- **FR-035**: 当 app_id 解析失败时,错误消息 MUST 包含: 1) 当前尝试使用的 app_id(如果有), 2) 可用的 app_id 列表, 3) 三种配置方式的示例代码, 4) 明确的修复建议

#### 生产部署配置

- **FR-007**: Dockerfile MUST 使用多阶段构建,最终镜像大小 < 500MB
- **FR-008**: Dockerfile MUST 包含健康检查端点,支持 Docker 和 Kubernetes 健康探测
- **FR-009**: docker-compose.prod.yml MUST 包含生产级配置: 持久化卷、资源限制、重启策略、日志驱动
- **FR-010**: GitHub Actions CI/CD MUST 包含完整流程: lint → type-check → unit-test → integration-test → build → push
- **FR-011**: GitHub Actions MUST 支持多环境部署(dev, staging, prod),使用不同的环境变量
- **FR-012**: CHANGELOG.md MUST 完整记录 v0.1.0(001规范)和 v0.2.0(002规范)的功能清单和已知限制

#### API 限流和重试

- **FR-013**: AuthSessionManager MUST 实现用户授权请求限流: 5 requests/minute/user
- **FR-014**: 限流器 MUST 使用滑动窗口算法,避免边界突刺问题
- **FR-015**: aPaaSClient MUST 实现 _call_apaas_api_with_retry() 方法,处理 401 错误时自动刷新 Token 并重试
- **FR-016**: Token 刷新重试 MUST 最多尝试 3 次,使用指数退避(1s, 2s, 4s)
- **FR-017**: 限流和重试的日志 MUST 记录详细上下文(user_id, app_id, request_id)

#### 监控和运维

- **FR-018**: MUST 添加定时任务: sync_user_info_batch,每日凌晨 2 点执行,同步用户信息
- **FR-019**: 定时任务 MUST 使用 APScheduler 或系统 cron,支持配置化调度策略
- **FR-020**: Prometheus 指标 MUST 新增: auth_rate_limit_triggered_total, token_refresh_retry_total
- **FR-021**: Grafana 仪表板 MUST 新增面板: API 限流趋势, Token 刷新成功率
- **FR-022**: 健康检查工具 MUST 支持命令行调用,输出格式: JSON / 文本 / 状态码

#### Token 生命周期 UX

- **FR-023**: AuthSessionManager MUST 检测 Token 即将过期(< 10% 生命周期剩余)
- **FR-024**: Token 过期时,CardAuthHandler MUST 自动发送新的授权卡片,附带友好消息
- **FR-025**: 授权卡片 MUST 包含过期提示: "您的授权已过期,请重新授权以继续使用"
- **FR-026**: 系统 MUST 防止重复发送授权卡片(同一用户 1 小时内最多 1 次)

#### 测试完整性

- **FR-027**: 集成测试 MUST 覆盖 Token 刷新场景: 模拟 401 错误,验证自动刷新和重试
- **FR-028**: 手动测试指南 MUST 包含真实飞书账号测试步骤,至少完成 1 次端到端验证
- **FR-029**: 所有新增代码 MUST 包含单元测试,覆盖率 ≥ 85%

### Key Entities

#### ApplicationContext (新增概念实体)

表示应用上下文,封装 app_id 及其相关配置。

**属性**:
- app_id: 应用唯一标识符
- is_default: 是否为默认应用
- sdk_client: 对应的 Lark SDK 客户端(懒加载)

**关系**:
- CredentialPool 持有多个 ApplicationContext
- 服务客户端绑定到单个 ApplicationContext

#### BaseServiceClient (新增基类)

所有服务客户端的抽象基类,提供统一的 app_id 管理能力。

**属性**:
- credential_pool: CredentialPool 实例
- _default_app_id: 客户端级默认 app_id(可选)
- _context_app_id: 上下文管理器设置的临时 app_id(可选)

**方法**:
- _resolve_app_id(app_id: str | None) -> str: 解析 app_id,优先级: 方法参数 > 上下文 > 客户端默认 > Pool 默认
- get_current_app_id() -> str | None: 获取当前使用的 app_id(不抛出异常)
- list_available_apps() -> list[str]: 列出所有可用的应用
- use_app(app_id: str): 上下文管理器,临时切换应用

**app_id 解析优先级**:
1. **方法参数**: 显式传递的 app_id (最高优先级)
2. **上下文管理器**: use_app() 设置的临时 app_id
3. **客户端默认值**: 初始化时指定的 app_id
4. **CredentialPool 默认值**: Pool 级别的默认 app_id
5. **无法确定**: 抛出 ConfigError 并提供详细的修复建议

#### RateLimiter (新增功能实体)

用户请求限流器。

**属性**:
- window_size: 时间窗口大小(秒)
- max_requests: 窗口内最大请求数
- request_timestamps: 用户请求时间戳记录

**方法**:
- is_allowed(user_id: str) -> bool: 检查是否允许请求
- record_request(user_id: str): 记录请求时间戳

#### ScheduledTask (新增功能实体)

定时任务配置。

**属性**:
- task_name: 任务名称
- schedule: cron 表达式或调度策略
- handler: 任务处理函数
- enabled: 是否启用

## Success Criteria

### Measurable Outcomes

#### 代码质量

- **SC-001**: 服务客户端单应用场景的代码行数减少 30%(减少 app_id 参数传递)
- **SC-002**: 多应用场景的代码可读性提升,无需手动管理 SDK 客户端
- **SC-003**: 所有重构代码通过现有单元测试和集成测试,无回归问题
- **SC-004**: 类型检查(mypy)和代码风格(ruff)检查 100% 通过

#### 生产就绪度

- **SC-005**: Docker 镜像大小从当前 X MB 优化到 < 500MB
- **SC-006**: 生产环境 docker-compose up 启动时间 < 30 秒,所有服务健康检查通过
- **SC-007**: GitHub Actions CI/CD 流程完整运行时间 < 10 分钟
- **SC-008**: CHANGELOG.md 完整记录所有功能,开发者可快速了解版本差异

#### 稳定性

- **SC-009**: API 限流器准确拦截超限请求,误判率 < 1%
- **SC-010**: Token 刷新重试机制成功率 ≥ 98%(在飞书 API 可用的情况下)
- **SC-011**: 定时任务按预期调度,执行失败时记录告警日志

#### 可观测性

- **SC-012**: Grafana 仪表板实时展示关键指标,数据延迟 < 10 秒
- **SC-013**: 限流和 Token 刷新事件 100% 记录到日志和指标
- **SC-014**: 健康检查工具 3 秒内返回结果,准确反映服务状态

#### 用户体验

- **SC-015**: Token 过期时,用户在 10 秒内收到友好的重新授权卡片
- **SC-016**: 授权卡片包含清晰的过期提示和操作指引
- **SC-017**: 重复授权请求防护生效,用户 1 小时内最多收到 1 次卡片

#### 测试完整性

- **SC-018**: 新增集成测试覆盖 Token 刷新场景,成功通过
- **SC-019**: 真实飞书账号手动测试至少完成 1 次,端到端流程验证通过
- **SC-020**: 整体测试覆盖率保持 ≥ 85%,核心模块 ≥ 90%

#### 应用管理能力

- **SC-021**: 开发者可通过 get_current_app_id() 在任何时候确认当前使用的应用
- **SC-022**: 错误消息中 100% 包含当前 app_id 信息(如果有)和可用 app_id 列表,帮助快速定位问题
- **SC-023**: 多应用切换场景的示例代码清晰易懂,开发者 5 分钟内理解最佳实践
- **SC-024**: use_app() 上下文管理器正确处理嵌套场景,退出后自动恢复原 app_id
- **SC-025**: 工厂方法创建的客户端实例完全隔离,不会互相影响

## API Design Examples

本章节提供详细的 API 设计示例,说明如何实现应用管理和切换能力。

### 单应用场景 (90% 使用场景)

```python
# 方式 1: 客户端级默认 app_id (推荐)
client = MessagingClient(credential_pool, app_id="cli_xxx")
client.send_text_message(receiver_id="ou_yyy", text="Hello")  # 自动使用 cli_xxx
client.send_image_message(receiver_id="ou_yyy", image_path="img.png")  # 自动使用 cli_xxx

# 方式 2: CredentialPool 级默认 app_id
credential_pool.set_default_app_id("cli_xxx")
client = MessagingClient(credential_pool)
client.send_text_message(receiver_id="ou_yyy", text="Hello")  # 自动使用 cli_xxx

# 方式 3: 只有一个应用时,自动作为默认应用
# 假设数据库中只配置了一个应用 cli_xxx
client = MessagingClient(credential_pool)
client.send_text_message(receiver_id="ou_yyy", text="Hello")  # 自动使用唯一的应用
```

### 多应用场景 (10% 使用场景)

```python
# 推荐方式 1: 工厂方法创建独立客户端 (最清晰)
app1_client = credential_pool.create_messaging_client(app_id="app1")
app2_client = credential_pool.create_messaging_client(app_id="app2")

app1_client.send_text_message(receiver_id="ou_yyy", text="From App1")  # 使用 app1
app2_client.send_text_message(receiver_id="ou_yyy", text="From App2")  # 使用 app2

# 方式 2: 上下文管理器临时切换 (推荐用于偶尔切换)
client = MessagingClient(credential_pool, app_id="app1")  # 默认 app1

with client.use_app("app2"):
    # 在这个上下文中使用 app2
    client.send_text_message(receiver_id="ou_yyy", text="From App2")
    client.send_image_message(receiver_id="ou_yyy", image_path="img.png")

# 退出上下文后自动恢复 app1
client.send_text_message(receiver_id="ou_yyy", text="From App1 again")

# 方式 3: 方法参数显式传递 (不推荐频繁切换时使用)
client = MessagingClient(credential_pool)
client.send_text_message(app_id="app1", receiver_id="ou_yyy", text="From App1")
client.send_text_message(app_id="app2", receiver_id="ou_yyy", text="From App2")
```

### 嵌套上下文管理器

```python
client = MessagingClient(credential_pool, app_id="app1")

with client.use_app("app2"):
    print(client.get_current_app_id())  # 输出: app2

    with client.use_app("app3"):
        print(client.get_current_app_id())  # 输出: app3

    # 退出内层上下文,恢复到 app2
    print(client.get_current_app_id())  # 输出: app2

# 退出所有上下文,恢复到 app1
print(client.get_current_app_id())  # 输出: app1
```

### 并发场景的最佳实践

**重要**: `use_app()` 上下文管理器**不支持**多线程并发使用同一客户端实例。如需在并发环境下使用多个应用,请遵循以下最佳实践:

```python
from concurrent.futures import ThreadPoolExecutor

# ❌ 错误: 多线程共享客户端实例并切换应用 (不支持!)
client = MessagingClient(credential_pool)

def send_in_thread(app_id, message):
    with client.use_app(app_id):  # ⚠️ 线程不安全!
        client.send_text_message(receiver_id="ou_xxx", text=message)

with ThreadPoolExecutor() as executor:
    executor.submit(send_in_thread, "app1", "msg1")
    executor.submit(send_in_thread, "app2", "msg2")


# ✅ 正确: 为每个应用创建独立客户端实例
def send_with_dedicated_client(app_id, message):
    # 每个线程创建自己的客户端实例
    client = credential_pool.create_messaging_client(app_id)
    client.send_text_message(receiver_id="ou_xxx", text=message)

with ThreadPoolExecutor() as executor:
    executor.submit(send_with_dedicated_client, "app1", "msg1")
    executor.submit(send_with_dedicated_client, "app2", "msg2")


# ✅ 备选: 在方法级别显式传递 app_id (无需切换)
client = MessagingClient(credential_pool)

def send_explicit(app_id, message):
    client.send_text_message(
        app_id=app_id,  # 显式传递,线程安全
        receiver_id="ou_xxx",
        text=message
    )

with ThreadPoolExecutor() as executor:
    executor.submit(send_explicit, "app1", "msg1")
    executor.submit(send_explicit, "app2", "msg2")
```

**设计理由**:
- 单应用场景(预计占 90%)无需考虑并发切换
- 多应用并发场景推荐使用工厂方法或显式参数,避免状态共享
- 避免引入线程本地存储 (threading.local) 的额外复杂性和性能开销

### 调试和确认当前应用

```python
client = MessagingClient(credential_pool, app_id="app1")

# 1. 确认当前使用的应用
current = client.get_current_app_id()
print(f"当前应用: {current}")  # 输出: app1

# 2. 查看所有可用应用
available = client.list_available_apps()
print(f"可用应用: {available}")  # 输出: ['app1', 'app2', 'app3']

# 3. 临时切换并验证
with client.use_app("app2"):
    print(f"临时切换到: {client.get_current_app_id()}")  # 输出: app2

print(f"恢复为: {client.get_current_app_id()}")  # 输出: app1

# 4. 检查特定应用是否可用
if "app3" in client.list_available_apps():
    with client.use_app("app3"):
        client.send_text_message(...)
```

### app_id 解析优先级示例

```python
# 假设配置: Pool 默认 app_id = "default_app"
credential_pool.set_default_app_id("default_app")

# 场景 1: 仅有 Pool 默认值
client = MessagingClient(credential_pool)
client.send_text_message(receiver_id="ou_yyy", text="Hi")
# 使用: default_app (Pool 默认)

# 场景 2: 客户端默认值覆盖 Pool 默认值
client = MessagingClient(credential_pool, app_id="client_app")
client.send_text_message(receiver_id="ou_yyy", text="Hi")
# 使用: client_app (客户端默认)

# 场景 3: 上下文管理器覆盖客户端默认值
client = MessagingClient(credential_pool, app_id="client_app")
with client.use_app("context_app"):
    client.send_text_message(receiver_id="ou_yyy", text="Hi")
# 使用: context_app (上下文管理器)

# 场景 4: 方法参数覆盖所有默认值 (最高优先级)
client = MessagingClient(credential_pool, app_id="client_app")
with client.use_app("context_app"):
    client.send_text_message(app_id="param_app", receiver_id="ou_yyy", text="Hi")
# 使用: param_app (方法参数,最高优先级)
```

### 错误处理示例

```python
# 场景 1: 无法确定 app_id
client = MessagingClient(credential_pool)  # 未设置任何默认值
try:
    client.send_text_message(receiver_id="ou_yyy", text="Hi")
except ConfigError as e:
    # 错误消息示例:
    # Cannot determine app_id. Please specify app_id via:
    # 1. Method parameter: client.send_message(app_id='cli_xxx', ...)
    # 2. Client initialization: MessagingClient(pool, app_id='cli_xxx')
    # 3. CredentialPool default: pool.set_default_app_id('cli_xxx')
    # Available apps: ['app1', 'app2', 'app3']
    print(e)

# 场景 2: app_id 不存在
client = MessagingClient(credential_pool)
try:
    client.send_text_message(app_id="non_existent_app", receiver_id="ou_yyy", text="Hi")
except AuthenticationError as e:
    # 错误消息示例:
    # Application not found: non_existent_app
    # Available apps: ['app1', 'app2', 'app3']
    print(e)
```

### BaseServiceClient 内部实现示例

```python
class BaseServiceClient:
    """所有服务客户端的基类"""

    def __init__(
        self,
        credential_pool: CredentialPool,
        app_id: str | None = None
    ):
        self.credential_pool = credential_pool
        self._default_app_id = app_id
        self._context_app_stack: list[str] = []  # 上下文栈,支持嵌套

    def _resolve_app_id(self, app_id: str | None = None) -> str:
        """解析 app_id,优先级: 参数 > 上下文 > 客户端默认 > Pool 默认"""
        # 1. 方法参数 (最高优先级)
        if app_id is not None:
            logger.debug(f"Using app_id from method parameter: {app_id}")
            return app_id

        # 2. 上下文管理器 (栈顶元素)
        if self._context_app_stack:
            context_app_id = self._context_app_stack[-1]
            logger.debug(f"Using app_id from context manager: {context_app_id}")
            return context_app_id

        # 3. 客户端默认值
        if self._default_app_id is not None:
            logger.debug(f"Using app_id from client default: {self._default_app_id}")
            return self._default_app_id

        # 4. CredentialPool 默认值
        pool_default = self.credential_pool.get_default_app_id()
        if pool_default is not None:
            logger.debug(f"Using app_id from pool default: {pool_default}")
            return pool_default

        # 5. 无法确定 - 抛出清晰错误
        available_apps = self.list_available_apps()
        raise ConfigError(
            "Cannot determine app_id. Please specify app_id via:\n"
            "1. Method parameter: client.send_message(app_id='cli_xxx', ...)\n"
            "2. Client initialization: MessagingClient(pool, app_id='cli_xxx')\n"
            "3. CredentialPool default: pool.set_default_app_id('cli_xxx')\n"
            f"Available apps: {available_apps}"
        )

    def get_current_app_id(self) -> str | None:
        """获取当前使用的 app_id (不抛出异常)"""
        try:
            return self._resolve_app_id()
        except ConfigError:
            return None

    def list_available_apps(self) -> list[str]:
        """列出所有可用的应用"""
        return self.credential_pool.list_app_ids()

    @contextmanager
    def use_app(self, app_id: str):
        """临时切换应用的上下文管理器

        支持嵌套使用,内层覆盖外层,退出内层后自动恢复外层。

        ⚠️ 警告: 此方法不支持多线程并发使用同一客户端实例。
        如需在并发环境下使用多个应用,请:
        - 方案 1: 为每个应用创建独立客户端实例 (推荐)
        - 方案 2: 在方法级别显式传递 app_id 参数

        详见规范文档中的"并发场景的最佳实践"章节。
        """
        # 验证 app_id 存在
        if app_id not in self.list_available_apps():
            raise AuthenticationError(
                f"Application not found: {app_id}",
                details={"available_apps": self.list_available_apps()}
            )

        # 压栈
        self._context_app_stack.append(app_id)
        logger.debug(f"Switched to app_id: {app_id} (stack depth: {len(self._context_app_stack)})")

        try:
            yield
        finally:
            # 出栈
            popped = self._context_app_stack.pop()
            logger.debug(f"Restored from app_id: {popped} (stack depth: {len(self._context_app_stack)})")
```

### CredentialPool 工厂方法实现示例

```python
class CredentialPool:
    def __init__(self, config, app_manager, token_storage, lock_dir):
        self.config = config
        self.app_manager = app_manager
        self.token_storage = token_storage
        self._default_app_id: str | None = None
        # ... 其他初始化

    def get_default_app_id(self) -> str | None:
        """获取默认 app_id"""
        # 1. 如果显式设置了默认值,使用它
        if self._default_app_id is not None:
            return self._default_app_id

        # 2. 委托给 ApplicationManager 自动选择
        return self.app_manager.get_default_app_id()

    def set_default_app_id(self, app_id: str) -> None:
        """设置默认 app_id"""
        # 验证 app_id 存在
        app = self.app_manager.get_application(app_id)
        if not app:
            available = self.list_app_ids()
            raise ConfigError(
                f"Application not found: {app_id}\n"
                f"Available apps: {available}"
            )

        if not app.is_active():
            raise ConfigError(
                f"Application is not active: {app_id}\n"
                f"Status: {app.status}"
            )

        self._default_app_id = app_id
        logger.info(f"Default app_id set to: {app_id}")

    def list_app_ids(self) -> list[str]:
        """列出所有可用的 app_id"""
        apps = self.app_manager.list_applications(status="active")
        return [app.app_id for app in apps]

    # 工厂方法
    def create_messaging_client(self, app_id: str | None = None) -> MessagingClient:
        """工厂方法: 创建绑定到特定应用的 MessagingClient"""
        return MessagingClient(self, app_id=app_id)

    def create_contact_client(self, app_id: str | None = None) -> ContactClient:
        """工厂方法: 创建绑定到特定应用的 ContactClient"""
        return ContactClient(self, app_id=app_id)

    def create_clouddoc_client(self, app_id: str | None = None) -> DocClient:
        """工厂方法: 创建绑定到特定应用的 DocClient"""
        return DocClient(self, app_id=app_id)
```

### ApplicationManager 默认应用逻辑示例

```python
class ApplicationManager:
    def get_default_app_id(self) -> str | None:
        """获取默认 app_id

        策略:
        1. 如果只有一个活跃应用,自动返回
        2. 如果有多个活跃应用,返回第一个 (按创建时间排序)
        3. 如果没有活跃应用,返回 None
        """
        apps = self.list_applications(status="active")

        if not apps:
            logger.warning("No active applications found")
            return None

        if len(apps) == 1:
            logger.debug(f"Single active app found: {apps[0].app_id}")
            return apps[0].app_id

        # 多个应用时,返回第一个 (按创建时间)
        default = apps[0].app_id
        logger.debug(
            f"Multiple active apps found, using first: {default}. "
            f"Available: {[app.app_id for app in apps]}"
        )
        return default
```

## Assumptions

1. **默认应用选择策略**: 如果配置中有多个应用,默认选择第一个 is_active=true 的应用;如果只有一个应用,自动作为默认应用
2. **线程安全**: `use_app()` 上下文管理器不支持多线程并发切换应用,并发场景推荐为每个应用创建独立客户端实例或使用方法级别的显式 app_id 参数
3. **限流存储**: 使用内存存储请求时间戳,服务重启后限流计数重置(生产环境可扩展为 Redis)
4. **定时任务可靠性**: 单实例部署时使用 APScheduler,多实例部署时需要外部调度器(如 Kubernetes CronJob)
5. **Docker 基础镜像**: 使用 python:3.12-slim 作为基础镜像,平衡大小和功能
6. **CI/CD 触发器**: GitHub Actions 在 push 到 main/master 分支或创建 Pull Request 时触发
7. **健康检查端点**: 默认使用 HTTP GET /health,返回 JSON 格式状态信息
8. **Token 过期阈值**: 定义"即将过期"为剩余生命周期 < 10%,或绝对时间 < 1 小时
9. **授权卡片防重复**: 使用内存缓存记录最近发送时间,1 小时内同一用户最多 1 次

## Dependencies

1. **外部服务**: 飞书开放平台 API (Token 刷新、用户信息同步依赖)
2. **基础设施**: PostgreSQL(Token 存储), RabbitMQ(事件队列, 可选), Redis(限流存储, 可选)
3. **监控系统**: Prometheus + Grafana (指标收集和可视化)
4. **CI/CD 平台**: GitHub Actions (自动化测试和部署)
5. **Python 库**: APScheduler(定时任务), python-dotenv(环境变量), ruff/mypy(代码质量)

## Out of Scope (本规范不包含)

1. **性能优化**: 不包括大规模性能测试(T076, 100并发/秒),可延后到后续版本
2. **边缘案例全覆盖**: 不包括 spec.md 中 29 个边缘案例的逐一验证(T077),当前重点是核心场景
3. **多实例部署**: 不包括分布式锁、分布式限流等多实例高可用方案,当前假设单实例部署
4. **WebSocket 重构**: 002 规范的 WebSocket 客户端暂不重构,保持现有设计
5. **数据库迁移工具**: 不包括数据库版本管理、回滚自动化等高级功能
6. **监控告警集成**: 不包括与 PagerDuty、钉钉等第三方告警平台的集成
7. **多云部署**: 不包括 AWS、阿里云等多云环境的部署配置

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| 代码重构引入回归问题 | 高 | 中 | 运行完整的单元测试和集成测试套件,增量重构,每次只改一个模块 |
| Docker 镜像优化后缺少依赖 | 中 | 低 | 在 CI 中测试镜像,运行健康检查和集成测试 |
| 限流算法误判 | 中 | 低 | 使用成熟的滑动窗口算法,编写单元测试覆盖边界条件 |
| Token 刷新重试失败 | 中 | 低 | 记录详细日志,触发告警,使用指数退避避免雪崩 |
| 定时任务调度失败 | 低 | 低 | 使用成熟的 APScheduler 库,记录执行日志,设置监控告警 |
| 真实飞书账号测试受限 | 低 | 中 | 提前申请测试账号和应用,准备详细的手动测试指南 |
| CI/CD 流程过长影响开发效率 | 低 | 中 | 优化测试执行时间,使用缓存加速构建,支持跳过非关键步骤 |

## Open Questions

_本规范无开放问题,所有关键决策已明确(包括线程安全策略已选择方案 B)。_
