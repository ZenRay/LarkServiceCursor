# WebSocket 用户授权

本指南介绍如何使用 Lark Service 实现 WebSocket 用户授权流程。

## 概述

WebSocket 用户授权允许你的应用通过交互式卡片获取用户的访问令牌（`user_access_token`），从而以用户身份调用飞书 API。

### 核心特性

✅ **交互式授权** - 通过飞书卡片进行用户授权
✅ **自动 Token 管理** - 自动刷新和持久化 token
✅ **会话跟踪** - 完整的授权会话生命周期管理
✅ **WebSocket 实时** - 通过 WebSocket 接收授权事件
✅ **HTTP 回调支持** - 支持 OAuth 重定向回调

### 授权流程

```
1. 应用发送授权卡片 → 用户
2. 用户点击"授权"按钮 → 跳转飞书授权页
3. 用户完成授权 → 飞书重定向到回调服务器
4. 回调服务器接收 code → 交换 user_access_token
5. Token 存储到数据库 → 授权完成
6. 卡片更新为"授权成功"状态
```

## 前置条件

### 1. 数据库配置

确保已运行数据库迁移：

```bash
alembic upgrade head
```

### 2. 飞书应用配置

在飞书开发者后台配置：

- **OAuth 重定向 URL**: `http://your-domain.com/callback`
- **事件订阅**: 启用 WebSocket 模式（可选）
- **卡片回调**: 配置回调 URL（可选）

### 3. 环境变量

```bash
# OAuth 配置
OAUTH_REDIRECT_URI=http://localhost:8000/callback  # 开发环境
FEISHU_API_BASE_URL=https://open.feishu.cn

# 回调服务器
CALLBACK_SERVER_ENABLED=true
CALLBACK_SERVER_HOST=0.0.0.0
CALLBACK_SERVER_PORT=8000
```

## 基本用法

### 初始化组件

```python
from lark_service.core import Config
from lark_service.core.storage import TokenStorageService
from lark_service.core import CredentialPool, ApplicationManager
from lark_service.auth import AuthSessionManager, CardAuthHandler
from lark_service.messaging import MessagingClient
from lark_service.server import CallbackServerManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

# 3. 创建数据库会话
engine = create_engine(config.postgres_url)
SessionLocal = sessionmaker(bind=engine)
db_session = SessionLocal()

# 4. 初始化授权组件
auth_session_manager = AuthSessionManager(
    db=db_session,
    feishu_api_base_url=config.feishu_api_base_url
)

messaging_client = MessagingClient(credential_pool=credential_pool)

card_auth_handler = CardAuthHandler(
    session_manager=auth_session_manager,
    messaging_client=messaging_client,
    app_id=config.app_id,
    app_secret=config.app_secret,
    oauth_redirect_uri=config.oauth_redirect_uri,
    feishu_api_base_url=config.feishu_api_base_url
)

# 5. 启动回调服务器（用于接收 OAuth 重定向）
callback_server = CallbackServerManager(
    host=config.callback_server_host,
    port=config.callback_server_port
)
callback_server.register_card_auth_handler(card_auth_handler)
callback_server.start()  # 在后台运行
```

### 发送授权卡片

```python
# 发送授权请求卡片给用户
response = card_auth_handler.send_auth_card(
    open_id="ou_xxx",  # 用户的 open_id
    app_id="cli_xxx",
)

print(f"✅ 授权卡片已发送！session_id: {response['session_id']}")
```

### 检查授权状态

```python
# 查询会话状态
session_id = response['session_id']
session = auth_session_manager.get_session(session_id)

if session.state == "completed":
    print(f"✅ 用户已授权！user_access_token: {session.user_access_token[:10]}...")
elif session.state == "rejected":
    print("❌ 用户拒绝了授权")
elif session.state == "pending":
    print("⏳ 等待用户授权...")
```

### 使用 user_access_token

```python
# 获取已授权用户的 token
user_token = auth_session_manager.get_user_access_token(
    open_id="ou_xxx",
    app_id="cli_xxx"
)

print(f"user_access_token: {user_token}")

# 使用 user_access_token 调用 API
# 示例：以用户身份发送消息
# （需要在 SDK 调用中传递 user_access_token）
```

## 高级用法

### 自定义授权卡片

```python
from lark_service.auth import AuthCardOptions

# 自定义卡片选项
options = AuthCardOptions(
    # 自定义授权理由
    # （注意：AuthCardOptions 当前使用固定模板）
)

response = card_auth_handler.send_auth_card(
    open_id="ou_xxx",
    app_id="cli_xxx",
    # options=options  # 暂不支持，使用默认模板
)
```

### Token 自动刷新

```python
# Token 会在过期前自动刷新（配置的阈值，默认 10%）
# 无需手动处理

# 强制刷新 token
refreshed_session = auth_session_manager.refresh_user_access_token(
    session_id=session_id
)
print(f"✅ Token 已刷新！新的过期时间: {refreshed_session.token_expires_at}")
```

### 会话管理

```python
# 获取用户的所有会话
sessions = auth_session_manager.get_sessions_by_open_id(
    open_id="ou_xxx",
    app_id="cli_xxx"
)

for session in sessions:
    print(f"Session {session.session_id}: {session.state}")

# 使会话失效
auth_session_manager.invalidate_session(session_id=session_id)
```

### 清理过期会话

```python
# 清理过期的会话（建议定时任务）
deleted_count = auth_session_manager.cleanup_expired_sessions(
    expiry_days=30  # 删除 30 天前过期的会话
)
print(f"✅ 已清理 {deleted_count} 个过期会话")
```

## WebSocket 事件处理（可选）

如果你的应用使用 WebSocket 接收事件：

```python
from lark_service.events import LarkWebSocketClient

# 创建 WebSocket 客户端
ws_client = LarkWebSocketClient(
    app_id=config.app_id,
    app_secret=config.app_secret,
    credential_pool=credential_pool
)

# 注册卡片交互事件处理器
def handle_card_event(event):
    """处理卡片交互事件（授权按钮点击）"""
    # 注意：卡片授权流程主要通过 HTTP 回调处理
    # WebSocket 事件订阅不包含 card.action.trigger
    pass

ws_client.register_handler("card.action.trigger", handle_card_event)

# 启动 WebSocket 客户端
ws_client.start()
```

> **注意**: 卡片授权流程主要依赖 HTTP OAuth 回调，WebSocket 用于其他事件订阅。

## 生产部署注意事项

### 1. 公网访问要求

**重要**: 飞书 OAuth 回调需要公网可访问的 URL。

#### 开发环境方案

使用内网穿透工具：

```bash
# 方案 1: Ngrok
ngrok http 8000

# 方案 2: Localtunnel
lt --port 8000

# 方案 3: Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8000
```

#### 生产环境方案

- **云服务器部署**: 使用公网 IP 或域名
- **Nginx 反向代理**: 配置 SSL 证书
- **负载均衡**: 多实例部署

### 2. 回调服务器配置

```python
# 生产环境配置
callback_server = CallbackServerManager(
    host="0.0.0.0",  # 监听所有网络接口
    port=8000,
)

# 配置为后台服务
callback_server.start()  # 非阻塞启动

# 或者在主线程中运行（阻塞）
# callback_server.run()  # 阻塞运行
```

### 3. 配置 OAuth Redirect URI

在飞书开发者后台配置：

```
# 生产环境
https://your-domain.com/callback

# 开发环境（使用 ngrok）
https://abc123.ngrok.io/callback
```

### 4. 环境变量

```bash
# 生产环境 .env
OAUTH_REDIRECT_URI=https://your-domain.com/callback
FEISHU_API_BASE_URL=https://open.feishu.cn
CALLBACK_SERVER_ENABLED=true
CALLBACK_SERVER_HOST=0.0.0.0
CALLBACK_SERVER_PORT=8000
```

## 错误处理

### 常见错误

#### 1. 授权码过期

```python
from lark_service.auth.exceptions import AuthorizationCodeExpiredError

try:
    session = auth_session_manager.complete_authorization(
        session_id=session_id,
        authorization_code=code
    )
except AuthorizationCodeExpiredError:
    print("❌ 授权码已过期，请重新授权")
```

#### 2. Token 刷新失败

```python
from lark_service.auth.exceptions import TokenRefreshFailedError

try:
    session = auth_session_manager.refresh_user_access_token(session_id)
except TokenRefreshFailedError as e:
    print(f"❌ Token 刷新失败: {e}")
```

#### 3. 会话不存在

```python
from lark_service.auth.exceptions import AuthSessionNotFoundError

try:
    session = auth_session_manager.get_session(session_id)
except AuthSessionNotFoundError:
    print("❌ 会话不存在或已过期")
```

## 监控指标

Lark Service 提供了 Prometheus 指标用于监控授权流程：

```python
# 授权会话指标
lark_service_auth_session_total          # 总会话数
lark_service_auth_session_active         # 活跃会话数
lark_service_auth_session_expired_total  # 过期会话数

# 授权成功/失败指标
lark_service_auth_success_total          # 成功次数
lark_service_auth_failure_total          # 失败次数（按原因分类）

# 授权耗时
lark_service_auth_duration_seconds       # 授权流程耗时（p50, p95, p99）

# Token 刷新
lark_service_token_refresh_total         # Token 刷新次数
lark_service_token_active_count          # 活跃 token 数量
```

## 完整示例

查看 `FINAL_TEST_GUIDE.md` 中的完整测试流程示例。

## 限制与注意事项

### ⚠️ 公网要求

- **OAuth 回调必须使用公网可访问的 URL**
- 本地开发需要使用 ngrok 等内网穿透工具
- 生产环境需要部署到云服务器或使用负载均衡

### ⚠️ 授权流程

- 卡片授权不能替代标准 OAuth 2.0 流程
- 必须配置 `redirect_uri` 才能获取 `user_access_token`
- `authorization_code` 有效期约 5 分钟

### ⚠️ Token 管理

- `user_access_token` 有效期通常为 2 小时
- 需要使用 `refresh_token` 自动刷新
- Token 加密存储在数据库中

## 相关文档

- [部署指南](../deployment.md) - 生产环境部署
- [监控指南](../monitoring.md) - Prometheus 监控配置
- [故障排查](../troubleshooting.md) - 常见问题解决

## API 参考

- [`AuthSessionManager`](../api/auth.rst#authsessionmanager) - 会话管理
- [`CardAuthHandler`](../api/auth.rst#cardauthhandler) - 卡片授权处理
- [`CallbackServerManager`](../api/server.rst#callbackservermanager) - 回调服务器管理
