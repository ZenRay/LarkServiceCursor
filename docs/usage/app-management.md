# 应用管理 (Application Management)

本文档详细介绍如何在 LarkService 中管理和切换飞书应用。

## 概述

LarkService 支持管理多个飞书应用,并提供灵活的应用切换机制。每个服务客户端都支持 5 层 `app_id` 解析优先级,让您可以轻松在不同场景下使用不同的应用。

### 核心概念

- **CredentialPool**: 管理所有应用的凭证和 Token
- **ApplicationManager**: 存储和管理应用配置 (app_id, app_secret)
- **BaseServiceClient**: 所有服务客户端的基类,提供统一的 `app_id` 管理
- **app_id 解析优先级**: 5层优先级,从高到低:方法参数 > 上下文管理器 > 客户端默认 > CredentialPool 默认 > 自动检测

## 5层 app_id 解析优先级

LarkService 使用以下优先级来确定使用哪个应用:

1. **方法参数** (最高优先级)
2. **上下文管理器** (`use_app()`)
3. **客户端级别默认值**
4. **CredentialPool 级别默认值**
5. **自动检测** (仅一个应用时) - 由 `ApplicationManager.get_default_app_id()` 提供

如果所有层级都未指定 `app_id`,则抛出 `ConfigError` 异常。

## 场景 1: 单应用场景

如果您只使用一个飞书应用,LarkService 可以自动检测并使用它。

### 示例代码

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化配置
config = Config()

# 初始化存储服务
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)

# 创建 CredentialPool
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用配置
app_manager.add_application(
    app_id="cli_a1b2c3d4e5f60789",  # 您的飞书应用 ID
    app_secret="your_app_secret_min_16_chars_required",  # 应用密钥
    description="主应用",
)

# 创建客户端 - 无需指定 app_id,自动检测单一应用
messaging_client = MessagingClient(credential_pool)

# 发送消息 - 无需指定 app_id
result = messaging_client.send_text_message(receiver_id="ou_xxx", content="Hello!")

print(f"消息发送成功: {result}")
```

### 返回值示例

```python
{
    "code": 0,
    "msg": "success",
    "data": {
        "message_id": "om_abc123xyz456",
        "create_time": "1710000000"
    }
}
```

## 场景 2: 多应用场景 - 客户端级别默认值

当您需要同时使用多个飞书应用时,可以为每个客户端设置默认的 `app_id`。

### 示例代码

```python
from pathlib import Path

from lark_service.contact.client import ContactClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化配置
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加多个应用
app_manager.add_application(
    app_id="cli_app1_example_id",  # 应用1
    app_secret="app1_secret_min_16_chars_required",
    description="营销应用",
)
app_manager.add_application(
    app_id="cli_app2_example_id",  # 应用2
    app_secret="app2_secret_min_16_chars_required",
    description="客服应用",
)

# 使用工厂方法创建客户端,并指定默认 app_id
marketing_client = credential_pool.create_messaging_client(app_id="cli_app1_example_id")
support_client = credential_pool.create_messaging_client(app_id="cli_app2_example_id")

# 每个客户端使用其默认 app_id
marketing_result = marketing_client.send_text_message(receiver_id="ou_user1", content="营销消息")
support_result = support_client.send_text_message(receiver_id="ou_user2", content="客服消息")

print(f"营销消息: {marketing_result}")
print(f"客服消息: {support_result}")
```

### 返回值示例

```python
# marketing_result
{
    "code": 0,
    "msg": "success",
    "data": {"message_id": "om_marketing_msg_001", "create_time": "1710000100"}
}

# support_result
{
    "code": 0,
    "msg": "success",
    "data": {"message_id": "om_support_msg_001", "create_time": "1710000200"}
}
```

## 场景 3: 动态切换应用 - 使用上下文管理器

使用 `use_app()` 上下文管理器在代码块内临时切换应用。

### 示例代码

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加两个应用
app_manager.add_application(
    app_id="cli_default_app_id_123",
    app_secret="default_secret_min_16_chars_required",
    description="默认应用",
)
app_manager.add_application(
    app_id="cli_temp_app_id_456",
    app_secret="temp_secret_min_16_chars_required",
    description="临时应用",
)

# 创建客户端,使用默认应用
client = credential_pool.create_messaging_client(app_id="cli_default_app_id_123")

# 使用默认应用发送消息
default_result = client.send_text_message(receiver_id="ou_user1", content="使用默认应用")
print(f"默认应用: {client.get_current_app_id()}")  # cli_default_app_id_123

# 临时切换到其他应用
with client.use_app("cli_temp_app_id_456"):
    temp_result = client.send_text_message(receiver_id="ou_user2", content="使用临时应用")
    print(f"上下文内: {client.get_current_app_id()}")  # cli_temp_app_id_456

# 上下文结束后,自动切回默认应用
after_result = client.send_text_message(receiver_id="ou_user3", content="恢复默认应用")
print(f"上下文后: {client.get_current_app_id()}")  # cli_default_app_id_123
```

### 输出示例

```
默认应用: cli_default_app_id_123
上下文内: cli_temp_app_id_456
上下文后: cli_default_app_id_123
```

## 场景 4: 方法参数覆盖 - 最高优先级

方法参数 `app_id` 拥有最高优先级,可以覆盖所有其他设置。

### 示例代码

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_default_app_123",
    app_secret="default_secret_min_16_chars_required",
    description="默认应用",
)
app_manager.add_application(
    app_id="cli_override_app_456",
    app_secret="override_secret_min_16_chars_required",
    description="覆盖应用",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_default_app_123")

# 方法参数覆盖客户端默认值
result = client.send_text_message(receiver_id="ou_user1", content="覆盖消息", app_id="cli_override_app_456")

# 验证使用了覆盖的 app_id (通过日志或返回值)
print(f"当前客户端默认: {client.get_current_app_id()}")  # cli_default_app_123
print(f"消息结果: {result}")
```

### 返回值示例

```python
{
    "code": 0,
    "msg": "success",
    "data": {"message_id": "om_override_msg_001", "create_time": "1710000300"}
}
```

## 场景 5: 嵌套上下文管理器

支持嵌套使用 `use_app()`,内层上下文的 `app_id` 优先级更高。

### 示例代码

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_app1_nested_123",
    app_secret="app1_secret_min_16_chars_required",
    description="应用1",
)
app_manager.add_application(
    app_id="cli_app2_nested_456",
    app_secret="app2_secret_min_16_chars_required",
    description="应用2",
)
app_manager.add_application(
    app_id="cli_app3_nested_789",
    app_secret="app3_secret_min_16_chars_required",
    description="应用3",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_app1_nested_123")

print(f"默认: {client.get_current_app_id()}")  # cli_app1_nested_123

with client.use_app("cli_app2_nested_456"):
    print(f"外层: {client.get_current_app_id()}")  # cli_app2_nested_456

    with client.use_app("cli_app3_nested_789"):
        print(f"内层: {client.get_current_app_id()}")  # cli_app3_nested_789

    print(f"外层恢复: {client.get_current_app_id()}")  # cli_app2_nested_456

print(f"默认恢复: {client.get_current_app_id()}")  # cli_app1_nested_123
```

### 输出示例

```
默认: cli_app1_nested_123
外层: cli_app2_nested_456
内层: cli_app3_nested_789
外层恢复: cli_app2_nested_456
默认恢复: cli_app1_nested_123
```

## 实用工具方法

### 获取当前应用 ID

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_current_app_123",
    app_secret="current_secret_min_16_chars_required",
    description="当前应用",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_current_app_123")

# 获取当前应用 ID
current_app = client.get_current_app_id()
print(f"当前使用的应用: {current_app}")  # cli_current_app_123

# 如果没有可解析的 app_id,返回 None (不抛出异常)
client_no_default = MessagingClient(credential_pool)  # 假设没有默认值
result = client_no_default.get_current_app_id()
print(f"无默认值时: {result}")  # None 或有效的 app_id (如果有自动检测)
```

### 列出所有可用应用

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_app_list_001",
    app_secret="app1_secret_min_16_chars_required",
    description="应用1",
)
app_manager.add_application(
    app_id="cli_app_list_002",
    app_secret="app2_secret_min_16_chars_required",
    description="应用2",
)

# 创建客户端
client = credential_pool.create_messaging_client()

# 列出所有可用的应用 ID
available_apps = client.list_available_apps()
print(f"可用应用: {available_apps}")  # ['cli_app_list_001', 'cli_app_list_002']

# 遍历应用
for app_id in available_apps:
    with client.use_app(app_id):
        print(f"当前应用: {client.get_current_app_id()}")
```

### 输出示例

```
可用应用: ['cli_app_list_001', 'cli_app_list_002']
当前应用: cli_app_list_001
当前应用: cli_app_list_002
```

## 错误处理

### 未指定 app_id

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import ConfigError
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加多个应用
app_manager.add_application(
    app_id="cli_error_app_001",
    app_secret="app1_secret_min_16_chars_required",
    description="应用1",
)
app_manager.add_application(
    app_id="cli_error_app_002",
    app_secret="app2_secret_min_16_chars_required",
    description="应用2",
)

# 创建客户端,没有指定默认 app_id
client = MessagingClient(credential_pool)

try:
    # 调用方法时没有提供 app_id,会抛出异常
    client.send_text_message(receiver_id="ou_user1", content="测试消息")
except ConfigError as e:
    print(f"错误: {e}")
    # 错误: Unable to determine app_id. Please provide it as a method parameter,
    # set a client default, use a context manager, or configure a default in CredentialPool.
    # Available apps: cli_error_app_001, cli_error_app_002

    # 解决方法: 使用任一优先级方式指定 app_id
    with client.use_app("cli_error_app_001"):
        result = client.send_text_message(receiver_id="ou_user1", content="修复后的消息")
        print(f"成功: {result}")
```

### 应用不存在

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import ConfigError
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_valid_app_123",
    app_secret="valid_secret_min_16_chars_required",
    description="有效应用",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_valid_app_123")

try:
    # 使用不存在的 app_id
    with client.use_app("cli_nonexistent_app"):
        client.send_text_message(receiver_id="ou_user1", content="测试")
except ConfigError as e:
    print(f"错误: {e}")
    # 错误: Application 'cli_nonexistent_app' not found in CredentialPool.
```

## 线程安全注意事项

`use_app()` 上下文管理器的堆栈是线程本地的 (thread-local),但不支持在 **同一客户端实例** 上从 **不同线程** 并发切换应用。

### 推荐做法

- **单线程**: 在同一线程内使用 `use_app()` 是完全安全的
- **多线程**: 每个线程应使用自己的客户端实例

### 示例代码

```python
import threading
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化 (共享)
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(postgres_url=config.postgres_url)
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_thread_app_001",
    app_secret="app1_secret_min_16_chars_required",
    description="线程应用1",
)
app_manager.add_application(
    app_id="cli_thread_app_002",
    app_secret="app2_secret_min_16_chars_required",
    description="线程应用2",
)


def worker(app_id: str, user_id: str) -> None:
    # 每个线程创建自己的客户端实例
    client = credential_pool.create_messaging_client(app_id=app_id)
    result = client.send_text_message(receiver_id=user_id, content=f"来自 {app_id}")
    print(f"线程 {threading.current_thread().name}: {result}")


# 创建多个线程
thread1 = threading.Thread(target=worker, args=("cli_thread_app_001", "ou_user1"))
thread2 = threading.Thread(target=worker, args=("cli_thread_app_002", "ou_user2"))

thread1.start()
thread2.start()

thread1.join()
thread2.join()
```

## 最佳实践

1. **单应用场景**: 无需手动指定 `app_id`,依赖自动检测
2. **多应用场景**: 使用工厂方法为每个客户端设置默认 `app_id`
3. **临时切换**: 使用 `use_app()` 上下文管理器
4. **显式覆盖**: 在方法参数中传递 `app_id` (最高优先级)
5. **错误处理**: 捕获 `ConfigError` 并提供清晰的错误信息
6. **多线程**: 每个线程使用独立的客户端实例

## 相关文档

- [消息服务](messaging.md)
- [通讯录服务](contact.md)
- [云文档服务](clouddoc.md)
- [aPaaS 服务](apaas.md)
- [高级用法](advanced.md)
