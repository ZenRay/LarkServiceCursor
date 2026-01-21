# WebSocket User Authorization - Deployment Guide

**Version**: v0.2.0
**Last Updated**: 2026-01-21
**Status**: ✅ 生产就绪
**Target Audience**: DevOps, SRE, System Administrators

---

## 📋 Overview

本指南介绍如何在生产环境部署 Lark Service WebSocket 用户授权功能,包括:

- ✅ 基础设施准备和配置
- ✅ 应用部署和启动
- ✅ 监控和告警配置
- ✅ 故障排查和维护

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│  Feishu Server  │
│  (WebSocket)    │
└────────┬────────┘
         │ Long Connection
         │
┌────────▼────────────────────────────────┐
│        Lark Service Application         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │   WebSocket  │  │  Auth Session   │ │
│  │    Client    │──│    Manager      │ │
│  └──────────────┘  └─────────────────┘ │
│                                         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │    Card      │  │    aPaaS        │ │
│  │   Handler    │──│    Client       │ │
│  └──────────────┘  └─────────────────┘ │
└─────────┬──────────────────┬───────────┘
          │                  │
┌─────────▼────────┐ ┌──────▼──────────┐
│   PostgreSQL     │ │   Prometheus    │
│   (Auth Data)    │ │   (Metrics)     │
└──────────────────┘ └─────────────────┘
```

---

## 🔧 Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, or equivalent)
- **Python**: 3.12+
- **Memory**: 512MB minimum, 1GB recommended
- **CPU**: 1 core minimum, 2 cores recommended
- **Disk**: 10GB minimum for logs and database

### Required Services

| Service | Version | Purpose |
|---------|---------|---------|
| PostgreSQL | 13+ | Auth sessions and token storage |
| Prometheus | 2.30+ | Metrics collection |
| Grafana | 9.5+ | Monitoring dashboards (optional) |

---

## 📦 Deployment Steps

### 1. Prepare Infrastructure

#### 1.1 PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE lark_service;
CREATE USER lark_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE lark_service TO lark_user;
EOF

# Test connection
psql -h localhost -U lark_user -d lark_service -c "SELECT version();"
```

#### 1.2 Python Environment

```bash
# Install Python 3.12+
sudo apt install python3.12 python3.12-venv python3-pip

# Create virtual environment
python3.12 -m venv /opt/lark-service/venv
source /opt/lark-service/venv/bin/activate

# Install Lark Service
pip install lark-service==0.2.0
```

### 2. Configuration

#### 2.1 Environment Variables

Create `/opt/lark-service/.env`:

```bash
# Feishu App Credentials
APP_ID=cli_a1b2c3d4e5f6g7h8
APP_SECRET=your_app_secret_here

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark_user
POSTGRES_PASSWORD=secure_password_here

# Encryption Keys
LARK_CONFIG_ENCRYPTION_KEY=$(openssl rand -hex 32)
LARK_TOKEN_ENCRYPTION_KEY=$(openssl rand -hex 32)

# WebSocket Configuration
WEBSOCKET_MAX_RECONNECT_RETRIES=10
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_FALLBACK_TO_HTTP=true

# Auth Configuration
AUTH_SESSION_EXPIRY_SECONDS=600
AUTH_TOKEN_REFRESH_THRESHOLD=0.8
AUTH_REQUEST_RATE_LIMIT=5

# User Info Sync (optional)
USER_INFO_SYNC_ENABLED=false
USER_INFO_SYNC_SCHEDULE="0 2 * * *"

# Logging
LOG_LEVEL=INFO
LOG_JSON_FORMAT=true

# Monitoring
PROMETHEUS_PORT=8000
```

#### 2.2 Database Migration

```bash
# Navigate to application directory
cd /opt/lark-service

# Run Alembic migrations
source venv/bin/activate
alembic upgrade head

# Verify migration
alembic current
# Expected output: a8b9c0d1e2f3 (head)
```

### 3. Application Deployment

#### 3.1 Systemd Service

Create `/etc/systemd/system/lark-service.service`:

```ini
[Unit]
Description=Lark Service WebSocket User Authorization
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=lark-service
Group=lark-service
WorkingDirectory=/opt/lark-service
Environment="PATH=/opt/lark-service/venv/bin"
EnvironmentFile=/opt/lark-service/.env

# Main application process
ExecStart=/opt/lark-service/venv/bin/python -m lark_service.main

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lark-service

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/lark-service/logs

[Install]
WantedBy=multi-user.target
```

#### 3.2 Start Service

```bash
# Create service user
sudo useradd -r -s /bin/false lark-service
sudo chown -R lark-service:lark-service /opt/lark-service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable lark-service
sudo systemctl start lark-service

# Check status
sudo systemctl status lark-service

# View logs
sudo journalctl -u lark-service -f
```

### 4. Monitoring Setup

#### 4.1 Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'lark-service'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    scrape_timeout: 10s
```

Reload Prometheus:

```bash
sudo systemctl reload prometheus
```

#### 4.2 Prometheus Alert Rules

Copy alert rules:

```bash
sudo cp docs/monitoring/alert-rules.yaml /etc/prometheus/rules/lark-service.yaml
```

Add to `prometheus.yml`:

```yaml
rule_files:
  - /etc/prometheus/rules/*.yaml
```

#### 4.3 Grafana Dashboard

1. Login to Grafana (http://localhost:3000)
2. Navigate to **Dashboards** → **Import**
3. Upload `docs/monitoring/grafana-dashboard.json`
4. Select Prometheus data source
5. Click **Import**

---

## 🔍 Health Checks

### Application Health

```bash
# Check service status
sudo systemctl status lark-service

# Check WebSocket connection
curl -s http://localhost:8000/metrics | grep websocket_connection_status
# Expected: lark_service_websocket_connection_status{app_id="..."} 1

# Check database connection
psql -h localhost -U lark_user -d lark_service -c "SELECT COUNT(*) FROM user_auth_sessions;"
```

### Monitoring Health

```bash
# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="lark-service")'

# Check metrics endpoint
curl -s http://localhost:8000/metrics | grep lark_service | head -20
```

---

## 🚨 Troubleshooting

### WebSocket Connection Issues

**Problem**: WebSocket connection fails to establish

**Symptoms**:
```
lark_service_websocket_connection_status 0
```

**Solutions**:

1. Check network connectivity:
```bash
curl -v https://open.feishu.cn/open-apis/ws/v1/connect
```

2. Verify APP_ID and APP_SECRET:
```bash
# Check environment variables
sudo systemctl show lark-service --property=Environment
```

3. Check firewall rules:
```bash
sudo ufw status
# Ensure outbound HTTPS (443) is allowed
```

4. Review logs:
```bash
sudo journalctl -u lark-service -n 100 --no-pager | grep -i websocket
```

### High Auth Failure Rate

**Problem**: Authentication success rate < 95%

**Symptoms**:
```
Prometheus alert: AuthSuccessRateLow
```

**Solutions**:

1. Check failure reasons:
```bash
curl -s http://localhost:8000/metrics | grep auth_failure_total
```

2. Common reasons and fixes:

| Reason | Cause | Solution |
|--------|-------|----------|
| `code_expired` | Authorization code expired (>10min) | Reduce session expiry time |
| `missing_code` | User clicked wrong button | Fix card UI |
| `user_rejected` | User declined authorization | User education |
| `unknown_error` | Network/API issues | Check logs, retry |

3. Review session expiry:
```bash
# Check AUTH_SESSION_EXPIRY_SECONDS
grep AUTH_SESSION_EXPIRY_SECONDS /opt/lark-service/.env
# Recommended: 300-600 seconds
```

### Database Performance Issues

**Problem**: Slow query performance

**Symptoms**:
- High auth duration (p95 > 15s)
- Database connection timeouts

**Solutions**:

1. Check missing indexes:
```sql
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE tablename = 'user_auth_sessions';
```

Expected indexes:
- `idx_auth_session_user` (app_id, user_id)
- `idx_auth_session_token_expires` (token_expires_at)
- `idx_auth_session_open_id` (open_id)

2. Run VACUUM:
```sql
VACUUM ANALYZE user_auth_sessions;
```

3. Check connection pool:
```bash
# Monitor active connections
psql -h localhost -U lark_user -d lark_service -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname = 'lark_service';"
```

### Token Refresh Failures

**Problem**: High token refresh failure rate

**Symptoms**:
```
token_refresh_total{outcome="failure"} increasing
```

**Solutions**:

1. Check Feishu API status:
```bash
curl -v https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
```

2. Verify refresh token availability:
```sql
SELECT COUNT(*) FROM user_auth_sessions
WHERE state = 'completed' AND refresh_token IS NOT NULL;
```

3. Review API rate limits:
- Check if hitting Feishu API rate limits
- Consider implementing backoff/retry

---

## 🔄 Maintenance

### Session Cleanup

Schedule periodic cleanup of expired sessions:

```bash
# Add to crontab
crontab -e

# Run cleanup every hour
0 * * * * cd /opt/lark-service && venv/bin/python -c \
  "from lark_service.auth.session_manager import AuthSessionManager; \
   from lark_service.core.database import get_db; \
   db = next(get_db()); \
   manager = AuthSessionManager(db); \
   count = manager.cleanup_expired_sessions(); \
   print(f'Cleaned up {count} sessions')"
```

### Log Rotation

Configure logrotate:

```bash
sudo tee /etc/logrotate.d/lark-service << EOF
/var/log/lark-service/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 lark-service lark-service
    postrotate
        systemctl reload lark-service > /dev/null 2>&1 || true
    endscript
}
EOF
```

### Database Backup

```bash
#!/bin/bash
# /opt/lark-service/scripts/backup-db.sh

BACKUP_DIR="/opt/lark-service/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/lark_service_$DATE.sql"

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -h localhost -U lark_user lark_service > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

Add to crontab:
```bash
# Daily backup at 3 AM
0 3 * * * /opt/lark-service/scripts/backup-db.sh
```

---

## 🔐 Security Best Practices

### 1. Secrets Management

**DO NOT** store secrets in plain text. Use one of:

- **Environment variables** (systemd EnvironmentFile)
- **Kubernetes Secrets** (if using K8s)
- **AWS Secrets Manager** / **Azure Key Vault** (cloud)
- **HashiCorp Vault** (self-hosted)

### 2. Network Security

```bash
# Firewall rules
sudo ufw allow 8000/tcp  # Prometheus metrics (internal only)
sudo ufw deny from any to any port 5432  # PostgreSQL (local only)

# Or use iptables
sudo iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### 3. Database Security

```sql
-- Revoke public access
REVOKE ALL ON DATABASE lark_service FROM PUBLIC;

-- Grant minimal privileges
GRANT CONNECT ON DATABASE lark_service TO lark_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lark_user;

-- Enable SSL
-- Edit postgresql.conf: ssl = on
-- Edit pg_hba.conf: hostssl all all 0.0.0.0/0 md5
```

### 4. Application Security

- ✅ Enable log sanitization (`sanitize_log_data()` already implemented)
- ✅ Use JSON logging in production (`LOG_JSON_FORMAT=true`)
- ✅ Rotate encryption keys periodically (every 90 days)
- ✅ Monitor failed auth attempts (use Prometheus alerts)

---

## 📊 Monitoring Checklist

- [ ] Prometheus scraping Lark Service metrics
- [ ] Grafana dashboard imported and accessible
- [ ] Alert rules configured in Prometheus
- [ ] Alert notifications configured (Slack/Email/PagerDuty)
- [ ] WebSocket connection status monitoring
- [ ] Auth success rate monitoring (>95%)
- [ ] Token refresh monitoring
- [ ] Database performance monitoring
- [ ] Log aggregation setup (ELK/Loki)

---

## 🚀 Scaling Considerations

### Horizontal Scaling

Lark Service can be scaled horizontally with some considerations:

1. **WebSocket Connection**: Each instance maintains its own WebSocket connection
   - Feishu allows multiple concurrent connections per app
   - Use load balancer for HTTP endpoints only

2. **Database**: Use connection pooling
   ```python
   # In config
   SQLALCHEMY_POOL_SIZE=10
   SQLALCHEMY_MAX_OVERFLOW=20
   ```

3. **Session Affinity**: Not required (stateless after auth completion)

### Load Balancing

```nginx
# Nginx configuration
upstream lark_service {
    server lark-service-1:8000;
    server lark-service-2:8000;
    server lark-service-3:8000;
}

server {
    listen 80;
    server_name lark-service.example.com;

    location /metrics {
        proxy_pass http://lark_service;
        allow 10.0.0.0/8;  # Internal only
        deny all;
    }
}
```

---

## 📞 Support

For issues and questions:

- **Documentation**: `specs/002-websocket-user-auth/`
- **GitHub Issues**: https://github.com/your-org/lark-service/issues
- **Monitoring**: Check Grafana dashboard first
- **Logs**: `sudo journalctl -u lark-service -f`

---

**Deployment Guide Version**: 1.0
**Compatible with**: Lark Service v0.2.0+
**Last Reviewed**: 2026-01-20
