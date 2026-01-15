# Lark Service 部署指南

**版本**: 1.0.0  
**更新时间**: 2026-01-15

## 1. 部署概述

Lark Service 是一个 Python 库,不是独立服务。它被其他 Python 应用导入使用,因此部署方式取决于调用方应用。

本文档介绍:
1. 依赖服务的部署 (PostgreSQL、RabbitMQ)
2. 在不同环境中使用 Lark Service
3. 配置管理和安全最佳实践

## 2. 依赖服务部署

### 2.1 PostgreSQL 部署

**用途**: 存储 Token 和用户缓存

#### 本地开发 (Docker)

```bash
docker run -d \
  --name lark-postgres \
  -e POSTGRES_DB=lark_service \
  -e POSTGRES_USER=lark \
  -e POSTGRES_PASSWORD=lark_password_123 \
  -p 5432:5432 \
  -v lark_postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# 初始化扩展
docker exec -it lark-postgres psql -U lark -d lark_service -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
```

#### 生产环境 (云服务)

**推荐**: 使用托管数据库服务

- **AWS**: RDS for PostgreSQL
- **Azure**: Azure Database for PostgreSQL
- **GCP**: Cloud SQL for PostgreSQL
- **阿里云**: RDS PostgreSQL

**配置要求**:
- PostgreSQL 15+
- 启用 `pgcrypto` 扩展
- 至少 2GB 内存
- SSD 存储
- 自动备份

**连接示例**:
```bash
# 环境变量配置
POSTGRES_HOST=your-rds-endpoint.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=your_secure_password
```

### 2.2 RabbitMQ 部署

**用途**: 处理交互式卡片回调 (可选,如果不使用卡片功能可以不部署)

#### 本地开发 (Docker)

```bash
docker run -d \
  --name lark-rabbitmq \
  -e RABBITMQ_DEFAULT_USER=lark \
  -e RABBITMQ_DEFAULT_PASS=rabbitmq_password_123 \
  -p 5672:5672 \
  -p 15672:15672 \
  -v lark_rabbitmq_data:/var/lib/rabbitmq \
  rabbitmq:3-management-alpine

# 访问管理界面: http://localhost:15672
# 用户名: lark, 密码: rabbitmq_password_123
```

#### 生产环境 (云服务)

**推荐**: 使用托管消息队列服务

- **AWS**: Amazon MQ for RabbitMQ
- **Azure**: Azure Service Bus
- **GCP**: Cloud Pub/Sub
- **阿里云**: 消息队列 RabbitMQ 版

**配置要求**:
- RabbitMQ 3.11+
- 集群模式 (高可用)
- 持久化存储
- 自动重启

### 2.3 Docker Compose 一键部署

```bash
# 克隆仓库
git clone https://github.com/your-org/lark-service.git
cd lark-service

# 启动所有依赖服务
docker compose up -d postgres rabbitmq

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f postgres
```

## 3. 在不同应用中使用

### 3.1 Django 应用

**安装**:
```bash
# 使用 uv (推荐)
uv pip install lark-service

# 或使用 pip
pip install lark-service
```

**配置** (`settings.py`):
```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# Lark Service 配置
LARK_CONFIG = {
    'POSTGRES_HOST': os.getenv('POSTGRES_HOST', 'localhost'),
    'POSTGRES_PORT': os.getenv('POSTGRES_PORT', '5432'),
    'POSTGRES_DB': os.getenv('POSTGRES_DB', 'lark_service'),
    'POSTGRES_USER': os.getenv('POSTGRES_USER', 'lark'),
    'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD'),
    'LARK_CONFIG_ENCRYPTION_KEY': os.getenv('LARK_CONFIG_ENCRYPTION_KEY'),
}
```

**使用**:
```python
# views.py
from lark_service import LarkServiceClient

def send_notification(request):
    client = LarkServiceClient(app_id="cli_your_app_id")
    
    response = client.messaging.send_text(
        receiver_id=request.user.lark_user_id,
        content="您有新的订单通知!"
    )
    
    return JsonResponse({"message_id": response.data['message_id']})
```

### 3.2 Flask 应用

**安装**:
```bash
# 使用 uv (推荐)
uv pip install lark-service

# 或使用 pip
pip install lark-service
```

**配置** (`config.py`):
```python
# config.py
import os

class Config:
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'lark_service')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'lark')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    LARK_CONFIG_ENCRYPTION_KEY = os.getenv('LARK_CONFIG_ENCRYPTION_KEY')
```

**使用**:
```python
# app.py
from flask import Flask, jsonify
from lark_service import LarkServiceClient

app = Flask(__name__)
app.config.from_object('config.Config')

@app.route('/send-message', methods=['POST'])
def send_message():
    client = LarkServiceClient(app_id="cli_your_app_id")
    
    response = client.messaging.send_text(
        receiver_id="ou_xxxxxxxx",
        content="Hello from Flask!"
    )
    
    return jsonify({"message_id": response.data['message_id']})
```

### 3.3 Apache Airflow

**安装** (在 Airflow 环境中):
```bash
# 使用 uv (推荐)
uv pip install lark-service

# 或使用 pip
pip install lark-service
```

**DAG 示例**:
```python
# dags/etl_to_lark.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from lark_service import LarkServiceClient

def load_to_lark(**context):
    """ETL 完成后将数据加载到飞书"""
    client = LarkServiceClient(app_id="cli_airflow_app")
    
    # 获取 ETL 结果
    etl_result = context['task_instance'].xcom_pull(task_ids='etl_task')
    
    # 发送通知
    client.messaging.send_text(
        receiver_id="ou_team_leader",
        content=f"✅ ETL 完成! 数据量: {etl_result['row_count']}"
    )
    
    # 写入飞书多维表格
    for record in etl_result['data']:
        client.clouddoc.bitable.create_record(
            app_token="bascnxxxxxx",
            table_id="tblxxxxxx",
            fields=record
        )

with DAG(
    'etl_to_lark',
    start_date=datetime(2026, 1, 1),
    schedule_interval='@daily',
) as dag:
    
    load_task = PythonOperator(
        task_id='load_to_lark',
        python_callable=load_to_lark,
        provide_context=True
    )
```

### 3.4 FastAPI 应用

**安装**:
```bash
# 使用 uv (推荐)
uv pip install lark-service

# 或使用 pip
pip install lark-service
```

**使用**:
```python
# main.py
from fastapi import FastAPI
from lark_service import LarkServiceClient

app = FastAPI()
lark_client = LarkServiceClient(app_id="cli_your_app_id")

@app.post("/send-notification")
async def send_notification(user_id: str, message: str):
    response = lark_client.messaging.send_text(
        receiver_id=user_id,
        content=message
    )
    
    return {"message_id": response.data['message_id']}
```

## 4. 环境变量配置

### 4.1 必需环境变量

```bash
# PostgreSQL 配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=your_secure_password

# RabbitMQ 配置 (可选)
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=your_secure_password

# 加密密钥 (必需)
LARK_CONFIG_ENCRYPTION_KEY=your_32_byte_base64_key

# 日志级别
LOG_LEVEL=INFO
```

### 4.2 生成加密密钥

```bash
# 生成 32 字节的 base64 编码密钥
openssl rand -base64 32

# 输出示例: 3yX9kL2mP5nQ8rT1uV4wZ6aB7cD0eF1g==
```

### 4.3 不同环境的配置管理

#### 开发环境

```bash
# .env.dev
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=dev_password
LOG_LEVEL=DEBUG
```

#### 测试环境

```bash
# .env.test
POSTGRES_HOST=test-postgres.internal
POSTGRES_PASSWORD=test_password
LOG_LEVEL=INFO
```

#### 生产环境

**推荐**: 使用密钥管理服务,不使用 .env 文件

- **AWS**: AWS Secrets Manager
- **Azure**: Azure Key Vault
- **GCP**: Secret Manager
- **Kubernetes**: Secrets

```yaml
# Kubernetes Secret 示例
apiVersion: v1
kind: Secret
metadata:
  name: lark-service-secrets
type: Opaque
stringData:
  POSTGRES_HOST: prod-postgres.internal
  POSTGRES_PASSWORD: prod_secure_password
  LARK_CONFIG_ENCRYPTION_KEY: your_production_key
```

## 5. 初始化应用配置

### 5.1 使用 CLI 添加应用

```bash
# 添加第一个应用
python -m lark_service.cli app add \
  --app-id "cli_your_app_id" \
  --app-secret "your_app_secret" \
  --name "生产应用" \
  --description "用于生产环境"

# 查看已添加的应用
python -m lark_service.cli app list

# 输出:
# ┌──────────────────┬──────────┬────────┬─────────────────────┐
# │ App ID           │ Name     │ Status │ Created At          │
# ├──────────────────┼──────────┼────────┼─────────────────────┤
# │ cli_your_app_id  │ 生产应用 │ Active │ 2026-01-15 10:30:00 │
# └──────────────────┴──────────┴────────┴─────────────────────┘
```

### 5.2 使用 Python API 添加应用

```python
from lark_service.core.storage.sqlite_storage import ApplicationManager

# 初始化应用管理器
app_manager = ApplicationManager()

# 添加应用配置
app_manager.create_application(
    app_id="cli_your_app_id",
    app_secret="your_app_secret",
    name="生产应用",
    description="用于生产环境"
)

print("应用配置已添加!")
```

## 6. 数据库迁移

### 6.1 初始化 Alembic

```bash
# 已在项目中配置,无需初始化
# 迁移脚本位于 migrations/versions/
```

### 6.2 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 回滚到上一个版本
alembic downgrade -1
```

### 6.3 创建新迁移

```bash
# 自动生成迁移脚本 (检测模型变更)
alembic revision --autogenerate -m "add new table"

# 手动创建迁移脚本
alembic revision -m "manual migration"
```

## 7. 健康检查

### 7.1 数据库连接检查

```python
from lark_service.core.storage.postgres_storage import PostgresStorage

def check_postgres_health():
    try:
        storage = PostgresStorage()
        # 执行简单查询
        result = storage.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 7.2 RabbitMQ 连接检查

```python
import pika

def check_rabbitmq_health():
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
        )
        connection.close()
        return {"status": "healthy", "rabbitmq": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## 8. 监控和日志

### 8.1 日志配置

```python
# 在应用启动时配置日志
import logging
from lark_service.utils.logger import setup_logger

# 设置日志级别
setup_logger(level=logging.INFO)

# 日志输出到文件
setup_logger(
    level=logging.INFO,
    log_file="/var/log/lark-service/app.log"
)
```

### 8.2 监控指标

**推荐监控项**:
- PostgreSQL 连接数
- RabbitMQ 队列长度
- Token 刷新频率
- API 调用延迟
- 错误率

**工具推荐**:
- Prometheus + Grafana
- Datadog
- New Relic
- CloudWatch (AWS)

## 9. 安全最佳实践

### 9.1 密钥管理

✅ **DO**:
- 使用环境变量或密钥管理服务
- 定期轮换加密密钥
- 使用强密码 (至少 16 字符)
- 限制密钥访问权限

❌ **DON'T**:
- 不要将密钥提交到 Git
- 不要在代码中硬编码密钥
- 不要在日志中输出密钥
- 不要使用默认密码

### 9.2 网络安全

✅ **DO**:
- 使用 TLS/SSL 加密数据库连接
- 限制数据库访问 IP (安全组/防火墙)
- 使用 VPC/私有网络
- 定期更新依赖包

### 9.3 数据库安全

```sql
-- 创建只读用户 (用于监控)
CREATE USER lark_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE lark_service TO lark_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lark_readonly;

-- 创建应用用户 (最小权限)
CREATE USER lark_app WITH PASSWORD 'app_password';
GRANT CONNECT ON DATABASE lark_service TO lark_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lark_app;
```

## 10. 故障排查

### 10.1 常见问题

**问题 1**: Token 获取失败

```
TokenAcquisitionError: Failed to get token: 10014
```

**解决方法**:
1. 检查应用配置是否正确
2. 确认飞书应用状态为"已启用"
3. 检查网络连接

**问题 2**: 数据库连接失败

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方法**:
1. 检查 PostgreSQL 是否运行
2. 验证环境变量配置
3. 检查网络连接和防火墙

**问题 3**: 加密密钥错误

```
cryptography.fernet.InvalidToken
```

**解决方法**:
1. 确认 `LARK_CONFIG_ENCRYPTION_KEY` 正确
2. 检查密钥格式 (base64 编码)
3. 重新生成密钥并重新添加应用配置

### 10.2 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG

# 运行应用
python your_app.py
```

### 10.3 查看日志

```bash
# Docker Compose 日志
docker compose logs -f postgres
docker compose logs -f rabbitmq

# 应用日志
tail -f /var/log/lark-service/app.log
```

## 11. 性能优化

### 11.1 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_tokens_app_id ON tokens(app_id);
CREATE INDEX idx_tokens_expires_at ON tokens(expires_at);

-- 定期清理过期数据
DELETE FROM tokens WHERE expires_at < NOW() - INTERVAL '7 days';
DELETE FROM user_cache WHERE expires_at < NOW();
```

### 11.2 连接池配置

```python
from sqlalchemy import create_engine

engine = create_engine(
    database_url,
    pool_size=10,          # 连接池大小
    max_overflow=20,       # 最大溢出连接
    pool_timeout=30,       # 获取连接超时
    pool_recycle=3600,     # 连接回收时间 (1小时)
)
```

## 12. 备份和恢复

### 12.1 PostgreSQL 备份

```bash
# 备份数据库
pg_dump -U lark -d lark_service > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -U lark -d lark_service < backup_20260115.sql
```

### 12.2 SQLite 备份

```bash
# 备份应用配置数据库
cp config/applications.db config/applications.db.backup_$(date +%Y%m%d)

# 恢复
cp config/applications.db.backup_20260115 config/applications.db
```

---

**维护者**: Lark Service Team  
**最后更新**: 2026-01-15  
**版本**: 1.0.0
