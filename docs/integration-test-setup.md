# 集成测试环境配置指南

本文档说明如何配置和运行 Lark Service 的集成测试。

---

## 📋 目录

1. [前置条件](#前置条件)
2. [获取飞书应用凭证](#获取飞书应用凭证)
3. [配置测试环境](#配置测试环境)
4. [准备测试数据](#准备测试数据)
5. [运行集成测试](#运行集成测试)
6. [常见问题](#常见问题)

---

## 🔧 前置条件

### 1. 数据库环境

确保 PostgreSQL 已启动并创建测试数据库:

```bash
# 启动 PostgreSQL (使用 Docker)
docker run -d \
  --name postgres-test \
  -e POSTGRES_USER=lark \
  -e POSTGRES_PASSWORD=test_password_123 \
  -e POSTGRES_DB=lark_service_test \
  -p 5432:5432 \
  postgres:15

# 或使用 docker-compose
docker-compose up -d postgres
```

### 2. Python 环境

```bash
# 安装依赖
pip install -r requirements.txt

# 或使用 uv (更快)
uv pip install -r requirements.txt
```

---

## 🔑 获取飞书应用凭证

### 步骤 1: 创建或选择飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 选择现有应用或创建新应用
3. 进入 **凭证与基础信息** 页面

### 步骤 2: 获取凭证

复制以下信息:
- **App ID**: `cli_xxxxxxxxxxxxxxxx`
- **App Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 步骤 3: 配置应用权限

在 **权限管理** 中开通以下权限:

#### 通讯录权限 (Contact 模块必需)
- ✅ `contact:user:read` - 获取用户基本信息
- ✅ `contact:user:read_sensitive` - 获取用户敏感信息 (手机号、邮箱)
- ✅ `contact:department:read` - 获取部门信息
- ✅ `im:chat:read` - 获取群组信息

#### 文档权限 (CloudDoc 模块必需)
- ✅ `docx:document` - 文档读写权限
- ✅ `bitable:app` - 多维表格权限
- ✅ `sheets:spreadsheet` - 电子表格权限
- ✅ `drive:drive` - 云空间权限

#### 消息权限 (Messaging 模块必需)
- ✅ `im:message` - 发送消息
- ✅ `im:message:send_as_bot` - 以机器人身份发送

### 步骤 4: 发布应用

- 开发环境: 添加测试用户到 **可用范围**
- 生产环境: 提交审核并发布

---

## ⚙️ 配置测试环境

### 方法 1: 使用 .env.test 文件 (推荐)

编辑项目根目录的 `.env.test` 文件:

```bash
# 编辑配置文件
nano .env.test

# 或使用您喜欢的编辑器
code .env.test
```

**必填配置:**

```bash
# ============================================
# 飞书应用凭证
# ============================================
TEST_APP_ID=cli_a1b2c3d4e5f6g7h8      # 替换为您的 App ID
TEST_APP_SECRET=abc123def456ghi789    # 替换为您的 App Secret

# ============================================
# 测试用户信息
# ============================================
TEST_USER_EMAIL=zhangsan@company.com  # 替换为真实用户邮箱
TEST_USER_MOBILE=+8613800138000       # 替换为真实用户手机号
```

**可选配置 (用于特定测试):**

```bash
# 如果您已知用户 ID (可选,测试会自动获取)
TEST_USER_OPEN_ID=ou_1234567890abcdef
TEST_USER_ID=12345678

# 如果您有测试文档 (可选,测试会自动创建)
TEST_DOC_TOKEN=doxcn1234567890abcdef
TEST_BITABLE_APP_TOKEN=bascn1234567890abcdef
TEST_BITABLE_TABLE_ID=tbl1234567890abcdef
```

### 方法 2: 使用环境变量

```bash
# 临时设置 (当前会话有效)
export TEST_APP_ID="cli_xxxxxxxxxxxxxxxx"
export TEST_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TEST_USER_EMAIL="test@company.com"

# 运行测试
pytest tests/integration/ -v
```

---

## 📝 准备测试数据

### 自动准备 (推荐)

大部分测试数据会自动创建,您只需提供:
1. ✅ 应用凭证 (`TEST_APP_ID`, `TEST_APP_SECRET`)
2. ✅ 一个真实用户的邮箱 (`TEST_USER_EMAIL`)

测试会自动:
- 创建测试文档
- 创建测试多维表格
- 查询用户信息
- 清理测试数据

### 手动准备 (可选)

如果您想使用现有的测试数据:

#### 1. 获取文档 Token

创建一个测试文档,从 URL 中提取 token:

```
https://example.feishu.cn/docx/doxcnABCDEFG1234567890
                              └─────────┬─────────┘
                                    文档 token
```

配置到 `.env.test`:
```bash
TEST_DOC_TOKEN=doxcnABCDEFG1234567890
```

#### 2. 获取多维表格 Token

创建一个测试多维表格,从 URL 中提取 app_token 和 table_id:

```
https://example.feishu.cn/base/bascnXYZ123?table=tblABC456
                              └────┬────┘      └───┬───┘
                              app_token        table_id
```

配置到 `.env.test`:
```bash
TEST_BITABLE_APP_TOKEN=bascnXYZ123
TEST_BITABLE_TABLE_ID=tblABC456
```

#### 3. 获取用户 ID

通过飞书管理后台或 API 查询用户 ID:

```bash
# 使用我们的 CLI 工具查询
python -m lark_service.cli user query --email test@company.com
```

---

## 🚀 运行集成测试

### 运行所有集成测试

```bash
# 使用 .env.test 配置
pytest tests/integration/ -v

# 指定环境文件
pytest tests/integration/ -v --envfile=.env.test
```

### 运行特定模块的测试

```bash
# 只测试 Contact 模块
pytest tests/integration/test_contact_integration.py -v

# 只测试 CloudDoc 模块
pytest tests/integration/test_clouddoc_integration.py -v
```

### 运行特定测试用例

```bash
# 测试用户查询
pytest tests/integration/test_contact_integration.py::test_get_user_by_email -v

# 测试文档创建
pytest tests/integration/test_clouddoc_integration.py::test_create_document -v
```

### 查看详细日志

```bash
# 显示详细日志输出
pytest tests/integration/ -v -s --log-cli-level=DEBUG

# 保存日志到文件
pytest tests/integration/ -v --log-file=integration_test.log
```

### 跳过集成测试 (运行单元测试)

```bash
# 只运行单元测试,跳过集成测试
pytest tests/unit/ -v

# 运行所有测试但跳过标记为 integration 的
pytest -v -m "not integration"
```

---

## 🔍 验证配置

运行配置验证脚本:

```bash
# 验证环境配置
python scripts/verify_integration_config.py

# 输出示例:
# ✅ PostgreSQL 连接正常
# ✅ 应用凭证配置正确
# ✅ 测试用户邮箱有效
# ✅ 应用权限充足
# ⚠️  未配置测试文档 (将自动创建)
```

---

## ❓ 常见问题

### Q1: 测试失败: "Permission Denied"

**原因**: 应用缺少必要权限

**解决**:
1. 检查应用权限配置 (见 [步骤 3](#步骤-3-配置应用权限))
2. 确保应用已发布或测试用户在可用范围内
3. 重新获取 Token (删除缓存的 Token)

```bash
# 清理 Token 缓存
python -m lark_service.cli token clear --app-id cli_xxx
```

### Q2: 测试失败: "User not found"

**原因**: 测试用户不在应用可用范围内

**解决**:
1. 在飞书开放平台添加测试用户到 **可用范围**
2. 或使用已在范围内的用户邮箱

### Q3: 测试失败: "Database connection error"

**原因**: PostgreSQL 未启动或配置错误

**解决**:
```bash
# 检查 PostgreSQL 状态
docker ps | grep postgres

# 启动 PostgreSQL
docker-compose up -d postgres

# 检查连接
psql -h localhost -U lark -d lark_service_test
```

### Q4: 如何清理测试数据?

```bash
# 清理测试数据库
python scripts/cleanup_test_data.py

# 或手动清理
psql -h localhost -U lark -d lark_service_test -c "TRUNCATE TABLE tokens, user_cache;"
```

### Q5: 测试运行很慢

**原因**: 集成测试需要真实 API 调用

**优化**:
1. 只运行需要的测试模块
2. 使用缓存减少 API 调用
3. 并行运行测试 (谨慎使用):

```bash
# 并行运行 (需要 pytest-xdist)
pip install pytest-xdist
pytest tests/integration/ -v -n 4  # 4 个并行进程
```

### Q6: 如何在 CI/CD 中运行集成测试?

在 GitHub Actions 中:

```yaml
# .github/workflows/integration-test.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: lark
          POSTGRES_PASSWORD: test_password_123
          POSTGRES_DB: lark_service_test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run integration tests
        env:
          TEST_APP_ID: ${{ secrets.TEST_APP_ID }}
          TEST_APP_SECRET: ${{ secrets.TEST_APP_SECRET }}
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_DB: lark_service_test
          POSTGRES_USER: lark
          POSTGRES_PASSWORD: test_password_123
        run: pytest tests/integration/ -v
```

在 GitHub 仓库设置中添加 Secrets:
- `TEST_APP_ID`
- `TEST_APP_SECRET`
- `TEST_USER_EMAIL`

---

## 📚 相关文档

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [API 参考文档](./api_reference.md)
- [架构设计文档](./architecture.md)
- [开发环境配置](./development-environment.md)

---

## 🆘 获取帮助

如果遇到问题:

1. 查看测试日志: `pytest tests/integration/ -v -s --log-cli-level=DEBUG`
2. 查看飞书开放平台错误码: https://open.feishu.cn/document/server-docs/api-call-guide/error-code
3. 提交 Issue: [GitHub Issues](https://github.com/your-repo/issues)

---

**最后更新**: 2026-01-16
