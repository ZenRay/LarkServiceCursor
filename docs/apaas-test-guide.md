# aPaaS 集成测试配置指南

## 概述

aPaaS (应用平台即服务) 集成测试需要**用户级访问令牌**,权限要求较高,需要与标准集成测试分离配置。本指南说明如何安全配置和运行 aPaaS 测试。

## 安全要求

⚠️ **重要安全提示**

aPaaS 操作需要 `user_access_token` (非 `tenant_access_token`),该令牌具有以下权限:
- 用户级别的工作空间数据访问权限
- 访问敏感数据表的能力
- 创建/修改/删除记录的权限

**安全最佳实践:**
1. ✅ **绝不**将 `.env.apaas` 提交到版本控制
2. ✅ 将凭据存储在安全位置(密码管理器、密钥保管库)
3. ✅ 使用专用测试工作空间(勿使用生产工作空间)
4. ✅ 定期轮换令牌(建议:每30天)
5. ✅ 授予最小必需权限
6. ✅ 测试完成后立即撤销令牌

## 配置步骤

### 1. 创建配置文件

复制示例文件创建配置:

```bash
cp .env.apaas.example .env.apaas
```

### 2. 获取用户访问令牌

aPaaS 需要 `user_access_token`。通过飞书开放平台获取:

**方法1: OAuth 2.0 授权流程(推荐生产环境)**
- 访问: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/authen-v1/authen/access_token
- 按照文档完成 OAuth 授权流程
- 请求作用域: `apaas:workspace.table:read`, `apaas:workspace.table:write`

**方法2: 手动生成(开发测试)**
- 登录飞书开发者后台
- 选择应用 → 权限与范围
- 开启 aPaaS 工作空间权限
- 生成用户访问令牌
- **注意:** 手动令牌有效期短,仅用于开发测试

### 3. 配置测试工作空间

创建专用测试工作空间:

1. 登录飞书 aPaaS 平台
2. 创建新工作空间: "集成测试工作空间"
3. 创建测试表,包含以下字段:
   - 文本字段(如"名称")
   - 数字字段(如"数量")
   - 单选字段(如"状态")
4. 复制工作空间 ID(格式: `ws_xxx`)
5. 复制表 ID(格式: `tbl_xxx`)

### 4. 填写配置文件

编辑 `.env.apaas`:

```bash
# 应用凭据
TEST_APAAS_APP_ID=cli_a1b2c3d4e5f6g7h8
TEST_APAAS_APP_SECRET=your_app_secret_here

# 用户访问令牌
TEST_APAAS_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxxxxx

# 测试工作空间和表ID
TEST_APAAS_WORKSPACE_ID=ws_a1b2c3d4e5f6g7h8
TEST_APAAS_TABLE_ID=tbl_a1b2c3d4e5f6g7h8
```

### 5. 验证配置

检查 `.env.apaas` 是否正确被 Git 忽略:

```bash
git status .env.apaas
# 应输出: "nothing to commit" (文件被忽略)
```

## 运行测试

### 运行所有 aPaaS 集成测试

```bash
pytest tests/integration/test_apaas_e2e.py -v
```

### 运行特定测试类

```bash
# 仅读操作
pytest tests/integration/test_apaas_e2e.py::TestWorkspaceTableReadOperations -v

# 仅写操作
pytest tests/integration/test_apaas_e2e.py::TestWorkspaceTableWriteOperations -v

# 仅批量操作
pytest tests/integration/test_apaas_e2e.py::TestWorkspaceTableBatchOperations -v
```

### 跳过 aPaaS 测试

aPaaS 测试在以下情况自动跳过:
- `.env.apaas` 文件不存在
- 任何必需的环境变量缺失
- 方法尚未实现(NotImplementedError)

## 测试覆盖

### 当前状态(Phase 5)

所有测试当前**已跳过**,原因:
- WorkspaceTableClient 方法是占位符实现
- 真实 API 调用将在后续阶段添加

### 计划测试场景

**读操作:**
- `test_list_workspace_tables` - 列出工作空间中的表
- `test_list_fields` - 获取字段定义
- `test_query_records_no_filter` - 无过滤查询
- `test_query_records_with_filter` - 带过滤表达式查询

**写操作:**
- `test_create_and_delete_record` - 创建和清理
- `test_update_record` - 更新现有记录

**批量操作:**
- `test_batch_create_records` - 批量创建(5条记录)
- `test_batch_update_records` - 批量更新(3条记录)

## 故障排除

### 错误: "缺少 aPaaS 测试配置"

**原因:** `.env.apaas` 未找到或不完整

**解决方案:**
```bash
# 检查文件是否存在
ls -la .env.apaas

# 验证所有变量已设置
grep TEST_APAAS .env.apaas
```

### 错误: "权限被拒绝" 或 "403 Forbidden"

**原因:** 权限不足或令牌过期

**解决方案:**
1. 验证令牌是 `user_access_token`(非 `tenant_access_token`)
2. 检查令牌是否过期
3. 验证用户具有工作空间权限
4. 如需要重新生成令牌

### 错误: "无效的 workspace_id 或 table_id"

**原因:** ID 格式错误或资源不存在

**解决方案:**
1. 验证 ID 格式: `ws_xxx` 用于工作空间,`tbl_xxx` 用于表
2. 检查 ID 在飞书 aPaaS 平台中存在
3. 确保用户有权访问指定的工作空间/表

### 配置后测试仍被跳过

**原因:** WorkspaceTableClient 方法尚未实现

**解决方案:**
- 这是 Phase 5 的预期行为
- 方法当前是占位符实现(抛出 `NotImplementedError`)
- 真实 API 实现将在后续阶段添加
- 方法实现后测试将自动运行

## 安全检查清单

测试前验证:

- [ ] `.env.apaas` 存在且配置正确
- [ ] `.env.apaas` 在 `.gitignore` 中
- [ ] 使用专用测试工作空间(非生产环境)
- [ ] 令牌具有最小必需权限
- [ ] 监控令牌过期时间
- [ ] 备份凭据已安全存储

测试后:

- [ ] 查看工作空间中创建的测试数据
- [ ] 如需要清理测试记录
- [ ] 如令牌暴露或泄露则轮换令牌
- [ ] 记录任何安全事件

## 相关文档

- [aPaaS API 规范](../specs/001-lark-service-core/contracts/apaas.yaml)
- [集成测试指南](./integration-test-guide.md)
- [飞书 aPaaS 文档](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list)

## 支持

如遇问题:
1. 查阅飞书开放平台文档
2. 查看测试日志: `pytest tests/integration/test_apaas_e2e.py -v -s`
3. 在飞书开发者控制台验证令牌权限
4. 如为 API 问题,联系飞书开放平台支持
