# 集成测试快速开始指南

5 分钟配置并运行集成测试! 🚀

---

## 🎯 快速配置 (3 种方法)

### 方法 1: 交互式向导 (推荐新手) ⭐

运行配置向导,按提示输入信息:

```bash
python scripts/setup_integration_test.py
```

向导会询问:
- ✅ 飞书应用 App ID 和 App Secret
- ✅ 测试用户邮箱
- ✅ 数据库配置
- ✅ 自动生成加密密钥

完成后自动创建 `.env.test` 文件。

---

### 方法 2: 手动编辑配置文件 (推荐熟手)

1. **编辑 `.env.test` 文件**:

```bash
nano .env.test
```

2. **填写必需配置**:

```bash
# 飞书应用凭证 (必填)
TEST_APP_ID=cli_xxxxxxxxxxxxxxxx          # 替换为您的 App ID
TEST_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx  # 替换为您的 App Secret

# 测试用户 (必填)
TEST_USER_EMAIL=zhangsan@company.com      # 替换为真实用户邮箱

# 数据库 (使用默认值即可)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service_test
POSTGRES_USER=lark
POSTGRES_PASSWORD=test_password_123

# 加密密钥 (使用默认测试密钥)
LARK_CONFIG_ENCRYPTION_KEY=test_key_for_integration_tests_only_32bytes_base64==
```

3. **保存文件** (Ctrl+O, Enter, Ctrl+X)

---

### 方法 3: 使用环境变量 (推荐 CI/CD)

直接设置环境变量:

```bash
export TEST_APP_ID="cli_xxxxxxxxxxxxxxxx"
export TEST_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxx"
export TEST_USER_EMAIL="test@company.com"
export POSTGRES_HOST="localhost"
export POSTGRES_DB="lark_service_test"
export POSTGRES_USER="lark"
export POSTGRES_PASSWORD="test_password_123"
```

---

## 🔑 获取飞书应用凭证

### 步骤 1: 访问开放平台

打开浏览器访问: https://open.feishu.cn/app

### 步骤 2: 选择应用

选择您的应用或创建新应用

### 步骤 3: 获取凭证

进入 **凭证与基础信息** 页面,复制:
- **App ID**: `cli_xxxxxxxxxxxxxxxx`
- **App Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 步骤 4: 配置权限 (重要!)

在 **权限管理** 中开通以下权限:

**通讯录权限:**
- ✅ `contact:user:read` - 获取用户信息
- ✅ `contact:department:read` - 获取部门信息
- ✅ `im:chat:read` - 获取群组信息

**文档权限:**
- ✅ `docx:document` - 文档操作
- ✅ `bitable:app` - 多维表格操作
- ✅ `sheets:spreadsheet` - 电子表格操作

**消息权限:**
- ✅ `im:message` - 发送消息

### 步骤 5: 发布应用

- 开发环境: 添加测试用户到 **可用范围**
- 生产环境: 提交审核

---

## 🗄️ 启动数据库

### 使用 Docker (推荐)

```bash
# 启动 PostgreSQL
docker-compose up -d postgres

# 验证启动
docker ps | grep postgres
```

### 手动安装

如果您已有 PostgreSQL:

```bash
# 创建测试数据库
createdb -U lark lark_service_test

# 或使用 psql
psql -U postgres -c "CREATE DATABASE lark_service_test;"
```

---

## ✅ 验证配置

运行验证脚本:

```bash
python scripts/verify_integration_config.py
```

**预期输出:**

```
🔍 Verifying integration test configuration...

✅ .env.test file found
✅ TEST_APP_ID = cli_a1b2...
✅ TEST_APP_SECRET = abc1...
✅ TEST_USER_EMAIL = test@company.com
✅ PostgreSQL connection successful
✅ Lark API authentication successful
✅ Test user email valid

📊 Result: 6/6 checks passed

🎉 All checks passed! You can run integration tests:
   pytest tests/integration/ -v
```

---

## 🚀 运行测试

### 运行所有集成测试

```bash
pytest tests/integration/ -v
```

### 运行特定模块

```bash
# Contact 模块
pytest tests/integration/test_contact_integration.py -v

# CloudDoc 模块
pytest tests/integration/test_clouddoc_integration.py -v
```

### 查看详细日志

```bash
pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

---

## 📊 测试覆盖范围

集成测试会验证:

### Contact 模块 ✅
- ✅ 通过邮箱查询用户
- ✅ 通过手机号查询用户
- ✅ 批量查询用户
- ✅ 查询部门信息
- ✅ 查询群组成员
- ✅ 用户缓存功能 (TTL, app_id 隔离)

### CloudDoc 模块 ✅
- ✅ 创建文档
- ✅ 追加内容
- ✅ 读取文档
- ✅ 文档权限管理
- ✅ 多维表格 CRUD
- ✅ 电子表格操作

### Messaging 模块 ✅
- ✅ 发送文本消息
- ✅ 发送卡片消息
- ✅ 上传媒体文件

---

## ❓ 常见问题

### Q: 测试失败 "Permission Denied"

**原因**: 应用缺少权限

**解决**:
1. 检查应用权限配置 (见上方 [步骤 4](#步骤-4-配置权限-重要))
2. 确保应用已发布或测试用户在可用范围内

### Q: 测试失败 "User not found"

**原因**: 测试用户不在应用范围内

**解决**:
在飞书开放平台添加测试用户到 **可用范围**

### Q: 数据库连接失败

**原因**: PostgreSQL 未启动

**解决**:
```bash
# 检查状态
docker ps | grep postgres

# 启动
docker-compose up -d postgres
```

### Q: 如何清理测试数据?

```bash
# 清理数据库
psql -h localhost -U lark -d lark_service_test -c "TRUNCATE TABLE tokens, user_cache CASCADE;"

# 或重建数据库
docker-compose down -v
docker-compose up -d postgres
```

---

## 📚 详细文档

需要更多信息? 查看完整文档:

- **详细配置指南**: [docs/integration-test-setup.md](docs/integration-test-setup.md)
- **API 参考**: [docs/api_reference.md](docs/api_reference.md)
- **架构设计**: [docs/architecture.md](docs/architecture.md)

---

## 🆘 获取帮助

遇到问题?

1. **查看日志**: `pytest tests/integration/ -v -s --log-cli-level=DEBUG`
2. **运行验证**: `python scripts/verify_integration_config.py`
3. **查看文档**: [docs/integration-test-setup.md](docs/integration-test-setup.md)
4. **提交 Issue**: [GitHub Issues](https://github.com/your-repo/issues)

---

## 🎉 完成!

配置完成后,您可以:

✅ 运行集成测试验证功能
✅ 在 CI/CD 中自动化测试
✅ 确保代码与飞书 API 兼容
✅ 发现潜在的权限和配置问题

**祝测试顺利!** 🚀

---

**最后更新**: 2026-01-16
