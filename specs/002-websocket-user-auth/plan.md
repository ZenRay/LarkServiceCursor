# Implementation Plan: WebSocket 用户授权方案

**Branch**: `002-websocket-user-auth` | **Date**: 2026-01-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-websocket-user-auth/spec.md`

---

## Summary

实现基于 WebSocket 长连接的用户授权方案,通过交互式卡片获取 `user_access_token`,解锁 aPaaS 高级功能(AI 能力、工作流触发等)。

**核心技术方案**:
- 使用 lark-oapi SDK 的 `lark.ws.Client` 建立 WebSocket 长连接
- 通过交互式卡片触发授权流程,使用临时授权码换取 Token
- 存储用户信息和 Token 到 PostgreSQL (加密存储)
- 支持 Token 自动刷新和用户信息同步
- 提供降级到 HTTP 回调的备用方案(可配置)

**技术特点**:
- ✅ 无需公网 HTTP 端点,部署极简
- ✅ 纯飞书内闭环,用户体验流畅
- ✅ 实时事件接收,响应速度快
- ✅ 复用现有 Phase 3 CardKit 服务

---

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**:
- lark-oapi SDK (v1.5.2+) - WebSocket 客户端和事件处理
- SQLAlchemy 2.0 - ORM 和数据库交互
- asyncio/aiohttp - 异步编程支持
- pytest - 测试框架
- pytest-asyncio - 异步测试支持
- pytest-mock - Mock 支持

**Storage**:
- PostgreSQL (生产) - 用户授权会话、Token、用户信息
- SQLite (开发/测试) - 本地测试数据库
- pg_crypto - Token 加密存储

**Testing**:
- pytest + pytest-asyncio - 单元测试和集成测试
- pytest-mock - 模拟 WebSocket 连接和飞书 API
- Contract Testing - 卡片事件契约验证
- Manual Interactive Testing - 真实授权流程测试(需人工交互)

**Target Platform**: Linux server (Docker), 支持 macOS/Windows 开发环境

**Project Type**: 单项目 Python 库 (扩展现有 lark-service 项目)

**Performance Goals**:
- WebSocket 连接可用率 ≥ 99.9%
- 授权完成时间 ≤ 15秒 (p95)
- 支持 1000 并发授权会话
- Token 刷新成功率 ≥ 98%

**Constraints**:
- 授权成功率 ≥ 95%
- WebSocket 重连时间 < 16秒 (1+2+4+8)
- 数据库查询延迟 < 50ms (p95)
- 内存占用增量 < 100MB

**Scale/Scope**:
- 预计 1000+ 用户
- 10万+ 授权会话/月
- 4个新 Python 模块 (~2000 行代码)
- 8个新测试文件 (~1500 行测试代码)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. 核心技术栈要求
- ✅ **Python 3.12**: 符合要求
- ✅ **lark-oapi SDK**: 使用官方 SDK 的 `lark.ws.Client` 和 `EventDispatcherHandler`
- ✅ **无自行实现**: 依赖 SDK 内置 WebSocket 客户端,不自行实现协议

### ✅ II. 代码质量门禁
- ✅ **Mypy 类型检查**: 目标 99%+ 覆盖率,所有新代码强类型标注
- ✅ **Ruff 格式化**: 所有代码遵循 ruff format 标准
- ✅ **Docstring 标准**: 所有公共类/函数包含标准格式 Docstring (英文)
- ✅ **质量门禁**: 提交前强制执行 ruff check, mypy, pytest

### ✅ III. 架构完整性 (非妥协)
- ✅ **领域驱动设计**: 新增 `auth` 模块和 `events` 模块,清晰边界
- ✅ **无循环依赖**:
  - `events.websocket_client` ← 独立模块
  - `auth.card_auth_handler` ← 依赖 `messaging` (Phase 3)
  - `auth.session_manager` ← 依赖 `core.models` (Phase 2)
  - `apaas.client` ← 扩展,依赖 `auth` 模块
- ✅ **模块职责**:
  - `events`: WebSocket 连接管理和事件分发
  - `auth`: 授权流程处理和会话管理
  - `apaas`: aPaaS 客户端集成 (Phase 5 扩展)

### ✅ IV. 响应一致性
- ✅ **标准化响应**: 所有 API 方法返回统一的 Result 类型或抛出标准异常
- ✅ **错误上下文**: 自定义异常 `AuthenticationRequired`, `TokenExpired`, `WebSocketConnectionError`
- ✅ **请求追踪**: 日志包含 session_id 和 request_id

### ✅ V. 安全性底线
- ✅ **Token 加密**: 使用 PostgreSQL pg_crypto 加密存储 user_access_token
- ✅ **环境变量**: app_id, app_secret 通过环境变量注入
- ✅ **无明文凭据**: 代码、日志、配置文件均脱敏处理
- ✅ **审计日志**: 记录所有授权操作 (创建、完成、失败、撤销)

### ✅ VI. 环境一致性
- ✅ **单一目录**: 所有代码在 `src/lark_service/` 下
- ✅ **环境切换**: 通过 .env 文件切换开发/测试/生产配置
- ✅ **无环境混合**: 使用 uv 统一依赖管理

### ✅ VII. 零信任安全 (非妥协)
- ✅ **.env 管理**: 敏感配置通过 .env 文件,已在 .gitignore 排除
- ✅ **无硬编码**: 代码中无任何凭据硬编码
- ✅ **生产建议**: 文档说明使用外部密钥管理服务 (可选)
- ✅ **密钥轮换**: 支持 Token 定期刷新和手动撤销

### ✅ VIII. 测试先行 (非妥协)
- ✅ **TDD 流程**: 所有新功能先写失败测试
- ✅ **红-绿-重构**: 严格遵循 TDD 循环
- ✅ **测试覆盖**: 目标 90%+ 覆盖率
- ✅ **PR 测试**: 所有 PR 必须包含测试代码

**特殊考虑 - 交互式授权测试**:
- 单元测试: Mock WebSocket 事件和飞书 API
- 集成测试: 使用 pytest fixtures 模拟完整流程
- 手动测试: 提供测试脚本 `tests/manual/interactive_auth_test.py` 供人工测试真实授权流程
- Contract 测试: 验证卡片事件契约

### ✅ IX. 文档语言规范
- ✅ **代码英文**: 变量名、函数名、类名、Docstring 全部英文
- ✅ **文档中文**: spec.md, plan.md, research.md, README 使用中文
- ✅ **日志英文**: 结构化日志消息使用英文

### ✅ X. 文件操作闭环 (非妥协)
- ✅ **原地更新**: 所有文档和代码在原文件上迭代
- ✅ **无冗余**: 不创建 spec_v2.md 或 plan_backup.md
- ✅ **闭环验证**: 创建 → 检查 → 更新都在同一文件

### ✅ XI. Git 提交规范 (非妥协)
- ✅ **格式化**: git add 前执行 `ruff format .`
- ✅ **质量检查**: git commit 前执行 `ruff check`, `mypy`, `pytest`
- ✅ **提交消息**: 遵循 Conventional Commits 格式
- ✅ **明确 Push**: 不自动 push,必须手动 `git push origin 002-websocket-user-auth`

---

## Project Structure

### Documentation (this feature)

```text
specs/002-websocket-user-auth/
├── spec.md              # 功能规范 (已完成)
├── research.md          # 技术调研 (已完成)
├── plan.md              # 本文件 - 技术实施计划
├── data-model.md        # Phase 1 输出 - 数据模型设计
├── quickstart.md        # Phase 1 输出 - 快速开始指南
├── contracts/           # Phase 1 输出 - API 契约
│   ├── websocket_events.yaml    # WebSocket 事件契约
│   └── auth_session_api.yaml    # 授权会话 API 契约
├── checklists/          # 质量检查清单
│   └── requirements.md  # 规范质量检查 (已完成)
└── README.md            # 功能概览 (已完成)
```

### Source Code (repository root)

**选择**: Option 1 - 单项目结构 (扩展现有 lark-service 项目)

```text
src/lark_service/
├── events/                          # NEW - WebSocket 事件管理模块
│   ├── __init__.py
│   ├── websocket_client.py          # WebSocket 客户端封装
│   ├── event_dispatcher.py          # 事件分发器 (可选,如 SDK 不够用)
│   └── types.py                     # WebSocket 相关类型定义
│
├── auth/                            # NEW - 授权管理模块
│   ├── __init__.py
│   ├── session_manager.py           # 授权会话管理器
│   ├── card_auth_handler.py         # 卡片授权处理器
│   ├── exceptions.py                # 授权相关异常
│   └── types.py                     # 授权相关类型定义
│
├── core/
│   ├── models/
│   │   └── auth_session.py          # EXTEND - 扩展 UserAuthSession 模型字段
│   └── config.py                    # EXTEND - 新增 WebSocket 和授权配置
│
├── apaas/
│   └── client.py                    # EXTEND - 集成 user_access_token 管理
│
└── messaging/                       # REUSE - Phase 3 已实现
    ├── client.py                    # 复用发送卡片
    └── cardkit/                     # 复用卡片构建

tests/
├── unit/
│   ├── events/                      # NEW - WebSocket 单元测试
│   │   ├── test_websocket_client.py
│   │   └── test_event_dispatcher.py
│   │
│   ├── auth/                        # NEW - 授权单元测试
│   │   ├── test_session_manager.py
│   │   ├── test_card_auth_handler.py
│   │   └── test_exceptions.py
│   │
│   └── apaas/
│       └── test_client_auth.py      # EXTEND - 测试 Token 集成
│
├── integration/
│   ├── test_websocket_auth_flow.py  # NEW - 完整授权流程测试
│   ├── test_token_refresh.py        # NEW - Token 刷新测试
│   └── test_apaas_with_auth.py      # NEW - aPaaS 集成测试
│
├── contract/
│   └── test_card_events.py          # NEW - 卡片事件契约测试
│
└── manual/                          # NEW - 手动交互测试
    ├── interactive_auth_test.py     # 真实授权流程测试脚本
    └── README.md                    # 测试说明和步骤

migrations/versions/                 # EXTEND - 数据库迁移
└── 20260119_xxxx_extend_auth_session.py  # 扩展 user_auth_sessions 表
```

**Structure Decision**:
- **单项目结构**: 扩展现有 lark-service 项目,避免循环依赖
- **新模块**: `events` (WebSocket) 和 `auth` (授权管理) 模块,职责清晰
- **复用模块**: `messaging` (Phase 3), `core.models` (Phase 2), `apaas` (Phase 5)
- **测试分层**: 单元测试 (Mock)、集成测试 (真实流程)、契约测试 (事件验证)、手动测试 (交互式授权)

---

## Complexity Tracking

> **无宪章违规,此表留空**

---

## Phase 0: Research & Unknowns Resolution

### ✅ 已完成 - research.md

**已解决的调研问题**:
1. ✅ WebSocket 长连接 vs OAuth vs HTTP 回调方案对比
2. ✅ lark-oapi SDK 的 `lark.ws.Client` 可行性验证
3. ✅ 临时授权码换取 user_access_token 的 API 流程
4. ✅ 用户信息获取和存储策略
5. ✅ Token 刷新机制和降级策略
6. ✅ 授权卡片设计和用户体验优化

**关键决策** (详见 research.md):
- **方案选择**: WebSocket 长连接 (98/100 分)
- **SDK 支持**: lark-oapi SDK 已内置,有完整示例 (example.py)
- **Token 换取**: 使用 authorization_code 调用 `/open-apis/authen/v1/oidc/access_token`
- **用户信息**: Token 刷新时同步更新 + 可选定期异步更新
- **降级策略**: 10次重连失败后切换到 HTTP 回调(可配置)

---

## Phase 1: Data Model & Contracts

### 1.1 Data Model Design → data-model.md

**需要定义的实体**:

#### 1. UserAuthSession (扩展现有模型)

**新增字段**:
```python
# 扩展 src/lark_service/core/models/auth_session.py
class UserAuthSession(Base):
    """User authentication session for WebSocket-based authorization."""

    # 现有字段 (保留)
    id: Mapped[int]
    session_id: Mapped[str]              # UUID
    app_id: Mapped[str]
    state: Mapped[str]                   # pending/completed/expired
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]

    # 新增字段 (Phase 002)
    user_id: Mapped[str]                 # 飞书用户 ID
    open_id: Mapped[str | None]          # 用户 OpenID
    union_id: Mapped[str | None]         # 用户 UnionID
    user_name: Mapped[str | None]        # 用户姓名
    mobile: Mapped[str | None]           # 手机号
    email: Mapped[str | None]            # 邮箱
    auth_method: Mapped[str]             # "websocket_card"
    user_access_token: Mapped[str | None]  # Token (已加密)
    token_expires_at: Mapped[datetime | None]

    # 索引
    __table_args__ = (
        Index('idx_auth_session_user', 'app_id', 'user_id'),
        Index('idx_auth_session_token_expires', 'token_expires_at'),
    )
```

#### 2. WebSocketConnectionStatus (新增配置实体)

```python
# src/lark_service/events/types.py
@dataclass
class WebSocketConnectionStatus:
    """WebSocket connection status tracking."""
    is_connected: bool
    last_connected_at: datetime | None
    last_disconnected_at: datetime | None
    reconnect_count: int
    last_error: str | None
```

#### 3. AuthCardOptions (新增配置实体)

```python
# src/lark_service/auth/types.py
@dataclass
class AuthCardOptions:
    """Options for authorization card customization."""
    include_detailed_description: bool = True
    auth_card_template_id: str | None = None
    custom_message: str | None = None
```

### 1.2 API Contracts → contracts/

**需要定义的契约**:

#### WebSocket 事件契约 (contracts/websocket_events.yaml)
- P2CardActionTrigger 事件结构
- 授权按钮 action.value 格式
- authorization_code 提取规则

#### 授权会话 API 契约 (contracts/auth_session_api.yaml)
- `AuthSessionManager.create_session()`
- `AuthSessionManager.get_active_token()`
- `AuthSessionManager.complete_session()`
- `AuthSessionManager.refresh_token()`

### 1.3 Quick Start Guide → quickstart.md

**内容概要**:
1. **5分钟快速开始**: 配置环境变量 → 启动 WebSocket 客户端 → 发送测试授权卡片
2. **开发者集成**: aPaaS 客户端调用示例
3. **测试授权流程**: 使用 `tests/manual/interactive_auth_test.py` 测试真实授权
4. **常见问题**: WebSocket 连接失败、Token 获取失败、权限不足

### 1.4 数据库迁移

**新增迁移文件**: `migrations/versions/20260119_xxxx_extend_auth_session.py`

**变更内容**:
```python
# 扩展 user_auth_sessions 表
op.add_column('user_auth_sessions',
    sa.Column('user_name', sa.String(128), nullable=True))
op.add_column('user_auth_sessions',
    sa.Column('mobile', sa.String(32), nullable=True))
op.add_column('user_auth_sessions',
    sa.Column('email', sa.String(128), nullable=True))
op.add_column('user_auth_sessions',
    sa.Column('union_id', sa.String(64), nullable=True))

# 新增索引
op.create_index('idx_auth_session_user', 'user_auth_sessions',
    ['app_id', 'user_id'])
op.create_index('idx_auth_session_token_expires', 'user_auth_sessions',
    ['token_expires_at'])
```

---

## Phase 2: Implementation Roadmap (TDD Approach)

### 2.1 TDD 实施原则

**严格遵循红-绿-重构循环**:
1. **红**: 编写失败测试,验证测试有效
2. **绿**: 实现最小可行代码,使测试通过
3. **重构**: 优化代码结构,保持测试通过

**测试层次**:
1. **单元测试** (Mock): 每个类和方法独立测试
2. **集成测试** (真实流程): 完整授权流程端到端测试
3. **契约测试**: 验证 WebSocket 事件和 API 契约
4. **手动测试**: 交互式授权流程测试 (需人工操作)

### 2.2 实施模块顺序 (按依赖关系)

#### Module 1: WebSocket 客户端 (P1 - 最高优先级)

**TDD 流程**:

**Step 1: 编写失败测试**
```python
# tests/unit/events/test_websocket_client.py
@pytest.mark.asyncio
async def test_websocket_client_connect_success():
    """Test: WebSocket client successfully establishes connection."""
    # RED - 测试失败 (类还不存在)
    client = LarkWebSocketClient(app_id="test", app_secret="test")
    await client.connect()
    assert client.is_connected() == True  # 预期通过,实际失败
```

**Step 2: 实现最小代码**
```python
# src/lark_service/events/websocket_client.py
import lark_oapi as lark

class LarkWebSocketClient:
    """Feishu WebSocket long connection client."""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._ws_client: lark.ws.Client | None = None
        self._is_connected = False

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        self._ws_client = lark.ws.Client(
            self.app_id,
            self.app_secret,
            event_handler=lark.EventDispatcherHandler.builder("", "").build(),
        )
        self._ws_client.start()  # 启动连接
        self._is_connected = True  # GREEN - 测试通过

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._is_connected
```

**Step 3: 添加更多测试 (断线重连)**
```python
@pytest.mark.asyncio
async def test_websocket_client_reconnect_on_disconnect(mocker):
    """Test: WebSocket client auto-reconnects with exponential backoff."""
    # RED - 重连逻辑未实现
    client = LarkWebSocketClient(app_id="test", app_secret="test")
    await client.connect()

    # 模拟断线
    client._simulate_disconnect()

    # 等待重连
    await asyncio.sleep(2)  # 等待第1次重连 (1秒后)
    assert client.reconnect_count == 1
    assert client.is_connected() == True
```

**Step 4: 实现重连逻辑**
```python
# GREEN - 添加重连功能
async def _reconnect_with_backoff(self, max_retries: int = 10):
    """Reconnect with exponential backoff."""
    for i in range(max_retries):
        delay = 2 ** i  # 1s, 2s, 4s, 8s...
        await asyncio.sleep(delay)
        try:
            await self.connect()
            break
        except Exception as e:
            self.reconnect_count += 1
            logger.warning(f"Reconnect attempt {i+1} failed: {e}")
```

**Step 5: 重构 (抽取配置类)**
```python
# REFACTOR - 优化代码结构
@dataclass
class WebSocketConfig:
    """WebSocket client configuration."""
    app_id: str
    app_secret: str
    max_reconnect_retries: int = 10
    heartbeat_interval: int = 30
    fallback_to_http_callback: bool = True

class LarkWebSocketClient:
    def __init__(self, config: WebSocketConfig):
        self.config = config
        # ...
```

**完整测试覆盖** (目标 90%+):
- ✅ 连接建立成功
- ✅ 连接失败处理
- ✅ 断线自动重连 (指数退避)
- ✅ 10次重连失败后降级
- ✅ 心跳保活机制
- ✅ 事件注册和分发
- ✅ 优雅关闭

**工作量估计**: 2-3天

---

#### Module 2: 授权会话管理器 (P1)

**TDD 流程**:

**Step 1: 编写失败测试**
```python
# tests/unit/auth/test_session_manager.py
def test_create_auth_session_success(db_session):
    """Test: Create new auth session with UUID and expiration."""
    # RED - 方法未实现
    manager = AuthSessionManager(db_session)
    session = manager.create_session(
        app_id="cli_test",
        user_id="ou_test",
        auth_method="websocket_card"
    )

    assert session.session_id is not None
    assert session.state == "pending"
    assert session.expires_at > datetime.now(UTC)
```

**Step 2: 实现最小代码**
```python
# src/lark_service/auth/session_manager.py
class AuthSessionManager:
    """Authentication session manager."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_session(
        self,
        app_id: str,
        user_id: str,
        auth_method: str = "websocket_card"
    ) -> UserAuthSession:
        """Create new auth session."""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(minutes=10)

        session = UserAuthSession(
            session_id=session_id,
            app_id=app_id,
            user_id=user_id,
            auth_method=auth_method,
            state="pending",
            expires_at=expires_at,
        )

        self.db.add(session)
        self.db.commit()
        return session  # GREEN - 测试通过
```

**Step 3: 添加复杂测试 (complete_session)**
```python
def test_complete_session_stores_token_and_user_info(db_session):
    """Test: Complete session stores encrypted token and user info."""
    # RED - complete_session 未实现
    manager = AuthSessionManager(db_session)
    session = manager.create_session("cli_test", "ou_test")

    user_info = {
        "name": "张三",
        "user_id": "ou_123",
        "open_id": "ou_123",
        "union_id": "on_456",
        "mobile": "+86-13800138000",
        "email": "zhangsan@example.com"
    }

    manager.complete_session(
        session_id=session.session_id,
        user_access_token="u-testtoken",
        token_expires_at=datetime.now(UTC) + timedelta(days=7),
        user_info=user_info
    )

    # 验证
    updated = manager.get_session(session.session_id)
    assert updated.state == "completed"
    assert updated.user_name == "张三"
    assert updated.user_access_token is not None  # 已加密
```

**完整测试覆盖**:
- ✅ 创建会话 (UUID 生成、过期时间)
- ✅ 完成会话 (Token 存储、用户信息存储)
- ✅ 获取活跃 Token (按 user_id 查询)
- ✅ 刷新 Token (调用飞书 API + 更新用户信息)
- ✅ 清理过期会话 (定时任务)
- ✅ 会话过期验证
- ✅ 多用户隔离

**工作量估计**: 1天

---

#### Module 3: 卡片授权处理器 (P1)

**TDD 流程**:

**Step 1: 编写失败测试**
```python
# tests/unit/auth/test_card_auth_handler.py
@pytest.mark.asyncio
async def test_send_auth_card_success(mocker):
    """Test: Send authorization card to user."""
    # RED - 方法未实现
    session_manager = mocker.Mock()
    messaging_client = mocker.Mock()
    handler = CardAuthHandler(session_manager, messaging_client)

    message_id = await handler.send_auth_card(
        app_id="cli_test",
        user_id="ou_test",
        session_id="session_123",
        options=AuthCardOptions(include_detailed_description=True)
    )

    assert message_id is not None
    messaging_client.send_card.assert_called_once()
```

**Step 2: 实现最小代码**
```python
# src/lark_service/auth/card_auth_handler.py
class CardAuthHandler:
    """Card-based authentication event handler."""

    def __init__(
        self,
        session_manager: AuthSessionManager,
        messaging_client: MessagingClient,
    ):
        self.session_manager = session_manager
        self.messaging_client = messaging_client

    async def send_auth_card(
        self,
        app_id: str,
        user_id: str,
        session_id: str,
        options: AuthCardOptions | None = None,
    ) -> str:
        """Send authorization card to user."""
        options = options or AuthCardOptions()

        # 构建卡片 (复用 Phase 3 CardBuilder)
        card = self._build_auth_card(session_id, options)

        # 发送卡片
        message_id = await self.messaging_client.send_card(
            receive_id=user_id,
            receive_id_type="open_id",
            card=card
        )

        return message_id  # GREEN - 测试通过
```

**Step 3: 测试事件处理 (核心逻辑)**
```python
@pytest.mark.asyncio
async def test_handle_card_auth_event_exchanges_token(mocker):
    """Test: Handle card auth event extracts code and exchanges for token."""
    # RED - handle_card_auth_event 未实现

    # Mock 飞书 API 响应
    mocker.patch('lark_service.auth.card_auth_handler._call_feishu_api',
        return_value={
            'user_access_token': 'u-test-token',
            'expires_in': 604800,  # 7天
            'user_info': {
                'name': '张三',
                'user_id': 'ou_123',
                'open_id': 'ou_123',
                'union_id': 'on_456',
                'mobile': '+86-13800138000',
                'email': 'zhangsan@example.com'
            }
        })

    # 构造卡片回调事件
    event = P2CardActionTrigger(
        event={
            'operator': {'open_id': 'ou_123'},
            'action': {
                'value': {
                    'session_id': 'session_123',
                    'authorization_code': 'auth_code_xyz'
                }
            }
        }
    )

    handler = CardAuthHandler(session_manager, messaging_client)
    response = await handler.handle_card_auth_event(event)

    # 验证
    assert response is not None
    session_manager.complete_session.assert_called_once_with(
        session_id='session_123',
        user_access_token='u-test-token',
        token_expires_at=mocker.ANY,
        user_info=mocker.ANY
    )
```

**Step 4: 实现 Token 换取逻辑**
```python
async def handle_card_auth_event(
    self,
    event: P2CardActionTrigger
) -> P2CardActionTriggerResponse:
    """Handle card authentication button click event."""
    # 提取数据
    open_id = event.event.operator.open_id
    authorization_code = event.event.action.value['authorization_code']
    session_id = event.event.action.value['session_id']

    try:
        # 换取 Token 和用户信息
        token_data = await self._exchange_token(authorization_code)
        user_info = await self._fetch_user_info(token_data['user_access_token'])

        # 完成会话
        token_expires_at = datetime.now(UTC) + timedelta(
            seconds=token_data['expires_in']
        )
        self.session_manager.complete_session(
            session_id=session_id,
            user_access_token=token_data['user_access_token'],
            token_expires_at=token_expires_at,
            user_info=user_info
        )

        # 返回成功响应
        return P2CardActionTriggerResponse({
            'toast': {'content': '授权成功!'},
            'card': self._build_success_card()
        })

    except Exception as e:
        logger.error(f"Auth failed for session {session_id}: {e}")
        return P2CardActionTriggerResponse({
            'toast': {'content': '授权失败,请重试'},
        })  # GREEN - 测试通过
```

**完整测试覆盖**:
- ✅ 发送授权卡片 (详细版/简洁版)
- ✅ 处理卡片回调事件
- ✅ 提取 authorization_code
- ✅ 换取 user_access_token
- ✅ 获取用户详细信息
- ✅ 更新卡片显示成功
- ✅ 错误处理 (Token 换取失败、用户拒绝)

**工作量估计**: 1-2天

---

#### Module 4: aPaaS 客户端集成 (P1)

**TDD 流程**:

**Step 1: 编写失败测试**
```python
# tests/unit/apaas/test_client_auth.py
@pytest.mark.asyncio
async def test_apaas_client_auto_injects_user_token(mocker):
    """Test: aPaaS client automatically injects user_access_token."""
    # RED - _get_user_access_token 未实现
    auth_manager = mocker.Mock()
    auth_manager.get_active_token.return_value = "u-test-token"

    client = aPaaSClient(app_id="cli_test", auth_manager=auth_manager)

    # 调用需要 user_access_token 的 API
    result = await client.call_ai_api(
        user_id="ou_test",
        prompt="测试提示词"
    )

    # 验证自动注入 Token
    auth_manager.get_active_token.assert_called_once_with("cli_test", "ou_test")
    assert result is not None
```

**Step 2: 扩展 aPaaSClient**
```python
# src/lark_service/apaas/client.py (扩展)
class aPaaSClient:
    """aPaaS Data Space client with user authentication support."""

    def __init__(
        self,
        app_id: str,
        auth_manager: AuthSessionManager | None = None,
        card_auth_handler: CardAuthHandler | None = None,
    ):
        self.app_id = app_id
        self.auth_manager = auth_manager
        self.card_auth_handler = card_auth_handler

    async def _get_user_access_token(
        self,
        user_id: str
    ) -> str:
        """Get user_access_token from session manager.

        Raises:
            AuthenticationRequired: If user not authenticated
        """
        if not self.auth_manager:
            raise AuthenticationRequired("Auth manager not configured")

        token = self.auth_manager.get_active_token(self.app_id, user_id)

        if not token:
            # 自动发送授权卡片
            if self.card_auth_handler:
                session = self.auth_manager.create_session(self.app_id, user_id)
                await self.card_auth_handler.send_auth_card(
                    self.app_id, user_id, session.session_id
                )

            raise AuthenticationRequired(
                f"User {user_id} not authenticated. "
                "Authorization card sent, please authorize."
            )

        return token  # GREEN - 测试通过

    async def call_ai_api(
        self,
        user_id: str,
        prompt: str
    ) -> dict:
        """Call aPaaS AI API with user authentication.

        Args:
            user_id: User ID
            prompt: AI prompt

        Returns:
            AI API response

        Raises:
            AuthenticationRequired: If user not authenticated
        """
        # 自动获取 Token
        user_access_token = await self._get_user_access_token(user_id)

        # 调用 API
        response = await self._call_apaas_api(
            endpoint='/ai/chat',
            data={'prompt': prompt},
            user_access_token=user_access_token
        )

        return response
```

**Step 3: 测试 Token 过期刷新**
```python
@pytest.mark.asyncio
async def test_apaas_client_auto_refreshes_expired_token(mocker):
    """Test: aPaaS client auto-refreshes expired token on 401."""
    # RED - 刷新逻辑未实现
    auth_manager = mocker.Mock()
    auth_manager.get_active_token.return_value = "u-expired-token"
    auth_manager.refresh_token.return_value = "u-new-token"

    client = aPaaSClient(app_id="cli_test", auth_manager=auth_manager)

    # 模拟 401 错误
    mocker.patch('lark_service.apaas.client._call_apaas_api',
        side_effect=[
            HTTPError(status_code=401),  # 第1次调用失败
            {'result': 'success'}         # 第2次调用成功
        ])

    result = await client.call_ai_api(user_id="ou_test", prompt="test")

    # 验证自动刷新
    auth_manager.refresh_token.assert_called_once_with("cli_test", "ou_test")
    assert result['result'] == 'success'
```

**Step 4: 实现刷新逻辑**
```python
async def _call_apaas_api_with_retry(
    self,
    endpoint: str,
    data: dict,
    user_access_token: str,
    user_id: str
) -> dict:
    """Call aPaaS API with auto token refresh on 401."""
    try:
        return await self._call_apaas_api(
            endpoint, data, user_access_token
        )
    except HTTPError as e:
        if e.status_code == 401:
            # Token 过期,尝试刷新
            logger.info(f"Token expired for {user_id}, refreshing...")
            new_token = self.auth_manager.refresh_token(self.app_id, user_id)

            # 重试 (仅1次)
            return await self._call_apaas_api(
                endpoint, data, new_token
            )
        raise  # GREEN - 测试通过
```

**完整测试覆盖**:
- ✅ 自动注入 user_access_token
- ✅ 缺少授权时自动发送卡片
- ✅ Token 过期时自动刷新
- ✅ 权限不足时明确提示 (403)
- ✅ 多用户并发调用隔离

**工作量估计**: 0.5天

---

### 2.3 集成测试 (P1)

**完整授权流程端到端测试**:

```python
# tests/integration/test_websocket_auth_flow.py
@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_auth_flow_from_card_to_api_call(
    db_session,
    websocket_client_mock,
    feishu_api_mock
):
    """Test: Complete authorization flow from card send to API call.

    Flow:
    1. User calls aPaaS API without auth
    2. System sends auth card
    3. User clicks "Authorize" button
    4. System receives WebSocket event
    5. System exchanges authorization_code for token
    6. System stores token and user info
    7. User calls aPaaS API again (success with token)
    """
    # Setup
    auth_manager = AuthSessionManager(db_session)
    messaging_client = MessagingClient(...)
    card_auth_handler = CardAuthHandler(auth_manager, messaging_client)
    apaas_client = aPaaSClient("cli_test", auth_manager, card_auth_handler)

    # Step 1: 调用 API 无授权 (触发授权卡片)
    with pytest.raises(AuthenticationRequired):
        await apaas_client.call_ai_api(
            user_id="ou_test",
            prompt="测试"
        )

    # 验证卡片已发送
    assert messaging_client.send_card.called

    # Step 2: 模拟用户点击授权按钮 (WebSocket 事件)
    event = P2CardActionTrigger(
        event={
            'operator': {'open_id': 'ou_test'},
            'action': {
                'value': {
                    'session_id': messaging_client.last_session_id,
                    'authorization_code': 'auth_code_test'
                }
            }
        }
    )

    # Step 3: 处理授权事件
    response = await card_auth_handler.handle_card_auth_event(event)
    assert response.toast['content'] == '授权成功!'

    # Step 4: 再次调用 API (应该成功)
    result = await apaas_client.call_ai_api(
        user_id="ou_test",
        prompt="测试"
    )

    assert result is not None

    # 验证 Token 已存储
    token = auth_manager.get_active_token("cli_test", "ou_test")
    assert token is not None
```

**工作量估计**: 1天

---

### 2.4 手动交互式测试 (P2)

**测试脚本**: `tests/manual/interactive_auth_test.py`

```python
#!/usr/bin/env python3
"""Interactive authorization flow test script.

This script tests the real authorization flow with user interaction.

Usage:
    python tests/manual/interactive_auth_test.py

Steps:
    1. Start WebSocket client
    2. Send authorization card to your test account
    3. Click "Authorize" button in Feishu
    4. Verify token is received and stored
    5. Test aPaaS API call with token
"""

import asyncio
import os
from lark_service.events.websocket_client import LarkWebSocketClient
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.card_auth_handler import CardAuthHandler

async def main():
    """Run interactive auth test."""
    print("=== Interactive Authorization Test ===\n")

    # 1. 初始化组件
    print("1. Initializing components...")
    websocket_client = LarkWebSocketClient(
        app_id=os.getenv("APP_ID"),
        app_secret=os.getenv("APP_SECRET")
    )
    auth_manager = AuthSessionManager(db_session)
    card_handler = CardAuthHandler(auth_manager, messaging_client)

    # 2. 启动 WebSocket 连接
    print("2. Starting WebSocket connection...")
    await websocket_client.connect()
    print("   ✅ Connected\n")

    # 3. 发送授权卡片
    print("3. Sending authorization card...")
    test_user_id = input("   Enter your OpenID (ou_xxx): ")

    session = auth_manager.create_session("cli_test", test_user_id)
    message_id = await card_handler.send_auth_card(
        app_id="cli_test",
        user_id=test_user_id,
        session_id=session.session_id
    )
    print(f"   ✅ Card sent (message_id: {message_id})")
    print("   📱 Please check Feishu and click 'Authorize' button\n")

    # 4. 等待授权完成
    print("4. Waiting for authorization...")
    for i in range(60):  # 等待最多60秒
        await asyncio.sleep(1)
        updated_session = auth_manager.get_session(session.session_id)
        if updated_session.state == "completed":
            print("   ✅ Authorization completed!")
            print(f"   User: {updated_session.user_name}")
            print(f"   Email: {updated_session.email}")
            print(f"   Token expires: {updated_session.token_expires_at}\n")
            break
        print(f"   Waiting... ({i+1}/60)")
    else:
        print("   ❌ Timeout: Authorization not completed\n")
        return

    # 5. 测试 API 调用
    print("5. Testing aPaaS API call with token...")
    apaas_client = aPaaSClient("cli_test", auth_manager)
    try:
        result = await apaas_client.call_ai_api(
            user_id=test_user_id,
            prompt="Hello, test!"
        )
        print("   ✅ API call successful!")
        print(f"   Result: {result}\n")
    except Exception as e:
        print(f"   ❌ API call failed: {e}\n")

    # 6. 清理
    print("6. Cleaning up...")
    await websocket_client.disconnect()
    print("   ✅ Done\n")

    print("=== Test Completed ===")

if __name__ == "__main__":
    asyncio.run(main())
```

**测试文档**: `tests/manual/README.md`

```markdown
# 手动交互式测试指南

## 前提条件

1. 飞书开放平台已创建应用
2. 配置 .env 文件包含 APP_ID 和 APP_SECRET
3. 数据库已应用 Alembic 迁移
4. 安装所有依赖: `uv pip install -r requirements.txt`

## 运行测试

```bash
# 启动测试脚本
python tests/manual/interactive_auth_test.py
```

## 测试步骤

1. **启动 WebSocket 连接**: 脚本自动连接
2. **输入测试用户**: 输入你的飞书 OpenID (ou_xxx)
3. **发送授权卡片**: 脚本发送卡片到你的飞书账号
4. **点击授权按钮**: 在飞书中打开卡片,点击"授权"
5. **等待完成**: 脚本等待授权完成(最多60秒)
6. **验证 API 调用**: 脚本测试使用 Token 调用 aPaaS API

## 预期结果

✅ 所有步骤成功,输出包含:
- WebSocket 连接成功
- 授权卡片发送成功
- 授权完成并获取用户信息
- API 调用成功

## 故障排查

### WebSocket 连接失败
- 检查网络连接
- 检查 APP_ID 和 APP_SECRET 是否正确
- 查看日志: `logs/websocket.log`

### 授权超时
- 确保在飞书中点击了"授权"按钮
- 检查 WebSocket 连接是否断开
- 查看 session 状态: `SELECT * FROM user_auth_sessions WHERE session_id='xxx'`

### API 调用失败
- 检查 Token 是否有效
- 检查应用权限配置
- 查看 API 响应错误信息
```

**工作量估计**: 0.5天

---

### 2.5 配置和监控 (P2)

#### 配置参数

```python
# src/lark_service/core/config.py (扩展)
@dataclass
class WebSocketAuthConfig:
    """WebSocket authorization configuration."""

    # WebSocket 配置
    max_reconnect_retries: int = 10
    heartbeat_interval: int = 30
    fallback_to_http_callback: bool = True

    # 授权卡片配置
    include_detailed_description: bool = True
    auth_card_template_id: str | None = None

    # Token 管理配置
    token_refresh_threshold: float = 0.1  # 10%

    # 用户信息同步配置
    user_info_sync_enabled: bool = False
    user_info_sync_schedule: str = "0 2 * * *"  # 每天凌晨2点

    # 限流配置
    auth_request_rate_limit: int = 5  # 每分钟最多5次
```

#### Prometheus 指标

```python
# src/lark_service/monitoring/websocket_metrics.py (新增)
from prometheus_client import Gauge, Counter, Histogram

# WebSocket 连接状态
websocket_connection_status = Gauge(
    'websocket_connection_status',
    'WebSocket connection status (1=connected, 0=disconnected)',
    ['app_id']
)

# WebSocket 重连次数
websocket_reconnect_count = Counter(
    'websocket_reconnect_total',
    'Total WebSocket reconnection attempts',
    ['app_id', 'success']
)

# 授权会话总数
user_auth_sessions_total = Gauge(
    'user_auth_sessions_total',
    'Total user auth sessions by state',
    ['app_id', 'state']
)

# 授权成功率
user_auth_success_rate = Gauge(
    'user_auth_success_rate',
    'User authorization success rate (sliding window 5min)',
    ['app_id']
)

# Token 刷新次数
user_access_token_refresh_total = Counter(
    'user_access_token_refresh_total',
    'Total user access token refreshes',
    ['app_id', 'success']
)

# 授权流程耗时
user_auth_duration_seconds = Histogram(
    'user_auth_duration_seconds',
    'User authorization flow duration',
    ['app_id', 'step']
)
```

**工作量估计**: 1天

---

## Phase 3: Testing Strategy (Summary)

### 测试覆盖目标

| 测试类型 | 覆盖率目标 | 工作量 |
|---------|----------|-------|
| **单元测试** | 90%+ | 2天 |
| **集成测试** | 核心流程 100% | 1天 |
| **契约测试** | 事件格式 100% | 0.5天 |
| **手动测试** | 真实授权 1次 | 0.5天 |
| **总计** | - | **4天** |

### TDD 检查清单

- [ ] 每个类和方法都有对应的失败测试
- [ ] 测试先于实现编写
- [ ] 所有测试初始状态为失败 (红)
- [ ] 实现最小代码使测试通过 (绿)
- [ ] 重构代码保持测试通过
- [ ] 测试覆盖率 ≥ 90%
- [ ] 所有 PR 包含测试代码
- [ ] 手动交互测试至少通过1次

---

## Phase 4: Documentation & Delivery

### 交付清单

#### 代码交付
- [ ] WebSocket 客户端模块 (`events/`)
- [ ] 授权管理模块 (`auth/`)
- [ ] aPaaS 集成扩展 (`apaas/client.py`)
- [ ] 数据库迁移 (`migrations/versions/xxx_extend_auth_session.py`)
- [ ] 配置扩展 (`core/config.py`)
- [ ] 监控指标 (`monitoring/websocket_metrics.py`)

#### 测试交付
- [ ] 单元测试 (90%+ 覆盖率)
- [ ] 集成测试 (端到端流程)
- [ ] 契约测试 (WebSocket 事件)
- [ ] 手动测试脚本 (`tests/manual/interactive_auth_test.py`)

#### 文档交付
- [ ] data-model.md (数据模型设计)
- [ ] quickstart.md (5分钟快速开始)
- [ ] contracts/ (API 契约定义)
- [ ] 手动测试指南 (`tests/manual/README.md`)
- [ ] CHANGELOG.md 更新

#### 质量门禁
- [ ] Ruff format 通过
- [ ] Ruff check 0 错误
- [ ] Mypy 99%+ 覆盖率
- [ ] Pytest 全部通过
- [ ] 代码覆盖率 ≥ 90%
- [ ] 所有 Docstring 符合标准
- [ ] Git 提交消息符合 Conventional Commits

---

## Timeline Estimate

| 阶段 | 任务 | 工作量 | 依赖 |
|------|------|-------|------|
| **Phase 0** | **调研** | **0天** | **已完成** |
| **Phase 1** | data-model.md | 0.5天 | Phase 0 |
| | contracts/ | 0.5天 | Phase 0 |
| | quickstart.md | 0.5天 | Phase 0 |
| | 数据库迁移 | 0.5天 | data-model |
| | **小计** | **2天** | |
| **Phase 2** | WebSocket 客户端 (TDD) | 2-3天 | Phase 1 |
| | 授权会话管理器 (TDD) | 1天 | Phase 1 |
| | 卡片授权处理器 (TDD) | 1-2天 | 会话管理器 |
| | aPaaS 集成 (TDD) | 0.5天 | 授权处理器 |
| | 集成测试 | 1天 | 所有模块 |
| | 手动测试 | 0.5天 | 集成测试 |
| | 配置和监控 | 1天 | 所有模块 |
| | **小计** | **7-9天** | |
| **Phase 3** | 文档完善 | 0.5天 | Phase 2 |
| | 代码审查和重构 | 0.5天 | Phase 2 |
| | **小计** | **1天** | |
| **总计** | **全部** | **10-12天** | |

**关键里程碑**:
- Day 2: Phase 1 完成,数据模型和契约就绪
- Day 5-7: WebSocket + 授权核心模块完成 (TDD)
- Day 8-9: 集成测试和手动测试完成
- Day 10-12: 文档、审查、交付

---

## Risk Mitigation

### 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| WebSocket 连接不稳定 | 中 | 高 | 实现断线重连 + 降级到 HTTP 回调 |
| 异步编程复杂度 | 中 | 中 | 参考 example.py + 充分单元测试 |
| Token 刷新不支持 | 低 | 中 | 验证飞书 API,备选方案重新授权 |
| 并发压力测试失败 | 低 | 中 | 数据库连接池优化 + 限流保护 |

### 进度风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| TDD 延长开发时间 | 中 | 低 | 测试和实现并行,充分利用 Mock |
| 手动测试依赖人工 | 高 | 低 | 提前准备测试账号和环境 |
| 代码审查发现问题 | 中 | 中 | 小步提交,频繁 review |

---

## Success Criteria

### 功能标准
- ✅ 用户可通过卡片完成授权 (≤ 15秒)
- ✅ 授权成功率 ≥ 95%
- ✅ WebSocket 连接可用率 ≥ 99.9%
- ✅ Token 自动刷新成功率 ≥ 98%
- ✅ aPaaS API 自动注入 user_access_token

### 质量标准
- ✅ 测试覆盖率 ≥ 90%
- ✅ Mypy 类型检查 99%+
- ✅ Ruff 检查 0 错误
- ✅ 所有 Docstring 符合标准
- ✅ Git 提交符合 Conventional Commits

### 文档标准
- ✅ quickstart.md 可在 5分钟内完成首次授权
- ✅ 手动测试指南清晰可执行
- ✅ API 契约完整定义
- ✅ CHANGELOG 更新完整

---

**计划状态**: ✅ Phase 0-1 就绪,等待 Phase 2 实施
**最后更新**: 2026-01-19
**下一步**: 运行 `/speckit.tasks` 生成详细任务清单
