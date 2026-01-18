# Quick Start Guide: Lark Service 核心组件

**Feature**: 001-lark-service-core
**Version**: 0.1.0
**Last Updated**: 2026-01-18
**Status**: Production Ready

## 概述

本指南将帮助您在 **5 分钟内**完成 Lark Service 核心组件的安装、配置并发送第一条飞书消息。

---

## 前置要求

### 环境要求

- **Python**: 3.12 或更高版本
- **SQLAlchemy**: 2.0+ (现代类型安全语法)
- **Docker**: 20.10+ (用于本地开发环境)
- **Docker Compose**: V2 (命令: `docker compose`)

### 飞书应用配置

1. 登录[飞书开放平台](https://open.feishu.cn)
2. 创建企业自建应用
3. 获取 **App ID** 和 **App Secret**
4. 开启以下权限:
   - `im:message` - 发送消息
   - `im:message.group_msg` - 发送群消息
   - `contact:user.base:readonly` - 读取用户信息

---

## 步骤 1: 选择集成方式

本服务支持两种集成方式,**推荐使用子项目集成方式**以便于开发调试和定制。

### 方式 1: 子项目集成 (推荐) ⭐

适用于需要频繁调试、深度定制或单体应用的场景。

```bash
# 1. 在你的项目中添加 lark-service 作为 Git 子模块
cd your-project
git submodule add https://github.com/your-org/lark-service.git libs/lark-service

# 2. 初始化子模块 (团队成员克隆项目后也需要执行)
git submodule update --init --recursive

# 3. 创建 Conda 环境 (推荐)
conda create -n your-project python=3.12
conda activate your-project

# 4. 安装 uv (快速包管理器)
pip install uv

# 5. 安装主项目依赖
uv pip install -r requirements.txt

# 6. 安装 lark-service 依赖
cd libs/lark-service
uv pip install -r requirements.txt
cd ../..
```

**在代码中使用**:

```python
# your_app/main.py
import sys
from pathlib import Path

# 添加子项目到 Python 路径
project_root = Path(__file__).parent.parent
lark_service_path = project_root / "libs" / "lark-service" / "src"
sys.path.insert(0, str(lark_service_path))

# 正常导入使用
from lark_service import LarkServiceClient
```

**优势**:
- ✅ **源码可见**: 便于学习、调试和定制
- ✅ **实时生效**: 修改代码无需重新安装
- ✅ **版本锁定**: Git 子模块确保团队环境一致
- ✅ **灵活定制**: 可以自由扩展功能

**项目结构**:
```
your-project/
├── libs/
│   └── lark-service/          # Git 子模块
│       ├── src/
│       │   └── lark_service/
│       ├── migrations/
│       ├── requirements.txt
│       └── pyproject.toml
├── your_app/
│   ├── __init__.py
│   └── main.py
├── .gitmodules                # 子模块配置
├── requirements.txt
└── .env
```

---

### 方式 2: PyPI 包安装 (备选)

适用于生产环境部署、多项目复用或快速集成的场景。

```bash
# 使用 uv 安装 (推荐,速度快 10-100x)
pip install uv
uv pip install lark-service

# 或使用 pip 安装
pip install lark-service

# 或从源码安装
git clone https://github.com/your-org/lark-service.git
cd lark-service
uv pip install -e .
```

**在代码中使用**:

```python
# 直接导入,无需配置路径
from lark_service import LarkServiceClient
```

**优势**:
- ✅ **标准化**: 符合 Python 生态最佳实践
- ✅ **依赖自动**: pip 自动安装所有依赖
- ✅ **更新简单**: `uv pip install --upgrade lark-service`

---

> 💡 **选择建议**:
> - **开发阶段**: 使用**方式 1 (子项目集成)** - 便于调试和定制
> - **生产部署**: 可选**方式 2 (PyPI 安装)** - 标准化管理
>
> 详细对比请参考: [research.md § 8 服务集成方式技术调研](research.md#8-服务集成方式技术调研)

---

**后续步骤说明**: 本指南后续内容以**子项目集成方式**为例。如果你选择 PyPI 安装,请跳过路径配置相关步骤。

---

## 步骤 2: 启动依赖服务

使用 Docker Compose 启动 PostgreSQL 和 RabbitMQ:

```bash
# 如果使用子项目集成方式,在主项目根目录执行
docker compose up -d postgres rabbitmq

# 如果使用 PyPI 安装方式,在 lark-service 目录执行
cd lark-service  # (仅 PyPI 方式)
docker compose up -d postgres rabbitmq
```

等待服务启动完成(约 10 秒):

```bash
# 检查服务状态
docker compose ps
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
from cryptography.fernet import Fernet
import os

# 初始化应用管理器
encryption_key = os.getenv("LARK_CONFIG_ENCRYPTION_KEY").encode()
app_manager = ApplicationManager(
    db_path="config/applications.db",
    encryption_key=encryption_key
)

# 添加应用配置
app_manager.add_application(
    app_id="cli_a1b2c3d4e5f6g7h8",
    app_name="我的飞书应用",
    app_secret="your_app_secret_here"
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
from lark_service.messaging.client import MessagingClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.config import Config
from lark_service.core.storage.sqlite_storage import ApplicationManager
from lark_service.core.storage.postgres_storage import TokenStorageService
from pathlib import Path

# 初始化配置和服务
config = Config()
app_manager = ApplicationManager(config.config_db_path, config.config_encryption_key)
token_storage = TokenStorageService(config.get_postgres_url())

# 创建 Token 池
pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage,
    lock_dir=Path("/tmp/lark_locks")
)

# 创建消息客户端
client = MessagingClient(pool)

# 发送文本消息(组件会自动获取和管理 Token)
app_id = "cli_a1b2c3d4e5f6g7h8"  # 使用您在步骤4.2中添加的 App ID
receive_id = "ou_xxxxxxxxxxxxxxxx"  # 替换为接收者的 open_id

result = client.send_text_message(
    app_id=app_id,
    receive_id=receive_id,
    receive_id_type="open_id",
    content="Hello from Lark Service! 🚀"
)

print(f"消息发送成功!")
print(f"Message ID: {result['message_id']}")

# 清理资源
pool.close()
token_storage.close()
app_manager.close()
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
Message ID: om_xxxxxxxxxxxxxxxx
```

并且接收者会在飞书中收到消息! ✅

---

## 常见功能示例

### 发送富文本消息

```python
from lark_service.messaging.client import MessagingClient

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
    app_id=app_id,
    receive_id=receive_id,
    receive_id_type="open_id",
    content=content
)
```
```

---

## 多应用场景

如果您的组织使用多个飞书自建应用,需要分别添加到 SQLite 数据库:

```bash
# 添加应用 1
python -m lark_service.cli app add \
  --app-id "cli_app1_xxxxxxxx" \
  --app-secret "secret1_xxxxxxxx" \
  --name "应用1-内部系统"

# 添加应用 2
python -m lark_service.cli app add \
  --app-id "cli_app2_xxxxxxxx" \
  --app-secret "secret2_xxxxxxxx" \
  --name "应用2-外部集成"
```

代码中指定 app_id:

```python
# 使用应用 1 发送消息
result1 = client.send_text_message(
    app_id="cli_app1_xxxxxxxx",
    receive_id="ou_xxx",
    receive_id_type="open_id",
    content="来自应用1的消息"
)

# 使用应用 2 发送消息
result2 = client.send_text_message(
    app_id="cli_app2_xxxxxxxx",
    receive_id="ou_xxx",
    receive_id_type="open_id",
    content="来自应用2的消息"
)
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
3. **探索架构设计**: 查看 `docs/architecture.md` 了解系统架构和设计原则
4. **集成更多模块**:
   - **CloudDoc**: 操作飞书文档、Sheet、多维表格 (`lark_service.clouddoc`)
   - **Contact**: 查询用户和组织架构 (`lark_service.contact`)
   - **aPaaS**: 数据空间操作 (`lark_service.apaas`)
   - **CardKit**: 构建交互式卡片 (`lark_service.cardkit`)
5. **查看测试示例**: 参考 `tests/integration/` 下的集成测试代码

---

## 获取帮助

- **问题反馈**: [GitHub Issues](https://github.com/your-org/lark-service/issues)
- **技术支持**: tech-support@your-company.com
- **飞书开放平台文档**: https://open.feishu.cn/document/home/index

---

**Happy Coding! 🚀**
