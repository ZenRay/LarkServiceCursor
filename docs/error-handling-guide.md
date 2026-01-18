# 异常处理与恢复策略指南

**版本**: 1.0.0
**更新时间**: 2026-01-15

---

## 核心原则

1. **快速失败**: 配置错误立即退出
2. **自动重试**: 网络错误指数退避重试
3. **优雅降级**: 可选组件失败不影响核心功能
4. **事务回滚**: 数据库操作失败自动回滚

## 启动失败处理 (CHK052)

### 退出码规范
- 0: 正常退出
- 1: 配置错误
- 2: 数据库错误
- 3: 依赖服务错误

### 配置加载失败
```python
if not encryption_key:
    logger.critical("LARK_CONFIG_ENCRYPTION_KEY not set")
    sys.exit(1)  # 立即失败
```

### 数据库连接失败
- 重试 3 次 (指数退避: 2s, 4s, 8s)
- 失败后退出码 2
- 提供详细诊断信息

### 服务降级策略
- 核心组件(Token管理): 必需,失败退出
- 可选组件(RabbitMQ/缓存): 失败降级运行
- 健康检查返回降级状态

## 数据库初始化回滚 (CHK058)

### Alembic 迁移失败
- 每个迁移一个事务
- 失败自动回滚
- 数据库状态不变

### SQLite 初始化失败
1. 创建临时数据库
2. 验证表结构
3. 替换旧数据库
4. 失败则恢复备份

## 运行时错误处理

### API 调用错误
- 参数错误: 不重试,立即失败
- 限流(429): 延迟30秒重试
- 网络超时: 指数退避重试3次
- Token 失效: 自动刷新并重试

### 数据库错误
- 唯一约束违反: 不重试
- 连接错误: 重试3次
- 事务冲突: 自动回滚,重试1次(间隔2秒) - **FR-119**
- 所有错误都回滚事务

**事务处理示例** (FR-119):

```python
def write_with_retry(session, data, max_retries=1):
    for attempt in range(max_retries + 1):
        try:
            with session.begin():
                session.add(data)
                session.commit()
                return True
        except IntegrityError:
            session.rollback()
            raise  # 唯一约束冲突,不重试
        except (OperationalError, TimeoutError):
            session.rollback()
            if attempt < max_retries:
                time.sleep(2)  # 间隔2秒重试
            else:
                raise
```

## 自动恢复场景

| 场景 | 恢复策略 | 恢复时间 |
|------|---------|---------|
| Token 过期 | 自动刷新 | <1秒 |
| 网络超时 | 重试3次 | <10秒 |
| 数据库断开 | 重新连接 | <5秒 |
| 限流 | 延迟重试 | 30秒 |

## 检查清单

- [ ] 配置错误立即退出
- [ ] 数据库失败会重试和回滚
- [ ] 依赖失败会降级
- [ ] 错误日志包含上下文
- [ ] 关键错误触发告警
