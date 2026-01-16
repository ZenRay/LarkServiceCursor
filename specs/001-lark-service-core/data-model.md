# Data Model: Lark Service 核心组件

**Feature**: 001-lark-service-core
**Date**: 2026-01-14
**Phase**: Phase 1 - Data Model Design

## 概述

本文档定义 Lark Service 核心组件的所有数据实体、关系、验证规则和状态转换。数据模型分为三类:
1. **持久化实体**: 存储在 PostgreSQL 数据库中
2. **内存实体**: 运行时对象,不持久化
3. **传输对象**: API 请求/响应的 Pydantic 模型

---

## 1. 持久化实体 (Database Models)

### 1.1 Application (应用配置管理)

**用途**: 存储和管理飞书应用的配置信息

**存储**: SQLite (`config/applications.db`)
**表名**: `applications`

**字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| app_id | VARCHAR(64) | PRIMARY KEY | 飞书应用 ID (如 cli_xxx) |
| app_name | VARCHAR(128) | NOT NULL | 应用名称(便于识别) |
| app_secret | TEXT | NOT NULL | 应用密钥(加密存储) |
| description | TEXT | NULL | 应用描述 |
| status | VARCHAR(16) | DEFAULT 'active' | 应用状态(active/disabled) |
| permissions | TEXT | NULL | 应用权限范围(JSON 数组) |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |
| created_by | VARCHAR(64) | NULL | 创建者(用于审计) |

**索引**:
- `INDEX idx_apps_status(status)` - 快速查询启用的应用

**状态枚举**:
- `active`: 启用,可正常使用
- `disabled`: 禁用,拒绝 Token 获取

**验证规则**:
- app_id 必须匹配格式 `cli_[a-z0-9]{16}`
- app_name 必须唯一且非空
- status 必须是 `active` 或 `disabled`
- app_secret 加密后存储(使用 Fernet 对称加密)

**SQLAlchemy 模型 (SQLite)**:
```python
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

ConfigBase = declarative_base()

class Application(ConfigBase):
    """
    Lark application configuration.
    Stored in SQLite for lightweight config management.
    """
    __tablename__ = "applications"

    app_id = Column(String(64), primary_key=True)
    app_name = Column(String(128), nullable=False, unique=True)
    app_secret = Column(Text, nullable=False)  # Encrypted
    description = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="active")
    permissions = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(64), nullable=True)

    def is_active(self) -> bool:
        """Check if application is active."""
        return self.status == "active"

    def get_decrypted_secret(self, encryption_key: str) -> str:
        """Decrypt and return app secret."""
        from cryptography.fernet import Fernet
        cipher = Fernet(encryption_key)
        return cipher.decrypt(self.app_secret.encode()).decode()
```

**示例数据**:
```sql
INSERT INTO applications (app_id, app_name, app_secret, description, status)
VALUES (
    'cli_a1b2c3d4e5f6g7h8',
    '内部通知系统',
    'gAAAAABh...',  -- Encrypted secret
    '用于发送工单、审批等内部通知',
    'active'
);
```

---

### 1.2 TokenStorage (Token 持久化)

**用途**: 存储多应用的访问令牌,支持加密持久化

**存储**: PostgreSQL
**表名**: `tokens`

**字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增主键 |
| app_id | VARCHAR(64) | NOT NULL | 飞书应用 ID |
| token_type | VARCHAR(32) | NOT NULL | Token 类型(app_access/tenant_access/user_access) |
| token_value | TEXT | NOT NULL | 加密后的 Token 值(使用 pg_crypto) |
| expires_at | TIMESTAMP | NOT NULL | Token 过期时间 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**索引**:
- `UNIQUE(app_id, token_type)` - 确保每个应用的每种 Token 只有一条记录
- `INDEX idx_tokens_expires(expires_at)` - 用于清理过期 Token

**验证规则**:
- app_id 必须匹配格式 `cli_[a-z0-9]{16}`
- token_type 必须是枚举值: `app_access_token`, `tenant_access_token`, `user_access_token`
- expires_at 必须大于当前时间

**生命周期**:
```
[创建] → [使用中] → [即将过期(剩余10%)] → [刷新] → [使用中]
                                    ↓
                               [已过期] → [清除]
```

**SQLAlchemy 模型**:
```python
from sqlalchemy import Column, String, Text, DateTime, Integer, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TokenStorage(Base):
    """
    Persistent token storage with encryption.
    """
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(64), nullable=False)
    token_type = Column(String(32), nullable=False)
    token_value = Column(Text, nullable=False)  # Encrypted
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('app_id', 'token_type', name='uq_app_token'),
    )
```

---

### 1.3 UserCache (用户信息缓存)

**用途**: 缓存飞书用户信息,减少API调用,支持多应用隔离

**存储**: PostgreSQL
**表名**: `user_cache`

**字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增主键 |
| app_id | VARCHAR(64) | NOT NULL | 飞书应用 ID |
| open_id | VARCHAR(64) | NOT NULL | 应用维度用户 ID |
| user_id | VARCHAR(64) | NOT NULL | 租户维度用户 ID |
| union_id | VARCHAR(64) | NOT NULL | 企业维度唯一用户 ID |
| name | VARCHAR(128) | NULL | 用户姓名 |
| email | VARCHAR(255) | NULL | 用户邮箱 |
| mobile | VARCHAR(32) | NULL | 用户手机号 |
| avatar_url | TEXT | NULL | 用户头像 URL |
| department_ids | TEXT | NULL | 所属部门 ID 列表(JSON 数组) |
| employee_no | VARCHAR(64) | NULL | 员工工号 |
| cached_at | TIMESTAMP | DEFAULT NOW() | 缓存时间 |
| expires_at | TIMESTAMP | NOT NULL | 缓存过期时间(cached_at + 24h) |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

**索引**:
- `UNIQUE(app_id, open_id)` - 确保每个应用中 open_id 唯一
- `INDEX idx_user_cache_union(union_id)` - 按 union_id 查询
- `INDEX idx_user_cache_email(email)` - 按邮箱查询
- `INDEX idx_user_cache_mobile(mobile)` - 按手机号查询
- `INDEX idx_user_cache_expires(expires_at)` - 用于清理过期缓存

**验证规则**:
- app_id 必须匹配格式 `cli_[a-z0-9]{16}`
- open_id, user_id, union_id 必须非空
- expires_at = cached_at + 24 小时
- email 必须符合邮箱格式(如果非空)

**缓存策略**:
- **TTL**: 24 小时
- **刷新策略**: 懒加载(查询时检查 TTL,过期则从飞书刷新)
- **写入策略**: 每次查询飞书后都更新缓存
- **清理策略**: 定期任务清理过期 7 天以上的记录

**SQLAlchemy 模型**:
```python
from sqlalchemy import Column, String, Text, DateTime, Integer, func
from datetime import datetime, timedelta

class UserCache(Base):
    """
    User information cache with multi-app isolation.
    """
    __tablename__ = "user_cache"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(64), nullable=False)
    open_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)
    union_id = Column(String(64), nullable=False)
    name = Column(String(128), nullable=True)
    email = Column(String(255), nullable=True)
    mobile = Column(String(32), nullable=True)
    avatar_url = Column(Text, nullable=True)
    department_ids = Column(Text, nullable=True)  # JSON array
    employee_no = Column(String(64), nullable=True)
    cached_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('app_id', 'open_id', name='uq_app_open_id'),
    )

    def is_expired(self) -> bool:
        """Check if cache is expired."""
        return datetime.utcnow() > self.expires_at

    @staticmethod
    def calculate_expires_at(cached_at: datetime) -> datetime:
        """Calculate cache expiration time (24 hours)."""
        return cached_at + timedelta(hours=24)
```

**示例数据**:
```sql
INSERT INTO user_cache (
    app_id, open_id, user_id, union_id, name, email,
    mobile, department_ids, cached_at, expires_at
)
VALUES (
    'cli_a1b2c3d4e5f6g7h8',
    'ou_7d8a6e6e2a3c4b8d',
    'g4318d3b',
    'on_8ed6aa262f46s39f',
    '张三',
    'zhangsan@company.com',
    '+86-13800138000',
    '["od-123456", "od-234567"]',
    '2026-01-14 10:00:00',
    '2026-01-15 10:00:00'
);
```

---

### 1.4 UserAuthSession

**用途**: 管理用户 OAuth 认证会话

**表名**: `auth_sessions`

**字段**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| session_id | VARCHAR(64) | PRIMARY KEY | UUID 会话标识 |
| app_id | VARCHAR(64) | NOT NULL | 飞书应用 ID |
| user_id | VARCHAR(64) | NULL | 用户 ID(认证完成后填充) |
| auth_method | VARCHAR(16) | NOT NULL | 认证方式(link/card) |
| state | VARCHAR(16) | NOT NULL | 会话状态(pending/completed/expired) |
| redirect_uri | TEXT | NULL | OAuth 回调 URI(link 方式) |
| expires_at | TIMESTAMP | NOT NULL | 会话过期时间(10分钟) |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**索引**:
- `INDEX idx_auth_sessions_expires(expires_at)` - 用于清理过期会话
- `INDEX idx_auth_sessions_app_user(app_id, user_id)` - 查询用户认证历史

**状态转换**:
```
[创建] → pending
           ↓
       [用户授权] → completed
           ↓
      [超时未授权] → expired
```

**验证规则**:
- session_id 必须是有效的 UUID v4
- auth_method 必须是 `link` 或 `card`
- state 必须是 `pending`, `completed`, `expired` 之一
- expires_at 必须在创建时间后 10 分钟内

**SQLAlchemy 模型**:
```python
class UserAuthSession(Base):
    """
    OAuth authentication session management.
    """
    __tablename__ = "auth_sessions"

    session_id = Column(String(64), primary_key=True)
    app_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=True)
    auth_method = Column(String(16), nullable=False)
    state = Column(String(16), nullable=False, default="pending")
    redirect_uri = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

---

## 2. 内存实体 (Runtime Objects)

### 2.1 CredentialPool

**用途**: 运行时 Token 缓存和刷新管理

**属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| _clients | Dict[str, LarkClient] | 每个 app_id 的 SDK 客户端实例 |
| _tokens | Dict[Tuple[str, TokenType], Token] | 内存中的 Token 缓存 |
| _locks | Dict[Tuple[str, TokenType], TokenRefreshLock] | Token 刷新锁 |
| _storage | TokenStorageService | 数据库存储服务 |

**核心方法**:
```python
class CredentialPool:
    def get_token(self, app_id: str, token_type: TokenType) -> str:
        """
        Get token with automatic refresh.

        Args:
        ----------
            app_id: Lark application ID
            token_type: Type of token (app_access/tenant_access/user_access)

        Returns:
        ----------
            Valid token string

        Raises:
        ----------
            TokenAcquisitionError: If token cannot be obtained
        """
        pass

    def refresh_token(self, app_id: str, token_type: TokenType) -> str:
        """
        Force refresh token (bypassing cache).
        """
        pass

    def clear_cache(self, app_id: str) -> None:
        """
        Clear all cached tokens for an application.
        """
        pass
```

---

### 2.2 TokenRefreshLock

**用途**: 混合线程锁和进程锁,确保并发安全

**属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| app_id | str | 应用 ID |
| token_type | TokenType | Token 类型 |
| _thread_lock | threading.Lock | 线程锁 |
| _process_lock | FileLock | 进程锁(文件锁) |

**使用方式**:
```python
lock = TokenRefreshLock(app_id="cli_xxx", token_type="tenant_access_token")
with lock:
    # Critical section: refresh token
    new_token = sdk_client.get_token()
```

---

## 3. 传输对象 (DTOs / Pydantic Models)

### 3.1 Message

**用途**: 表示要发送的飞书消息

```python
from pydantic import BaseModel, Field
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    RICH_TEXT = "post"
    IMAGE = "image"
    FILE = "file"
    INTERACTIVE_CARD = "interactive"

class Message(BaseModel):
    """
    Lark message data transfer object.

    Attributes:
    ----------
        receiver_id: User ID or chat ID
        msg_type: Type of message
        content: Message content (structure varies by type)
        app_id: Application ID for token isolation
    """
    receiver_id: str = Field(..., min_length=1, description="Receiver user or chat ID")
    msg_type: MessageType = Field(..., description="Message type")
    content: dict = Field(..., description="Message content payload")
    app_id: str = Field(..., regex=r"^cli_[a-z0-9]{16}$", description="Lark app ID")

    class Config:
        use_enum_values = True
```

---

### 3.2 ImageAsset / FileAsset

**用途**: 表示上传的图片/文件资源

```python
class ImageAsset(BaseModel):
    """
    Uploaded image asset.
    """
    image_key: str = Field(..., description="Lark image key")
    image_type: str = Field(default="message", description="Image type")
    file_size: int = Field(..., gt=0, le=10*1024*1024, description="Size in bytes (max 10MB)")
    upload_time: datetime = Field(default_factory=datetime.now)

class FileAsset(BaseModel):
    """
    Uploaded file asset.
    """
    file_key: str = Field(..., description="Lark file key")
    file_name: str = Field(..., min_length=1, description="Original filename")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., gt=0, le=30*1024*1024, description="Size in bytes (max 30MB)")
    upload_time: datetime = Field(default_factory=datetime.now)
```

---

### 3.3 CallbackEvent

**用途**: 表示交互式卡片回调事件

```python
class CallbackEvent(BaseModel):
    """
    Interactive card callback event.
    """
    event_type: str = Field(..., description="Event type (e.g., card.action.trigger)")
    card_id: str = Field(..., description="Card ID")
    user_id: str = Field(..., description="User who triggered the action")
    action: dict = Field(..., description="Action payload")
    signature: str = Field(..., description="Lark callback signature")
    timestamp: datetime = Field(..., description="Event timestamp")
    app_id: str = Field(..., description="Application ID")

    def verify_signature(self, encryption_key: str) -> bool:
        """
        Verify Lark callback signature.

        Returns:
        ----------
            True if signature is valid, False otherwise
        """
        pass
```

---

### 3.4 StandardResponse

**用途**: 统一的 API 响应格式

```python
class StandardResponse(BaseModel):
    """
    Standardized API response structure.

    Attributes:
    ----------
        code: Business status code (0 = success)
        message: Human-readable message
        request_id: Unique request identifier for tracing
        data: Response payload (optional)
        error: Error details (optional)
    """
    code: int = Field(..., description="Business status code")
    message: str = Field(..., description="Response message")
    request_id: str = Field(..., description="Unique request ID")
    data: Optional[dict] = Field(None, description="Response data")
    error: Optional[dict] = Field(None, description="Error context")

    @classmethod
    def success(cls, data: dict, request_id: str, message: str = "Success") -> "StandardResponse":
        return cls(code=0, message=message, request_id=request_id, data=data)

    @classmethod
    def error(cls, code: int, message: str, request_id: str, error_details: dict = None) -> "StandardResponse":
        return cls(code=code, message=message, request_id=request_id, error=error_details)
```

---

### 3.5 User / ChatGroup (Contact 模块)

**用途**: 表示飞书用户和群组信息

```python
class User(BaseModel):
    """
    Lark user information.

    Attributes:
    ----------
        open_id: Application-scoped user ID
        user_id: Tenant-scoped user ID
        union_id: Enterprise-wide unique user ID
        name: User display name
        email: User email address
        mobile: User mobile number
        avatar_url: User avatar URL
        department_ids: List of department IDs user belongs to
        employee_no: Employee number
    """
    open_id: str = Field(..., description="App-scoped user ID")
    user_id: str = Field(..., description="Tenant-scoped user ID")
    union_id: str = Field(..., description="Enterprise-wide unique ID")
    name: Optional[str] = Field(None, description="User name")
    email: Optional[str] = Field(None, description="User email")
    mobile: Optional[str] = Field(None, description="User mobile")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    department_ids: List[str] = Field(default_factory=list, description="Department IDs")
    employee_no: Optional[str] = Field(None, description="Employee number")

class ChatGroup(BaseModel):
    """
    Lark chat group information.
    """
    chat_id: str = Field(..., description="Chat group ID")
    name: str = Field(..., description="Chat group name")
    owner_id: str = Field(..., description="Chat owner user ID")
    member_count: int = Field(..., ge=0, description="Number of members")
    created_at: Optional[datetime] = Field(None, description="Creation time")
```

---

### 3.6 WorkspaceTable / TableRecord (aPaaS 模块)

**用途**: 表示 aPaaS 数据空间的表格和记录

```python
class FieldDefinition(BaseModel):
    """
    Field definition in workspace table.
    """
    field_id: str = Field(..., description="Field ID")
    field_name: str = Field(..., description="Field name")
    field_type: str = Field(..., description="Field type (text, number, date, etc.)")
    is_required: bool = Field(default=False, description="Whether field is required")

class WorkspaceTable(BaseModel):
    """
    aPaaS workspace table metadata.

    Attributes:
    ----------
        workspace_id: Workspace ID
        table_id: Table ID
        table_name: Table display name
        fields: List of field definitions
        record_count: Number of records in table
    """
    workspace_id: str = Field(..., description="Workspace ID")
    table_id: str = Field(..., description="Table ID")
    table_name: str = Field(..., description="Table name")
    fields: List[FieldDefinition] = Field(default_factory=list, description="Field definitions")
    record_count: int = Field(default=0, ge=0, description="Number of records")

class TableRecord(BaseModel):
    """
    aPaaS workspace table record.

    Attributes:
    ----------
        record_id: Unique record ID
        table_id: Parent table ID
        fields: Field values as dictionary (field_id -> value)
        version: Record version for optimistic locking
        created_at: Record creation time
        updated_at: Record update time
    """
    record_id: str = Field(..., description="Record ID")
    table_id: str = Field(..., description="Parent table ID")
    fields: Dict[str, Any] = Field(..., description="Field values (field_id -> value)")
    version: Optional[int] = Field(None, description="Record version for conflict detection")
    created_at: Optional[datetime] = Field(None, description="Creation time")
    updated_at: Optional[datetime] = Field(None, description="Update time")

    def get_field_value(self, field_id: str, default: Any = None) -> Any:
        """
        Get field value by field ID.

        Args:
        ----------
            field_id: Field ID to retrieve
            default: Default value if field not found

        Returns:
        ----------
            Field value or default
        """
        return self.fields.get(field_id, default)
```

---

### 3.7 Workflow / AICapability (aPaaS 模块)

**用途**: 表示工作流和 AI 能力

```python
class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Workflow(BaseModel):
    """
    aPaaS workflow representation.
    """
    workflow_id: str = Field(..., description="Workflow ID")
    workflow_name: str = Field(..., description="Workflow name")
    execution_id: Optional[str] = Field(None, description="Execution ID (after trigger)")
    status: Optional[WorkflowStatus] = Field(None, description="Execution status")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    created_at: Optional[datetime] = Field(None, description="Creation time")

class AICapability(BaseModel):
    """
    aPaaS AI capability representation.
    """
    capability_id: str = Field(..., description="AI capability ID")
    capability_type: str = Field(..., description="Capability type (e.g., text_classification)")
    input_data: Dict[str, Any] = Field(..., description="Input data for AI")
    output_result: Optional[Dict[str, Any]] = Field(None, description="AI processing result")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Result confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
```

---

## 4. 实体关系图

```
[SQLite - 配置层]
┌──────────────────┐
│ Application      │
│──────────────────│
│ app_id (PK)      │
│ app_name         │
│ app_secret (enc) │
│ status           │
│ created_at       │
└──────────────────┘
          │
          │ (app_id 关联)
          │
          ▼
[PostgreSQL - 数据层]
┌─────────────────┐           ┌──────────────────┐           ┌──────────────────┐
│ TokenStorage    │           │ UserAuthSession  │           │ UserCache        │
│─────────────────│           │──────────────────│           │──────────────────│
│ id (PK)         │           │ session_id (PK)  │           │ id (PK)          │
│ app_id (FK)     │◄─────────┐│ app_id (FK)      │           │ app_id (FK)      │
│ token_type      │          ││ user_id          │           │ open_id (UQ)     │
│ token_value     │          ││ auth_method      │           │ user_id          │
│ expires_at      │          ││ state            │           │ union_id         │
│ created_at      │          ││ expires_at       │           │ name             │
│ updated_at      │          │└──────────────────┘           │ email            │
└─────────────────┘          │                               │ cached_at        │
          │                  │                               │ expires_at       │
          │                  │                               └──────────────────┘
          │                  │                                        │
          │                  │
          │                  │
          │ (app_id 查询)    │
          │                  │
          ▼                  │
[运行时内存层]               │
    ┌────────────────────┐  │
    │ CredentialPool     │◄─┘
    │────────────────────│
    │ _app_configs (map) │  ← 从 SQLite 加载
    │ _clients (map)     │
    │ _tokens (map)      │
    │ _locks (map)       │
    │ _storage           │
    └────────────────────┘
             │
             │ (使用)
             │
 ┌───────────┼───────────┐
 │           │           │
 ▼           ▼           ▼
┌────────┐ ┌──────────┐ ┌─────────┐
│Message │ │ImageAsset│ │FileAsset│
│────────│ │──────────│ │─────────│
│app_id  │ │image_key │ │file_key │
│content │ │file_size │ │file_size│
└────────┘ └──────────┘ └─────────┘

图例:
━━━ 数据库表关联
─── 运行时引用
(FK) 外键关联
(enc) 加密字段
```

---

## 5. 数据迁移策略

### 5.1 SQLite 初始化 (应用配置)

```python
# src/lark_service/db/init_config_db.py

from sqlalchemy import create_engine
from src.lark_service.models.config import ConfigBase, Application

def init_config_database(db_path: str = "config/applications.db"):
    """
    Initialize SQLite database for application configuration.
    """
    engine = create_engine(f"sqlite:///{db_path}")

    # Create tables
    ConfigBase.metadata.create_all(engine)

    # Create default application (optional)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if default app exists
    default_app = session.query(Application).filter_by(
        app_id=os.getenv("LARK_DEFAULT_APP_ID")
    ).first()

    if not default_app and os.getenv("LARK_DEFAULT_APP_ID"):
        # Add default app from environment variables
        from cryptography.fernet import Fernet
        cipher = Fernet(os.getenv("LARK_CONFIG_ENCRYPTION_KEY").encode())
        encrypted_secret = cipher.encrypt(
            os.getenv("LARK_DEFAULT_APP_SECRET").encode()
        ).decode()

        default_app = Application(
            app_id=os.getenv("LARK_DEFAULT_APP_ID"),
            app_name="Default Application",
            app_secret=encrypted_secret,
            status="active",
            created_by="system"
        )
        session.add(default_app)
        session.commit()
        print(f"✓ Created default application: {default_app.app_id}")

    session.close()
    print(f"✓ Config database initialized: {db_path}")
```

### 5.2 PostgreSQL 迁移 (Token 存储)

```python
# migrations/versions/001_initial_schema.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create tokens table
    op.create_table(
        'tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.String(length=64), nullable=False),
        sa.Column('token_type', sa.String(length=32), nullable=False),
        sa.Column('token_value', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('app_id', 'token_type', name='uq_app_token')
    )

    op.create_index('idx_tokens_expires', 'tokens', ['expires_at'])

    # Create auth_sessions table
    op.create_table(
        'auth_sessions',
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('app_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=True),
        sa.Column('auth_method', sa.String(length=16), nullable=False),
        sa.Column('state', sa.String(length=16), nullable=False),
        sa.Column('redirect_uri', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('session_id')
    )

    op.create_index('idx_auth_sessions_expires', 'auth_sessions', ['expires_at'])
    op.create_index('idx_auth_sessions_app_user', 'auth_sessions', ['app_id', 'user_id'])

    # Create user_cache table
    op.create_table(
        'user_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.String(length=64), nullable=False),
        sa.Column('open_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('union_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('mobile', sa.String(length=32), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('department_ids', sa.Text(), nullable=True),
        sa.Column('employee_no', sa.String(length=64), nullable=True),
        sa.Column('cached_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('app_id', 'open_id', name='uq_app_open_id')
    )

    op.create_index('idx_user_cache_union', 'user_cache', ['union_id'])
    op.create_index('idx_user_cache_email', 'user_cache', ['email'])
    op.create_index('idx_user_cache_mobile', 'user_cache', ['mobile'])
    op.create_index('idx_user_cache_expires', 'user_cache', ['expires_at'])

    # Enable pg_crypto extension for encryption
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

def downgrade():
    # Drop user_cache table
    op.drop_index('idx_user_cache_expires', table_name='user_cache')
    op.drop_index('idx_user_cache_mobile', table_name='user_cache')
    op.drop_index('idx_user_cache_email', table_name='user_cache')
    op.drop_index('idx_user_cache_union', table_name='user_cache')
    op.drop_table('user_cache')

    # Drop auth_sessions table
    op.drop_index('idx_auth_sessions_app_user', table_name='auth_sessions')
    op.drop_index('idx_auth_sessions_expires', table_name='auth_sessions')
    op.drop_table('auth_sessions')

    # Drop tokens table
    op.drop_index('idx_tokens_expires', table_name='tokens')
    op.drop_table('tokens')
```

---

## 6. 验证规则总结

| 实体 | 字段 | 验证规则 |
|------|------|---------|
| Application | app_id | 格式: `cli_[a-z0-9]{16}` |
| Application | status | 枚举: active, disabled |
| TokenStorage | app_id | 格式: `cli_[a-z0-9]{16}` |
| TokenStorage | token_type | 枚举: app_access_token, tenant_access_token, user_access_token |
| TokenStorage | expires_at | 必须 > 当前时间 |
| UserCache | app_id | 格式: `cli_[a-z0-9]{16}` |
| UserCache | open_id | 非空字符串 |
| UserCache | user_id | 非空字符串 |
| UserCache | union_id | 非空字符串 |
| UserCache | email | 邮箱格式(如果非空) |
| UserCache | expires_at | cached_at + 24小时 |
| UserAuthSession | session_id | UUID v4 格式 |
| UserAuthSession | auth_method | 枚举: link, card |
| UserAuthSession | state | 枚举: pending, completed, expired |
| Message | receiver_id | 非空字符串 |
| Message | msg_type | 枚举: text, post, image, file, interactive |
| ImageAsset | file_size | 0 < size ≤ 10MB |
| FileAsset | file_size | 0 < size ≤ 30MB |
| CallbackEvent | signature | 非空,需签名验证 |
| User | open_id, user_id, union_id | 非空字符串 |
| WorkspaceTable | workspace_id, table_id | 非空字符串 |
| TableRecord | record_id, table_id | 非空字符串 |
| Workflow | workflow_id | 非空字符串 |
| AICapability | capability_id | 非空字符串 |

---

## 7. 性能优化建议

1. **Token 缓存策略**:
   - 内存缓存优先(CredentialPool._tokens)
   - 数据库作为持久化备份
   - 缓存失效时间 = Token 过期时间 - 10%

2. **数据库索引**:
   - (app_id, token_type) 联合唯一索引 - 加速 Token 查询
   - expires_at 索引 - 加速过期数据清理
   - (app_id, user_id) 联合索引 - 加速用户认证历史查询

3. **连接池配置**:
   - SQLAlchemy pool_size=5 (常驻连接)
   - max_overflow=10 (峰值扩展)
   - pool_recycle=3600 (1小时回收连接)

4. **定时清理**:
   - 每小时清理过期 Token: `DELETE FROM tokens WHERE expires_at < NOW()`
   - 每小时清理过期认证会话: `DELETE FROM auth_sessions WHERE expires_at < NOW()`
   - 每天清理过期 7 天以上的用户缓存: `DELETE FROM user_cache WHERE expires_at < NOW() - INTERVAL '7 days'`

5. **用户缓存优化**:
   - 优先使用 union_id 索引查询(企业唯一)
   - email/mobile 索引适用于首次查询(未知 ID)
   - 批量查询时使用 IN 语句减少查询次数
   - 缓存命中率目标 ≥ 80%

---

**Phase 1 数据模型设计完成,进入 API 契约设计。**
