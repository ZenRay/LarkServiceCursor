# Lark Service API Reference

**Version**: 0.1.0
**Last Updated**: 2026-01-18
**Status**: Production Ready

本文档提供 Lark Service 所有模块的完整 API 参考,包括方法签名、参数说明、返回值和使用示例。

---

## 目录

1. [核心模块 (Core)](#1-核心模块-core)
   - [CredentialPool](#11-credentialpool)
   - [Config](#12-config)
   - [ApplicationManager](#13-applicationmanager)
2. [消息模块 (Messaging)](#2-消息模块-messaging)
   - [MessagingClient](#21-messagingclient)
   - [MediaUploader](#22-mediauploader)
3. [卡片模块 (CardKit)](#3-卡片模块-cardkit)
   - [CardBuilder](#31-cardbuilder)
   - [CallbackHandler](#32-callbackhandler)
4. [云文档模块 (CloudDoc)](#4-云文档模块-clouddoc)
   - [DocClient](#41-docclient)
   - [BitableClient](#42-bitableclient)
   - [SheetClient](#43-sheetclient)
5. [通讯录模块 (Contact)](#5-通讯录模块-contact)
   - [ContactClient](#51-contactclient)
   - [CacheManager](#52-cachemanager)
6. [aPaaS 模块](#6-apaas-模块)
   - [WorkspaceTableClient](#61-workspacetableclient)
7. [CLI 工具](#7-cli-工具)

---

## 1. 核心模块 (Core)

### 1.1 CredentialPool

**路径**: `lark_service.core.credential_pool`

Token 凭证池,负责自动获取、刷新和管理飞书 API 的访问令牌。

#### 初始化

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.config import Config
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.core.storage.postgres_storage import TokenStorageService

config = Config()
app_manager = ApplicationManager(config.config_db_path, config.config_encryption_key)
token_storage = TokenStorageService(config.get_postgres_url())

pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage,
    lock_dir=Path("/tmp/lark_locks")
)
```

#### 方法

##### `get_token(app_id: str, token_type: str) -> str`

获取指定应用的访问令牌。自动处理缓存、刷新和并发控制。

**参数**:
- `app_id` (str): 应用 ID,如 "cli_xxx"
- `token_type` (str): Token 类型,支持:
  - `"app_access_token"`: 应用级别令牌
  - `"tenant_access_token"`: 租户级别令牌
  - `"user_access_token"`: 用户级别令牌

**返回**: `str` - 访问令牌字符串

**异常**:
- `TokenAcquisitionError`: Token 获取失败
- `ConfigError`: 应用配置不存在或无效

**示例**:

```python
# 获取应用级别 Token
token = pool.get_token("cli_myapp123", "app_access_token")
print(f"Token: {token}")

# 自动处理过期刷新,无需手动管理
token2 = pool.get_token("cli_myapp123", "app_access_token")  # 可能返回缓存的 Token
```

##### `refresh_token(app_id: str, token_type: str) -> str`

强制刷新指定应用的访问令牌。

**参数**:
- `app_id` (str): 应用 ID
- `token_type` (str): Token 类型

**返回**: `str` - 新的访问令牌

**示例**:

```python
# 强制刷新 Token (通常不需要手动调用)
new_token = pool.refresh_token("cli_myapp123", "app_access_token")
```

---

### 1.2 Config

**路径**: `lark_service.core.config`

配置管理类,从环境变量加载所有配置。

#### 初始化

```python
from lark_service.core.config import Config

# 自动从环境变量加载
config = Config()

# 或者显式指定配置
config = Config(
    postgres_host="localhost",
    postgres_port=5432,
    postgres_db="lark_service",
    log_level="INFO",
    max_retries=3,
    token_refresh_threshold=0.1
)
```

#### 属性

```python
config.postgres_host: str          # PostgreSQL 主机
config.postgres_port: int          # PostgreSQL 端口
config.postgres_db: str            # 数据库名
config.postgres_user: str          # 数据库用户
config.postgres_password: str      # 数据库密码
config.config_encryption_key: bytes  # 配置加密密钥
config.log_level: str              # 日志级别
config.max_retries: int            # 最大重试次数
config.retry_backoff_base: float   # 重试退避基数
config.token_refresh_threshold: float  # Token 刷新阈值 (0.1 = 剩余 10% 时刷新)
```

#### 方法

##### `get_postgres_url() -> str`

获取 PostgreSQL 连接字符串。

**返回**: `str` - 格式: `postgresql://user:pass@host:port/db`

**示例**:

```python
db_url = config.get_postgres_url()
# "postgresql://lark:password@localhost:5432/lark_service"
```

---

### 1.3 ApplicationManager

**路径**: `lark_service.core.storage.sqlite_storage`

管理飞书应用配置的 SQLite 存储服务。

#### 初始化

```python
from lark_service.core.storage.sqlite_storage import ApplicationManager
from cryptography.fernet import Fernet

encryption_key = Fernet.generate_key()
manager = ApplicationManager(
    db_path="config/applications.db",
    encryption_key=encryption_key
)
```

#### 方法

##### `add_application(app_id: str, app_name: str, app_secret: str) -> None`

添加新的应用配置。

**参数**:
- `app_id` (str): 应用 ID
- `app_name` (str): 应用名称
- `app_secret` (str): 应用密钥 (将自动加密存储)

**示例**:

```python
manager.add_application(
    app_id="cli_myapp123",
    app_name="My Application",
    app_secret="your_app_secret_here"
)
```

##### `get_application(app_id: str) -> dict[str, Any] | None`

获取应用配置。

**返回**: 包含应用信息的字典,或 None

**示例**:

```python
app = manager.get_application("cli_myapp123")
if app:
    print(f"App Name: {app['app_name']}")
    print(f"App Secret: {app['app_secret']}")  # 已自动解密
```

##### `list_applications() -> list[dict[str, Any]]`

列出所有应用。

**返回**: 应用配置列表

**示例**:

```python
apps = manager.list_applications()
for app in apps:
    print(f"{app['app_id']}: {app['app_name']} (Active: {app['is_active']})")
```

---

## 2. 消息模块 (Messaging)

### 2.1 MessagingClient

**路径**: `lark_service.messaging.client`

发送各种类型的飞书消息。

#### 初始化

```python
from lark_service.messaging.client import MessagingClient

client = MessagingClient(credential_pool)
```

#### 方法

##### `send_text_message(app_id: str, receive_id: str, receive_id_type: str, content: str) -> dict[str, Any]`

发送文本消息。

**参数**:
- `app_id` (str): 应用 ID
- `receive_id` (str): 接收者 ID
- `receive_id_type` (str): ID 类型,可选值:
  - `"open_id"`: 开放平台 ID
  - `"user_id"`: 用户 ID
  - `"union_id"`: 统一 ID
  - `"email"`: 邮箱地址
  - `"chat_id"`: 群聊 ID
- `content` (str): 消息文本内容

**返回**: `dict` - 包含 `message_id` 等信息

**示例**:

```python
result = client.send_text_message(
    app_id="cli_myapp123",
    receive_id="ou_user123",
    receive_id_type="open_id",
    content="Hello, this is a test message!"
)

print(f"Message sent: {result['message_id']}")
```

##### `send_rich_text_message(app_id: str, receive_id: str, receive_id_type: str, content: list[list[dict]]) -> dict[str, Any]`

发送富文本消息(支持格式化文本、链接、@提醒等)。

**参数**:
- `content` (list[list[dict]]): 富文本内容结构

**示例**:

```python
# 富文本: 段落 → 行 → 元素
content = [
    [  # 第一段
        {"tag": "text", "text": "这是粗体文本", "style": ["bold"]},
        {"tag": "a", "text": "点击链接", "href": "https://example.com"},
    ],
    [  # 第二段
        {"tag": "text", "text": "普通文本"},
        {"tag": "at", "user_id": "ou_user456"},  # @某人
    ]
]

result = client.send_rich_text_message(
    app_id="cli_myapp123",
    receive_id="ou_user123",
    receive_id_type="open_id",
    content=content
)
```

##### `send_image_message(app_id: str, receive_id: str, receive_id_type: str, image_path: str) -> dict[str, Any]`

发送图片消息(自动上传图片)。

**参数**:
- `image_path` (str): 本地图片文件路径

**示例**:

```python
result = client.send_image_message(
    app_id="cli_myapp123",
    receive_id="ou_user123",
    receive_id_type="open_id",
    image_path="/path/to/image.jpg"
)
```

##### `send_card_message(app_id: str, receive_id: str, receive_id_type: str, card: dict) -> dict[str, Any]`

发送交互式卡片消息。

**参数**:
- `card` (dict): 卡片 JSON 结构(通常由 CardBuilder 生成)

**示例**:

```python
from lark_service.cardkit.builder import CardBuilder

builder = CardBuilder()
card = builder.build_notification_card(
    title="系统通知",
    content="您有一个新的待办事项",
    note="请及时处理"
)

result = client.send_card_message(
    app_id="cli_myapp123",
    receive_id="ou_user123",
    receive_id_type="open_id",
    card=card
)
```

##### `send_batch_messages(app_id: str, receive_ids: list[str], receive_id_type: str, message_type: str, content: Any) -> list[dict]`

批量发送消息。

**参数**:
- `receive_ids` (list[str]): 接收者 ID 列表
- `message_type` (str): 消息类型 ("text", "image", "card" 等)
- `content` (Any): 消息内容(根据 message_type 而定)

**返回**: `list[dict]` - 每个接收者的发送结果

**示例**:

```python
results = client.send_batch_messages(
    app_id="cli_myapp123",
    receive_ids=["ou_user1", "ou_user2", "ou_user3"],
    receive_id_type="open_id",
    message_type="text",
    content="批量通知消息"
)

for result in results:
    print(f"User {result['receive_id']}: {result['status']}")
```

---

### 2.2 MediaUploader

**路径**: `lark_service.messaging.media_uploader`

上传图片和文件到飞书。

#### 方法

##### `upload_image(app_id: str, image_path: str) -> str`

上传图片并返回 image_key。

**参数**:
- `app_id` (str): 应用 ID
- `image_path` (str): 图片文件路径

**返回**: `str` - image_key

**限制**:
- 文件大小: ≤ 20MB
- 支持格式: jpg, jpeg, png, gif, bmp, webp

**示例**:

```python
from lark_service.messaging.media_uploader import MediaUploader

uploader = MediaUploader(credential_pool)
image_key = uploader.upload_image("cli_myapp123", "/path/to/photo.jpg")
print(f"Uploaded image: {image_key}")
```

---

## 3. 卡片模块 (CardKit)

### 3.1 CardBuilder

**路径**: `lark_service.cardkit.builder`

构建交互式卡片。

#### 方法

##### `build_notification_card(title: str, content: str, note: str = "") -> dict`

构建通知类卡片。

**示例**:

```python
from lark_service.cardkit.builder import CardBuilder

builder = CardBuilder()
card = builder.build_notification_card(
    title="审批通知",
    content="您有一个报销申请需要审批",
    note="申请人: 张三 | 金额: ¥1,234.56"
)
```

##### `build_approval_card(title: str, applicant: str, content: str, approve_button: bool = True) -> dict`

构建审批类卡片(带按钮)。

**示例**:

```python
card = builder.build_approval_card(
    title="报销申请",
    applicant="张三",
    content="差旅费用报销",
    approve_button=True
)
```

---

## 4. 云文档模块 (CloudDoc)

### 4.1 DocClient

**路径**: `lark_service.clouddoc.doc_client`

飞书文档操作。

#### 方法

##### `get_document(app_id: str, doc_id: str) -> Document`

获取文档元数据。

**示例**:

```python
from lark_service.clouddoc.doc_client import DocClient

client = DocClient(credential_pool)
doc = client.get_document("cli_myapp123", "doccnXXX")

print(f"Title: {doc.title}")
print(f"Owner: {doc.owner_id}")
```

---

### 4.2 BitableClient

**路径**: `lark_service.clouddoc.bitable.client`

多维表格操作。

#### 方法

##### `query_records(app_id: str, app_token: str, table_id: str, filter: str = "", page_size: int = 100) -> list[dict]`

查询记录。

**示例**:

```python
from lark_service.clouddoc.bitable.client import BitableClient

client = BitableClient(credential_pool)
records = client.query_records(
    app_id="cli_myapp123",
    app_token="bascnXXX",
    table_id="tblXXX",
    filter='CurrentValue.[Status] = "进行中"',
    page_size=50
)

for record in records:
    print(record["fields"])
```

##### `create_record(app_id: str, app_token: str, table_id: str, fields: dict) -> dict`

创建记录。

**示例**:

```python
record = client.create_record(
    app_id="cli_myapp123",
    app_token="bascnXXX",
    table_id="tblXXX",
    fields={
        "Name": "新任务",
        "Status": "待开始",
        "Priority": "高"
    }
)

print(f"Created record: {record['record_id']}")
```

---

## 5. 通讯录模块 (Contact)

### 5.1 ContactClient

**路径**: `lark_service.contact.client`

用户和部门查询。

#### 方法

##### `get_user_by_email(app_id: str, email: str) -> User`

根据邮箱查询用户。

**示例**:

```python
from lark_service.contact.client import ContactClient

client = ContactClient(credential_pool, enable_cache=True)
user = client.get_user_by_email("cli_myapp123", "user@example.com")

print(f"Name: {user.name}")
print(f"Open ID: {user.open_id}")
print(f"User ID: {user.user_id}")
print(f"Email: {user.email}")
```

##### `batch_get_users_by_id(app_id: str, user_ids: list[str]) -> list[User]`

批量获取用户信息。

**示例**:

```python
users = client.batch_get_users_by_id(
    app_id="cli_myapp123",
    user_ids=["ou_user1", "ou_user2", "ou_user3"]
)

for user in users:
    print(f"{user.name} ({user.email})")
```

---

## 6. aPaaS 模块

### 6.1 WorkspaceTableClient

**路径**: `lark_service.apaas.client`

数据空间表格操作。

#### 方法

##### `list_workspace_tables(app_id: str, user_access_token: str, workspace_id: str) -> list[WorkspaceTable]`

列出工作空间的所有表格。

**示例**:

```python
from lark_service.apaas.client import WorkspaceTableClient

client = WorkspaceTableClient(credential_pool)
tables = client.list_workspace_tables(
    app_id="cli_myapp123",
    user_access_token="u-xxx",
    workspace_id="wspXXX"
)

for table in tables:
    print(f"{table.name} (ID: {table.table_id})")
```

##### `sql_query(app_id: str, user_access_token: str, workspace_id: str, sql: str) -> tuple[list[dict], list[str], dict]`

执行 SQL 查询(核心方法)。

**参数**:
- `sql` (str): SQL 语句(SELECT/INSERT/UPDATE/DELETE)

**返回**: `tuple`
  - `list[dict]`: 记录列表
  - `list[str]`: 列名列表
  - `dict`: 元数据(total, has_more等)

**示例**:

```python
# SELECT 查询
records, columns, metadata = client.sql_query(
    app_id="cli_myapp123",
    user_access_token="u-xxx",
    workspace_id="wspXXX",
    sql="SELECT * FROM users WHERE status = 'active' LIMIT 10"
)

print(f"Columns: {columns}")
for record in records:
    print(record)

# INSERT 操作
created, _, _ = client.sql_query(
    app_id="cli_myapp123",
    user_access_token="u-xxx",
    workspace_id="wspXXX",
    sql="INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com') RETURNING id"
)

# UPDATE 操作
updated, _, _ = client.sql_query(
    app_id="cli_myapp123",
    user_access_token="u-xxx",
    workspace_id="wspXXX",
    sql="UPDATE users SET status = 'inactive' WHERE id = '123'"
)

# DELETE 操作
deleted, _, _ = client.sql_query(
    app_id="cli_myapp123",
    user_access_token="u-xxx",
    workspace_id="wspXXX",
    sql="DELETE FROM users WHERE status = 'inactive'"
)
```

##### `batch_create_records(app_id: str, user_access_token: str, workspace_id: str, table_name: str, records: list[dict]) -> list[dict]`

批量创建记录(自动分块,500 条/批)。

**示例**:

```python
import pandas as pd

# 从 DataFrame 批量导入
df = pd.read_csv("users.csv")
records = df.to_dict("records")

results = client.batch_create_records(
    app_id="cli_myapp123",
    user_access_token="u-xxx",
    workspace_id="wspXXX",
    table_name="users",
    records=records
)

print(f"Created {len(results)} records")
```

---

## 7. CLI 工具

### 命令行管理工具

```bash
# 添加应用
lark-service-cli app add \
  --app-id cli_myapp123 \
  --app-name "My Application" \
  --app-secret "your_secret_here"

# 列出所有应用
lark-service-cli app list

# 显示应用详情
lark-service-cli app show cli_myapp123

# 更新应用
lark-service-cli app update cli_myapp123 --app-name "New Name"

# 禁用应用
lark-service-cli app disable cli_myapp123

# 启用应用
lark-service-cli app enable cli_myapp123

# 删除应用
lark-service-cli app delete cli_myapp123 --force
```

---

## 8. 异常处理

### 常见异常

```python
from lark_service.core.exceptions import (
    TokenAcquisitionError,  # Token 获取失败
    ConfigError,            # 配置错误
    APIError,               # API 调用错误
    ValidationError,        # 参数验证错误
)

try:
    token = pool.get_token("cli_myapp123", "app_access_token")
except TokenAcquisitionError as e:
    print(f"Failed to acquire token: {e}")
except ConfigError as e:
    print(f"Configuration error: {e}")
except APIError as e:
    print(f"API error: {e.code} - {e.message}")
```

---

## 9. 最佳实践

### 9.1 Token 管理

```python
# ✅ 推荐: 复用 CredentialPool 实例
pool = CredentialPool(...)
client1 = MessagingClient(pool)
client2 = ContactClient(pool)

# ❌ 不推荐: 为每个客户端创建新的 Pool
client1 = MessagingClient(CredentialPool(...))
client2 = ContactClient(CredentialPool(...))
```

### 9.2 批量操作

```python
# ✅ 推荐: 使用批量 API
results = client.send_batch_messages(app_id, user_ids, "text", "Hello")

# ❌ 不推荐: 循环单次调用
for user_id in user_ids:
    client.send_text_message(app_id, user_id, "open_id", "Hello")
```

### 9.3 缓存使用

```python
# ✅ 推荐: 启用缓存(减少 API 调用)
client = ContactClient(pool, enable_cache=True)

# 首次调用: 从 API 获取并缓存
user = client.get_user_by_email(app_id, "user@example.com")

# 后续调用: 从缓存读取(24h TTL)
user = client.get_user_by_email(app_id, "user@example.com")
```

### 9.4 错误处理

```python
from lark_service.core.exceptions import APIError, TokenAcquisitionError

try:
    result = client.send_text_message(...)
except TokenAcquisitionError:
    # Token 获取失败 - 检查应用配置
    logger.error("Token acquisition failed")
except APIError as e:
    # API 调用失败 - 重试或降级处理
    if e.code == 99991663:  # Rate limit
        time.sleep(30)
        # 重试
    else:
        logger.error(f"API error: {e}")
```

---

## 10. 性能建议

### 10.1 连接池配置

```python
# PostgreSQL 连接池
engine = create_engine(
    db_url,
    pool_size=10,        # 根据并发量调整
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

### 10.2 并发控制

```python
# 对于高并发场景,使用连接池和异步
import concurrent.futures

def send_to_user(user_id):
    return client.send_text_message(app_id, user_id, "open_id", "Hello")

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = executor.map(send_to_user, user_ids)
```

---

## 附录

### A. 完整示例

```python
#!/usr/bin/env python3
"""Complete example of using Lark Service."""

from pathlib import Path
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.core.storage.postgres_storage import TokenStorageService
from lark_service.messaging.client import MessagingClient
from lark_service.cardkit.builder import CardBuilder

# 1. 初始化配置
config = Config()
app_manager = ApplicationManager(config.config_db_path, config.config_encryption_key)
token_storage = TokenStorageService(config.get_postgres_url())

# 2. 创建 Token 池
pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage,
    lock_dir=Path("/tmp/lark_locks")
)

# 3. 创建客户端
messaging = MessagingClient(pool)
builder = CardBuilder()

# 4. 发送消息
app_id = "cli_myapp123"
user_id = "ou_user123"

# 文本消息
result = messaging.send_text_message(
    app_id=app_id,
    receive_id=user_id,
    receive_id_type="open_id",
    content="Hello from Lark Service!"
)
print(f"Message sent: {result['message_id']}")

# 卡片消息
card = builder.build_notification_card(
    title="System Notification",
    content="Your task has been completed",
    note="Click to view details"
)
result = messaging.send_card_message(
    app_id=app_id,
    receive_id=user_id,
    receive_id_type="open_id",
    card=card
)
print(f"Card sent: {result['message_id']}")

# 5. 清理资源
pool.close()
token_storage.close()
app_manager.close()
```

---

**文档维护**: Lark Service Team
**反馈**: 如有问题或建议,请提交 Issue
**更新频率**: 随版本发布同步更新
