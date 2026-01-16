# Technical Research: Lark Service 核心组件

**Feature**: 001-lark-service-core
**Date**: 2026-01-14
**Phase**: Phase 0 - Technical Research

## 调研目标

解决技术实施计划中的所有技术选型和最佳实践问题,为 Phase 1 详细设计提供充分依据。

---

## 1. 存储方案设计:混合架构

### 1.1 应用配置 vs Token 数据分离

**核心决策**: 采用 **混合存储架构**

| 数据类型 | 存储方案 | 理由 |
|---------|---------|------|
| **应用配置** (App ID/Secret/元数据) | SQLite | 轻量级,配置管理,读多写少,低并发 |
| **Token 数据** (运行时凭证) | PostgreSQL | 高并发读写,频繁刷新,多进程安全 |

### 1.2 SQLite (应用配置管理)

**用途**: 存储和管理飞书应用的配置信息

**访问模式**:
- **读**: 频繁(每次获取 Token 时读取 App Secret)
- **写**: 低频(新增/修改应用配置时)
- **并发**: 低(配置管理是低频操作)

**优势**:
- ✅ 单文件,零配置,易于部署
- ✅ 无需额外服务依赖
- ✅ 可随代码打包(初始配置)
- ✅ 文件级加密(使用 SQLCipher)

**数据表**:
```sql
CREATE TABLE applications (
    app_id VARCHAR(64) PRIMARY KEY,
    app_name VARCHAR(128) NOT NULL,
    app_secret TEXT NOT NULL,  -- Encrypted
    description TEXT,
    status VARCHAR(16) DEFAULT 'active',  -- active/disabled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64)
);

CREATE INDEX idx_apps_status ON applications(status);
```

### 1.3 PostgreSQL (Token 持久化)

**用途**: 存储运行时的访问 Token

**访问模式**:
- **读**: 极高频(每个 API 调用都需要 Token)
- **写**: 高频(Token 刷新,每 2 小时一次)
- **并发**: 高(多进程并发读写)

**优势**:
- ✅ MVCC 支持高并发读写
- ✅ 原生 pg_crypto 加密扩展
- ✅ 生产级可靠性和扩展性

**数据表**:
```sql
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(64) NOT NULL,
    token_type VARCHAR(32) NOT NULL,
    token_value TEXT NOT NULL,  -- Encrypted
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(app_id, token_type)
);
```

### 1.4 混合架构的优势

| 优势 | 说明 |
|------|------|
| **职责分离** | 配置管理和运行时数据分离,符合单一职责原则 |
| **降低复杂度** | SQLite 无需额外服务,降低部署复杂度 |
| **提升可靠性** | PostgreSQL 故障不影响应用配置读取 |
| **灵活部署** | SQLite 文件可随代码打包,支持离线配置 |
| **性能优化** | 配置读取走 SQLite(本地文件),Token 读写走 PostgreSQL(网络) |

### 1.5 实施方案

**SQLite 配置**:
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

# SQLite engine (thread-safe, single file)
config_engine = create_engine(
    "sqlite:///config/applications.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Reuse single connection
)
```

**PostgreSQL 配置**:
```python
# PostgreSQL engine (connection pool)
token_engine = create_engine(
    "postgresql://user:pass@host:5432/lark_tokens",
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600
)
```

**加密方案**:
- **SQLite**: 使用 SQLCipher 或应用层加密(如 Fernet)
- **PostgreSQL**: 使用 pg_crypto 扩展

### 1.6 决策总结

✅ **应用配置** → SQLite
- 轻量级,适合配置管理
- 无需额外服务
- 文件级加密

✅ **Token 数据** → PostgreSQL
- 高并发性能
- 原生加密支持
- 生产级可靠性

**SQLite 用于 Token 被拒绝原因**:
- 并发写入限制(多进程 Token 刷新会冲突)
- 无法满足高频读写性能要求

---

## 2. RabbitMQ vs Redis Pub/Sub 回调处理方案对比

### 评估标准

| 标准 | RabbitMQ | Redis Pub/Sub | 权重 |
|------|----------|---------------|------|
| **消息持久化** | ✅ 支持持久化队列和消息 | ❌ 仅内存,重启丢失 | 高 |
| **消息可靠性** | ✅ ACK机制,确保送达 | ❌ Fire-and-forget,无确认 | 高 |
| **复杂度** | ⚠️ 需要独立服务 | ✅ 轻量级,通常已部署 | 中 |
| **性能** | ✅ 10k+ msg/s | ✅ 100k+ msg/s | 中 |
| **功能丰富度** | ✅ 路由、延迟、死信队列 | ❌ 仅发布订阅 | 中 |

### 场景分析

**卡片回调的特性**:
- 用户点击卡片按钮 → 飞书服务器回调 → 组件接收 → 异步处理
- 不能丢失(用户操作必须被处理)
- 需要签名验证(防止伪造)
- 处理失败需要重试

**失败场景**:
- RabbitMQ: 消息持久化,消费者崩溃后可重新消费
- Redis Pub/Sub: 订阅者下线时消息丢失,无法恢复

### 决策: RabbitMQ ✅

**选择理由**:
1. **消息可靠性**: ACK 机制确保回调不丢失,符合生产级要求
2. **持久化支持**: 服务重启后回调事件可恢复处理
3. **死信队列**: 处理失败的回调可路由到死信队列人工介入
4. **功能完整**: 支持延迟消息(认证超时提醒)、优先级队列等高级特性

**Redis Pub/Sub 被拒绝原因**:
- 无持久化,不符合"不丢失用户操作"的可靠性要求
- 仅适合实时通知场景,不适合业务逻辑处理

**实施方案**:
- 使用 pika 客户端(Python RabbitMQ 官方库)
- 队列配置: durable=True, delivery_mode=2(持久化)
- 消费者配置: prefetch_count=1, auto_ack=False(手动确认)
- 死信队列: 处理失败 3 次后路由到 DLX

---

## 3. 线程锁+进程锁实现方案

### 并发场景分析

**Token 刷新并发问题**:
- **线程并发**: 同一进程内多个线程同时检测到 Token 即将过期
- **进程并发**: 多个进程(如 uWSGI workers)同时触发刷新

### 实施方案

```python
import threading
import multiprocessing
from filelock import FileLock

class TokenRefreshLock:
    """
    Hybrid lock for thread and process safety.
    """

    def __init__(self, app_id: str, token_type: str):
        self.app_id = app_id
        self.token_type = token_type

        # Thread lock (in-memory)
        self._thread_lock = threading.Lock()

        # Process lock (file-based)
        lock_file = f"/tmp/lark_token_{app_id}_{token_type}.lock"
        self._process_lock = FileLock(lock_file, timeout=30)

    def __enter__(self):
        # Acquire thread lock first
        self._thread_lock.acquire()

        # Then acquire process lock
        self._process_lock.acquire()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Release in reverse order
        self._process_lock.release()
        self._thread_lock.release()
```

**关键决策**:
1. **使用 filelock 库**: 跨进程文件锁,支持超时(30秒)
2. **锁粒度**: 每个 (app_id, token_type) 一个锁,避免全局锁竞争
3. **锁顺序**: 先线程锁后进程锁,避免死锁
4. **超时机制**: 30 秒超时避免永久阻塞,超时后记录 ERROR 日志

**死锁避免**:
- 所有代码路径使用相同的锁获取顺序
- 使用 `with` 语句确保锁释放
- 超时机制作为最后防线

---

## 4. user_access_token 认证流程设计

### 飞书 OAuth 2.0 流程

**标准流程**:
1. 用户点击授权 → 跳转飞书授权页面
2. 用户同意授权 → 飞书回调 redirect_uri 并带上 code
3. 后端用 code 换取 user_access_token

### 两种认证方式设计

#### 方式 1: 消息链接认证 (推荐)

**流程**:
1. 组件生成授权链接: `https://open.feishu.cn/oauth/authorize?app_id=xxx&redirect_uri=xxx&state=session_id`
2. 通过消息发送链接给用户: "请点击授权: [链接]"
3. 用户点击 → 飞书授权页面 → 同意
4. 飞书回调组件的 HTTP 端点: `GET /auth/callback?code=xxx&state=session_id`
5. 组件用 code 换取 user_access_token 并存储

**优点**:
- 标准 OAuth 流程,可靠性高
- 用户体验清晰(浏览器授权页面)

**缺点**:
- 需要组件暴露 HTTP 端点(增加部署复杂度)
- 需要配置公网可访问的 redirect_uri

#### 方式 2: 卡片认证

**流程**:
1. 组件发送交互式卡片,卡片包含"授权"按钮
2. 用户点击按钮 → 触发卡片回调
3. 回调中携带卡片自定义参数(session_id)
4. 组件在回调处理函数中调用飞书 API 获取用户信息
5. 使用 app_access_token 代为获取 user_access_token(需要应用权限)

**优点**:
- 无需暴露 HTTP 端点
- 流程在飞书内闭环

**缺点**:
- 依赖卡片回调机制
- 需要应用具备"代理获取用户 Token"的权限

### 决策: 支持两种方式,优先消息链接 ✅

**实施方案**:
1. **默认使用消息链接认证**(方式 1),标准且可靠
2. **可选卡片认证**(方式 2),适合无法暴露公网端点的场景
3. 认证会话管理:
   - session_id: UUID 唯一标识
   - 过期时间: 10 分钟
   - 状态: pending → completed/expired
4. 存储在 `auth_sessions` 表,定时清理过期会话

**数据模型**:
```python
class UserAuthSession(Base):
    __tablename__ = "auth_sessions"

    session_id = Column(String, primary_key=True)
    app_id = Column(String, nullable=False)
    user_id = Column(String, nullable=True)  # 认证完成后填充
    auth_method = Column(Enum("link", "card"), nullable=False)
    state = Column(Enum("pending", "completed", "expired"), default="pending")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

---

## 5. lark-oapi SDK 使用最佳实践

### SDK 初始化

```python
import lark_oapi as lark

class LarkClient:
    """
    Wrapper for lark-oapi SDK with multi-app support.
    """

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

        # SDK Client initialization
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()

    def get_tenant_access_token(self) -> str:
        """
        Get tenant_access_token using SDK.
        """
        request = lark.GetTenantAccessTokenRequest()
        response = self.client.auth.v3.tenant_access_token.get(request)

        if not response.success():
            raise TokenAcquisitionError(
                f"Failed to get token: {response.code} - {response.msg}"
            )

        return response.data.tenant_access_token
```

### 多应用隔离方案

**实施方式**:
- 为每个 app_id 创建独立的 `LarkClient` 实例
- `CredentialPool` 维护 `Dict[str, LarkClient]` 映射
- 所有 API 调用接口都需要传入 `app_id` 参数

```python
class CredentialPool:
    def __init__(self):
        self._clients: Dict[str, LarkClient] = {}
        self._tokens: Dict[Tuple[str, TokenType], Token] = {}
        self._locks: Dict[Tuple[str, TokenType], TokenRefreshLock] = {}

    def get_client(self, app_id: str) -> LarkClient:
        if app_id not in self._clients:
            app_secret = os.getenv(f"LARK_APP_SECRET_{app_id}")
            self._clients[app_id] = LarkClient(app_id, app_secret)
        return self._clients[app_id]

    def get_token(self, app_id: str, token_type: TokenType) -> str:
        # Check cache first
        key = (app_id, token_type)
        if key in self._tokens and not self._tokens[key].is_expired():
            return self._tokens[key].value

        # Refresh with lock
        lock = self._get_lock(app_id, token_type)
        with lock:
            # Double check after acquiring lock
            if key in self._tokens and not self._tokens[key].is_expired():
                return self._tokens[key].value

            # Refresh token
            client = self.get_client(app_id)
            new_token = client.get_tenant_access_token()
            self._tokens[key] = Token(value=new_token, expires_at=...)

            # Persist to database
            self._save_to_db(app_id, token_type, new_token)

            return new_token
```

### 异常处理模式

**SDK 异常类型**:
- `lark.ApiException`: API 调用失败(网络、超时)
- `lark.BusinessException`: 业务错误(权限不足、参数错误)

**映射到内部异常**:
```python
class ErrorMapper:
    @staticmethod
    def map_sdk_exception(e: Exception) -> LarkServiceException:
        if isinstance(e, lark.ApiException):
            if "timeout" in str(e):
                return RetryableError("Network timeout", original=e)
            return RetryableError("API call failed", original=e)

        if isinstance(e, lark.BusinessException):
            error_code = e.code
            if error_code == 99991663:  # Token invalid
                return TokenExpiredError("Token expired", original=e)
            if error_code == 99991664:  # Rate limited
                return RateLimitedError("API rate limited", original=e)
            return NonRetryableError(f"Business error: {e.msg}", original=e)

        return UnknownError("Unexpected error", original=e)
```

---

## 6. 数据库 Schema 设计

### tokens 表

```sql
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(64) NOT NULL,
    token_type VARCHAR(32) NOT NULL,
    token_value TEXT NOT NULL,  -- Encrypted using pg_crypto
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(app_id, token_type)
);

-- Index for fast lookup
CREATE INDEX idx_tokens_app_token ON tokens(app_id, token_type);

-- Index for expired token cleanup
CREATE INDEX idx_tokens_expires ON tokens(expires_at);
```

### auth_sessions 表

```sql
CREATE TABLE auth_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    app_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64),
    auth_method VARCHAR(16) NOT NULL,  -- 'link' or 'card'
    state VARCHAR(16) NOT NULL DEFAULT 'pending',  -- 'pending', 'completed', 'expired'
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for cleanup expired sessions
CREATE INDEX idx_auth_sessions_expires ON auth_sessions(expires_at);
CREATE INDEX idx_auth_sessions_app_user ON auth_sessions(app_id, user_id);
```

### 加密实现

```sql
-- Enable pg_crypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt token before insert
INSERT INTO tokens (app_id, token_type, token_value, expires_at)
VALUES (
    'app_123',
    'tenant_access_token',
    pgp_sym_encrypt('actual_token_value', 'encryption_key'),
    NOW() + INTERVAL '2 hours'
);

-- Decrypt token on read
SELECT
    app_id,
    token_type,
    pgp_sym_decrypt(token_value::bytea, 'encryption_key') AS token_value,
    expires_at
FROM tokens
WHERE app_id = 'app_123' AND token_type = 'tenant_access_token';
```

**加密密钥管理**:
- 密钥存储在环境变量 `LARK_TOKEN_ENCRYPTION_KEY`
- 密钥轮换: 支持新旧密钥共存,逐步迁移

---

## 7. Docker 容器化部署方案

### docker-compose.yml

```yaml
version: '3.8'

services:
  lark-service:
    build: .
    container_name: lark-service
    environment:
      - LARK_APP_ID=${LARK_APP_ID}
      - LARK_APP_SECRET=${LARK_APP_SECRET}
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=lark_service
      - POSTGRES_USER=lark
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - RABBITMQ_HOST=rabbitmq
      - RABBITMQ_PORT=5672
      - LARK_TOKEN_ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - postgres
      - rabbitmq
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    container_name: lark-postgres
    environment:
      - POSTGRES_DB=lark_service
      - POSTGRES_USER=lark
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: lark-rabbitmq
    environment:
      - RABBITMQ_DEFAULT_USER=lark
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - "5672:5672"      # AMQP
      - "15672:15672"    # Management UI
    restart: unless-stopped

volumes:
  postgres_data:
  rabbitmq_data:
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# 注意: 生产环境可以使用 uv 加速安装 (10-100x 速度提升)
# RUN pip install uv && uv pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY migrations/ ./migrations/

# Create non-root user
RUN useradd -m -u 1000 lark && chown -R lark:lark /app
USER lark

# Health check endpoint
EXPOSE 8000

# Run migrations and start service
CMD ["sh", "-c", "alembic upgrade head && python -m src.lark_service"]
```

### 环境变量最佳实践

**.env.example**:
```bash
# Lark Application Credentials
LARK_APP_ID=cli_xxxxx
LARK_APP_SECRET=xxxxx

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=changeme

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=changeme

# Encryption
LARK_TOKEN_ENCRYPTION_KEY=change-this-to-a-random-32-byte-key

# Logging
LOG_LEVEL=INFO
```

**安全注意事项**:
1. .env 文件必须在 .gitignore 中
2. 生产环境使用 Docker secrets 或 Kubernetes secrets
3. 密钥使用强随机生成(如 `openssl rand -base64 32`)

---

## 6. Contact 模块用户缓存策略

### 6.1 缓存需求分析

**查询场景**:
- 根据邮箱/手机号查询用户 → 获取 open_id、user_id、union_id
- 高频查询(发送消息前需要获取用户ID)
- 用户信息变更频率低(姓名、部门变更通常以月/季度为周期)

**缓存目标**:
- 减少飞书 API 调用次数
- 提升查询响应速度
- 降低 API 限流风险

### 6.2 缓存方案设计

| 维度 | 选择 | 理由 |
|------|------|------|
| **存储位置** | PostgreSQL | 与 Token 共用数据库,减少依赖;支持 app_id 隔离 |
| **TTL** | 24 小时 | 平衡缓存命中率与数据新鲜度 |
| **刷新策略** | 懒加载刷新 | 缓存过期或未命中时自动从飞书拉取 |
| **隔离方式** | 按 app_id 隔离 | 不同应用的 open_id 不同,必须隔离存储 |

### 6.3 数据库表结构

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
    department_ids TEXT[],  -- 部门ID数组
    employee_no VARCHAR(64),
    cached_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(app_id, email),
    UNIQUE(app_id, mobile),
    UNIQUE(app_id, open_id)
);

CREATE INDEX idx_user_cache_expires ON user_cache(expires_at);
CREATE INDEX idx_user_cache_union_id ON user_cache(union_id);
```

### 6.4 缓存查询逻辑

```python
def get_user_by_email(app_id: str, email: str) -> User:
    # 1. 查询本地缓存
    cached = db.query(UserCache).filter(
        UserCache.app_id == app_id,
        UserCache.email == email,
        UserCache.expires_at > datetime.now()
    ).first()

    if cached:
        return User.from_cache(cached)  # 缓存命中

    # 2. 缓存未命中或过期,调用飞书 API
    lark_user = lark_api.get_user_by_email(email)

    # 3. 更新缓存
    db.merge(UserCache(
        app_id=app_id,
        email=email,
        open_id=lark_user.open_id,
        user_id=lark_user.user_id,
        union_id=lark_user.union_id,
        cached_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=24)
    ))

    return lark_user
```

### 6.5 缓存性能优化

| 优化策略 | 实施方式 |
|---------|---------|
| **批量刷新** | 查询部门成员时,批量更新缓存(减少单次查询) |
| **后台清理** | 定时任务清理过期缓存(避免表膨胀) |
| **索引优化** | expires_at 索引(加速过期查询),union_id 索引(跨应用关联) |

### 6.6 边缘案例处理

| 场景 | 处理策略 |
|------|---------|
| **用户信息变更** | TTL 到期后自动刷新,获取最新数据 |
| **用户离职/删除** | 飞书 API 返回 404 → 删除缓存,返回明确错误 |
| **不同 app 相同 user** | 按 app_id 隔离,open_id 不同但 union_id 相同 |
| **权限不足** | 直接返回权限错误,不缓存错误状态 |

---

## 7. aPaaS 模块技术调研

### 7.1 飞书 aPaaS 数据空间概述

**官方文档**: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list

**核心概念**:
- **Workspace (工作空间)**: 数据空间的顶层容器
- **Table (数据表)**: 类似数据库表,包含字段定义和记录
- **Record (记录)**: 表中的一行数据
- **Field (字段)**: 列定义,支持文本、数字、日期、选择等类型

### 7.2 权限模型

| Token 类型 | 可访问资源 | 适用场景 |
|-----------|-----------|---------|
| **app_access_token** | ❌ 无权限 | 不适用于 aPaaS |
| **tenant_access_token** | ❌ 无权限 | 不适用于 aPaaS |
| **user_access_token** | ✅ 用户有权限的数据空间 | **aPaaS 唯一可用 Token** |

**关键约束**:
- 所有 aPaaS 操作均需要 user_access_token
- 需要用户首次认证(飞书卡片或消息链接)
- 权限范围由用户在飞书侧的数据空间权限决定

### 7.3 CRUD 操作 API 映射

| 操作 | 飞书 API 端点 | 说明 |
|------|--------------|------|
| **查询表列表** | `GET /apaas/v1/workspaces/{workspace_id}/tables` | 获取工作空间下所有表及字段定义 |
| **查询记录** | `POST /apaas/v1/tables/{table_id}/records/search` | 支持过滤、排序、分页 |
| **更新记录** | `PUT /apaas/v1/tables/{table_id}/records/{record_id}` | 部分字段更新,支持版本控制 |
| **删除记录** | `DELETE /apaas/v1/tables/{table_id}/records/{record_id}` | 物理删除 |

### 7.4 并发控制方案

**问题**: 多个用户/进程同时更新同一记录 → 数据覆盖

**飞书 API 支持**: 记录包含 `version` 字段

**实施方案**:
```python
def update_record(table_id: str, record_id: str, fields: dict, version: int):
    # 1. 读取当前记录版本
    current = lark_api.get_record(table_id, record_id)

    # 2. 版本检查
    if current.version != version:
        raise VersionConflictError(
            f"并发写冲突,当前版本 {current.version},提供版本 {version}"
        )

    # 3. 更新(飞书侧会自动递增版本号)
    updated = lark_api.update_record(table_id, record_id, fields)
    return updated
```

### 7.5 AI 能力调用

**超时控制**:
- AI 调用耗时不可预测(几秒到几十秒)
- 默认超时: 30 秒
- 超时后主动返回错误,避免长时间阻塞

**实施方案**:
```python
import asyncio

async def invoke_ai_capability(capability_id: str, input_params: dict, timeout: int = 30):
    try:
        result = await asyncio.wait_for(
            lark_api.invoke_ai(capability_id, input_params),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        raise AITimeoutError(f"AI 调用超过 {timeout} 秒未返回")
```

### 7.6 边缘案例处理

| 场景 | 处理策略 |
|------|---------|
| **工作空间不存在** | 返回明确错误 + 可用工作空间列表建议 |
| **权限不足** | 返回权限错误 + 所需权限说明 (apaas:workspace:read) |
| **并发写冲突** | 返回冲突错误 + 当前版本号,建议重新读取后再更新 |
| **配额已满** | 返回配额超限错误 + 清理建议 |
| **AI 调用超时** | 主动超时返回,记录 WARNING 日志 |

### 7.7 技术风险

| 风险 | 缓解措施 |
|------|---------|
| **user_access_token 过期** | 监控过期事件,提示用户重新认证 |
| **数据空间权限变更** | 每次调用验证权限,返回明确错误 |
| **API 限流** | 指数退避重试,记录限流日志 |

---

## 总结

### 关键技术决策

| 决策点 | 选择方案 | 理由 |
|--------|---------|------|
| **应用配置存储** | SQLite | 轻量级配置管理 + 文件级加密 + 无需额外服务 |
| **Token 数据存储** | PostgreSQL | 并发性能 + 原生加密 + 生产级可靠性 |
| **用户信息缓存** | PostgreSQL | 与 Token 共用数据库 + 24h TTL + app_id 隔离 |
| **回调队列** | RabbitMQ | 消息持久化 + ACK 机制 + 死信队列 |
| **并发锁** | filelock (线程锁+进程锁) | 支持多进程部署 + 超时机制 |
| **用户认证** | 消息链接优先,卡片可选 | 标准 OAuth 流程 + 灵活性 |
| **SDK 封装** | 每个 app_id 独立 LarkClient | 多应用隔离 + 配置清晰 |
| **aPaaS 权限** | user_access_token (必需) | 飞书 aPaaS API 权限要求 |
| **AI 超时控制** | asyncio.wait_for (30秒) | 避免长时间阻塞 + 明确超时错误 |

### 技术风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| PostgreSQL 单点故障 | 主从复制 + 故障自动切换 |
| RabbitMQ 消息堆积 | 设置队列长度限制 + 死信队列 |
| 文件锁性能瓶颈 | 锁粒度细化到 (app_id, token_type) |
| 认证会话过期未清理 | 定时任务清理 + 数据库索引优化 |

### 待办事项

- [ ] 编写 PostgreSQL 迁移脚本(Alembic)
- [ ] 实现 Token 加密/解密工具类
- [ ] 配置 RabbitMQ 死信队列和消息 TTL
- [ ] 编写 Docker健康检查脚本
- [ ] 准备单元测试和集成测试环境

---

## 8. 服务集成方式技术调研

### 8.1 集成方式概述

本服务设计为**可复用的 Lark API 封装组件**,支持多种集成方式以适应不同的项目需求和开发场景。

#### 设计目标

| 目标 | 说明 |
|------|------|
| **灵活性** | 支持 PyPI 包安装和子项目集成两种方式 |
| **可调试性** | 子项目方式便于实时调试和定制 |
| **标准化** | PyPI 方式符合 Python 生态最佳实践 |
| **主推方案** | 以 Git Submodule 子项目集成为主,PyPI 安装为辅 |

---

### 8.2 方式对比:子项目集成 vs PyPI 安装

#### 对比表

| 维度 | 子项目集成 (Git Submodule) ⭐ 推荐 | PyPI 包安装 |
|------|----------------------------------|-------------|
| **安装方式** | `git submodule add <repo> libs/lark-service` | `uv pip install lark-service` |
| **代码可见性** | ✅ 源码完全可见,可直接查看和修改 | ❌ 安装在 site-packages,不易查看 |
| **实时调试** | ✅ 修改即生效,无需重新安装 | ❌ 需要 `pip install -e .` 或重新安装 |
| **版本控制** | ✅ Git 子模块锁定特定 commit | ✅ requirements.txt 锁定版本号 |
| **更新方式** | `git submodule update --remote` | `uv pip install --upgrade lark-service` |
| **依赖管理** | ⚠️ 需要手动安装子项目依赖 | ✅ 自动安装所有依赖 |
| **隔离性** | ⚠️ 代码在项目内,可能产生耦合 | ✅ 完全隔离在虚拟环境 |
| **定制能力** | ✅ 可以自由修改和扩展 | ❌ 修改需要 fork 或 patch |
| **团队协作** | ⚠️ 需要团队成员初始化子模块 | ✅ requirements.txt 一键安装 |
| **CI/CD** | ⚠️ 需要配置子模块拉取 | ✅ 标准 pip 安装流程 |
| **适用场景** | 开发调试、深度定制、单体应用 | 生产部署、多项目复用、快速集成 |

#### 推荐策略

```
开发阶段 (主推) ──→ Git Submodule 子项目集成
                   ├─ 实时调试
                   ├─ 快速迭代
                   └─ 深度定制

生产部署 (备选) ──→ PyPI 包安装
                   ├─ 稳定版本
                   ├─ 快速部署
                   └─ 标准化管理
```

---

### 8.3 子项目集成技术方案 (主推方案) ⭐

#### 8.3.1 Git Submodule 集成

**项目结构**:

```
your-project/
├── libs/
│   └── lark-service/              # Git 子模块
│       ├── src/
│       │   └── lark_service/
│       │       ├── __init__.py
│       │       ├── core/
│       │       ├── modules/
│       │       └── ...
│       ├── migrations/            # Alembic 迁移脚本
│       ├── requirements.txt
│       ├── pyproject.toml
│       └── README.md
├── your_app/
│   ├── __init__.py
│   ├── main.py
│   └── config.py
├── .gitmodules                    # 子模块配置
├── requirements.txt               # 主项目依赖
└── pyproject.toml
```

**集成步骤**:

```bash
# 1. 添加子模块
cd your-project
git submodule add https://github.com/your-org/lark-service.git libs/lark-service

# 2. 初始化子模块 (团队成员克隆项目后执行)
git submodule update --init --recursive

# 3. 安装子项目依赖
cd libs/lark-service
uv pip install -r requirements.txt

# 4. 配置 Python 路径 (可选,或在代码中动态添加)
export PYTHONPATH="${PYTHONPATH}:$(pwd)/libs/lark-service/src"
```

**代码使用**:

```python
# your_app/main.py
import sys
from pathlib import Path

# 方式 1: 动态添加路径 (推荐)
project_root = Path(__file__).parent.parent
lark_service_path = project_root / "libs" / "lark-service" / "src"
sys.path.insert(0, str(lark_service_path))

# 方式 2: 使用 PYTHONPATH 环境变量 (见上面步骤 4)

from lark_service import LarkServiceClient
from lark_service.modules.messaging import MessagingModule

# 正常使用
client = LarkServiceClient()
messaging = MessagingModule(client)
messaging.send_text_message(chat_id="oc_xxx", text="Hello")
```

**依赖管理**:

```toml
# your-project/pyproject.toml
[project]
name = "your-project"
dependencies = [
    # 包含 lark-service 的依赖
    "lark-oapi>=1.2.0",
    "pydantic>=2.0.0,<3.0.0",
    "SQLAlchemy>=2.0.0,<3.0.0",
    "psycopg2-binary>=2.9.0",
    "pika>=1.3.0",
    "cryptography>=41.0.0",
    "python-dotenv>=1.0.0",
    "filelock>=3.12.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "alembic>=1.12.0",
    # 你的项目依赖
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
]
```

**版本更新**:

```bash
# 更新子模块到最新版本
cd your-project
git submodule update --remote libs/lark-service

# 锁定到特定版本
cd libs/lark-service
git checkout v1.2.0
cd ../..
git add libs/lark-service
git commit -m "chore: 锁定 lark-service 到 v1.2.0"
```

**优势**:

1. **实时调试**: 修改 `libs/lark-service` 代码立即生效
2. **版本控制**: Git 子模块锁定特定 commit,确保团队一致
3. **源码可见**: 便于学习、调试和定制
4. **独立更新**: 可以选择性更新子模块版本

**注意事项**:

1. **依赖冲突**: 确保 lark-service 的依赖版本与主项目兼容
2. **数据库迁移**: 需要手动运行 Alembic 迁移
   ```bash
   cd libs/lark-service
   alembic upgrade head
   ```
3. **配置文件**: 子项目的 `.env` 和 SQLite 数据库路径需要配置
   ```python
   # your_app/config.py
   from pathlib import Path

   LARK_SERVICE_ROOT = Path(__file__).parent.parent / "libs" / "lark-service"
   LARK_CONFIG_DB = LARK_SERVICE_ROOT / "data" / "lark_config.db"
   ```

---

#### 8.3.2 直接复制代码 (不推荐)

**适用场景**: 深度定制且不需要跟随上游更新

**项目结构**:

```
your-project/
├── your_app/
│   ├── lark_service/              # 直接复制
│   │   ├── __init__.py
│   │   ├── core/
│   │   ├── modules/
│   │   └── ...
│   ├── main.py
│   └── config.py
└── requirements.txt
```

**优点**:
- ✅ 完全自主,可以任意修改
- ✅ 无外部依赖,不需要 Git 子模块

**缺点**:
- ❌ 更新困难,需要手动同步上游代码
- ❌ 版本混乱,难以追踪变更
- ❌ 多项目复制导致代码冗余

**建议**: 仅在以下情况使用
- 需要大量修改核心逻辑
- 不需要跟随上游更新
- 作为项目的永久组成部分

---

### 8.4 PyPI 包安装方案 (备选方案)

#### 8.4.1 标准安装

```bash
# 使用 uv (推荐,速度快 10-100x)
uv pip install lark-service

# 或使用 pip
pip install lark-service

# 安装特定版本
uv pip install lark-service==1.2.0

# 安装开发版本
uv pip install lark-service[dev]
```

#### 8.4.2 依赖管理

```toml
# pyproject.toml
[project]
dependencies = [
    "lark-service>=1.0.0,<2.0.0",
]

# 或 requirements.txt
lark-service>=1.0.0,<2.0.0
```

#### 8.4.3 代码使用

```python
# 直接导入,无需配置路径
from lark_service import LarkServiceClient
from lark_service.modules.messaging import MessagingModule

client = LarkServiceClient()
messaging = MessagingModule(client)
```

#### 8.4.4 优势

1. **标准化**: 符合 Python 生态最佳实践
2. **依赖自动**: pip 自动安装所有依赖
3. **隔离性好**: 安装在虚拟环境,不污染项目
4. **更新简单**: `uv pip install --upgrade lark-service`

#### 8.4.5 适用场景

- 生产环境部署
- 多个项目复用同一版本
- 快速集成,不需要定制
- 团队协作,标准化管理

---

### 8.5 集成方式选择决策树

```
是否需要频繁调试或修改 lark-service 代码?
├─ 是 ──→ 使用 Git Submodule 子项目集成 ⭐
│         ├─ 开发阶段
│         ├─ 深度定制
│         └─ 单体应用
│
└─ 否 ──→ 是否需要多项目复用?
          ├─ 是 ──→ 使用 PyPI 包安装
          │         ├─ 生产环境
          │         ├─ 微服务架构
          │         └─ 快速集成
          │
          └─ 否 ──→ 是否需要完全自主控制?
                    ├─ 是 ──→ 直接复制代码 (不推荐)
                    └─ 否 ──→ 使用 Git Submodule ⭐
```

---

### 8.6 CI/CD 配置

#### 8.6.1 子项目集成的 CI/CD

**GitHub Actions 示例**:

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code with submodules
        uses: actions/checkout@v4
        with:
          submodules: recursive  # 关键: 拉取子模块

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: |
          uv pip install -r requirements.txt
          cd libs/lark-service
          uv pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/
```

**GitLab CI 示例**:

```yaml
# .gitlab-ci.yml
variables:
  GIT_SUBMODULE_STRATEGY: recursive  # 关键: 拉取子模块

test:
  image: python:3.12-slim
  before_script:
    - pip install uv
    - uv pip install -r requirements.txt
    - cd libs/lark-service && uv pip install -r requirements.txt && cd ../..
  script:
    - pytest tests/
```

#### 8.6.2 PyPI 安装的 CI/CD

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt  # 包含 lark-service

      - name: Run tests
        run: pytest tests/
```

---

### 8.7 Docker 部署配置

#### 8.7.1 子项目集成的 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件 (包含子模块)
COPY . .

# 安装 Python 依赖
RUN pip install uv && \
    uv pip install -r requirements.txt && \
    cd libs/lark-service && \
    uv pip install -r requirements.txt

# 运行数据库迁移
RUN cd libs/lark-service && alembic upgrade head

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "your_app.main"]
```

**构建时拉取子模块**:

```bash
# 方式 1: 构建前更新子模块
git submodule update --init --recursive
docker build -t your-app .

# 方式 2: 使用 BuildKit 的 Git 支持
docker buildx build --ssh default -t your-app .
```

#### 8.7.2 PyPI 安装的 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖 (包含 lark-service)
RUN pip install uv && \
    uv pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "your_app.main"]
```

---

### 8.8 最佳实践建议

#### 8.8.1 开发阶段 (推荐 Git Submodule)

**工作流程**:

```bash
# 1. 克隆项目
git clone https://github.com/your-org/your-project.git
cd your-project

# 2. 初始化子模块
git submodule update --init --recursive

# 3. 创建 Conda 环境
conda create -n your-project python=3.12
conda activate your-project

# 4. 安装依赖
pip install uv
uv pip install -r requirements.txt
cd libs/lark-service
uv pip install -r requirements.txt
cd ../..

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 6. 启动依赖服务
docker compose up -d postgres rabbitmq

# 7. 运行数据库迁移
cd libs/lark-service
alembic upgrade head
cd ../..

# 8. 开发调试
python -m your_app.main
```

**调试 lark-service 代码**:

```python
# 直接修改 libs/lark-service/src/lark_service/xxx.py
# 修改后立即生效,无需重新安装
```

#### 8.8.2 生产部署 (可选 PyPI)

**如果发布了稳定版本到 PyPI**:

```bash
# 1. 使用 requirements.txt 锁定版本
lark-service==1.2.0

# 2. 部署时直接安装
uv pip install -r requirements.txt

# 3. 无需管理子模块
```

#### 8.8.3 版本管理策略

**子项目方式**:

```bash
# 开发分支使用最新代码
git submodule update --remote libs/lark-service

# 发布分支锁定特定版本
cd libs/lark-service
git checkout v1.2.0
cd ../..
git add libs/lark-service
git commit -m "chore: 锁定 lark-service 到 v1.2.0"
```

**PyPI 方式**:

```toml
# 开发环境使用最新版本
lark-service>=1.0.0

# 生产环境锁定版本
lark-service==1.2.0
```

---

### 8.9 常见问题与解决方案

#### Q1: 子模块更新后代码不生效?

**原因**: Python 缓存了旧的 `.pyc` 文件

**解决**:
```bash
# 清理 Python 缓存
find libs/lark-service -type d -name __pycache__ -exec rm -rf {} +
find libs/lark-service -type f -name "*.pyc" -delete

# 重启应用
python -m your_app.main
```

#### Q2: 依赖版本冲突?

**原因**: lark-service 的依赖与主项目冲突

**解决**:
```toml
# 在主项目 pyproject.toml 中统一管理版本
[project]
dependencies = [
    "pydantic>=2.0.0,<3.0.0",  # 统一版本范围
    "SQLAlchemy>=2.0.0,<3.0.0",
]
```

#### Q3: 团队成员忘记初始化子模块?

**解决**: 添加初始化脚本

```bash
# scripts/setup.sh
#!/bin/bash
set -e

echo "初始化 Git 子模块..."
git submodule update --init --recursive

echo "安装依赖..."
pip install uv
uv pip install -r requirements.txt
cd libs/lark-service
uv pip install -r requirements.txt
cd ../..

echo "✅ 环境设置完成!"
```

#### Q4: CI/CD 构建失败?

**原因**: 未配置子模块拉取

**解决**: 见 8.6 节 CI/CD 配置

---

### 8.10 技术决策总结

| 决策项 | 选择 | 理由 |
|--------|------|------|
| **主推集成方式** | Git Submodule 子项目集成 | 便于开发调试、深度定制、实时迭代 |
| **备选方式** | PyPI 包安装 | 生产环境标准化部署 |
| **版本控制** | Git 子模块锁定 commit | 确保团队环境一致 |
| **依赖管理** | 主项目统一管理 | 避免版本冲突 |
| **数据库迁移** | 手动运行 Alembic | 子项目方式需要显式执行 |
| **CI/CD 策略** | 配置子模块递归拉取 | 确保构建成功 |

---

**Phase 0 完成,可进入 Phase 1 详细设计。**
