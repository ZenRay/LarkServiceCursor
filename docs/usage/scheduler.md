# Scheduler 定时任务

Lark Service 提供了基于 APScheduler 的定时任务调度服务,用于执行周期性的维护和监控操作。

## 功能特点

- ✅ **Interval Jobs**: 按固定时间间隔执行
- ✅ **Cron Jobs**: 按 cron 表达式执行
- ✅ **Prometheus 集成**: 自动记录任务执行指标
- ✅ **错误处理**: 自动捕获和记录任务异常
- ✅ **优雅关闭**: 支持 graceful shutdown

## 快速开始

### 基础用法

```python
from lark_service.scheduler.scheduler import SchedulerService

# 创建 scheduler 实例
scheduler = SchedulerService()

# 定义任务函数
def my_task():
    print("Task is running!")

# 添加 interval job (每小时执行一次)
scheduler.add_interval_job(
    my_task,
    hours=1,
    job_id="hourly_task"
)

# 添加 cron job (每天上午 9 点执行)
scheduler.add_cron_job(
    my_task,
    cron_expression="0 9 * * *",
    job_id="morning_task"
)

# 启动 scheduler
scheduler.start()

# ... 你的应用继续运行 ...

# 关闭 scheduler
scheduler.shutdown(wait=True)
```

### 使用预定义任务

```python
from lark_service.scheduler.scheduler import SchedulerService
from lark_service.scheduler.tasks import register_scheduled_tasks

# 创建并启动 scheduler
scheduler = SchedulerService()

# 注册所有预定义的定时任务
register_scheduled_tasks(scheduler)

# 启动 scheduler
scheduler.start()
```

## 预定义任务

Lark Service 包含以下预定义任务:

### 1. 用户信息同步 (`sync_user_info`)

- **执行频率**: 每 6 小时
- **功能**: 从飞书同步用户信息到本地缓存
- **状态**: 占位实现 (待完善)

```python
def sync_user_info_task():
    """同步飞书用户信息"""
    # TODO: 实现用户同步逻辑
    pass
```

### 2. Token 过期检查 (`check_token_expiry`)

- **执行频率**: 每天 9:00 AM 和 9:00 PM
- **功能**: 检查所有应用的 refresh_token 过期情况并发送通知
- **状态**: 占位实现 (待完善)

```python
def check_token_expiry_task():
    """检查 Token 过期并发送通知"""
    # TODO: 实现 token 过期检查逻辑
    pass
```

### 3. 过期 Token 清理 (`cleanup_expired_tokens`)

- **执行频率**: 每天 3:00 AM
- **功能**: 清理已过期的 token 记录
- **状态**: 占位实现 (待完善)

```python
def cleanup_expired_tokens_task():
    """清理过期的 Token"""
    # TODO: 实现 token 清理逻辑
    pass
```

### 4. 健康检查 (`scheduler_health_check`)

- **执行频率**: 每 5 分钟
- **功能**: 验证 scheduler 服务正常运行
- **状态**: ✅ 已实现

```python
def health_check_task():
    """Scheduler 健康检查"""
    logger.debug(f"⚡ Scheduler health check: All systems nominal")
```

## 自定义任务

### 创建自定义任务

```python
from lark_service.scheduler.scheduler import SchedulerService

scheduler = SchedulerService()

# 方式 1: 简单函数
def backup_database():
    print("Backing up database...")

scheduler.add_interval_job(
    backup_database,
    hours=24,  # 每 24 小时执行
    job_id="daily_backup"
)

# 方式 2: 带参数的函数
def send_report(report_type: str):
    print(f"Sending {report_type} report")

scheduler.add_cron_job(
    lambda: send_report("weekly"),
    cron_expression="0 9 * * 1",  # 每周一 9:00 AM
    job_id="weekly_report"
)

scheduler.start()
```

### Interval Job 选项

```python
# 秒级间隔
scheduler.add_interval_job(task, seconds=30, job_id="every_30_seconds")

# 分钟级间隔
scheduler.add_interval_job(task, minutes=5, job_id="every_5_minutes")

# 小时级间隔
scheduler.add_interval_job(task, hours=2, job_id="every_2_hours")

# 天级间隔
scheduler.add_interval_job(task, days=1, job_id="daily")

# 组合使用
scheduler.add_interval_job(
    task,
    hours=1,
    minutes=30,  # 每 1.5 小时
    job_id="every_90_minutes"
)
```

### Cron Job 表达式

```python
# Cron 表达式格式: "分 时 日 月 星期"

# 每天上午 9 点
scheduler.add_cron_job(task, "0 9 * * *", "morning_task")

# 每小时的第 0 分和第 30 分
scheduler.add_cron_job(task, "0,30 * * * *", "twice_hourly")

# 工作日上午 9 点
scheduler.add_cron_job(task, "0 9 * * 1-5", "weekday_morning")

# 每月 1 号凌晨 2 点
scheduler.add_cron_job(task, "0 2 1 * *", "monthly")

# 每周日晚上 11 点
scheduler.add_cron_job(task, "0 23 * * 0", "sunday_night")
```

## 任务管理

### 查看所有任务

```python
jobs = scheduler.get_jobs()
for job in jobs:
    print(f"Job ID: {job.id}")
    print(f"Next run: {job.next_run_time}")
```

### 移除任务

```python
# 移除特定任务
scheduler.remove_job("my_task_id")

# 移除所有任务
scheduler.remove_all_jobs()
```

## Docker 中运行

Scheduler 默认在 Docker 容器中自动启动:

```yaml
# docker-compose.yml
services:
  lark-service:
    environment:
      SCHEDULER_ENABLED: "true"  # 启用 Scheduler (默认)
      PROMETHEUS_ENABLED: "true"  # 启用监控
```

查看 scheduler 日志:

```bash
docker compose logs -f lark-service

# 输出示例:
# ✅ Scheduler started successfully
# ✅ Registered: sync_user_info (every 6 hours)
# ✅ Registered: check_token_expiry (daily at 9 AM and 9 PM)
# ✅ Registered: cleanup_expired_tokens (daily at 3 AM)
# ✅ Registered: scheduler_health_check (every 5 minutes)
# 📅 Total scheduled tasks registered: 4
```

## Prometheus 监控

Scheduler 自动导出以下 Prometheus 指标:

### 任务执行计数器

```promql
# 成功执行的任务总数
scheduled_task_executions_total{task_name="sync_user_info", status="success"}

# 失败执行的任务总数
scheduled_task_executions_total{task_name="sync_user_info", status="error"}
```

### 任务执行时长

```promql
# 任务执行时长 (秒)
scheduled_task_duration_seconds{task_name="sync_user_info"}
```

### Grafana 查询示例

```promql
# 任务执行成功率
rate(scheduled_task_executions_total{status="success"}[5m])
/
rate(scheduled_task_executions_total[5m])

# 任务平均执行时长
avg(scheduled_task_duration_seconds) by (task_name)

# 任务执行失败告警
rate(scheduled_task_executions_total{status="error"}[5m]) > 0.1
```

## 最佳实践

### 1. 错误处理

```python
def robust_task():
    try:
        # 你的任务逻辑
        perform_operation()
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        # 发送告警通知
        send_alert(f"Task failed: {e}")
```

### 2. 超时控制

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError("Task timeout")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def task_with_timeout():
    with timeout(300):  # 5 分钟超时
        perform_long_operation()
```

### 3. 幂等性

确保任务可以安全地重复执行:

```python
def idempotent_task():
    # 检查是否已执行
    if is_already_executed():
        logger.info("Task already executed, skipping")
        return

    # 执行任务
    perform_operation()

    # 标记为已执行
    mark_as_executed()
```

### 4. 分布式锁

在多实例环境中使用分布式锁:

```python
from lark_service.core.lock_manager import DistributedLockManager

def distributed_task():
    lock_manager = DistributedLockManager(pool)

    async with lock_manager.acquire("task_lock", timeout=60):
        # 只有一个实例会执行这里的代码
        perform_exclusive_operation()
```

## 故障排查

### 任务未执行

1. 检查 scheduler 是否启动:
   ```bash
   docker compose logs lark-service | grep "Scheduler started"
   ```

2. 检查任务是否注册:
   ```bash
   docker compose logs lark-service | grep "Registered:"
   ```

3. 检查环境变量:
   ```bash
   docker compose exec lark-service env | grep SCHEDULER_ENABLED
   ```

### 任务执行失败

查看详细错误日志:

```bash
docker compose logs lark-service | grep "Error during"
```

检查 Prometheus 指标:

```bash
curl http://localhost:9090/metrics | grep scheduled_task_executions_total
```

## 下一步

- 📊 [Prometheus 监控配置](../monitoring.md)
- 🔔 [Token 监控服务](./token-monitoring.md)
- 🐳 [生产环境部署](../deployment/PRODUCTION_DEPLOYMENT.md)
