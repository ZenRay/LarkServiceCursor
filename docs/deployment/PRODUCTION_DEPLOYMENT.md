# LarkService 生产环境部署指南

本文档提供 LarkService 在生产环境中的完整部署指南。

## 目录

1. [系统要求](#系统要求)
2. [前置准备](#前置准备)
3. [环境配置](#环境配置)
4. [部署步骤](#部署步骤)
5. [监控配置](#监控配置)
6. [运维管理](#运维管理)
7. [故障排查](#故障排查)
8. [安全加固](#安全加固)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 20 GB SSD | 100 GB SSD |
| 网络 | 10 Mbps | 100 Mbps+ |

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.0+

---

## 前置准备

### 1. 安装 Docker 和 Docker Compose

```bash
# 安装 Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose V2
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

### 2. 获取代码

```bash
git clone https://github.com/your-org/lark-service.git
cd lark-service
git checkout main  # 或指定版本标签
```

### 3. 配置飞书应用

在飞书开放平台创建应用并获取:
- **App ID**: 应用凭证的 App ID
- **App Secret**: 应用凭证的 App Secret
- **Verification Token**: 事件订阅的 Verification Token (可选)
- **Encrypt Key**: 事件订阅的 Encrypt Key (可选)

---

## 环境配置

### 1. 创建环境变量文件

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

#### 基础配置

```bash
# 环境标识
ENVIRONMENT=production

# 日志级别
LOG_LEVEL=INFO
```

#### 飞书应用配置

```bash
# 飞书应用凭证
LARK_APP_ID=your_app_id
LARK_APP_SECRET=your_app_secret
LARK_VERIFICATION_TOKEN=your_verification_token  # 可选
LARK_ENCRYPT_KEY=your_encrypt_key  # 可选

# 配置加密密钥(用于加密存储的敏感信息)
LARK_CONFIG_ENCRYPTION_KEY=your_random_32_char_encryption_key
```

**🔐 重要**: `LARK_CONFIG_ENCRYPTION_KEY` 必须是 32 字符的随机字符串,可用以下命令生成:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32)[:32])"
```

#### 数据库配置

```bash
# PostgreSQL 配置
POSTGRES_HOST=lark-postgres
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=your_secure_password_here

# 数据库连接 URL
DATABASE_URL=postgresql://lark_user:your_secure_password_here@lark-postgres:5432/lark_service
```

#### RabbitMQ 配置

```bash
# RabbitMQ 配置
RABBITMQ_HOST=lark-rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=lark_user
RABBITMQ_PASSWORD=your_secure_password_here
RABBITMQ_VHOST=/
```

#### 监控配置

```bash
# Prometheus 配置
PROMETHEUS_ENABLED=true
METRICS_PORT=9090

# Scheduler 配置
SCHEDULER_ENABLED=true
```

#### Token 监控配置

```bash
# Token 过期警告阈值(天)
TOKEN_WARNING_THRESHOLD=30
TOKEN_CRITICAL_THRESHOLD=7

# Token 过期通知管理员
ADMIN_USER_ID=ou_xxxxxxxxxxxx  # 飞书用户 Open ID
```

---

## 部署步骤

### 1. 构建镜像

```bash
# 构建生产镜像
docker compose build
```

### 2. 启动服务

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f lark-service
```

### 3. 验证部署

#### 检查服务健康状态

```bash
# LarkService 健康检查
curl http://localhost:9090/health

# Prometheus 指标
curl http://localhost:9090/metrics

# Grafana (默认账号: admin/admin)
curl http://localhost:3000/api/health
```

#### 验证数据库连接

```bash
docker compose exec postgres psql -U lark_user -d lark_service -c "SELECT 1;"
```

#### 验证 RabbitMQ

访问 http://localhost:15672 (默认账号: lark_user / your_password)

---

## 监控配置

### 1. Prometheus

Prometheus 自动抓取以下端点:
- **LarkService**: http://lark-service:9090/metrics

配置文件位于 `monitoring/prometheus/prometheus.yml`。

### 2. Grafana

#### 访问 Grafana

1. 打开浏览器访问: http://your-server-ip:3000
2. 默认登录: `admin` / `admin`
3. 首次登录后修改密码

#### 导入仪表板

我们提供了预配置的仪表板:

1. **系统概览仪表板**
   - 文件: `monitoring/grafana/dashboards/lark-service-overview.json`
   - 显示: HTTP 请求、Token 状态、API 调用统计

2. **Token 监控仪表板**
   - 文件: `monitoring/grafana/dashboards/lark-service-tokens.json`
   - 显示: Token 过期时间、刷新频率、缓存命中率

3. **Scheduler 任务仪表板**
   - 文件: `monitoring/grafana/dashboards/lark-service-scheduler.json`
   - 显示: 定时任务执行情况、成功率、执行时长

#### 导入步骤

1. 登录 Grafana
2. 点击 `+` -> `Import Dashboard`
3. 上传 JSON 文件或粘贴内容
4. 选择 Prometheus 数据源
5. 点击 `Import`

### 3. 告警规则

告警规则配置在 `monitoring/prometheus/alerts/lark_service_alerts.yml`:

- **Token 即将过期**: Token 剩余有效期 < 7 天
- **Token 刷新失败率高**: 失败率 > 10%
- **定时任务失败**: 任务连续失败 > 3 次
- **服务响应缓慢**: P95 响应时间 > 5s

---

## 运维管理

### 日常维护

#### 查看日志

```bash
# 实时日志
docker compose logs -f lark-service

# 最近 100 行
docker compose logs --tail 100 lark-service

# 指定时间范围
docker compose logs --since 2h lark-service
```

#### 重启服务

```bash
# 重启单个服务
docker compose restart lark-service

# 重启所有服务
docker compose restart
```

#### 更新服务

```bash
# 拉取最新代码
git pull origin main

# 重新构建并部署
docker compose build lark-service
docker compose up -d lark-service
```

### 数据备份

#### PostgreSQL 备份

```bash
# 手动备份
docker compose exec postgres pg_dump -U lark_user lark_service > backup_$(date +%Y%m%d_%H%M%S).sql

# 定时备份(添加到 crontab)
0 2 * * * cd /path/to/lark-service && docker compose exec -T postgres pg_dump -U lark_user lark_service | gzip > /backup/lark_service_$(date +\%Y\%m\%d).sql.gz
```

#### 恢复备份

```bash
# 停止服务
docker compose stop lark-service

# 恢复数据库
docker compose exec -T postgres psql -U lark_user lark_service < backup.sql

# 重启服务
docker compose start lark-service
```

### 日志轮转

配置 Docker 日志大小限制 (编辑 `docker-compose.yml`):

```yaml
services:
  lark-service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 检查日志
docker compose logs lark-service

# 常见原因:
# - 环境变量配置错误
# - 端口被占用
# - 依赖服务(PostgreSQL/RabbitMQ)未就绪
```

#### 2. Token 刷新失败

```bash
# 检查飞书应用凭证是否正确
grep LARK_APP .env

# 查看 Token 刷新日志
docker compose logs lark-service | grep "token_refresh"

# 验证网络连接
docker compose exec lark-service ping open.feishu.cn
```

#### 3. 数据库连接失败

```bash
# 检查数据库状态
docker compose exec postgres pg_isready -U lark_user

# 测试连接
docker compose exec lark-service psql $DATABASE_URL -c "SELECT 1"
```

#### 4. Prometheus 无法抓取指标

```bash
# 验证指标端点
curl http://localhost:9090/metrics

# 检查 Prometheus 配置
docker compose exec prometheus cat /etc/prometheus/prometheus.yml

# 查看 Prometheus 日志
docker compose logs prometheus
```

### 性能优化

#### 数据库优化

```sql
-- 查看慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 创建索引(示例)
CREATE INDEX idx_token_expires_at ON tokens(expires_at);
```

#### Token 缓存优化

调整 Token 缓存策略(在代码中):

```python
# 增加缓存时间(保留更多余量)
TOKEN_CACHE_BUFFER = 300  # 提前 5 分钟刷新
```

---

## 安全加固

### 1. 网络隔离

使用防火墙限制访问:

```bash
# 仅允许必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS (如果配置了反向代理)
sudo ufw enable

# 禁止外部访问内部服务
# PostgreSQL(5432), RabbitMQ(5672) 应仅在 Docker 网络内访问
```

### 2. 使用 HTTPS

配置 Nginx 反向代理:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /metrics {
        # 限制 Prometheus 访问
        allow 172.20.0.0/16;  # Docker 网络
        deny all;
        proxy_pass http://localhost:9090;
    }
}
```

### 3. 密钥管理

- **不要将 `.env` 文件提交到 Git**
- 使用密钥管理服务(如 HashiCorp Vault, AWS Secrets Manager)
- 定期轮换敏感凭证

### 4. 最小权限原则

```bash
# 为服务创建专用用户
sudo useradd -r -s /bin/false lark

# 设置文件权限
sudo chown -R lark:lark /opt/lark-service
chmod 600 .env
```

---

## 扩展部署

### 高可用部署

#### 多实例部署

```yaml
services:
  lark-service:
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
```

#### 负载均衡

使用 Nginx 或 HAProxy:

```nginx
upstream lark_backend {
    least_conn;
    server lark-service-1:8000;
    server lark-service-2:8000;
    server lark-service-3:8000;
}
```

### Kubernetes 部署

参考 `k8s/` 目录下的 YAML 文件(如果提供):

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## 联系与支持

- **文档**: https://lark-service.readthedocs.io
- **Issues**: https://github.com/your-org/lark-service/issues
- **讨论**: https://github.com/your-org/lark-service/discussions

---

## 附录

### A. 端口列表

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|---------|---------|------|
| LarkService | 8000 | 8000 | HTTP API (可选) |
| Metrics | 9090 | 9090 | Prometheus 指标 |
| Prometheus | 9090 | 9091 | Prometheus UI |
| Grafana | 3000 | 3000 | Grafana UI |
| PostgreSQL | 5432 | 5432 | 数据库 |
| RabbitMQ | 5672 | 5672 | AMQP |
| RabbitMQ Mgmt | 15672 | 15672 | 管理界面 |

### B. 环境变量完整列表

参考项目根目录的 `.env.example` 文件。

### C. Docker Compose 服务依赖图

```
lark-service
├── postgres (数据库)
├── rabbitmq (消息队列)
└── (可选) redis (缓存)

prometheus
└── lark-service (抓取指标)

grafana
└── prometheus (数据源)
```

---

**最后更新**: 2026-01-22
**版本**: v0.5.0
