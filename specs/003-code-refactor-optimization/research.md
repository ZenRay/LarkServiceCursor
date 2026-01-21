# 技术调研: 代码重构与优化方案

**Feature**: 003-code-refactor-optimization
**Date**: 2026-01-21
**Phase**: Phase 0 - Technical Research

## 调研目标

基于 001 和 002 规范的待办任务清单,解决以下核心问题:
1. **代码重构**: 优化 `app_id` 管理,减少冗余传参
2. **应用切换**: 设计灵活的多应用场景支持
3. **生产就绪**: 完成 Docker、CI/CD、监控等基础设施
4. **稳定性增强**: 实现 API 限流、重试、Token UX 优化

---

## 📋 目录

1. [调研背景](#调研背景)
2. [问题定义](#问题定义)
3. [代码分析](#代码分析)
4. [重构方案设计](#重构方案设计)
5. [应用切换机制](#应用切换机制)
6. [线程安全策略](#线程安全策略)
7. [最终决策总结](#最终决策总结)

---

## 调研背景

### 现状分析

**001 和 002 规范待办任务**:
- P1 任务: 8 个 (生产环境部署、API 限流、Token UX、真实测试)
- P2 任务: 5 个 (重试逻辑、定时任务、集成测试优化)
- P3 任务: 12 个 (性能测试、边缘案例验证、文档完善)

### 核心问题

**问题 1**: `app_id` 冗余传参
```python
# 当前代码模式 (冗余)
credential_pool = CredentialPool(...)  # 已有 app_id 信息
client = MessagingClient(credential_pool)
client.send_text_message(
    app_id="cli_xxx",  # ❌ 每次都要传
    receiver_id="ou_yyy",
    text="Hello"
)
```

**问题 2**: 缺乏清晰的应用切换机制
- 多应用场景下如何优雅切换?
- 如何确认当前使用的是哪个应用?
- 如何避免应用混淆?

**问题 3**: 生产环境基础设施未完成
- Docker 镜像未优化 (多阶段构建)
- CI/CD 流程不完整
- 监控和告警缺失

---

## 问题定义

### 核心需求

从用户提出的问题中提炼出 5 个核心需求:

| 需求编号 | 需求描述 | 优先级 |
|---------|---------|--------|
| REQ-1 | 简化 `app_id` 传参,支持默认值和继承 | P0 |
| REQ-2 | 提供灵活的应用切换机制 | P0 |
| REQ-3 | 提供应用确认和调试能力 | P0 |
| REQ-4 | 完成生产环境基础设施 | P1 |
| REQ-5 | 增强系统稳定性(限流/重试/监控) | P1 |

### 设计目标

1. **向后兼容**: 现有代码无需修改即可运行
2. **简洁优先**: 单应用场景 (90%) 的使用体验最简单
3. **灵活扩展**: 多应用场景有清晰的最佳实践
4. **生产就绪**: 完整的 Docker、CI/CD、监控能力

---

## 代码分析

### 当前 `app_id` 使用模式

#### MessagingClient 分析

**文件**: `src/lark_service/messaging/client.py`

**当前实现**:
```python
class MessagingClient:
    def __init__(
        self,
        credential_pool: CredentialPool,
        media_uploader: MediaUploader | None = None,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        self.credential_pool = credential_pool
        # ... 其他初始化

    def _send_message(
        self,
        app_id: str,  # ❌ 必须显式传入
        receiver_id: str,
        msg_type: str,
        content: str | dict[str, Any],
        receive_id_type: str = "open_id",
    ) -> dict[str, Any]:
        client = self.credential_pool._get_sdk_client(app_id)
        # ... 调用飞书 API
```

**问题**:
- ❌ 每个方法都需要 `app_id` 参数
- ❌ 单应用场景下重复传参造成代码冗余
- ❌ 无法在客户端级别设置默认应用

#### ContactClient 分析

**文件**: `src/lark_service/contact/client.py`

**当前实现**: 与 `MessagingClient` 类似,所有方法都要求显式传入 `app_id`

#### CloudDocClient 分析

**文件**: `src/lark_service/clouddoc/bitable/client.py`

**当前实现**: 同样需要显式传入 `app_id` 和 `app_token`

#### CredentialPool 分析

**文件**: `src/lark_service/core/credential_pool.py`

**当前实现**:
```python
class CredentialPool:
    def _get_sdk_client(self, app_id: str) -> lark.Client:
        """根据 app_id 获取 SDK 客户端"""
        # 1. 从 ApplicationManager 获取应用配置
        app = self.app_manager.get_application(app_id)

        # 2. 创建/缓存 SDK 客户端
        client = (
            lark.Client.builder()
            .app_id(app_id)
            .app_secret(app_secret)
            # ...
        )
        return client
```

**观察**:
- ✅ CredentialPool 已经管理所有应用配置
- ✅ ApplicationManager 可以提供默认应用选择逻辑
- ❌ 但没有暴露默认 app_id 的能力

### 问题根源

**核心矛盾**: CredentialPool 已经持有所有应用信息,但服务客户端没有利用这一点,导致 `app_id` 必须在每次调用时显式传递。

---

## 重构方案设计

### 方案概述

**核心思路**: 引入分层的 `app_id` 解析机制,支持在多个层级设置默认值。

### 设计原则

1. **向后兼容**: 保留方法参数,作为最高优先级
2. **默认值继承**: 支持客户端和 Pool 级别的默认值
3. **优先级明确**: 定义清晰的解析优先级
4. **错误友好**: 无法确定时提供详细的修复建议

### app_id 解析优先级

定义 **5 层优先级**:

```
1. 方法参数 (最高)
   ↓
2. 上下文管理器
   ↓
3. 客户端默认值
   ↓
4. CredentialPool 默认值
   ↓
5. 抛出 ConfigError (无法确定)
```

### 关键设计决策

#### 决策 1: 引入 BaseServiceClient 基类

**目的**: 统一所有服务客户端的 `app_id` 管理逻辑

**设计**:
```python
class BaseServiceClient:
    def __init__(
        self,
        credential_pool: CredentialPool,
        app_id: str | None = None,
    ):
        self.credential_pool = credential_pool
        self._client_default_app_id = app_id
        self._context_app_stack: list[str] = []  # 上下文栈

    def _resolve_app_id(self, app_id: str | None = None) -> str:
        """解析 app_id,按优先级选择"""
        # 1. 方法参数
        if app_id is not None:
            return app_id

        # 2. 上下文管理器 (栈顶)
        if self._context_app_stack:
            return self._context_app_stack[-1]

        # 3. 客户端默认值
        if self._client_default_app_id is not None:
            return self._client_default_app_id

        # 4. CredentialPool 默认值
        pool_default = self.credential_pool.get_default_app_id()
        if pool_default is not None:
            return pool_default

        # 5. 无法确定 → 抛出错误
        raise ConfigError("No app_id specified. Please provide...")
```

**优势**:
- ✅ 所有客户端继承统一的逻辑,减少重复代码
- ✅ 优先级逻辑集中管理,易于维护
- ✅ 支持嵌套上下文管理器

#### 决策 2: CredentialPool 支持默认 app_id

**设计**:
```python
class CredentialPool:
    def __init__(self, ...):
        self._default_app_id: str | None = None

    def set_default_app_id(self, app_id: str) -> None:
        """设置默认应用"""
        self._default_app_id = app_id

    def get_default_app_id(self) -> str | None:
        """获取默认 app_id"""
        if self._default_app_id is not None:
            return self._default_app_id

        # 委托给 ApplicationManager 自动选择
        return self.app_manager.get_default_app_id()
```

**ApplicationManager 增强**:
```python
class ApplicationManager:
    def get_default_app_id(self) -> str | None:
        """智能选择默认应用"""
        apps = self.get_active_applications()

        if not apps:
            return None

        # 只有一个应用 → 自动作为默认
        if len(apps) == 1:
            return apps[0].app_id

        # 多个应用 → 返回第一个 (按创建时间)
        return apps[0].app_id
```

#### 决策 3: 方法参数变为可选

**重构前**:
```python
def send_text_message(
    self,
    app_id: str,  # 必需
    receiver_id: str,
    text: str,
) -> dict[str, Any]:
    pass
```

**重构后**:
```python
def send_text_message(
    self,
    receiver_id: str,
    text: str,
    app_id: str | None = None,  # 可选
) -> dict[str, Any]:
    resolved_app_id = self._resolve_app_id(app_id)
    # ... 使用 resolved_app_id
```

**向后兼容性**:
- ✅ 现有代码仍可显式传递 `app_id`
- ✅ 新代码可省略 `app_id` 参数

---

## 应用切换机制

### 4 种切换方式

基于不同场景的需求,设计了 4 种灵活的应用切换方式:

#### 方式 1: 工厂方法 (推荐用于多应用场景)

**实现**:
```python
class CredentialPool:
    def create_messaging_client(self, app_id: str) -> MessagingClient:
        """为指定应用创建独立的客户端实例"""
        return MessagingClient(
            credential_pool=self,
            app_id=app_id
        )
```

**使用场景**:
```python
# 长期运行的多应用服务
app1_client = pool.create_messaging_client("app1")
app2_client = pool.create_messaging_client("app2")

app1_client.send_text_message(...)  # 始终使用 app1
app2_client.send_text_message(...)  # 始终使用 app2
```

**优势**:
- ✅ 完全隔离,不会混淆
- ✅ 线程安全
- ✅ 适合长期运行的多应用场景

#### 方式 2: 上下文管理器 (推荐用于临时切换)

**实现**:
```python
class BaseServiceClient:
    @contextmanager
    def use_app(self, app_id: str):
        """临时切换应用的上下文管理器"""
        # 验证 app_id 存在
        if app_id not in self.list_available_apps():
            raise AuthenticationError(f"Application not found: {app_id}")

        # 压栈
        self._context_app_stack.append(app_id)
        try:
            yield
        finally:
            # 出栈
            self._context_app_stack.pop()
```

**使用场景**:
```python
client = MessagingClient(pool, app_id="app1")

with client.use_app("app2"):
    client.send_text_message(...)  # 临时使用 app2

# 自动恢复到 app1
client.send_text_message(...)
```

**优势**:
- ✅ 明确的作用域
- ✅ 自动恢复
- ✅ 支持嵌套 (内层覆盖外层)

#### 方式 3: 方法参数 (向后兼容)

**使用场景**:
```python
client = MessagingClient(pool)
client.send_text_message(app_id="app1", ...)
client.send_text_message(app_id="app2", ...)
```

**优势**:
- ✅ 向后兼容现有代码
- ✅ 最高优先级
- ⚠️ 频繁切换时代码冗余

#### 方式 4: 客户端默认值 (推荐用于单应用)

**使用场景**:
```python
client = MessagingClient(pool, app_id="app1")
client.send_text_message(...)  # 自动使用 app1
```

**优势**:
- ✅ 最简洁
- ✅ 适合 90% 的单应用场景

### 应用确认和调试

提供 **3 种确认方式**:

#### 1. 查询当前 app_id

```python
class BaseServiceClient:
    def get_current_app_id(self) -> str | None:
        """获取当前使用的 app_id (不抛出异常)"""
        try:
            return self._resolve_app_id()
        except ConfigError:
            return None

# 使用
current = client.get_current_app_id()
print(f"当前应用: {current}")
```

#### 2. 列出所有可用应用

```python
class BaseServiceClient:
    def list_available_apps(self) -> list[str]:
        """列出所有可用的应用"""
        return self.credential_pool.list_app_ids()

# 使用
apps = client.list_available_apps()
print(f"可用应用: {apps}")
```

#### 3. 日志记录

所有 API 调用自动记录使用的 `app_id`:

```python
logger.info(
    f"Sending message using app_id={app_id}, "
    f"receiver={receiver_id}"
)
```

### 错误处理

当无法确定 `app_id` 时,提供详细的错误消息:

```python
raise ConfigError(
    "No app_id specified. Please provide app_id using one of:\n"
    "1. Method parameter: client.send_message(app_id='cli_xxx', ...)\n"
    "2. Client initialization: MessagingClient(pool, app_id='cli_xxx')\n"
    "3. CredentialPool default: pool.set_default_app_id('cli_xxx')\n"
    f"Available apps: {self.list_available_apps()}"
)
```

---

## 线程安全策略

### 问题分析

**背景**: `use_app()` 上下文管理器使用实例变量 `_context_app_stack`,在多线程环境下可能出现竞态条件。

**场景示例**:
```python
client = MessagingClient(pool)

# 线程 1
with client.use_app("app1"):
    client.send_message(...)  # 期望使用 app1

# 线程 2 (同时运行)
with client.use_app("app2"):
    client.send_message(...)  # 期望使用 app2

# ⚠️ 可能导致应用混淆
```

### 方案对比

| 方案 | 描述 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|---------|
| **方案 A** | 使用线程本地存储 (threading.local) | 支持并发切换,对用户透明 | 实现复杂,性能开销,调试困难 | 并发切换频繁的场景 (≤10%) |
| **方案 B** | 文档说明不支持并发切换 | 实现简单,性能好,维护成本低 | 需要用户遵循最佳实践 | 单应用或隔离多应用场景 (≥90%) |

### 最终决策: 方案 B

**选择依据**:
1. **使用频率**: 单应用场景占 90%,无需考虑并发切换
2. **技术复杂度**: 避免引入线程本地存储的额外复杂性
3. **性能考虑**: 避免 threading.local 的性能开销
4. **维护成本**: 更简单的实现,更少的潜在 bug

### 实施细节

#### 1. 更新文档和警告

在 `use_app()` 方法添加明确警告:

```python
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
    # ... 实现
```

#### 2. 并发场景最佳实践

**❌ 错误用法**:
```python
from concurrent.futures import ThreadPoolExecutor

client = MessagingClient(credential_pool)

def send_in_thread(app_id, message):
    with client.use_app(app_id):  # ⚠️ 线程不安全!
        client.send_text_message(receiver_id="ou_xxx", text=message)

with ThreadPoolExecutor() as executor:
    executor.submit(send_in_thread, "app1", "msg1")
    executor.submit(send_in_thread, "app2", "msg2")
```

**✅ 正确用法 1: 独立客户端实例**
```python
def send_with_dedicated_client(app_id, message):
    # 每个线程创建自己的客户端实例
    client = credential_pool.create_messaging_client(app_id)
    client.send_text_message(receiver_id="ou_xxx", text=message)

with ThreadPoolExecutor() as executor:
    executor.submit(send_with_dedicated_client, "app1", "msg1")
    executor.submit(send_with_dedicated_client, "app2", "msg2")
```

**✅ 正确用法 2: 显式参数**
```python
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

#### 3. 假设声明

在规范的 Assumptions 章节添加:

```
2. **线程安全**: `use_app()` 上下文管理器不支持多线程并发切换应用,
   并发场景推荐为每个应用创建独立客户端实例或使用方法级别的显式 app_id 参数
```

### 影响范围

#### 代码实施影响
- ✅ 无需实现线程本地存储,降低实施复杂度
- ✅ `BaseServiceClient` 实现更简单,维护成本更低
- ✅ 减少潜在的线程安全 bug

#### 文档影响
- ✅ 需在用户文档中明确说明不支持并发切换
- ✅ 需提供并发场景的最佳实践示例和教程
- ✅ API 文档中 `use_app()` 方法需添加警告说明

#### 用户体验影响
- ✅ 单应用场景(主流)使用体验不受影响
- ✅ 多应用并发场景有清晰的最佳实践指导
- ⚠️ 需通过文档教育用户正确的并发使用方式

---

## 最终决策总结

### 核心决策

| 决策编号 | 决策内容 | 理由 | 影响 |
|---------|---------|------|------|
| **D-001** | 引入 BaseServiceClient 基类 | 统一 app_id 管理逻辑 | 所有服务客户端需继承此基类 |
| **D-002** | 5 层 app_id 解析优先级 | 兼容性和灵活性平衡 | API 设计核心原则 |
| **D-003** | app_id 参数变为可选 | 简化单应用场景 | 向后兼容,现有代码无需改动 |
| **D-004** | 提供 4 种应用切换方式 | 覆盖所有使用场景 | 增加 API 表面积,需要文档支持 |
| **D-005** | 线程安全采用方案 B | 简单性优先,适应主流场景 | 需明确文档说明并发限制 |

### 规范完整性

#### 功能需求: 35 个

**代码重构 (FR-001 ~ FR-006, FR-030 ~ FR-035)**:
- ✅ app_id 默认值支持 (Pool/客户端)
- ✅ 优先级解析
- ✅ 向后兼容
- ✅ 错误处理
- ✅ 应用查询和切换能力

**生产环境 (FR-007 ~ FR-012)**:
- ✅ Docker 多阶段构建
- ✅ 生产级 docker-compose.yml
- ✅ GitHub Actions CI/CD
- ✅ 健康检查端点

**稳定性增强 (FR-013 ~ FR-026)**:
- ✅ API 限流 (5 requests/minute/user)
- ✅ aPaaS 客户端重试逻辑
- ✅ Prometheus 指标导出
- ✅ Token 过期 UX 优化

**测试完整性 (FR-027 ~ FR-029)**:
- ✅ 向后兼容测试
- ✅ 集成测试 Token 刷新
- ✅ 真实飞书账号手动测试

#### 用户故事: 6 个

**US1**: 简化单应用场景 (4 个验收场景)
**US2**: 优雅支持多应用 (7 个验收场景)
**US3**: 完成生产部署 (5 个验收场景)
**US4**: API 限流/重试 (4 个验收场景)
**US5**: 监控和运维 (5 个验收场景)
**US6**: Token UX 优化 (3 个验收场景)

#### 成功标准: 25 个

**代码质量 (SC-001 ~ SC-007)**:
- 所有测试通过
- Ruff/mypy 无错误
- 测试覆盖率 ≥ 95%
- 示例代码易懂

**生产就绪 (SC-008 ~ SC-012)**:
- Docker 镜像 < 500MB
- 健康检查响应 < 100ms
- CI/CD 完整流程

**稳定性 (SC-013 ~ SC-017)**:
- 限流准确率 100%
- 重试成功率 ≥ 95%
- Token 刷新成功率 ≥ 98%

**可观测性 (SC-018 ~ SC-020)**:
- Prometheus 指标导出
- Grafana 仪表板
- 日志结构化

**用户体验 (SC-021 ~ SC-025)**:
- 可确认当前应用
- 错误消息包含 app_id
- 上下文管理器正确性

### 问题解决确认

| 原始问题 | 解决状态 | 解决方案 |
|---------|---------|---------|
| ❓ credentials 中已有 app_id,还需每次传参吗? | ✅ 完全解决 | app_id 参数变为可选,支持多层默认值 |
| ❓ 如何支持应用切换? | ✅ 完全解决 | 提供 4 种切换方式 + 清晰的优先级 |
| ❓ 如何确认当前使用的 app? | ✅ 完全解决 | 3 种确认方式 (查询/列表/日志) |
| ❓ 如何切换 app? | ✅ 完全解决 | 200+ 行 API 示例 + 最佳实践 |
| ❓ 支持多应用调用? | ✅ 完全解决 | 工厂方法 + 上下文管理器 |
| ❓ 线程安全策略? | ✅ 已明确 | 方案 B: 文档说明 + 并发最佳实践 |

### 后续行动

#### 1. 立即行动 (Phase 0)
- ✅ 规范已完成 (spec.md)
- ✅ 技术调研已完成 (research.md)
- ✅ 质量检查已通过 (requirements.md)

#### 2. 下一阶段 (Phase 1)
- ⬜ 创建技术实施计划 (plan.md)
- ⬜ 创建任务清单 (tasks.md)
- ⬜ 开始增量重构

#### 3. 重点关注
1. **BaseServiceClient 实现**: 核心逻辑,需要详细的单元测试
2. **向后兼容性**: 确保现有代码无需修改
3. **文档完善**: 用户文档、API 文档、并发最佳实践
4. **生产部署**: Docker、CI/CD、监控一次性完成

---

## 附录: 关键代码示例

### BaseServiceClient 完整实现

```python
from abc import ABC
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class BaseServiceClient(ABC):
    """所有服务客户端的基类,提供统一的 app_id 管理"""

    def __init__(
        self,
        credential_pool: CredentialPool,
        app_id: str | None = None,
    ):
        self.credential_pool = credential_pool
        self._client_default_app_id = app_id
        self._context_app_stack: list[str] = []  # 上下文栈,支持嵌套

    def _resolve_app_id(self, app_id: str | None = None) -> str:
        """解析 app_id,优先级: 参数 > 上下文 > 客户端默认 > Pool 默认"""
        # 1. 方法参数 (最高优先级)
        if app_id is not None:
            logger.debug(f"Using app_id from method parameter: {app_id}")
            return app_id

        # 2. 上下文管理器 (栈顶)
        if self._context_app_stack:
            context_app = self._context_app_stack[-1]
            logger.debug(
                f"Using app_id from context (depth {len(self._context_app_stack)}): "
                f"{context_app}"
            )
            return context_app

        # 3. 客户端默认值
        if self._client_default_app_id is not None:
            logger.debug(
                f"Using app_id from client default: {self._client_default_app_id}"
            )
            return self._client_default_app_id

        # 4. CredentialPool 默认值
        pool_default = self.credential_pool.get_default_app_id()
        if pool_default is not None:
            logger.debug(f"Using app_id from CredentialPool default: {pool_default}")
            return pool_default

        # 5. 无法确定 → 抛出错误
        available_apps = self.list_available_apps()
        raise ConfigError(
            "No app_id specified. Please provide app_id using one of:\n"
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
        logger.debug(
            f"Switched to app_id: {app_id} "
            f"(stack depth: {len(self._context_app_stack)})"
        )

        try:
            yield
        finally:
            # 出栈
            popped = self._context_app_stack.pop()
            logger.debug(
                f"Restored from app_id: {popped} "
                f"(stack depth: {len(self._context_app_stack)})"
            )
```

### CredentialPool 增强

```python
class CredentialPool:
    def __init__(self, config, app_manager, token_storage, lock_dir):
        self.config = config
        self.app_manager = app_manager
        self.token_storage = token_storage
        self._default_app_id: str | None = None
        # ... 其他初始化

    def set_default_app_id(self, app_id: str) -> None:
        """设置默认应用"""
        self._default_app_id = app_id
        logger.info(f"Default app_id set to: {app_id}")

    def get_default_app_id(self) -> str | None:
        """获取默认 app_id"""
        # 1. 如果显式设置了默认值,使用它
        if self._default_app_id is not None:
            return self._default_app_id

        # 2. 委托给 ApplicationManager 自动选择
        return self.app_manager.get_default_app_id()

    def list_app_ids(self) -> list[str]:
        """列出所有活跃的应用 ID"""
        apps = self.app_manager.get_active_applications()
        return [app.app_id for app in apps]

    # 工厂方法
    def create_messaging_client(self, app_id: str) -> MessagingClient:
        """为指定应用创建消息客户端"""
        return MessagingClient(credential_pool=self, app_id=app_id)

    def create_contact_client(self, app_id: str) -> ContactClient:
        """为指定应用创建通讯录客户端"""
        return ContactClient(credential_pool=self, app_id=app_id)

    def create_clouddoc_client(self, app_id: str) -> CloudDocClient:
        """为指定应用创建云文档客户端"""
        return CloudDocClient(credential_pool=self, app_id=app_id)
```

### ApplicationManager 增强

```python
class ApplicationManager:
    def get_default_app_id(self) -> str | None:
        """智能选择默认应用

        规则:
        - 只有一个应用时,自动作为默认应用
        - 多个应用时,返回第一个 (按创建时间)
        - 无活跃应用时,返回 None
        """
        apps = self.get_active_applications()

        if not apps:
            logger.debug("No active applications found")
            return None

        # 只有一个应用时,自动作为默认
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

---

**调研总结**: 本调研完整分析了代码重构、应用切换、线程安全等核心问题,提供了清晰的设计方案和实施细节。所有技术决策均已明确,规范已达到可实施状态。

**下一步**: 执行 `/speckit.plan` 创建技术实施计划。
