# 集成测试配置指南

本文档说明如何配置和运行 Phase 4 集成测试。

---

## 📋 前置要求

### 1. 基础设施

需要运行以下服务:

```bash
# 使用 docker-compose 启动 (推荐)
docker-compose up -d postgres rabbitmq

# 或手动启动
# PostgreSQL: 端口 5432
# RabbitMQ: 端口 5672
```

### 2. 飞书应用配置

需要一个有效的飞书应用,并配置以下权限:

#### Contact 模块测试所需权限:
- `contact:user.email:readonly` - 通过邮箱查询用户
- `contact:user.phone:readonly` - 通过手机号查询用户
- `contact:user.employee_id:readonly` - 通过 user_id 查询用户
- `contact:user.id:readonly` - 获取用户 open_id
- `contact:department.list` - 查询部门列表
- `im:chat:readonly` - 查询群组信息

#### CloudDoc 模块测试所需权限:
- `docx:document:readonly` - 读取文档
- `docx:document` - 创建和编辑文档 (写操作测试)
- `bitable:app:readonly` - 读取多维表格
- `bitable:app` - 创建和编辑多维表格 (写操作测试)
- `sheets:spreadsheet:readonly` - 读取电子表格
- `sheets:spreadsheet` - 编辑电子表格 (写操作测试)

---

## 🔧 配置步骤

### 步骤 1: 创建 `.env.test` 文件

在项目根目录创建 `.env.test` 文件:

```bash
# 复制示例文件
cp .env.example .env.test
```

### 步骤 2: 配置基础设施连接

编辑 `.env.test`,填入 PostgreSQL 和 RabbitMQ 配置:

```bash
# ============================================
# PostgreSQL 配置
# ============================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lark_service
POSTGRES_USER=lark
POSTGRES_PASSWORD=your_postgres_password

# ============================================
# RabbitMQ 配置
# ============================================
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=lark
RABBITMQ_PASSWORD=your_rabbitmq_password

# ============================================
# 加密密钥
# ============================================
# 生成方式: openssl rand -base64 32
LARK_CONFIG_ENCRYPTION_KEY=your_random_32_byte_key_here

# ============================================
# 日志配置
# ============================================
LOG_LEVEL=DEBUG  # 测试时建议使用 DEBUG
```

### 步骤 3: 配置飞书应用凭证

在 `.env.test` 中添加测试应用配置:

```bash
# ============================================
# 集成测试专用配置
# ============================================

# 飞书应用凭证
TEST_APP_ID=cli_a1b2c3d4e5f6g7h8
TEST_APP_SECRET=your_app_secret_here

# Contact 测试数据
TEST_USER_EMAIL=test@yourcompany.com      # 必需: 用于测试邮箱查询
TEST_USER_MOBILE=+8613800138000           # 可选: 用于测试手机号查询
TEST_DEPARTMENT_ID=od-xxx                 # 可选: 用于测试部门查询
TEST_CHAT_ID=oc_xxx                       # 可选: 用于测试群组查询

# CloudDoc 测试数据
TEST_DOC_TOKEN=doxcnXXXXXXXXXXXXXXXXXXXX  # 可选: 测试文档 ID (需要读权限)
TEST_BITABLE_APP_TOKEN=bascnXXXXXXXXXXXX  # 可选: 测试多维表格 ID (需要读权限)
TEST_SHEET_TOKEN=shtcnXXXXXXXXXXXXXXXXXX  # 可选: 测试电子表格 ID (需要读权限)
```

### 步骤 4: 生成加密密钥

```bash
# 生成随机加密密钥
openssl rand -base64 32

# 将生成的密钥填入 .env.test 的 LARK_CONFIG_ENCRYPTION_KEY
```

---

## 🚀 运行集成测试

### 完整测试套件

```bash
# 运行所有集成测试
pytest tests/integration/ -v

# 运行并显示详细输出
pytest tests/integration/ -v -s
```

### Contact 模块测试

```bash
# 运行所有 Contact 测试
pytest tests/integration/test_contact_e2e.py -v

# 运行特定测试类
pytest tests/integration/test_contact_e2e.py::TestContactWithoutCache -v

# 运行单个测试
pytest tests/integration/test_contact_e2e.py::TestContactWithoutCache::test_get_user_by_email_success -v
```

### CloudDoc 模块测试

```bash
# 运行所有 CloudDoc 测试
pytest tests/integration/test_clouddoc_e2e.py -v

# 跳过需要写权限的测试
pytest tests/integration/test_clouddoc_e2e.py -v -m "not write_permission"

# 只运行读操作测试
pytest tests/integration/test_clouddoc_e2e.py::TestDocumentOperations::test_get_document_success -v
```

---

## 📊 测试说明

### Contact 模块 (8 个测试)

#### 不使用缓存的测试 (3 个)
- `test_get_user_by_email_success` - 通过邮箱查询用户成功
- `test_get_user_by_email_not_found` - 用户不存在时返回 NotFoundError
- `test_get_user_by_mobile_success` - 通过手机号查询用户

#### 缓存功能测试 (4 个)
- `test_cache_miss_then_hit` - 验证缓存未命中→API 调用→缓存命中流程
- `test_cache_by_different_identifiers` - 验证多标识符缓存 (email/mobile/user_id)
- `test_cache_invalidation` - 验证缓存失效机制
- `test_cache_app_isolation` - 验证不同 App 的缓存隔离

#### 批量操作测试 (1 个)
- `test_batch_get_users_with_cache` - 验证批量查询的缓存优化

### CloudDoc 模块 (9 个测试)

#### 文档操作 (3 个)
- `test_get_document_success` - 获取文档元数据
- `test_get_document_not_found` - 文档不存在处理
- `test_append_blocks_to_document` - 追加内容块 (需要写权限,默认跳过)

#### 多维表格操作 (2 个)
- `test_bitable_crud_operations` - 记录 CRUD 操作 (需要写权限,默认跳过)
- `test_bitable_query_with_filter` - 过滤查询

#### 权限管理 (1 个)
- `test_grant_and_revoke_permission` - 授予和撤销权限 (需要写权限,默认跳过)

#### 电子表格操作 (1 个)
- `test_sheet_read_write` - Sheet 读写操作 (需要写权限,默认跳过)

#### 错误处理 (2 个)
- `test_invalid_doc_id_format` - 无效 ID 格式验证
- `test_permission_denied` - 权限拒绝处理

---

## ⚠️ 当前状态说明

### 测试框架状态: ✅ 完整

- ✅ 所有 fixtures 正确初始化
- ✅ CredentialPool 正确配置
- ✅ ContactCacheManager 正确集成
- ✅ 异常处理正确
- ✅ 测试可以收集和运行

### API 实现状态: ⏸️ Placeholder

**当前行为:**
- Contact 和 CloudDoc 的客户端方法是 **placeholder**
- 所有方法都抛出 `NotFoundError` 或 `PermissionDeniedError`
- 这是**正常的**,因为还未实现真实的 Lark API 调用

**测试运行结果:**
```bash
$ pytest tests/integration/test_contact_e2e.py::TestContactWithoutCache::test_get_user_by_email_success -v

FAILED - NotFoundError: User not found: test@yourcompany.com
```

这个失败是**预期的**! 表示:
1. ✅ 测试框架工作正常
2. ✅ 异常处理正确
3. ⏸️ 等待实现真实 API 调用

---

## 🔨 实现真实 API 调用

要让测试通过,需要在以下文件中实现真实的 Lark API 调用:

### Contact 模块

**文件:** `src/lark_service/contact/client.py`

**需要实现的方法:**

```python
def get_user_by_email(self, app_id: str, email: str) -> User:
    """通过邮箱查询用户 - 需要实现真实 API 调用"""
    # TODO: 实现 Lark API 调用
    # 1. 获取 tenant_access_token
    # 2. 调用 lark_oapi.api.contact.v3.User.get()
    # 3. 解析响应并返回 User 模型
    raise NotFoundError(f"User not found: {email}")  # 当前 placeholder

def get_user_by_mobile(self, app_id: str, mobile: str) -> User:
    """通过手机号查询用户 - 需要实现真实 API 调用"""
    raise NotFoundError(f"User not found: {mobile}")  # 当前 placeholder

def get_user_by_user_id(self, app_id: str, user_id: str) -> User:
    """通过 user_id 查询用户 - 需要实现真实 API 调用"""
    raise NotFoundError(f"User not found: {user_id}")  # 当前 placeholder

def batch_get_users(self, app_id: str, queries: list[BatchUserQuery]) -> list[User]:
    """批量查询用户 - 需要实现真实 API 调用"""
    raise NotFoundError("Batch query not implemented")  # 当前 placeholder
```

### CloudDoc 模块

**文件:** `src/lark_service/clouddoc/client.py`

**需要实现的方法:**

```python
def get_document(self, app_id: str, doc_id: str) -> Document:
    """获取文档 - 需要实现真实 API 调用"""
    raise NotFoundError(f"Document not found: {doc_id}")  # 当前 placeholder

def append_blocks(self, app_id: str, doc_id: str, blocks: list[ContentBlock]) -> list[str]:
    """追加内容块 - 需要实现真实 API 调用"""
    raise PermissionDeniedError("Write operation not implemented")  # 当前 placeholder
```

**文件:** `src/lark_service/clouddoc/bitable/client.py`

```python
def create_record(self, app_id: str, app_token: str, table_id: str, fields: dict) -> BaseRecord:
    """创建记录 - 需要实现真实 API 调用"""
    raise PermissionDeniedError("Write operation not implemented")  # 当前 placeholder

def list_records(self, app_id: str, app_token: str, table_id: str, ...) -> list[BaseRecord]:
    """查询记录 - 需要实现真实 API 调用"""
    raise NotFoundError("Bitable query not implemented")  # 当前 placeholder
```

**文件:** `src/lark_service/clouddoc/sheet/client.py`

```python
def read_range(self, app_id: str, sheet_token: str, range_str: str) -> SheetRange:
    """读取范围 - 需要实现真实 API 调用"""
    raise NotFoundError("Sheet read not implemented")  # 当前 placeholder

def write_range(self, app_id: str, sheet_token: str, range_str: str, values: list[list]) -> bool:
    """写入范围 - 需要实现真实 API 调用"""
    raise PermissionDeniedError("Write operation not implemented")  # 当前 placeholder
```

---

## 🎯 实现优先级建议

### 高优先级 (解锁集成测试)

1. **Contact.get_user_by_email** - 最基础的用户查询
2. **Contact.get_user_by_mobile** - 手机号查询
3. **CloudDoc.get_document** - 文档元数据查询

### 中优先级 (完善功能)

4. **Contact.batch_get_users** - 批量查询优化
5. **Bitable.list_records** - 多维表格查询
6. **Sheet.read_range** - 电子表格读取

### 低优先级 (写操作,可选)

7. **CloudDoc.append_blocks** - 文档编辑
8. **Bitable.create_record** - 记录创建
9. **Sheet.write_range** - 电子表格写入

---

## 📚 相关文档

- [Lark OpenAPI 文档](https://open.feishu.cn/document/home/index)
- [Contact API 参考](https://open.feishu.cn/document/server-docs/contact-v3/user/get)
- [CloudDoc API 参考](https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/get)
- [Bitable API 参考](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/list)

---

## 🐛 故障排查

### 问题 1: `Missing required config: TEST_APP_ID`

**原因:** `.env.test` 文件未配置或未加载

**解决:**
```bash
# 检查文件是否存在
ls -la .env.test

# 检查文件内容
cat .env.test | grep TEST_APP_ID

# 确保文件在项目根目录
pwd
```

### 问题 2: `Connection refused` (PostgreSQL)

**原因:** PostgreSQL 未启动

**解决:**
```bash
# 使用 docker-compose
docker-compose up -d postgres

# 检查连接
psql -h localhost -U lark -d lark_service
```

### 问题 3: `NotFoundError: User not found`

**原因:** 这是**正常的**! API 方法还是 placeholder

**解决:** 实现真实的 API 调用 (参见上面的"实现真实 API 调用"章节)

### 问题 4: 测试超时

**原因:** 重试策略导致的延迟 (已修复)

**当前状态:** ✅ 已优化
- 客户端错误 (4xx) 不再重试
- 测试运行时间正常 (~4-5 秒)

---

## ✅ 检查清单

运行集成测试前,确认以下项目:

- [ ] PostgreSQL 运行中 (`docker-compose ps`)
- [ ] RabbitMQ 运行中 (可选,某些测试需要)
- [ ] `.env.test` 文件存在且配置完整
- [ ] `TEST_APP_ID` 和 `TEST_APP_SECRET` 已填写
- [ ] `TEST_USER_EMAIL` 已填写 (Contact 测试必需)
- [ ] 飞书应用权限已配置
- [ ] 加密密钥已生成 (`LARK_CONFIG_ENCRYPTION_KEY`)

---

## 🎉 总结

**当前状态:**
- ✅ 测试框架完整且可运行
- ✅ Fixtures 正确配置
- ✅ 环境变量加载正常
- ⏸️ 等待实现真实 API 调用

**下一步:**
1. 配置 `.env.test` 文件
2. 实现 Contact 和 CloudDoc 的真实 API 调用
3. 运行集成测试验证功能
4. 添加性能基准测试

**配置完成后,即可运行:**
```bash
pytest tests/integration/test_contact_e2e.py -v
```
