# 数据库时区配置指南

## 问题背景

在分布式环境中,应用服务器和数据库服务器可能使用不同的时区,导致时间计算错误。

## 当前架构

### 时间源策略

**应用层统一时间源**:
- Token 创建时间 (`created_at`): Python `datetime.now()`
- Token 过期时间 (`expires_at`): Python `datetime.now() + timedelta()`
- 所有时间计算在应用层完成

### 优势

1. **一致性**: 所有时间使用相同的时间源
2. **可测试性**: 易于 mock 和测试
3. **业务逻辑内聚**: 时间计算逻辑都在应用层

---

## PostgreSQL 配置

### 1. 设置数据库时区

```sql
-- 查看当前时区
SHOW timezone;

-- 设置为 UTC (推荐)
ALTER DATABASE lark_service SET timezone TO 'UTC';

-- 或设置为本地时区
ALTER DATABASE lark_service SET timezone TO 'Asia/Shanghai';
```

### 2. 连接字符串配置

在 `get_postgres_url()` 中添加时区参数:

```python
def get_postgres_url(self) -> str:
    """Get PostgreSQL connection URL with timezone."""
    return (
        f"postgresql://{self.postgres_user}:{self.postgres_password}"
        f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        f"?timezone=UTC"  # ← 显式指定时区
    )
```

### 3. SQLAlchemy 配置

```python
from sqlalchemy import create_engine

engine = create_engine(
    postgres_url,
    connect_args={
        "options": "-c timezone=utc"  # PostgreSQL 特定配置
    }
)
```

---

## 最佳实践

### 1. 使用 UTC 时间

**推荐**: 数据库和应用都使用 UTC

```python
from datetime import datetime, timezone

# 使用 UTC 时间
now_utc = datetime.now(timezone.utc)
expires_at = now_utc + timedelta(hours=2)

# 存储时去掉时区信息 (数据库已配置为 UTC)
token_storage.set_token(
    app_id=app_id,
    token_type=token_type,
    token_value=token_value,
    expires_at=expires_at.replace(tzinfo=None),
    created_at=now_utc.replace(tzinfo=None),
)
```

### 2. 避免混用时区

**错误示例**:
```python
# ❌ 混用不同时区
created_at = datetime.now()  # 本地时区
expires_at = datetime.utcnow()  # UTC
```

**正确示例**:
```python
# ✅ 统一使用本地时区
now = datetime.now()
created_at = now
expires_at = now + timedelta(hours=2)

# ✅ 或统一使用 UTC
now = datetime.now(timezone.utc)
created_at = now.replace(tzinfo=None)
expires_at = (now + timedelta(hours=2)).replace(tzinfo=None)
```

### 3. 环境变量配置

在 `.env` 文件中添加:

```bash
# 数据库时区配置
POSTGRES_TIMEZONE=UTC
# 或
POSTGRES_TIMEZONE=Asia/Shanghai

# 应用时区 (如果需要)
TZ=UTC
```

### 4. Docker 环境配置

在 `docker-compose.yml` 中:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: lark_service
      POSTGRES_USER: lark
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      TZ: UTC  # ← 设置容器时区
      PGTZ: UTC  # ← 设置 PostgreSQL 时区
    command:
      - "postgres"
      - "-c"
      - "timezone=UTC"  # ← 启动参数指定时区

  app:
    build: .
    environment:
      TZ: UTC  # ← 应用容器也使用 UTC
```

---

## 验证配置

### 1. 检查数据库时区

```sql
-- 连接到数据库
psql -h localhost -U lark -d lark_service

-- 查看时区配置
SHOW timezone;

-- 查看当前数据库时间
SELECT now();
SELECT current_timestamp;
```

### 2. 检查应用时区

```python
from datetime import datetime
import time

print(f"System timezone: {time.tzname}")
print(f"Current time: {datetime.now()}")
print(f"UTC time: {datetime.utcnow()}")
```

### 3. 验证一致性

```python
import time
from datetime import datetime
from sqlalchemy import text

# 应用时间
app_time = datetime.now()
print(f"App time: {app_time}")

# 数据库时间
with engine.connect() as conn:
    result = conn.execute(text("SELECT now()"))
    db_time = result.scalar()
    print(f"DB time: {db_time}")

# 计算差异
diff = abs((app_time - db_time.replace(tzinfo=None)).total_seconds())
print(f"Time difference: {diff:.3f} seconds")

# 应该小于 1 秒
assert diff < 1.0, f"Time sync issue: {diff}s difference"
```

---

## 故障排查

### 问题 1: 时间相差 8 小时

**原因**: 时区不一致 (UTC vs Asia/Shanghai)

**解决**:
```bash
# 检查系统时区
timedatectl

# 统一使用 UTC
sudo timedatectl set-timezone UTC

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

### 问题 2: DST (夏令时) 问题

**原因**: 某些时区有夏令时调整

**解决**: 使用 UTC 避免夏令时问题

### 问题 3: 容器时间不同步

**原因**: Docker 容器使用主机时间,但可能有偏差

**解决**:
```yaml
# docker-compose.yml
services:
  app:
    volumes:
      - /etc/localtime:/etc/localtime:ro  # 同步主机时间
      - /etc/timezone:/etc/timezone:ro
```

---

## 监控和告警

### 1. 添加时间同步检查

```python
# src/lark_service/core/health.py
def check_time_sync(engine, threshold_seconds: float = 5.0) -> bool:
    """Check if app and DB time are synchronized."""
    from sqlalchemy import text
    from datetime import datetime
    
    app_time = datetime.now()
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT now()"))
        db_time = result.scalar()
    
    diff = abs((app_time - db_time.replace(tzinfo=None)).total_seconds())
    
    if diff > threshold_seconds:
        logger.warning(
            "Time sync issue detected",
            extra={
                "app_time": app_time.isoformat(),
                "db_time": db_time.isoformat(),
                "diff_seconds": diff,
            }
        )
        return False
    
    return True
```

### 2. 启动时检查

```python
# src/lark_service/cli/app.py
@app.command()
def check_health():
    """Check system health including time sync."""
    config = Config.load_from_env()
    token_storage = TokenStorageService(config.get_postgres_url())
    
    if not check_time_sync(token_storage.engine):
        console.print("[red]✗[/red] Time sync issue detected!")
        sys.exit(1)
    
    console.print("[green]✓[/green] Time sync OK")
```

---

## 总结

### 当前架构 (推荐)

- ✅ **应用层统一时间源**: 使用 `datetime.now()`
- ✅ **数据库时区配置**: 设置为 UTC 或与应用一致
- ✅ **显式设置 created_at**: 不依赖数据库默认值
- ✅ **添加时间同步检查**: 启动时验证

### 为什么不使用数据库时间?

1. **业务逻辑在应用层**: Token 过期时间由应用计算
2. **简化测试**: 易于 mock 和单元测试
3. **避免跨层转换**: 减少时间源切换的复杂度
4. **性能更好**: 减少数据库往返查询

### 配置清单

- [ ] 设置 PostgreSQL 时区为 UTC
- [ ] 配置连接字符串包含时区参数
- [ ] 统一应用和数据库时区
- [ ] 添加启动时时间同步检查
- [ ] 在 Docker 环境中配置时区
- [ ] 添加监控告警

---

**更新时间**: 2026-01-15  
**相关文档**: 
- [错误处理指南](./error-handling-guide.md)
- [可观测性指南](./observability-guide.md)
