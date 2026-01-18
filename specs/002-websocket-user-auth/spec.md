# Feature Specification: WebSocket User Authorization for aPaaS

**Feature Branch**: `002-websocket-user-auth`
**Created**: 2026-01-18
**Status**: Draft
**Input**: 实现基于WebSocket长连接的用户授权方案,通过交互式卡片获取user_access_token,支持aPaaS高级功能

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 用户通过卡片完成授权 (Priority: P1) 🎯 MVP

当用户需要使用需要个人权限的功能(如aPaaS AI能力、工作流触发)时,系统通过交互式卡片引导用户完成授权,无需跳转浏览器,全程在飞书内完成。

**Why this priority**: 这是获取 user_access_token 的核心流程,没有它就无法访问任何需要用户权限的 aPaaS 功能。WebSocket 方案比 OAuth 方案更简单(无需 HTTP 端点),用户体验更好(飞书内闭环)。

**Independent Test**: 发送授权卡片给测试用户 → 用户点击"授权"按钮 → 系统接收 WebSocket 事件 → 获取 user_access_token → 存储到数据库 → 卡片更新显示授权成功。可独立验证完整流程。

**Acceptance Scenarios**:

1. **Given** 用户尚未授权且尝试调用需要 user_access_token 的 API
   **When** 系统检测到缺少授权
   **Then** 系统自动发送授权请求卡片给用户

2. **Given** 用户收到授权卡片
   **When** 用户点击"授权"按钮
   **Then** 飞书通过 WebSocket 推送卡片回调事件到系统

3. **Given** 系统接收到卡片回调事件
   **When** 事件中包含用户的 open_id 和临时授权码
   **Then** 系统调用飞书 API 换取 user_access_token 并存储

4. **Given** user_access_token 已成功获取
   **When** 系统存储 Token 到数据库
   **Then** 卡片更新显示"授权成功"并展示授权范围

5. **Given** 用户已完成授权
   **When** 用户再次调用需要权限的 API
   **Then** 系统直接使用已存储的 user_access_token,无需重新授权

---

### User Story 2 - WebSocket 长连接自动管理 (Priority: P1) 🎯 基础设施

系统启动时自动与飞书建立 WebSocket 长连接,接收实时事件,并自动处理断线重连,确保事件不丢失。

**Why this priority**: WebSocket 连接是接收卡片回调事件的基础,必须优先实现。没有稳定的长连接,用户授权流程就无法完成。

**Independent Test**: 启动系统 → 验证 WebSocket 连接建立成功 → 模拟断线 → 验证自动重连 → 发送测试事件 → 验证事件成功接收。

**Acceptance Scenarios**:

1. **Given** 系统启动且配置了有效的 app_id 和 app_secret
   **When** 系统初始化 WebSocket 客户端
   **Then** 成功与飞书服务器建立 WebSocket 连接

2. **Given** WebSocket 连接已建立
   **When** 网络中断或连接断开
   **Then** 系统自动使用指数退避策略重连(1s→2s→4s→8s,最多10次)

3. **Given** WebSocket 连接空闲超过30秒
   **When** 系统发送心跳 ping 消息
   **Then** 飞书服务器响应 pong,保持连接活跃

4. **Given** WebSocket 连接正常
   **When** 飞书推送任何事件(卡片回调、消息接收、菜单点击)
   **Then** 系统的事件分发器正确路由事件到对应的处理器

---

### User Story 3 - Token 生命周期管理 (Priority: P2)

系统自动管理 user_access_token 的完整生命周期,包括过期检测、自动刷新、多用户隔离。

**Why this priority**: 确保 Token 持续可用,避免用户频繁重新授权。但可以在 P1 完成后再实现,初期可以手动重新授权。

**Independent Test**: 模拟 Token 即将过期 → 系统自动刷新 Token → 验证新 Token 可用 → 验证多用户 Token 正确隔离。

**Acceptance Scenarios**:

1. **Given** user_access_token 剩余有效期少于10%
   **When** 系统检测到 Token 即将过期
   **Then** 自动调用刷新 API 获取新 Token

2. **Given** 系统存储了多个用户的 Token
   **When** 调用 API 时指定不同的 user_id
   **Then** 系统正确使用对应用户的 Token,实现多用户隔离

3. **Given** user_access_token 已完全过期且无法刷新
   **When** 用户尝试调用需要权限的 API
   **Then** 系统重新发送授权卡片,引导用户重新授权

4. **Given** 用户已授权30天
   **When** Token 长期未使用
   **Then** 系统清理过期的 Token 和会话数据

---

### User Story 4 - aPaaS 功能集成 (Priority: P2)

aPaaS 客户端自动检测并使用 user_access_token,支持 AI 能力调用、工作流触发等高级功能。

**Why this priority**: 这是获取 user_access_token 的最终目标,但可以在 Token 管理完成后集成。

**Independent Test**: 调用 aPaaS AI API → 系统自动使用 user_access_token → 验证 AI 调用成功返回结果。

**Acceptance Scenarios**:

1. **Given** 用户已授权且 user_access_token 有效
   **When** 调用 aPaaS AI 能力 API
   **Then** 系统自动注入 user_access_token 并成功调用

2. **Given** 用户尚未授权
   **When** 调用需要 user_access_token 的 aPaaS API
   **Then** 系统抛出 AuthenticationRequired 异常,并发送授权卡片

3. **Given** user_access_token 已过期
   **When** 调用 aPaaS API 时收到401错误
   **Then** 系统自动尝试刷新 Token 并重试,失败则引导重新授权

---

### User Story 5 - 授权会话监控与管理 (Priority: P3)

管理员可以查看所有授权会话的状态,包括活跃会话、过期会话、授权范围等,并可手动撤销授权。

**Why this priority**: 运维和安全管理功能,重要但不紧急,可以在核心功能稳定后补充。

**Independent Test**: 管理员查询授权会话列表 → 查看特定用户的授权详情 → 手动撤销某个用户的授权 → 验证该用户下次调用时需要重新授权。

**Acceptance Scenarios**:

1. **Given** 管理员登录系统
   **When** 查询所有授权会话
   **Then** 系统返回会话列表,包含用户ID、授权时间、Token过期时间、授权范围

2. **Given** 管理员选择某个用户的会话
   **When** 手动撤销授权
   **Then** 系统删除 user_access_token 并通知用户授权已撤销

3. **Given** 系统运行中
   **When** 定时任务检测到过期会话(超过10分钟未完成或Token已过期)
   **Then** 自动清理过期会话数据,释放存储空间

---

### Edge Cases

#### 网络和连接异常

- **WebSocket 连接失败**: 系统记录 ERROR 日志,使用指数退避重试,10次失败后进入降级模式(使用 HTTP 回调备用方案)
- **连接中断时收到授权请求**: 系统将授权请求加入待处理队列,连接恢复后批量处理
- **重连期间丢失事件**: 飞书会缓存未送达的事件,重连后自动推送(官方保证机制)

#### 授权流程异常

- **用户拒绝授权**: 卡片显示"授权被拒绝",API 返回 AuthenticationRequired 错误,记录 WARNING 日志
- **用户多次点击授权按钮**: 系统使用 session_id 去重,同一会话只处理一次授权请求
- **授权卡片过期未操作**: 10分钟后会话自动过期,卡片显示"授权链接已失效",用户需重新触发授权
- **换取 Token 失败**: 记录详细错误信息(错误码、错误消息),卡片显示友好错误提示,引导用户重试
- **Token 权限不足**: 明确告知用户缺少的权限(如 apaas:workspace:write),引导联系管理员开通权限

#### 多用户和并发场景

- **同一用户在多个设备同时授权**: 最后完成的授权覆盖之前的 Token,旧设备上的 Token 自动失效
- **多用户同时请求授权**: 系统为每个用户创建独立的会话(session_id),互不干扰
- **高并发授权请求**: 使用数据库事务和唯一索引避免重复授权,限流保护(每用户每分钟最多5次授权请求)

#### 数据一致性

- **Token 存储失败**: 回滚授权会话,卡片显示"授权失败,请重试",记录 ERROR 日志
- **数据库连接中断**: 授权流程失败,返回错误给用户,连接恢复后自动重试(最多3次)
- **Token 在数据库中存在但已被飞书撤销**: 下次调用时收到401错误,系统自动清理本地 Token,引导重新授权

#### 安全和隐私

- **恶意伪造卡片回调事件**: 系统验证事件签名(使用飞书提供的签名验证机制),签名无效则拒绝处理
- **Token 泄露风险**: Token 在数据库中加密存储(使用 pg_crypto),传输时使用 HTTPS,日志中脱敏显示
- **过期会话清理**: 定时任务(每小时)清理10分钟前创建但未完成的会话,防止数据库膨胀

---

## Requirements *(mandatory)*

### Functional Requirements

#### WebSocket 长连接管理

- **FR-001**: 系统 MUST 在启动时自动建立与飞书的 WebSocket 长连接,使用 lark-oapi SDK 的 `lark.ws.Client`
- **FR-002**: 系统 MUST 注册卡片回调事件处理器(`register_p2_card_action_trigger`),监听用户点击授权按钮事件
- **FR-003**: 系统 MUST 实现自动断线重连机制,使用指数退避策略(1s→2s→4s→8s),最多重试10次
- **FR-004**: 系统 MUST 每30秒发送心跳 ping 消息,保持连接活跃
- **FR-005**: 系统 MUST 记录 WebSocket 连接状态变化(连接、断开、重连)到结构化日志,包含时间戳和失败原因
- **FR-006**: 系统 MUST 支持优雅关闭,断开 WebSocket 连接前完成正在处理的事件

#### 授权卡片发送与处理

- **FR-007**: 系统 MUST 提供 `send_auth_card(app_id, user_id, session_id)` 方法,发送授权请求卡片给用户
- **FR-008**: 授权卡片 MUST 包含以下元素:
  - 授权请求说明(为什么需要授权)
  - "授权"按钮(action="user_auth", value包含session_id)
  - 授权范围说明(将获得哪些权限)
  - 隐私政策链接
- **FR-009**: 卡片按钮的 action.value MUST 包含 session_id,用于关联授权会话
- **FR-010**: 系统 MUST 在用户点击授权按钮后,从事件中提取 `open_id` 和 `session_id`
- **FR-011**: 系统 MUST 调用飞书 OAuth API (`/open-apis/authen/v1/access_token`) 换取 user_access_token
- **FR-012**: 系统 MUST 在授权成功后更新卡片,显示"授权成功"和授权时间,禁用授权按钮

#### 授权会话管理

- **FR-013**: 系统 MUST 创建授权会话时生成唯一的 session_id (UUID v4格式)
- **FR-014**: 系统 MUST 存储授权会话到数据库 `user_auth_sessions` 表,包含字段:
  - session_id (主键)
  - app_id (应用ID)
  - user_id / open_id (用户标识)
  - auth_method (固定为"websocket_card")
  - state (pending/completed/expired)
  - created_at, expires_at (10分钟有效期), completed_at
- **FR-015**: 系统 MUST 在用户完成授权后,更新会话状态为 completed,记录 completed_at 时间
- **FR-016**: 系统 MUST 定时清理过期会话(每小时),删除 created_at 超过10分钟且状态为 pending 的记录
- **FR-017**: 系统 MUST 拒绝处理已过期的 session_id,返回错误 "授权链接已失效"

#### Token 存储与管理

- **FR-018**: 系统 MUST 存储 user_access_token 到数据库,复用现有 `user_auth_sessions` 表的 `user_access_token` 和 `token_expires_at` 字段
- **FR-019**: user_access_token MUST 加密存储(使用 PostgreSQL pg_crypto 扩展)
- **FR-020**: 系统 MUST 支持多用户隔离,每个 (app_id, user_id) 组合维护独立的 Token
- **FR-021**: 系统 MUST 提供 `get_user_access_token(app_id, user_id)` 方法,返回有效的 Token 或抛出 AuthenticationRequired 异常
- **FR-022**: 系统 MUST 在 Token 剩余有效期少于10%时,自动调用刷新 API 获取新 Token
- **FR-023**: 系统 MUST 在 Token 完全过期时,清除数据库中的记录,下次调用时重新引导授权

#### aPaaS 客户端集成

- **FR-024**: aPaaSClient MUST 提供 `_get_user_access_token(app_id, user_id)` 私有方法,从 AuthSessionManager 获取 Token
- **FR-025**: aPaaSClient 的所有需要 user_access_token 的方法 MUST 自动调用 `_get_user_access_token`,无需手动传入 Token
- **FR-026**: aPaaSClient MUST 在检测到缺少授权时(AuthenticationRequired 异常),自动发送授权卡片给用户
- **FR-027**: aPaaSClient MUST 在 Token 过期(401错误)时,自动尝试刷新 Token 并重试API调用(最多1次重试)
- **FR-028**: aPaaSClient MUST 在权限不足(403错误)时,明确告知缺少的权限,记录 WARNING 日志

#### 错误处理与日志

- **FR-029**: 系统 MUST 在所有关键步骤记录结构化日志(JSON格式),包含 session_id, app_id, user_id, timestamp
- **FR-030**: 系统 MUST 在授权失败时,记录详细错误信息(错误码、错误消息、堆栈跟踪)到 ERROR 级别日志
- **FR-031**: 系统 MUST 在卡片中展示用户友好的错误提示,避免暴露技术细节(如错误码映射为中文说明)
- **FR-032**: 系统 MUST 对敏感信息脱敏(Token 仅显示前6位和后4位,其余用 * 代替)
- **FR-033**: 系统 MUST 提供标准化的异常类型:
  - `AuthenticationRequired`: 用户未授权
  - `TokenExpired`: Token 已过期
  - `PermissionDenied`: 权限不足
  - `WebSocketConnectionError`: WebSocket 连接失败

#### 安全与隐私

- **FR-034**: 系统 MUST 验证所有 WebSocket 事件的签名,使用飞书提供的签名验证机制
- **FR-035**: 系统 MUST 对每用户每分钟的授权请求限流(最多5次),防止恶意滥用
- **FR-036**: 系统 MUST 使用 HTTPS 传输所有与飞书的 API 调用
- **FR-037**: 系统 MUST 在日志中脱敏 user_access_token 和 app_secret
- **FR-038**: 系统 MUST 支持管理员手动撤销用户授权(删除 user_access_token)

#### 监控与可观测性

- **FR-039**: 系统 MUST 提供 Prometheus 指标:
  - `websocket_connection_status` (连接状态: 1=connected, 0=disconnected)
  - `websocket_reconnect_count` (重连次数累计)
  - `user_auth_sessions_total` (授权会话总数,按状态分组)
  - `user_auth_success_rate` (授权成功率,sliding window 5分钟)
  - `user_access_token_refresh_count` (Token 刷新次数)
- **FR-040**: 系统 MUST 在 WebSocket 连接断开超过5分钟时,触发告警通知
- **FR-041**: 系统 MUST 记录授权流程的关键步骤耗时(卡片发送、用户点击、Token 换取、存储)到 Tracing 系统

---

### Key Entities

#### UserAuthSession (授权会话)

已存在于数据库,位于 `user_auth_sessions` 表,包含字段:

- **session_id** (VARCHAR(64), PRIMARY KEY): 会话唯一标识 (UUID)
- **app_id** (VARCHAR(64)): 飞书应用 ID
- **user_id / open_id** (VARCHAR(64)): 用户标识
- **auth_method** (VARCHAR(32)): 认证方式,新增值 "websocket_card"
- **state** (VARCHAR(16)): 会话状态 (pending/completed/expired)
- **user_access_token** (VARCHAR(512), ENCRYPTED): 用户访问 Token (加密存储)
- **token_expires_at** (TIMESTAMP): Token 过期时间
- **created_at** (TIMESTAMP): 会话创建时间
- **expires_at** (TIMESTAMP): 会话过期时间 (created_at + 10分钟)
- **completed_at** (TIMESTAMP): 授权完成时间

关系: 一个用户可以有多个会话(历史记录),但同一时间只有一个 active 会话(state=completed 且 token 未过期)

#### WebSocketClient (WebSocket 客户端)

新增 Python 类,位于 `src/lark_service/events/websocket_client.py`:

- **app_id** (str): 飞书应用 ID
- **app_secret** (str): 飞书应用密钥
- **ws_client** (lark.ws.Client): lark-oapi SDK 的 WebSocket 客户端实例
- **event_handler** (EventDispatcherHandler): 事件分发器,注册各类事件处理函数
- **connection_status** (ConnectionStatus): 连接状态 (connected/disconnected/reconnecting)
- **reconnect_count** (int): 重连次数统计
- **last_heartbeat_at** (datetime): 最后一次心跳时间

行为方法:
- `connect()`: 建立 WebSocket 连接
- `disconnect()`: 断开连接
- `register_handler(event_type, handler_func)`: 注册事件处理器
- `start()`: 启动客户端(阻塞或异步)
- `is_connected()`: 检查连接状态

#### AuthSessionManager (授权会话管理器)

新增 Python 类,位于 `src/lark_service/auth/session_manager.py`:

- **db_session** (SQLAlchemy Session): 数据库会话
- **credential_pool** (CredentialPool): Token 管理池

行为方法:
- `create_session(app_id, user_id, auth_method)` → UserAuthSession: 创建新的授权会话
- `get_session(session_id)` → UserAuthSession | None: 根据 session_id 查询会话
- `complete_session(session_id, user_access_token, expires_at)` → None: 标记会话完成
- `get_active_token(app_id, user_id)` → str | None: 获取用户的有效 Token
- `refresh_token(app_id, user_id)` → str: 刷新 Token
- `revoke_token(app_id, user_id)` → None: 撤销用户授权
- `cleanup_expired_sessions()` → int: 清理过期会话,返回清理数量

#### CardAuthHandler (卡片授权处理器)

新增 Python 类,位于 `src/lark_service/auth/card_auth_handler.py`:

- **session_manager** (AuthSessionManager): 会话管理器
- **messaging_client** (MessagingClient): 消息客户端(用于发送卡片)

行为方法:
- `send_auth_card(app_id, user_id, session_id)` → str: 发送授权卡片,返回 message_id
- `handle_card_auth_event(event: P2CardActionTrigger)` → P2CardActionTriggerResponse: 处理授权按钮点击事件
- `_exchange_token(open_id, session_id)` → (user_access_token, expires_at): 换取 Token
- `_update_card_success(message_id, auth_time)` → None: 更新卡片为成功状态

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### 用户体验指标

- **SC-001**: 用户从收到授权卡片到完成授权的平均时间 ≤ 15秒
- **SC-002**: 授权成功率 ≥ 95% (成功完成授权的会话数 / 创建的授权会话总数)
- **SC-003**: 用户无需跳出飞书应用即可完成授权(100%飞书内闭环)
- **SC-004**: 用户在已授权的情况下,调用 aPaaS API 的响应时间 ≤ 500ms (99th percentile)

#### 系统可靠性指标

- **SC-005**: WebSocket 连接可用率 ≥ 99.9% (每月连接可用时间 / 总运行时间)
- **SC-006**: WebSocket 断线后自动重连成功率 ≥ 99% (成功重连次数 / 断线次数)
- **SC-007**: 系统支持至少 1000 个并发授权会话,无性能衰减
- **SC-008**: Token 刷新成功率 ≥ 98% (成功刷新次数 / 刷新请求总数)

#### 功能完整性指标

- **SC-009**: 所有需要 user_access_token 的 aPaaS API(AI 能力、工作流触发)都能自动使用 WebSocket 授权方案
- **SC-010**: 系统在 WebSocket 连接失败时,能在5分钟内触发告警通知,管理员可及时处理
- **SC-011**: 过期会话清理准确率 100% (清理的会话都是真正过期的,无误删)
- **SC-012**: 授权流程的每个关键步骤都有结构化日志记录,故障排查时能在2分钟内定位问题

#### 安全性指标

- **SC-013**: 100% 的 WebSocket 事件都经过签名验证,无一例外
- **SC-014**: 100% 的 user_access_token 都加密存储在数据库
- **SC-015**: 日志中 0% 的敏感信息(Token、密钥)以明文形式出现
- **SC-016**: 恶意授权请求(超过限流阈值)的拦截率 ≥ 99.9%

#### 开发效率指标

- **SC-017**: 开发人员添加新的需要 user_access_token 的 API 时,无需编写授权逻辑代码(自动集成)
- **SC-018**: aPaaS 客户端的代码改动 ≤ 50行(主要是调用 `_get_user_access_token` 方法)
- **SC-019**: 从 WebSocket 方案切换到 OAuth 备用方案的成本 ≤ 1天(通过配置切换,无需重构代码)

---

## Assumptions *(mandatory for this feature)*

### 技术假设

1. **lark-oapi SDK WebSocket 支持**: 假设 lark-oapi SDK (v1.5.2+) 的 `lark.ws.Client` 已稳定可用,支持事件注册和自动重连
2. **飞书 WebSocket 事件可靠性**: 假设飞书会缓存未送达的事件,重连后自动推送(官方文档保证机制)
3. **数据库已存在**: 假设 `user_auth_sessions` 表已通过 Alembic 迁移创建,无需重新建表
4. **Python 异步支持**: 假设项目已部分异步化(使用 asyncio),WebSocket 客户端可以异步运行

### 业务假设

1. **用户授权意愿**: 假设用户在理解授权用途后,愿意授权(授权成功率目标 95%)
2. **授权有效期**: 假设飞书 user_access_token 有效期为 7-30 天(根据飞书文档),足够长期使用
3. **Token 刷新机制**: 假设飞书提供 Token 刷新 API (如 `/open-apis/authen/v1/refresh_access_token`),无需每次重新授权
4. **授权范围固定**: 假设授权范围为 "读取和操作用户有权限的 aPaaS 数据空间",无需动态调整

### 运维假设

1. **网络稳定性**: 假设生产环境网络稳定,WebSocket 连接中断频率 < 1次/天
2. **数据库性能**: 假设 PostgreSQL 能承受每秒 100 次授权会话查询,无性能瓶颈
3. **监控系统可用**: 假设 Prometheus 和 Grafana 已部署,可以接收和展示 WebSocket 指标
4. **定时任务支持**: 假设系统支持 cron 定时任务或 APScheduler,用于定时清理过期会话

### 安全假设

1. **飞书签名机制**: 假设飞书 WebSocket 事件包含签名字段,可以通过验证签名确保事件来源可信
2. **数据库加密**: 假设 PostgreSQL 已启用 pg_crypto 扩展,支持字段级加密
3. **HTTPS 传输**: 假设所有与飞书的 API 调用都通过 HTTPS,无需额外配置 TLS
4. **权限控制**: 假设飞书应用已配置正确的权限范围,能够代用户获取 user_access_token

### 用户场景假设

1. **主要使用 aPaaS**: 假设 user_access_token 的主要用途是访问 aPaaS 功能,其他场景(如高级云文档权限)为次要
2. **单设备使用**: 假设大部分用户在单一设备(如企业电脑)上使用,多设备同时授权的情况较少(<10%)
3. **授权频率**: 假设用户平均每月授权1-2次,不会频繁授权(否则需要优化授权体验)
4. **权限稳定**: 假设用户在飞书侧的权限不会频繁变化,Token 获取后可以长期使用

---

## Dependencies *(mandatory for this feature)*

### 外部依赖

1. **lark-oapi SDK**: 依赖 lark-oapi (v1.5.2+) 的 `lark.ws.Client` 和 `EventDispatcherHandler`
2. **飞书 OpenAPI**: 依赖飞书以下 API:
   - `/open-apis/authen/v1/access_token`: 换取 user_access_token
   - `/open-apis/authen/v1/refresh_access_token`: 刷新 Token (如果支持)
   - `/open-apis/im/v1/messages/create`: 发送授权卡片
   - `/open-apis/im/v1/messages/:message_id`: 更新卡片内容
3. **飞书卡片搭建工具**: 需要在飞书开放平台创建授权卡片模板,获取 template_id

### 内部依赖

1. **Phase 2 (US1 Token 管理)**: 必须完成,复用 `user_auth_sessions` 表和 CredentialPool 的基础设施
2. **Phase 3 (US2 消息服务)**: 必须完成,使用 MessagingClient 发送授权卡片
3. **Phase 3 (US2 CardKit)**: 必须完成,使用 CardBuilder 构建授权卡片
4. **Phase 5 (US5 aPaaS)**: 已完成基础功能,本功能将增强 aPaaS 客户端支持 user_access_token

### 基础设施依赖

1. **PostgreSQL 数据库**: 必须运行且已应用 Alembic 迁移,包含 `user_auth_sessions` 表
2. **Prometheus + Grafana**: 可选,用于监控 WebSocket 连接状态和授权指标
3. **日志系统**: 必须配置结构化日志输出(JSON 格式),便于故障排查
4. **网络**: 必须允许与飞书服务器建立 WebSocket 连接(wss://),端口通常为 443

### 权限依赖

1. **飞书应用权限**: 必须在飞书开放平台配置以下权限:
   - `im:message:send_as_bot` (发送卡片消息)
   - `contact:user:read_id` (读取用户 open_id)
   - `authen:user.auth.app_ticket` (获取用户授权)
2. **数据库权限**: 应用用户必须有 `user_auth_sessions` 表的 SELECT, INSERT, UPDATE, DELETE 权限

---

## Out of Scope *(clarification)*

以下功能明确**不在本功能范围内**,避免范围蔓延:

### 不实现的功能

1. **OAuth 2.0 HTTP 回调方案**: 本功能仅实现 WebSocket 方案,OAuth 作为备用方案留待后续实现
2. **用户撤销授权主动通知**: 不实现用户在飞书侧撤销授权时的主动推送通知,仅在下次 API 调用时检测
3. **授权范围动态调整**: 不支持运行时动态调整授权范围,授权范围固定为 "aPaaS 数据空间读写"
4. **多应用授权聚合**: 不实现跨多个飞书应用的授权聚合,每个应用独立管理授权
5. **授权审计日志导出**: 不提供授权审计日志的导出功能(CSV/JSON),仅在数据库中存储
6. **授权卡片多语言**: 授权卡片仅支持中文,不支持多语言国际化

### 明确的边界

1. **仅支持飞书 aPaaS**: 本功能仅为 aPaaS 功能提供 user_access_token,不支持其他需要用户授权的场景(如云文档高级权限)
2. **仅支持 WebSocket 方式**: 本功能不处理 HTTP 回调方式的授权,WebSocket 是唯一支持的方式
3. **不处理应用级 Token**: 本功能仅管理 user_access_token,不影响现有的 app_access_token 和 tenant_access_token 管理
4. **不实现授权管理界面**: 不提供 Web UI 查看和管理授权,仅提供 API 和 CLI 工具

---

## Notes *(optional)*

### 实现建议

1. **参考 example.py**: 优先使用 lark-oapi SDK 的 `lark.ws.Client` 和 `EventDispatcherHandler`,避免重复造轮子
2. **复用现有组件**: 尽量复用 Phase 2 的 `CredentialPool` 和 Phase 3 的 `MessagingClient`,减少代码重复
3. **测试驱动开发**: 先写测试用例,后写实现代码,确保每个功能都有测试覆盖
4. **日志优先**: 在所有关键步骤添加结构化日志,便于故障排查

### 技术选型

1. **同步 vs 异步**: 建议使用异步实现(asyncio),与 WebSocket 客户端的异步特性匹配
2. **事件分发模式**: 使用 lark-oapi SDK 的 `EventDispatcherHandler.builder()` 模式,代码更清晰
3. **数据库 ORM**: 继续使用 SQLAlchemy 2.0,复用现有的 `UserAuthSession` 模型
4. **卡片构建**: 优先使用飞书卡片搭建工具创建模板,代码中仅传入 template_id 和变量

### 风险提示

1. **WebSocket 稳定性**: 如果 WebSocket 连接频繁断开,考虑增加重连间隔或降级到 HTTP 回调方案
2. **Token 刷新支持**: 如果飞书不支持 user_access_token 刷新,需要调整 SC-008 成功率目标
3. **并发授权压力**: 如果并发授权数超过1000,考虑增加数据库连接池大小或引入缓存
4. **授权卡片模板审核**: 飞书卡片模板需要审核,预留2-3天审核时间

### 后续优化方向

1. **多语言支持**: 在 v0.3.0 中支持授权卡片多语言(中文/英文)
2. **OAuth 备用方案**: 在 v0.3.0 中实现 HTTP 回调方式作为 WebSocket 的备用方案
3. **授权管理 UI**: 在 v0.4.0 中提供 Web UI 查看和管理授权会话
4. **授权范围细化**: 在 v0.4.0 中支持动态调整授权范围(只读/读写/管理)
