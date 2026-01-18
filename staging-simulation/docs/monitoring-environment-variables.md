# Staging模拟环境 - 监控配置说明

本文档说明如何通过环境变量配置Prometheus和Grafana监控系统。

---

## 📋 环境变量列表

### Metrics服务器配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `METRICS_HOST` | `0.0.0.0` | Metrics服务器监听地址 |
| `METRICS_PORT` | `9091` | Metrics服务器端口 |
| `METRICS_ENABLED` | `true` | 是否启用metrics暴露 |

### Prometheus配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `PROMETHEUS_SCRAPE_INTERVAL` | `15s` | 全局抓取间隔 |
| `PROMETHEUS_EVALUATION_INTERVAL` | `15s` | 规则评估间隔 |
| `LARK_SERVICE_METRICS_HOST` | `172.17.0.1` | Lark Service metrics地址 |
| `LARK_SERVICE_METRICS_PORT` | `9091` | Lark Service metrics端口 |
| `LARK_SERVICE_SCRAPE_INTERVAL` | `10s` | Lark Service抓取间隔 |
| `RABBITMQ_HOST` | `rabbitmq` | RabbitMQ服务地址 |
| `RABBITMQ_METRICS_PORT` | `15692` | RabbitMQ metrics端口 |
| `ENVIRONMENT` | `staging-local` | 环境标识 |

### Grafana配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GRAFANA_PORT` | `3000` | Grafana Web端口 |
| `GRAFANA_ADMIN_USER` | `admin` | 管理员用户名 |
| `GRAFANA_ADMIN_PASSWORD` | `admin_local_only` | 管理员密码 |
| `PROMETHEUS_HOST` | `prometheus` | Prometheus服务地址 |
| `PROMETHEUS_PORT` | `9090` | Prometheus端口 |

---

## 🔧 配置方式

### 方式1: 使用.env.local文件

```bash
# 1. 复制模板
cp env.local.template .env.local

# 2. 编辑配置
vim .env.local

# 3. Docker Compose会自动加载
docker compose up -d
```

### 方式2: 环境变量导出

```bash
# 导出环境变量
export LARK_SERVICE_METRICS_HOST=192.168.1.100
export LARK_SERVICE_METRICS_PORT=9091
export GRAFANA_PORT=3001

# 启动服务
docker compose up -d
```

### 方式3: Docker Compose命令行

```bash
docker compose up -d \
  -e LARK_SERVICE_METRICS_HOST=192.168.1.100 \
  -e GRAFANA_PORT=3001
```

---

## 🌍 不同环境配置示例

### 本地开发环境

```bash
# .env.local
ENVIRONMENT=development
LARK_SERVICE_METRICS_HOST=172.17.0.1  # Docker网桥IP
LARK_SERVICE_METRICS_PORT=9091
PROMETHEUS_SCRAPE_INTERVAL=10s
GRAFANA_PORT=3000
```

### Staging环境

```bash
# staging.env
ENVIRONMENT=staging
LARK_SERVICE_METRICS_HOST=lark-service.staging.internal
LARK_SERVICE_METRICS_PORT=9091
PROMETHEUS_SCRAPE_INTERVAL=15s
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=<secure-password>
```

### Production环境

```bash
# production.env
ENVIRONMENT=production
LARK_SERVICE_METRICS_HOST=lark-service.prod.internal
LARK_SERVICE_METRICS_PORT=9091
PROMETHEUS_SCRAPE_INTERVAL=30s
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=<strong-password>
# 生产环境应使用外部Prometheus/Grafana实例
```

---

## 🔍 IP地址配置说明

### Docker网桥IP (本地开发)

在本地使用Docker Compose时，Prometheus运行在容器内，需要访问宿主机上的metrics服务器：

```bash
# 查看Docker网桥IP
ip addr show docker0 | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1

# 通常是
LARK_SERVICE_METRICS_HOST=172.17.0.1
```

### 容器内访问 (容器化部署)

如果应用也运行在Docker容器中：

```bash
# 使用容器名称
LARK_SERVICE_METRICS_HOST=lark-service-app

# 或使用服务发现
LARK_SERVICE_METRICS_HOST=lark-service.local
```

### Kubernetes环境

```bash
# 使用Service名称
LARK_SERVICE_METRICS_HOST=lark-service-svc.default.svc.cluster.local
LARK_SERVICE_METRICS_PORT=9091
```

---

## 🚀 快速验证

### 1. 检查环境变量是否生效

```bash
# 进入Prometheus容器
docker compose exec prometheus env | grep LARK_SERVICE

# 进入Grafana容器
docker compose exec grafana env | grep PROMETHEUS
```

### 2. 验证Prometheus配置

```bash
# 查看Prometheus配置
curl -s http://localhost:9090/api/v1/status/config | python3 -m json.tool

# 查看Targets
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

### 3. 验证Grafana数据源

```bash
# 访问Grafana
open http://localhost:3000

# 检查数据源
curl -s -u admin:admin_local_only http://localhost:3000/api/datasources | python3 -m json.tool
```

---

## 📝 配置变更流程

### 1. 修改配置

```bash
# 编辑.env.local
vim staging-simulation/.env.local

# 修改监控相关配置
LARK_SERVICE_METRICS_HOST=new-host
GRAFANA_PORT=3001
```

### 2. 重启服务

```bash
cd staging-simulation

# 重启Prometheus和Grafana
docker compose restart prometheus grafana

# 或重建服务
docker compose up -d --force-recreate prometheus grafana
```

### 3. 验证变更

```bash
# 检查Prometheus targets
curl http://localhost:9090/api/v1/targets

# 检查Grafana端口
curl http://localhost:3001/api/health
```

---

## ⚠️ 注意事项

### 安全性

1. **生产环境密码**:
   - 不要使用默认的`admin_local_only`
   - 使用强密码或外部认证

2. **Metrics暴露**:
   - 考虑使用认证保护`/metrics`端点
   - 使用防火墙限制访问

3. **环境变量**:
   - 不要将包含敏感信息的`.env`文件提交到Git
   - 使用密钥管理服务（如Vault）

### 性能

1. **抓取间隔**:
   - 开发环境: 10-15秒
   - 生产环境: 30-60秒
   - 根据实际需求调整

2. **数据保留**:
   - Prometheus默认保留15天
   - 通过`--storage.tsdb.retention.time`调整

### 网络

1. **容器网络**:
   - 确保Prometheus能访问metrics端点
   - 检查防火墙规则

2. **DNS解析**:
   - 使用容器名称作为hostname
   - 在docker-compose网络中自动解析

---

## 🔧 故障排查

### Prometheus无法采集数据

```bash
# 1. 检查target配置
docker compose exec prometheus cat /etc/prometheus/prometheus.yml

# 2. 检查环境变量
docker compose exec prometheus env | grep LARK_SERVICE

# 3. 测试连接
docker compose exec prometheus wget -O- http://172.17.0.1:9091/metrics

# 4. 查看日志
docker compose logs prometheus
```

### Grafana无法连接Prometheus

```bash
# 1. 检查数据源配置
docker compose exec grafana cat /etc/grafana/provisioning/datasources/prometheus.yml

# 2. 测试连接
docker compose exec grafana wget -O- http://prometheus:9090/api/v1/query?query=up

# 3. 查看日志
docker compose logs grafana
```

---

## 📚 相关文档

- [Prometheus配置文档](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Grafana数据源配置](https://grafana.com/docs/grafana/latest/datasources/prometheus/)
- [Docker Compose环境变量](https://docs.docker.com/compose/environment-variables/)

---

**维护者**: Backend Team
**创建日期**: 2026-01-18
**最后更新**: 2026-01-18
