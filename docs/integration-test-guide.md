# 集成测试指南

本文档说明如何配置和运行 Lark Service 的集成测试(真实API测试)。

## 📋 测试分类

### 1. 单元测试 (Unit Tests)
- **位置**: `tests/unit/`
- **特点**: 使用mock,不需要真实API凭证
- **运行**: `pytest tests/unit/`
- **状态**: ✅ 199 passed, 29 skipped (100%通过率)

### 2. 集成测试 (Integration Tests)
- **位置**: `tests/integration/`
- **特点**: 使用真实Lark API,需要配置凭证
- **运行**: `pytest tests/integration/`
- **状态**: ✅ 28 passed, 3 skipped

## 🔧 配置集成测试环境

### 步骤1: 创建配置文件

```bash
# 复制示例配置文件
cp docs/env.test.example .env.test
```

### 步骤2: 填写必需的配置

编辑 `.env.test` 文件,至少填写以下必需项:

```bash
# 飞书应用凭证 (必需)
TEST_APP_ID=cli_xxxxxxxxxxxxxxxxxx
TEST_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 步骤3: 填写模块测试数据(可选)

根据你要测试的模块,填写相应的测试数据:

#### Contact模块测试
```bash
TEST_USER_EMAIL=test@yourcompany.com
TEST_USER_MOBILE=+8613800138000
TEST_USER_ID=ou_xxxxxxxxxxxxxxxxxx
TEST_DEPARTMENT_ID=od_xxxxxxxxxxxxxxxxxx
TEST_CHAT_ID=oc_xxxxxxxxxxxxxxxxxx
```

#### CloudDoc模块测试
```bash
# 文档测试
TEST_DOC_TOKEN=doxcnxxxxxxxxxxxxxxxxxx

# Bitable测试
TEST_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxxxxxxx
TEST_WRITABLE_BITABLE_TOKEN=bascnxxxxxxxxxxxxxxxxxx  # 写操作需要

# Sheet测试
TEST_SHEET_TOKEN=shtcnxxxxxxxxxxxxxxxxxx
TEST_WRITABLE_SHEET_TOKEN=shtcnxxxxxxxxxxxxxxxxxx  # 写操作需要
```

## 🚀 运行集成测试

### 运行所有集成测试
```bash
pytest tests/integration/ -v
```

### 运行特定模块的集成测试

#### Contact模块
```bash
pytest tests/integration/test_contact_e2e.py -v
```

#### CloudDoc模块
```bash
pytest tests/integration/test_clouddoc_e2e.py -v
```

#### Bitable模块
```bash
pytest tests/integration/test_bitable_e2e.py -v
```

#### Sheet模块
```bash
pytest tests/integration/test_sheet_e2e.py -v
```

### 运行特定测试类
```bash
# 只运行读操作测试
pytest tests/integration/test_bitable_e2e.py::TestBitableReadOperations -v

# 只运行写操作测试(需要写权限)
pytest tests/integration/test_bitable_e2e.py::TestBitableWriteOperations -v
```

## 📊 当前测试状态

### Contact模块 ✅
- **单元测试**: 23 passed (100%)
- **集成测试**: 8 passed
- **状态**: 完全实现,生产就绪

### CloudDoc - Doc客户端 ✅
- **单元测试**: 10 passed, 5 skipped
- **集成测试**: 20 passed, 3 skipped
- **状态**: 核心功能完全实现,生产就绪

### CloudDoc - Bitable客户端 ⚠️
- **单元测试**: 9 passed, 11 skipped
- **集成测试**: 新创建,需要配置后运行
- **状态**: 部分实现(query/create/update/delete已实现,batch操作为placeholder)
- **真实API实现**:
  - ✅ `query_records` - SDK实现
  - ✅ `create_record` - HTTP实现
  - ✅ `update_record` - HTTP实现
  - ✅ `delete_record` - HTTP实现
  - ⚠️ `batch_*` - Placeholder

### CloudDoc - Sheet客户端 ⚠️
- **单元测试**: 14 passed, 11 skipped
- **集成测试**: 新创建,但所有测试都skip(placeholder实现)
- **状态**: Placeholder实现,待开发

## 🔑 权限要求

### Contact模块权限
- `contact:user.email:readonly`
- `contact:user.phone:readonly`
- `contact:user.employee_id:readonly`
- `contact:user.id:readonly`
- `contact:department.list`
- `im:chat:readonly`

### CloudDoc模块权限

#### 读操作
- `docx:document:readonly`
- `bitable:app:readonly`
- `sheets:spreadsheet:readonly`

#### 写操作(可选)
- `docx:document`
- `bitable:app`
- `sheets:spreadsheet`

## 📝 测试数据准备

### 获取测试Token

1. **文档Token**:
   - 打开飞书文档,URL中的`doxcn...`部分

2. **Bitable Token**:
   - 打开多维表格,URL中的`bascn...`部分
   - 表格ID: 在多维表格中,URL中的`tbl...`部分

3. **Sheet Token**:
   - 打开电子表格,URL中的`shtcn...`部分

### 配置写权限测试

如果要测试写操作(create/update/delete):

1. 创建专门的测试文档/表格
2. 确保应用有写权限
3. 在`.env.test`中配置`TEST_WRITABLE_*`变量

## ⚠️ 注意事项

1. **不要提交 `.env.test`**: 该文件包含敏感信息,已在`.gitignore`中配置

2. **使用测试数据**: 不要在生产数据上运行写操作测试

3. **清理测试数据**: 写操作测试会自动清理创建的测试数据

4. **跳过的测试**:
   - 单元测试中skip的测试是因为需要真实API
   - 集成测试中skip的测试是因为缺少配置或功能未实现

5. **Bitable表格ID**:
   - 集成测试中的`tblXXXXXXXXXXXXXXXX`需要替换为实际的表格ID
   - 可以通过Bitable API获取表格列表

## 🐛 故障排查

### 测试被跳过
- 检查`.env.test`文件是否存在
- 检查必需的环境变量是否已配置
- 运行 `pytest tests/integration/ -v -s` 查看详细信息

### 认证失败
- 检查`TEST_APP_ID`和`TEST_APP_SECRET`是否正确
- 检查应用是否有相应的权限

### 找不到资源
- 检查Token是否正确(doc_token, bitable_token等)
- 检查应用是否有访问该资源的权限

### Bitable测试失败
- 确认`table_id`是否正确
- 确认表格字段名称(Name, Status等)与测试代码匹配
- 可以先运行`list_fields`获取表格结构

## 📚 相关文档

- [环境变量配置示例](./env.test.example)
- [Phase 4完成报告](./phase4-completion-report.md)
- [Phase 4检查清单](../specs/001-lark-service-core/checklists/phase4-completion-quality.md)
