# 故障排查手册

本文档提供Lark Service系统故障的诊断方法和排查步骤。

## 目录

1. [快速诊断流程](#快速诊断流程)
2. [常见问题排查](#常见问题排查)
3. [性能问题排查](#性能问题排查)
4. [数据一致性问题](#数据一致性问题)
5. [诊断工具](#诊断工具)
6. [日志分析](#日志分析)

---

## 快速诊断流程

遇到问题时，按照以下流程快速定位：

```
┌─────────────────┐
│  发现问题症状    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      NO
│  服务是否运行？  ├──────────► 启动服务
└────────┬────────┘
         │ YES
         ▼
┌─────────────────┐      NO
│  健康检查通过？  ├──────────► 查看健康检查日志
└────────┬────────┘
         │ YES
         ▼
┌─────────────────┐
│  查看应用日志    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  查看监控指标    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  深入排查根因    │
└─────────────────┘
```

### 第1步: 检查服务状态

```bash
# Docker环境
cd staging-simulation
docker compose ps

# 查看所有服务状态
curl http://localhost:9091/health
```

**期望输出**:
```json
{
  "status": "healthy",
  "mock_data": "running"
}
```

### 第2步: 运行健康检查

```bash
# 完整健康检查
python scripts/health_check.py --all

# 或使用staging脚本
cd staging-simulation
bash scripts/check_config.sh
```

### 第3步: 查看日志

```bash
# 应用日志
docker compose logs -f --tail=100 lark-service

# 查看最近的错误
docker compose logs lark-service | grep ERROR

# 查看特定时间段
docker compose logs --since="2026-01-18T08:00:00" lark-service
```

### 第4步: 查看监控指标

访问监控仪表板:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

关键指标:
```
# HTTP错误率
rate(lark_service_http_requests_total{status=~"5.."}[5m])

# API调用失败率
rate(lark_service_api_errors_total[5m])

# Token刷新失败
lark_service_token_refreshes_total{status="failure"}
```

---

## 常见问题排查

### 问题1: 服务无法启动

**症状**:
- Docker容器持续重启
- 应用进程立即退出

**排查步骤**:

1. 查看容器日志
```bash
docker compose logs lark-service
```

2. 检查常见原因
```bash
# 配置错误
python scripts/validate_env.py

# 端口冲突
netstat -tuln | grep -E "9091|8000"

# 权限问题
ls -la /var/log/lark-service/
```

3. 逐个依赖检查
```bash
# PostgreSQL
docker compose exec postgres pg_isready

# Redis
docker compose exec redis redis-cli ping

# RabbitMQ
curl http://localhost:15673/api/overview
```

**常见错误码**:
- Exit 1: 配置错误
- Exit 137: 内存不足（OOM）
- Exit 139: 段错误（Segmentation Fault）

**解决方案**: 参见 [错误恢复指南](./error-recovery-guide.md#配置错误)

---

### 问题2: API调用失败

**症状**:
- 返回5xx错误
- 超时
- Token错误

**排查步骤**:

1. 验证凭据
```bash
# 检查环境变量
env | grep LARK

# 测试凭据
python -m lark_service.cli.app validate --app-id <APP_ID>
```

2. 测试网络连通性
```bash
# 测试到飞书API的连接
curl -v https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "your_app_id",
    "app_secret": "your_app_secret"
  }'
```

3. 查看API调用日志
```bash
# 筛选API错误
docker compose logs lark-service | grep "LarkAPIError"

# 查看token刷新记录
docker compose logs lark-service | grep "token_refresh"
```

4. 检查限流情况
```bash
# 查询Prometheus
# rate(lark_service_api_calls_total[1m])
```

**解决方案**: 参见 [错误恢复指南](./error-recovery-guide.md#api调用错误)

---

### 问题3: 数据库查询慢

**症状**:
- API响应时间长
- 数据库CPU使用率高

**排查步骤**:

1. 查看慢查询日志
```sql
-- 连接数据库
psql -h localhost -p 5433 -U lark -d lark_service

-- 查看慢查询
SELECT
  query,
  calls,
  total_time,
  mean_time,
  max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

2. 查看当前运行的查询
```sql
SELECT
  pid,
  now() - query_start as duration,
  state,
  query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

3. 检查索引
```sql
-- 查看缺失的索引
SELECT
  schemaname,
  tablename,
  attname,
  n_distinct,
  correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND correlation < 0.1;
```

4. 分析查询执行计划
```sql
EXPLAIN ANALYZE
SELECT * FROM tokens WHERE app_id = 'xxx';
```

**优化建议**:
- 添加索引
- 优化查询语句
- 使用连接池
- 配置缓存

---

### 问题4: 内存泄漏

**症状**:
- 内存使用持续增长
- 容器被OOM Killer杀死

**排查步骤**:

1. 监控内存使用
```bash
# 查看容器内存
docker stats lark-service

# 查看进程内存
docker compose exec lark-service ps aux
```

2. 使用内存分析工具
```python
# 在代码中添加
import tracemalloc
tracemalloc.start()

# 执行操作后
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

3. 检查常见原因
```bash
# 未关闭的数据库连接
SELECT count(*) FROM pg_stat_activity;

# 缓存过大
redis-cli INFO memory

# 未释放的对象
# 使用objgraph分析Python对象
```

**解决方案**:
- 配置连接池大小
- 设置缓存上限
- 使用弱引用
- 定期重启（临时方案）

---

### 问题5: 消息丢失

**症状**:
- 消息发送成功但未送达
- 队列消息堆积

**排查步骤**:

1. 检查RabbitMQ状态
```bash
# 访问管理界面
http://localhost:15673

# 查看队列状态
docker compose exec rabbitmq rabbitmqctl list_queues
```

2. 检查消费者
```bash
# 查看连接
docker compose exec rabbitmq rabbitmqctl list_consumers
```

3. 查看死信队列
```bash
# 检查DLX
docker compose exec rabbitmq rabbitmqctl list_exchanges | grep dlx
```

4. 查看应用日志
```bash
docker compose logs lark-service | grep "message_queue"
```

**常见原因**:
- 消费者未启动
- 消息TTL过短
- 队列满
- 网络分区

---

## 性能问题排查

### CPU使用率高

**诊断**:

1. 查看CPU使用
```bash
# 容器CPU
docker stats

# 进程CPU
top -p $(pgrep -f "lark_service")
```

2. 分析CPU热点
```python
# 使用cProfile
python -m cProfile -o profile.stats -m lark_service.cli.app

# 分析结果
python -m pstats profile.stats
```

3. 检查Prometheus
```
# CPU使用率
rate(process_cpu_seconds_total[5m])
```

**常见原因**:
- 密集计算操作
- 正则表达式性能差
- 数据库查询未优化
- 死循环

---

### 响应时间慢

**诊断**:

1. 使用APM工具
```python
# 添加tracing
from lark_service.utils.tracing import trace_request

@trace_request
def slow_function():
    pass
```

2. 分析延迟来源
```bash
# 查询P95延迟
histogram_quantile(0.95,
  rate(lark_service_http_request_duration_seconds_bucket[5m])
)
```

3. 逐层排查
- API调用延迟: 查看 `lark_service_api_call_duration_seconds`
- 数据库延迟: 查看慢查询日志
- 网络延迟: 使用 `curl -w "@curl-format.txt"`

**优化建议**:
- 使用缓存
- 异步处理
- 数据库查询优化
- CDN加速

---

## 数据一致性问题

### Token缓存不一致

**症状**: 缓存的token与数据库不一致

**排查**:

1. 比对数据
```python
# 查询Redis
redis-cli GET "token:app1:tenant_access_token"

# 查询数据库
psql -c "SELECT * FROM tokens WHERE app_id='app1'"
```

2. 检查更新逻辑
```bash
docker compose logs lark-service | grep "token_update"
```

**解决方案**:
- 清空缓存重建
- 检查缓存失效逻辑
- 使用缓存版本号

---

### 数据库主从延迟

**症状**: 主库写入后从库读取不到

**排查**:

1. 检查复制延迟
```sql
SELECT
  application_name,
  state,
  sync_state,
  replay_lag
FROM pg_stat_replication;
```

2. 检查网络
```bash
# 测试主从连接
pg_isready -h slave-host -p 5432
```

**解决方案**:
- 优化网络
- 读写分离时注意强一致性需求
- 使用read-your-writes模式

---

## 诊断工具

### 1. 健康检查脚本

```bash
# 完整检查
python scripts/health_check.py --all

# 单项检查
python scripts/health_check.py --database
python scripts/health_check.py --redis
python scripts/health_check.py --rabbitmq
```

### 2. 配置验证

```bash
# 验证环境变量
python scripts/validate_env.py

# 验证数据库连接
python -c "from lark_service.core.config import Config; Config.from_env()"
```

### 3. 数据库诊断

```bash
# 连接测试
psql -h localhost -p 5433 -U lark -d lark_service -c "SELECT 1"

# 表大小
psql -c "SELECT pg_size_pretty(pg_total_relation_size('tokens'))"

# 索引使用情况
psql -c "SELECT * FROM pg_stat_user_indexes"
```

### 4. 性能测试

```bash
# 压力测试
locust -f tests/performance/load_test_scenarios.py --host=http://localhost:8000

# API基准测试
python tests/performance/benchmark_test.py
```

### 5. 日志分析

```bash
# 错误统计
docker compose logs lark-service | grep ERROR | wc -l

# 最频繁的错误
docker compose logs lark-service | grep ERROR | sort | uniq -c | sort -rn | head -10

# 响应时间分析
docker compose logs lark-service | grep "duration_ms" | awk '{print $NF}' | sort -n
```

---

## 日志分析

### 日志格式

生产环境使用JSON格式:
```json
{
  "timestamp": "2026-01-18T08:00:00Z",
  "level": "ERROR",
  "logger": "lark_service.core",
  "message": "Token refresh failed",
  "request_id": "req-123",
  "app_id": "cli_xxx",
  "error_code": "99991663"
}
```

### 日志查询

使用`jq`解析JSON日志:

```bash
# 查找特定错误码
cat app.log | jq 'select(.error_code == "99991663")'

# 统计错误类型
cat app.log | jq -r '.error_code' | sort | uniq -c

# 按时间筛选
cat app.log | jq 'select(.timestamp > "2026-01-18T08:00:00Z")'

# 追踪请求链路
cat app.log | jq 'select(.request_id == "req-123")'
```

### 日志聚合

如果使用ELK或Loki:

```
# Elasticsearch查询
GET /lark-service-*/_search
{
  "query": {
    "match": {
      "level": "ERROR"
    }
  }
}

# Loki查询
{level="error"} |= "token"
```

---

## 故障排查清单

遇到问题时，按此清单逐项检查:

- [ ] 服务是否运行？
- [ ] 健康检查是否通过？
- [ ] 配置是否正确？
- [ ] 网络是否连通？
- [ ] 依赖服务是否正常？
- [ ] 资源是否充足（CPU/内存/磁盘）？
- [ ] 日志有无异常？
- [ ] 监控指标是否异常？
- [ ] 最近是否有变更？
- [ ] 是否有已知问题？

---

## 升级路径

如果无法解决，按以下顺序升级:

1. **查看文档**:
   - [错误恢复指南](./error-recovery-guide.md)
   - [部署指南](./deployment.md)
   - [API文档](./api-documentation.md)

2. **搜索已知问题**:
   - GitHub Issues
   - 飞书开放平台文档
   - Stack Overflow

3. **联系支持**:
   - 技术支持: support@example.com
   - Slack频道: #lark-service-support
   - 工单系统: https://support.example.com

4. **紧急热线**:
   - 生产环境问题: XXX-XXXX-XXXX
   - 安全事件: XXX-XXXX-XXXX

---

## 相关文档

- [错误恢复指南](./error-recovery-guide.md)
- [部署指南](./deployment.md)
- [监控配置](./monitoring-setup.md)
- [性能优化指南](./performance-tuning-guide.md)
- [安全指南](./security-guide.md)
