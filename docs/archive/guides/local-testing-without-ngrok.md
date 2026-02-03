# 本地测试指南（无需 ngrok）

如果你没有 ngrok 或不想使用内网穿透工具，有以下几种方案可以在本地测试用户授权流程。

## 📋 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **方案 1**: 其他内网穿透工具 | 免费、简单 | 需要安装工具 | 个人开发测试 |
| **方案 2**: 本地公网 IP | 无需额外工具 | 需要有公网 IP | 有公网 IP 的服务器 |
| **方案 3**: 模拟飞书回调 | 完全本地化 | 不是真实流程 | 开发阶段调试 |
| **方案 4**: Docker + 反向代理 | 接近生产环境 | 配置复杂 | 团队协作测试 |

---

## 方案 1：使用其他内网穿透工具（推荐）

### 1.1 使用 Localtunnel（最简单）

**安装：**
```bash
npm install -g localtunnel
```

**使用：**
```bash
# 启动本地服务（端口 8000）
lt --port 8000

# 输出示例：
# your url is: https://funny-cat-12.loca.lt
```

复制输出的 URL，配置到飞书开放平台即可。

### 1.2 使用 Cloudflare Tunnel（免费且稳定）

**安装：**
```bash
# Linux/macOS
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

**使用：**
```bash
# 启动隧道
cloudflared tunnel --url http://localhost:8000

# 输出示例：
# Your quick Tunnel has been created! Visit it at:
# https://random-name-123.trycloudflare.com
```

### 1.3 使用 Serveo（无需安装）

**使用：**
```bash
ssh -R 80:localhost:8000 serveo.net

# 输出示例：
# Forwarding HTTP traffic from https://xyz123.serveo.net
```

---

## 方案 2：使用本地公网 IP（适合有公网 IP 的服务器）

### 前提条件
- 服务器有公网 IP
- 端口 8000 已开放（防火墙规则）

### 步骤

#### 1. 检查公网 IP
```bash
curl ifconfig.me
# 输出：123.456.789.10
```

#### 2. 开放防火墙端口
```bash
# Ubuntu/Debian
sudo ufw allow 8000

# CentOS/RHEL
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

#### 3. 修改回调服务器配置

在 `.env` 中设置：
```bash
CALLBACK_SERVER_HOST=0.0.0.0  # 监听所有接口
CALLBACK_SERVER_PORT=8000
```

#### 4. 启动测试
```bash
python test.py
```

#### 5. 配置飞书开放平台

回调 URL：`http://123.456.789.10:8000/callback`

**⚠️ 注意：**
- HTTP（非 HTTPS）可能被飞书拒绝
- 建议配置 SSL 证书（使用 Let's Encrypt）

---

## 方案 3：模拟飞书回调（纯本地测试）

这个方案不需要真实的飞书回调，而是模拟整个流程。

### 创建模拟测试脚本

```bash
cat > test_local_mock.py << 'EOF'
#!/usr/bin/env python3
"""
纯本地模拟测试 - 无需外网访问

模拟飞书的卡片回调流程，完全在本地运行
"""

import asyncio
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.clients.messaging import MessagingClient
from lark_service.config import Config
from lark_service.core.app_manager import ApplicationManager
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.token_storage import TokenStorageService
from lark_service.models.base import Base


async def main():
    """模拟完整的授权流程"""
    print("=" * 70)
    print("  本地模拟测试 - 用户授权流程")
    print("=" * 70)

    # 加载环境变量
    load_dotenv()

    app_id = os.getenv("LARK_APP_ID")
    app_secret = os.getenv("LARK_APP_SECRET")
    test_open_id = os.getenv("TEST_OPEN_ID")
    encryption_key = os.getenv("LARK_CONFIG_ENCRYPTION_KEY")

    if not all([app_id, app_secret, test_open_id, encryption_key]):
        print("❌ 缺少必需的环境变量")
        return

    # 初始化服务
    config = Config(max_retries=3, retry_backoff_base=2, timeout=30)
    app_manager = ApplicationManager(encryption_key=encryption_key)

    try:
        app_manager.add_application(
            app_id=app_id,
            app_name="Test",
            app_secret=app_secret,
        )
    except Exception:
        pass

    token_storage = TokenStorageService(db_path="data/test_config.db")
    pool = CredentialPool(config=config, app_manager=app_manager, token_storage=token_storage)

    # 初始化数据库
    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'lark_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'lark_password_123')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'lark_service')}"
    )

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()

    # 创建授权组件
    session_manager = AuthSessionManager(db=db_session)
    messaging_client = MessagingClient(credential_pool=pool)
    card_handler = CardAuthHandler(
        session_manager=session_manager,
        messaging_client=messaging_client,
        app_id=app_id,
        app_secret=app_secret,
    )

    # 步骤 1: 创建授权会话
    print("\n[步骤 1] 创建授权会话")
    session = session_manager.create_session(
        app_id=app_id,
        user_id=test_open_id,
        auth_method="websocket_card",
    )
    print(f"✅ 会话已创建: {session.session_id}")

    # 步骤 2: 模拟飞书回调事件
    print("\n[步骤 2] 模拟飞书回调事件")
    print("ℹ️  在真实场景中，这个事件由飞书发送")
    print("ℹ️  现在我们模拟用户点击授权并获得 authorization_code")

    # 模拟的 authorization_code（真实场景由飞书提供）
    mock_auth_code = "mock_authorization_code_for_testing"

    # 构建模拟的卡片回调事件
    mock_event = {
        "operator": {
            "open_id": test_open_id,
        },
        "action": {
            "value": {
                "session_id": session.session_id,
                "action": "authorize",
                "authorization_code": mock_auth_code,  # 模拟的授权码
            }
        }
    }

    print(f"✅ 模拟事件已构建")
    print(f"   Session ID: {session.session_id}")
    print(f"   Authorization Code: {mock_auth_code}")

    # 步骤 3: 处理授权事件
    print("\n[步骤 3] 处理授权事件")
    print("⚠️  注意：由于是模拟的 authorization_code，")
    print("   实际的 token 交换会失败（这是预期的）")

    try:
        response = await card_handler.handle_card_auth_event(mock_event)
        print(f"✅ 事件处理完成")
        print(f"   响应: {response}")
    except Exception as e:
        print(f"❌ 事件处理失败: {e}")
        print("ℹ️  这是预期的，因为 authorization_code 是模拟的")

    # 步骤 4: 检查会话状态
    print("\n[步骤 4] 检查会话状态")
    db_session.expire(session)
    db_session.refresh(session)

    print(f"   Session ID: {session.session_id}")
    print(f"   状态: {session.state}")
    print(f"   User ID: {session.user_id}")

    print("\n" + "=" * 70)
    print("  模拟测试完成")
    print("=" * 70)
    print("\n💡 说明：")
    print("  此脚本模拟了完整的授权流程，但使用了模拟的 authorization_code")
    print("  要进行真实测试，需要：")
    print("  1. 使用内网穿透工具（localtunnel、cloudflared 等）")
    print("  2. 或部署到有公网 IP 的服务器")
    print("  3. 在飞书开放平台配置真实的回调地址")

    # 清理
    app_manager.close()
    db_session.close()
    pool.close()


if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x test_local_mock.py
```

**运行模拟测试：**
```bash
python test_local_mock.py
```

---

## 方案 4：Docker + Nginx 反向代理（团队协作）

适合团队开发，提供稳定的测试环境。

### 创建 Docker Compose 配置

```yaml
# docker-compose.callback.yml
version: '3.8'

services:
  callback-server:
    build:
      context: .
      dockerfile: Dockerfile.callback
    ports:
      - "8000:8000"
    environment:
      - CALLBACK_SERVER_ENABLED=true
      - CALLBACK_SERVER_HOST=0.0.0.0
      - CALLBACK_SERVER_PORT=8000
    env_file:
      - .env
    depends_on:
      - postgres
    networks:
      - lark-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro  # SSL 证书
    depends_on:
      - callback-server
    networks:
      - lark-network

networks:
  lark-network:
    driver: bridge
```

### 启动服务
```bash
docker-compose -f docker-compose.callback.yml up -d
```

---

## 📊 方案选择建议

### 个人开发（推荐方案 1）
```bash
# 最简单：Localtunnel
npm install -g localtunnel
lt --port 8000
```

### 有公网服务器（方案 2）
```bash
# 配置 .env
CALLBACK_SERVER_HOST=0.0.0.0

# 开放端口
sudo ufw allow 8000

# 运行测试
python test.py
```

### 开发调试（方案 3）
```bash
# 创建模拟测试脚本
python test_local_mock.py
```

### 团队协作（方案 4）
```bash
# Docker 部署
docker-compose -f docker-compose.callback.yml up -d
```

---

## 🔧 快速对比命令

### Localtunnel
```bash
npm install -g localtunnel
lt --port 8000
# URL: https://xxx.loca.lt
```

### Cloudflare Tunnel
```bash
cloudflared tunnel --url http://localhost:8000
# URL: https://xxx.trycloudflare.com
```

### Serveo
```bash
ssh -R 80:localhost:8000 serveo.net
# URL: https://xxx.serveo.net
```

---

## ❓ 常见问题

### Q: Localtunnel 需要密码？

有时 Localtunnel 会显示密码页面。解决方法：
```bash
lt --port 8000 --subdomain my-unique-name
```

### Q: Cloudflare Tunnel 连接失败？

检查 cloudflared 是否正确安装：
```bash
cloudflared --version
```

### Q: 我的服务器没有公网 IP 怎么办？

使用方案 1（内网穿透工具）或方案 3（模拟测试）。

---

## 📚 相关资源

- [Localtunnel 文档](https://theboroer.github.io/localtunnel-www/)
- [Cloudflare Tunnel 文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps)
- [Serveo 文档](https://serveo.net/)

---

## 🎯 推荐配置

如果你是**个人开发者**，推荐使用 **Localtunnel**（最简单）：

```bash
# 安装
npm install -g localtunnel

# 终端 1：启动 localtunnel
lt --port 8000

# 终端 2：运行测试
python test.py
```

就这么简单！ 🚀
