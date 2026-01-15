# 安全配置指南

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
