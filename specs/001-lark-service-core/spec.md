# Feature Specification: Lark Service 核心组件

**Feature Branch**: `001-lark-service-core`
**Created**: 2026-01-14
**Status**: Draft
**Input**: 为内部系统开发一个 Lark Service 企业自建应用核心组件，旨在通过封装飞书 OpenAPI 提供高度复用且透明的接入能力

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 透明 Token 管理与 API 调用 (Priority: P1)

内部服务开发者需要调用飞书 API 发送消息或查询用户信息时,希望无需关心 Token 的获取、刷新和过期问题。组件应该在后台自动维护所有必要的访问凭证,并在 API 调用失败时智能重试。

**Why this priority**: 这是核心价值主张,没有自动凭证管理,组件就失去了主要意义。所有其他功能都依赖于这一基础能力。

**Independent Test**: 可以通过发起一个简单的 API 调用(如获取用户信息)来独立测试,验证调用方无需提供任何 Token,且组件能在 Token 过期时自动刷新。

**Acceptance Scenarios**:

1. **Given** 内部服务首次启动且没有任何缓存的 Token, **When** 调用方请求发送一条飞书消息(传入 app_id), **Then** 组件自动获取对应 app_id 的 `app_access_token` 并成功发送消息,Token 存储到数据库,调用方无需感知 Token 存在
2. **Given** 组件已缓存的 `tenant_access_token` 距离过期还有 5 分钟, **When** 调用方发起新的 API 请求, **Then** 组件在使用旧 Token 的同时触发后台刷新(使用线程锁+进程锁防止并发重复刷新),确保下次调用使用新 Token
3. **Given** 组件服务重启, **When** 调用方再次发起 API 请求, **Then** 组件从数据库加载之前缓存的 Token(如未过期),无需重新获取即可正常调用
4. **Given** API 调用因网络波动返回超时错误, **When** 组件检测到可重试的失败, **Then** 组件按照指数退避策略自动重试最多 3 次,并在最终失败时返回清晰的错误信息
5. **Given** 飞书返回 Token 无效错误(如被管理员撤销), **When** 组件检测到凭证失效, **Then** 组件立即清除数据库缓存,尝试重新获取 Token,并在 2 次尝试后仍失败时返回不可重试错误
6. **Given** 需要使用 user_access_token 调用个人数据 API, **When** 用户首次使用, **Then** 组件发送认证卡片或消息链接,用户完成授权后组件获取 user_access_token 并存储到数据库

---

### User Story 2 - 消息服务封装 (Priority: P2)

内部服务需要通过飞书发送各种类型的通知(如工单提醒、审批通知),希望使用简单的接口发送文本消息、富文本消息、图片、文件和交互式卡片,而不需要研究飞书 API 的复杂参数结构。

**Why this priority**: 消息发送是飞书集成最常见的使用场景,是 MVP 的重要组成部分,但依赖于 P1 的凭证管理能力。

**Independent Test**: 可以通过调用 Messaging 模块的接口发送一条测试消息到指定用户或群组,验证消息成功送达且格式正确。

**Acceptance Scenarios**:

**文本和富文本消息**:
1. **Given** 工单系统需要发送文本通知, **When** 调用 `send_text_message(user_id, "您有新的工单待处理")`, **Then** 用户在飞书中收到文本消息,内容正确
2. **Given** 审批系统需要发送富文本通知包含链接和强调文本, **When** 调用 `send_rich_text_message()` 并传入富文本结构, **Then** 用户收到格式正确的富文本消息

**图片消息**:
1. **Given** 需要发送图片消息(如报表截图), **When** 调用 `upload_image(image_path)` 获取 image_key 后发送图片消息, **Then** 用户收到图片消息,图片正常显示
2. **Given** 需要直接发送本地图片, **When** 调用 `send_image_message(user_id, image_path)` 自动处理上传, **Then** 用户收到图片消息

**文件消息**:
1. **Given** 需要发送文件消息(如文档、视频), **When** 调用 `upload_file(file_path)` 获取 file_key 后发送文件消息, **Then** 用户收到文件消息,可以下载
2. **Given** 需要直接发送本地文件, **When** 调用 `send_file_message(user_id, file_path)` 自动处理上传, **Then** 用户收到文件消息

**交互式卡片和批量发送**:
1. **Given** 需要发送交互式卡片让用户快速审批, **When** 调用 `send_interactive_card()` 并传入卡片配置和回调处理函数, **Then** 用户收到可交互的卡片消息
2. **Given** 用户点击卡片按钮, **When** 飞书服务器发送回调请求到组件, **Then** 组件验证签名后将回调事件发送到消息队列,注册的处理函数异步处理回调逻辑
3. **Given** 回调处理函数需要更新卡片状态, **When** 处理函数返回更新指令, **Then** 组件自动更新原卡片消息,用户看到状态变化(如"审批中"→"已通过")
4. **Given** 需要向多个用户批量发送相同消息, **When** 调用批量发送接口并传入用户列表, **Then** 所有用户都收到消息,且有明确的成功/失败状态反馈

**验证方式**:
- **消息成功送达验证**: 通过 API 返回的 `message_id` 和飞书客户端接收确认来验证,组件记录发送日志包含 message_id、receiver_id、发送时间戳
- **卡片交互回调验证**: 端到端测试流程包括:发送卡片 → 模拟用户点击 → 验证回调请求到达 → 验证签名通过 → 验证消息队列接收事件 → 验证回调处理函数执行 → 验证卡片状态更新

---

### User Story 3 - 云文档服务封装 (Priority: P3)

内部服务需要操作飞书云文档(包括 Doc 文档、Sheet 电子表格、多维表格等),希望使用简单的接口进行文档的创建、读取、更新操作,以及对多维表格数据的 CRUD 操作。

**Why this priority**: 云文档集成扩展了组件的应用场景,但不是所有内部服务都需要,优先级低于消息功能。

**Independent Test**: 可以通过创建一个测试文档、写入内容、读取内容并验证一致性来独立测试。对于多维表格,可以创建、读取、更新、删除记录来验证。

**Acceptance Scenarios**:

**Doc 文档操作**:
1. **Given** 报表系统需要生成周报, **When** 调用 `create_document(title="周报")`, **Then** 在飞书中创建一个新文档,返回文档 ID
2. **Given** 需要向文档写入结构化内容, **When** 调用 `append_content(doc_id, content_blocks)`, **Then** 文档中追加指定内容,格式正确
3. **Given** 需要读取文档内容进行分析, **When** 调用 `get_document_content(doc_id)`, **Then** 返回文档的完整内容结构
4. **Given** 需要更新文档的特定段落, **When** 调用 `update_block(doc_id, block_id, new_content)`, **Then** 文档中的指定段落被更新

**文档素材上传和下载**:
1. **Given** 需要在文档中插入图片, **When** 调用 `upload_doc_media(doc_id, image_path, media_type="image")`, **Then** 图片上传成功,返回 file_token 可用于文档内引用
2. **Given** 需要在文档中插入附件, **When** 调用 `upload_doc_media(doc_id, file_path, media_type="file")`, **Then** 文件上传成功,可在文档中引用
3. **Given** 需要下载文档中的附件, **When** 调用 `download_doc_media(file_token, save_path)`, **Then** 文件下载到本地指定路径

**多维表格操作**:
1. **Given** 需要向多维表格添加新记录, **When** 调用 `create_record(table_id, fields)`, **Then** 在表格中创建新记录,返回记录 ID
2. **Given** 需要查询表格中的记录, **When** 调用 `query_records(table_id, filters)`, **Then** 返回符合条件的记录列表
3. **Given** 需要更新表格中的记录, **When** 调用 `update_record(table_id, record_id, fields)`, **Then** 记录被更新,返回更新后的数据
4. **Given** 需要删除表格中的记录, **When** 调用 `delete_record(table_id, record_id)`, **Then** 记录被删除,返回成功状态

**Sheet 电子表格操作**:
1. **Given** 需要读取 Sheet 中的数据, **When** 调用 `get_sheet_data(sheet_id, range)`, **Then** 返回指定范围的单元格数据
2. **Given** 需要写入数据到 Sheet, **When** 调用 `update_sheet_data(sheet_id, range, values)`, **Then** Sheet 中的数据被更新

---

### User Story 4 - 通讯录服务封装 (Priority: P3)

内部服务需要查询用户信息或组织架构,获取不同类型的用户标识(open_id、user_id、union_id)和群组标识(chat_id)以支撑消息发送等服务应用。同时需要将人员信息存储到数据库以便快速查询,当未查询到库中的人员信息时,使用 Contact 模块的查询能力从飞书获取并更新本地缓存。

**Why this priority**: 通讯录查询是许多集成场景的辅助功能,本地缓存可提升查询性能并减少API调用,但不是核心使用场景,优先级较低。

**Independent Test**: 可以通过邮箱查询用户信息并验证返回包含完整的 open_id、user_id、union_id,以及验证本地缓存命中和缓存未命中时的自动刷新逻辑。

**Acceptance Scenarios**:

1. **Given** 需要根据用户邮箱发送消息, **When** 调用 `get_user_by_email(email, app_id)`, **Then** 返回用户的 open_id、user_id、union_id 和基本信息(name、avatar、department),并存储到 PostgreSQL 数据库
2. **Given** 数据库中已缓存用户信息且未过期(TTL<24小时), **When** 再次查询相同用户, **Then** 直接从数据库返回,无需调用飞书API
3. **Given** 数据库中用户信息已过期(TTL>24小时), **When** 查询该用户, **Then** 从飞书API刷新数据并更新数据库缓存
4. **Given** 需要查询群组ID以发送群消息, **When** 调用 `get_chat_by_name(chat_name)`, **Then** 返回 chat_id 和群组基本信息
5. **Given** 需要获取某部门的所有成员, **When** 调用 `get_department_users(dept_id)`, **Then** 返回部门成员列表及其完整ID信息,并批量更新数据库缓存
6. **Given** 不同应用(app_id)查询相同用户, **When** 分别调用 `get_user_by_email()` 传入不同 app_id, **Then** 返回相同的 union_id 但不同的 open_id,并按 app_id 隔离存储

---

### User Story 5 - aPaaS 平台集成 (Priority: P4)

内部服务需要与飞书 aPaaS 平台集成,对 AI 平台的数据空间(Workspace)中的表格进行 CRUD 操作,实现外部数据对接数据空间的能力。此外还需要支持调用 AI 能力和触发自动化工作流。

**Why this priority**: aPaaS 平台集成是高级功能,主要服务于需要 AI 能力、数据空间集成和自动化流程的场景,使用场景相对有限,适合作为后期扩展功能。

**Independent Test**: 可以通过查询工作空间下的数据表列表、对表格记录进行读写操作来独立验证集成是否正常工作。需要 user_access_token 权限。

**Acceptance Scenarios**:

**数据空间表格操作**:
1. **Given** 需要查询工作空间下的数据表列表, **When** 调用 `list_workspace_tables(workspace_id, user_access_token)`, **Then** 返回数据表列表及其元信息(表格ID、名称、字段定义)
2. **Given** 需要读取数据空间表格的记录, **When** 调用 `query_table_records(table_id, query_conditions, user_access_token)`, **Then** 返回符合条件的记录列表
3. **Given** 需要更新数据空间表格的记录, **When** 调用 `update_table_record(table_id, record_id, update_data, user_access_token)`, **Then** 记录被成功更新并返回最新数据
4. **Given** 需要删除数据空间表格的记录, **When** 调用 `delete_table_record(table_id, record_id, user_access_token)`, **Then** 记录被成功删除并返回确认信息
5. **Given** user_access_token 权限不足, **When** 尝试访问工作空间数据表, **Then** 返回明确的权限不足错误和所需权限说明

**AI 能力和工作流**:
1. **Given** 需要调用飞书 AI 能力进行文本分析, **When** 调用 `invoke_ai_capability(capability_id, input_data, user_access_token)`, **Then** 返回 AI 处理结果
2. **Given** 需要触发飞书自动化流程, **When** 调用 `trigger_workflow(workflow_id, parameters, user_access_token)`, **Then** 工作流被触发,返回执行状态
3. **Given** 需要查询自动化流程的执行状态, **When** 调用 `get_workflow_status(execution_id, user_access_token)`, **Then** 返回流程的当前执行状态和结果

---

### Edge Cases

- **凭证获取失败**: 当飞书 API 返回凭证获取失败(如 App ID/Secret 错误)时,组件应返回明确的配置错误信息,而不是无限重试
- **并发调用竞争**: 当多个并发请求同时触发 Token 刷新时,组件应确保只发起一次刷新请求,其他请求等待刷新完成
- **API 限流**: 当飞书 API 返回限流错误时,组件应识别错误码并延迟重试,避免加剧限流
- **Token 提前过期**: 飞书返回的 Token 实际过期时间可能早于声明的过期时间,组件应在收到 Token 失效错误时立即刷新
- **网络分区**: 当组件与飞书 API 之间网络完全不可达时,组件应在合理的超时时间内返回错误,不阻塞调用方
- **恶意输入**: 当调用方传入超大消息内容或恶意构造的参数时,组件应在发送前进行参数校验,返回清晰的参数错误
- **飞书错误码变更**: 当飞书 API 返回未知的错误码时,组件应能够优雅降级,返回通用错误信息而不是崩溃
- **多应用场景**: 当企业使用多个飞书自建应用时,组件应按 app_id 隔离凭证,避免不同应用的 Token 混用
- **数据库连接失败**: 当 Token 数据库读取失败时,组件应视为缓存未命中,直接请求新 Token 并重试写入数据库;如数据库持续不可用,每次调用都重新请求 Token(记录 ERROR 日志提示修复数据库)
- **Token 数据库损坏**: 当读取到的 Token 数据格式错误或解密失败时,组件应清除损坏记录,重新获取 Token 并覆盖写入
- **消息队列故障**: 当消息队列不可用时,卡片回调应同步处理或返回明确的服务降级错误,避免回调丢失
- **并发刷新死锁**: 当多进程同时尝试获取锁时,组件应设置合理的锁超时时间(如 30 秒),避免永久阻塞
- **用户认证超时**: 当用户未在规定时间内(如 10 分钟)完成 user_access_token 认证时,组件应清理认证会话并提示重新发起
- **文件大小超限**: 当上传的图片超过 10MB 或文件超过 30MB 时,组件应在上传前检测并返回清晰的大小限制错误
- **文件类型不支持**: 当上传不支持的文件类型时,组件应返回支持的文件类型列表和错误提示
- **空文件上传**: 当尝试上传空文件时,组件应拒绝上传并返回明确的错误信息
- **文件下载失败**: 当文档素材的 file_token 无效或文件已被删除时,组件应返回友好的错误信息而不是崩溃
- **用户邮箱/手机号不存在**: 当查询的邮箱或手机号在飞书中不存在时,组件应返回空结果并记录INFO日志,不应抛出异常
- **通讯录权限不足**: 当应用权限不足无法访问用户详细信息时,组件应返回明确的权限不足错误和所需权限范围说明
- **部门已删除**: 当查询已被删除的部门成员列表时,组件应返回部门不存在错误,而不是返回空列表
- **用户数据同步延迟**: 当飞书侧用户信息已更新但本地缓存未刷新时,组件应在缓存TTL过期后自动从飞书拉取最新数据
- **群组不存在**: 当查询的 chat_id 不存在或群组已解散时,组件应返回明确的群组不存在错误
- **跨应用ID隔离**: 当不同 app_id 查询相同用户时,组件应正确返回不同的 open_id 但相同的 union_id,避免ID混用
- **数据空间不存在**: 当查询的工作空间或数据表不存在时,组件应返回明确的资源不存在错误和可用工作空间列表建议
- **数据空间权限不足**: 当 user_access_token 权限不足无法访问数据空间时,组件应返回权限不足错误和所需权限说明
- **数据空间并发写冲突**: 当多个请求同时更新同一记录导致版本冲突时,组件应返回冲突错误并建议重新读取后再更新
- **数据空间配额已满**: 当工作空间存储配额已满无法创建新记录时,组件应返回配额超限错误和清理建议
- **AI 调用超时**: 当 AI 能力调用超过合理时间(如 30 秒)未返回时,组件应主动超时并返回超时错误
- **工作流触发失败**: 当工作流不存在或参数错误导致触发失败时,组件应返回明确的失败原因和参数校验信息

## Requirements *(mandatory)*

### Functional Requirements

#### 应用配置管理

- **FR-001**: 组件 MUST 提供应用配置管理功能,支持动态增删改查飞书应用配置,无需重启服务
- **FR-002**: 组件 MUST 使用 SQLite 存储应用配置(App ID、App Secret、应用名称、描述等),支持轻量级配置管理
- **FR-003**: 组件 MUST 加密存储应用 Secret,使用对称加密算法(如 Fernet),加密密钥从环境变量读取
- **FR-004**: 组件 MUST 支持应用状态管理,包含启用(active)和禁用(disabled)两种状态,禁用的应用拒绝 Token 获取
- **FR-005**: 组件 MUST 记录应用配置的审计信息,包含创建者、创建时间、更新时间,支持配置变更追踪

#### 应用配置管理 CLI 工具

- **FR-005.1**: 组件 MUST 提供命令行工具 `lark-service-cli` 用于管理应用配置,支持通过 `python -m lark_service.cli` 或安装后的 `lark-service-cli` 命令调用
- **FR-005.2**: CLI 工具 MUST 支持 `app add` 命令添加应用配置,必需参数包括 `--app-id`、`--app-secret`、`--name`,可选参数包括 `--description`
- **FR-005.3**: CLI 工具 MUST 支持 `app list` 命令列出所有应用,以表格形式展示 app_id、name、status、created_at,支持 `--json` 选项输出 JSON 格式
- **FR-005.4**: CLI 工具 MUST 支持 `app show` 命令显示应用详情,必需参数为 `--app-id`,app_secret 必须脱敏显示(如 `secret_****`),支持 `--json` 选项
- **FR-005.5**: CLI 工具 MUST 支持 `app update` 命令更新应用配置,必需参数为 `--app-id`,支持部分字段更新(name、description、app_secret)
- **FR-005.6**: CLI 工具 MUST 支持 `app delete` 命令删除应用配置,必需参数为 `--app-id`,需要用户交互式确认或使用 `--force` 选项跳过确认
- **FR-005.7**: CLI 工具 MUST 支持 `app enable` 和 `app disable` 命令启用或禁用应用,必需参数为 `--app-id`
- **FR-005.8**: CLI 工具 MUST 在操作失败时返回非零退出码(参数错误返回 1,数据库错误返回 2,权限错误返回 3),并输出清晰的错误信息和修复建议
- **FR-005.9**: CLI 工具 MUST 在所有命令中支持 `--help` 选项显示详细帮助信息,包含参数说明、使用示例和注意事项

#### 凭证管理

- **FR-006**: 组件 MUST 支持自动获取和维护 `app_access_token`、`tenant_access_token` 和 `user_access_token` 三种类型的访问凭证
- **FR-007**: 组件 MUST 实现凭证的主动失效检测,在 Token 到期前 10% 的时间窗口内自动触发刷新(例如 7200 秒过期的 Token 在剩余 720 秒时刷新)
- **FR-008**: 组件 MUST 支持并发安全的 Token 刷新,使用线程锁(threading.Lock)和进程锁(multiprocessing.Lock)组合,确保单机多进程部署下不会触发重复刷新
- **FR-009**: 组件 MUST 在凭证获取失败时明确区分可重试错误(如网络超时)和不可重试错误(如配置错误),并采取相应策略
- **FR-010**: 组件 MUST 从应用配置管理模块动态加载应用 Secret,严禁硬编码敏感配置
- **FR-011**: 组件 MUST 支持多应用场景,调用时传入 app_id 参数,组件内部按 app_id 隔离 Token 存储和刷新
- **FR-012**: 组件 MUST 使用 PostgreSQL 持久化存储 Token,支持服务重启后恢复凭证,避免频繁重新获取
- **FR-013**: 组件 MUST 实现 Token 懒加载机制,启动时仅验证配置有效性,Token 在首次使用时按需获取,避免启动阻塞
- **FR-014**: 组件 MUST 支持 user_access_token 的用户首次认证流程,提供飞书卡片认证和消息链接认证两种方式

#### API 调用与重试

- **FR-015**: 组件 MUST 封装所有飞书 API 调用,调用方无需直接操作 Token
- **FR-016**: 组件 MUST 实现智能重试机制,针对网络超时、限流、Token 失效等错误自动重试,最大重试次数为 3 次
- **FR-017**: 组件 MUST 使用指数退避策略进行重试,初始延迟 1 秒,每次重试延迟翻倍(1s, 2s, 4s)
- **FR-018**: 组件 MUST 识别飞书 API 限流错误码,在遇到限流时延迟更长时间再重试(如 30 秒)
  - **FR-018.1**: 限流错误(HTTP 429)MUST 检查响应头 `Retry-After`,如果存在则按其值延迟,否则默认延迟 30 秒
  - **FR-018.2**: 限流错误响应 MUST 包含 error.details 字段,说明限流原因和建议的重试时间
- **FR-019**: 组件 MUST 为每个 API 请求生成唯一的请求 ID,用于日志追踪和问题排查

#### 响应标准化

- **FR-020**: 组件暴露的所有接口 MUST 返回标准化响应结构,包含业务状态码、请求 ID、数据负载和错误信息
- **FR-021**: 组件 MUST 将飞书原始错误码映射为语义化的内部错误类型(如 `TokenExpired`、`RateLimited`、`InvalidParameter`)
- **FR-022**: 组件 MUST 在错误响应中包含足够的上下文信息,帮助调用方快速定位问题(如哪个参数错误、建议的修复方式)
  - **FR-022.1**: 参数验证错误 MUST 返回 HTTP 400,错误响应包含:具体参数名、错误原因、正确格式示例
  - **FR-022.2**: content 为空字符串时 MUST 返回错误码 40002,错误消息 "Message content cannot be empty"
  - **FR-022.3**: receiver_id 不存在时 MUST 返回错误码 40003,错误消息 "Receiver not found: {receiver_id}"
  - **FR-022.4**: 用户无权限接收消息时 MUST 返回错误码 40301,错误消息 "Permission denied: user cannot receive messages"
  - **FR-022.5**: 使用无效 image_key/file_key 时 MUST 返回错误码 40004,错误消息 "Invalid media key: {key} (expired or not found)"

#### 消息服务(Messaging 模块) - 基于飞书消息 API (IM v1)

**重要说明**: Messaging 模块基于飞书**消息 API (IM v1)** 实现,官方文档: https://open.feishu.cn/document/server-docs/im-v1/introduction

**基础消息**:
- **FR-023**: Messaging 模块 MUST 使用飞书消息 API 支持发送纯文本消息(`msg_type: text`)到指定用户或群组
- **FR-024**: Messaging 模块 MUST 使用飞书消息 API 支持发送富文本消息(`msg_type: post`),包含加粗、斜体、链接、@提及等格式
  - **FR-024.1**: 富文本格式规范 MUST 支持以下元素:加粗(`**text**`)、斜体(`*text*`)、删除线(`~~text~~`)、链接(`[text](url)`)、@提及用户(`<at user_id="xxx">`)、@所有人(`<at user_id="all">`)
  - **FR-024.2**: 富文本 MUST 支持多语言内容,使用 `zh_cn`、`en_us` 等语言标识
- **FR-025**: Messaging 模块 MUST 使用飞书消息 API 支持发送交互式卡片消息(`msg_type: interactive`),卡片内容由 CardKit 模块构建
- **FR-026**: Messaging 模块 MUST 支持批量发送消息,并返回每个接收者的发送结果
  - **FR-026.1**: 批量发送 MUST 采用"继续策略",即使部分接收者失败也继续发送其余消息,不回滚已成功的发送
  - **FR-026.2**: 批量响应 MUST 返回结构化结果,包含 total(总数)、success(成功数)、failed(失败数)和 results 数组
  - **FR-026.3**: results 数组中每个元素 MUST 包含 receiver_id、status(success/failed)、message_id(成功时)、error(失败时包含错误码和错误消息)
- **FR-027**: Messaging 模块 MUST 使用飞书消息 API 支持消息撤回(`DELETE /im/v1/messages/{message_id}`)、编辑(`PATCH`仅文本消息)、回复等消息生命周期管理操作
  - **FR-027.1**: 消息撤回时间限制为发送后 24 小时内,超时返回明确错误
  - **FR-027.2**: 消息编辑仅支持文本消息(`msg_type: text`),时间限制为发送后 24 小时内
  - **FR-027.3**: 消息回复嵌套层级限制为 3 层,超过限制返回参数错误

**图片消息**:
- **FR-028**: Messaging 模块 MUST 使用飞书消息 API 支持上传图片(JPEG、PNG、WEBP、GIF、TIFF、BMP、ICO),图片大小限制 10MB
  - **FR-028.1**: 文件类型验证 MUST 通过文件扩展名和 MIME type 双重检查,优先检查 MIME type
  - **FR-028.2**: image_key 有效期为 30 天,组件 SHOULD 记录上传时间,过期的 image_key 重新上传
  - **FR-028.3**: 图片上传失败时 MUST 自动重试,遵循通用重试策略(FR-016/FR-017):最大 3 次,指数退避 1s/2s/4s
- **FR-029**: Messaging 模块 MUST 使用飞书消息 API 支持发送图片消息(`msg_type: image`),接收 image_key 或本地图片路径
- **FR-030**: Messaging 模块 MUST 提供便捷方法 `send_image_message()` 自动处理图片上传和发送流程

**文件消息**:
- **FR-031**: Messaging 模块 MUST 使用飞书消息 API 支持上传文件(视频、音频、常见文件类型),文件大小限制 30MB,禁止上传空文件
  - **FR-031.1**: file_key 有效期为 30 天,组件 SHOULD 记录上传时间,过期的 file_key 重新上传
  - **FR-031.2**: 视频文件 MUST 支持格式:MP4、AVI、MOV、WMV,大小限制 30MB
  - **FR-031.3**: 音频文件 MUST 支持格式:MP3、WAV、AAC、OGG,大小限制 30MB
  - **FR-031.4**: 文档文件 MUST 支持格式:PDF、DOC、DOCX、XLS、XLSX、PPT、PPTX、TXT,大小限制 30MB
- **FR-032**: Messaging 模块 MUST 使用飞书消息 API 支持发送文件消息(`msg_type: file`),接收 file_key 或本地文件路径
- **FR-033**: Messaging 模块 MUST 提供便捷方法 `send_file_message()` 自动处理文件上传和发送流程

#### 卡片服务(CardKit 模块) - 基于飞书卡片 API (CardKit v1)

**重要说明**: CardKit 模块基于飞书**卡片 API (CardKit v1)** 实现,官方文档: https://open.feishu.cn/document/cardkit-v1/feishu-card-resource-overview

**卡片构建**:
- **FR-034**: CardKit 模块 MUST 提供卡片构建器(CardBuilder),支持通过编程方式构建飞书交互式卡片 JSON 结构
- **FR-035**: CardKit 模块 MUST 提供常用卡片模板,包括审批卡片(approval)、通知卡片(notification)、表单卡片(form)
- **FR-036**: CardKit 模块 MUST 支持卡片组件:header(标题)、div(文本块)、action(按钮)、form(表单输入)、hr(分割线)、image(图片)、markdown(富文本)
- **FR-037**: CardKit 模块 MUST 验证构建的卡片 JSON 结构符合飞书卡片规范,在发送前进行 schema 验证

**卡片交互回调**:
- **FR-038**: CardKit 模块 MUST 提供回调处理器,统一接收飞书卡片交互回调(`card.action.trigger` 事件)
- **FR-039**: CardKit 模块 MUST 验证飞书回调请求签名,使用 Encrypt Key 防止伪造请求和重放攻击
- **FR-040**: CardKit 模块 MUST 处理 URL 验证回调(`url_verification`),在首次配置回调地址时响应 challenge
- **FR-041**: CardKit 模块 MUST 将验证通过的回调事件异步路由到 RabbitMQ 消息队列,解耦回调处理
  - **FR-041.1**: 回调处理超时限制为 5 秒,超时返回 HTTP 200 但记录 WARNING 日志
  - **FR-041.2**: 回调处理函数抛出异常时 MUST 捕获异常,返回 HTTP 200 避免飞书重试,记录 ERROR 日志包含完整堆栈信息
  - **FR-041.3**: 消息队列发送失败时 MUST 重试 3 次(间隔 1s、2s、4s),最终失败则同步处理回调并记录 ERROR 日志
- **FR-042**: CardKit 模块 MUST 支持注册回调处理函数,根据 action.value 或 card_id 路由到对应的业务处理逻辑

**卡片更新**:
- **FR-043**: CardKit 模块 MUST 支持主动更新已发送的卡片内容,通过消息 API 的 `PATCH /im/v1/messages/{message_id}` 接口
- **FR-044**: CardKit 模块 MUST 支持在回调响应中返回新的卡片 JSON,飞书自动更新原卡片(如"待审批"→"已通过")
- **FR-045**: CardKit 模块 MUST 提供构建回调响应的辅助方法 `build_update_response()`,简化卡片更新逻辑

**MVP 范围说明**:
- **FR-045.1**: Phase 3 MVP 包含基础卡片功能:header、div、action、markdown 组件,审批和通知卡片模板
- **FR-045.2**: 高级功能延后到后续版本:form 表单输入组件、表单卡片模板、多步骤卡片、卡片分享、卡片搜索

#### 云文档服务(CloudDoc 模块)

**文档 URL 解析与访问** ⭐:
- **FR-045**: CloudDoc 模块 MUST 提供统一的文档 URL 解析工具(DocumentUrlResolver),自动识别知识库(Wiki)和云空间(Drive)文档
- **FR-045.1**: DocumentUrlResolver MUST 支持通过正则表达式直接提取云空间文档的 doc_token(文档、表格、多维表格、文件)
- **FR-045.2**: DocumentUrlResolver MUST 支持调用 Wiki API 获取知识库文档的 obj_token(实际可用的文档 token)
- **FR-045.3**: DocumentUrlResolver MUST 自动处理知识库快捷方式(shortcut),递归获取原始节点的 obj_token
- **FR-045.4**: DocumentUrlResolver MUST 返回统一的 DocumentInfo 对象,包含 doc_type、doc_token、source_type 等信息
- **FR-045.5**: CloudDoc 模块 MUST 提供统一的文档访问客户端(UnifiedDocClient),支持通过 URL 直接访问文档,无需手动判断文档来源

**Doc 文档**:
- **FR-046**: CloudDoc 模块 MUST 支持创建新的 Doc 云文档
- **FR-047**: CloudDoc 模块 MUST 支持向 Doc 文档追加内容块(文本、标题、图片、表格等)
- **FR-047.1**: CloudDoc 模块 MUST 定义明确的 ContentBlock 数据结构,支持 7 种内容类型(paragraph、heading、image、table、code、list、divider)
- **FR-047.2**: CloudDoc 模块 MUST 限制单次追加最大 100 个 block,单个 block 最大 100 KB
- **FR-048**: CloudDoc 模块 MUST 支持读取 Doc 文档的完整内容结构
- **FR-049**: CloudDoc 模块 MUST 支持更新 Doc 文档中指定内容块的内容
- **FR-050**: CloudDoc 模块 MUST 支持文档权限管理,包含授予/撤销用户权限(可阅读、可编辑、可评论、可管理)和权限查询
- **FR-050.1**: CloudDoc 模块 MUST 定义 4 种权限类型(read、write、comment、manage),权限层级为 manage > write > comment > read

**文档素材管理**:
- **FR-051**: CloudDoc 模块 MUST 支持上传素材文件到指定云文档(图片、视频、文件等)
- **FR-051.1**: CloudDoc 模块 MUST 限制图片上传最大 10 MB,支持 6 种格式(jpg、jpeg、png、gif、bmp、webp),最大尺寸 4096×4096
- **FR-051.2**: CloudDoc 模块 MUST 限制文件上传最大 30 MB,支持 9 种格式(pdf、doc、docx、xls、xlsx、ppt、pptx、zip、rar、7z)
- **FR-052**: CloudDoc 模块 MUST 支持下载云文档中的素材文件到本地
- **FR-053**: CloudDoc 模块 MUST 返回上传后的 file_token 供文档内容块引用

**多维表格(Bitable)**:
- **FR-054**: CloudDoc 模块 MUST 支持在多维表格中创建新记录
- **FR-055**: CloudDoc 模块 MUST 支持根据条件查询多维表格记录
- **FR-055.1**: CloudDoc 模块 MUST 定义 QueryFilter 数据结构,支持 10 种过滤操作符(is、is_not、contains、not_contains、gt、lt、gte、lte、is_empty、is_not_empty)
- **FR-055.2**: CloudDoc 模块 MUST 支持 and/or 逻辑连接符,最多 20 个过滤条件
- **FR-055.3**: CloudDoc 模块 MUST 支持分页查询,单次最多返回 500 条记录
- **FR-056**: CloudDoc 模块 MUST 支持更新多维表格中的现有记录
- **FR-057**: CloudDoc 模块 MUST 支持删除多维表格中的记录
- **FR-058**: CloudDoc 模块 MUST 支持批量操作多维表格记录(批量创建、更新、删除)
- **FR-058.1**: CloudDoc 模块 MUST 限制批量创建/更新/删除最大 500 条记录

**Sheet 电子表格**:
- **FR-059**: CloudDoc 模块 MUST 支持读取 Sheet 指定范围的单元格数据
- **FR-059.1**: CloudDoc 模块 MUST 支持 4 种范围格式(单元格范围 A1:B10、整列 A:C、整行 3:5、单个单元格 A1)
- **FR-059.2**: CloudDoc 模块 MUST 限制单次读取最大 100,000 个单元格
- **FR-060**: CloudDoc 模块 MUST 支持更新 Sheet 指定范围的单元格数据
- **FR-060.1**: CloudDoc 模块 MUST 限制单次更新最大 10,000 个单元格
- **FR-061**: CloudDoc 模块 MUST 支持 Sheet 的格式化操作,包含设置单元格样式(字体、颜色、对齐方式)、合并/拆分单元格、设置列宽行高、冻结窗格
- **FR-061.1**: CloudDoc 模块 MUST 限制单次合并最大 1,000 个单元格,冻结窗格最大 100 行/100 列

**知识库(Wiki)集成** ⭐:
- **FR-061.2**: CloudDoc 模块 MUST 支持获取知识库节点信息,返回 obj_token(实际的文档 token)
- **FR-061.3**: CloudDoc 模块 MUST 支持获取知识库节点列表,支持分页(最大 50 条/页)
- **FR-061.4**: CloudDoc 模块 MUST 支持获取知识空间列表,返回用户有权限访问的空间
- **FR-061.5**: CloudDoc 模块 MUST 缓存 node_token → obj_token 的映射,TTL 为 1 小时,减少 Wiki API 调用

#### 通讯录服务(Contact 模块)

**用户查询与缓存**:
- **FR-062**: Contact 模块 MUST 支持根据邮箱、手机号查询用户的 open_id、user_id、union_id 三种标识
- **FR-062.1**: Contact 模块 MUST 明确 3 种用户 ID 的作用域和使用场景:open_id(应用内)、user_id(租户内)、union_id(跨租户)
- **FR-062.2**: Contact 模块 MUST 使用 union_id 作为缓存主键,确保跨应用的用户唯一性
- **FR-063**: Contact 模块 MUST 支持获取用户的详细信息(姓名、头像、部门、职位、员工工号等)
- **FR-064**: Contact 模块 MUST 将查询到的用户信息存储到 PostgreSQL 数据库,按 app_id 隔离存储(不同应用的 open_id 不同)
- **FR-064.1**: Contact 模块 MUST 使用缓存 key 格式 `user:{app_id}:{union_id}`,确保应用级隔离
- **FR-065**: Contact 模块 MUST 实现用户信息缓存机制,TTL 为 24 小时,缓存命中时直接返回数据库数据
- **FR-065.1**: Contact 模块 MUST 在缓存命中时响应时间 < 100 ms,缓存未命中时 < 2 秒
- **FR-065.2**: Contact 模块 MUST 实现缓存命中率目标 > 80%
- **FR-066**: Contact 模块 MUST 在缓存过期或未命中时,自动从飞书 API 刷新数据并更新数据库
- **FR-066.1**: Contact 模块 MUST 在 API 调用失败时,如果有过期缓存则返回过期缓存,避免服务不可用
- **FR-066.2**: Contact 模块 MUST 支持主动失效缓存(用户信息更新时)和强制失效(管理员操作)
- **FR-066.3**: Contact 模块 MUST 实现 LRU 容量淘汰策略,最大缓存 100,000 条记录

**批量操作**:
- **FR-066.4**: Contact 模块 MUST 支持批量查询用户,最大 200 个用户/次
- **FR-066.5**: Contact 模块 MUST 支持批量更新缓存,最大 1,000 条记录/次

**群组查询**:
- **FR-067**: Contact 模块 MUST 支持根据群组名称查询 chat_id
- **FR-068**: Contact 模块 MUST 支持获取群组的详细信息(群名称、群主、成员数量等)

**组织架构查询**:
- **FR-069**: Contact 模块 MUST 支持获取部门的成员列表,并批量更新数据库缓存
- **FR-069.1**: Contact 模块 MUST 限制单个部门最大 1,000 个用户
- **FR-070**: Contact 模块 MUST 支持查询组织架构树(部门层级关系)

#### aPaaS 平台服务(aPaaS 模块)

**数据空间表格操作**:
- **FR-071**: aPaaS 模块 MUST 支持查询工作空间(Workspace)下的数据表列表,返回表格ID、名称、字段定义
- **FR-072**: aPaaS 模块 MUST 支持根据条件查询数据空间表格的记录(支持过滤、排序、分页)
- **FR-073**: aPaaS 模块 MUST 支持更新数据空间表格的记录,支持部分字段更新
- **FR-074**: aPaaS 模块 MUST 支持删除数据空间表格的记录
- **FR-075**: aPaaS 模块 MUST 使用 user_access_token 进行数据空间操作,并验证权限有效性
- **FR-076**: aPaaS 模块 MUST 处理并发写冲突,返回明确的冲突错误和重试建议

**AI 能力与工作流**:
- **FR-077**: aPaaS 模块 MUST 支持调用飞书 AI 能力(如文本分析、智能问答等),需要 user_access_token
- **FR-078**: aPaaS 模块 MUST 支持触发飞书自动化工作流,传入参数并返回执行ID
- **FR-079**: aPaaS 模块 MUST 支持查询自动化工作流的执行状态和结果
- **FR-080**: aPaaS 模块 MUST 设置 AI 调用的超时时间(默认 30 秒),超时后返回明确错误

#### 架构与可扩展性

- **FR-081**: 组件 MUST 采用模块化设计,各功能域模块(Messaging、CloudDoc、Contact、aPaaS)严禁循环依赖
- **FR-082**: 组件 MUST 提供清晰的模块接口,允许内部服务按需导入所需模块,而不是强制导入全部功能
- **FR-083**: 组件 MUST 支持外部服务扩展,预留接口供外部系统注册自定义的飞书 API 调用逻辑
- **FR-083.1**: 组件依赖飞书 OpenAPI 版本为 v1 (IM API v1, CardKit API v1),如飞书 API 升级到 v2,组件需评估兼容性
- **FR-083.2**: 组件假设飞书 API 可用性 SLA ≥ 99.9%,网络延迟 P95 ≤ 500ms (国内环境)
- **FR-083.3**: 组件明确不支持的功能边界:视频消息(msg_type: video)、音视频通话、语音消息、群管理(创建/解散群组)、机器人管理

#### 性能与超时策略

**API 调用超时**:
- **FR-084**: 组件 MUST 为所有飞书 API 调用设置默认超时时间为 30 秒,避免无限等待
- **FR-085**: 媒体上传 API 的超时时间 MUST 根据文件大小动态调整:基础 30 秒 + (文件大小MB × 2秒),最大 120 秒
- **FR-086**: 组件 MUST 在超时时返回明确的 `RequestTimeoutError`,包含已耗时和超时阈值

**性能目标** *(建议性)*:
- **FR-084.1**: 单条消息发送(不含媒体上传)的 P95 响应时间 SHOULD ≤ 2 秒
- **FR-084.2**: 批量发送 200 条消息的总耗时 SHOULD ≤ 30 秒(含并发控制)
- **FR-084.3**: 10MB 图片上传的 P95 响应时间 SHOULD ≤ 15 秒
- **FR-084.4**: Token 获取和刷新的 P95 响应时间 SHOULD ≤ 1 秒
- **FR-084.5**: CloudDoc 文档创建的 P95 响应时间 SHOULD ≤ 2 秒
- **FR-084.6**: CloudDoc 内容读取的 P95 响应时间 SHOULD ≤ 1 秒
- **FR-084.7**: CloudDoc 内容追加的 P95 响应时间 SHOULD ≤ 3 秒
- **FR-084.8**: Bitable 查询的 P95 响应时间 SHOULD ≤ 2 秒
- **FR-084.9**: Sheet 读取的 P95 响应时间 SHOULD ≤ 2 秒
- **FR-084.10**: Sheet 更新的 P95 响应时间 SHOULD ≤ 3 秒
- **FR-084.11**: Contact 缓存命中的响应时间 SHOULD ≤ 100 ms
- **FR-084.12**: Contact 缓存未命中的响应时间 SHOULD ≤ 2 秒
- **FR-084.13**: 云空间文档 URL 解析(正则表达式)SHOULD ≤ 1 ms
- **FR-084.14**: 知识库文档 URL 解析(含 API 调用)SHOULD ≤ 500 ms

**并发控制** *(建议性)*:
- **FR-085.1**: 批量消息发送 SHOULD 控制并发请求数为 5-10,避免触发飞书限流
- **FR-085.2**: 媒体上传 SHOULD 控制并发上传数为 3,避免占用过多网络带宽

#### 可观测性

- **FR-087**: 组件 MUST 记录完整的请求链路日志,包含请求 ID、API 端点、请求参数(敏感信息脱敏)、响应状态码、耗时
- **FR-088**: 组件 MUST 记录所有 Token 刷新事件,包含 Token 类型、刷新时间、刷新原因、结果
- **FR-089**: 组件 MUST 记录所有重试事件,包含重试次数、重试原因、重试间隔、最终结果
- **FR-090**: 组件 MUST 支持配置日志级别(DEBUG、INFO、WARNING、ERROR),默认为 INFO
- **FR-091**: 组件 MUST 在关键操作失败时记录 ERROR 级别日志,包含足够的错误上下文用于问题排查

#### 安全需求 (Security Requirements)

**配置安全**:
- **FR-092**: 所有敏感配置(App Secret、加密密钥、数据库密码)MUST 仅通过环境变量注入,严禁硬编码在代码或配置文件中
- **FR-093**: 加密密钥(LARK_CONFIG_ENCRYPTION_KEY)MUST 符合 Fernet 规范(32字节 URL-safe base64编码),最小强度为 256 bit
- **FR-094**: SQLite 应用配置文件 MUST 设置文件权限为 0600(仅所有者读写),禁止其他用户访问
- **FR-095**: 配置文件存储路径 MUST 在部署文档中明确指定,默认为 `./config/applications.db`(相对于项目根目录)
- **FR-096**: 组件 MUST 将配置按敏感度分类:`public`(日志级别)、`internal`(数据库连接)、`secret`(密钥/密码),不同类别采用不同的访问控制策略

**密钥管理**:
- **FR-097**: App Secret 在 SQLite 中 MUST 使用 Fernet 对称加密存储,加密密钥来自环境变量
- **FR-098**: 加密密钥 MUST 支持轮换机制,提供 CLI 命令重新加密所有 App Secret:`lark-service-cli config rotate-key --new-key <new_key>`
- **FR-099**: 所有密钥类信息(App Secret、Token、密码)MUST 在日志中脱敏显示(仅显示前4位+`****`或完全隐藏)
  - **FR-099.1**: app_access_token、tenant_access_token、user_access_token 在日志中 MUST 仅显示前 8 位 + `****`
  - **FR-099.2**: App Secret 在日志中 MUST 完全隐藏,显示为 `[REDACTED]`
  - **FR-099.3**: 用户敏感信息(手机号、邮箱、身份证号)在日志中 MUST 脱敏:手机号显示前 3 位+`****`+后 4 位,邮箱显示前 2 位+`***`+@后内容
- **FR-100**: Token 在 PostgreSQL 中 MUST 加密存储(使用 pg_crypto 扩展),防止数据库泄露导致 Token 泄露

**依赖安全**:
- **FR-101**: 项目 MUST 使用 `safety` 工具扫描 Python 依赖的已知安全漏洞,CI 流程中集成安全检查
- **FR-102**: 项目 MUST 每月至少检查一次依赖更新,及时修复高危和严重漏洞(CVSS ≥ 7.0)
- **FR-103**: requirements.txt MUST 锁定依赖版本(使用 `==` 而非 `>=`),避免意外引入不兼容或有漏洞的版本

**容器安全**:
- **FR-104**: Docker 基础镜像 MUST 使用官方镜像(如 `python:3.12-slim`),并定期更新到最新补丁版本
- **FR-105**: Docker 镜像 MUST 在 CI 流程中使用 `trivy` 或 `grype` 进行安全扫描,阻止存在高危漏洞的镜像部署
- **FR-106**: 容器运行 MUST 使用非 root 用户(UID ≥ 1000),在 Dockerfile 中显式指定 `USER` 指令
- **FR-107**: 容器 MUST 仅暴露必需的端口,禁止使用 `EXPOSE 0.0.0.0:*` 形式暴露所有端口

**环境隔离**:
- **FR-108**: 本地开发环境与生产环境 MUST 使用不同的加密密钥和数据库凭证,通过 `.env.development` 和 `.env.production` 区分
- **FR-109**: 生产环境的 `.env` 文件 MUST 在部署后设置文件权限为 0600,禁止提交到版本控制系统
- **FR-110**: 多租户场景(不同 app_id)的 Token 和配置 MUST 完全隔离,禁止跨应用访问

### Key Entities

- **CredentialPool**: 凭证池,负责管理和维护所有类型的访问 Token,包含 Token 值、过期时间、刷新时间、Token 类型、app_id(应用隔离)、锁对象(并发控制)等属性
- **TokenStorage**: Token 存储对象,封装数据库持久化逻辑,包含 app_id、token_type、token_value、expires_at、created_at、updated_at 等字段
- **CallbackEvent**: 回调事件对象,表示飞书交互式卡片回调,包含事件类型、卡片 ID、用户操作、签名验证状态、路由目标等属性
- **UserAuthSession**: 用户认证会话对象,用于 user_access_token 认证流程,包含 session_id、app_id、user_id、认证方式(卡片/链接)、状态、过期时间等属性
- **APIRequest**: API 请求对象,封装飞书 API 调用的请求信息,包含 API 端点、HTTP 方法、请求参数、请求 ID、重试配置、app_id 等属性
- **APIResponse**: API 响应对象,标准化的响应结构,包含业务状态码、请求 ID、数据负载、错误信息、原始响应等属性
- **Message**: 消息对象,表示要发送的飞书消息,包含接收者 ID、消息类型(文本/富文本/图片/文件/卡片)、消息内容、发送时间等属性
- **ImageAsset**: 图片资源对象,表示上传的图片,包含 image_key、图片类型、大小、上传时间等属性
- **FileAsset**: 文件资源对象,表示上传的文件,包含 file_key、文件名、文件类型、大小、上传时间等属性
- **DocumentInfo**: 文档信息对象,表示解析后的文档信息,包含 doc_type、doc_token(实际可用的 token)、source_type(wiki/drive)、space_id、node_token、title、owner 等属性
- **DocumentUrlResolver**: 文档 URL 解析器,统一处理知识库和云空间文档的 URL 解析和 token 获取,支持正则表达式提取和 API 调用两种方式
- **WikiNode**: 知识库节点对象,表示知识库中的节点,包含 space_id、node_token、obj_token(实际的文档 token)、obj_type、node_type(origin/shortcut)、origin_node_token、has_child、title、creator、owner 等属性
- **WikiSpace**: 知识空间对象,表示知识库空间,包含 space_id、name、description、space_type(team/personal)、visibility(public/private)等属性
- **Document**: Doc 文档对象,表示飞书 Doc 云文档,包含文档 ID、标题、内容块列表、权限信息、创建时间等属性
- **ContentBlock**: 文档内容块对象,表示文档中的一个内容单元,包含 block_id、type(paragraph/heading/image/table/code/list/divider)、content、attributes(style/level/language/color)等属性
- **MediaAsset**: 文档素材对象,表示云文档中的素材文件,包含 file_token、素材类型、父文档 ID、大小、上传时间等属性
- **BaseRecord**: 多维表格记录对象,表示多维表格中的一行数据,包含记录 ID、表格 ID、字段值映射、创建时间、更新时间等属性
- **QueryFilter**: 查询过滤器对象,表示多维表格查询条件,包含 conjunction(and/or)、conditions(过滤条件列表,最多 20 个)等属性
- **FilterCondition**: 过滤条件对象,表示单个过滤条件,包含 field_name、operator(is/is_not/contains/gt/lt等 10 种)、value 等属性
- **SheetRange**: Sheet 电子表格范围对象,表示 Sheet 中的数据范围,包含 Sheet ID、起始行列、结束行列、单元格数据等属性
- **User**: 用户对象,表示飞书用户,包含 open_id、user_id、union_id、姓名、邮箱、手机号、部门 ID、职位、头像 URL、员工工号等属性
- **UserCache**: 用户缓存对象(PostgreSQL 存储),包含 app_id、open_id、user_id、union_id、用户详细信息、cached_at、expires_at 等字段,支持按 app_id 隔离
- **ChatGroup**: 群组对象,表示飞书群聊,包含 chat_id、群名称、群主 ID、成员数量、创建时间等属性
- **Department**: 部门对象,表示组织架构中的部门,包含部门 ID、部门名称、父部门 ID、成员列表等属性
- **WorkspaceTable**: 数据空间表格对象,表示 aPaaS 工作空间中的数据表,包含 workspace_id、table_id、表格名称、字段定义列表、记录数量等属性
- **TableRecord**: 数据空间表格记录对象,表示表格中的一行数据,包含 record_id、table_id、字段值映射(Dict)、版本号(用于并发控制)、created_at、updated_at 等属性
- **Workflow**: aPaaS 工作流对象,表示自动化流程,包含工作流 ID、名称、触发参数、执行状态、执行结果等属性
- **AICapability**: AI 能力对象,表示飞书 AI 服务,包含能力 ID、能力类型、输入参数、输出结果等属性
- **ErrorMapping**: 错误映射对象,将飞书原始错误码映射为内部语义化错误,包含原始错误码、错误类型、错误描述、是否可重试等属性

#### 代码质量与文档

**Docstring 标准**:
- **FR-111**: 所有公共 API(模块、类、函数)MUST 包含 Docstring,覆盖率要求 100%
- **FR-112**: Docstring MUST 采用 Google 风格,包含以下必需部分:
  - 功能简述(单行)
  - 详细说明(可选)
  - Args: 参数列表(参数名、类型、说明)
  - Returns: 返回值(类型、说明)
  - Raises: 可能抛出的异常(异常类、触发条件)
  - Example: 使用示例(可选,推荐用于复杂 API)
- **FR-113**: 私有方法(以 `_` 开头)和内部工具函数 SHOULD 包含 Docstring,至少说明用途和参数

**类型注解**:
- **FR-114**: 所有公共 API MUST 包含完整的类型注解(参数和返回值),mypy strict 模式覆盖率要求 ≥ 99%
- **FR-115**: 复杂类型(如 Union、Optional、Dict)MUST 使用类型别名(TypeAlias)提高可读性

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 内部服务开发者能在 10 分钟内完成组件集成并发送第一条测试消息,无需阅读飞书 API 文档
- **SC-002**: 组件在正常运行情况下,99.9% 的 API 调用无需调用方手动处理 Token 失效问题
- **SC-003**: 在 Token 即将过期的场景下,组件的主动刷新机制使得 95% 以上的 API 调用无需等待 Token 刷新(命中已刷新的新 Token)
- **SC-004**: 在飞书 API 出现瞬时故障(如网络超时)时,组件的重试机制使得 80% 以上的调用最终成功,调用方无需手动重试
- **SC-005**: 组件的错误信息使得开发者能在 5 分钟内定位问题根因(如配置错误、参数错误、权限不足等),无需查看组件源码
- **SC-006**: 组件支持每秒 100 次并发 API 调用,且 Token 刷新不成为性能瓶颈,99.9% 的请求响应时间应小于 2 秒
- **SC-007**: 组件的日志记录使得运维人员能在 10 分钟内追踪任意一次 API 调用的完整链路(从请求发起到响应返回)
- **SC-008**: 新增一个飞书服务模块(如日历服务)的开发工作量不超过 2 人天,且无需修改核心凭证管理逻辑
- **SC-009**: 内部服务使用组件后,因飞书集成问题产生的支持工单减少 70% 以上
- **SC-010**: 组件的参数校验能在 API 调用前捕获 90% 以上的参数错误,避免无效的网络请求
- **SC-011**: 运维人员能在 2 分钟内通过应用配置管理接口新增一个飞书应用配置,无需修改代码或重启服务
- **SC-012**: Contact 模块的用户信息缓存命中率达到 80% 以上,减少飞书 API 调用次数
- **SC-013**: aPaaS 数据空间表格操作支持每秒 50 次并发查询,响应时间 95 分位数小于 2 秒
- **SC-014**: 依赖安全扫描在 CI 中阻止存在高危漏洞(CVSS ≥ 7.0)的代码合并,实现零高危漏洞部署
- **SC-015**: Docker 镜像安全扫描在 CI 中阻止存在严重漏洞的镜像构建,镜像安全评分 ≥ B 级
- **SC-016**: CloudDoc 模块支持每秒 50 次并发文档操作,响应时间 95 分位数小于 3 秒
- **SC-017**: DocumentUrlResolver 能正确识别和解析 100% 的标准飞书文档 URL(6 种格式)
- **SC-018**: 知识库 node_token 缓存命中率达到 90% 以上,减少 Wiki API 调用次数
- **SC-019**: Contact 模块在 API 调用失败时,80% 以上的请求能返回过期缓存,避免服务不可用
- **SC-020**: CloudDoc 和 Contact 模块的 API 契约覆盖率达到 100%,所有端点都有明确的请求/响应定义

## Clarifications

### Session 2026-01-14

- Q: 应用配置管理方案 → A: 使用 SQLite 轻量级存储应用配置(App ID/Secret/元数据),支持动态增删改查,无需重启服务
- Q: Token 持久化存储策略 → A: 使用 PostgreSQL 存储 Token,支持高并发读写和字段级加密
- Q: 混合存储架构设计 → A: 应用配置用 SQLite(低频配置管理),Token 数据用 PostgreSQL(高频并发读写),职责分离
- Q: 并发 Token 刷新的锁机制 → A: 使用线程锁和进程锁组合(threading.Lock + multiprocessing.Lock),支持单机多进程部署
- Q: 多应用凭证隔离方式 → A: 调用时传入 app_id 参数,组件从 SQLite 动态加载应用配置,按 app_id 隔离 Token
- Q: 交互式卡片回调处理方式 → A: 使用消息队列(如 RabbitMQ)异步处理回调事件,组件统一接收飞书回调并路由到注册的处理函数
- Q: 凭证池故障恢复策略 → A: 启动时仅验证配置,Token 懒加载。user_access_token 需要用户首次认证,支持飞书卡片或消息链接等多种认证方式
- Q: Contact 模块用户信息缓存方案 → A: 至少包括 open_id、user_id、union_id 三种标识,群查询需要 chat_id。user_access_token 与 app_id、user 相关联,不同应用相同用户有不同 user_access_token,因此用户信息按 app_id 隔离存储到 PostgreSQL,TTL 为 24 小时
- Q: aPaaS 数据空间操作定义 → A: 飞书 aPaaS 独立的数据存储服务(参考 https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list),包括查询表格列表、读取记录(query)、更新记录(update)、删除记录(delete),需要 user_access_token 权限

### Session 2026-01-15 (Phase 4 补充)

- Q: 知识库文档访问方式 → A: 云文档可以存放在两个位置:1) 云空间(Drive) - 直接使用 doc_token;2) 知识库(Wiki) - 需要先通过 node_token 调用 Wiki API 获取 obj_token(实际的文档 token)。参考: https://open.feishu.cn/document/server-docs/docs/wiki-v2/space-node/get_node
- Q: 文档 URL 解析工具设计 → A: 提供统一的 DocumentUrlResolver 工具类,采用双路径处理策略:1) 优先尝试云空间解析(正则表达式,< 1ms);2) 失败后尝试知识库解析(API 调用,100-500ms)。支持 6 种 URL 格式(docx、doc、sheets、base、file、wiki),返回统一的 DocumentInfo 对象
- Q: 知识库快捷方式处理 → A: DocumentUrlResolver 自动递归获取快捷方式(shortcut)指向的原始节点的 obj_token,无需调用方手动处理
- Q: 知识库 node_token 缓存策略 → A: 缓存 node_token → obj_token 的映射,TTL 为 1 小时(知识库结构变化较少),使用 LRU 缓存或 Redis,缓存 key 格式为 `wiki_node:{space_id}:{node_token}`
- Q: CloudDoc 内容块类型定义 → A: 支持 7 种内容类型(paragraph、heading、image、table、code、list、divider),每种类型有明确的 content 类型和 attributes。限制:单次追加最大 100 个 block,单个 block 最大 100 KB
- Q: Bitable 过滤器语法 → A: 定义 QueryFilter 数据结构,支持 10 种操作符(is、is_not、contains、not_contains、gt、lt、gte、lte、is_empty、is_not_empty),支持 and/or 逻辑连接,最多 20 个条件,单次查询最多返回 500 条记录
- Q: Sheet 范围格式规范 → A: 支持 4 种范围格式(单元格范围 A1:B10、整列 A:C、整行 3:5、单个单元格 A1)。限制:单次读取最大 100,000 个单元格,单次更新最大 10,000 个单元格,单次合并最大 1,000 个单元格
- Q: 媒体上传限制 → A: 图片最大 10 MB,支持 6 种格式(jpg、jpeg、png、gif、bmp、webp),最大尺寸 4096×4096。文件最大 30 MB,支持 9 种格式(pdf、doc、docx、xls、xlsx、ppt、pptx、zip、rar、7z)
- Q: Contact 用户 ID 类型使用策略 → A: 明确 3 种 ID 的作用域:open_id(应用内,用于消息发送)、user_id(租户内,用于组织架构)、union_id(跨租户,用于缓存主键)。缓存 key 格式为 `user:{app_id}:{union_id}`,确保应用级隔离
- Q: Contact 缓存失效策略 → A: 支持 4 种失效方式:1) TTL 过期(24 小时);2) 主动失效(用户信息更新时);3) 强制失效(管理员操作);4) 容量淘汰(LRU,最大 100,000 条)。API 调用失败时,如果有过期缓存则返回过期缓存,避免服务不可用

## Assumptions

- 假设所有内部服务都运行在可以访问飞书 OpenAPI 的网络环境中
- 假设企业已完成飞书自建应用的创建和配置,App ID 和 App Secret 可用
- 假设应用配置变更是低频操作(平均每周少于 10 次),适合使用 SQLite 存储
- 假设内部服务的并发量在合理范围内(每秒数百次调用),不需要考虑超大规模的流量场景
- 假设飞书 OpenAPI 的接口协议保持相对稳定,不会频繁出现破坏性变更
- 假设内部服务的开发者具备基本的 Python 编程能力和 API 调用经验
- 假设组件部署环境支持 SQLite(应用配置)和 PostgreSQL(Token 存储)两种数据库
- 假设组件部署环境支持消息队列(如 RabbitMQ)用于异步处理回调事件
- 假设应用配置文件(SQLite)可以随代码打包部署,支持离线配置初始化
- 假设飞书 API 的限流策略为每秒 10 次调用(实际值需要验证),组件的重试策略基于此假设
- 假设 Token 的默认过期时间为 2 小时(7200 秒),组件在剩余 720 秒(10%)时触发刷新
- 假设用户信息变更频率较低,24 小时 TTL 的缓存策略可满足大部分场景
- 假设 aPaaS 数据空间操作需要用户级权限(user_access_token),应用级 Token 无法访问

---

## Phase 4 补充说明 (CloudDoc & Contact)

### CloudDoc 模块数据结构

#### Document (文档)
```python
{
  "doc_id": "doxcn1234567890abcdefghij",    # 文档 ID (doxcn/doccn 开头,20+ 字符)
  "title": "测试文档",                       # 文档标题 (1-255 字符)
  "owner_id": "ou_1234567890abcdefghij",    # 所有者 open_id (可选)
  "create_time": "2026-01-15T10:00:00Z",    # 创建时间 (可选)
  "update_time": "2026-01-15T12:00:00Z",    # 更新时间 (可选)
  "content_blocks": [...]                    # 内容块列表 (可选)
}
```

#### ContentBlock (内容块)
```python
{
  "block_id": "blk1234567890abcdefghij",    # 块 ID (20+ 字符,可选)
  "block_type": "text",                      # 类型: text, heading, image, table, code, list, divider
  "content": "文本内容",                     # 内容 (字符串或对象)
  "attributes": {                            # 属性 (可选)
    "style": "bold",                         # 样式
    "level": 1                               # 标题级别 (heading 类型)
  }
}
```

**限制:**
- 单次追加最大 100 个 block
- 单个 block 最大 100 KB
- 标题级别 1-6
- 文档标题 1-255 字符

#### BaseRecord (多维表格记录)
```python
{
  "record_id": "rec1234567890abcdefghij",   # 记录 ID (rec 开头,20+ 字符,创建时可选)
  "fields": {                                # 字段值 (必需)
    "Name": "张三",
    "Age": 30,
    "Email": "zhangsan@company.com"
  },
  "create_time": "2026-01-15T10:00:00Z",    # 创建时间 (可选)
  "update_time": "2026-01-15T12:00:00Z"     # 更新时间 (可选)
}
```

#### FilterCondition (过滤条件)
```python
{
  "field_name": "Age",                       # 字段名
  "operator": "gte",                         # 操作符
  "value": 18                                # 比较值
}
```

**支持的操作符:**
- `eq` - 等于
- `ne` - 不等于
- `gt` - 大于
- `gte` - 大于等于
- `lt` - 小于
- `lte` - 小于等于
- `contains` - 包含
- `not_contains` - 不包含
- `is_empty` - 为空
- `is_not_empty` - 不为空

**限制:**
- 最多 20 个过滤条件
- 单次查询最多 500 条记录
- 批量创建/更新/删除最大 500 条

#### SheetRange (电子表格范围)
```python
{
  "sheet_id": "sheet_id_123",               # Sheet ID
  "range_notation": "A1:B10"                # 范围表示法
}
```

**支持的范围格式:**
1. A1 表示法: `A1:B10`
2. 行列索引: `R1C1:R10C2`
3. 命名范围: `SalesData`
4. 整列/整行: `A:A`, `1:1`

**限制:**
- 读取最大 100,000 个单元格
- 更新最大 10,000 个单元格
- 合并最大 1,000 个单元格
- 冻结窗格最大 100 行/100 列

### Contact 模块数据结构

#### User (用户)
```python
{
  "open_id": "ou_1234567890abcdefghij",     # 应用内用户 ID (必需,20+ 字符)
  "user_id": "7g9j1234",                     # 租户内用户 ID (必需,8+ 字符)
  "union_id": "on_1234567890abcdefghij",    # 全局用户 ID (必需,20+ 字符)
  "name": "张三",                            # 用户姓名 (必需,1-100 字符)
  "avatar": "https://...",                   # 头像 URL (可选)
  "email": "zhangsan@company.com",          # 邮箱 (可选)
  "mobile": "+8613800138000",               # 手机号 (可选)
  "department_ids": ["dept_001"],           # 部门 ID 列表 (可选)
  "employee_no": "E001",                    # 工号 (可选)
  "job_title": "工程师",                     # 职位 (可选)
  "status": 1                                # 状态: 1-激活,2-未激活,4-已离职 (可选)
}
```

**三种 ID 的使用场景:**
- `open_id`: 应用内标识,用于发送消息、授权等 (不同应用不同)
- `user_id`: 租户内标识,用于用户管理、权限控制 (同一租户内相同)
- `union_id`: 全局标识,用于跨租户识别、缓存 key (跨租户相同,推荐)

#### Department (部门)
```python
{
  "department_id": "dept_001",              # 部门 ID
  "name": "技术部",                          # 部门名称
  "parent_department_id": "dept_000",       # 父部门 ID (可选)
  "member_count": 50,                       # 成员数量
  "status": 1                                # 状态: 1-正常,2-停用
}
```

#### ChatGroup (群组)
```python
{
  "chat_id": "oc_1234567890abcdefghij",     # 群组 ID (oc_ 开头,20+ 字符)
  "name": "技术讨论组",                      # 群名称
  "description": "技术团队交流",             # 群描述 (可选)
  "owner_id": "ou_xxx",                     # 群主 open_id
  "member_count": 25                        # 成员数量
}
```

**限制:**
- 批量查询用户最大 200 个/次
- 部门成员查询分页,每页最多 50 个
- 群成员查询分页,每页最多 100 个

### Phase 4 错误码定义

#### CloudDoc 模块错误码

| 错误码 | 错误类型 | 说明 | 是否可重试 |
|--------|----------|------|-----------|
| 50001 | InvalidParameterError | 文档标题为空或超长 | ❌ |
| 50002 | InvalidParameterError | 内容块数量超限 (>100) | ❌ |
| 50003 | InvalidParameterError | 内容块大小超限 (>100KB) | ❌ |
| 50004 | InvalidParameterError | 权限类型无效 | ❌ |
| 50005 | InvalidParameterError | 成员类型无效 | ❌ |
| 50006 | NotFoundError | 文档不存在 | ❌ |
| 50007 | NotFoundError | 内容块不存在 | ❌ |
| 50008 | PermissionDeniedError | 无文档操作权限 | ❌ |
| 50009 | PermissionDeniedError | 无权限管理权限 | ❌ |
| 50101 | InvalidParameterError | 记录字段为空 | ❌ |
| 50102 | InvalidParameterError | 分页大小超限 (>500) | ❌ |
| 50103 | InvalidParameterError | 批量操作数量超限 (>500) | ❌ |
| 50104 | InvalidParameterError | 过滤条件超限 (>20) | ❌ |
| 50105 | InvalidParameterError | 过滤操作符无效 | ❌ |
| 50106 | NotFoundError | 记录不存在 | ❌ |
| 50107 | NotFoundError | 表格不存在 | ❌ |
| 50201 | InvalidParameterError | Sheet 范围为空 | ❌ |
| 50202 | InvalidParameterError | 单元格数量超限 | ❌ |
| 50203 | InvalidParameterError | 字体大小无效 (6-36) | ❌ |
| 50204 | InvalidParameterError | 对齐方式无效 | ❌ |
| 50205 | InvalidParameterError | 合并类型无效 | ❌ |
| 50206 | InvalidParameterError | 列宽无效 (10-500) | ❌ |
| 50207 | InvalidParameterError | 行高无效 (10-500) | ❌ |
| 50208 | InvalidParameterError | 冻结行列超限 (>100) | ❌ |
| 50209 | NotFoundError | Sheet 不存在 | ❌ |

#### Contact 模块错误码

| 错误码 | 错误类型 | 说明 | 是否可重试 |
|--------|----------|------|-----------|
| 60001 | InvalidParameterError | 邮箱格式无效 | ❌ |
| 60002 | InvalidParameterError | 手机号格式无效 | ❌ |
| 60003 | InvalidParameterError | 用户 ID 格式无效 | ❌ |
| 60004 | InvalidParameterError | 批量查询数量超限 (>200) | ❌ |
| 60005 | InvalidParameterError | 分页大小超限 (>50) | ❌ |
| 60006 | NotFoundError | 用户不存在 | ❌ |
| 60007 | NotFoundError | 部门不存在 | ❌ |
| 60008 | NotFoundError | 群组不存在 | ❌ |
| 60009 | PermissionDeniedError | 无通讯录读取权限 | ❌ |
| 60010 | PermissionDeniedError | 无敏感信息读取权限 | ❌ |
| 60101 | CacheError | 缓存写入失败 | ✅ |
| 60102 | CacheError | 缓存读取失败 | ✅ |
| 60103 | CacheError | 缓存清理失败 | ✅ |

#### 通用错误码映射

**飞书 API 错误码 → 内部错误类型:**

| 飞书错误码 | 内部错误类型 | 说明 |
|-----------|-------------|------|
| 99991663 | AuthenticationError | App Secret 无效 |
| 99991664 | AuthenticationError | Tenant access token 无效 |
| 99991668 | PermissionDeniedError | 应用权限不足 |
| 230001 | NotFoundError | 用户不存在 |
| 230002 | NotFoundError | 部门不存在 |
| 230011 | PermissionDeniedError | 无通讯录读取权限 |
| 1254044 | NotFoundError | 文档不存在 |
| 1254045 | PermissionDeniedError | 无文档访问权限 |
| 1254046 | InvalidParameterError | 文档参数无效 |

### Phase 4 实现状态

#### 已实现功能 ✅

**CloudDoc 模块:**
- ✅ Document, ContentBlock, BaseRecord, SheetRange 数据模型
- ✅ DocClient: 创建文档、追加内容、读取文档、权限管理
- ✅ BitableClient: CRUD 操作、批量操作、过滤查询、分页
- ✅ SheetClient: 读写数据、格式化、合并单元格、冻结窗格
- ✅ 完整的参数验证和错误处理
- ✅ 60 个单元测试 (100% 通过)

**Contact 模块:**
- ✅ User, Department, ChatGroup 数据模型
- ✅ ContactClient: 用户查询、部门查询、群组查询、批量操作
- ✅ ContactCacheManager: PostgreSQL 缓存、TTL 24h、app_id 隔离
- ✅ 缓存统计、懒加载刷新、显式失效
- ✅ 完整的参数验证和错误处理
- ✅ 46 个单元测试 (100% 通过)

**质量指标:**
- ✅ 225 个单元测试全部通过
- ✅ 64.15% 代码覆盖率
- ✅ 0 个 ruff 错误
- ✅ 0 个 mypy 类型错误
- ✅ 完整的类型注解
- ✅ 符合代码规范

#### 待实现功能 ⏳

**CloudDoc 模块:**
- ⏳ MediaClient: 上传/下载文档素材 (T056, 可选)
- ⏳ DocumentUrlResolver: 统一文档 URL 解析 (FR-045)
- ⏳ Wiki 节点缓存: node_token → obj_token 映射

**Contact 模块:**
- ⏳ 缓存集成到 ContactClient (T062b)
- ⏳ LRU 容量淘汰策略 (FR-066.3)

**测试:**
- ⏳ 集成测试 (T059b, T065)
- ⏳ 性能基准测试

#### 已知限制

**SDK 相关:**
- ⚠️ lark-oapi v1.5.2 的 InternalTenantAccessTokenRequest 有 bug
  - 已绕过: 使用 HTTP 直接请求
  - 影响: 配置验证脚本、CredentialPool
  - 状态: 已修复
- ⚠️ UpdateDocumentBlockRequest 在 SDK 中不可用
  - 影响: update_block 方法为 placeholder 实现
  - 状态: 待 SDK 更新

**API 限制:**
- 知识库文档需要额外 API 调用获取 obj_token (100-500ms)
- 部分 API 响应不包含完整字段 (如 create_time)
- 批量操作限制 500 条/次

### Phase 4 测试策略

#### 单元测试 ✅ (已完成)
- **覆盖范围**: 所有客户端方法、参数验证、错误处理
- **Mock 策略**: 模拟 SDK 响应,隔离外部依赖
- **测试数据**: 使用符合验证规则的 mock ID
- **结果**: 225 passed, 3 skipped

#### 集成测试 ⏳ (环境已就绪)
- **测试环境**: .env.test 已配置,PostgreSQL 已连接
- **测试数据**: 真实 App ID/Secret,测试用户邮箱
- **测试场景**:
  - Contact: 查询用户 → 缓存 → 再次查询 (验证缓存命中)
  - CloudDoc: 创建文档 → 写入内容 → 读取验证
  - Bitable: CRUD 记录 → 过滤查询 → 批量操作
- **运行方式**: `pytest tests/integration/ -v`

#### 性能测试 ⏳ (待实施)
- 缓存命中响应时间 < 100ms
- 缓存未命中响应时间 < 2s
- 文档操作响应时间 < 3s
- 并发测试: 100 并发请求
