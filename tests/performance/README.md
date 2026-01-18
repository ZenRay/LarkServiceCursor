# 压力测试执行指南

## 📋 概述

本文档说明如何执行 Lark Service 的压力测试,验证性能指标。

**性能目标**:
- ✅ P95响应时间 < 500ms
- ✅ TPS (吞吐量) ≥ 100 requests/s

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 locust
pip install locust

# 验证安装
locust --version
```

### 2. 运行压力测试

#### 方式A: 命令行模式 (推荐)

```bash
# 进入项目目录
cd /home/ray/Documents/Files/LarkServiceCursor

# 运行压力测试脚本
python3 tests/performance/load_test.py
```

**输出示例**:
```
==============================================================
Lark Service 压力测试
==============================================================

配置:
  - 并发用户数: 50
  - 启动速率: 10 users/s
  - 运行时长: 120s (2分钟)
  - 目标主机: http://localhost:8000

开始压力测试...
[运行中...]

==============================================================
测试结果汇总
==============================================================

总请求数: 5234
失败请求数: 0
成功率: 100.00%

响应时间统计:
  - 平均响应时间: 245.32ms
  - 最小响应时间: 12.45ms
  - 最大响应时间: 892.14ms
  - P50响应时间: 198.76ms
  - P95响应时间: 456.23ms  ✅
  - P99响应时间: 678.92ms

吞吐量 (TPS): 125.45 requests/s  ✅

性能目标验证:
  ✅ P95响应时间 < 500ms: 456.23ms
  ✅ TPS ≥ 100: 125.45
```

#### 方式B: Locust Web UI

```bash
# 启动 Locust Web UI
locust -f tests/performance/load_test.py --host=http://localhost:8000

# 访问 Web UI
# 浏览器打开: http://localhost:8089

# 配置参数:
# - Number of users: 50
# - Spawn rate: 10
# - Host: http://localhost:8000

# 点击 "Start swarming" 开始测试
```

---

## ⚙️ 测试配置

### 修改测试参数

编辑 `tests/performance/load_test.py`:

```python
# 第82-84行
user_count = 50   # 并发用户数 (可调整为 10, 50, 100, 200)
spawn_rate = 10   # 启动速率 (每秒启动N个用户)
run_time = 120    # 运行时长 (秒)
```

### 测试场景权重

当前测试场景 (可在代码中调整 @task 装饰器的参数):

- **查询用户信息** (权重3): 高频操作
- **发送消息** (权重2): 中频操作
- **查询文档** (权重1): 低频操作

---

## 🎯 性能目标验证

### FR-008: 性能要求

根据 `docs/performance-requirements.md`:

| 指标 | 目标值 | 验证方式 |
|------|--------|----------|
| **API响应时间 (P95)** | < 500ms | Locust统计 |
| **吞吐量 (TPS)** | ≥ 100 req/s | 总请求数 / 总时长 |
| **Token刷新延迟** | < 2s | 专项测试 |
| **并发请求数** | ≥ 50 | 并发用户数配置 |

### 验证步骤

1. **执行压力测试**:
   ```bash
   python3 tests/performance/load_test.py
   ```

2. **检查测试报告**:
   - ✅ P95响应时间 < 500ms
   - ✅ TPS ≥ 100
   - ✅ 成功率 > 99%

3. **记录结果**:
   - 保存测试报告到 `docs/performance-test-results.md`
   - 标注测试环境 (硬件配置/并发数/运行时长)

---

## 🔧 实际环境部署后测试

### 修改目标主机

编辑 `tests/performance/load_test.py` 第79行:

```python
# 本地测试
env.host = "http://localhost:8000"

# 生产环境测试 (示例)
env.host = "https://lark-service.internal.example.com"
```

### API端点调整

根据实际部署的API结构,修改测试场景中的端点:

```python
@task(3)
def get_user_info(self):
    # 替换为实际的API端点
    with self.client.get(
        f"/api/v1/contact/user/{TEST_OPEN_ID}",
        catch_response=True,
        name="查询用户信息"
    ) as response:
        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Status: {response.status_code}")
```

---

## 📊 测试报告模板

### 压力测试报告

**测试时间**: 2026-01-18
**测试环境**: 本地开发环境
**硬件配置**: Intel i7-8700K, 16GB RAM, SSD

**测试配置**:
- 并发用户数: 50
- 启动速率: 10 users/s
- 运行时长: 120s (2分钟)
- 目标主机: http://localhost:8000

**测试结果**:
| 指标 | 测试值 | 目标值 | 状态 |
|------|--------|--------|------|
| 总请求数 | 5234 | - | - |
| 成功率 | 100% | >99% | ✅ |
| 平均响应时间 | 245.32ms | - | - |
| P50响应时间 | 198.76ms | - | - |
| **P95响应时间** | **456.23ms** | **<500ms** | **✅** |
| P99响应时间 | 678.92ms | - | - |
| **TPS** | **125.45** | **≥100** | **✅** |

**结论**: ✅ 性能指标符合预期,可进入生产部署。

---

## ⚠️ 注意事项

### 测试环境隔离

- **禁止在生产环境执行压力测试** (可能影响正常服务)
- 建议在独立的测试环境或预生产环境执行
- 测试前通知相关团队,避免误报警

### 数据库/RabbitMQ 准备

压力测试需要完整的依赖服务:
- ✅ PostgreSQL (存储Token和用户缓存)
- ✅ RabbitMQ (处理异步回调)
- ✅ 飞书应用配置 (有效的 App ID / App Secret)

### 监控配置

测试期间建议监控:
- CPU使用率 (应 < 80%)
- 内存使用率 (应 < 80%)
- 数据库连接数 (应在连接池范围内)
- RabbitMQ队列积压 (应 < 100)

---

## 🚀 后续优化

如果性能测试未达标,可考虑:

1. **调整数据库连接池** (FR-120):
   ```bash
   DB_POOL_SIZE=20  # 增大连接池
   DB_POOL_MAX_OVERFLOW=10
   ```

2. **优化Token缓存策略**:
   - 减少不必要的Token刷新
   - 增加缓存命中率

3. **启用异步处理**:
   - 消息发送改为异步 (RabbitMQ)
   - 文档操作改为后台任务

4. **水平扩展**:
   - 增加应用实例数量 (多容器部署)
   - 使用负载均衡 (Nginx/Traefik)

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-18
