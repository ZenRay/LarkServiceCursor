# 数据库迁移回滚指南

## 概述

本文档说明如何安全地回滚Lark Service的数据库迁移，包括回滚策略、操作步骤和验证方法。

## 迁移版本

| 版本 | 描述 | 创建日期 | 回滚影响 |
|------|------|----------|---------|
| `6fc3f28b87c8` | Initial Schema (tokens, user_cache, user_auth_sessions) | 2026-01-15 | 删除所有表和索引 |

## 回滚策略

### 1. 回滚前检查

**必须执行的检查项**:
```bash
# 1. 确认当前数据库版本
alembic current

# 2. 检查迁移历史
alembic history --verbose

# 3. 备份当前数据库（必须！）
pg_dump -h localhost -U lark_user -d lark_service > backup_before_downgrade_$(date +%Y%m%d_%H%M%S).sql

# 4. 确认备份文件大小
ls -lh backup_before_downgrade_*.sql
```

### 2. 回滚级别

#### 2.1 回滚一个版本
```bash
# 回滚到前一个版本
alembic downgrade -1
```

#### 2.2 回滚到特定版本
```bash
# 回滚到指定版本
alembic downgrade <revision_id>

# 示例: 回滚到初始状态(base)
alembic downgrade base
```

#### 2.3 回滚到base（清空所有迁移）
```bash
# 警告：这将删除所有表！
alembic downgrade base
```

### 3. 回滚后验证

```bash
# 1. 确认当前版本
alembic current

# 2. 检查数据库表结构
psql -h localhost -U lark_user -d lark_service -c "\dt"

# 3. 验证数据完整性
psql -h localhost -U lark_user -d lark_service -c "SELECT COUNT(*) FROM tokens;"
```

## 回滚场景与处理

### 场景1: 迁移失败需要回滚

**症状**: `alembic upgrade head` 执行失败，部分表未创建

**处理步骤**:
```bash
# 1. 备份当前状态
pg_dump -h localhost -U lark_user -d lark_service > backup_failed_migration.sql

# 2. 检查当前版本
alembic current

# 3. 回滚到上一个稳定版本
alembic downgrade -1

# 4. 修复迁移脚本
# 编辑 migrations/versions/*.py

# 5. 重新执行迁移
alembic upgrade head

# 6. 验证
alembic current
psql -h localhost -U lark_user -d lark_service -c "\dt"
```

### 场景2: 发现数据损坏需要回滚

**症状**: 迁移成功但数据出现问题

**处理步骤**:
```bash
# 1. 立即停止应用服务
docker compose stop app

# 2. 备份损坏的数据（用于分析）
pg_dump -h localhost -U lark_user -d lark_service > backup_corrupted_data.sql

# 3. 回滚迁移
alembic downgrade -1

# 4. 恢复备份数据
psql -h localhost -U lark_user -d lark_service < backup_before_upgrade.sql

# 5. 验证数据完整性
# 运行数据验证脚本

# 6. 重启应用
docker compose start app
```

### 场景3: 生产环境紧急回滚

**症状**: 生产环境迁移后出现严重问题

**紧急回滚流程** (RTO目标: 15分钟):
```bash
# 0. 通知团队并启动应急响应
echo "[$(date)] 开始紧急回滚" | tee -a rollback.log

# 1. 立即停止应用（防止数据进一步损坏）
docker compose stop app
echo "[$(date)] 应用已停止" | tee -a rollback.log

# 2. 回滚数据库迁移
alembic downgrade -1
echo "[$(date)] 数据库迁移已回滚" | tee -a rollback.log

# 3. 恢复最近备份（如果数据损坏）
# psql -h localhost -U lark_user -d lark_service < /backups/latest_backup.sql

# 4. 验证数据库状态
alembic current
psql -h localhost -U lark_user -d lark_service -c "\dt"
echo "[$(date)] 数据库状态已验证" | tee -a rollback.log

# 5. 重启应用
docker compose start app
echo "[$(date)] 应用已重启" | tee -a rollback.log

# 6. 健康检查
curl -f http://localhost:8000/health/ready
echo "[$(date)] 健康检查通过" | tee -a rollback.log

# 7. 监控应用日志
docker compose logs -f app
```

## 测试回滚流程

### 测试环境回滚演练

**目的**: 验证回滚流程的正确性，确保团队熟悉操作

**演练脚本** (`scripts/test_migration_rollback.sh`):
```bash
#!/bin/bash
set -e

echo "=== 数据库迁移回滚测试 ==="
echo "开始时间: $(date)"

# 1. 记录初始状态
echo "1. 记录初始状态"
alembic current > /tmp/migration_before.txt
pg_dump -h localhost -U lark -d lark_service > /tmp/backup_test.sql

# 2. 执行升级
echo "2. 执行数据库升级"
alembic upgrade head
alembic current

# 3. 插入测试数据
echo "3. 插入测试数据"
psql -h localhost -U lark -d lark_service -c "
INSERT INTO tokens (app_id, token_type, token_value, expires_at)
VALUES ('test_app', 'test_token', 'test_value', now() + interval '1 hour');
"

# 4. 验证数据存在
echo "4. 验证测试数据"
TEST_COUNT=$(psql -h localhost -U lark -d lark_service -t -c "SELECT COUNT(*) FROM tokens WHERE app_id='test_app';")
echo "测试数据条数: $TEST_COUNT"

# 5. 执行回滚
echo "5. 执行数据库回滚"
alembic downgrade -1
alembic current

# 6. 验证表已删除
echo "6. 验证表已删除"
TABLE_EXISTS=$(psql -h localhost -U lark -d lark_service -t -c "
SELECT EXISTS (
   SELECT FROM information_schema.tables
   WHERE  table_schema = 'public'
   AND    table_name   = 'tokens'
);")
echo "tokens表存在: $TABLE_EXISTS"

# 7. 重新升级
echo "7. 重新升级到最新版本"
alembic upgrade head
alembic current

# 8. 验证测试数据已丢失（正常行为）
echo "8. 验证数据状态"
FINAL_COUNT=$(psql -h localhost -U lark -d lark_service -t -c "SELECT COUNT(*) FROM tokens;" || echo "0")
echo "最终数据条数: $FINAL_COUNT"

echo "=== 测试完成 ==="
echo "结束时间: $(date)"
```

### 回滚测试检查清单

- [ ] 备份可以正常创建
- [ ] `alembic downgrade -1` 执行成功
- [ ] 表和索引被正确删除
- [ ] `alembic current` 显示正确版本
- [ ] 重新升级 `alembic upgrade head` 成功
- [ ] 应用可以正常启动
- [ ] 健康检查通过
- [ ] 日志无ERROR

## 回滚影响分析

### 版本 6fc3f28b87c8 (Initial Schema)

**回滚操作** (`downgrade()`):
1. 删除索引 `idx_auth_session_expires`, `idx_auth_session_state`
2. 删除表 `user_auth_sessions`
3. 删除索引 `idx_user_cache_union_id`, `idx_user_cache_user_id`, `idx_user_cache_expires`
4. 删除表 `user_cache`
5. 删除索引 `idx_tokens_expires`
6. 删除表 `tokens`

**数据影响**:
- ⚠️ **所有Token数据将丢失** (需要重新获取)
- ⚠️ **所有用户缓存将丢失** (需要重新从飞书API获取)
- ⚠️ **所有认证会话将丢失** (用户需要重新登录)

**业务影响**:
- **Token管理**: 应用重启后会自动重新获取Token (影响: 启动时间+1-2秒)
- **用户缓存**: 第一次查询用户信息会调用飞书API (影响: 响应时间+500ms)
- **用户认证**: 正在进行的user_access_token认证流程会失败 (影响: 用户需要重新发起认证)

**恢复时间**:
- RTO (恢复时间目标): **5分钟**
- RPO (恢复点目标): **0** (无数据丢失风险,所有数据可从飞书API重新获取)

## 最佳实践

### 1. 永远先备份
```bash
# 备份脚本模板
#!/bin/bash
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/lark_service_before_downgrade_$TIMESTAMP.sql"

mkdir -p "$BACKUP_DIR"
pg_dump -h localhost -U lark_user -d lark_service > "$BACKUP_FILE"
gzip "$BACKUP_FILE"
echo "备份完成: $BACKUP_FILE.gz"
```

### 2. 在测试环境先演练
- 每个迁移脚本必须在测试环境验证回滚流程
- 记录回滚时间和影响范围
- 更新本文档的回滚影响分析

### 3. 生产环境回滚窗口
- **推荐时间**: 凌晨2-4点(业务低峰期)
- **预留时间**: 回滚操作时间×3 (留出问题处理时间)
- **通知机制**: 提前24小时通知团队和用户

### 4. 回滚后监控
```bash
# 监控检查清单
- [ ] 应用日志无ERROR
- [ ] 数据库连接正常
- [ ] Token自动获取成功
- [ ] API响应时间正常(<500ms)
- [ ] 用户查询功能正常
- [ ] 无大量飞书API调用(缓存重建)
```

## 故障排查

### 问题1: 回滚失败 - 表不存在

**错误信息**:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable)
relation "tokens" does not exist
```

**解决方案**:
```bash
# 1. 检查当前数据库状态
psql -h localhost -U lark_user -d lark_service -c "\dt"

# 2. 检查alembic版本表
psql -h localhost -U lark_user -d lark_service -c "SELECT * FROM alembic_version;"

# 3. 手动清理alembic版本表
psql -h localhost -U lark_user -d lark_service -c "DELETE FROM alembic_version;"

# 4. 重新标记为base状态
alembic stamp base

# 5. 重新执行迁移
alembic upgrade head
```

### 问题2: 回滚后应用无法启动

**症状**: 应用启动时报错 "table tokens does not exist"

**解决方案**:
```bash
# 1. 确认数据库迁移状态
alembic current
# 应该显示: base (没有版本)

# 2. 重新升级到最新版本
alembic upgrade head

# 3. 重启应用
docker compose restart app

# 4. 检查健康状态
curl http://localhost:8000/health/ready
```

### 问题3: 备份文件损坏无法恢复

**预防措施**:
```bash
# 验证备份文件完整性
pg_restore --list backup.sql > /dev/null && echo "备份文件完整" || echo "备份文件损坏"

# 使用多种备份方式
1. SQL dump: pg_dump
2. Custom format: pg_dump -Fc
3. Directory format: pg_dump -Fd
```

## 文档维护

### 更新频率
- 每次新增迁移脚本时,必须更新"迁移版本"表
- 每季度回顾和更新回滚流程
- 每次回滚操作后,记录实际耗时和问题

### 责任人
- **文档维护**: DevOps Team
- **回滚审批**: Tech Lead
- **执行操作**: On-call Engineer

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-18
**下次审查**: 2026-04-18
