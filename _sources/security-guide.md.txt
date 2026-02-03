# 安全配置指南

**最后更新**: 2026-01-15
**版本**: 2.0
**状态**: Production Ready

---

## 🚨 安全需求清单 (Blocker)

在部署到生产环境前,**必须**完成以下安全检查:

### 配置安全 (MUST)

- [ ] ✅ **FR-077**: 所有敏感配置仅通过环境变量注入,代码中无硬编码
- [ ] ✅ **FR-078**: 加密密钥符合 Fernet 规范(32字节,256 bit)
- [ ] ✅ **FR-079**: SQLite 配置文件权限设置为 0600
- [ ] ✅ **FR-080**: 配置文件路径为 `./config/applications.db`
- [ ] ✅ **FR-081**: 配置按敏感度分类(public/internal/secret)

### 密钥管理 (MUST)

- [ ] ✅ **FR-082**: App Secret 使用 Fernet 加密存储
- [ ] ✅ **FR-083**: 提供密钥轮换 CLI 命令
- [ ] ✅ **FR-084**: 日志中密钥脱敏(前4位+`****`)
- [ ] ✅ **FR-085**: Token 在 PostgreSQL 中加密存储

### 依赖安全 (MUST)

- [ ] ✅ **FR-086**: 使用 `safety` 扫描依赖漏洞
- [ ] ✅ **FR-087**: 每月检查依赖更新,修复高危漏洞
- [ ] ✅ **FR-088**: 依赖版本锁定(使用 `==`)

### 容器安全 (MUST)

- [ ] ✅ **FR-089**: 使用官方 Python 镜像
- [ ] ✅ **FR-090**: CI 中集成镜像安全扫描
- [ ] ✅ **FR-091**: 容器以非 root 用户运行(UID ≥ 1000)
- [ ] ✅ **FR-092**: 仅暴露必需端口

### 环境隔离 (MUST)

- [ ] ✅ **FR-093**: 开发/生产环境使用不同密钥
- [ ] ✅ **FR-094**: 生产 `.env` 文件权限为 0600
- [ ] ✅ **FR-095**: 多租户 Token 完全隔离

---

## 🔐 加密密钥管理

### 密钥作用

`LARK_CONFIG_ENCRYPTION_KEY` 用于加密/解密存储在 SQLite 数据库中的 Feishu 应用密钥 (`app_secret`)。

**加密流程**:
```
用户输入 app_secret (明文)
    ↓
使用 Fernet 对称加密
    ↓
存储到数据库 (密文)
    ↓
使用时解密还原
```

### 为什么需要加密?

1. **数据库泄露防护**: 即使数据库文件被盗,攻击者也无法直接读取敏感信息
2. **备份安全**: 数据库备份可以更安全地存储和传输
3. **多人协作**: 数据库文件可以共享,但密钥单独管理
4. **合规要求**: 满足数据安全和隐私保护规范

---

## 🚀 部署配置

### 开发环境

#### 1. 生成加密密钥

```bash
# 生成新的 Fernet 密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 2. 配置 .env 文件

```bash
# .env (本地开发环境)
LARK_CONFIG_ENCRYPTION_KEY=your-generated-key-here
LARK_CONFIG_DB_PATH=data/lark_config.db

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=your-postgres-password

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=your-rabbitmq-password
```

#### 3. 重要提醒

⚠️ **绝对不要将 `.env` 文件提交到 Git!**

```bash
# 确认 .env 在 .gitignore 中
cat .gitignore | grep .env

# 如果不在,添加它
echo ".env" >> .gitignore
```

---

### 生产环境

#### 方案 A: 系统环境变量 (推荐)

**优点**: 简单、安全、不依赖文件

```bash
# 在服务器上设置
export LARK_CONFIG_ENCRYPTION_KEY="your-production-key"

# 或在 ~/.bashrc 或 ~/.profile 中
echo 'export LARK_CONFIG_ENCRYPTION_KEY="your-production-key"' >> ~/.bashrc
source ~/.bashrc
```

**Systemd Service 配置**:
```ini
[Unit]
Description=Lark Service
After=network.target

[Service]
Type=simple
User=lark-service
WorkingDirectory=/opt/lark-service
Environment="LARK_CONFIG_ENCRYPTION_KEY=your-production-key"
Environment="POSTGRES_HOST=db.example.com"
Environment="POSTGRES_PASSWORD=secure-password"
ExecStart=/usr/bin/python -m lark_service.cli
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 方案 B: Docker Secrets

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  lark-service:
    image: lark-service:latest
    environment:
      - LARK_CONFIG_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
      - POSTGRES_HOST=postgres
    secrets:
      - encryption_key
    volumes:
      - ./data:/app/data

secrets:
  encryption_key:
    external: true
```

**创建 Secret**:
```bash
# 创建 Docker secret
echo "your-production-key" | docker secret create encryption_key -

# 部署
docker stack deploy -c docker-compose.yml lark-service
```

#### 方案 C: Kubernetes Secrets

**创建 Secret**:
```bash
# 从文件创建
kubectl create secret generic lark-service-secrets \
  --from-literal=encryption-key='your-production-key' \
  --from-literal=postgres-password='your-db-password'
```

**Deployment 配置**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lark-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: lark-service
        image: lark-service:latest
        env:
        - name: LARK_CONFIG_ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: lark-service-secrets
              key: encryption-key
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: lark-service-secrets
              key: postgres-password
```

#### 方案 D: 云服务密钥管理

**AWS Secrets Manager**:
```python
import boto3
import os
from botocore.exceptions import ClientError

def get_secret():
    secret_name = "lark-service/encryption-key"
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# 在应用启动时设置
os.environ['LARK_CONFIG_ENCRYPTION_KEY'] = get_secret()
```

**Azure Key Vault**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_secret():
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url="https://your-vault.vault.azure.net/",
        credential=credential
    )

    secret = client.get_secret("lark-encryption-key")
    return secret.value

os.environ['LARK_CONFIG_ENCRYPTION_KEY'] = get_secret()
```

---

## 🔄 密钥轮换

### 何时需要轮换密钥?

1. 定期轮换 (建议每 90 天)
2. 怀疑密钥泄露
3. 员工离职
4. 安全审计要求

### 轮换步骤

```bash
# 1. 生成新密钥
NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. 导出所有应用配置 (使用旧密钥)
lark-service-cli app list --json > apps_backup.json

# 3. 备份数据库
cp data/lark_config.db data/lark_config.db.backup

# 4. 使用新密钥重新加密
# (需要实现密钥轮换工具)
python scripts/rotate_encryption_key.py \
  --old-key "$OLD_KEY" \
  --new-key "$NEW_KEY" \
  --db-path data/lark_config.db

# 5. 更新环境变量
export LARK_CONFIG_ENCRYPTION_KEY="$NEW_KEY"

# 6. 验证
lark-service-cli app list
```

---

## 📁 文件权限管理

### SQLite 配置文件权限 (FR-079, FR-080)

**默认路径**: `./config/applications.db` (相对于项目根目录)

**权限设置** (MUST):
```bash
# 设置文件权限为 0600 (仅所有者读写)
chmod 600 ./config/applications.db

# 验证权限
ls -l ./config/applications.db
# 应显示: -rw------- 1 user group ... applications.db
```

**部署时自动化**:
```bash
# 在部署脚本中
#!/bin/bash
CONFIG_DIR="./config"
CONFIG_DB="$CONFIG_DIR/applications.db"

# 创建目录
mkdir -p $CONFIG_DIR
chmod 700 $CONFIG_DIR

# 初始化数据库
python -m lark_service.db.init_config_db

# 设置权限
chmod 600 $CONFIG_DB

echo "✅ 配置文件权限已设置"
```

### 生产环境 .env 文件权限 (FR-094)

```bash
# 设置 .env.production 权限
chmod 600 .env.production

# 验证
ls -l .env.production
# 应显示: -rw------- 1 user group ... .env.production

# 检查是否在 .gitignore 中
grep -q ".env" .gitignore && echo "✅ .env 已忽略" || echo "❌ 需要添加到 .gitignore"
```

---

## 🔖 配置敏感度分类 (FR-081)

根据敏感程度,配置项分为三个等级:

### Public (公开级)

**特点**: 不包含敏感信息,可以公开查看

| 配置项 | 示例值 | 存储方式 | 访问控制 |
|--------|--------|---------|---------|
| `LOG_LEVEL` | `INFO`, `DEBUG` | 环境变量或配置文件 | 无限制 |
| `LOG_FORMAT` | `json`, `text` | 环境变量 | 无限制 |
| `FEATURE_FLAGS` | `enable_cache=true` | 配置文件 | 无限制 |
| `API_TIMEOUT` | `30` (秒) | 配置文件 | 无限制 |

**部署建议**:
- ✅ 可以提交到版本控制
- ✅ 可以在日志中显示
- ✅ 可以通过 API 查询

### Internal (内部级)

**特点**: 包含内部网络信息,仅内部可见

| 配置项 | 示例值 | 存储方式 | 访问控制 |
|--------|--------|---------|---------|
| `POSTGRES_HOST` | `db.internal` | 环境变量 | 仅内部网络 |
| `POSTGRES_PORT` | `5432` | 环境变量 | 仅内部网络 |
| `POSTGRES_DB` | `lark_service` | 环境变量 | 仅内部网络 |
| `RABBITMQ_HOST` | `mq.internal` | 环境变量 | 仅内部网络 |
| `RABBITMQ_PORT` | `5672` | 环境变量 | 仅内部网络 |

**部署建议**:
- ⚠️ 不应提交到版本控制
- ✅ 可以在内部日志中显示 (脱敏处理)
- ❌ 不应通过外部 API 暴露

### Secret (机密级)

**特点**: 高度敏感,泄露会导致安全风险

| 配置项 | 示例值 | 存储方式 | 访问控制 |
|--------|--------|---------|---------|
| `LARK_CONFIG_ENCRYPTION_KEY` | `32字节Fernet密钥` | 环境变量 + 密钥管理服务 | 文件权限 0600 + 加密 |
| `APP_SECRET` | `应用密钥` | 加密存储(SQLite) | Fernet 加密 + 权限 0600 |
| `POSTGRES_PASSWORD` | `数据库密码` | 环境变量 + Vault | 密钥管理服务 |
| `RABBITMQ_PASSWORD` | `消息队列密码` | 环境变量 + Vault | 密钥管理服务 |
| `Token` (所有类型) | `访问令牌` | 加密存储(PostgreSQL) | pg_crypto 加密 |

**部署建议**:
- ❌ 严禁提交到版本控制
- ❌ 严禁在日志中显示 (必须脱敏或完全隐藏)
- ❌ 严禁通过 API 暴露
- ✅ 使用密钥管理服务 (如 HashiCorp Vault)
- ✅ 定期轮换

### 日志脱敏规则 (FR-084)

```python
# 日志脱敏示例
def mask_secret(value: str, prefix_len: int = 4) -> str:
    """Mask sensitive values in logs.

    Args:
        value: Original value
        prefix_len: Number of prefix characters to show

    Returns:
        Masked string (e.g., "cli_****")
    """
    if not value or len(value) <= prefix_len:
        return "****"
    return f"{value[:prefix_len]}****"

# 使用示例
logger.info(f"App registered: app_id={app_id}, app_secret={mask_secret(app_secret)}")
# 输出: App registered: app_id=cli_12345678, app_secret=test****
```

---

## 🛡️ 依赖安全管理

### 安全扫描工具 (FR-086)

**safety - Python 依赖漏洞扫描**:

```bash
# 安装 safety
pip install safety

# 扫描依赖
safety check --file requirements.txt --json

# CI 集成 (阻止高危漏洞)
safety check --file requirements.txt --exit-code
```

**示例输出**:
```
+==============================================================================+
|                                                                              |
|                               /$$$$$$            /$$                         |
|                              /$$__  $$          | $$                         |
|           /$$$$$$$  /$$$$$$ | $$  \__//$$$$$$  /$$$$$$   /$$   /$$          |
|          /$$_____/ |____  $$| $$$$   /$$__  $$|_  $$_/  | $$  | $$          |
|         |  $$$$$$   /$$$$$$$| $$_/  | $$$$$$$$  | $$    | $$  | $$          |
|          \____  $$ /$$__  $$| $$    | $$_____/  | $$ /$$| $$  | $$          |
|          /$$$$$$$/|  $$$$$$$| $$    |  $$$$$$$  |  $$$$/|  $$$$$$$          |
|         |_______/  \_______/|__/     \_______/   \___/   \____  $$          |
|                                                           /$$  | $$          |
|                                                          |  $$$$$$/          |
|  Safety 2.x                                              \______/           |
|  by pyup.io                                                                  |
|                                                                              |
+==============================================================================+

 REPORT

  Safety is using PyUp's free open-source vulnerability database.

  Scanning dependencies in requirements.txt:

  -> cryptography==3.4.8 [CVE-2023-23931] (CVSS: 9.1 - CRITICAL)
     Vulnerability found in cryptography < 39.0.1
     Fix: Upgrade to cryptography>=39.0.1

  Scan complete. 1 vulnerability found.
```

### 依赖更新策略 (FR-087)

| 优先级 | CVSS 范围 | 响应时间 | 行动 |
|--------|----------|---------|------|
| **P0** | ≥ 9.0 (严重) | 24小时 | 立即修复并发布补丁版本 |
| **P1** | 7.0-8.9 (高危) | 7天 | 计划修复,包含在下一个版本 |
| **P2** | 4.0-6.9 (中危) | 30天 | 定期修复,月度更新 |
| **P3** | < 4.0 (低危) | 90天 | 可选修复,季度评估 |

**月度检查流程**:
```bash
# 1. 检查过时的依赖
pip list --outdated

# 2. 检查安全漏洞
safety check --file requirements.txt

# 3. 更新高危依赖
pip install --upgrade package-name==new-version

# 4. 重新测试
pytest tests/ --cov=src

# 5. 更新 requirements.txt
pip freeze > requirements.txt
```

### 依赖版本锁定 (FR-088)

```txt
# ✅ 推荐 - 精确版本锁定
lark-oapi==1.2.15
pydantic==2.5.3
SQLAlchemy==2.0.25
cryptography==41.0.7

# ❌ 避免 - 范围版本 (可能引入不兼容或漏洞版本)
lark-oapi>=1.2.0
pydantic~=2.5.0
SQLAlchemy^2.0.0
```

**版本锁定最佳实践**:
1. 使用 `==` 而非 `>=`, `~=`, `^`
2. 定期更新 (月度/季度)
3. 每次更新后运行完整测试
4. 记录更新原因 (安全修复/功能需求/性能优化)

---

## 🐳 容器安全

### Docker 镜像最佳实践 (FR-089, FR-091)

**安全 Dockerfile 示例**:
```dockerfile
# 1. 使用官方基础镜像
FROM python:3.12-slim AS base

# 2. 创建非 root 用户 (UID ≥ 1000)
RUN groupadd -r larkuser --gid=1001 && \
    useradd -r -u 1001 -g larkuser larkuser

# 3. 设置工作目录
WORKDIR /app

# 4. 复制依赖文件
COPY --chown=larkuser:larkuser requirements.txt .

# 5. 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制应用代码
COPY --chown=larkuser:larkuser . .

# 7. 切换到非 root 用户
USER 1001

# 8. 健康检查 (可选)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# 9. 仅暴露必需端口 (如果需要 HTTP 服务)
# EXPOSE 8000

# 10. 启动应用
CMD ["python", "-m", "lark_service"]
```

### 镜像安全扫描 (FR-090)

**Trivy 扫描**:
```bash
# 构建镜像
docker build -t lark-service:latest .

# 扫描高危和严重漏洞
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL lark-service:latest

# CI 集成 (阻止漏洞镜像)
trivy image --exit-code 1 --severity CRITICAL lark-service:latest
```

**示例输出**:
```
2026-01-15T10:30:00.000Z        INFO    Vulnerability scanning is enabled
2026-01-15T10:30:00.000Z        INFO    Detected OS: debian
2026-01-15T10:30:00.000Z        INFO    Number of language-specific files: 1

lark-service:latest (debian 11.6)
================================================================================
Total: 0 (HIGH: 0, CRITICAL: 0)

Python (python-pkg)
================================================================================
Total: 0 (HIGH: 0, CRITICAL: 0)

✅ No vulnerabilities found
```

### CI/CD 集成示例

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install safety
        run: pip install safety

      - name: Scan dependencies
        run: safety check --file requirements.txt --exit-code

  docker-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t lark-service:${{ github.sha }} .

      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'lark-service:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## 🔄 密钥轮换流程

### CLI 密钥轮换命令 (FR-083)

```bash
# 1. 生成新密钥
lark-service-cli config generate-key
# 输出: Generated key: xxxxx-new-key-xxxxx=

# 2. 轮换密钥并重新加密所有 App Secret
lark-service-cli config rotate-key --new-key xxxxx-new-key-xxxxx=
# 输出:
# ✅ Re-encrypted 5 applications
# ✅ Key rotation completed

# 3. 更新环境变量
export LARK_CONFIG_ENCRYPTION_KEY="xxxxx-new-key-xxxxx="

# 4. 验证
lark-service-cli app list
# 应正常显示应用列表
```

### 轮换频率建议

| 场景 | 频率 | 说明 |
|------|------|------|
| **正常运营** | 每季度 | 定期轮换提升安全性 |
| **员工离职** | 立即 | 防止密钥泄露 |
| **安全事件** | 立即 | 发现泄露或异常访问 |
| **合规审计** | 按要求 | 满足安全合规要求 |

---

## ✅ 安全检查清单

### 开发环境
- [ ] `.env` 文件在 `.gitignore` 中
- [ ] 不要在代码中硬编码密钥
- [ ] 不要在日志中输出密钥
- [ ] 使用强密钥 (Fernet 生成的 32 字节密钥)

### 生产环境
- [ ] 使用环境变量或密钥管理服务
- [ ] 不要将 `.env` 文件部署到生产环境
- [ ] 限制密钥访问权限 (仅必要的服务账号)
- [ ] 启用密钥轮换机制
- [ ] 定期审计密钥使用情况
- [ ] 备份密钥到安全位置

### 数据库
- [ ] SQLite 文件权限设置为 600 (仅所有者可读写)
- [ ] 定期备份数据库
- [ ] 加密数据库备份文件
- [ ] 限制数据库文件访问

---

## 🔍 常见问题

### Q1: 如果忘记了加密密钥怎么办?

**A**: 无法恢复!Fernet 是对称加密,没有密钥就无法解密。建议:
- 将密钥安全备份到多个位置
- 使用密钥管理服务
- 记录密钥轮换历史

### Q2: 可以使用弱密钥吗 (如 "123456")?

**A**: 不可以!必须使用 Fernet 生成的密钥:
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()  # 正确的密钥格式
```

### Q3: 多个环境可以共用一个密钥吗?

**A**: 不建议。建议:
- 开发环境: 独立密钥
- 测试环境: 独立密钥
- 生产环境: 独立密钥

### Q4: 数据库文件可以直接复制到其他环境吗?

**A**: 可以,但需要:
1. 目标环境有相同的加密密钥
2. 或者使用密钥轮换工具重新加密

### Q5: 如何验证密钥是否正确?

**A**: 尝试读取应用配置:
```bash
lark-service-cli app list
# 如果能正常显示,说明密钥正确
```

---

## 📚 相关文档

- [Cryptography 库文档](https://cryptography.io/en/latest/fernet/)
- [Fernet 规范](https://github.com/fernet/spec/)
- [OWASP 密钥管理指南](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)
