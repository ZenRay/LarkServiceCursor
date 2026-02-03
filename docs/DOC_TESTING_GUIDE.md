# 🚀 文档示例代码运行环境准备指南

## 📋 需要启动的服务

### 1. Docker Compose 服务

#### 启动所有服务
```bash
cd /home/ray/Documents/Files/LarkServiceCursor
docker compose up -d
```

#### 包含的服务：
- **PostgreSQL** (端口 5432) - Token 存储数据库
- **RabbitMQ** (端口 5672, 管理端口 15672) - 消息队列
- **Redis** (可选，如启用缓存)

#### 检查服务状态
```bash
docker compose ps
```

#### 查看服务日志
```bash
docker compose logs -f postgres
docker compose logs -f rabbitmq
```

### 2. 数据库初始化

#### 运行数据库迁移
```bash
# 确保 PostgreSQL 已启动
alembic upgrade head
```

#### 验证数据库连接
```bash
python -c "
from lark_service.core.config import Config
from lark_service.core.storage import TokenStorageService

config = Config.load_from_env()
token_storage = TokenStorageService(db_path=config.config_db_path)
print('✅ 数据库连接成功')
"
```

### 3. 配置应用

#### 添加测试应用
```bash
lark-service-cli app add \
    --app-id cli_a8c8dc731cb9900e \
    --app-secret IVIdCYYQ9xnbO2d50xg0BcKWzMbJvMyw \
    --app-name "长沙仓服务应用"
```

#### 验证应用配置
```bash
lark-service-cli app list
```

## 🧪 测试文档示例

### 快速测试（quickstart.md）

```bash
# 创建测试脚本
cat > test_quickstart.py << 'EOF'
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
token_storage = TokenStorageService(db_path=config.config_db_path)
credential_pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage
)

# 3. 创建消息客户端
messaging_client = MessagingClient(pool=credential_pool)

print("✅ 所有组件初始化成功！")
print(f"Config DB: {config.config_db_path}")
print(f"Token DB: {config.token_db_url}")
EOF

# 运行测试
python test_quickstart.py
```

## 📊 已验证的文档列表

✅ 所有核心文档已验证通过（81 个代码块）：

1. ✅ quickstart.md - 4 个代码块
2. ✅ installation.md - 1 个代码块
3. ✅ api-examples.md - 9 个代码块
4. ✅ usage/app-management.md - 13 个代码块
5. ✅ usage/messaging.md - 2 个代码块
6. ✅ usage/card.md - 21 个代码块
7. ✅ usage/contact.md - 1 个代码块
8. ✅ usage/clouddoc.md - 1 个代码块
9. ✅ usage/auth.md - 14 个代码块
10. ✅ usage/scheduler.md - 15 个代码块

## 🔧 常见问题

### Q: PostgreSQL 连接失败
```bash
# 检查 .env 配置
cat .env | grep POSTGRES

# 检查 PostgreSQL 容器状态
docker compose ps postgres

# 重启 PostgreSQL
docker compose restart postgres
```

### Q: 应用配置不存在
```bash
# 检查配置数据库
sqlite3 config/applications.db "SELECT app_id, app_name FROM applications;"

# 重新添加应用
lark-service-cli app add --app-id YOUR_APP_ID --app-secret YOUR_SECRET --app-name "测试应用"
```

### Q: Token 存储错误
```bash
# 检查 Token 数据库连接
python -c "
from lark_service.core.storage import TokenStorageService
from lark_service.core.config import Config

config = Config.load_from_env()
try:
    ts = TokenStorageService(db_path=config.config_db_path)
    print('✅ Token 存储初始化成功')
except Exception as e:
    print(f'❌ 错误: {e}')
"
```

## 📝 环境变量检查清单

确保 `.env` 文件包含以下配置：

```bash
# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=your_password

# SQLite 配置
CONFIG_DB_PATH=config/applications.db

# 加密密钥
LARK_CONFIG_ENCRYPTION_KEY=your_32_byte_key

# 飞书 API 配置（可选，CLI 添加应用时会存储）
# LARK_APP_ID=cli_xxx
# LARK_APP_SECRET=xxx
```

## 🎯 下一步

1. ✅ 启动 Docker Compose 服务
2. ✅ 运行数据库迁移
3. ✅ 添加应用配置
4. ✅ 运行测试脚本验证
5. 📚 开始使用文档示例代码

所有代码示例已验证可用！
