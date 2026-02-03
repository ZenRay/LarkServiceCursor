# 性能需求与测试规范

**版本**: 1.0.0
**更新时间**: 2026-01-15
**状态**: Draft

---

## 📊 性能目标 (CHK025, CHK026)

### 核心性能指标

| 指标 ID | 指标名称 | 目标值 | 验证方法 |
|---------|---------|--------|---------|
| **P001** | 并发 API 调用吞吐量 | ≥ 100 次/秒 | 压力测试 |
| **P002** | Token 自动处理成功率 | ≥ 99.9% | 统计分析 |
| **P003** | API 响应时间 (P99) | ≤ 2 秒 | 性能监控 |
| **P004** | Token 刷新耗时 | ≤ 500ms | 单元测试 |
| **P005** | 数据库查询耗时 | ≤ 50ms | 性能测试 |

---

## 🎯 P001: 并发 API 调用吞吐量 (≥ 100 次/秒)

### 测试场景定义

**场景 1: 单应用并发调用**
```python
# 测试设置
- 并发用户数: 10
- 每用户请求数: 10
- 总请求数: 100
- 测试时长: ≤ 1 秒
- 应用数: 1

# API 类型分布
- get_token: 50%
- send_message: 30%
- get_user: 20%

# 预期结果
- 成功率: ≥ 95%
- 平均响应时间: ≤ 500ms
- P99 响应时间: ≤ 2s
```

**场景 2: 多应用并发调用**
```python
# 测试设置
- 并发应用数: 5
- 每应用请求数: 20
- 总请求数: 100
- 测试时长: ≤ 1 秒

# 预期结果
- 应用间隔离: 互不影响
- Token 无冲突: 无并发刷新错误
- 成功率: ≥ 95%
```

### 测试工具

**Locust 压力测试**:
```python
# tests/performance/test_concurrent_calls.py
from locust import HttpUser, task, between

class LarkServiceUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Setup test environment."""
        self.app_id = "cli_test12345678"

    @task(5)
    def get_token(self):
        """Test token acquisition (50% of traffic)."""
        self.client.get(f"/api/token?app_id={self.app_id}")

    @task(3)
    def send_message(self):
        """Test message sending (30% of traffic)."""
        self.client.post("/api/message", json={
            "app_id": self.app_id,
            "receive_id": "ou_test",
            "msg_type": "text",
            "content": "Test message"
        })

    @task(2)
    def get_user(self):
        """Test user query (20% of traffic)."""
        self.client.get(f"/api/user?app_id={self.app_id}&open_id=ou_test")
```

**运行测试**:
```bash
# 启动 Locust
locust -f tests/performance/test_concurrent_calls.py \
       --host=http://localhost:8000 \
       --users=10 \
       --spawn-rate=10 \
       --run-time=10s \
       --headless

# 预期输出
# Name               # reqs      # fails  |     Avg     Min     Max  Median  |   req/s
# ---------------------------------------------------------------------------------
# GET /api/token        500          5     |     150      50     800     120  |    50.0
# POST /api/message     300          3     |     200      80    1200     180  |    30.0
# GET /api/user         200          2     |     180      60     900     150  |    20.0
# ---------------------------------------------------------------------------------
# Aggregated           1000         10     |     170      50    1200     140  |   100.0
#
# ✅ 吞吐量: 100 req/s (达标)
# ✅ 成功率: 99.0% (达标)
```

---

## 🎯 P002: Token 自动处理成功率 (≥ 99.9%)

### 验证方法

**定义**:
- **成功**: 调用方无需手动介入,Token 自动获取、刷新、重试成功
- **失败**: 需要调用方手动重试、重新获取 Token、或处理 Token 失效错误

**统计公式**:
```
自动处理成功率 = (自动成功次数 / 总调用次数) × 100%
```

**测试场景**:

1. **新 Token 获取** (自动成功)
   ```python
   # 第一次调用,无缓存 Token
   token = pool.get_token("cli_12345678")
   # ✅ 自动从 API 获取并缓存
   ```

2. **缓存 Token 使用** (自动成功)
   ```python
   # 第二次调用,Token 未过期
   token = pool.get_token("cli_12345678")
   # ✅ 直接返回缓存 Token
   ```

3. **Token 自动刷新** (自动成功)
   ```python
   # Token 剩余 5% 生命周期
   token = pool.get_token("cli_12345678")
   # ✅ 后台自动刷新,返回新 Token
   ```

4. **Token 过期重试** (自动成功)
   ```python
   # Token 已过期,API 调用失败
   # ✅ 自动刷新 Token 并重试,成功
   ```

5. **网络故障重试** (自动成功)
   ```python
   # 网络超时
   # ✅ 指数退避重试,成功
   ```

6. **Token 无效** (自动失败,需手动介入)
   ```python
   # App Secret 被撤销
   # ❌ 3次重试后仍失败,抛出异常
   ```

**实现统计**:
```python
# src/lark_service/core/credential_pool.py
class CredentialPool:
    def __init__(self, config: Config):
        self.stats = {
            "total_calls": 0,
            "auto_success": 0,
            "manual_required": 0,
        }

    def get_token(self, app_id: str, **kwargs) -> str:
        """Track success rate."""
        self.stats["total_calls"] += 1

        try:
            token = self._get_token_with_retry(app_id, **kwargs)
            self.stats["auto_success"] += 1
            return token
        except TokenAcquisitionError:
            self.stats["manual_required"] += 1
            raise

    def get_success_rate(self) -> float:
        """Calculate auto-handling success rate."""
        if self.stats["total_calls"] == 0:
            return 0.0
        return (self.stats["auto_success"] / self.stats["total_calls"]) * 100
```

**验证测试**:
```python
# tests/integration/test_token_success_rate.py
def test_token_auto_handling_success_rate():
    """Verify ≥ 99.9% auto-handling success rate."""
    pool = CredentialPool(config)

    # 模拟 10,000 次调用
    total_calls = 10000
    for i in range(total_calls):
        try:
            pool.get_token(f"cli_test{i % 100}")
        except TokenAcquisitionError:
            # 仅在 App Secret 无效时失败
            pass

    # 验证成功率
    success_rate = pool.get_success_rate()
    assert success_rate >= 99.9, f"Success rate {success_rate}% < 99.9%"

    # 输出统计
    print(f"""
    Token Auto-Handling Statistics:
    - Total Calls: {pool.stats['total_calls']}
    - Auto Success: {pool.stats['auto_success']}
    - Manual Required: {pool.stats['manual_required']}
    - Success Rate: {success_rate:.2f}%
    """)
```

---

## 🎯 P003: API 响应时间 (P99 ≤ 2 秒)

### 测试方法

**使用 pytest-benchmark**:
```python
# tests/performance/test_response_time.py
import pytest
from lark_service.core.credential_pool import CredentialPool

def test_get_token_response_time(benchmark):
    """Benchmark token acquisition response time."""
    pool = CredentialPool(config)
    app_id = "cli_benchmark_test"

    # 运行基准测试
    result = benchmark(pool.get_token, app_id)

    # 验证 P99 响应时间
    stats = benchmark.stats
    p99_time = stats.get("p99", 0)

    assert p99_time <= 2.0, f"P99 response time {p99_time}s > 2s"

    print(f"""
    Response Time Statistics:
    - Min: {stats['min']:.3f}s
    - Max: {stats['max']:.3f}s
    - Mean: {stats['mean']:.3f}s
    - Median: {stats['median']:.3f}s
    - P95: {stats['p95']:.3f}s
    - P99: {p99_time:.3f}s ✅
    """)
```

**运行测试**:
```bash
pytest tests/performance/test_response_time.py --benchmark-only

# 预期输出
# -------------------------------------------------------------------------
# Name                          Min     Max    Mean  Median    P95    P99
# -------------------------------------------------------------------------
# test_get_token_response_time  0.050   1.800  0.150   0.120  0.500  1.200
# -------------------------------------------------------------------------
# ✅ P99: 1.200s < 2.0s (达标)
```

---

## 🎯 P004: Token 刷新耗时 (≤ 500ms)

### 测试场景

```python
# tests/unit/core/test_token_refresh_performance.py
import time
import pytest

def test_token_refresh_performance():
    """Verify token refresh completes within 500ms."""
    pool = CredentialPool(config)
    app_id = "cli_perf_test12345"

    # 预热: 获取初始 Token
    pool.get_token(app_id)

    # 测试刷新性能
    start_time = time.time()
    pool.refresh_token(app_id)
    elapsed_time = time.time() - start_time

    # 验证耗时
    assert elapsed_time <= 0.5, f"Refresh time {elapsed_time:.3f}s > 0.5s"

    print(f"Token refresh completed in {elapsed_time:.3f}s ✅")
```

---

## 🎯 P005: 数据库查询耗时 (≤ 50ms)

### 测试场景

```python
# tests/performance/test_database_performance.py
import time

def test_database_query_performance():
    """Verify database queries complete within 50ms."""
    storage = TokenStorageService(config)

    # 测试 Token 查询
    start_time = time.time()
    token = storage.get_token("cli_db_test", "app_access_token")
    query_time = (time.time() - start_time) * 1000  # Convert to ms

    assert query_time <= 50, f"Query time {query_time:.1f}ms > 50ms"

    print(f"Database query completed in {query_time:.1f}ms ✅")
```

---

## 📈 性能监控

### 生产环境监控指标

```python
# 使用 Prometheus 监控
from prometheus_client import Counter, Histogram

# 请求计数器
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

# 响应时间直方图
api_response_time = Histogram(
    'api_response_time_seconds',
    'API response time',
    ['method', 'endpoint']
)

# Token 刷新计数器
token_refresh_total = Counter(
    'token_refresh_total',
    'Total token refreshes',
    ['app_id', 'token_type', 'result']
)
```

### 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: lark_service_performance
    rules:
      # P001: 吞吐量低于阈值
      - alert: LowThroughput
        expr: rate(api_requests_total[1m]) < 100
        for: 5m
        annotations:
          summary: "API throughput below 100 req/s"

      # P002: 成功率低于阈值
      - alert: LowSuccessRate
        expr: |
          (
            sum(rate(api_requests_total{status="success"}[5m])) /
            sum(rate(api_requests_total[5m]))
          ) < 0.999
        for: 5m
        annotations:
          summary: "Success rate below 99.9%"

      # P003: P99 响应时间超标
      - alert: HighResponseTime
        expr: histogram_quantile(0.99, api_response_time_seconds) > 2
        for: 5m
        annotations:
          summary: "P99 response time > 2s"
```

---

## ✅ 验收标准

### Phase 1 性能验收

- [ ] 并发测试达到 100 req/s (P001)
- [ ] 成功率 ≥ 99.9% (P002)
- [ ] P99 响应时间 ≤ 2s (P003)
- [ ] Token 刷新 ≤ 500ms (P004)
- [ ] 数据库查询 ≤ 50ms (P005)

### Phase 2 性能验收

- [ ] 压力测试报告生成
- [ ] 性能监控指标上线
- [ ] 告警规则配置完成
- [ ] 性能瓶颈分析和优化

---

## 🔧 性能优化建议

### 数据库优化

1. **索引优化**
   ```sql
   -- Token 查询索引
   CREATE INDEX idx_tokens_app_type ON tokens(app_id, token_type);

   -- 用户缓存索引
   CREATE INDEX idx_user_cache_app_open ON user_cache(app_id, open_id);
   ```

2. **连接池配置**
   ```python
   # PostgreSQL 连接池
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,          # 连接池大小
       max_overflow=10,       # 最大溢出连接
       pool_pre_ping=True,    # 连接健康检查
       pool_recycle=3600,     # 连接回收时间
   )
   ```

### 缓存优化

1. **本地内存缓存**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def get_cached_token(app_id: str, token_type: str) -> str:
       """LRU cache for hot tokens."""
       return pool.get_token(app_id, token_type)
   ```

2. **Token 预加载**
   ```python
   def warm_up_tokens(app_ids: list[str]) -> None:
       """Pre-fetch tokens for frequently used apps."""
       for app_id in app_ids:
           pool.get_token(app_id)
   ```

---

**维护者**: Lark Service Team
**参考**: [performance-requirements.md](./performance-requirements.md)
