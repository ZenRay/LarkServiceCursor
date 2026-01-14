# Quick Start Guide: Lark Service 核心组件

**Feature**: 001-lark-service-core  
**Version**: 1.0.0  
**Last Updated**: 2026-01-14

## 概述

本指南将帮助您在 **5 分钟内**完成 Lark Service 核心组件的安装、配置并发送第一条飞书消息。

---

## 前置要求

### 环境要求

- **Python**: 3.12 或更高版本
- **Docker**: 20.10+ (用于本地开发环境)
- **Docker Compose**: 1.29+ (用于编排 PostgreSQL 和 RabbitMQ)

### 飞书应用配置

1. 登录[飞书开放平台](https://open.feishu.cn)
2. 创建企业自建应用
3. 获取 **App ID** 和 **App Secret**
4. 开启以下权限:
   - `im:message` - 发送消息
   - `im:message.group_msg` - 发送群消息
   - `contact:user.base:readonly` - 读取用户信息

---

## 步骤 1: 安装

### 方式 1: 使用 pip 安装 (推荐)

```bash
pip install lark-service
```

### 方式 2: 从源码安装

```bash
git clone https://github.com/your-org/lark-service.git
cd lark-service
pip install -e .
```

---

## 步骤 2: 启动依赖服务

使用 Docker Compose 启动 PostgreSQL 和 RabbitMQ:

```bash
# 在项目根目录
docker-compose up -d postgres rabbitmq
```

等待服务启动完成(约 10 秒):

```bash
# 检查服务状态
docker-compose ps
```

输出应该显示:
```
NAME                COMMAND                  SERVICE             STATUS
lark-postgres       "docker-entrypoint.s…"   postgres            Up
lark-rabbitmq       "docker-entrypoint.s…"   rabbitmq            Up
```

---

## 步骤 3: 配置环境变量

在项目根目录创建 `.env` 文件:

```bash
cp .env.example .env
```

编辑 `.env` 文件,填入数据库和加密配置:

```bash
# PostgreSQL 配置 (Token 存储和用户缓存)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=lark_password_123       # 修改为强密码

# RabbitMQ 配置 (消息队列)
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=rabbitmq_password_123   # 修改为强密码

# 应用配置加密密钥 (SQLite 应用配置加密)
LARK_CONFIG_ENCRYPTION_KEY=$(openssl rand -base64 32)

# Token 数据加密密钥 (PostgreSQL Token 加密,可选)
# LARK_TOKEN_ENCRYPTION_KEY=$(openssl rand -base64 32)

# 日志级别
LOG_LEVEL=INFO
```

> **注意**: 飞书应用凭证(App ID/Secret)不在 .env 中配置,而是通过应用配置管理接口动态添加到 SQLite 数据库中。

---

## 步骤 4: 初始化数据库

### 4.1 初始化 PostgreSQL (Token 存储)

运行数据库迁移创建表结构:

```bash
# 使用 alembic 运行 PostgreSQL 迁移
alembic upgrade head
```

预期输出:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema (tokens, user_cache, auth_sessions)
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, Add indexes
```

### 4.2 初始化应用配置 (SQLite)

添加您的飞书应用配置:

```bash
# 使用 CLI 添加应用配置
python -m lark_service.cli app add \
  --app-id "cli_a1b2c3d4e5f6g7h8" \
  --app-secret "your_app_secret_here" \
  --name "我的飞书应用" \
  --description "用于内部系统集成"
```

或者使用 Python API:

```python
from lark_service.core.storage.sqlite_storage import ApplicationManager

# 初始化应用管理器
app_manager = ApplicationManager()

# 添加应用配置
app_manager.create_application(
    app_id="cli_a1b2c3d4e5f6g7h8",
    app_secret="your_app_secret_here",
    name="我的飞书应用",
    description="用于内部系统集成"
)

print("应用配置已添加到 SQLite 数据库!")
```

预期输出:
```
✓ 应用配置已成功添加
  App ID: cli_a1b2c3d4e5f6g7h8
  Name: 我的飞书应用
  Status: active
  Created: 2026-01-15 10:30:00
```

> **安全提示**: App Secret 会使用 `LARK_CONFIG_ENCRYPTION_KEY` 自动加密存储在 SQLite 数据库中。

---

## 步骤 5: 发送第一条消息! 🎉

创建测试脚本 `test_send_message.py`:

```python
from lark_service import LarkServiceClient

# 初始化客户端(传入 app_id,组件会自动从 SQLite 加载配置)
client = LarkServiceClient(
    app_id="cli_a1b2c3d4e5f6g7h8",  # 使用您在步骤4.2中添加的 App ID
)

# 发送文本消息(组件会自动获取和管理 Token)
response = client.messaging.send_text(
    receiver_id="ou_xxxxxxxxxxxxxxxx",  # 替换为接收者的 user_id
    content="Hello from Lark Service! 🚀"
)

print(f"消息发送成功!")
print(f"Request ID: {response.request_id}")
print(f"Message ID: {response.data['message_id']}")
```

> **工作原理**: 
> 1. 组件从 SQLite 加载应用配置(App ID/Secret)
> 2. 自动获取 `app_access_token` 并存储到 PostgreSQL
> 3. 使用 Token 调用飞书 API 发送消息
> 4. 整个过程对调用方完全透明!

运行脚本:

```bash
python test_send_message.py
```

如果一切正常,您应该看到输出:

```
消息发送成功!
Request ID: req_a1b2c3d4e5f6g7h8
Message ID: om_xxxxxxxxxxxxxxxx
```

并且接收者会在飞书中收到消息! ✅

---

## 步骤 6: 验证 Token 自动刷新

让我们验证组件的自动 Token 管理功能:

```python
from lark_service import LarkServiceClient
import time

client = LarkServiceClient(app_id="cli_a1b2c3d4e5f6g7h8")

# 发送第一条消息(首次获取 Token)
print("发送第一条消息...")
client.messaging.send_text(
    receiver_id="ou_xxxxxxxxxxxxxxxx",
    content="测试消息 1"
)
print("✓ Token 自动获取成功")

# 等待 1 秒后再次发送(使用缓存的 Token)
time.sleep(1)
print("发送第二条消息...")
client.messaging.send_text(
    receiver_id="ou_xxxxxxxxxxxxxxxx",
    content="测试消息 2"
)
print("✓ Token 缓存命中,无需重新获取")

# 查看 Token 缓存信息
token_info = client.credential_pool.get_token_info("cli_a1b2c3d4e5f6g7h8", "tenant_access_token")
print(f"Token 过期时间: {token_info['expires_at']}")
print(f"Token 来源: {token_info['source']}")  # 'cache' 或 'database' 或 'fresh'
```

---

## 常见功能示例

### 发送图片消息

```python
# 方式 1: 先上传,再发送
image_key = client.messaging.upload_image("path/to/image.png")
client.messaging.send_image(
    receiver_id="ou_xxxxxxxxxxxxxxxx",
    image_key=image_key
)

# 方式 2: 一步到位(推荐)
client.messaging.send_image_message(
    receiver_id="ou_xxxxxxxxxxxxxxxx",
    image_path="path/to/image.png"
)
```

### 发送文件消息

```python
client.messaging.send_file_message(
    receiver_id="ou_xxxxxxxxxxxxxxxx",
    file_path="path/to/report.pdf"
)
```

### 发送交互式卡片

```python
card_content = {
    "header": {
        "title": {
            "tag": "plain_text",
            "content": "审批通知"
        }
    },
    "elements": [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**申请人**: 张三\n**申请事项**: 请假申请"
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "同意"},
                    "type": "primary",
                    "value": "approve"
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "拒绝"},
                    "type": "danger",
                    "value": "reject"
                }
            ]
        }
    ]
}

# 发送卡片并注册回调处理函数
client.messaging.send_interactive_card(
    receiver_id="ou_xxxxxxxxxxxxxxxx",
    card_content=card_content,
    callback_handler=handle_approval_callback  # 自定义回调函数
)

def handle_approval_callback(event):
    """处理用户点击卡片按钮的回调"""
    user_id = event['user_id']
    action = event['action']['value']  # 'approve' or 'reject'
    
    if action == 'approve':
        print(f"用户 {user_id} 同意了审批")
        # 更新业务系统状态
    else:
        print(f"用户 {user_id} 拒绝了审批")
```

### 批量发送消息

```python
receiver_ids = [
    "ou_user1",
    "ou_user2",
    "ou_user3"
]

response = client.messaging.batch_send(
    receiver_ids=receiver_ids,
    msg_type="text",
    content="群发通知: 系统将于今晚 22:00 维护"
)

print(f"总数: {response.data['total']}")
print(f"成功: {response.data['success']}")
print(f"失败: {response.data['failed']}")

# 查看每个接收者的发送结果
for result in response.data['results']:
    print(f"{result['receiver_id']}: {result['status']}")
```

---

## 多应用场景

如果您的组织使用多个飞书自建应用,需要分别添加到 SQLite 数据库:

```bash
# 添加应用 1
python -m lark_service.cli app add \
  --app-id "cli_app1_xxxxxxxx" \
  --app-secret "secret1_xxxxxxxx" \
  --name "应用1-内部系统" \
  --description "用于内部工单系统"

# 添加应用 2
python -m lark_service.cli app add \
  --app-id "cli_app2_xxxxxxxx" \
  --app-secret "secret2_xxxxxxxx" \
  --name "应用2-外部集成" \
  --description "用于外部合作伙伴集成"
```

代码中指定 app_id:

```python
# 使用应用 1 发送消息
client1 = LarkServiceClient(app_id="cli_app1_xxxxxxxx")
client1.messaging.send_text(receiver_id="ou_xxx", content="来自应用1的消息")

# 使用应用 2 发送消息
client2 = LarkServiceClient(app_id="cli_app2_xxxxxxxx")
client2.messaging.send_text(receiver_id="ou_xxx", content="来自应用2的消息")
```

组件会自动按 app_id 隔离 Token 和配置,避免混用。

---

## 故障排查

### 问题 1: Token 获取失败

**错误信息**:
```
TokenAcquisitionError: Failed to get token: 10014 - app_id or app_secret invalid
```

**解决方法**:
1. 检查 SQLite 数据库中的应用配置是否正确:
   ```bash
   python -m lark_service.cli app list
   python -m lark_service.cli app show --app-id "cli_xxx"
   ```
2. 确认飞书应用状态为"已启用"(登录飞书开放平台查看)
3. 检查应用权限配置是否包含所需权限
4. 如果配置错误,可以更新:
   ```bash
   python -m lark_service.cli app update \
     --app-id "cli_xxx" \
     --app-secret "new_secret"
   ```

### 问题 2: 数据库连接失败

**错误信息**:
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方法**:
1. 确认 PostgreSQL 服务已启动: `docker-compose ps postgres`
2. 检查 `.env` 中的数据库配置是否正确
3. 重启服务: `docker-compose restart postgres`

### 问题 3: 消息发送失败

**错误信息**:
```
RateLimitedError: API rate limited (code: 99991664)
```

**解决方法**:
- 飞书 API 被限流,组件会自动重试(延迟 30 秒)
- 如果频繁触发限流,考虑降低调用频率或申请提升配额

### 问题 4: 查看日志

```bash
# 查看应用日志
tail -f logs/lark_service.log

# 查看 PostgreSQL 日志
docker-compose logs -f postgres

# 查看 RabbitMQ 日志
docker-compose logs -f rabbitmq
```

---

## 下一步

恭喜您完成快速开始! 接下来您可以:

1. **阅读完整 API 文档**: 查看 `docs/api_reference.md` 了解所有可用接口
2. **部署到生产环境**: 查看 `docs/deployment.md` 了解生产部署最佳实践
3. **集成更多模块**:
   - **CloudDoc**: 操作飞书文档、Sheet、多维表格
   - **Contact**: 查询用户和组织架构
   - **aPaaS**: 调用 AI 能力和自动化工作流

---

## 获取帮助

- **问题反馈**: [GitHub Issues](https://github.com/your-org/lark-service/issues)
- **技术支持**: tech-support@your-company.com
- **飞书开放平台文档**: https://open.feishu.cn/document/home/index

---

**Happy Coding! 🚀**
