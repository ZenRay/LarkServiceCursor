# Staging环境本地模拟

**目的**: 在本地Docker环境中模拟staging环境，验证部署流程和工具的可用性

**创建日期**: 2026-01-18

---

## 目录结构

```
staging-simulation/
├── README.md                    # 本文件
├── docker-compose.yml           # Docker Compose配置
├── .env.local                   # 本地环境变量
├── nginx/
│   └── nginx.conf              # Nginx配置（如需要）
└── logs/                        # 日志目录
    ├── app.log
    └── nginx.log
```

---

## 快速启动

### 1. 启动所有服务
```bash
cd staging-simulation
docker compose up -d
```

### 2. 查看服务状态
```bash
docker compose ps
```

### 3. 查看日志
```bash
docker compose logs -f
```

### 4. 停止所有服务
```bash
docker compose down
```

### 5. 清理所有数据（包括数据库）
```bash
docker compose down -v
```

---

## 部署验证流程

### 步骤1: 启动依赖服务
```bash
# 启动PostgreSQL和RabbitMQ
docker compose up -d postgres rabbitmq

# 等待服务就绪
sleep 10

# 验证PostgreSQL连接
docker compose exec postgres psql -U lark_staging -d lark_service_staging -c "SELECT version();"

# 验证RabbitMQ
curl http://localhost:15672
```

### 步骤2: 配置环境变量
```bash
# 复制配置模板
cp ../config/staging.env.template .env.local

# 编辑配置（使用本地服务地址）
vim .env.local

# 验证配置
cd ..
source .venv-test/bin/activate
python scripts/validate_env.py staging-simulation/.env.local
```

### 步骤3: 数据库初始化
```bash
# 加载环境变量
export $(cat staging-simulation/.env.local | grep -v '^#' | xargs)

# 执行迁移
alembic upgrade head

# 验证
alembic current
```

### 步骤4: 运行健康检查
```bash
# 运行健康检查脚本
python scripts/staging_health_check.py
```

### 步骤5: 运行测试
```bash
# 单元测试
pytest tests/unit/ -v --cov=src/lark_service

# 集成测试
pytest tests/integration/ -v

# 性能测试
locust -f tests/performance/load_test.py --host=http://localhost:8000
```

### 步骤6: 验证备份恢复
```bash
# 测试备份
bash scripts/backup_database.sh

# 测试恢复
bash scripts/restore_database.sh

# 测试回滚
bash scripts/test_migration_rollback.sh
```

---

## 服务说明

### PostgreSQL
- **端口**: 5432
- **数据库**: lark_service_staging
- **用户**: lark_staging
- **密码**: staging_password_local_only

### RabbitMQ
- **AMQP端口**: 5672
- **管理界面**: http://localhost:15672
- **用户**: lark_staging
- **密码**: staging_rabbitmq_local_only

---

## 注意事项

1. **仅用于本地测试**: 这是模拟环境，不要用于实际生产
2. **密码安全**: 使用的是测试密码，真实staging环境必须使用强密码
3. **数据持久化**: 默认使用Docker volumes，`docker compose down -v`会删除所有数据
4. **端口冲突**: 确保本地5432、5672、15672端口未被占用

---

## 故障排查

### PostgreSQL连接失败
```bash
# 检查容器状态
docker compose ps postgres

# 查看日志
docker compose logs postgres

# 重启
docker compose restart postgres
```

### RabbitMQ连接失败
```bash
# 检查容器状态
docker compose ps rabbitmq

# 查看日志
docker compose logs rabbitmq

# 重启
docker compose restart rabbitmq
```

---

## 清理环境

```bash
# 停止所有服务
docker compose down

# 删除所有数据卷
docker compose down -v

# 删除所有镜像
docker compose down --rmi all

# 清理日志
rm -rf logs/*
```

---

**维护者**: Ray
**最后更新**: 2026-01-18
