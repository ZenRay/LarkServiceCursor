# 如何配置集成测试资源

## 📋 概述

集成测试需要真实的飞书资源（Bitable/Sheet/Doc）来验证API功能。本文档说明如何创建测试资源并获取相应的token。

## 🎯 需要的资源

### 1. 应用凭证（必需）

这些用于获取访问token：

```bash
LARK_APP_ID=cli_xxx              # 飞书应用ID
LARK_APP_SECRET=xxx              # 飞书应用密钥
```

**获取方式**：
1. 访问 https://open.feishu.cn/app
2. 创建企业自建应用
3. 进入"凭证与基础信息"获取

### 2. 测试资源Token（可选）

这些用于集成测试：

| 资源类型 | 环境变量 | 用途 |
|---------|---------|------|
| Bitable | `TEST_BITABLE_APP_TOKEN` | 测试多维表格CRUD |
| Sheet | `TEST_SHEET_TOKEN` | 测试电子表格读写 |
| Doc | `TEST_DOC_TOKEN` | 测试文档操作 |

## 🔧 创建和配置测试资源

### 方案1: 在飞书中手动创建（推荐）

#### Step 1: 创建Bitable测试表格

1. **创建Bitable**
   - 在飞书中点击"创建" → "多维表格"
   - 命名: "Lark Service Integration Test"

2. **配置权限**
   - 点击右上角"共享" → "管理协作者"
   - 添加你的测试应用
   - 授予"可编辑"权限

3. **获取Token**
   - URL格式: `https://xxx.feishu.cn/base/{app_token}?table={table_id}`
   - 示例: `https://xxx.feishu.cn/base/bascnABC123/table=tblXYZ789`
   - `app_token` → `TEST_BITABLE_APP_TOKEN`
   - `table_id` → `TEST_BITABLE_TABLE_ID`

4. **配置测试数据**
   - 添加以下字段:
     - Name (单行文本)
     - Age (数字)
     - Active (复选框)
     - Email (单行文本)
   - 添加几行测试数据

#### Step 2: 创建Sheet测试表格

1. **创建Sheet**
   - 点击"创建" → "电子表格"
   - 命名: "Lark Service Sheet Test"

2. **配置权限**
   - 共享给测试应用，授予"可编辑"权限

3. **获取Token**
   - URL格式: `https://xxx.feishu.cn/sheets/{spreadsheet_token}`
   - 示例: `https://xxx.feishu.cn/sheets/shtcnABC123`
   - `spreadsheet_token` → `TEST_SHEET_TOKEN`
   - Sheet ID通常是 "sheet1" (第一个sheet)

4. **配置测试数据**
   - 在A1:C1添加表头: Name, Age, Email
   - 添加几行测试数据

#### Step 3: 创建Doc测试文档

1. **创建文档**
   - 点击"创建" → "文档"
   - 命名: "Lark Service Doc Test"

2. **配置权限**
   - 共享给测试应用，授予"可编辑"权限

3. **获取Token**
   - URL格式: `https://xxx.feishu.cn/docs/{document_token}`
   - 示例: `https://xxx.feishu.cn/docs/doccnABC123`
   - `document_token` → `TEST_DOC_TOKEN`

4. **添加测试内容**
   - 添加标题、段落、列表等
   - 方便测试读取功能

### 方案2: 使用setup脚本自动创建

```bash
# 运行自动化设置脚本（在项目根目录）
cd /home/ray/Documents/Files/LarkServiceCursor
python scripts/setup_integration_test.py

# 或使用staging-simulation的脚本
bash staging-simulation/scripts/update_test_tokens.sh

# 脚本会:
# 1. 检查应用权限
# 2. 创建测试资源
# 3. 生成 .env.integration 配置文件
```

## ⚙️ 配置环境变量

### 本地Docker测试

编辑 `staging-simulation/.env.local`:

```bash
# 基础凭证
LARK_APP_ID=cli_your_real_app_id
LARK_APP_SECRET=your_real_secret

# 集成测试（可选）
TEST_APP_ID=${LARK_APP_ID}
TEST_APP_SECRET=${LARK_APP_SECRET}

# Bitable测试
TEST_BITABLE_APP_TOKEN=bascnABC123XYZ
TEST_BITABLE_TABLE_ID=tblDEF456UVW
# TEST_WRITABLE_BITABLE_TOKEN=bascnWritable123  # 可选

# Sheet测试
TEST_SHEET_TOKEN=shtcnGHI789JKL
TEST_SHEET_ID=sheet1
# TEST_WRITABLE_SHEET_TOKEN=shtcnWritable456  # 可选

# Doc测试
TEST_DOC_TOKEN=doccnMNO012PQR
```

### Staging环境

编辑 `config/.env.staging`:

```bash
# 同上配置
```

## 🧪 运行集成测试

### 运行所有集成测试

```bash
cd /home/ray/Documents/Files/LarkServiceCursor
source .venv-test/bin/activate

# 设置环境变量
export $(cat staging-simulation/.env.local | grep -v '^#' | xargs)

# 运行所有集成测试
pytest tests/integration/ -v

# 或分别运行
pytest tests/integration/test_bitable_e2e.py -v    # Bitable测试
pytest tests/integration/test_sheet_e2e.py -v      # Sheet测试
pytest tests/integration/test_clouddoc_e2e.py -v   # Doc测试
pytest tests/integration/test_contact_e2e.py -v    # 通讯录测试 (不需要额外token)
```

### 如果没有配置测试资源

测试会自动跳过，显示：

```
SKIPPED [1] test_bitable_e2e.py:31: Integration test environment not configured
(missing TEST_APP_ID, TEST_APP_SECRET, or TEST_BITABLE_APP_TOKEN)
```

这是正常的，不影响核心功能验证。

## 📊 测试覆盖范围

### 有测试资源Token

可以测试的功能：

- ✅ Bitable CRUD (创建/读取/更新/删除记录)
- ✅ Bitable过滤和分页
- ✅ Sheet读取和写入
- ✅ Sheet格式化和合并单元格
- ✅ Doc权限管理
- ✅ Doc内容读取

### 无测试资源Token

可以测试的功能：

- ✅ 通讯录服务 (已验证100%通过)
- ✅ Token管理
- ✅ 单元测试 (覆盖率60.38%)
- ✅ 核心逻辑验证

## 🔒 安全注意事项

### ⚠️ 不要泄露Token

```bash
# ❌ 错误 - 不要提交到Git
git add .env.local
git commit -m "add env"

# ✅ 正确 - .env.local已在.gitignore中
cat .gitignore | grep ".env.local"
```

### ⚠️ 使用测试专用资源

- 不要使用生产数据
- 创建独立的测试空间
- 定期清理测试数据

### ⚠️ 限制权限

- 测试应用只授予必需权限
- 使用只读token进行读取测试
- 写操作使用独立的可写token

## 📚 相关文档

- [集成测试总结](./integration-test-summary-2026-01-18.md)
- [飞书API文档](https://open.feishu.cn/document/)
- [测试环境配置](../staging-simulation/README.md)

## 🔗 快速链接

- [飞书开放平台](https://open.feishu.cn/)
- [创建应用](https://open.feishu.cn/app)
- [API调试工具](https://open.feishu.cn/api-explorer/)

## ❓ 常见问题

### Q1: 为什么需要这些token？

A: 集成测试需要真实的飞书资源来验证API功能是否正常工作。这些token用于访问测试资源。

### Q2: 可以跳过这些测试吗？

A: 可以。如果不配置这些token，相关测试会自动跳过。核心功能已通过单元测试验证。

### Q3: 如何知道哪些测试需要哪些token？

A: 运行测试时，pytest会显示跳过原因：

```
SKIPPED - missing TEST_BITABLE_APP_TOKEN
```

### Q4: 测试会修改我的数据吗？

A: 写测试会创建/修改/删除记录，但只在指定的测试资源中操作。建议使用专门的测试表格。

### Q5: 如何清理测试数据？

A:
```bash
# 手动清理
# 1. 在飞书中打开测试资源
# 2. 删除测试数据行

# 或重新创建测试资源
# 删除旧资源 → 创建新资源 → 更新token
```

---

**文档版本**: 1.0
**最后更新**: 2026-01-18
**维护人**: Backend Team
