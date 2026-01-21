# Quick Start Guide: 应用管理与切换

**Feature**: 003-code-refactor-optimization
**Date**: 2026-01-21
**Phase**: Phase 1 - Design

## 概述

本指南演示如何使用重构后的 API 进行应用管理和切换。重构后的核心改进:
- ✅ **简化单应用场景**: app_id 参数变为可选,减少 90% 的重复传参
- ✅ **优雅多应用支持**: 提供 4 种灵活的应用切换方式
- ✅ **向后兼容**: 现有代码无需修改即可运行

---

## 目录

1. [快速开始 - 单应用场景 (3 分钟)](#快速开始---单应用场景-3-分钟)
2. [多应用场景 - 工厂方法](#多应用场景---工厂方法推荐)
3. [多应用场景 - 上下文管理器](#多应用场景---上下文管理器)
4. [应用确认和调试](#应用确认和调试)
5. [错误处理最佳实践](#错误处理最佳实践)
6. [并发场景最佳实践](#并发场景最佳实践-重要)
7. [完整示例](#完整示例)

---

## 快速开始 - 单应用场景 (3 分钟)

### 场景: 只使用一个飞书应用 (90% 的使用场景)

#### 方式 1: 客户端级默认 app_id (推荐 ⭐)

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient

# 1. 初始化 CredentialPool
pool = CredentialPool(...)

# 2. 创建客户端,指定默认 app_id
client = MessagingClient(pool, app_id="cli_xxx")

# 3. 调用 API,无需再传 app_id ✨
client.send_text_message(
    receiver_id="ou_yyy",
    text="Hello, this is a test message!"
)

client.send_image_message(
    receiver_id="ou_yyy",
    image_path="/path/to/image.png"
)

# 所有方法自动使用 cli_xxx
```

**优点**:
- ✅ 最简洁,减少 90% 的 app_id 传参
- ✅ 适合单应用场景
- ✅ 代码清晰,易于维护

---

#### 方式 2: CredentialPool 级默认 app_id

```python
# 1. 初始化 CredentialPool
pool = CredentialPool(...)

# 2. 设置 Pool 级别的默认 app_id
pool.set_default_app_id("cli_xxx")

# 3. 创建客户端 (不指定 app_id)
messaging_client = MessagingClient(pool)
contact_client = ContactClient(pool)
clouddoc_client = DocClient(pool)

# 4. 所有客户端自动继承默认 app_id
messaging_client.send_text_message(receiver_id="ou_yyy", text="Hello")
contact_client.get_user_info(user_id="ou_yyy")
clouddoc_client.create_doc(title="New Doc")

# 所有客户端使用 cli_xxx
```

**优点**:
- ✅ 一次设置,多个客户端共享
- ✅ 适合需要多种客户端的场景
- ✅ 统一管理默认应用

---

#### 方式 3: 自动检测 (只有一个应用时)

```python
# 假设数据库中只配置了一个应用: cli_xxx

# 1. 初始化 CredentialPool (不设置默认)
pool = CredentialPool(...)

# 2. 创建客户端 (不指定 app_id)
client = MessagingClient(pool)

# 3. 系统自动使用唯一的应用
client.send_text_message(receiver_id="ou_yyy", text="Hello")
# 自动使用 cli_xxx

# 日志: DEBUG "Single active app found: cli_xxx"
```

**优点**:
- ✅ 零配置,自动检测
- ✅ 适合单应用开发环境
- ✅ 开箱即用

---

## 多应用场景 - 工厂方法(推荐)

### 场景: 需要管理多个飞书应用 (10% 的使用场景)

**推荐原因**: 完全隔离,不会混淆,线程安全

```python
from lark_service.core.credential_pool import CredentialPool

# 1. 初始化 CredentialPool
pool = CredentialPool(...)

# 2. 使用工厂方法创建独立客户端
app1_messaging = pool.create_messaging_client("app1")
app1_contact = pool.create_contact_client("app1")

app2_messaging = pool.create_messaging_client("app2")
app2_contact = pool.create_contact_client("app2")

# 3. 每个客户端绑定到特定应用,不会混淆
app1_messaging.send_text_message(
    receiver_id="ou_xxx",
    text="This message is from App1"
)

app2_messaging.send_text_message(
    receiver_id="ou_yyy",
    text="This message is from App2"
)

app1_contact.get_user_info(user_id="ou_xxx")  # 使用 app1
app2_contact.get_user_info(user_id="ou_yyy")  # 使用 app2
```

**优点**:
- ✅ 完全隔离,每个客户端绑定一个应用
- ✅ 不会混淆,不会误用
- ✅ 线程安全,可并发使用
- ✅ 适合长期运行的多应用服务

**使用建议**:
- 在服务启动时创建所有需要的客户端
- 将客户端作为服务的成员变量
- 避免频繁创建/销毁客户端

---

## 多应用场景 - 上下文管理器

### 场景: 偶尔需要切换应用

**推荐原因**: 明确的作用域,自动恢复

```python
# 1. 创建默认客户端 (app1)
client = MessagingClient(pool, app_id="app1")

# 2. 正常使用 app1
client.send_text_message(receiver_id="ou_xxx", text="From App1")

# 3. 临时切换到 app2
with client.use_app("app2"):
    # 在这个上下文中使用 app2
    client.send_text_message(receiver_id="ou_yyy", text="From App2")
    client.send_image_message(receiver_id="ou_yyy", image_path="img.png")
    # ... 其他操作

# 4. 退出上下文后,自动恢复到 app1
client.send_text_message(receiver_id="ou_xxx", text="Back to App1")
```

**嵌套上下文**:
```python
client = MessagingClient(pool, app_id="app1")

print(client.get_current_app_id())  # app1

with client.use_app("app2"):
    print(client.get_current_app_id())  # app2

    with client.use_app("app3"):
        print(client.get_current_app_id())  # app3
        client.send_text_message(...)  # 使用 app3

    # 退出内层,恢复到 app2
    print(client.get_current_app_id())  # app2
    client.send_text_message(...)  # 使用 app2

# 退出所有上下文,恢复到 app1
print(client.get_current_app_id())  # app1
```

**优点**:
- ✅ 明确的作用域
- ✅ 自动恢复,不会忘记
- ✅ 支持嵌套
- ✅ 适合偶尔切换应用的场景

**⚠️ 重要警告**:
- **不支持多线程并发使用同一客户端实例**
- 多线程场景请使用工厂方法或显式参数
- 详见 [并发场景最佳实践](#并发场景最佳实践-重要)

---

## 应用确认和调试

### 确认当前使用的应用

```python
client = MessagingClient(pool, app_id="app1")

# 方法 1: get_current_app_id()
current = client.get_current_app_id()
print(f"当前应用: {current}")  # 输出: app1

# 方法 2: 在上下文中确认
with client.use_app("app2"):
    current = client.get_current_app_id()
    print(f"临时切换到: {current}")  # 输出: app2

print(f"恢复为: {client.get_current_app_id()}")  # 输出: app1
```

### 查看所有可用应用

```python
# 列出所有已配置的活跃应用
available = client.list_available_apps()
print(f"可用应用: {available}")
# 输出: ['app1', 'app2', 'app3']

# 条件切换
if "app3" in client.list_available_apps():
    with client.use_app("app3"):
        client.send_text_message(...)
else:
    print("App3 未配置或未激活")
```

### 日志调试

所有 API 调用都会记录使用的 app_id:

```python
client.send_text_message(receiver_id="ou_xxx", text="Test")
# 日志: INFO Sending message using app_id=app1, receiver=ou_xxx
```

---

## 错误处理最佳实践

### 错误 1: 无法确定 app_id

```python
# 场景: 没有设置任何默认值
client = MessagingClient(pool)  # 没有指定 app_id
pool.set_default_app_id(...)    # 也没有设置 Pool 默认值

try:
    client.send_text_message(receiver_id="ou_xxx", text="Hello")
except ConfigError as e:
    print(e)
    # 输出:
    # Cannot determine app_id. Please specify app_id via:
    # 1. Method parameter: client.send_message(app_id='cli_xxx', ...)
    # 2. Client initialization: MessagingClient(pool, app_id='cli_xxx')
    # 3. CredentialPool default: pool.set_default_app_id('cli_xxx')
    # Available apps: ['app1', 'app2', 'app3']
```

**解决方法**:
```python
# 方法 1: 设置客户端默认值
client = MessagingClient(pool, app_id="app1")

# 方法 2: 设置 Pool 默认值
pool.set_default_app_id("app1")

# 方法 3: 显式传参 (向后兼容)
client.send_text_message(app_id="app1", receiver_id="ou_xxx", text="Hello")
```

### 错误 2: app_id 不存在

```python
try:
    client.send_text_message(
        app_id="non_existent_app",
        receiver_id="ou_xxx",
        text="Hello"
    )
except AuthenticationError as e:
    print(e)
    # 输出:
    # Application not found: non_existent_app
    # Available apps: ['app1', 'app2', 'app3']
```

**解决方法**:
```python
# 检查应用是否存在
available = client.list_available_apps()
if "app3" in available:
    client.send_text_message(app_id="app3", ...)
else:
    print(f"App3 不存在,可用应用: {available}")
```

### 错误 3: 上下文管理器中的 app_id 不存在

```python
try:
    with client.use_app("non_existent_app"):
        client.send_text_message(...)
except AuthenticationError as e:
    print(e)
    # 输出:
    # Application not found: non_existent_app
    # Available apps: ['app1', 'app2', 'app3']
```

---

## 并发场景最佳实践 (重要)

### ⚠️ 重要警告

**`use_app()` 上下文管理器不支持多线程并发使用同一客户端实例。**

### ❌ 错误用法: 多线程共享客户端并切换应用

```python
from concurrent.futures import ThreadPoolExecutor

# ❌ 错误: 多线程共享客户端实例并使用 use_app()
client = MessagingClient(credential_pool)

def send_in_thread(app_id, message):
    with client.use_app(app_id):  # ⚠️ 线程不安全!
        client.send_text_message(receiver_id="ou_xxx", text=message)

with ThreadPoolExecutor() as executor:
    executor.submit(send_in_thread, "app1", "msg1")
    executor.submit(send_in_thread, "app2", "msg2")
    # 可能导致应用混淆,消息发送到错误的应用
```

### ✅ 正确用法 1: 为每个应用创建独立客户端 (推荐)

```python
from concurrent.futures import ThreadPoolExecutor

def send_with_dedicated_client(app_id, message):
    # 每个线程创建自己的客户端实例
    client = credential_pool.create_messaging_client(app_id)
    client.send_text_message(receiver_id="ou_xxx", text=message)

with ThreadPoolExecutor() as executor:
    executor.submit(send_with_dedicated_client, "app1", "msg1")
    executor.submit(send_with_dedicated_client, "app2", "msg2")
    # 完全隔离,线程安全 ✅
```

### ✅ 正确用法 2: 在方法级别显式传递 app_id

```python
from concurrent.futures import ThreadPoolExecutor

# 创建共享客户端
client = MessagingClient(credential_pool)

def send_explicit(app_id, message):
    # 显式传递 app_id,不使用上下文管理器
    client.send_text_message(
        app_id=app_id,  # 显式传递,线程安全 ✅
        receiver_id="ou_xxx",
        text=message
    )

with ThreadPoolExecutor() as executor:
    executor.submit(send_explicit, "app1", "msg1")
    executor.submit(send_explicit, "app2", "msg2")
```

### 设计理由

- **单应用场景** (90%): 无需考虑并发切换
- **多应用并发场景**: 推荐使用工厂方法或显式参数
- **避免复杂性**: 不引入线程本地存储 (threading.local)
- **性能考虑**: 避免额外的性能开销

---

## 完整示例

### 示例 1: 单应用消息服务

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient

# 初始化
pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage,
    lock_dir="/tmp/locks"
)

# 方式 1: 客户端默认 app_id
client = MessagingClient(pool, app_id="cli_production")

# 发送消息
client.send_text_message(
    receiver_id="ou_user123",
    text="Hello from production app!"
)

# 发送图片
client.send_image_message(
    receiver_id="ou_user123",
    image_path="/path/to/image.png"
)

# 发送卡片
client.send_card_message(
    receiver_id="ou_user123",
    card_content={"type": "template", "data": {...}}
)

# 所有操作自动使用 cli_production
```

### 示例 2: 多应用管理服务

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient
from lark_service.contact.client import ContactClient

# 初始化
pool = CredentialPool(...)

# 创建专用客户端
prod_messaging = pool.create_messaging_client("cli_production")
prod_contact = pool.create_contact_client("cli_production")

dev_messaging = pool.create_messaging_client("cli_development")
dev_contact = pool.create_contact_client("cli_development")

# 生产环境操作
prod_messaging.send_text_message(
    receiver_id="ou_prod_user",
    text="Production message"
)
prod_user = prod_contact.get_user_info(user_id="ou_prod_user")

# 开发环境操作
dev_messaging.send_text_message(
    receiver_id="ou_dev_user",
    text="Development message"
)
dev_user = dev_contact.get_user_info(user_id="ou_dev_user")

# 完全隔离,不会混淆
```

### 示例 3: 动态应用选择

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient

pool = CredentialPool(...)

def send_notification(user_id: str, message: str, app_env: str):
    """
    根据环境动态选择应用发送通知

    Args:
        user_id: 用户 ID
        message: 消息内容
        app_env: 应用环境 ('prod', 'staging', 'dev')
    """
    # 映射环境到 app_id
    app_mapping = {
        'prod': 'cli_production',
        'staging': 'cli_staging',
        'dev': 'cli_development'
    }

    app_id = app_mapping.get(app_env)
    if not app_id:
        raise ValueError(f"Unknown environment: {app_env}")

    # 创建专用客户端
    client = pool.create_messaging_client(app_id)

    # 发送消息
    client.send_text_message(receiver_id=user_id, text=message)

    print(f"Sent notification using {app_id}")

# 使用
send_notification("ou_user123", "Hello from prod", "prod")
send_notification("ou_user456", "Hello from dev", "dev")
```

### 示例 4: 带错误处理的完整流程

```python
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import ConfigError, AuthenticationError
from lark_service.messaging.client import MessagingClient

def send_message_safe(
    pool: CredentialPool,
    app_id: str,
    receiver_id: str,
    text: str
) -> bool:
    """
    安全地发送消息,包含完整的错误处理

    Returns:
        True if success, False otherwise
    """
    try:
        # 检查应用是否存在
        client = MessagingClient(pool)
        if app_id not in client.list_available_apps():
            print(f"Error: App {app_id} not found")
            print(f"Available apps: {client.list_available_apps()}")
            return False

        # 创建客户端并发送
        client = pool.create_messaging_client(app_id)
        client.send_text_message(receiver_id=receiver_id, text=text)

        print(f"✅ Message sent successfully using {app_id}")
        return True

    except ConfigError as e:
        print(f"❌ Configuration error: {e}")
        return False

    except AuthenticationError as e:
        print(f"❌ Authentication error: {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

# 使用
pool = CredentialPool(...)
success = send_message_safe(
    pool=pool,
    app_id="cli_production",
    receiver_id="ou_user123",
    text="Hello!"
)
```

---

## app_id 解析优先级总结

重构后,app_id 按以下优先级解析:

```
1. 方法参数 (最高优先级)
   ↓ (如果未提供)
2. 上下文管理器 (use_app)
   ↓ (如果未使用)
3. 客户端默认值 (MessagingClient 初始化时指定)
   ↓ (如果未指定)
4. CredentialPool 默认值 (pool.set_default_app_id)
   ↓ (如果未设置)
5. 自动检测 (数据库中唯一的活跃应用)
   ↓ (如果无法确定)
6. 抛出 ConfigError (包含详细的修复建议)
```

**示例**:
```python
# 假设: pool 默认 = "pool_app"
pool.set_default_app_id("pool_app")

# 场景 1: 所有优先级都指定
client = MessagingClient(pool, app_id="client_app")
with client.use_app("context_app"):
    client.send_text_message(app_id="param_app", ...)
# 使用: param_app (方法参数,最高优先级)

# 场景 2: 无方法参数
with client.use_app("context_app"):
    client.send_text_message(...)
# 使用: context_app (上下文管理器)

# 场景 3: 无方法参数和上下文
client.send_text_message(...)
# 使用: client_app (客户端默认值)

# 场景 4: 仅有 Pool 默认值
client2 = MessagingClient(pool)  # 无客户端默认值
client2.send_text_message(...)
# 使用: pool_app (Pool 默认值)
```

---

## 向后兼容说明

**重要**: 所有现有 API 保持不变,现有代码无需修改即可运行。

**之前的代码 (仍然支持)**:
```python
client = MessagingClient(credential_pool)
client.send_text_message(
    app_id="cli_xxx",  # ← 显式传递,仍然有效
    receiver_id="ou_yyy",
    text="Hello"
)
```

**新的推荐写法**:
```python
client = MessagingClient(credential_pool, app_id="cli_xxx")
client.send_text_message(
    receiver_id="ou_yyy",
    text="Hello"  # ← 无需 app_id,更简洁
)
```

**迁移路径**:
- 可选择性迁移,不强制
- 新代码推荐使用新 API
- 现有代码无需修改

---

## 下一步

- **实施指南**: 参考 [plan.md](./plan.md) 了解详细的实施计划
- **API 契约**: 参考 [contracts/](./contracts/) 目录了解详细的 API 规范
- **数据模型**: 参考 [data-model.md](./data-model.md) 了解实体关系
- **任务清单**: 运行 `/speckit.tasks` 生成详细的任务清单

---

**Quick Start Status**: ✅ Complete
**Last Updated**: 2026-01-21
