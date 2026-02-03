# 分布式追踪配置指南

## 📋 概述

本文档定义 Lark Service 的分布式追踪配置，使用 request_id 实现请求链路追踪。

## 🎯 追踪策略

### Request ID 规范

**生成规则**:
- 格式: `{prefix}-{timestamp}-{random}`
- 示例: `req-20260118-a7f3c2d1`
- 长度: 固定24字符
- 字符集: [a-z0-9-]

**传播机制**:
1. **HTTP Headers**: `X-Request-ID`
2. **日志上下文**: 通过 `ContextFilter` 自动注入
3. **异步任务**: 通过队列消息传递
4. **回调处理**: 从请求头提取

## 🔧 实现方案

### 1. Request ID 生成器

`src/lark_service/utils/tracing.py`:

```python
"""分布式追踪工具"""

import time
import random
import string
from typing import Optional

def generate_request_id(prefix: str = "req") -> str:
    """
    生成唯一的请求ID

    格式: {prefix}-{timestamp}-{random}
    示例: req-20260118-a7f3c2d1
    """
    timestamp = int(time.time() * 1000) % 100000000  # 8位时间戳
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}-{timestamp:08d}-{random_str}"

def validate_request_id(request_id: str) -> bool:
    """验证请求ID格式"""
    if not request_id:
        return False
    parts = request_id.split('-')
    if len(parts) != 3:
        return False
    if not parts[1].isdigit() or len(parts[1]) != 8:
        return False
    if len(parts[2]) != 8:
        return False
    return True

class TracingContext:
    """追踪上下文管理器"""

    _current_request_id: Optional[str] = None
    _current_app_id: Optional[str] = None

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        """设置当前请求ID"""
        cls._current_request_id = request_id

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """获取当前请求ID"""
        return cls._current_request_id

    @classmethod
    def set_app_id(cls, app_id: str) -> None:
        """设置当前应用ID"""
        cls._current_app_id = app_id

    @classmethod
    def get_app_id(cls) -> Optional[str]:
        """获取当前应用ID"""
        return cls._current_app_id

    @classmethod
    def clear(cls) -> None:
        """清除上下文"""
        cls._current_request_id = None
        cls._current_app_id = None
```

### 2. FastAPI 中间件

`src/lark_service/api/middleware.py`:

```python
"""API中间件"""

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from lark_service.utils.tracing import generate_request_id, validate_request_id, TracingContext
from lark_service.utils.logger import set_request_context, get_logger

logger = get_logger(__name__)

class TracingMiddleware(BaseHTTPMiddleware):
    """追踪中间件 - 处理 request_id 传播"""

    async def dispatch(self, request: Request, call_next):
        # 1. 从请求头获取或生成 request_id
        request_id = request.headers.get('X-Request-ID')
        if not request_id or not validate_request_id(request_id):
            request_id = generate_request_id()

        # 2. 设置追踪上下文
        TracingContext.set_request_id(request_id)

        # 3. 设置日志上下文
        set_request_context(request_id=request_id)

        # 4. 记录请求开始
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            }
        )

        # 5. 处理请求
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # 6. 添加响应头
        response.headers['X-Request-ID'] = request_id

        # 7. 记录请求完成
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )

        # 8. 清除上下文
        TracingContext.clear()

        return response
```

### 3. 异步任务追踪

`src/lark_service/messaging/tasks.py`:

```python
"""异步任务处理"""

from lark_service.utils.tracing import TracingContext, generate_request_id
from lark_service.utils.logger import set_request_context, get_logger

logger = get_logger(__name__)

def process_message_task(message_data: dict):
    """
    处理消息队列任务

    消息格式:
    {
        "request_id": "req-20260118-a7f3c2d1",  # 原始请求ID
        "app_id": "cli_xxx",
        "payload": {...}
    }
    """
    # 1. 从消息提取 request_id
    request_id = message_data.get('request_id')
    if not request_id:
        request_id = generate_request_id(prefix="task")

    # 2. 设置追踪上下文
    TracingContext.set_request_id(request_id)
    app_id = message_data.get('app_id')
    if app_id:
        TracingContext.set_app_id(app_id)

    # 3. 设置日志上下文
    set_request_context(request_id=request_id, app_id=app_id)

    try:
        # 4. 处理任务
        logger.info("Task started", extra={"task_type": "process_message"})

        # ... 任务处理逻辑 ...

        logger.info("Task completed successfully")

    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise
    finally:
        # 5. 清除上下文
        TracingContext.clear()
```

### 4. 飞书回调追踪

`src/lark_service/cardkit/callback_handler.py` (补充):

```python
# 在现有 handle_callback 方法中添加追踪

async def handle_callback(self, request: Request) -> dict:
    """处理卡片回调"""

    # 1. 从请求头提取原始 request_id
    request_id = request.headers.get('X-Request-ID') or request.headers.get('X-Lark-Request-Id')
    if not request_id:
        request_id = generate_request_id(prefix="callback")

    # 2. 设置追踪上下文
    TracingContext.set_request_id(request_id)
    set_request_context(request_id=request_id)

    logger.info(
        "Feishu callback received",
        extra={
            "request_id": request_id,
            "callback_type": "card_action",
        }
    )

    try:
        # ... 处理回调逻辑 ...

        return result
    finally:
        TracingContext.clear()
```

## 📊 追踪字段标准

### 日志必需字段

所有日志必须包含以下字段（通过 `ContextFilter` 自动注入）:

```json
{
  "timestamp": "2026-01-18T06:30:00+08:00",
  "level": "INFO",
  "logger": "lark_service.api.endpoints",
  "message": "Processing user request",
  "request_id": "req-20260118-a7f3c2d1",
  "app_id": "cli_a8d27f9bf635500e",
  "duration_ms": 123.45,
  "user_id": "ou_xxx" // 可选
}
```

### 跨服务传递

**HTTP调用**:
```python
import requests
from lark_service.utils.tracing import TracingContext

def call_external_api(url: str, data: dict):
    headers = {
        'X-Request-ID': TracingContext.get_request_id(),
        'X-App-ID': TracingContext.get_app_id(),
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()
```

**消息队列**:
```python
from lark_service.utils.tracing import TracingContext

def publish_message(channel, message_data: dict):
    # 注入追踪字段
    message_with_trace = {
        "request_id": TracingContext.get_request_id(),
        "app_id": TracingContext.get_app_id(),
        "payload": message_data,
    }
    channel.basic_publish(
        exchange='',
        routing_key='task_queue',
        body=json.dumps(message_with_trace)
    )
```

## 🔍 追踪查询

### Elasticsearch/Kibana 查询

```json
{
  "query": {
    "match": {
      "request_id": "req-20260118-a7f3c2d1"
    }
  },
  "sort": [
    { "timestamp": "asc" }
  ]
}
```

### Grafana Loki 查询

```logql
{job="lark-service"}
  |= "req-20260118-a7f3c2d1"
  | json
  | line_format "{{.timestamp}} [{{.level}}] {{.logger}} - {{.message}}"
```

### PostgreSQL 慢查询关联

```sql
-- 关联 request_id 查询慢查询日志
SELECT
  request_id,
  query,
  duration_ms,
  timestamp
FROM slow_query_log
WHERE request_id = 'req-20260118-a7f3c2d1'
ORDER BY timestamp;
```

## 📈 追踪指标

### Prometheus Metrics

```python
# 在 metrics.py 中定义
REQUEST_DURATION = Histogram(
    'lark_service_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)

REQUEST_COUNTER = Counter(
    'lark_service_requests_total',
    'Total request count',
    ['method', 'endpoint', 'status_code']
)

# 使用
@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    with REQUEST_DURATION.labels(
        method="GET",
        endpoint="/api/users/{user_id}",
        status_code=200
    ).time():
        # ... 处理逻辑 ...
        REQUEST_COUNTER.labels(
            method="GET",
            endpoint="/api/users/{user_id}",
            status_code=200
        ).inc()
```

## 🚀 最佳实践

### 1. 始终传播 request_id

✅ **正确**:
```python
logger.info("Processing request", extra={
    "request_id": TracingContext.get_request_id()
})
```

❌ **错误**:
```python
logger.info("Processing request")  # 缺少 request_id
```

### 2. 异步任务包含原始 request_id

✅ **正确**:
```python
task_data = {
    "request_id": TracingContext.get_request_id(),  # 传递原始ID
    "payload": data
}
queue.publish(task_data)
```

### 3. 错误日志包含完整上下文

✅ **正确**:
```python
try:
    process_data()
except Exception as e:
    logger.error(
        f"Processing failed: {e}",
        exc_info=True,  # 包含堆栈跟踪
        extra={
            "request_id": TracingContext.get_request_id(),
            "app_id": TracingContext.get_app_id(),
            "user_data": safe_mask_data(user_data)  # 脱敏
        }
    )
```

### 4. 性能追踪

```python
import time

def trace_operation(operation_name: str):
    """装饰器: 追踪操作耗时"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{operation_name} completed",
                    extra={"duration_ms": round(duration_ms, 2)}
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{operation_name} failed after {duration_ms:.2f}ms: {e}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator

@trace_operation("fetch_user_from_api")
def fetch_user(user_id: str):
    # ... API 调用 ...
    pass
```

## 🔗 相关文档

- [日志配置](../config/logging-production.yaml)
- [监控告警](../config/prometheus-alerts.yaml)
- [可观测性指南](./observability-guide.md)

---

**文档版本**: 1.0
**最后更新**: 2026-01-18
**负责人**: Backend Team
