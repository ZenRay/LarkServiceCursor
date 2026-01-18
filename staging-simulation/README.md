# Staging环境本地模拟

本目录提供Docker环境模拟staging环境，用于本地测试和验证。

---

## 📁 目录结构

```
staging-simulation/
├── README.md                    # 本文件
├── docker-compose.yml           # Docker服务配置
├── env.local.template           # 环境变量模板
├── .env.local                   # 本地环境变量（gitignore）
├── .gitignore                   # Git忽略规则
│
├── init-db.sh                   # PostgreSQL初始化脚本
├── prometheus.yml               # Prometheus配置
│
├── scripts/                     # 工具脚本
│   ├── start.sh                 # 一键启动环境
│   ├── check_config.sh          # 配置验证
│   ├── update_test_tokens.sh    # 更新测试资源token
│   ├── verify_test_config.sh    # 验证测试配置
│   ├── backup_docker.sh         # 数据库备份
│   ├── restore_docker.sh        # 数据库恢复
│   └── test-deployment.sh       # 完整部署测试
│
├── backups/                     # 备份目录（gitignore）
└── logs/                        # 日志目录（gitignore）
```

---

## 🚀 快速开始

### 1. 一键启动环境

```bash
cd staging-simulation
bash scripts/start.sh
```

这将自动：
- 启动所有Docker服务
- 等待服务就绪
- 验证数据库配置
- 显示连接信息

### 2. 配置环境变量

```bash
# 复制模板
cp env.local.template .env.local

# 编辑配置（替换示例值为真实值）
vim .env.local

# 验证配置
bash scripts/check_config.sh
```

**必须配置的项**:
- `LARK_APP_ID`: 飞书应用ID
- `LARK_APP_SECRET`: 飞书应用密钥
- `TOKEN_ENCRYPTION_KEY`: Token加密密钥

### 3. 初始化数据库

```bash
cd ..
source .venv-test/bin/activate
export $(cat staging-simulation/.env.local | grep -v '^#' | xargs)
alembic upgrade head
```

### 4. 运行测试

```bash
# 验证测试配置
bash staging-simulation/scripts/verify_test_config.sh

# 运行完整测试
bash staging-simulation/scripts/test-deployment.sh
```

---

## 🐳 Docker服务

### 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| **PostgreSQL** | 5433 | 主数据库 |
| **RabbitMQ** | 5673 (AMQP)<br>15673 (Management) | 消息队列 |
| **Redis** | 6380 | 缓存和分布式锁 |
| **Prometheus** | 9090 | 监控数据采集 |
| **Grafana** | 3000 | 数据可视化 |

### Docker命令

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f postgres

# 停止所有服务
docker compose down

# 清理所有数据（包括volumes）
docker compose down -v
```

---

## 🛠️ 工具脚本说明

### 环境管理

#### `scripts/start.sh`
一键启动Docker环境，自动等待服务就绪。

```bash
bash scripts/start.sh
```

### 配置管理

#### `scripts/check_config.sh`
检查`.env.local`配置完整性。

```bash
cd staging-simulation
bash scripts/check_config.sh
```

#### `scripts/update_test_tokens.sh`
自动添加集成测试资源token到`.env.local`。

```bash
bash scripts/update_test_tokens.sh
```

#### `scripts/verify_test_config.sh`
验证所有测试配置是否就绪。

```bash
bash scripts/verify_test_config.sh
```

### 数据库管理

#### `scripts/backup_docker.sh`
备份PostgreSQL数据库。

```bash
bash scripts/backup_docker.sh
```

备份文件保存在`backups/`目录。

#### `scripts/restore_docker.sh`
从备份恢复数据库。

```bash
bash scripts/restore_docker.sh backups/lark_service_full_20260118_070000.sql.gz
```

### 测试

#### `scripts/test-deployment.sh`
运行完整的部署测试流程。

```bash
bash scripts/test-deployment.sh
```

包含：
1. 环境配置验证
2. 健康检查
3. 数据库迁移
4. 单元测试
5. 集成测试
6. 备份测试
7. 回滚测试

---

## 🔧 服务连接信息

### PostgreSQL

```bash
Host: localhost
Port: 5433
Database: lark_service_staging
User: lark_staging
Password: staging_password_local_only

# 连接命令
docker compose exec postgres psql -U lark_staging -d lark_service_staging
```

### RabbitMQ

```bash
AMQP: amqp://lark_staging:staging_rabbitmq_local_only@localhost:5673/lark-staging
Management UI: http://localhost:15673
User: lark_staging
Password: staging_rabbitmq_local_only
```

### Redis

```bash
Host: localhost
Port: 6380
Password: staging_redis_local_only

# 连接命令
redis-cli -h localhost -p 6380 -a staging_redis_local_only
```

### Prometheus

```bash
UI: http://localhost:9090
```

### Grafana

```bash
UI: http://localhost:3000
User: admin
Password: admin_local_only
```

---

## 📊 集成测试配置

### 配置测试资源Token

如果需要运行完整的Bitable/Sheet/Doc集成测试，需要配置测试资源token：

```bash
# 方法1: 使用脚本自动添加
bash scripts/update_test_tokens.sh

# 方法2: 手动编辑
vim .env.local
```

添加以下配置：

```bash
TEST_BITABLE_APP_TOKEN=your_bitable_token
TEST_BITABLE_TABLE_ID=your_table_id
TEST_SHEET_TOKEN=your_sheet_token
TEST_SHEET_ID=sheet1
TEST_DOC_TOKEN=your_doc_token
```

获取token的方法请参考: [集成测试配置指南](../docs/integration-test-setup-guide.md)

### 运行集成测试

```bash
# 验证配置
bash scripts/verify_test_config.sh

# 运行测试
cd ..
export $(cat staging-simulation/.env.local | grep -v '^#' | xargs)
export POSTGRES_HOST=localhost POSTGRES_PORT=5433
export POSTGRES_DB=lark_service_staging
export POSTGRES_USER=lark_staging
export POSTGRES_PASSWORD=staging_password_local_only

pytest tests/integration/test_bitable_e2e.py -v
pytest tests/integration/test_clouddoc_e2e.py -v
```

---

## ⚠️ 注意事项

### 安全

1. **仅用于本地测试**：不要在生产环境使用这些配置
2. **密码安全**：所有密码都是测试用，不要用于生产
3. **`.env.local`已忽略**：不要提交包含真实凭证的文件

### 端口冲突

如果遇到端口冲突，修改`docker-compose.yml`中的端口映射：

```yaml
ports:
  - "5433:5432"  # 外部:内部
```

### 数据持久化

- Docker volumes存储数据
- `docker compose down -v` 会删除所有数据
- 重要数据请使用`scripts/backup_docker.sh`备份

---

## 🐛 故障排查

### PostgreSQL连接失败

```bash
# 检查容器状态
docker compose ps postgres

# 查看日志
docker compose logs postgres

# 重启容器
docker compose restart postgres

# 验证连接
docker compose exec postgres pg_isready -U lark_staging
```

### RabbitMQ连接失败

```bash
# 检查状态
docker compose ps rabbitmq

# 查看日志
docker compose logs rabbitmq

# 访问管理界面
curl http://localhost:15673
```

### Alembic连接5432端口

确保环境变量中`POSTGRES_PORT=5433`：

```bash
export POSTGRES_PORT=5433
alembic current
```

---

## 🧹 清理环境

### 停止服务但保留数据

```bash
docker compose down
```

### 清理所有数据

```bash
docker compose down -v
rm -rf backups/*.sql*
```

### 重置环境

```bash
docker compose down -v
docker compose up -d
bash scripts/start.sh
```

---

## 📚 相关文档

- [集成测试配置指南](../docs/integration-test-setup-guide.md)
- [集成测试报告](../docs/integration-test-complete-report-2026-01-18.md)
- [Staging部署检查清单](../docs/staging-deployment-checklist.md)
- [部署指南](../docs/deployment.md)

---

**维护者**: Backend Team
**创建日期**: 2026-01-18
**最后更新**: 2026-01-18
**版本**: 1.1
