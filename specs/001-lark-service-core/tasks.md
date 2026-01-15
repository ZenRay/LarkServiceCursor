# Tasks: Lark Service 核心组件

**Input**: Design documents from `/specs/001-lark-service-core/`  
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, contracts/

**Organization**: Tasks organized by阶段 and user story (US1-US5) to enable independent implementation and testing.

**Tests**: Following TDD principle (Constitution VIII) - write failing tests before implementation.

## Format: `- [ ] [TaskID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup & Infrastructure (项目初始化)

**目标**: 项目初始化、基础结构搭建和开发环境配置

**预计时间**: ~1天

### 项目结构

- [X] T001 按 plan.md 创建项目目录结构 (src/lark_service/, tests/, docs/, migrations/)
- [X] T002 初始化 Python 项目 pyproject.toml (Python 3.12, 项目元数据, 构建配置)
- [X] T003 [P] 创建 requirements.txt 包含核心依赖 (lark-oapi, pydantic v2, SQLAlchemy 2.0, psycopg2-binary, pika, cryptography)
- [X] T004 [P] 创建 .env.example 包含必需环境变量 (LARK_CONFIG_ENCRYPTION_KEY, POSTGRES_*, RABBITMQ_*, LOG_LEVEL)
- [X] T005 [P] 创建 .gitignore (排除 .env, __pycache__, *.pyc, .mypy_cache, .pytest_cache, config/applications.db)
- [X] T006 [P] 在 pyproject.toml 配置 ruff (line-length=100, target-version=py312)
- [X] T007 [P] 在 pyproject.toml 配置 mypy (strict=True, disallow_untyped_defs=True)
- [X] T008 [P] 在 pyproject.toml 配置 pytest (testpaths, asyncio_mode, coverage settings)

### Docker 和开发环境

- [X] T009 创建应用 Dockerfile (多阶段构建, Python 3.12-slim 基础镜像)
- [X] T010 创建 docker-compose.yml (postgres:15, rabbitmq:3-management, app service 挂载卷)
- [X] T011 [P] 创建数据库初始化脚本 migrations/init.sql (启用 pg_crypto 扩展)
- [X] T012 [P] 配置 Alembic PostgreSQL 迁移工具 (alembic.ini, migrations/env.py, versions/)

### 文档

- [X] T013 [P] 创建 README.md (项目概述、安装说明、快速开始参考 quickstart.md)
- [X] T014 [P] 创建 docs/architecture.md (高层架构图、模块依赖关系)
- [X] T015 [P] 创建 docs/deployment.md (Docker 部署、环境变量、健康检查)

### 阶段检查点 (量化验收标准)

#### 1. 构建验证 (CHK041, CHK043)
- [ ] `docker compose build` 成功完成
  - **镜像大小**: ≤ 500MB (基础镜像 + 依赖)
  - **构建时间**: ≤ 5 分钟 (首次构建,无缓存)
  - **失败处理**: 构建失败时输出完整错误堆栈到 stderr,包含失败步骤和原因

#### 2. 依赖安装 (CHK044)
- [ ] `uv pip install -r requirements.txt` 无错误
  - **警告容忍**: 允许 deprecation warnings,但不允许 error
  - **超时时间**: ≤ 2 分钟 (使用 uv 加速)
  - **兼容性**: pip 和 uv 安装结果一致

#### 3. 代码质量 (CHK017, CHK047, CHK048)
- [ ] `ruff check .` 通过
  - **错误数**: 0 errors (阻塞)
  - **警告数**: ≤ 5 warnings (非阻塞)
  - **排除路径**: `migrations/`, `__pycache__/`, `.pytest_cache/`, `htmlcov/`
  
- [ ] `mypy src/` 类型检查
  - **错误上限**: 0 errors (阻塞)
  - **覆盖率**: ≥ 99% (计算范围: src/lark_service/, 不包含 tests/)
  - **计算方式**: `mypy --html-report mypy-report src/` 生成覆盖率报告

#### 4. 环境启动 (CHK050)
- [ ] `docker compose up -d` 启动成功
  - **服务就绪时间**: PostgreSQL ≤ 10秒, RabbitMQ ≤ 15秒
  - **健康检查**: 
    ```bash
    # PostgreSQL
    docker compose exec -T postgres pg_isready -U lark
    
    # RabbitMQ
    curl -f http://localhost:15672/api/health/checks/alarms
    ```
  - **超时策略**: 如果 30秒 内未就绪,检查日志并退出

#### 5. 文档完整性
- [ ] README.md 和 docs/ 文件就位
  - **必需文档**: README.md, architecture.md, security-guide.md, development-environment.md, docstring-standard.md, deployment.md
  - **文档格式**: 所有 Markdown 文件符合规范 (标题层级、代码块、链接有效)

---

## Phase 2: Foundational - US1 透明 Token 管理 (Priority: P1) 🎯 MVP

**目标**: 实现自动 Token 管理,支持多应用隔离的 Token 获取、刷新和持久化存储

**独立测试**: 调用简单 API(如发送消息)验证无需手动提供 Token,且 Token 过期时自动刷新

**预计时间**: ~3-4天

**为何是 Foundational**: 所有其他用户故事(消息、文档、通讯录、aPaaS)都依赖 Token 管理,必须优先完成

### 数据库层 (SQLite + PostgreSQL)

- [ ] T016 [P] [US1] 创建 SQLite Application 模型 src/lark_service/core/models/application.py (Application SQLAlchemy 模型,带加密)
- [ ] T017 [P] [US1] 创建 PostgreSQL TokenStorage 模型 src/lark_service/core/models/token_storage.py (TokenStorage 包含 app_id, token_type, token_value, expires_at)
- [ ] T018 [P] [US1] 创建 PostgreSQL UserCache 模型 src/lark_service/core/models/user_cache.py (UserCache 包含 open_id, user_id, union_id, TTL 24h)
- [ ] T019 [P] [US1] 创建 UserAuthSession 模型 src/lark_service/core/models/auth_session.py (session_id, state, auth_method, expires_at)
- [ ] T020 [US1] 创建 Alembic 迁移 001_initial_schema.py (tokens, user_cache, auth_sessions 表及索引)
- [ ] T021 [US1] 实现 SQLite 初始化脚本 src/lark_service/db/init_config_db.py (创建 applications.db, 从 .env 添加默认应用)

### CLI 命令行工具

- [x] T021.1 [P] [US1] 创建 CLI 入口模块 src/lark_service/cli/__init__.py (Click 命令组定义, main() 函数作为入口点) ✅
- [x] T021.2 [US1] 实现 app add 命令 src/lark_service/cli/app.py (添加应用配置, 参数验证, 加密存储, 成功提示) ✅
- [x] T021.3 [US1] 实现 app list 命令 src/lark_service/cli/app.py (列出所有应用, Rich 表格展示, 支持 --json 选项) ✅
- [x] T021.4 [US1] 实现 app show 命令 src/lark_service/cli/app.py (显示应用详情, app_secret 脱敏显示为 secret_****, 支持 --json 选项) ✅
- [x] T021.5 [US1] 实现 app update 命令 src/lark_service/cli/app.py (更新应用配置, 支持部分字段更新, 重新加密 app_secret) ✅
- [x] T021.6 [US1] 实现 app delete 命令 src/lark_service/cli/app.py (删除应用配置, 交互式确认或 --force 选项, 级联删除 Token) ✅
- [x] T021.7 [US1] 实现 app enable/disable 命令 src/lark_service/cli/app.py (启用/禁用应用, 更新 is_active 状态) ✅
- [x] T021.8 [P] [US1] 添加 CLI 单元测试 tests/unit/cli/test_app_commands.py (命令参数验证, 输出格式, 错误处理, 退出码) ✅
- [x] T021.9 [US1] 配置 setup.py 入口点 setup.py (console_scripts: lark-service-cli=lark_service.cli:main) ✅
 ✅
### 核心基础设施
 ✅
- [x] T022 [P] [US1] 实现配置加载器 src/lark_service/core/config.py (加载 .env, 验证必需变量, Config dataclass) ✅
- [x] T023 [P] [US1] 实现自定义异常 src/lark_service/core/exceptions.py (TokenAcquisitionError, ConfigError, APIError 基类) ✅
- [x] T024 [P] [US1] 实现 StandardResponse src/lark_service/core/response.py (Pydantic 模型,包含 code, message, request_id, data, error) ✅
- [x] T025 [P] [US1] 实现日志设置 src/lark_service/utils/logger.py (结构化日志、日志级别、request_id 注入) ✅
- [x] T026 [P] [US1] 实现参数校验器 src/lark_service/utils/validators.py (app_id 格式、邮箱格式、文件大小限制) ✅
 ✅
### 存储层服务
 ✅
- [x] T027 [US1] 实现 SQLite 存储服务 src/lark_service/core/storage/sqlite_storage.py (ApplicationManager CRUD, 加密/解密) ✅
- [x] T028 [US1] 实现 PostgreSQL 存储服务 src/lark_service/core/storage/postgres_storage.py (TokenStorageService 包含 get/set/delete, 连接池) ✅
 ✅
### 并发控制
 ✅
- [x] T029 [US1] 实现锁管理器 src/lark_service/core/lock_manager.py (TokenRefreshLock 使用 threading.Lock + filelock 进程级锁, 超时 30s) ✅
 ✅
### Token 凭证池核心
 ✅
- [x] T030 [US1] 实现重试策略 src/lark_service/core/retry.py (指数退避 1s→2s→4s, 最多3次重试, 限流处理30s) ✅
- [x] T031 [US1] 实现 CredentialPool src/lark_service/core/credential_pool.py (get_token, refresh_token, 懒加载, 多应用隔离) ✅
- [x] T032 [US1] 集成 lark-oapi SDK 到 credential_pool.py (每个 app_id 的 SDK 客户端初始化, 通过 SDK 获取 token) ✅
 ✅
### TDD 测试 (先写失败测试)
 ✅
- [x] T033 [P] [US1] Application 模型单元测试 tests/unit/core/test_application_model.py (加密/解密、状态验证) ✅
- [x] T034 [P] [US1] TokenStorage 模型单元测试 tests/unit/core/test_token_storage_model.py (唯一约束、expires_at 验证) ✅
- [x] T035 [P] [US1] 锁管理器单元测试 tests/unit/core/test_lock_manager.py (并发访问、超时行为) ✅
- [x] T036 [P] [US1] 重试策略单元测试 tests/unit/core/test_retry.py (指数退避、最大重试次数、限流检测) ✅
- [x] T037 [US1] Token 凭证池集成测试 tests/integration/test_credential_pool.py (懒加载、Token刷新、数据库持久化、多应用隔离) ✅
- [x] T038 [US1] Token 生命周期集成测试 tests/integration/test_token_lifecycle.py (获取 → 使用 → 刷新 → 过期 → 重新获取) ✅
 ✅
### 阶段检查点
 ✅
- [x] **构建验证**: `docker build -t lark-service:latest .` 成功 ✅
- [x] **代码质量**: `ruff check src/ tests/` 无错误, `mypy src/` 99%+ 覆盖率 ✅
- [x] **单元测试**: `pytest tests/unit/core/ -v` 全部通过 ✅
- [x] **集成测试**: `pytest tests/integration/test_credential_pool.py -v` 通过 ✅
- [x] **功能验证**: 手工测试 CredentialPool.get_token() 返回有效 Token,服务重启后从数据库恢复 ✅
- [x] **文档更新**: 更新 docs/architecture.md 补充 Token 管理架构图 ✅

---

## Phase 3: US2 消息服务封装 (Priority: P2)

**目标**: 实现消息发送能力(文本、富文本、图片、文件、交互式卡片、批量发送)

**独立测试**: 发送测试消息到指定用户,验证消息成功送达且格式正确

**预计时间**: ~2-3天

**依赖**: US1 (Token 管理) 必须完成

### Pydantic 模型

- [ ] T039 [P] [US2] 创建 Message 模型 src/lark_service/messaging/models.py (Message, MessageType enum, ImageAsset, FileAsset, CallbackEvent)

### 媒体上传

- [ ] T040 [P] [US2] 实现媒体上传器 src/lark_service/messaging/media_uploader.py (upload_image, upload_file 包含大小验证, 返回 image_key/file_key)

### 消息客户端

- [ ] T041 [US2] 实现消息客户端 src/lark_service/messaging/client.py (send_text_message, send_rich_text_message, send_image_message, send_file_message 自动上传)
- [ ] T042 [US2] 实现批量发送 messaging/client.py (send_batch_messages 包含每个接收者的状态跟踪)
- [ ] T043 [US2] 实现消息生命周期管理 messaging/client.py (recall_message 消息撤回, edit_message 消息编辑, reply_message 消息回复)

### 交互式卡片

- [ ] T044 [P] [US2] 实现卡片构建器 src/lark_service/messaging/card_builder.py (CardBuilder 常用卡片模板辅助工具, 按钮动作)
- [ ] T045 [US2] 实现卡片发送 messaging/client.py (send_interactive_card 包含回调 URL 注册)
- [ ] T046 [US2] 实现回调处理器 src/lark_service/messaging/callback_handler.py (RabbitMQ 集成、签名验证、事件路由到注册的处理函数)

### TDD 测试

- [ ] T047 [P] [US2] 消息 API 契约测试 tests/contract/test_messaging_contract.py (验证符合 contracts/messaging.yaml)
- [ ] T048 [P] [US2] 媒体上传器单元测试 tests/unit/messaging/test_media_uploader.py (文件大小限制、类型验证、mock lark-oapi 调用)
- [ ] T049 [P] [US2] 卡片构建器单元测试 tests/unit/messaging/test_card_builder.py (卡片结构验证)
- [ ] T050 [US2] 消息集成测试 tests/integration/test_messaging_e2e.py (发送文本 → 验证送达, 发送卡片 → 触发回调 → 验证处理函数调用)

### 阶段检查点

- [ ] **构建验证**: `docker build -t lark-service:latest .` 成功
- [ ] **代码质量**: `ruff check src/lark_service/messaging/` 无错误, `mypy src/lark_service/messaging/` 通过
- [ ] **单元测试**: `pytest tests/unit/messaging/ -v` 全部通过
- [ ] **契约测试**: `pytest tests/contract/test_messaging_contract.py -v` 通过
- [ ] **功能验证**: 手工发送文本、图片、文件消息到测试账号,验证送达;发送交互式卡片,点击按钮验证回调处理
- [ ] **文档更新**: 更新 docs/api_reference.md 补充 Messaging 模块 API 文档

---

## Phase 4: US3 云文档 + US4 通讯录 (Priority: P3, 可并行)

**目标**: 实现云文档操作(Doc/Sheet/多维表格/素材上传下载) + 通讯录查询(用户/部门/缓存)

**独立测试**: 
- US3: 创建测试文档、写入内容、读取验证;CRUD 多维表格记录
- US4: 通过邮箱查询用户,验证返回三种ID;验证缓存命中和自动刷新

**预计时间**: ~3-4天 (两个故事可并行开发)

**依赖**: US1 (Token 管理) 必须完成

### US3: CloudDoc 模块

#### Pydantic 模型

- [ ] T051 [P] [US3] 创建 CloudDoc 模型 src/lark_service/clouddoc/models.py (Document, BaseRecord, SheetRange, MediaAsset, FieldDefinition)

#### Doc 文档客户端

- [ ] T052 [P] [US3] 实现 Doc 客户端 src/lark_service/clouddoc/doc_client.py (create_document, append_content, get_document_content, update_block)
- [ ] T053 [US3] 实现文档权限管理 clouddoc/doc_client.py (grant_permission 授予权限, revoke_permission 撤销权限, list_permissions 查询权限, 支持可阅读/可编辑/可评论/可管理四种权限类型)

#### 多维表格客户端

- [ ] T054 [P] [US3] 实现 Bitable 客户端 src/lark_service/clouddoc/bitable_client.py (create_record, query_records 包含过滤器/分页, update_record, delete_record, 批量操作)

#### Sheet 客户端

- [ ] T055 [P] [US3] 实现 Sheet 客户端 src/lark_service/clouddoc/sheet_client.py (get_sheet_data 指定范围, update_sheet_data, format_cells 设置样式/字体/颜色/对齐, merge_cells 合并单元格, set_column_width 设置列宽行高, freeze_panes 冻结窗格)

#### 文档素材管理

- [ ] T056 [US3] 实现媒体客户端 src/lark_service/clouddoc/media_client.py (upload_doc_media 上传图片/文件, download_doc_media, 返回 file_token)

#### TDD 测试

- [ ] T057 [P] [US3] CloudDoc API 契约测试 tests/contract/test_clouddoc_contract.py (验证符合 contracts/clouddoc.yaml)
- [ ] T058 [P] [US3] Bitable 客户端单元测试 tests/unit/clouddoc/test_bitable_client.py (过滤器构建、分页)
- [ ] T059 [US3] CloudDoc 集成测试 tests/integration/test_clouddoc_e2e.py (创建 doc → 写入内容 → 读取 → 验证, CRUD bitable 记录)

### US4: Contact 模块

#### Pydantic 模型

- [ ] T060 [P] [US4] 创建 Contact 模型 src/lark_service/contact/models.py (User 包含 open_id/user_id/union_id, ChatGroup, Department)

#### 通讯录客户端

- [ ] T061 [US4] 实现 Contact 客户端 src/lark_service/contact/client.py (get_user_by_email, get_user_by_mobile, get_chat_by_name, get_department_users 批量更新缓存)
- [ ] T062 [US4] 实现用户缓存逻辑 contact/client.py (检查 PostgreSQL 缓存, TTL 24h, 未命中时懒加载刷新, app_id 隔离)

#### TDD 测试

- [ ] T063 [P] [US4] Contact API 契约测试 tests/contract/test_contact_contract.py (验证符合 contracts/contact.yaml)
- [ ] T064 [P] [US4] 用户缓存单元测试 tests/unit/contact/test_user_cache.py (TTL 过期、app_id 隔离)
- [ ] T065 [US4] Contact 集成测试 tests/integration/test_contact_e2e.py (查询用户 → 缓存 → 再次查询命中缓存 → 过期 → 刷新)

### 阶段检查点

- [ ] **构建验证**: `docker build -t lark-service:latest .` 成功
- [ ] **代码质量**: `ruff check src/lark_service/clouddoc/ src/lark_service/contact/` 无错误, `mypy` 通过
- [ ] **单元测试**: `pytest tests/unit/clouddoc/ tests/unit/contact/ -v` 全部通过
- [ ] **契约测试**: `pytest tests/contract/test_clouddoc_contract.py tests/contract/test_contact_contract.py -v` 通过
- [ ] **功能验证**: 
  - CloudDoc: 创建测试文档,插入内容,读取验证一致性;CRUD 多维表格记录
  - Contact: 通过邮箱查询用户,验证返回完整ID;再次查询验证缓存命中(无API调用)
- [ ] **文档更新**: 更新 docs/api_reference.md 补充 CloudDoc 和 Contact 模块文档

---

## Phase 5: US5 aPaaS 平台集成 (Priority: P4)

**目标**: 实现 aPaaS 数据空间表格 CRUD 操作 + AI 能力调用 + 工作流触发

**独立测试**: 查询工作空间表格列表,CRUD 记录,验证需要 user_access_token 权限

**预计时间**: ~2-3天

**依赖**: US1 (Token 管理,特别是 user_access_token 认证流程) 必须完成

### Pydantic 模型

- [ ] T066 [P] [US5] 创建 aPaaS 模型 src/lark_service/apaas/models.py (WorkspaceTable, TableRecord, FieldDefinition, Workflow, AICapability, WorkflowStatus enum)

### 数据空间客户端

- [ ] T067 [P] [US5] 实现工作空间表格客户端 src/lark_service/apaas/workspace_client.py (list_workspace_tables, query_table_records 包含过滤器/排序/分页, update_table_record 包含版本冲突检测, delete_table_record)

### AI 和工作流客户端

- [ ] T068 [P] [US5] 实现 AI 客户端 src/lark_service/apaas/ai_client.py (invoke_ai_capability 超时30s, 需要 user_access_token)
- [ ] T069 [P] [US5] 实现工作流客户端 src/lark_service/apaas/workflow_client.py (trigger_workflow, get_workflow_status, 需要 user_access_token)

### TDD 测试

- [ ] T070 [P] [US5] aPaaS API 契约测试 tests/contract/test_apaas_contract.py (验证符合 contracts/apaas.yaml)
- [ ] T071 [P] [US5] 工作空间客户端单元测试 tests/unit/apaas/test_workspace_client.py (查询过滤器构建、冲突检测)
- [ ] T072 [US5] aPaaS 集成测试 tests/integration/test_apaas_e2e.py (需要 user_access_token, 列表表格 → 查询记录 → 更新 → 删除 → 验证, 调用 AI 超时测试)

### 阶段检查点

- [ ] **构建验证**: `docker build -t lark-service:latest .` 成功
- [ ] **代码质量**: `ruff check src/lark_service/apaas/` 无错误, `mypy src/lark_service/apaas/` 通过
- [ ] **单元测试**: `pytest tests/unit/apaas/ -v` 全部通过
- [ ] **契约测试**: `pytest tests/contract/test_apaas_contract.py -v` 通过
- [ ] **功能验证**: 使用有效 user_access_token 查询工作空间表格,CRUD 记录;调用 AI 能力验证返回结果;权限不足时返回明确错误
- [ ] **文档更新**: 更新 docs/api_reference.md 补充 aPaaS 模块文档

---

## Phase 6: 集成测试、部署验证与文档完善

**目标**: 端到端测试、性能验证、Docker 部署、CI/CD 配置、文档完善

**预计时间**: ~2天

### 端到端集成测试

- [ ] T073 [P] 端到端测试 tests/integration/test_end_to_end.py (从应用配置初始化 → 获取Token → 发送消息 → 创建文档 → 查询用户 → 全流程验证)
- [ ] T074 [P] 并发测试 tests/integration/test_concurrency.py (100并发API调用,验证Token刷新不成为瓶颈,锁机制正常工作)
- [ ] T075 [P] 故障恢复测试 tests/integration/test_failure_recovery.py (数据库断连恢复、消息队列故障降级、Token失效重试)

### 性能与可靠性验证

- [ ] T076 执行性能基准测试 (模拟每秒100次并发调用,验证99.9%调用无需手动处理Token,响应时间99.9%<2秒根据SC-006)
- [ ] T077 验证边缘案例覆盖 (验证spec.md中29个边缘案例的处理逻辑,确保优雅降级)

### Docker 与部署

- [ ] T078 优化 Dockerfile (多阶段构建减少镜像大小,健康检查端点)
- [ ] T079 [P] 创建生产环境 docker-compose.yml (生产就绪配置,持久化卷,资源限制,重启策略)
- [ ] T080 [P] 创建 .github/workflows/ci.yml (GitHub Actions: lint → type-check → test → build → push)

### 文档完善

- [ ] T081 [P] 完善 docs/architecture.md (补充完整架构图,数据流图,模块依赖关系)
- [ ] T082 [P] 完善 docs/api_reference.md (所有模块的完整API文档,包含示例代码)
- [ ] T083 [P] 验证 quickstart.md (按quickstart.md步骤从零搭建,验证5分钟内完成首次消息发送)
- [ ] T084 创建 CHANGELOG.md (v0.1.0版本说明,核心功能清单,已知限制)

### 阶段检查点(最终验收)

- [ ] **构建验证**: `docker build -t lark-service:v0.1.0 .` 成功,镜像大小<500MB
- [ ] **代码质量**: `ruff check .` 零错误, `mypy src/` 覆盖率≥99%, `ruff format .` 代码格式化
- [ ] **CI验证**: GitHub Actions所有workflow通过(lint、type-check、test、build)
- [ ] **测试覆盖**: `pytest --cov=src/lark_service --cov-report=html` 覆盖率≥90%,关键业务逻辑≥95%
- [ ] **功能验证**: 
  - ✅ 按quickstart.md完成5分钟快速开始,成功发送首条消息
  - ✅ 验证Token自动刷新(等待Token即将过期,触发主动刷新,下次调用使用新Token)
  - ✅ 验证服务重启后Token从数据库恢复
  - ✅ 验证多应用场景(配置2个app_id,验证Token隔离)
  - ✅ 验证交互式卡片回调处理(发送卡片→点击按钮→回调到消息队列→处理函数执行)
  - ✅ 验证用户缓存(查询用户→缓存命中→TTL过期→自动刷新)
- [ ] **性能验证**: 100并发/秒压测通过,99.9%调用无需手动Token管理,Token刷新无性能瓶颈
- [ ] **文档完整**: README.md、docs/、quickstart.md、CHANGELOG.md 全部就位且准确
- [ ] **部署验证**: `docker-compose -f docker-compose.prod.yml up -d` 启动成功,健康检查通过,可对外提供服务

---

## 依赖关系与执行顺序

### 阶段依赖

```
Phase 1 (Setup)
    ↓
Phase 2 (US1 Token 管理) ← Foundational, 阻塞所有其他用户故事
    ↓
    ├─→ Phase 3 (US2 消息服务)
    ├─→ Phase 4 (US3 云文档 + US4 通讯录) ← 可并行开发
    └─→ Phase 5 (US5 aPaaS平台)
    ↓
Phase 6 (集成测试与部署)
```

### 用户故事依赖

- **US1 (P1)**: 无依赖 - Foundational 组件
- **US2 (P2)**: 依赖 US1 完成 (需要 CredentialPool.get_token())
- **US3 (P3)**: 依赖 US1 完成 (需要 Token 管理)
- **US4 (P3)**: 依赖 US1 完成 (需要 Token 管理 + UserCache in PostgreSQL)
- **US5 (P4)**: 依赖 US1 完成 (需要 user_access_token 认证流程)

### 关键路径

**最短路径到MVP** (仅实现 US1 + US2):
```
Phase 1 (Setup) → Phase 2 (US1) → Phase 3 (US2) → 部分 Phase 6 (基础集成测试)
预计时间: 7-9天
```

**完整功能交付** (US1-US5):
```
Phase 1 → Phase 2 → Phase 3 → Phase 4 (并行US3+US4) → Phase 5 → Phase 6
预计时间: 14-18天
```

### 并行执行机会

#### Phase 1 (Setup)
可并行任务: T003, T004, T005, T006, T007, T008, T011, T012, T013, T014, T015

#### Phase 2 (US1 Foundational)
- 数据库模型(T016-T019)可并行创建
- 核心基础设施(T022-T026)可并行实现
- 单元测试(T033-T036)可并行编写

#### Phase 3 (US2)
- T039 (模型) 和 T040 (上传器) 可并行
- T043 (卡片构建器) 可与 T040-T042 并行

#### Phase 4 (US3 + US4)
**US3 和 US4 可完全并行开发** (不同模块,无依赖):
- US3: T050-T057 (CloudDoc模块)
- US4: T058-T063 (Contact模块)

#### Phase 5 (US5)
- T064 (模型), T065-T067 (客户端) 可在模型完成后并行

#### Phase 6 (集成测试)
- T071-T073 (集成测试) 可并行执行
- T077-T082 (文档和配置) 可并行完成

---

## 并行示例: Phase 2 (US1 Foundational)

```bash
# 步骤 1: 并行创建所有数据库模型
任务 T016: 创建 Application 模型 (SQLite)
任务 T017: 创建 TokenStorage 模型 (PostgreSQL)
任务 T018: 创建 UserCache 模型 (PostgreSQL)
任务 T019: 创建 UserAuthSession 模型 (PostgreSQL)

# 步骤 2: 创建迁移脚本(依赖模型完成)
任务 T020: 创建 Alembic 迁移
任务 T021: SQLite 初始化脚本

# 步骤 3: 并行实现核心基础设施
任务 T022: 配置加载器
任务 T023: 自定义异常
任务 T024: StandardResponse
任务 T025: 日志设置
任务 T026: 参数校验器

# 步骤 4: 实现存储服务(依赖模型和配置)
任务 T027: SQLite 存储服务
任务 T028: PostgreSQL 存储服务

# 步骤 5: 并发控制和 Token 凭证池(依赖存储服务)
任务 T029: 锁管理器
任务 T030: 重试策略
任务 T031: CredentialPool
任务 T032: lark-oapi SDK 集成

# 步骤 6: 并行编写所有单元测试
任务 T033-T036: 单元测试
任务 T037-T038: 集成测试
```

---

## 实施策略

### 策略 1: MVP 优先 (US1 + US2, ~9天)

**目标**: 实现核心凭证管理和基础消息发送,可快速验证价值

1. ✅ Phase 1: Setup (1天)
2. ✅ Phase 2: US1 凭证管理 (4天) → **停止并验证**
   - 验证: Token 自动获取、刷新、多应用隔离、数据库持久化
3. ✅ Phase 3: US2 消息服务 (3天) → **停止并验证**
   - 验证: 发送文本、图片、文件、卡片消息
4. ✅ 部分 Phase 6: 基础集成测试 (1天)
   - 验证: quickstart.md 5分钟快速开始

**交付物**: 可用的Python包,支持消息发送和自动凭证管理

### 策略 2: 增量交付 (US1-US5, ~16天)

**目标**: 每个用户故事独立交付,增量构建完整功能

1. ✅ Setup → US1 (凭证管理) → 测试并部署 ✅ **里程碑 1: MVP核心**
2. ✅ US2 (消息服务) → 测试并部署 ✅ **里程碑 2: 可用消息系统**
3. ✅ US3 (云文档) + US4 (通讯录) 并行 → 测试并部署 ✅ **里程碑 3: 完整办公套件**
4. ✅ US5 (aPaaS平台) → 测试并部署 ✅ **里程碑 4: 高级集成**
5. ✅ Phase 6 (完整集成测试和部署验证) ✅ **里程碑 5: 生产就绪**

### 策略 3: 并行团队开发 (3人团队)

**前提**: Phase 1 + Phase 2 (US1) 必须由团队共同完成

**Phase 2 (US1) 完成后**:
- **开发者 A**: Phase 3 (US2 消息服务)
- **开发者 B**: Phase 4 (US3 云文档)
- **开发者 C**: Phase 4 (US4 通讯录)

**Phase 3-4 完成后**:
- **开发者 A**: Phase 5 (US5 aPaaS平台)
- **开发者 B + C**: Phase 6 (集成测试和文档完善)

**预计时间**: 12-14天 (相比串行节省 4-6天)

---

## Constitution 合规性检查清单

### 每个阶段结束必须验证以下原则:

#### ✅ I. 核心技术栈
- [ ] 使用 Python 3.12
- [ ] 使用官方 lark-oapi SDK (无自行实现基础调用)

#### ✅ II. 代码质量门禁
- [ ] `mypy src/` 静态类型覆盖率 ≥ 99%
- [ ] `ruff check .` 零错误
- [ ] 所有公共函数/类包含标准格式 Docstring (Args/Returns/Raises/Example)

#### ✅ III. 架构完整性
- [ ] 5个模块(core, messaging, clouddoc, contact, apaas) 无循环依赖
- [ ] `import` 检查确认仅单向依赖 core 模块

#### ✅ IV. 响应一致性
- [ ] 所有API返回 StandardResponse (code, message, request_id, data/error)

#### ✅ V. 安全性底线
- [ ] Token 使用 PostgreSQL pg_crypto 加密
- [ ] App Secret 使用 Fernet 加密
- [ ] 环境变量注入敏感配置(无硬编码)

#### ✅ VI. 环境一致性
- [ ] 单一目录结构 (src/, tests/, docs/, migrations/)

#### ✅ VII. 零信任安全
- [ ] `.env` 管理所有密钥
- [ ] `.gitignore` 排除 .env
- [ ] 代码中无硬编码凭据

#### ✅ VIII. 测试先行 (TDD)
- [ ] 所有实现任务前先完成对应测试任务
- [ ] 验证测试失败后再实现功能(红-绿-重构)

#### ✅ IX. 文档语言规范
- [ ] 代码/Docstring/日志/变量命名使用英文
- [ ] 文档/README/设计文档使用中文

#### ✅ X. 文件操作闭环
- [ ] 所有文档(spec.md, plan.md, tasks.md, data-model.md)原地更新
- [ ] 无冗余或重复文件

---

## 注意事项

- **[P] 标记**: 不同文件,无依赖,可并行执行
- **[Story] 标签**: 追溯任务到具体用户故事
- **TDD 原则**: 所有测试任务必须在实现任务前完成并验证失败
- **独立测试**: 每个用户故事完成后可独立测试,不依赖其他故事
- **阶段检查点**: 每个阶段结束必须通过构建验证、代码质量、CI验证、功能验证、文档更新
- **提交策略**: 每完成一个任务或逻辑组立即 commit
- **停止并验证**: 在任何检查点停止,独立验证该阶段功能正常后再继续

---

## 总结

- **总任务数**: 82 个
- **总阶段数**: 6 个 (符合≤6个阶段要求)
- **用户故事**: 5 个 (US1-P1, US2-P2, US3-P3, US4-P3, US5-P4)
- **并行机会**: 
  - Setup 阶段: 9 个并行任务
  - US1 阶段: 15 个并行任务
  - US3 + US4: 完全并行 (可节省 3-4天)
- **MVP 范围**: Phase 1 + Phase 2 (US1) + Phase 3 (US2) = 9天
- **完整交付**: 所有 6 个阶段 = 16-18天 (串行) 或 12-14天 (3人并行)
- **独立测试**: 每个用户故事都有明确的独立测试标准
- **Constitution 合规**: 所有阶段检查点包含 10 条核心原则验证
