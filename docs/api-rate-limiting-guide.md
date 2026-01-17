# API速率限制配置指南

本文档说明Lark Service的API速率限制功能，包括配置方法、限流策略和最佳实践。

---

## 📋 概述

API速率限制（Rate Limiting）用于：
- 🛡️ 防止API滥用和DDoS攻击
- ⚖️ 确保服务公平性，避免单一用户占用过多资源
- 💰 支持基于用量的分级计费
- 📈 提高系统稳定性和可预测性

---

## 🎯 限流策略

### 1. 固定窗口（Fixed Window）

**原理**: 在固定时间窗口内限制请求数。

**优点**:
- 实现简单
- 内存占用少

**缺点**:
- 边界突发问题（窗口切换时可能瞬间2倍请求）

**适用场景**: Token刷新等低频操作

### 2. 滑动窗口（Sliding Window）

**原理**: 基于请求时间戳的滑动时间窗口。

**优点**:
- 更平滑的限流
- 无边界突发问题

**缺点**:
- 内存占用稍高（需记录每个请求时间）

**适用场景**: API调用等中高频操作（推荐）

### 3. 令牌桶（Token Bucket）

**原理**: 按固定速率补充令牌，请求消耗令牌。

**优点**:
- 支持突发流量
- 更灵活的流量控制

**缺点**:
- 实现相对复杂

**适用场景**: 企业用户等需要突发能力的场景

---

## ⚙️ 配置方法

### 环境变量配置

在`.env.local`或`staging.env`中添加：

```bash
# 启用速率限制
RATE_LIMIT_ENABLED=true

# 默认限流策略
RATE_LIMIT_STRATEGY=sliding_window  # fixed_window | sliding_window | token_bucket

# 基础限流（普通用户）
RATE_LIMIT_BASIC_MAX_REQUESTS=60
RATE_LIMIT_BASIC_WINDOW_SECONDS=60

# 标准限流（付费用户）
RATE_LIMIT_STANDARD_MAX_REQUESTS=300
RATE_LIMIT_STANDARD_WINDOW_SECONDS=60

# 高级限流（企业用户）
RATE_LIMIT_PREMIUM_MAX_REQUESTS=1200
RATE_LIMIT_PREMIUM_WINDOW_SECONDS=60
RATE_LIMIT_PREMIUM_BURST_SIZE=200

# Token刷新限流
RATE_LIMIT_TOKEN_REFRESH_MAX_REQUESTS=10
RATE_LIMIT_TOKEN_REFRESH_WINDOW_SECONDS=60
```

### 代码配置

```python
from lark_service.core.rate_limiter import (
    RateLimitConfig,
    RateLimitStrategy,
    create_rate_limiter,
)

# 创建限流器
config = RateLimitConfig(
    max_requests=100,  # 100次/分钟
    window_seconds=60,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
)

limiter = create_rate_limiter(config)

# 检查限流
result = limiter.check_rate_limit("user:12345")

if not result.allowed:
    print(f"Rate limited! Retry after {result.retry_after}s")
else:
    print(f"Request allowed. Remaining: {result.remaining}")
```

### FastAPI中间件集成

```python
from fastapi import FastAPI
from lark_service.core.rate_limiter import rate_limit_middleware

app = FastAPI()

# 添加速率限制中间件
app.middleware("http")(rate_limit_middleware())

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 📊 预定义限流配置

| 配置名称 | 限制 | 策略 | 适用对象 |
|---------|------|------|---------|
| `basic` | 60次/分钟 | 滑动窗口 | 免费用户 |
| `standard` | 300次/分钟 | 滑动窗口 | 付费用户 |
| `premium` | 1200次/分钟 (突发200) | 令牌桶 | 企业用户 |
| `token_refresh` | 10次/分钟 | 固定窗口 | Token刷新操作 |
| `api_call` | 100次/分钟 | 滑动窗口 | API调用 |

---

## 🔍 响应头

限流中间件会在响应中添加以下HTTP头：

```
X-RateLimit-Limit: 100          # 限制总数
X-RateLimit-Remaining: 85       # 剩余配额
X-RateLimit-Reset: 1705567200   # 重置时间戳
Retry-After: 15                 # 建议重试时间（仅429响应）
```

### 429 Too Many Requests响应

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 15
}
```

---

## 🧪 测试速率限制

### 单元测试

```bash
# 运行速率限制单元测试
pytest tests/unit/core/test_rate_limiter.py -v

# 测试覆盖率
pytest tests/unit/core/test_rate_limiter.py --cov=lark_service.core.rate_limiter
```

### 压力测试

```bash
# 运行速率限制压测场景
python tests/performance/load_test_scenarios.py

# 或使用Locust Web UI
locust -f tests/performance/load_test_scenarios.py --host=http://localhost:8000
```

### 手动测试

```bash
# 快速连续请求，触发限流
for i in {1..200}; do
  curl -w "\nStatus: %{http_code}\n" http://localhost:8000/api/v1/health
done
```

---

## 📈 监控指标

Prometheus metrics自动采集限流相关指标：

```promql
# 限流触发次数
rate(lark_service_rate_limit_exceeded_total[5m])

# 按用户分组的限流
sum(rate(lark_service_rate_limit_exceeded_total[5m])) by (user_id)

# 配额使用率
lark_service_rate_limit_usage_ratio
```

### Grafana告警

建议配置以下告警：

```yaml
- alert: HighRateLimitUsage
  expr: lark_service_rate_limit_usage_ratio > 0.9
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "用户 {{ $labels.user_id }} 限流配额使用率 > 90%"

- alert: RateLimitAbuse
  expr: rate(lark_service_rate_limit_exceeded_total[1m]) > 10
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "检测到异常高频请求，可能存在滥用"
```

---

## 🎯 最佳实践

### 1. 选择合适的限流策略

- **固定窗口**: 简单操作（如Token刷新）
- **滑动窗口**: 常规API调用（推荐默认）
- **令牌桶**: 需要突发能力的场景

### 2. 合理设置限额

```python
# 根据业务特性设置
- API查询类: 300-600次/分钟
- 数据写入类: 60-120次/分钟
- Token管理类: 10-30次/分钟
```

### 3. 提供清晰的错误信息

```python
# ✅ 好的做法
{
  "error": "rate_limit_exceeded",
  "message": "您已超过API调用限制（100次/分钟）",
  "retry_after": 15,
  "limit": 100,
  "window": "1 minute"
}

# ❌ 不好的做法
{
  "error": "Too many requests"
}
```

### 4. 客户端重试策略

```python
import time
import requests

def api_call_with_retry(url, max_retries=3):
    """带重试的API调用"""
    for attempt in range(max_retries):
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            # 遵守Retry-After头
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue

        response.raise_for_status()

    raise Exception("Max retries exceeded")
```

### 5. 用户标识

```python
# 优先级顺序：
1. API Key / Access Token (最准确)
2. User ID (需要认证)
3. IP地址 (可能不准确，特别是共享代理)

# 推荐组合
rate_limit_key = f"{user_id}:{endpoint}"  # 按用户+端点限流
```

---

## ⚠️ 注意事项

### 分布式部署

在多实例部署时，考虑使用集中式限流：

```python
# 使用Redis实现分布式限流
from redis import Redis
from redis_rate_limit import RateLimiter

redis_client = Redis(host='localhost', port=6379)
limiter = RateLimiter(redis_client)
```

### 白名单

为特殊用户（如监控、内部服务）设置白名单：

```python
RATE_LIMIT_WHITELIST = [
    "monitoring_service",
    "internal_admin",
]

if user_id in RATE_LIMIT_WHITELIST:
    return  # 跳过限流
```

### 成本考虑

- 内存限流器适用于单实例/中小规模
- Redis限流器适用于大规模分布式部署
- 考虑限流数据的持久化和恢复

---

## 🔧 故障排查

### 问题1: 频繁触发限流

**排查步骤**:
1. 检查metrics：`lark_service_rate_limit_exceeded_total`
2. 查看日志：`grep "Rate limit exceeded" app.log`
3. 分析用户行为模式

**解决方案**:
- 调整限额配置
- 优化客户端请求频率
- 为高级用户提升配额

### 问题2: 限流不生效

**排查步骤**:
1. 确认`RATE_LIMIT_ENABLED=true`
2. 检查中间件是否正确挂载
3. 验证用户标识正确提取

**解决方案**:
```bash
# 测试限流端点
curl -v http://localhost:8000/api/v1/health \
  -H "X-User-ID: test_user"

# 查看响应头
# 应包含: X-RateLimit-Limit, X-RateLimit-Remaining
```

### 问题3: 性能影响

**优化建议**:
- 使用固定窗口或令牌桶（比滑动窗口快）
- 定期清理过期的限流记录
- 考虑使用本地缓存 + Redis两级存储

---

## 📚 参考资料

- [Rate Limiting Strategies](https://en.wikipedia.org/wiki/Rate_limiting)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [IETF Draft: RateLimit Header Fields](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)

---

**维护者**: Backend Team
**创建日期**: 2026-01-18
**最后更新**: 2026-01-18
