# 生产环境配置指南

**版本**: 1.0.0
**更新时间**: 2026-01-18
**重要性**: ⚠️ **P1阻塞项 - 生产部署必需**

---

## 📋 配置检查清单

### 1. 生成加密密钥

```bash
# 生成Fernet加密密钥
python3 -c "from cryptography.fernet import Fernet; print('加密密钥:', Fernet.generate_key().decode())"
```

**示例输出**:
```
加密密钥: J1bBAW1hWNdQSYlTNmHuwevjw0C--Fhu7vfgQaG5dzM=
```

### 2. 设置环境变量

创建生产环境配置文件:

```bash
# 创建 .env.production 文件
cat > .env.production << 'ENVEOF'
# ===== 加密密钥 =====
LARK_CONFIG_ENCRYPTION_KEY=J1bBAW1hWNdQSYlTNmHuwevjw0C--Fhu7vfgQaG5dzM=

# ===== PostgreSQL 配置 (FR-122) =====
POSTGRES_HOST=prod-db.internal.example.com
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=your_strong_password_here_min_16_chars

# PostgreSQL 连接池配置 (FR-120)
DB_POOL_SIZE=10
DB_POOL_TIMEOUT=30
DB_POOL_MAX_OVERFLOW=5
DB_POOL_RECYCLE=3600

# ===== RabbitMQ 配置 (FR-122.1) =====
RABBITMQ_HOST=prod-mq.internal.example.com
RABBITMQ_PORT=5672
RABBITMQ_USER=lark_service
RABBITMQ_PASSWORD=your_strong_password_here_min_16_chars
RABBITMQ_VHOST=/
RABBITMQ_QUEUE_NAME=lark_card_callbacks
RABBITMQ_DLQ_NAME=lark_card_callbacks_dlq
RABBITMQ_HEARTBEAT=60
RABBITMQ_CONNECTION_TIMEOUT=30

# ===== Contact 缓存配置 =====
CONTACT_CACHE_TTL_HOURS=24

# ===== Token 刷新阈值 =====
TOKEN_REFRESH_THRESHOLD=300

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_FORMAT=json

# ===== 飞书 API 配置 =====
LARK_API_BASE_URL=https://open.feishu.cn

# ===== 环境标识 =====
ENVIRONMENT=production
LARK_CONFIG_DB_PATH=./config/applications.db
ENVEOF
```

### 3. 设置文件权限 (FR-109)

```bash
# 设置 .env.production 权限为 600 (仅所有者可读写)
chmod 600 .env.production

# 验证权限
ls -l .env.production
# 应显示: -rw------- 1 user group ... .env.production

# 设置 SQLite 配置文件权限
chmod 600 config/applications.db

# 验证权限
ls -l config/applications.db
# 应显示: -rw------- 1 user group ... config/applications.db
```

### 4. 验证配置

```bash
# 运行生产就绪检查脚本
./scripts/production-checks.sh

# 预期输出:
# ✓ 所有必需环境变量已设置
# ✓ .env 文件权限正确 (600)
# ✓ SQLite配置文件权限正确 (600)
```

---

## 🔒 安全最佳实践

### 强密码要求

- **长度**: ≥ 16 字符
- **复杂度**: 包含大小写字母、数字、特殊字符
- **唯一性**: PostgreSQL 和 RabbitMQ 使用不同密码
- **轮换**: 每90天更换一次密码

### 生成强密码

```bash
# 方法1: 使用 openssl
openssl rand -base64 24

# 方法2: 使用 pwgen
pwgen -s 32 1

# 方法3: 使用 Python
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

### 环境变量管理

✅ **推荐做法**:
- 使用 `.env.production` 文件存储配置
- 文件权限设置为 600
- 将 `.env.*` 加入 `.gitignore`
- 使用密钥管理服务 (AWS Secrets Manager / HashiCorp Vault)

❌ **禁止做法**:
- 将 `.env.production` 提交到 Git
- 在代码中硬编码密码
- 使用弱密码或默认密码
- 在日志中明文记录敏感信息

---

## 📊 配置验证脚本

创建验证脚本 `scripts/validate-config.sh`:

```bash
#!/bin/bash
#
# 验证生产环境配置
#

echo "========================================="
echo "生产环境配置验证"
echo "========================================="
echo ""

# 检查环境变量
required_envs=(
    "LARK_CONFIG_ENCRYPTION_KEY"
    "POSTGRES_HOST"
    "POSTGRES_DB"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
    "RABBITMQ_HOST"
    "RABBITMQ_USER"
    "RABBITMQ_PASSWORD"
)

all_set=true
for env in "${required_envs[@]}"; do
    if [ -z "${!env}" ]; then
        echo "❌ 缺少环境变量: $env"
        all_set=false
    else
        echo "✓ $env 已设置"
    fi
done

echo ""

# 检查文件权限
if [ -f ".env.production" ]; then
    perms=$(stat -c "%a" .env.production 2>/dev/null || stat -f "%A" .env.production 2>/dev/null)
    if [ "$perms" = "600" ]; then
        echo "✓ .env.production 权限正确 (600)"
    else
        echo "⚠️ .env.production 权限不安全: $perms (应为600)"
        echo "  修复: chmod 600 .env.production"
        all_set=false
    fi
else
    echo "⚠️ .env.production 文件不存在"
    all_set=false
fi

if [ -f "config/applications.db" ]; then
    perms=$(stat -c "%a" config/applications.db 2>/dev/null || stat -f "%A" config/applications.db 2>/dev/null)
    if [ "$perms" = "600" ]; then
        echo "✓ config/applications.db 权限正确 (600)"
    else
        echo "⚠️ config/applications.db 权限不安全: $perms (应为600)"
        echo "  修复: chmod 600 config/applications.db"
        all_set=false
    fi
fi

echo ""
echo "========================================="
if [ "$all_set" = true ]; then
    echo "✅ 所有配置检查通过!"
    exit 0
else
    echo "⚠️ 部分配置检查失败,请修复后重试"
    exit 1
fi
