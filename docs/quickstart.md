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

## 步骤 5: 发送第一条消息

```python
from lark_service.core import Config
from lark_service.core.storage import TokenStorageService
from lark_service.core import CredentialPool, ApplicationManager
from lark_service.messaging import MessagingClient

# 1. 加载配置
config = Config.load_from_env()

# 2. 初始化核心组件
app_manager = ApplicationManager()
token_storage = TokenStorageService(config.postgres_url)
credential_pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage
)

# 3. 创建消息客户端
messaging_client = MessagingClient(credential_pool=credential_pool)

# 4. 发送文本消息
response = messaging_client.send_text_message(
    app_id="cli_a8d27f9bf635500e",
    receiver_id="ou_xxx",  # 用户 open_id
    content="你好，这是来自 Lark Service 的第一条消息！"
)

print(f"✅ 消息发送成功！message_id: {response['message_id']}")
```

## 步骤 6: 发送交互式卡片

```python
from lark_service.cardkit import CardBuilder

# 创建卡片
card = CardBuilder() \
    .add_header("欢迎使用 Lark Service", color="blue") \
    .add_text("这是一条交互式卡片消息") \
    .add_button("点击我", value={"action": "click"}) \
    .build()

# 发送卡片
response = messaging_client.send_card_message(
    app_id="cli_a8d27f9bf635500e",
    receiver_id="ou_xxx",
    card=card
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
from lark_service.contact import ContactClient

contact_client = ContactClient(credential_pool=credential_pool)

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
