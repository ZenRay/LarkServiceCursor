# 高级用法

本文档介绍 LarkService 的高级使用场景和最佳实践。

## 目录

- [多应用管理](#多应用管理)
- [自定义重试策略](#自定义重试策略)
- [批量操作优化](#批量操作优化)
- [错误处理最佳实践](#错误处理最佳实践)
- [日志配置](#日志配置)
- [性能优化](#性能优化)
- [安全最佳实践](#安全最佳实践)

## 多应用管理

详细的多应用管理指南请参考 [应用管理文档](app-management.md)。这里展示一些高级场景。

### 动态应用切换策略

根据业务逻辑动态选择使用哪个应用。

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_vip_app_123456",
    app_secret="vip_secret_min_16_chars_required",
    description="VIP用户应用",
)
app_manager.add_application(
    app_id="cli_normal_app_789",
    app_secret="normal_secret_min_16_chars_required",
    description="普通用户应用",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_normal_app_789")


def send_message_by_user_level(user_id: str, content: str, is_vip: bool = False) -> dict:
    """根据用户等级选择不同应用发送消息"""
    if is_vip:
        # VIP用户使用专属应用
        with client.use_app("cli_vip_app_123456"):
            return client.send_text_message(receiver_id=user_id, content=f"[VIP] {content}")
    else:
        # 普通用户使用默认应用
        return client.send_text_message(receiver_id=user_id, content=content)


# 使用示例
vip_result = send_message_by_user_level("ou_vip_user", "尊享服务", is_vip=True)
normal_result = send_message_by_user_level("ou_normal_user", "标准服务", is_vip=False)

print(f"VIP消息: {vip_result}")
print(f"普通消息: {normal_result}")
```

### 多服务客户端协同

在复杂业务流程中协同使用多个服务客户端。

```python
from pathlib import Path

from lark_service.clouddoc.client import DocClient
from lark_service.contact.client import ContactClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_workflow_app_123",
    app_secret="workflow_secret_min_16_chars_required",
    description="工作流应用",
)

# 创建多个服务客户端,共享同一个应用
messaging_client = credential_pool.create_messaging_client(app_id="cli_workflow_app_123")
contact_client = credential_pool.create_contact_client(app_id="cli_workflow_app_123")
doc_client = credential_pool.create_clouddoc_client(app_id="cli_workflow_app_123")


def create_team_report(department_id: str, report_title: str, report_content: str) -> dict:
    """创建团队报告并通知成员"""
    results = {}

    # 1. 获取部门成员
    members = contact_client.get_department_members(department_id=department_id)
    results["members_count"] = len(members)

    # 2. 创建文档
    doc = doc_client.create_document(title=report_title)
    results["doc_token"] = doc.token

    # 3. 向文档添加内容
    from lark_service.clouddoc.models import ContentBlock

    blocks = [ContentBlock(block_type="paragraph", text=report_content)]
    doc_client.append_blocks(doc_id=doc.token, blocks=blocks)

    # 4. 通知所有成员
    notification_results = []
    for member in members[:5]:  # 限制前5个成员作为示例
        msg_result = messaging_client.send_text_message(
            receiver_id=member.open_id, content=f"新报告已创建: {report_title}\n文档链接: https://feishu.cn/docs/{doc.token}"
        )
        notification_results.append(msg_result)

    results["notifications_sent"] = len(notification_results)
    return results


# 使用示例
result = create_team_report(
    department_id="od_dept_123",
    report_title="Q1 团队总结",
    report_content="本季度团队完成了以下目标...",
)

print(f"报告创建结果: {result}")
```

## 自定义重试策略

为不稳定的API调用配置自定义重试策略。

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.retry import RetryStrategy
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_retry_app_123",
    app_secret="retry_secret_min_16_chars_required",
    description="重试应用",
)

# 自定义重试策略
custom_retry = RetryStrategy(
    max_retries=5,  # 最多重试5次
    initial_delay=2.0,  # 初始延迟2秒
    max_delay=60.0,  # 最大延迟60秒
    exponential_base=2.0,  # 指数退避基数
)

# 创建客户端,使用自定义重试策略
client = MessagingClient(credential_pool, app_id="cli_retry_app_123", retry_strategy=custom_retry)

# 发送消息,如果失败会自动重试
try:
    result = client.send_text_message(receiver_id="ou_user1", content="重要消息")
    print(f"消息发送成功: {result}")
except Exception as e:
    print(f"重试{custom_retry.max_retries}次后仍失败: {e}")
```

## 批量操作优化

高效处理大量数据的批量操作。

### 批量发送消息

```python
from pathlib import Path
from typing import Any

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_batch_app_123",
    app_secret="batch_secret_min_16_chars_required",
    description="批量应用",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_batch_app_123")


def batch_send_notifications(users: list[dict[str, Any]], message: str) -> list[dict]:
    """批量发送通知消息"""
    results = []
    failed = []

    for user in users:
        try:
            result = client.send_text_message(receiver_id=user["open_id"], content=message)
            results.append({"user_id": user["open_id"], "success": True, "result": result})
        except Exception as e:
            failed.append({"user_id": user["open_id"], "error": str(e)})

    print(f"成功: {len(results)}, 失败: {len(failed)}")
    return results


# 使用示例
users_list = [
    {"open_id": "ou_user1", "name": "User1"},
    {"open_id": "ou_user2", "name": "User2"},
    {"open_id": "ou_user3", "name": "User3"},
]

batch_results = batch_send_notifications(users_list, "系统维护通知")
print(f"批量发送结果: {len(batch_results)} 条消息")
```

### 批量创建aPaaS记录

```python
from pathlib import Path

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_apaas_batch_123",
    app_secret="apaas_secret_min_16_chars_required",
    description="aPaaS批量应用",
)

# 创建客户端
apaas_client = credential_pool.create_workspace_table_client(app_id="cli_apaas_batch_123")

# 批量创建记录
records_data = [
    {"name": "Record 1", "value": 100},
    {"name": "Record 2", "value": 200},
    {"name": "Record 3", "value": 300},
]

result = apaas_client.batch_create_records(
    user_access_token="u-xxx", workspace_id="ws_123", table_id="table_001", records=records_data
)

print(f"批量创建结果: {result}")
```

## 错误处理最佳实践

### 分级错误处理

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    ConfigError,
    InvalidParameterError,
    NotFoundError,
    PermissionDeniedError,
)
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_error_handling_123",
    app_secret="error_secret_min_16_chars_required",
    description="错误处理应用",
)

# 创建客户端
client = credential_pool.create_messaging_client(app_id="cli_error_handling_123")


def safe_send_message(receiver_id: str, content: str) -> dict | None:
    """安全发送消息,带完整错误处理"""
    try:
        return client.send_text_message(receiver_id=receiver_id, content=content)

    except ConfigError as e:
        # 配置错误 - 通常是app_id未指定
        print(f"配置错误: {e}")
        print("请检查应用配置")
        return None

    except InvalidParameterError as e:
        # 参数错误
        print(f"参数错误: {e}")
        print(f"receiver_id={receiver_id}, content={content}")
        return None

    except PermissionDeniedError as e:
        # 权限不足
        print(f"权限错误: {e}")
        print("请检查应用权限配置")
        return None

    except NotFoundError as e:
        # 资源不存在
        print(f"资源不存在: {e}")
        print(f"用户 {receiver_id} 可能不存在")
        return None

    except APIError as e:
        # 通用API错误
        print(f"API错误: {e}")
        print(f"错误码: {e.code}, 消息: {e.message}")
        return None

    except Exception as e:
        # 未知错误
        print(f"未知错误: {e}")
        return None


# 使用示例
result = safe_send_message("ou_user1", "测试消息")
if result:
    print(f"发送成功: {result}")
else:
    print("发送失败,已记录错误")
```

## 日志配置

### 自定义日志级别

```python
import logging

from lark_service.utils.logger import get_logger

# 获取LarkService日志器
logger = get_logger()

# 设置日志级别为DEBUG以查看详细信息
logger.setLevel(logging.DEBUG)

# 添加自定义处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 现在所有LarkService操作都会输出详细日志
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_logging_app_123",
    app_secret="logging_secret_min_16_chars_required",
    description="日志应用",
)

client = credential_pool.create_messaging_client(app_id="cli_logging_app_123")
result = client.send_text_message(receiver_id="ou_user1", content="测试日志")

# 控制台会输出详细的调试信息
print(f"结果: {result}")
```

## 性能优化

### Token缓存

LarkService 自动缓存 access_token,避免频繁请求。

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")

# CredentialPool会自动管理Token缓存和刷新
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_cache_app_123",
    app_secret="cache_secret_min_16_chars_required",
    description="缓存应用",
)

# 首次获取Token会调用API
token1 = credential_pool.get_token("cli_cache_app_123")
print(f"首次获取Token: {token1[:20]}...")

# 后续获取会从缓存中读取,无需API调用
token2 = credential_pool.get_token("cli_cache_app_123")
print(f"缓存获取Token: {token2[:20]}...")

# Token过期后会自动刷新
assert token1 == token2  # 在有效期内,两次获取的Token相同
```

### 连接池复用

所有客户端共享同一个 `CredentialPool`,避免重复初始化。

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService

# 初始化 (全局单例)
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_pool_app_123",
    app_secret="pool_secret_min_16_chars_required",
    description="连接池应用",
)

# 创建多个客户端,共享同一个CredentialPool
messaging_client = credential_pool.create_messaging_client(app_id="cli_pool_app_123")
contact_client = credential_pool.create_contact_client(app_id="cli_pool_app_123")
doc_client = credential_pool.create_clouddoc_client(app_id="cli_pool_app_123")

# 所有客户端共享Token缓存和连接资源
# 这样可以显著提升性能并减少API调用次数
```

## 安全最佳实践

### 敏感信息保护

```python
import os
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService

# 从环境变量读取敏感信息
app_id = os.getenv("LARK_APP_ID")
app_secret = os.getenv("LARK_APP_SECRET")

if not app_id or not app_secret:
    raise ValueError("请设置环境变量 LARK_APP_ID 和 LARK_APP_SECRET")

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 使用环境变量中的凭证
app_manager.add_application(app_id=app_id, app_secret=app_secret, description="生产应用")

# 创建客户端
client = credential_pool.create_messaging_client(app_id=app_id)

# 使用示例
result = client.send_text_message(receiver_id="ou_user1", content="安全消息")
print(f"消息已发送: {result.get('data', {}).get('message_id')}")
```

### 数据库文件权限

确保数据库文件权限正确,防止未授权访问。

```bash
# 在Linux/Mac上设置文件权限
chmod 600 data/applications.db
chmod 600 data/tokens.db

# 确保数据目录只有所有者可访问
chmod 700 data/
```

### Token过期处理

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import APIError
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService
from lark_service.messaging.client import MessagingClient

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config, app_manager=app_manager, token_storage=token_storage, lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_token_app_123",
    app_secret="token_secret_min_16_chars_required",
    description="Token应用",
)

client = credential_pool.create_messaging_client(app_id="cli_token_app_123")


def send_with_token_refresh(receiver_id: str, content: str) -> dict:
    """发送消息,自动处理Token过期"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            return client.send_text_message(receiver_id=receiver_id, content=content)
        except APIError as e:
            if e.code == 99991663 and attempt < max_retries - 1:  # Token过期
                print("Token已过期,刷新后重试...")
                # CredentialPool会自动刷新Token
                continue
            raise


# 使用示例
result = send_with_token_refresh("ou_user1", "测试消息")
print(f"发送成功: {result}")
```

## 相关文档

- [应用管理](app-management.md)
- [消息服务](messaging.md)
- [通讯录服务](contact.md)
- [云文档服务](clouddoc.md)
- [aPaaS 服务](apaas.md)
