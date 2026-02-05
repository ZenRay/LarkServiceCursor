# 5分钟快速开始

本指南将帮助你在 5 分钟内完成 Lark Service 的基本配置并发送第一条消息。

## 前置条件

- 已安装 Python 3.12+
- 已配置飞书企业自建应用
- 已获取 `app_id` 和 `app_secret`

## 步骤 1: 安装

```bash
pip install -r requirements.txt
```

## 步骤 2: 配置环境变量

创建 `.env` 文件：

```bash
# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=your_password

# 加密密钥（使用 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 生成）
LARK_CONFIG_ENCRYPTION_KEY=your_32_byte_key
```

## 步骤 3: 初始化数据库

```bash
# 运行迁移
alembic upgrade head
```

## 步骤 4: 添加飞书应用

```bash
lark-service-cli app add \
    --app-id cli_a8d27f9bf635500e \
    --app-secret xxx \
    --app-name "我的测试应用"
```

## 步骤 5: 获取接收者 ID

发送消息前需要获取接收者的 ID。有以下几种方式：

### 方式 1: 群聊 ID（推荐用于测试）

1. 在飞书中打开目标群聊
2. 点击右上角「...」→「设置」
3. 在群设置中找到「群组 ID」（格式：`oc_xxx`）
4. 复制群组 ID 用于发送消息

### 方式 2: 用户 open_id

**注意**：每个应用的用户 open_id 是独立的，不能跨应用使用。

使用 CLI 工具查询：

```bash
# 通过手机号查询
lark-service-cli contact get-user-by-mobile \
    --app-id cli_a8d27f9bf635500e \
    --mobile "+8613800138000"

# 通过邮箱查询
lark-service-cli contact get-user-by-email \
    --app-id cli_a8d27f9bf635500e \
    --email "user@example.com"
```

或使用 Python 代码：

```python
from lark_service.contact.client import ContactClient

contact_client = ContactClient(credential_pool)
user = contact_client.get_user_by_mobile(
    app_id="cli_a8d27f9bf635500e",
    mobile="+8613800138000"
)
print(f"用户 open_id: {user['open_id']}")
```

## 步骤 6: 发送第一条消息

```python
from lark_service.core.config import Config
from lark_service.core.storage import ApplicationManager, TokenStorageService
from lark_service.core.credential_pool import CredentialPool
from lark_service.messaging.client import MessagingClient

# 1. 加载配置
config = Config.load_from_env()

# 2. 初始化核心组件
app_manager = ApplicationManager(
    db_path=config.config_db_path,
    encryption_key=config.config_encryption_key
)
token_storage = TokenStorageService(config.get_postgres_url())
credential_pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage
)

# 3. 创建消息客户端
messaging_client = MessagingClient(credential_pool)

# 4. 发送文本消息
# 注意：需要使用当前应用的接收者 ID
# 选项1：发送到群聊（推荐用于测试，群聊 ID 通用）
response = messaging_client.send_text_message(
    app_id="cli_a8d27f9bf635500e",
    receiver_id="oc_xxx",  # 群聊 ID，从飞书群聊设置中获取
    content="你好，这是来自 Lark Service 的第一条消息！",
    receive_id_type="chat_id"  # 指定接收者类型为群聊
)

# 选项2：发送到个人（open_id 是应用特定的）
# 需要先通过手机号或邮箱获取用户的 open_id
# from lark_service.contact.client import ContactClient
# contact_client = ContactClient(credential_pool)
# user = contact_client.get_user_by_mobile(
#     app_id="cli_a8d27f9bf635500e",
#     mobile="+8613800138000"
# )
# response = messaging_client.send_text_message(
#     app_id="cli_a8d27f9bf635500e",
#     receiver_id=user['open_id'],
#     content="你好！"
# )

print(f"✅ 消息发送成功！message_id: {response['message_id']}")
```

## 步骤 7: 发送交互式卡片

```python
from lark_service.cardkit.builder import CardBuilder

# 方式 1: 使用模板方法 (快速)
card = CardBuilder().build_notification_card(
    title="欢迎使用 Lark Service",
    content="这是一条交互式卡片消息，支持 **Markdown** 格式！",
    level="info",
    action_text="查看详情",
    action_url="https://example.com"
)

# 方式 2: 使用链式 API (灵活)
card = (CardBuilder()
    .add_header("欢迎使用 Lark Service", template="blue")
    .add_markdown("**功能特点**:")
    .add_text("• 简单易用的 API")
    .add_text("• 完善的错误处理")
    .add_text("• 详细的文档支持")
    .add_divider()
    .add_button("查看文档", url="https://example.com", button_type="primary")
    .build()
)

# 发送卡片（使用与步骤6相同的接收者）
response = messaging_client.send_card_message(
    app_id="cli_a8d27f9bf635500e",
    receiver_id="oc_xxx",  # 替换为实际的群聊 ID
    card=card,
    receive_id_type="chat_id"
)

print(f"✅ 卡片发送成功！message_id: {response['message_id']}")
```

## 🎉 完成！

恭喜！你已经成功发送了第一条消息和交互式卡片。

## 下一步

- 📖 [消息服务](usage/messaging.md) - 学习各种消息类型
- 🎴 [卡片服务](usage/card.md) - 创建复杂的交互式卡片
- 👥 [通讯录服务](usage/contact.md) - 查询用户和部门信息
- 📁 [云文档服务](usage/clouddoc.md) - 操作文档、表格和多维表格
- 🔐 [用户授权](usage/auth.md) - WebSocket 用户授权流程

## 常见问题

### Q: 如何获取用户的 open_id？

```python
from lark_service.contact.client import ContactClient

contact_client = ContactClient(pool=credential_pool)

# 通过邮箱查询
user = contact_client.get_user_by_email(
    app_id="cli_xxx",
    email="user@example.com"
)
print(f"open_id: {user.open_id}")
```

### Q: 如何处理 token 过期？

Lark Service 会自动管理 token 的刷新，无需手动处理。

### Q: 如何启用日志？

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)
```

更多问题请查看 [故障排查](troubleshooting.md) 文档。
