# Implementation Plan: Lark Service 核心组件

**Branch**: `001-lark-service-core` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-lark-service-core/spec.md`

## Summary

为内部系统开发 Lark Service 核心组件,通过封装飞书 OpenAPI 提供高度复用且透明的接入能力。核心价值包括:
1. **动态应用配置管理**: SQLite 存储应用配置,支持运行时增删改查,无需重启服务
2. **全自动 Token 管理闭环**: 支持多应用(app_id)隔离的 Token 自动管理,PostgreSQL 持久化存储,懒加载启动策略
3. **模块化服务封装**: Messaging(消息/图片/文件)、CloudDoc(Doc/Sheet/多维表格)、Contact(通讯录)、aPaaS(AI平台)
4. **生产级可靠性**: 智能重试(指数退避)、并发控制(线程锁+进程锁)、消息队列异步回调、标准化响应

技术方案基于 Python 3.12 + lark-oapi SDK + 混合存储(SQLite + PostgreSQL) + RabbitMQ,采用领域驱动设计,严格遵循项目宪章的 10 条核心原则。

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: 
- lark-oapi (官方 SDK)
- pydantic v2 (强类型校验和数据验证)
- SQLAlchemy 2.0 (ORM,支持 PostgreSQL)
- psycopg2-binary (PostgreSQL 驱动)
- pika (RabbitMQ 客户端)
- ruff (代码格式化和 linting)
- mypy (静态类型检查)
- pytest (测试框架)
- pytest-asyncio (异步测试支持)

**Storage**: 
- SQLite (应用配置管理,轻量级,文件级加密)
- PostgreSQL (Token 持久化存储,高并发,字段级加密)  
**Message Queue**: RabbitMQ (交互式卡片回调异步处理)  
**Testing**: pytest + pytest-cov (单元测试/集成测试/契约测试)  
**Target Platform**: Linux server (Docker 容器化部署)  
**Project Type**: Single library package (可作为 Python 包被内部服务导入)  
**Performance Goals**: 
- 支持每秒 100 次并发 API 调用
- Token 刷新不成为性能瓶颈
- 99.9% 的调用无需手动处理 Token 失效

**Constraints**: 
- Token 预刷新时间窗口: 剩余 10% 有效期时触发
- API 重试最大次数: 3 次(指数退避 1s→2s→4s)
- 限流重试延迟: 30 秒
- 用户认证超时: 10 分钟
- 并发锁超时: 30 秒

**Scale/Scope**: 
- 支持多应用场景(app_id 隔离)
- 预期内部服务并发量: 每秒数百次调用
- 模块数量: 5 个核心模块(凭证、消息、文档、通讯录、aPaaS)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 核心原则合规性检查

| 原则 | 要求 | 状态 | 说明 |
|------|------|------|------|
| **I. 核心技术栈** | Python 3.X + lark-oapi SDK | ✅ PASS | Python 3.12 + 官方 lark-oapi SDK |
| **II. 代码质量门禁** | 99% mypy + ruff + Docstring | ✅ PASS | 所有依赖已规划,CI 集成 mypy/ruff |
| **III. 架构完整性** | DDD + 禁止循环依赖 | ✅ PASS | 5 个独立模块,仅单向依赖凭证管理 |
| **IV. 响应一致性** | 标准化响应结构 | ✅ PASS | 统一 Response 模型(状态码/请求ID/错误上下文) |
| **V. 安全性底线** | 加密扩展 + 环境变量 | ✅ PASS | PostgreSQL 支持加密,仅环境变量注入配置 |
| **VI. 环境一致性** | 单一目录物理隔离 | ✅ PASS | 项目根目录包含 src/tests/docs/configs/ |
| **VII. 零信任安全** | .env + 禁止硬编码 | ✅ PASS | .env 管理密钥,.gitignore 排除 |
| **VIII. 测试先行** | TDD 红-绿-重构 | ✅ PASS | 先写失败测试,再实现功能 |
| **IX. 文档语言规范** | 代码英文 + 文档中文 | ✅ PASS | Docstring/代码英文,README/设计文档中文 |
| **X. 文件操作闭环** | 原地修改 + 禁止冗余 | ✅ PASS | 所有文件在原地迭代更新 |

**结论**: 所有宪章原则通过,无违规项,无需复杂性豁免。

---

## Architecture Design (架构设计细节)

### 分层架构与职责划分 (CHK002, CHK023, CHK118)

本项目采用 **领域驱动设计 (DDD)** 的分层架构,严格遵循单向依赖原则。

#### 层级结构

```
┌─────────────────────────────────────────┐
│         应用层 (Application Layer)        │  ← 业务模块:messaging/clouddoc/contact/apaas
│   职责:实现具体业务逻辑,调用核心层服务    │
└─────────────────┬───────────────────────┘
                  │ 单向依赖
                  ▼
┌─────────────────────────────────────────┐
│           核心层 (Core Layer)            │  ← 基础设施:credential/storage/retry/lock
│   职责:提供通用能力,不依赖业务模块      │
└─────────────────┬───────────────────────┘
                  │ 单向依赖
                  ▼
┌─────────────────────────────────────────┐
│         数据层 (Data Layer)              │  ← 数据模型:Application/TokenStorage/UserCache
│   职责:数据持久化,ORM 映射              │
└─────────────────────────────────────────┘
```

#### 核心层 (core/) 职责边界

**定义**: 提供与业务无关的通用基础设施,所有应用层模块都依赖它,但它不依赖任何应用层。

| 模块 | 职责 | 禁止行为 |
|------|------|---------|
| `config.py` | 加载和验证环境变量配置 | ❌ 不应包含业务逻辑 |
| `credential_pool.py` | Token 生命周期管理 (获取/刷新/缓存) | ❌ 不应调用业务模块 |
| `storage/` | 数据库访问抽象层 (SQLite/PostgreSQL) | ❌ 不应包含业务规则 |
| `lock_manager.py` | 并发控制 (线程锁+文件锁) | ❌ 不应依赖业务上下文 |
| `retry.py` | 重试策略 (指数退避) | ❌ 不应包含业务判断 |
| `response.py` | 标准化响应结构 | ❌ 不应依赖特定 API |
| `exceptions.py` | 通用异常定义 | ❌ 不应包含业务异常 |

**核心层设计原则**:
1. **高内聚**: 每个模块职责单一明确
2. **低耦合**: 模块间通过接口交互
3. **可测试**: 所有逻辑可独立单元测试
4. **可替换**: 存储层可切换实现 (SQLite ↔ PostgreSQL)

#### 应用层模块职责 (CHK002)

**定义**: 实现具体业务功能,封装飞书 API 调用,依赖核心层提供的能力。

| 模块 | 职责 | 核心依赖 |
|------|------|---------|
| `messaging/` | 消息发送、卡片交互、媒体上传 | `credential_pool`, `retry`, `response` |
| `clouddoc/` | 文档/表格/多维表格操作 | `credential_pool`, `retry`, `response` |
| `contact/` | 通讯录查询、用户缓存 | `credential_pool`, `storage`, `response` |
| `apaas/` | 数据空间、AI、工作流 | `credential_pool`, `retry`, `response` |

**应用层设计原则**:
1. **业务隔离**: 模块间禁止相互调用
2. **API 封装**: 屏蔽飞书 API 复杂性
3. **参数校验**: 调用前验证所有参数
4. **错误转换**: 将飞书错误转为内部语义化错误

#### 数据层职责

**定义**: 定义数据模型,处理持久化逻辑,ORM 映射。

| 模块 | 存储引擎 | 用途 |
|------|---------|------|
| `models/application.py` | SQLite | 应用配置 (低频读写) |
| `models/token_storage.py` | PostgreSQL | Token 缓存 (高频读写) |
| `models/user_cache.py` | PostgreSQL | 用户信息缓存 (24h TTL) |
| `models/auth_session.py` | PostgreSQL | 用户认证会话 (10min TTL) |

**数据层设计原则**:
1. **模型纯粹**: 仅包含数据定义和简单方法
2. **无业务逻辑**: 不包含复杂计算或判断
3. **类型安全**: 使用 SQLAlchemy 2.0 `Mapped[T]` 类型注解
4. **加密存储**: 敏感字段加密 (app_secret, token)

---

### 领域驱动设计 (DDD) 实践边界 (CHK022)

**DDD 在本项目中的应用范围**:

#### 采用的 DDD 概念

1. **分层架构** ✅
   - 应用层、核心层、数据层明确分离
   - 单向依赖,禁止循环引用

2. **聚合根 (Aggregate Root)** ✅
   - `CredentialPool`: Token 管理的聚合根
   - `Application`: 应用配置的聚合根
   - 通过聚合根访问相关实体

3. **值对象 (Value Object)** ✅
   - `StandardResponse`: 不可变的响应对象
   - `APIRequest`: 封装请求参数的值对象

4. **仓储模式 (Repository)** ✅
   - `ApplicationManager`: 应用配置仓储
   - `TokenStorageService`: Token 仓储
   - `PostgresStorage`: 用户缓存仓储

5. **领域服务 (Domain Service)** ✅
   - `CredentialPool`: 跨聚合的 Token 管理服务
   - `LockManager`: 并发控制服务

#### 不采用的 DDD 概念 (简化)

1. **领域事件 (Domain Event)** ❌
   - 项目规模较小,事件溯源过度设计

2. **CQRS (命令查询分离)** ❌
   - 读写模式简单,无需分离

3. **事件驱动架构** ❌ (部分)
   - 仅在卡片回调场景使用消息队列
   - 核心逻辑保持同步调用

4. **微服务拆分** ❌
   - 单体库设计,无需服务拆分

**DDD 实践原则**:
- ✅ 采用 DDD 的模块化和分层思想
- ✅ 使用聚合、仓储、领域服务等核心模式
- ❌ 不追求 DDD 的所有概念和复杂性
- ✅ 以实用性和可维护性为优先

---

### 配置优先级规则 (CHK015)

本项目配置加载遵循以下优先级(从高到低):

```
1. 环境变量 (最高优先级)
   ↓
2. .env 文件 
   ↓
3. 代码默认值 (最低优先级)
```

#### 详细规则

| 配置项 | 环境变量 | .env 文件 | 代码默认值 | 最终值 |
|--------|---------|-----------|-----------|--------|
| `LOG_LEVEL` | `ERROR` | `INFO` | `INFO` | `ERROR` ✅ |
| `POSTGRES_PORT` | - | `5433` | `5432` | `5433` ✅ |
| `TOKEN_REFRESH_THRESHOLD` | - | - | `0.1` | `0.1` ✅ |

#### 实现示例

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
    """Configuration with priority: ENV > .env > defaults."""
    
    # 默认值 (优先级 3)
    log_level: str = "INFO"
    postgres_port: int = 5432
    token_refresh_threshold: float = 0.1
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load config with priority handling."""
        # 加载 .env 文件 (优先级 2)
        load_dotenv()
        
        # 环境变量覆盖 (优先级 1)
        return cls(
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            postgres_port=int(os.getenv("POSTGRES_PORT", cls.postgres_port)),
            token_refresh_threshold=float(
                os.getenv("TOKEN_REFRESH_THRESHOLD", cls.token_refresh_threshold)
            ),
        )
```

**配置覆盖场景**:
- **开发环境**: 使用 `.env.development`
- **生产环境**: 环境变量注入,不使用 .env 文件
- **CI 环境**: 环境变量注入,使用 `.env.ci`

---

## Project Structure

### Documentation (this feature)

```text
specs/001-lark-service-core/
├── plan.md              # 本文件(技术实施计划)
├── spec.md              # 功能规范
├── research.md          # Phase 0: 技术调研(待生成)
├── data-model.md        # Phase 1: 数据模型设计(待生成)
├── quickstart.md        # Phase 1: 快速开始指南(待生成)
├── contracts/           # Phase 1: API 契约(待生成)
│   ├── credential_pool.yaml
│   ├── messaging.yaml
│   ├── clouddoc.yaml
│   ├── contact.yaml
│   └── apaas.yaml
├── checklists/          # 质量检查清单
│   └── requirements.md
└── tasks.md             # Phase 2: 任务清单(由 /speckit.tasks 生成)
```

### Source Code (repository root)

```text
lark-service/
├── src/
│   └── lark_service/
│       ├── __init__.py
│       ├── core/                    # 核心基础设施
│       │   ├── __init__.py
│       │   ├── config.py            # 配置管理(.env加载)
│       │   ├── credential_pool.py   # Token管理(多应用隔离)
│       │   ├── storage.py           # 数据库存储层
│       │   ├── lock_manager.py      # 并发锁管理(线程锁+进程锁)
│       │   ├── retry.py             # 重试策略(指数退避)
│       │   ├── response.py          # 标准化响应模型
│       │   └── exceptions.py        # 自定义异常类型
│       ├── messaging/               # 消息服务模块
│       │   ├── __init__.py
│       │   ├── client.py            # 消息发送客户端
│       │   ├── models.py            # 消息模型(Message, ImageAsset, FileAsset)
│       │   ├── card_builder.py      # 交互式卡片构建器
│       │   ├── callback_handler.py  # 卡片回调处理(RabbitMQ)
│       │   └── media_uploader.py    # 图片/文件上传
│       ├── clouddoc/                # 云文档服务模块
│       │   ├── __init__.py
│       │   ├── doc_client.py        # Doc文档操作(CRUD,权限管理:可阅读/可编辑/可评论/可管理)
│       │   ├── sheet_client.py      # Sheet电子表格操作(读写,格式化:样式/合并/列宽/冻结)
│       │   ├── bitable_client.py    # 多维表格操作(CRUD,批量操作,过滤查询)
│       │   ├── media_client.py      # 文档素材上传下载(图片10MB,文件30MB)
│       │   └── models.py            # 文档模型(Document, BaseRecord, SheetRange, MediaAsset)
│       ├── contact/                 # 通讯录服务模块
│       │   ├── __init__.py
│       │   ├── client.py            # 通讯录查询客户端(邮箱/手机号查询,PostgreSQL缓存24h TTL)
│       │   └── models.py            # 用户模型(User包含open_id/user_id/union_id, ChatGroup, Department)
│       ├── apaas/                   # aPaaS平台服务模块
│       │   ├── __init__.py
│       │   ├── workspace_client.py  # 数据空间表格CRUD(需要user_access_token)
│       │   ├── ai_client.py         # AI能力调用(30秒超时)
│       │   ├── workflow_client.py   # 自动化工作流触发
│       │   └── models.py            # aPaaS模型(WorkspaceTable, TableRecord, Workflow, AICapability)
│       └── utils/                   # 工具函数
│           ├── __init__.py
│           ├── logger.py            # 日志配置
│           └── validators.py        # 参数校验
│
├── tests/
│   ├── unit/                        # 单元测试
│   │   ├── core/
│   │   ├── messaging/
│   │   ├── clouddoc/
│   │   ├── contact/
│   │   └── apaas/
│   ├── integration/                 # 集成测试
│   │   ├── test_end_to_end.py
│   │   └── test_token_lifecycle.py
│   └── contract/                    # 契约测试
│       ├── test_messaging_contract.py
│       └── test_clouddoc_contract.py
│
├── docs/                            # 文档
│   ├── architecture.md              # 架构设计文档
│   ├── api_reference.md             # API参考文档
│   └── deployment.md                # 部署指南
│
├── migrations/                      # 数据库迁移脚本
│   └── versions/
│
├── .env.example                     # 环境变量模板
├── pyproject.toml                   # 项目配置(依赖、构建、工具配置)
├── requirements.txt                 # 依赖锁定文件
├── README.md                        # 项目说明
├── Dockerfile                       # Docker镜像构建
├── docker-compose.yml               # 本地开发环境(PostgreSQL + RabbitMQ)
└── .gitignore                       # Git忽略规则
```

**Structure Decision**: 采用 **Option 1: Single project** 结构。这是一个 Python 库项目,供内部服务以包的形式导入使用,不是独立的 web/mobile 应用。按功能域(Messaging、CloudDoc、Contact、aPaaS)清晰划分模块,核心基础设施(凭证管理、存储、重试)统一放在 `core/` 目录,避免循环依赖。

## Complexity Tracking

> 本项目无宪章违规项,此表留空。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

---

## Phase 0: 技术调研 (Research)

**目标**: 解决所有技术选型和最佳实践问题,为 Phase 1 设计提供充分依据。

### 调研任务清单

1. **SQLite vs PostgreSQL 持久化方案对比**
   - 评估标准: 并发性能、加密支持、部署复杂度、扩展性
   - 输出: 最优方案选择和理由

2. **RabbitMQ vs Redis Pub/Sub 回调处理方案对比**
   - 评估标准: 消息可靠性、持久化能力、性能、运维成本
   - 输出: 最优方案选择和理由

3. **线程锁+进程锁实现方案**
   - 调研 threading.Lock + multiprocessing.Lock 最佳实践
   - 锁超时机制设计
   - 避免死锁的模式

4. **user_access_token 认证流程设计**
   - 调研飞书 OAuth 2.0 授权流程
   - 卡片认证 vs 消息链接认证的实现方式
   - 认证会话管理(session_id、过期时间)

5. **lark-oapi SDK 使用最佳实践**
   - SDK 初始化和配置
   - 多应用(app_id)隔离的实现方式
   - SDK 的异常处理模式

6. **数据库 Schema 设计**
   - Token 存储表结构(支持加密字段)
   - 认证会话表结构
   - 索引优化策略

7. **Docker 容器化部署方案**
   - 多服务编排(应用 + PostgreSQL + RabbitMQ)
   - 环境变量注入最佳实践
   - 健康检查和容器重启策略

**输出文件**: `research.md` (包含所有调研结论和技术决策理由)

---

## Phase 1: 设计与契约 (Design & Contracts)

**前置条件**: research.md 完成

### 1.1 数据模型设计 (data-model.md)

**目标**: 定义所有核心实体的数据结构、关系和验证规则。

**核心实体**:

1. **TokenStorage** (数据库表: `tokens`)
   - 字段: app_id, token_type, token_value(加密), expires_at, created_at, updated_at
   - 索引: (app_id, token_type) 唯一索引
   - 加密: token_value 使用 PostgreSQL pg_crypto 扩展加密

2. **UserAuthSession** (数据库表: `auth_sessions`)
   - 字段: session_id, app_id, user_id, auth_method, state, expires_at, created_at
   - 索引: session_id 主键, (app_id, user_id) 索引

3. **CredentialPool** (内存对象)
   - 属性: app_id, tokens(Dict[TokenType, Token]), locks(Dict[TokenType, Lock])
   - 方法: get_token(), refresh_token(), clear_cache()

4. **Message** (Pydantic 模型)
   - 字段: receiver_id, msg_type, content, app_id
   - 验证: receiver_id 非空, msg_type 枚举值

5. **CallbackEvent** (Pydantic 模型)
   - 字段: event_type, card_id, user_action, signature, timestamp
   - 验证: 签名验证逻辑

**输出文件**: `data-model.md`

### 1.2 API 契约设计 (contracts/)

**目标**: 定义所有模块暴露的接口契约(OpenAPI 格式)。

**契约文件**:

1. **credential_pool.yaml**: 凭证管理接口
   - `POST /credentials/token` - 获取指定类型 Token
   - `POST /credentials/refresh` - 刷新 Token
   - `DELETE /credentials/{app_id}` - 清除指定应用缓存

2. **messaging.yaml**: 消息服务接口
   - `POST /messaging/text` - 发送文本消息
   - `POST /messaging/image` - 发送图片消息
   - `POST /messaging/file` - 发送文件消息
   - `POST /messaging/card` - 发送交互式卡片
   - `POST /messaging/batch` - 批量发送消息

3. **clouddoc.yaml**: 云文档服务接口
   - `POST /clouddoc/documents` - 创建 Doc 文档
   - `GET /clouddoc/documents/{doc_id}` - 读取文档内容
   - `POST /clouddoc/bitable/records` - 创建多维表格记录
   - `GET /clouddoc/sheets/{sheet_id}/data` - 读取 Sheet 数据

4. **contact.yaml**: 通讯录服务接口
   - `GET /contact/users/by_email` - 根据邮箱查询用户
   - `GET /contact/departments/{dept_id}/users` - 获取部门成员

5. **apaas.yaml**: aPaaS 平台服务接口
   - `POST /apaas/ai/invoke` - 调用 AI 能力
   - `POST /apaas/workflows/trigger` - 触发工作流

**输出文件**: `contracts/*.yaml` (5 个 OpenAPI 规范文件)

### 1.3 快速开始指南 (quickstart.md)

**目标**: 提供 5 分钟快速上手文档,包含安装、配置、第一个调用。

**内容大纲**:
1. 环境要求(Python 3.12+, Docker Compose V2, PostgreSQL, RabbitMQ)
2. 安装步骤(`uv pip install lark-service` 或 `pip install lark-service`)
3. 配置 .env 文件(App ID/Secret)
4. 第一个消息发送示例代码
5. 验证 Token 自动刷新功能
6. 故障排查常见问题

**环境管理**:
- 推荐使用 Conda 管理 Python 环境
- 推荐使用 uv 作为包管理器 (速度提升 10-100x)
- 使用 Docker Compose V2 命令 (`docker compose` 而非 `docker-compose`)

**输出文件**: `quickstart.md`

### 1.4 CLI 工具设计

**目标**: 设计命令行工具用于管理应用配置,提供友好的用户交互体验。

#### 技术选型

| 组件 | 技术选择 | 理由 |
|------|---------|------|
| **命令行框架** | Click 8.x | 声明式命令定义,自动生成帮助文档,嵌套命令支持完善,社区活跃 |
| **表格输出** | Rich 13.x | 美观的表格展示,支持颜色和样式,提升用户体验 |
| **JSON 输出** | 内置 json 模块 | 无额外依赖,支持 `--json` 选项便于脚本集成 |
| **密码输入** | Click.prompt(hide_input=True) | 安全输入敏感信息,避免命令行历史记录泄露 |

#### 命令结构

```bash
lark-service-cli                     # 主命令(通过 python -m lark_service.cli 或安装后的命令调用)
├── app                              # 应用配置管理命令组
│   ├── add                          # 添加应用配置
│   │   --app-id TEXT               # 飞书应用 App ID (必需)
│   │   --app-secret TEXT           # 飞书应用 App Secret (必需,可交互式输入)
│   │   --name TEXT                 # 应用名称 (必需)
│   │   --description TEXT          # 应用描述 (可选)
│   │   --json                      # JSON 格式输出 (可选)
│   │
│   ├── list                         # 列出所有应用
│   │   --json                      # JSON 格式输出 (可选)
│   │
│   ├── show                         # 显示应用详情
│   │   --app-id TEXT               # 应用 ID (必需)
│   │   --json                      # JSON 格式输出 (可选)
│   │
│   ├── update                       # 更新应用配置
│   │   --app-id TEXT               # 应用 ID (必需)
│   │   --app-secret TEXT           # 新的 App Secret (可选)
│   │   --name TEXT                 # 新的应用名称 (可选)
│   │   --description TEXT          # 新的应用描述 (可选)
│   │   --json                      # JSON 格式输出 (可选)
│   │
│   ├── delete                       # 删除应用配置
│   │   --app-id TEXT               # 应用 ID (必需)
│   │   --force                     # 跳过确认 (可选)
│   │   --json                      # JSON 格式输出 (可选)
│   │
│   ├── enable                       # 启用应用
│   │   --app-id TEXT               # 应用 ID (必需)
│   │   --json                      # JSON 格式输出 (可选)
│   │
│   └── disable                      # 禁用应用
│       --app-id TEXT               # 应用 ID (必需)
│       --json                      # JSON 格式输出 (可选)
│
└── --help                           # 显示帮助信息
```

#### 实现要点

**1. 入口点配置** (`setup.py` 或 `pyproject.toml`):

```python
# setup.py
entry_points={
    'console_scripts': [
        'lark-service-cli=lark_service.cli:main',
    ],
}

# 或 pyproject.toml
[project.scripts]
lark-service-cli = "lark_service.cli:main"
```

**2. 命令实现示例** (`src/lark_service/cli/app.py`):

```python
import click
from rich.console import Console
from rich.table import Table
from lark_service.core.storage.sqlite_storage import ApplicationManager

console = Console()

@click.group()
def app():
    """应用配置管理命令组"""
    pass

@app.command()
@click.option('--app-id', required=True, help='飞书应用 App ID')
@click.option('--app-secret', prompt=True, hide_input=True, help='飞书应用 App Secret')
@click.option('--name', required=True, help='应用名称')
@click.option('--description', default='', help='应用描述')
@click.option('--json', 'output_json', is_flag=True, help='以 JSON 格式输出')
def add(app_id, app_secret, name, description, output_json):
    """添加飞书应用配置"""
    try:
        app_manager = ApplicationManager()
        app_manager.create_application(
            app_id=app_id,
            app_secret=app_secret,
            name=name,
            description=description
        )
        
        if output_json:
            click.echo(json.dumps({
                "status": "success",
                "app_id": app_id,
                "name": name
            }))
        else:
            console.print(f"✓ 应用配置已成功添加", style="green")
            console.print(f"  App ID: {app_id}")
            console.print(f"  Name: {name}")
        
        sys.exit(0)
    except Exception as e:
        if output_json:
            click.echo(json.dumps({"status": "error", "message": str(e)}))
        else:
            console.print(f"✗ 添加失败: {str(e)}", style="red")
        sys.exit(1)

@app.command()
@click.option('--json', 'output_json', is_flag=True, help='以 JSON 格式输出')
def list(output_json):
    """列出所有应用配置"""
    try:
        app_manager = ApplicationManager()
        apps = app_manager.list_applications()
        
        if output_json:
            click.echo(json.dumps([{
                "app_id": app.app_id,
                "name": app.name,
                "status": "active" if app.is_active else "disabled",
                "created_at": app.created_at.isoformat()
            } for app in apps]))
        else:
            table = Table(title="飞书应用配置列表")
            table.add_column("App ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Created At", style="magenta")
            
            for app in apps:
                status = "✓ Active" if app.is_active else "✗ Disabled"
                table.add_row(app.app_id, app.name, status, app.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            
            console.print(table)
        
        sys.exit(0)
    except Exception as e:
        if output_json:
            click.echo(json.dumps({"status": "error", "message": str(e)}))
        else:
            console.print(f"✗ 查询失败: {str(e)}", style="red")
        sys.exit(2)
```

**3. 安全性设计**:

- **app_secret 脱敏**: `show` 命令中显示为 `secret_****` (仅显示前 6 位和后 4 位)
- **交互式确认**: `delete` 命令需要用户输入 `yes` 确认,或使用 `--force` 跳过
- **密码输入**: `add` 和 `update` 命令的 `--app-secret` 支持 `prompt=True, hide_input=True`,避免命令行历史记录泄露
- **审计日志**: 所有配置变更操作记录到应用日志

**4. 错误处理与退出码**:

| 退出码 | 含义 | 示例场景 |
|-------|------|---------|
| **0** | 成功 | 操作成功完成 |
| **1** | 参数错误 | 缺少必需参数,参数格式错误,app_id 不存在 |
| **2** | 数据库错误 | SQLite 连接失败,写入失败,加密密钥错误 |
| **3** | 权限错误 | 文件权限不足,数据库文件不可写 |

**5. 用户体验优化**:

- **彩色输出**: 使用 Rich 库提供美观的表格和彩色文本
- **进度提示**: 长时间操作显示进度条或 spinner
- **详细帮助**: 每个命令支持 `--help` 显示详细说明和示例
- **友好错误**: 错误信息包含问题描述和修复建议

#### 测试策略

**单元测试** (`tests/unit/cli/test_app_commands.py`):

```python
from click.testing import CliRunner
from lark_service.cli.app import app

def test_app_add_success():
    runner = CliRunner()
    result = runner.invoke(app, ['add', 
        '--app-id', 'cli_test123',
        '--app-secret', 'secret_test',
        '--name', 'Test App',
        '--json'
    ])
    assert result.exit_code == 0
    assert 'success' in result.output

def test_app_list_json_output():
    runner = CliRunner()
    result = runner.invoke(app, ['list', '--json'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)

def test_app_delete_without_force_requires_confirmation():
    runner = CliRunner()
    result = runner.invoke(app, ['delete', '--app-id', 'cli_test123'], input='no\n')
    assert result.exit_code == 1
    assert '已取消' in result.output
```

**输出文件**: 
- `src/lark_service/cli/__init__.py`
- `src/lark_service/cli/app.py`
- `tests/unit/cli/test_app_commands.py`

### 1.5 Agent 上下文更新

运行 `.specify/scripts/bash/update-agent-context.sh cursor-agent` 更新 AI 辅助开发的上下文信息。

---

## Security Implementation (安全实施细节)

### 配置安全

**文件权限管理**:
```bash
# SQLite 配置文件权限
chmod 600 ./config/applications.db

# 生产环境 .env 文件权限
chmod 600 .env.production
```

**配置敏感度分类**:
| 类别 | 示例 | 存储方式 | 访问控制 |
|------|------|---------|---------|
| `public` | LOG_LEVEL, FEATURE_FLAGS | 环境变量或配置文件 | 无限制 |
| `internal` | POSTGRES_HOST, POSTGRES_PORT | 环境变量 | 仅内部网络 |
| `secret` | APP_SECRET, ENCRYPTION_KEY, POSTGRES_PASSWORD | 环境变量 + 加密存储 | 文件权限 0600 + 加密 |

**环境隔离策略**:
```bash
# 开发环境
.env.development  # 本地测试密钥和数据库

# 生产环境
.env.production   # 生产密钥,不同的数据库凭证

# CI 环境
.env.ci           # 测试专用密钥和临时数据库
```

### 密钥管理

**加密密钥规范**:
```python
# 生成符合 Fernet 规范的密钥 (Python)
from cryptography.fernet import Fernet
key = Fernet.generate_key()  # 32字节 URL-safe base64编码
print(key.decode())  # 输出: xxxxx...=

# 环境变量设置
export LARK_CONFIG_ENCRYPTION_KEY="xxxxx...="
```

**密钥轮换流程**:
```bash
# 1. 生成新密钥
lark-service-cli config generate-key

# 2. 轮换密钥并重新加密
lark-service-cli config rotate-key --new-key <new_key>

# 3. 更新环境变量
export LARK_CONFIG_ENCRYPTION_KEY="<new_key>"

# 4. 重启服务
docker compose restart
```

**日志脱敏规则**:
```python
# 密钥类信息脱敏
"app_secret": "cli_****"           # 仅显示前4位
"token": "****"                    # 完全隐藏
"password": "****"                 # 完全隐藏

# 日志示例
logger.info(f"App registered: app_id={app_id}, app_secret={app_secret[:4]}****")
```

### 依赖安全

**安全扫描工具配置**:
```yaml
# .github/workflows/security-scan.yml (示例)
name: Security Scan
on: [push, pull_request]

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Safety Check
        run: |
          pip install safety
          safety check --json --file requirements.txt
          # 阻止 CVSS ≥ 7.0 的漏洞
          
  docker-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Image
        run: docker build -t lark-service:latest .
      - name: Trivy Scan
        run: |
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy image --severity HIGH,CRITICAL lark-service:latest
```

**依赖更新策略**:
| 优先级 | CVSS 范围 | 响应时间 | 行动 |
|--------|----------|---------|------|
| P0 | ≥ 9.0 (严重) | 24小时 | 立即修复并发布补丁 |
| P1 | 7.0-8.9 (高危) | 7天 | 计划修复,下一个版本 |
| P2 | 4.0-6.9 (中危) | 30天 | 定期修复,月度更新 |
| P3 | < 4.0 (低危) | 90天 | 可选修复,季度评估 |

**依赖锁定最佳实践**:
```txt
# requirements.txt - 使用精确版本
lark-oapi==1.2.15          # ✅ 精确版本
pydantic==2.5.3            # ✅ 精确版本
SQLAlchemy==2.0.25         # ✅ 精确版本

# ❌ 避免范围版本
# lark-oapi>=1.2.0         # 可能引入不兼容版本
# pydantic~=2.5.0          # 可能引入漏洞版本
```

### 容器安全

**Dockerfile 安全最佳实践**:
```dockerfile
# 使用官方基础镜像
FROM python:3.12-slim AS base

# 非 root 用户运行
RUN groupadd -r larkuser -g 1001 && \
    useradd -r -u 1001 -g larkuser larkuser

# 最小权限文件复制
COPY --chown=larkuser:larkuser . /app
WORKDIR /app

# 切换到非 root 用户
USER 1001

# 仅暴露必需端口 (如果需要 HTTP 服务)
# EXPOSE 8000

CMD ["python", "-m", "lark_service"]
```

**镜像扫描集成**:
```bash
# CI 中的镜像扫描
trivy image --severity HIGH,CRITICAL --exit-code 1 lark-service:latest

# 本地扫描
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image lark-service:latest
```

### 环境隔离

**多环境配置矩阵**:
| 配置项 | 开发环境 | 生产环境 | 说明 |
|--------|---------|---------|------|
| ENCRYPTION_KEY | dev-key-xxx | prod-key-yyy | 不同密钥 |
| POSTGRES_HOST | localhost | prod-db.internal | 不同数据库 |
| LOG_LEVEL | DEBUG | INFO | 不同日志级别 |
| POSTGRES_PASSWORD | dev-password | <vault> | 生产使用密钥管理服务 |

**访问控制策略**:
```python
# 应用配置访问控制 (示例)
class ApplicationManager:
    def get_app_secret(self, app_id: str, app_context: str) -> str:
        """Get app secret with access control.
        
        Args:
            app_id: Application ID
            app_context: Calling context (dev/prod)
            
        Raises:
            PermissionError: If cross-context access detected
        """
        app = self.get_application(app_id)
        
        # 禁止跨应用访问
        if app_context not in ["dev", "prod"]:
            raise PermissionError("Invalid context")
            
        return app.get_decrypted_secret(self.encryption_key)
```

---

## Phase 2: 宪章复核 (Constitution Re-check)

**前置条件**: Phase 1 设计完成

重新验证 Constitution Check 表格中的所有原则,确保设计方案符合宪章要求:

- ✅ **原则 III (架构完整性)**: 检查 data-model.md 中的模块依赖图,确认无循环依赖
- ✅ **原则 IV (响应一致性)**: 检查 contracts/ 中的响应结构,确认统一包含状态码/请求ID/错误上下文
- ✅ **原则 V/VII (安全性)**: 检查 Token 存储设计使用加密,配置仅通过环境变量注入,已补充详细安全实施细节

**如发现违规**: 记录到 Complexity Tracking 表格并提供豁免理由,或回到 Phase 1 修正设计。

---

## 下一步

Phase 0 和 Phase 1 的具体内容将在后续步骤中生成。完成 Phase 1 后,使用 `/speckit.tasks` 命令生成任务清单(tasks.md),开始实施开发。

**预期产出文件**:
- ✅ plan.md (本文件)
- ⏳ research.md (Phase 0)
- ⏳ data-model.md (Phase 1)
- ⏳ quickstart.md (Phase 1)
- ⏳ contracts/*.yaml (Phase 1)
- ⏳ tasks.md (Phase 2, 由 /speckit.tasks 生成)
