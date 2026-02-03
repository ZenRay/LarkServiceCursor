# 安装指南

## 环境要求

- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose (可选，推荐)

## 使用 pip 安装

### 开发环境

```bash
pip install -r requirements.txt
```

### 生产环境

```bash
pip install -r requirements-prod.txt
```

## 使用 Docker 部署

### 1. 克隆项目

```bash
git clone <repository_url>
cd LarkServiceCursor
```

### 2. 配置环境变量

复制并编辑环境变量文件：

```bash
cp .env.example .env
```

必需的环境变量：

```bash
# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=your_secure_password

# 加密密钥
LARK_CONFIG_ENCRYPTION_KEY=your_32_byte_fernet_key

# 飞书应用配置（通过 CLI 添加）
# APP_ID 和 APP_SECRET 在应用初始化时配置
```

### 3. 启动服务

```bash
docker compose up -d
```

### 4. 运行数据库迁移

```bash
docker compose exec app alembic upgrade head
```

### 5. 配置飞书应用

使用 CLI 工具添加应用配置：

```bash
lark-service-cli app add \
    --app-id cli_xxx \
    --app-secret xxx \
    --app-name "我的应用"
```

## 验证安装

```python
from lark_service.core import Config
from lark_service.messaging import MessagingClient

# 加载配置
config = Config.load_from_env()

# 测试连接
print("✅ Lark Service 安装成功！")
```

## 下一步

- 阅读 [快速开始](quickstart.md) 了解基本用法
- 查看 [使用指南](usage/messaging.md) 学习各模块功能
- 参考 [API 文档](api/core.rst) 查看完整 API
