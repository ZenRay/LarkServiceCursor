# 错误恢复指南

本文档提供Lark Service常见错误的恢复步骤和最佳实践。

## 目录

1. [Token相关错误](#token相关错误)
2. [数据库连接错误](#数据库连接错误)
3. [API调用错误](#api调用错误)
4. [缓存错误](#缓存错误)
5. [配置错误](#配置错误)
6. [消息队列错误](#消息队列错误)

---

## Token相关错误

### 错误1: Token过期 (99991663)

**症状**:
```
LarkAPIError: Authentication token expired (code: 99991663)
```

**原因**: Access token已过期，需要刷新

**恢复步骤**:
1. 检查token是否在有效期内
```bash
# 查询token信息
python -m lark_service.cli.app token-info --app-id <APP_ID>
```

2. 手动刷新token
```bash
# 刷新tenant_access_token
python -m lark_service.cli.app refresh-token --app-id <APP_ID>
```

3. 如果问题持续，检查凭据是否正确
```bash
# 验证App ID和App Secret
python -m lark_service.cli.app validate --app-id <APP_ID>
```

**预防措施**:
- 使用CredentialPool自动管理token
- 设置合理的缓存过期时间（默认提前5分钟刷新）
- 监控token刷新失败告警

---

### 错误2: 凭据无效 (99991400/99991401)

**症状**:
```
LarkAPIError: Invalid App ID or App Secret (code: 99991400)
```

**原因**: App ID或App Secret配置错误

**恢复步骤**:
1. 验证飞书开放平台配置
   - 登录 https://open.feishu.cn/app
   - 检查App ID是否正确
   - 重新生成App Secret

2. 更新环境变量
```bash
# 编辑配置文件
vim .env.local

# 更新配置
LARK_APP_ID=cli_xxx
LARK_APP_SECRET=xxx
```

3. 重启应用
```bash
# 重新加载配置
docker compose restart lark-service
```

**预防措施**:
- 使用密钥管理系统（如Vault）存储凭据
- 定期轮换App Secret
- 在staging环境先验证配置

---

## 数据库连接错误

### 错误3: 数据库连接失败

**症状**:
```
OperationalError: could not connect to server
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**原因**: PostgreSQL服务不可用或配置错误

**恢复步骤**:
1. 检查PostgreSQL服务状态
```bash
# Docker环境
docker compose ps postgres

# 系统服务
systemctl status postgresql
```

2. 验证连接参数
```bash
# 测试连接
psql -h localhost -p 5432 -U lark -d lark_service

# 检查环境变量
echo $POSTGRES_HOST
echo $POSTGRES_PORT
```

3. 检查网络连通性
```bash
# 测试端口
nc -zv localhost 5432

# 查看防火墙规则
sudo iptables -L
```

4. 修复步骤
```bash
# 重启PostgreSQL
docker compose restart postgres

# 或重建容器
docker compose down postgres
docker compose up -d postgres
```

**预防措施**:
- 配置数据库健康检查
- 使用连接池（已实现）
- 设置合理的超时和重试策略
- 配置主从复制和自动故障转移

---

### 错误4: 数据库死锁

**症状**:
```
DatabaseError: deadlock detected
```

**原因**: 多个事务互相等待对方释放锁

**恢复步骤**:
1. 识别死锁事务
```sql
-- 查看当前锁
SELECT * FROM pg_locks WHERE NOT granted;

-- 查看活跃事务
SELECT * FROM pg_stat_activity WHERE state != 'idle';
```

2. 终止死锁事务
```sql
-- 终止特定进程
SELECT pg_terminate_backend(pid);
```

3. 应用层重试
- CredentialPool已实现自动重试机制
- 检查retry_on_error装饰器配置

**预防措施**:
- 保持事务简短
- 按固定顺序获取锁
- 使用乐观锁替代悲观锁
- 监控长时间运行的事务

---

## API调用错误

### 错误5: API限流 (99991405)

**症状**:
```
LarkAPIError: Rate limit exceeded (code: 99991405)
```

**原因**: 超过飞书API调用频率限制

**恢复步骤**:
1. 等待限流窗口重置（通常1分钟）
2. 检查调用频率
```python
# 查看API调用统计
from lark_service.monitoring.metrics import MetricsCollector
collector = MetricsCollector()
# 查询 lark_service_api_calls_total
```

3. 实施降级策略
- 使用缓存减少API调用
- 批量操作替代单次调用
- 实施客户端限流

**预防措施**:
- 配置rate_limiter（已实现）
- 使用exponential backoff重试
- 监控API调用量
- 与飞书申请更高的API配额

---

### 错误6: 网络超时

**症状**:
```
TimeoutError: Request timeout after 30s
```

**原因**: 网络延迟或API响应慢

**恢复步骤**:
1. 检查网络连通性
```bash
# 测试到飞书API的连接
curl -I https://open.feishu.cn

# 测试DNS解析
nslookup open.feishu.cn
```

2. 调整超时配置
```python
# config.py
API_TIMEOUT = 60  # 增加到60秒
```

3. 实施重试策略
- retry_on_error已配置3次重试
- 使用exponential backoff

**预防措施**:
- 配置合理的超时时间
- 实施熔断机制
- 监控API响应时间
- 使用CDN加速

---

## 缓存错误

### 错误7: Redis连接失败

**症状**:
```
ConnectionError: Error connecting to Redis
```

**原因**: Redis服务不可用

**恢复步骤**:
1. 检查Redis服务状态
```bash
# Docker环境
docker compose ps redis

# 测试连接
redis-cli -h localhost -p 6379 ping
```

2. 重启Redis
```bash
docker compose restart redis
```

3. 应用降级
- 系统会自动降级到数据库查询
- 监控缓存未命中率

**预防措施**:
- 配置Redis哨兵或集群
- 实施缓存预热
- 监控Redis内存使用
- 配置持久化策略

---

### 错误8: 缓存雪崩

**症状**: 大量缓存同时失效，导致数据库压力激增

**恢复步骤**:
1. 限流保护数据库
```python
# 启用rate_limiter
from lark_service.core.rate_limiter import RateLimitConfig, FixedWindowRateLimiter

limiter = FixedWindowRateLimiter(
    RateLimitConfig(max_requests=1000, window_seconds=60)
)
```

2. 重建缓存
```bash
# 预热关键数据
python scripts/cache_warmup.py
```

**预防措施**:
- 设置随机过期时间
- 实施缓存预热
- 使用多级缓存
- 配置熔断机制

---

## 配置错误

### 错误9: 环境变量缺失

**症状**:
```
ConfigError: Required environment variable LARK_APP_ID is not set
```

**原因**: 必需的环境变量未配置

**恢复步骤**:
1. 检查配置文件
```bash
# 查看当前配置
env | grep LARK

# 验证配置
python scripts/validate_env.py
```

2. 补充缺失配置
```bash
# 复制模板
cp .env.example .env.local

# 编辑配置
vim .env.local
```

3. 重启应用
```bash
docker compose restart
```

**预防措施**:
- 使用配置验证脚本（已提供）
- 提供完整的.env.example
- 部署前运行检查清单
- 使用配置管理工具

---

## 消息队列错误

### 错误10: RabbitMQ连接失败

**症状**:
```
AMQPConnectionError: Connection refused
```

**原因**: RabbitMQ服务不可用

**恢复步骤**:
1. 检查RabbitMQ状态
```bash
# 检查服务
docker compose ps rabbitmq

# 查看日志
docker compose logs rabbitmq
```

2. 重启RabbitMQ
```bash
docker compose restart rabbitmq
```

3. 验证连接
```bash
# 访问管理界面
http://localhost:15672
# 默认用户名/密码: guest/guest
```

**预防措施**:
- 配置RabbitMQ集群
- 实施消息持久化
- 监控队列长度
- 配置死信队列

---

## 通用恢复策略

### 1. 健康检查

定期运行健康检查脚本：
```bash
python scripts/health_check.py --all
```

### 2. 日志分析

查看应用日志：
```bash
# Docker环境
docker compose logs -f lark-service

# 系统日志
tail -f /var/log/lark-service/app.log
```

### 3. 监控告警

访问监控仪表板：
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### 4. 回滚策略

如果问题持续：
```bash
# 回滚到上一个版本
git checkout <previous-commit>
docker compose up -d --build

# 或使用蓝绿部署
./scripts/deploy.sh --rollback
```

### 5. 紧急联系

- 技术支持: support@example.com
- 飞书开放平台: https://open.feishu.cn/document/
- 紧急热线: XXX-XXXX-XXXX

---

## 最佳实践

1. **定期备份**: 每天自动备份数据库
2. **监控告警**: 配置关键指标告警
3. **文档更新**: 记录所有故障和恢复过程
4. **演练**: 定期进行故障演练
5. **自动化**: 自动化常见恢复操作

---

## 相关文档

- [故障排查手册](./troubleshooting-guide.md)
- [部署指南](./deployment.md)
- [监控配置](./monitoring-setup.md)
- [安全指南](./security-guide.md)
