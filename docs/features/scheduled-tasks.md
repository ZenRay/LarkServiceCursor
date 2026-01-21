# 定时任务 (Scheduled Tasks)

本文档介绍 Lark Service 中的定时任务功能,包括如何配置、管理和监控定时任务。

## 概述

Lark Service 使用 [APScheduler](https://apscheduler.readthedocs.io/) 实现定时任务调度功能,提供以下特性:

- ⏰ **灵活的调度策略**: 支持固定间隔 (Interval) 和 Cron 表达式
- 📊 **自动监控**: 集成 Prometheus 指标,实时监控任务执行状态
- 🔄 **自动重试**: 任务失败时自动记录,支持手动重试
- 🛡️ **异常处理**: 任务异常不会影响调度器运行
- 📝 **详细日志**: 记录每次任务执行的详细信息

## 内置定时任务

### 1. 用户信息同步 (User Info Sync)

**任务 ID**: `sync_user_info`
**调度策略**: 每 6 小时执行一次
**功能描述**:

- 从飞书 API 获取所有活跃应用的用户列表
- 更新本地数据库中的用户信息
- 记录最后同步时间

**配置**:

```python
# 默认配置 - 每 6 小时
scheduler.add_interval_job(
    sync_user_info_task,
    hours=6,
    job_id="sync_user_info",
)
```

### 2. Token 过期检查 (Token Expiry Check)

**任务 ID**: `check_token_expiry`
**调度策略**: 每天 2 次(9:00 AM, 6:00 PM)
**功能描述**:

- 检查所有应用的 Token 过期时间
- 发送过期提醒通知:
  - 7 天预警:普通提醒
  - 3 天严重警告:紧急通知
  - 已过期:关键告警
- 更新 Prometheus 指标

**配置**:

```python
# Cron 表达式: 每天 9AM 和 6PM
scheduler.add_cron_job(
    check_token_expiry_task,
    cron_expression="0 9,18 * * *",
    job_id="check_token_expiry",
)
```

### 3. 过期 Token 清理 (Expired Token Cleanup)

**任务 ID**: `cleanup_expired_tokens`
**调度策略**: 每天凌晨 3:00 AM
**功能描述**:

- 清理过期超过 7 天的 Token
- 保持数据库整洁
- 减少存储空间占用

**配置**:

```python
# Cron 表达式: 每天凌晨 3 点
scheduler.add_cron_job(
    cleanup_expired_tokens_task,
    cron_expression="0 3 * * *",
    job_id="cleanup_expired_tokens",
)
```

### 4. 健康检查 (Health Check)

**任务 ID**: `health_check`
**调度策略**: 每 5 分钟
**功能描述**:

- 检查数据库连接
- 检查 RabbitMQ 连接(如果配置)
- 检查飞书 API 可用性
- 记录健康状态

**配置**:

```python
# 每 5 分钟
scheduler.add_interval_job(
    health_check_task,
    minutes=5,
    job_id="health_check",
)
```

## 自定义定时任务

### 添加 Interval 任务

```python
from lark_service.scheduler.scheduler import scheduler_service

def my_task():
    """自定义任务逻辑"""
    print("执行定时任务...")
    # Your task logic here

# 添加每小时执行一次的任务
scheduler_service.add_interval_job(
    my_task,
    hours=1,
    job_id="my_custom_task",
)
```

### 添加 Cron 任务

```python
from lark_service.scheduler.scheduler import scheduler_service

async def my_async_task():
    """异步自定义任务"""
    # Your async task logic here
    pass

# 添加每天早上 8 点执行的任务
scheduler_service.add_cron_job(
    my_async_task,
    cron_expression="0 8 * * *",  # 分 时 日 月 周
    job_id="my_daily_task",
)
```

### Cron 表达式说明

Cron 表达式格式: `minute hour day month day_of_week`

| 字段 | 允许值 | 特殊字符 |
|------|--------|----------|
| minute | 0-59 | * , - / |
| hour | 0-23 | * , - / |
| day | 1-31 | * , - / |
| month | 1-12 | * , - / |
| day_of_week | 0-6 (0=Sunday) | * , - / |

**常用示例**:

```python
"0 0 * * *"      # 每天午夜
"0 9 * * 1-5"    # 工作日早上 9 点
"*/15 * * * *"   # 每 15 分钟
"0 0,12 * * *"   # 每天 0 点和 12 点
"0 0 1 * *"      # 每月 1 号午夜
```

## 监控和管理

### Prometheus 指标

定时任务会自动导出以下 Prometheus 指标:

```python
# 任务执行总数
scheduled_task_executions_total{task_name="...", status="success|failure"}

# 任务执行耗时
scheduled_task_duration_seconds{task_name="..."}
```

### Grafana 监控面板

访问 Grafana (`http://localhost:3000`) 查看:

1. **Scheduler Monitoring** - 调度器总览
   - 任务执行率(成功/失败)
   - 任务执行耗时(P95/P99)
   - 任务失败统计

2. **Token Expiry Monitoring** - Token 过期监控
   - Token 过期倒计时
   - Token 状态表格
   - 过期警告统计

### 日志查看

查看定时任务日志:

```bash
# 查看所有调度器日志
docker logs lark-service 2>&1 | grep "scheduler"

# 查看特定任务的日志
docker logs lark-service 2>&1 | grep "sync_user_info"
```

### 手动执行任务

如果需要手动触发定时任务:

```python
from lark_service.scheduler.tasks import sync_user_info_task
import asyncio

# 同步任务
sync_user_info_task()

# 异步任务
asyncio.run(sync_user_info_task())
```

### 临时禁用任务

```python
from lark_service.scheduler.scheduler import scheduler_service

# 移除任务
scheduler_service.remove_job("task_id")

# 重新添加
# ... 使用 add_interval_job 或 add_cron_job
```

## 配置选项

### 调度器配置

在 `src/lark_service/scheduler/scheduler.py` 中修改:

```python
scheduler = BackgroundScheduler(
    timezone="Asia/Shanghai",  # 时区
    job_defaults={
        "coalesce": True,        # 合并多个待执行的实例
        "max_instances": 1,      # 同一任务同时运行的最大实例数
        "misfire_grace_time": 60 # 错过执行的宽限时间(秒)
    }
)
```

### Token 过期监控配置

```python
monitor = TokenExpiryMonitor(
    messaging_client=client,
    warning_days=7,   # 预警天数
    critical_days=3,  # 严重警告天数
)
```

## 最佳实践

### 1. 任务设计原则

- ✅ **幂等性**: 任务应该能够安全地重复执行
- ✅ **超时控制**: 避免长时间运行的任务阻塞调度器
- ✅ **错误处理**: 在任务内部处理预期的异常
- ✅ **日志记录**: 记录关键操作和错误信息

### 2. 调度策略选择

- **高频任务** (< 1 小时): 使用 `add_interval_job`
- **定时任务** (特定时间): 使用 `add_cron_job`
- **避免资源竞争**: 错开多个任务的执行时间

### 3. 监控和告警

- 设置 Prometheus 告警规则
- 定期检查 Grafana 面板
- 关注任务失败率和执行时长

### 4. 性能优化

- 批量处理数据而非逐条处理
- 使用数据库连接池
- 避免在任务中进行阻塞 I/O 操作

## 故障排查

### 任务未执行

1. 检查调度器是否启动:

```bash
docker logs lark-service 2>&1 | grep "Scheduler started"
```

2. 检查任务是否注册:

```python
from lark_service.scheduler.scheduler import scheduler_service
jobs = scheduler_service.get_jobs()
print([job.id for job in jobs])
```

3. 检查时区设置是否正确

### 任务执行失败

1. 查看详细日志:

```bash
docker logs lark-service 2>&1 | grep -A 20 "Failed scheduled task"
```

2. 检查 Prometheus 指标:

```promql
scheduled_task_executions_total{status="failure"}
```

3. 验证任务依赖(数据库、API 等)是否正常

### 性能问题

1. 检查任务执行时长:

```promql
histogram_quantile(0.95, scheduled_task_duration_seconds_bucket)
```

2. 减少任务执行频率或优化任务逻辑

3. 考虑将长任务拆分为多个小任务

## 参考资料

- [APScheduler 官方文档](https://apscheduler.readthedocs.io/)
- [Cron 表达式生成器](https://crontab.guru/)
- [Prometheus 查询语法](https://prometheus.io/docs/prometheus/latest/querying/basics/)
