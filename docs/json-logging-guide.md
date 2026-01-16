# JSON日志配置指南

## 概述

Lark Service支持结构化JSON日志格式,便于日志聚合、分析和监控。

## 启用JSON日志

### 方法1: 代码配置

```python
from lark_service.utils import setup_logger

# 启用JSON格式日志
logger = setup_logger(
    name="lark_service",
    level="INFO",
    json_format=True,  # 启用JSON格式
    log_file="logs/app.json"  # 可选:输出到文件
)
```

### 方法2: 环境变量配置

```bash
# .env文件
LOG_FORMAT=json
LOG_LEVEL=INFO
LOG_FILE=logs/app.json
```

```python
import os
from lark_service.utils import setup_logger

logger = setup_logger(
    name="lark_service",
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_format=os.getenv("LOG_FORMAT") == "json",
    log_file=os.getenv("LOG_FILE")
)
```

## JSON日志格式

### 标准字段

```json
{
  "timestamp": "2026-01-17T05:48:00.123Z",
  "level": "INFO",
  "logger": "lark_service",
  "message": "User query completed",
  "module": "contact.client",
  "function": "get_user_by_email",
  "line": 145
}
```

### 上下文字段

使用`set_request_context()`添加请求级别的上下文:

```python
from lark_service.utils import set_request_context, clear_request_context

# 设置请求上下文
set_request_context(
    request_id="req-123",
    app_id="cli_xxx",
    user_id="ou_xxx"
)

# 日志会自动包含上下文
logger.info("Processing request")
# 输出:
# {
#   "timestamp": "2026-01-17T05:48:00.123Z",
#   "level": "INFO",
#   "message": "Processing request",
#   "request_id": "req-123",
#   "app_id": "cli_xxx",
#   "user_id": "ou_xxx"
# }

# 清除上下文
clear_request_context()
```

### 额外字段

使用`extra`参数添加自定义字段:

```python
logger.info(
    "User query completed",
    extra={
        "email": "user@example.com",
        "query_time_ms": 45,
        "cache_hit": True
    }
)
# 输出:
# {
#   "timestamp": "2026-01-17T05:48:00.123Z",
#   "level": "INFO",
#   "message": "User query completed",
#   "email": "user@example.com",
#   "query_time_ms": 45,
#   "cache_hit": true
# }
```

## 敏感信息脱敏

结合masking模块自动脱敏敏感信息:

```python
from lark_service.utils import masking

# 脱敏email
email = "john.doe@example.com"
logger.info(
    "User logged in",
    extra={"email": masking.mask_email(email)}  # jo***@ex***.com
)

# 脱敏手机号
mobile = "+8615680013621"
logger.info(
    "SMS sent",
    extra={"mobile": masking.mask_mobile(mobile)}  # +86****3621
)

# 脱敏token
token = "t-abc123def456ghi789"
logger.info(
    "API call",
    extra={"token": masking.mask_token(token)}  # t-ab***i789
)

# 批量脱敏字典
user_data = {
    "email": "john@example.com",
    "mobile": "+8615680013621",
    "name": "John"
}
logger.info(
    "User data",
    extra=masking.mask_dict(user_data)
)
```

## 日志聚合集成

### ELK Stack

```yaml
# logstash配置
input {
  file {
    path => "/var/log/lark-service/*.json"
    codec => "json"
  }
}

filter {
  # JSON已经解析,直接使用
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "lark-service-%{+YYYY.MM.dd}"
  }
}
```

### Grafana Loki

```yaml
# promtail配置
scrape_configs:
  - job_name: lark-service
    static_configs:
      - targets:
          - localhost
        labels:
          job: lark-service
          __path__: /var/log/lark-service/*.json
    pipeline_stages:
      - json:
          expressions:
            level: level
            timestamp: timestamp
            message: message
```

## 性能考虑

### JSON vs 文本日志

- **JSON格式**:
  - 优点: 结构化,易于解析和查询
  - 缺点: 文件大小增加约30%

- **文本格式**:
  - 优点: 人类可读,文件较小
  - 缺点: 解析复杂

### 建议

- **开发环境**: 使用文本格式 (`json_format=False`)
- **生产环境**: 使用JSON格式 (`json_format=True`)
- **高性能场景**: 考虑异步日志写入

## 示例配置

### 完整示例

```python
import os
from pathlib import Path
from lark_service.utils import setup_logger, set_request_context
from lark_service.utils import masking

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置日志
logger = setup_logger(
    name="lark_service",
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_format=os.getenv("LOG_FORMAT") == "json",
    log_file=log_dir / "app.json" if os.getenv("LOG_FORMAT") == "json" else None
)

# 使用日志
def process_user_request(request_id: str, app_id: str, email: str):
    # 设置请求上下文
    set_request_context(request_id=request_id, app_id=app_id)

    try:
        logger.info(
            "Processing user request",
            extra={
                "email": masking.mask_email(email),
                "action": "get_user"
            }
        )

        # 业务逻辑...

        logger.info("Request completed successfully")

    except Exception as e:
        logger.error(
            "Request failed",
            extra={"error": str(e)},
            exc_info=True
        )
    finally:
        # 清除上下文
        from lark_service.utils import clear_request_context
        clear_request_context()
```

## 最佳实践

1. **始终脱敏敏感信息**: 使用masking模块脱敏email、手机号、token
2. **使用请求上下文**: 为每个请求设置request_id,便于追踪
3. **结构化extra字段**: 使用有意义的字段名,避免嵌套过深
4. **适当的日志级别**:
   - DEBUG: 详细调试信息
   - INFO: 关键业务事件
   - WARNING: 警告但不影响功能
   - ERROR: 错误需要关注
5. **日志轮转**: 配置日志文件轮转,避免文件过大

## 故障排查

### 日志未输出

检查日志级别配置:

```python
logger.setLevel("DEBUG")  # 临时调整为DEBUG
```

### JSON格式错误

确保extra字段可JSON序列化:

```python
# ❌ 错误: datetime对象不可序列化
logger.info("Event", extra={"time": datetime.now()})

# ✅ 正确: 转换为字符串
logger.info("Event", extra={"time": datetime.now().isoformat()})
```

### 性能问题

考虑异步日志:

```python
import logging.handlers

handler = logging.handlers.QueueHandler(queue)
logger.addHandler(handler)
```

---

**更新时间**: 2026-01-17
**维护者**: Lark Service Team
