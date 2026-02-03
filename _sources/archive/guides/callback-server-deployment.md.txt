# Lark Callback Server 部署指南

本文档说明如何部署和配置 Lark Callback Server 以接收飞书的卡片交互回调。

## 📋 目录

- [架构说明](#架构说明)
- [环境要求](#环境要求)
- [配置说明](#配置说明)
- [部署方式](#部署方式)
- [飞书开放平台配置](#飞书开放平台配置)
- [扩展回调处理器](#扩展回调处理器)
- [故障排查](#故障排查)

---

## 架构说明

Lark Callback Server 是一个基于 Python 标准库 `http.server` 的轻量级 HTTP 服务器，用于接收飞书的各类回调事件。

### 核心组件

1. **CallbackServer** (`src/lark_service/server/callback_server.py`)
   - HTTP 服务器主体
   - 处理请求路由和签名验证

2. **CallbackRouter** (`src/lark_service/server/callback_router.py`)
   - 回调路由器
   - 将不同类型的回调分发到相应的处理器

3. **Callback Handlers** (`src/lark_service/server/handlers/`)
   - 各类回调的具体处理逻辑
   - 当前支持：卡片授权回调 (`card_action_trigger`)

### 为什么需要 HTTP 回调服务器？

根据[飞书官方事件列表](https://open.feishu.cn/document/server-docs/event-subscription-guide/event-list)，**卡片交互事件 (`card.action.trigger`) 不属于"事件订阅"系统**，而是通过"回调配置"系统处理。

这意味着：
- ✅ 卡片交互必须通过 HTTP 回调接收
- ❌ 无法通过 WebSocket 事件订阅接收卡片交互

---

## 环境要求

### 必需

- Python 3.12+
- PostgreSQL 数据库
- 公网可访问的域名或 IP（或使用 ngrok 等内网穿透工具）

### 可选

- Docker（用于容器化部署）
- Nginx（用于反向代理和 HTTPS）

---

## 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# === 飞书应用配置 ===
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
LARK_VERIFICATION_TOKEN=xxx
LARK_ENCRYPT_KEY=xxx  # 可选，用于签名验证
LARK_CONFIG_ENCRYPTION_KEY=xxx  # 用于加密敏感配置

# === 回调服务器配置 ===
# ⚠️ IMPORTANT: 回调服务器是可选的！
# 只有在需要接收卡片交互回调时才需要启用
CALLBACK_SERVER_ENABLED=false  # 设置为 true 启用回调服务器
CALLBACK_SERVER_HOST=0.0.0.0
CALLBACK_SERVER_PORT=8080

# === 数据库配置 ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=lark_password_123

# === Token 存储配置 ===
TOKEN_DB_PATH=data/config.db
```

---

## 部署方式

### ⚠️ 重要提示

**回调服务器是可选的！** 只有在需要接收卡片交互回调（如用户授权）时才需要启动。

如果你的应用不需要：
- ❌ 卡片交互授权
- ❌ 其他 HTTP 回调事件

那么你**不需要启动回调服务器**！

### 启用回调服务器

在 `.env` 文件中设置：

```bash
CALLBACK_SERVER_ENABLED=true
```

### 方式 1：直接运行

```bash
cd /home/ray/Documents/Files/LarkServiceCursor

# 设置 PYTHONPATH
export PYTHONPATH=/home/ray/Documents/Files/LarkServiceCursor/src:$PYTHONPATH

# 设置启用回调服务器
export CALLBACK_SERVER_ENABLED=true

# 启动服务器
python src/lark_service/server/run_server.py
```

如果 `CALLBACK_SERVER_ENABLED` 未设置为 `true`，服务器会显示警告并退出。

### 方式 2：使用 systemd 服务

创建 systemd 服务文件 `/etc/systemd/system/lark-callback.service`:

```ini
[Unit]
Description=Lark Callback Server
After=network.target postgresql.service

[Service]
Type=simple
User=lark
WorkingDirectory=/opt/lark-service
Environment="PYTHONPATH=/opt/lark-service/src"
EnvironmentFile=/opt/lark-service/.env
ExecStart=/usr/bin/python3 /opt/lark-service/src/lark_service/server/run_server.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable lark-callback
sudo systemctl start lark-callback
sudo systemctl status lark-callback
```

### 方式 3：使用 Docker

创建 `Dockerfile.callback`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY src/ src/
COPY .env .

# 设置环境变量
ENV PYTHONPATH=/app/src

# 暴露端口
EXPOSE 8080

# 启动服务器
CMD ["python", "src/lark_service/server/run_server.py"]
```

构建并运行：

```bash
docker build -f Dockerfile.callback -t lark-callback-server .
docker run -d -p 8080:8080 --name lark-callback lark-callback-server
```

### 方式 4：本地测试（使用 ngrok）

如果没有公网域名，可以使用 ngrok 暴露本地端口：

```bash
# 在终端 1：启动回调服务器
python src/lark_service/server/run_server.py

# 在终端 2：启动 ngrok
ngrok http 8080

# ngrok 会提供一个公网 URL，例如：
# https://abc123.ngrok.io
```

---

## 飞书开放平台配置

### 1. 进入应用管理

访问 [飞书开放平台](https://open.feishu.cn/app)，进入你的应用。

### 2. 配置回调地址

找到 **"事件与回调"** → **"回调配置"** (或 "Callback Configuration")

配置回调 URL：

```
https://your-domain.com/callback
```

或使用 ngrok 临时 URL：

```
https://abc123.ngrok.io/callback
```

### 3. URL 验证

首次配置回调地址时，飞书会发送 URL 验证请求：

```json
{
  "type": "url_verification",
  "challenge": "xxx",
  "token": "xxx"
}
```

服务器会自动响应验证请求，返回：

```json
{
  "challenge": "xxx"
}
```

### 4. 添加回调事件类型

在 **"订阅的回调事件"** 中，勾选：

- ✅ `card.action.trigger` (卡片交互)

保存配置。

### 5. 配置重定向 URI（用于 OAuth）

在 **"安全设置"** → **"重定向 URL"** 中，添加：

```
https://open.feishu.cn/
```

**注意**：虽然使用 HTTP 回调模式，但 OAuth 授权流程仍需要配置 `redirect_uri`。

---

## 扩展回调处理器

### 添加新的回调处理器

#### 步骤 1：创建处理器

在 `src/lark_service/server/handlers/` 中创建新的处理器文件，例如 `message_handler.py`：

```python
"""Handler for message callbacks."""

from typing import Any
from lark_service.utils.logger import get_logger

logger = get_logger()


def create_message_handler() -> Any:
    """Create a callback handler for message events."""

    async def handle_message_receive(callback_data: dict[str, Any]) -> dict[str, Any]:
        """Handle message receive callbacks."""
        try:
            message = callback_data.get("message", {})
            content = message.get("content")

            logger.info(f"Received message: {content}")

            # 处理消息逻辑
            # ...

            return {"status": "ok"}

        except Exception as e:
            logger.error(f"Failed to handle message: {e}", exc_info=True)
            return {"error": str(e)}

    return handle_message_receive
```

#### 步骤 2：注册处理器

在 `src/lark_service/server/run_server.py` 中注册：

```python
from lark_service.server.handlers.message_handler import create_message_handler

# ... 初始化代码 ...

# Register message handler
message_handler = create_message_handler()
server.register_handler("message_receive", message_handler)
```

#### 步骤 3：配置飞书回调

在飞书开放平台的 **"回调配置"** 中，添加新的回调事件类型。

---

## 故障排查

### 问题 1：回调服务器无法启动

**症状**：
```
ModuleNotFoundError: No module named 'lark_service'
```

**解决方案**：
```bash
export PYTHONPATH=/path/to/LarkServiceCursor/src:$PYTHONPATH
```

---

### 问题 2：飞书回调超时

**症状**：
- 飞书显示"回调地址不可达"
- 服务器日志无请求记录

**可能原因**：
1. 防火墙阻止了外网访问
2. 回调 URL 配置错误
3. 服务器未运行

**解决方案**：
```bash
# 检查服务器是否运行
curl http://localhost:8080/health

# 检查防火墙
sudo ufw status
sudo ufw allow 8080

# 使用 ngrok 测试
ngrok http 8080
```

---

### 问题 3：签名验证失败

**症状**：
```
Signature verification failed
```

**解决方案**：
1. 确认 `.env` 中的 `LARK_ENCRYPT_KEY` 与飞书开放平台一致
2. 检查服务器时间是否准确（签名验证依赖时间戳）

```bash
# 同步系统时间
sudo ntpdate -u pool.ntp.org
```

---

### 问题 4：卡片授权失败

**症状**：
- 用户点击授权按钮后无响应
- 日志显示"No handler for callback type"

**解决方案**：
1. 确认已注册 `card_action_trigger` 处理器
2. 检查回调数据格式是否正确

```bash
# 查看服务器日志
tail -f /var/log/lark-callback/server.log

# 查看已注册的处理器
curl http://localhost:8080/health
```

---

## 监控和日志

### 健康检查

```bash
curl http://localhost:8080/health
```

响应：
```json
{
  "status": "ok",
  "message": "Lark Callback Server is running",
  "registered_handlers": ["card_action_trigger"]
}
```

### 日志位置

日志通过 `lark_service.utils.logger` 模块输出，可以配置输出到文件或 stdout。

---

## 安全建议

1. **启用签名验证**：配置 `LARK_ENCRYPT_KEY` 以验证请求来源
2. **使用 HTTPS**：在 Nginx 等反向代理中配置 SSL 证书
3. **限制访问**：配置防火墙规则，仅允许飞书服务器 IP 访问
4. **定期更新**：及时更新依赖包和系统安全补丁

---

## 参考资料

- [飞书事件列表](https://open.feishu.cn/document/server-docs/event-subscription-guide/event-list)
- [飞书卡片回调文档](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-callback-communication)
- [飞书长连接接收事件](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/request-url-configuration-case)
