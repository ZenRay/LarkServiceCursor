# 可观测性与监控指南

**版本**: 1.0.0
**更新时间**: 2026-01-15
**状态**: Production Ready

---

## 📊 可观测性目标

### 三大支柱

| 支柱 | 目的 | 实现方式 |
|------|------|---------|
| **日志 (Logging)** | 记录系统事件和错误 | 结构化日志 + 日志聚合 |
| **指标 (Metrics)** | 监控系统性能和健康 | Prometheus + Grafana |
| **追踪 (Tracing)** | 分析请求链路和延迟 | 分布式追踪 (可选) |

---

## 📝 日志规范 (CHK088, CHK089)

### 日志格式标准

**结构化日志格式 (JSON)**:
```json
{
  "timestamp": "2026-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "lark_service.core.credential_pool",
  "message": "Token acquired successfully",
  "request_id": "req_abc123",
  "app_id": "cli_12345678",
  "token_type": "app_access_token",
  "duration_ms": 150
}
```

**必需字段**:
- `timestamp`: ISO 8601 格式
- `level`: DEBUG/INFO/WARNING/ERROR/CRITICAL
- `logger`: 模块路径
- `message`: 人类可读的消息

**可选字段** (根据场景):
- `request_id`: 请求追踪ID
- `app_id`: 应用ID
- `user_id`: 用户ID
- `duration_ms`: 操作耗时
- `error`: 错误详情
- `stack_trace`: 堆栈信息

### 构建日志规范 (CHK088)

**Docker 构建日志格式**:
```bash
# 启用 BuildKit 的详细日志
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# 构建时输出详细日志
docker build --progress=plain --no-cache -t lark-service:latest . 2>&1 | tee build.log
```

**日志内容要求**:
```
[build 1/10] FROM docker.io/library/python:3.12-slim
[build 2/10] RUN apt-get update && apt-get install -y ...
  ✅ Package installation: 45s
[build 3/10] WORKDIR /app
[build 4/10] COPY requirements.txt .
[build 5/10] RUN pip install --no-cache-dir -r requirements.txt
  ✅ Dependencies installed: 120s
[build 6/10] COPY . .
[build 7/10] RUN groupadd -r larkuser ...
  ✅ User created: larkuser (UID 1001)
[build 8/10] USER 1001
[build 9/10] EXPOSE 8000
[build 10/10] CMD ["python", "-m", "lark_service"]

✅ Build completed: 180s
📦 Image size: 485MB
```

**失败日志格式**:
```
[build 5/10] RUN pip install --no-cache-dir -r requirements.txt
❌ ERROR: Failed to install dependencies

   Error details:
   ERROR: Could not find a version that satisfies the requirement lark-oapi==1.2.15

   Stack trace:
   Traceback (most recent call last):
     File "/usr/local/lib/python3.12/site-packages/pip/_internal/...", line 123, in resolve
       ...

   Possible causes:
   1. Package version not found in PyPI
   2. Network connectivity issues
   3. Private package requires authentication

   Suggested actions:
   1. Check package name and version: pip search lark-oapi
   2. Verify network access to PyPI
   3. Update requirements.txt with valid version
```

### 配置加载日志 (CHK089)

**实现示例**:
```python
# src/lark_service/core/config.py
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration with comprehensive logging."""
        logger.info("Starting configuration load")

        # 加载 .env 文件
        env_file = Path(".env")
        if env_file.exists():
            logger.info(f"Loading .env file: {env_file.absolute()}")
            load_dotenv(env_file)
        else:
            logger.warning(f".env file not found: {env_file.absolute()}")

        # 加载必需配置
        encryption_key = os.getenv("LARK_CONFIG_ENCRYPTION_KEY")
        if not encryption_key:
            logger.error("LARK_CONFIG_ENCRYPTION_KEY not set")
            raise ConfigError("Missing required environment variable")
        else:
            logger.info("Encryption key loaded (length: 44 chars)")

        # 加载可选配置
        log_level = os.getenv("LOG_LEVEL", "INFO")
        logger.info(f"Log level: {log_level}")

        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        logger.info(f"PostgreSQL: {postgres_host}:{postgres_port}")

        config = cls(
            config_encryption_key=encryption_key,
            log_level=log_level,
            postgres_host=postgres_host,
            postgres_port=postgres_port,
            # ... 其他配置
        )

        logger.info("Configuration loaded successfully")
        logger.debug(f"Config: {config}")  # 仅 DEBUG 级别输出详情

        return config
```

**日志输出示例**:
```
2026-01-15 10:30:00 - lark_service.core.config - [INFO] - Starting configuration load
2026-01-15 10:30:00 - lark_service.core.config - [INFO] - Loading .env file: /app/.env
2026-01-15 10:30:00 - lark_service.core.config - [INFO] - Encryption key loaded (length: 44 chars)
2026-01-15 10:30:00 - lark_service.core.config - [INFO] - Log level: INFO
2026-01-15 10:30:00 - lark_service.core.config - [INFO] - PostgreSQL: localhost:5432
2026-01-15 10:30:00 - lark_service.core.config - [INFO] - Configuration loaded successfully
```

### 关键操作日志

**Token 管理日志**:
```python
# Token 获取
logger.info(
    "Token acquired",
    extra={
        "app_id": app_id,
        "token_type": token_type,
        "source": "cache" if cached else "api",
        "duration_ms": elapsed_ms,
    }
)

# Token 刷新
logger.info(
    "Token refreshed",
    extra={
        "app_id": app_id,
        "token_type": token_type,
        "reason": "expiring_soon",
        "old_expires_at": old_token.expires_at,
        "new_expires_at": new_token.expires_at,
    }
)

# Token 失效
logger.warning(
    "Token invalidated",
    extra={
        "app_id": app_id,
        "token_type": token_type,
        "reason": "api_error_invalid_token",
    }
)
```

**API 调用日志**:
```python
logger.info(
    "API request",
    extra={
        "request_id": request_id,
        "method": "POST",
        "endpoint": "/open-apis/im/v1/messages",
        "app_id": app_id,
        "params": {  # 脱敏后的参数
            "receive_id": "ou_****",
            "msg_type": "text",
        },
    }
)

logger.info(
    "API response",
    extra={
        "request_id": request_id,
        "status_code": 200,
        "duration_ms": 250,
        "success": True,
    }
)
```

---

## 📈 健康检查 (CHK030, CHK090)

### 健康检查响应时间阈值 (CHK030)

| 检查类型 | 响应时间阈值 | 超时行为 |
|---------|-------------|---------|
| **Liveness** | ≤ 1 秒 | 返回 503 Service Unavailable |
| **Readiness** | ≤ 2 秒 | 返回 503 Not Ready |
| **数据库连接** | ≤ 500ms | 标记为 unhealthy |
| **消息队列连接** | ≤ 500ms | 标记为 degraded |

### 健康检查端点实现

**基础健康检查**:
```python
# src/lark_service/health.py
from fastapi import FastAPI, Response
from datetime import datetime
import time

app = FastAPI()

@app.get("/health/live")
async def liveness():
    """Liveness probe - 应用是否活着.

    响应时间: ≤ 1 秒
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/ready")
async def readiness():
    """Readiness probe - 应用是否就绪.

    响应时间: ≤ 2 秒
    检查项:
    - 数据库连接
    - 消息队列连接
    - 配置加载
    """
    checks = {}
    overall_status = "ready"

    # 检查数据库
    start_time = time.time()
    try:
        db_engine.execute("SELECT 1")
        db_duration_ms = (time.time() - start_time) * 1000
        checks["database"] = {
            "status": "healthy",
            "duration_ms": round(db_duration_ms, 2),
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_status = "not_ready"

    # 检查消息队列
    start_time = time.time()
    try:
        # 简单连接测试
        connection = pika.BlockingConnection(...)
        connection.close()
        mq_duration_ms = (time.time() - start_time) * 1000
        checks["message_queue"] = {
            "status": "healthy",
            "duration_ms": round(mq_duration_ms, 2),
        }
    except Exception as e:
        checks["message_queue"] = {
            "status": "degraded",
            "error": str(e),
        }
        # MQ 失败不阻止服务 (降级运行)

    # 返回结果
    if overall_status != "ready":
        return Response(
            content=json.dumps({
                "status": overall_status,
                "checks": checks,
                "timestamp": datetime.now().isoformat(),
            }),
            status_code=503,
            media_type="application/json",
        )

    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }
```

### 监控指标 (CHK090)

**Prometheus 指标定义**:
```python
# src/lark_service/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info

# 应用信息
app_info = Info('lark_service_app', 'Application information')
app_info.info({
    'version': '0.1.0',
    'python_version': '3.12',
    'environment': 'production',
})

# 健康检查指标
health_check_total = Counter(
    'health_check_total',
    'Total health check requests',
    ['endpoint', 'status']
)

health_check_duration = Histogram(
    'health_check_duration_seconds',
    'Health check duration',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# 数据库健康状态
database_health = Gauge(
    'database_health_status',
    'Database health status (1=healthy, 0=unhealthy)'
)

# 消息队列健康状态
message_queue_health = Gauge(
    'message_queue_health_status',
    'Message queue health status (1=healthy, 0=degraded/unhealthy)'
)

# Token 池指标
token_pool_size = Gauge(
    'token_pool_size',
    'Number of tokens in pool',
    ['token_type']
)

token_refresh_total = Counter(
    'token_refresh_total',
    'Total token refresh operations',
    ['app_id', 'token_type', 'result']
)

# API 调用指标
api_request_total = Counter(
    'api_request_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
```

**使用示例**:
```python
import time
from metrics import (
    health_check_total,
    health_check_duration,
    database_health,
)

@app.get("/health/ready")
async def readiness():
    start_time = time.time()

    # ... 健康检查逻辑 ...

    # 记录指标
    duration = time.time() - start_time
    health_check_duration.labels(endpoint="readiness").observe(duration)
    health_check_total.labels(endpoint="readiness", status=overall_status).inc()

    # 更新数据库健康状态
    database_health.set(1 if db_healthy else 0)

    return response
```

### Kubernetes 健康检查配置

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lark-service
spec:
  template:
    spec:
      containers:
      - name: lark-service
        image: lark-service:latest
        ports:
        - containerPort: 8000

        # Liveness Probe (应用是否活着)
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 1
          failureThreshold: 3

        # Readiness Probe (应用是否就绪)
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 2
          successThreshold: 1
          failureThreshold: 3

        # Startup Probe (应用启动检查)
        startupProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 1
          failureThreshold: 30  # 最多等待 300秒
```

---

## 📊 Grafana 仪表盘

### 推荐仪表盘

**1. 系统健康仪表盘**:
- 服务可用性 (Uptime)
- 健康检查成功率
- 数据库连接状态
- 消息队列状态

**2. 性能仪表盘**:
- API 响应时间 (P50/P95/P99)
- API 吞吐量 (req/s)
- Token 刷新频率
- 数据库查询时间

**3. 错误仪表盘**:
- 错误率趋势
- 错误类型分布
- Top 10 错误
- 错误堆栈追踪

### 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: lark_service_health
    rules:
      # 服务不可用
      - alert: ServiceDown
        expr: up{job="lark-service"} == 0
        for: 1m
        annotations:
          summary: "Lark Service is down"

      # 数据库不健康
      - alert: DatabaseUnhealthy
        expr: database_health_status == 0
        for: 2m
        annotations:
          summary: "Database connection unhealthy"

      # 健康检查响应慢
      - alert: HealthCheckSlow
        expr: |
          histogram_quantile(0.95,
            health_check_duration_seconds_bucket{endpoint="readiness"}
          ) > 2
        for: 5m
        annotations:
          summary: "Health check P95 > 2s"
```

---

## ✅ 可观测性检查清单

### 日志检查

- [ ] 所有关键操作都有日志记录
- [ ] 日志包含 request_id 用于追踪
- [ ] 敏感信息已脱敏 (密钥/密码)
- [ ] 错误日志包含堆栈信息
- [ ] 日志级别配置正确

### 指标检查

- [ ] 定义了核心业务指标
- [ ] 定义了系统健康指标
- [ ] 指标有明确的 labels
- [ ] 指标暴露在 /metrics 端点
- [ ] 配置了 Prometheus 采集

### 健康检查

- [ ] Liveness 端点响应 ≤ 1秒
- [ ] Readiness 端点响应 ≤ 2秒
- [ ] 检查了数据库连接
- [ ] 检查了外部依赖
- [ ] 配置了 Kubernetes probes

### 告警检查

- [ ] 配置了服务不可用告警
- [ ] 配置了错误率告警
- [ ] 配置了性能告警
- [ ] 告警发送到正确的渠道
- [ ] 告警有明确的处理流程

---

**维护者**: Lark Service Team
**参考**: [observability-guide.md](./observability-guide.md)
