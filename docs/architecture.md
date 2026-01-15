# Lark Service 架构设计文档

**版本**: 1.0.0  
**更新时间**: 2026-01-15  
**状态**: Draft

## 1. 系统概述

Lark Service 是一个 Python 库项目,封装飞书 OpenAPI,为内部系统提供高度复用且透明的接入能力。

### 1.1 设计目标

- **透明性**: 开发者无需关心 Token 管理,组件自动处理认证细节
- **复用性**: 作为 Python 包,可被任何 Python 应用导入使用
- **可靠性**: 99.9% 可用性,自动重试和故障恢复
- **安全性**: 加密存储敏感信息,零信任安全原则
- **可扩展性**: 模块化设计,易于添加新功能

### 1.2 核心特性

1. **自动 Token 管理**: 懒加载、自动刷新、并发安全、多应用隔离
2. **模块化架构**: Messaging、CloudDoc、Contact、aPaaS 四大模块
3. **混合存储**: SQLite (应用配置) + PostgreSQL (Token/用户缓存)
4. **消息队列**: RabbitMQ 处理交互式卡片回调
5. **CLI 工具**: 命令行管理应用配置

## 2. 系统架构

### 2.1 高层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      调用方应用                                   │
│         (Django / Flask / FastAPI / Airflow / Celery)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ 集成方式:
                            │ 1. Git Submodule (推荐) ⭐
                            │ 2. uv pip install lark-service
                            │ import lark_service
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LarkServiceClient                              │
│                  (统一客户端入口)                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬─────────────────┐
        ▼                   ▼                   ▼                 ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Messaging   │   │  CloudDoc    │   │   Contact    │   │    aPaaS     │
│   模块       │   │   模块       │   │    模块      │   │    模块      │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │                  │
       └──────────────────┴──────────────────┴──────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Token 凭证池                                  │
│  • get_token(app_id, token_type)                                │
│  • refresh_token(app_id, token_type)                            │
│  • 懒加载 • 自动刷新 • 并发安全 • 多应用隔离                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬─────────────────┐
        ▼                   ▼                   ▼                 ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  SQLite      │   │ PostgreSQL   │   │  RabbitMQ    │   │ Lark OpenAPI │
│  应用配置    │   │ Token存储    │   │  消息队列    │   │   飞书API    │
│  加密存储    │   │ 用户缓存     │   │  卡片回调    │   │              │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### 2.2 模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                        应用层                                │
│  Messaging │ CloudDoc │ Contact │ aPaaS                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       核心层 (core/)                         │
│  • CredentialPool (Token 管理)                              │
│  • Config (配置加载)                                         │
│  • Retry (重试策略)                                          │
│  • Response (标准响应)                                       │
│  • Exceptions (异常定义)                                     │
│  • LockManager (并发控制)                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      存储层 (storage/)                       │
│  • SQLiteStorage (应用配置管理)                              │
│  • PostgresStorage (Token 和用户缓存)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据模型层 (models/)                     │
│  • Application (SQLite)                                      │
│  • TokenStorage (PostgreSQL)                                 │
│  • UserCache (PostgreSQL)                                    │
│  • AuthSession (PostgreSQL)                                  │
└─────────────────────────────────────────────────────────────┘
```

**依赖原则**:
- ✅ 单向依赖: 上层依赖下层,下层不依赖上层
- ✅ 核心隔离: 核心层不依赖应用层模块
- ✅ 存储抽象: 应用层通过核心层访问存储,不直接访问数据库

## 3. Token 管理架构

### 3.1 Token 生命周期

```
┌─────────────┐
│  应用启动   │
└──────┬──────┘
       │
       ▼
┌─────────────┐      No      ┌─────────────┐
│ 需要Token?  │─────────────→│  继续执行   │
└──────┬──────┘              └─────────────┘
       │ Yes
       ▼
┌─────────────┐      Yes     ┌─────────────┐
│ 本地有缓存? │─────────────→│ 检查是否过期│
└──────┬──────┘              └──────┬──────┘
       │ No                         │
       │                            │ 未过期
       │                            ▼
       │                     ┌─────────────┐
       │                     │  返回Token  │
       │                     └─────────────┘
       │                            │
       │                            │ 即将过期 (剩余<10%)
       ▼                            ▼
┌─────────────┐              ┌─────────────┐
│ 获取锁      │◀─────────────│ 后台刷新    │
└──────┬──────┘              └─────────────┘
       │
       ▼
┌─────────────┐      成功     ┌─────────────┐
│ 调用飞书API │─────────────→│ 存储到PG    │
└──────┬──────┘              └──────┬──────┘
       │ 失败                       │
       │                            ▼
       ▼                     ┌─────────────┐
┌─────────────┐              │  返回Token  │
│ 重试(指数退避)│              └─────────────┘
└──────┬──────┘
       │ 3次失败
       ▼
┌─────────────┐
│  抛出异常   │
└─────────────┘
```

### 3.2 并发控制

**问题**: 多个进程/线程同时请求 Token,可能导致重复刷新

**解决方案**: 线程锁 + 进程锁

```python
# 线程锁 (同一进程内)
threading_lock = threading.Lock()

# 进程锁 (跨进程)
file_lock = filelock.FileLock("/tmp/lark_token_{app_id}_{token_type}.lock")

with threading_lock:
    with file_lock.acquire(timeout=30):
        # 双重检查: 可能其他进程已经刷新了
        token = get_from_cache()
        if token and not is_expired(token):
            return token
        
        # 刷新 Token
        new_token = refresh_from_api()
        save_to_cache(new_token)
        return new_token
```

### 3.3 多应用隔离

**设计**: 按 `app_id` 隔离 Token 和配置

```
PostgreSQL tokens 表:
┌─────────┬────────────┬─────────────┬──────────────┬────────────┐
│ app_id  │ token_type │ token_value │  expires_at  │ created_at │
├─────────┼────────────┼─────────────┼──────────────┼────────────┤
│ cli_app1│ app_access │ t-xxx1      │ 2026-01-15   │ 2026-01-15 │
│ cli_app2│ app_access │ t-xxx2      │ 2026-01-15   │ 2026-01-15 │
│ cli_app1│ tenant     │ t-xxx3      │ 2026-01-15   │ 2026-01-15 │
└─────────┴────────────┴─────────────┴──────────────┴────────────┘

唯一约束: (app_id, token_type)
```

## 4. 存储架构

### 4.1 混合存储设计

**SQLite (应用配置)**:
- **用途**: 存储飞书应用配置 (App ID、App Secret、应用名称等)
- **优势**: 轻量级、无需额外服务、文件级加密
- **位置**: `config/applications.db`
- **并发**: 低并发场景 (仅配置管理时写入)

**PostgreSQL (Token 和用户缓存)**:
- **用途**: 存储 Token、用户缓存、认证会话
- **优势**: 高并发、事务支持、pg_crypto 加密
- **表结构**:
  - `tokens`: Token 存储
  - `user_cache`: 用户信息缓存 (24h TTL)
  - `auth_sessions`: OAuth 认证会话

### 4.2 数据库 Schema

**tokens 表**:
```sql
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(64) NOT NULL,
    token_type VARCHAR(32) NOT NULL,
    token_value TEXT NOT NULL,  -- 加密存储
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(app_id, token_type)
);

CREATE INDEX idx_tokens_app_id ON tokens(app_id);
CREATE INDEX idx_tokens_expires_at ON tokens(expires_at);
```

**user_cache 表**:
```sql
CREATE TABLE user_cache (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(64) NOT NULL,
    open_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64),
    union_id VARCHAR(64),
    email VARCHAR(255),
    mobile VARCHAR(32),
    name VARCHAR(128),
    cached_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,  -- 24h TTL
    UNIQUE(app_id, open_id)
);

CREATE INDEX idx_user_cache_app_id ON user_cache(app_id);
CREATE INDEX idx_user_cache_expires_at ON user_cache(expires_at);
```

## 5. 安全架构

### 5.1 加密策略

**SQLite 应用配置加密**:
```python
from cryptography.fernet import Fernet

# 加密密钥从环境变量读取
encryption_key = os.getenv("LARK_CONFIG_ENCRYPTION_KEY")
fernet = Fernet(encryption_key)

# 加密 App Secret
encrypted_secret = fernet.encrypt(app_secret.encode())

# 解密 App Secret
decrypted_secret = fernet.decrypt(encrypted_secret).decode()
```

**PostgreSQL Token 加密 (可选)**:
```sql
-- 使用 pg_crypto 扩展
INSERT INTO tokens (app_id, token_type, token_value, expires_at)
VALUES (
    'cli_xxx',
    'app_access',
    pgp_sym_encrypt('token_value', 'encryption_key'),
    NOW() + INTERVAL '2 hours'
);

-- 解密
SELECT pgp_sym_decrypt(token_value::bytea, 'encryption_key') FROM tokens;
```

### 5.2 零信任原则

- ✅ 所有敏感信息加密存储
- ✅ 加密密钥从环境变量读取,不硬编码
- ✅ .env 文件加入 .gitignore
- ✅ 生产环境使用 Docker secrets 或 Kubernetes secrets
- ✅ 最小权限原则 (数据库用户权限最小化)

## 6. 性能优化

### 6.1 缓存策略

**Token 缓存**:
- 内存缓存 (进程内,最快)
- PostgreSQL 缓存 (跨进程,持久化)
- 懒加载 (首次使用时才获取)

**用户信息缓存**:
- PostgreSQL 缓存 (24 小时 TTL)
- 自动过期清理 (定时任务)

### 6.2 连接池

```python
# SQLAlchemy 连接池配置
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,          # 连接池大小
    max_overflow=20,       # 最大溢出连接
    pool_timeout=30,       # 获取连接超时
    pool_recycle=3600,     # 连接回收时间
)
```

### 6.3 重试策略

```python
# 指数退避重试
retry_delays = [1, 2, 4]  # 秒
max_retries = 3

for attempt in range(max_retries):
    try:
        return call_api()
    except RetryableError:
        if attempt < max_retries - 1:
            time.sleep(retry_delays[attempt])
        else:
            raise
```

## 7. 可观测性

### 7.1 日志架构

```python
# 结构化日志
logger.info(
    "token_acquired",
    extra={
        "app_id": app_id,
        "token_type": token_type,
        "request_id": request_id,
        "duration_ms": duration,
    }
)
```

### 7.2 监控指标

- Token 获取成功率
- Token 刷新频率
- API 调用延迟 (P50、P95、P99)
- 数据库连接池使用率
- 缓存命中率

### 7.3 请求追踪

```python
# 每个请求生成唯一 ID
request_id = str(uuid.uuid4())

# 贯穿整个调用链
logger.info("api_call_start", extra={"request_id": request_id})
# ... API 调用 ...
logger.info("api_call_end", extra={"request_id": request_id})
```

## 8. 部署架构

### 8.1 本地开发

```bash
# 创建 Conda 环境
conda create -n lark-service python=3.12
conda activate lark-service

# 安装 uv
pip install uv

# 启动依赖服务
docker compose up -d  # 启动 PostgreSQL + RabbitMQ

# 安装开发模式
uv pip install -e .

# 运行测试
pytest tests/
```

### 8.2 生产部署

**作为 Python 库**:
```bash
# 在应用中安装 (使用 uv 更快)
uv pip install lark-service

# 或使用 pip
pip install lark-service

# 配置环境变量
export POSTGRES_HOST=prod-postgres
export LARK_CONFIG_ENCRYPTION_KEY=xxx

# 应用代码中导入使用
from lark_service import LarkServiceClient
```

**依赖服务**:
- PostgreSQL 15+ (高可用集群)
- RabbitMQ 3+ (集群模式)

## 9. 扩展性设计

### 9.1 添加新模块

```python
# 1. 创建模块目录
src/lark_service/new_module/
├── __init__.py
├── client.py
├── models.py

# 2. 实现客户端
class NewModuleClient:
    def __init__(self, credential_pool):
        self.credential_pool = credential_pool
    
    def some_method(self):
        token = self.credential_pool.get_token(...)
        # 调用飞书 API

# 3. 注册到主客户端
class LarkServiceClient:
    def __init__(self, app_id):
        self.new_module = NewModuleClient(self.credential_pool)
```

### 9.2 添加新 Token 类型

```python
# 在 CredentialPool 中添加
def get_user_access_token(self, app_id, user_id):
    return self._get_token(
        app_id=app_id,
        token_type="user_access",
        fetch_func=lambda: self._fetch_user_token(user_id)
    )
```

## 10. 技术栈总结

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| **语言** | Python 3.12 | 现代 Python,类型提示支持 |
| **核心依赖** | lark-oapi, Pydantic v2, SQLAlchemy 2.0 | 官方 SDK,数据验证,ORM |
| **数据库** | SQLite + PostgreSQL | 混合存储架构 |
| **消息队列** | RabbitMQ | 可靠的消息传递 |
| **加密** | cryptography, pg_crypto | 对称加密,数据库加密 |
| **并发** | threading, filelock | 线程锁,进程锁 |
| **CLI** | Click, Rich | 命令行框架,美化输出 |
| **测试** | Pytest, pytest-cov | 单元测试,覆盖率 |
| **代码质量** | Ruff, Mypy | 格式化,类型检查 |
| **容器化** | Docker, Docker Compose | 容器化部署 |

---

**维护者**: Lark Service Team  
**最后更新**: 2026-01-15  
**版本**: 1.0.0
