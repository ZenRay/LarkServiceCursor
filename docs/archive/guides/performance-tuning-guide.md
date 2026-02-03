# 性能调优指南

本文档提供Lark Service系统的性能优化建议和调优方法。

## 性能目标

- API响应时间P95 < 500ms
- 吞吐量 ≥ 100 requests/s
- Token刷新成功率 > 99.9%
- 数据库查询P95 < 100ms
- 缓存命中率 > 80%

## 数据库优化

### 1. 索引优化

```sql
-- 为常用查询添加索引
CREATE INDEX idx_tokens_app_id ON tokens(app_id);
CREATE INDEX idx_tokens_expires_at ON tokens(expires_at);
CREATE INDEX idx_user_cache_user_id ON user_cache(user_id);

-- 复合索引
CREATE INDEX idx_tokens_app_token_type ON tokens(app_id, token_type);
```

### 2. 连接池配置

```python
# config.py
DB_POOL_SIZE = 20  # 根据并发量调整
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600  # 1小时回收连接
```

### 3. 查询优化

- 使用EXPLAIN ANALYZE分析慢查询
- 避免SELECT *，只查询需要的字段
- 使用批量操作替代循环查询
- 实施分页查询

## 缓存优化

### 1. Redis配置

```ini
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
```

### 2. 缓存策略

```python
# 设置合理的TTL
TOKEN_CACHE_TTL = 7000  # Token有效期7200s，提前200s刷新
USER_CACHE_TTL = 3600   # 用户信息1小时

# 使用缓存预热
def warmup_cache():
    # 预加载热门数据
    pass
```

### 3. 缓存穿透保护

```python
# 使用布隆过滤器
# 缓存空值（短TTL）
# 实施请求合并
```

## API调用优化

### 1. 批量操作

```python
# 批量获取用户信息
users = contact_client.batch_get_users(user_ids)

# 而不是
for user_id in user_ids:
    user = contact_client.get_user(user_id)
```

### 2. 并发控制

```python
# 使用异步并发
import asyncio

async def fetch_all():
    tasks = [fetch_user(id) for id in ids]
    return await asyncio.gather(*tasks)
```

### 3. 速率限制

```python
from lark_service.core.rate_limiter import rate_limit

# 防止超出API限流
@rate_limit(max_requests=1000, window_seconds=60)
def call_api():
    pass
```

## 应用层优化

### 1. 连接复用

```python
# 复用HTTP连接
session = requests.Session()
session.mount('https://', HTTPAdapter(pool_connections=10, pool_maxsize=20))
```

### 2. 超时配置

```python
# 合理设置超时
API_TIMEOUT = 30
DB_TIMEOUT = 10
REDIS_TIMEOUT = 5
```

### 3. 异步处理

```python
# 耗时操作使用消息队列异步处理
def send_message(msg):
    queue.publish("message_queue", msg)
```

## 监控和分析

### 1. 性能指标

```promql
# 关键指标
rate(lark_service_http_request_duration_seconds_sum[5m]) / rate(lark_service_http_request_duration_seconds_count[5m])

# P95延迟
histogram_quantile(0.95, rate(lark_service_http_request_duration_seconds_bucket[5m]))
```

### 2. 慢查询分析

```sql
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### 3. 性能剖析

```python
# 使用cProfile
python -m cProfile -o profile.stats app.py

# 分析结果
python -m pstats profile.stats
```

## 系统层优化

### 1. 资源配置

```yaml
# Docker Compose
services:
  lark-service:
    cpus: "2"
    memory: 4g
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4g
```

### 2. 操作系统调优

```bash
# 增加文件描述符
ulimit -n 65536

# TCP优化
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.core.somaxconn=1024
```

### 3. 负载均衡

```nginx
upstream lark_service {
    least_conn;
    server app1:8000 weight=3;
    server app2:8000 weight=2;
    keepalive 32;
}
```

## 相关文档

- [监控配置](./monitoring-setup.md)
- [故障排查](./troubleshooting-guide.md)
- [性能测试](../tests/performance/README.md)
