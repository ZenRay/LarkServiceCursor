# Phase 2 实施计划

**计划日期**: 2026-01-21
**预计时间**: 2-3小时
**任务**: T005-T008 (CloudDoc + aPaaS + 文档)

---

## 📋 任务概览

### Phase 2 目标
完成剩余两个客户端的重构,并补充完整的文档和示例。

### 任务列表
- **T005**: 重构 CloudDoc 客户端 (DocClient) - 7个方法
- **T006**: 重构 aPaaS 客户端 (WorkspaceTableClient) - 10个方法
- **T007**: 集成测试补充 (CloudDoc + aPaaS + 跨客户端)
- **T008**: 文档创建和更新

---

## 🎯 T005: 重构 DocClient

### 现状分析
```python
class DocClient:
    def __init__(self, credential_pool, retry_strategy=None):
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()
        # ❌ 未继承 BaseServiceClient
```

### 重构目标
```python
from lark_service.core.base_service_client import BaseServiceClient

class DocClient(BaseServiceClient):
    def __init__(
        self,
        credential_pool: CredentialPool,
        app_id: str | None = None,  # ✅ 新增
        retry_strategy: RetryStrategy | None = None,
    ):
        super().__init__(credential_pool, app_id)  # ✅ 调用基类
        self.retry_strategy = retry_strategy or RetryStrategy()
```

### 需要重构的方法

#### 1. create_document
```python
# Before:
def create_document(
    self,
    app_id: str,
    title: str,
    folder_token: str | None = None,
) -> Document:

# After:
def create_document(
    self,
    title: str,
    folder_token: str | None = None,
    app_id: str | None = None,
) -> Document:
    resolved_app_id = self._resolve_app_id(app_id)
    # ... 使用 resolved_app_id
```

#### 2. get_document
```python
# Before:
def get_document(self, app_id: str, doc_id: str) -> Document:

# After:
def get_document(
    self,
    doc_id: str,
    app_id: str | None = None,
) -> Document:
    resolved_app_id = self._resolve_app_id(app_id)
```

#### 3-7. 其他方法 (相同模式)
- `get_document_content()`
- `append_block()`
- `update_block()`
- `batch_update_block()`
- `get_document_raw_content()`

### 实施步骤
1. ✅ 修改 `__init__` 继承 BaseServiceClient
2. ✅ 更新 `create_document` 方法签名
3. ✅ 更新 `get_document` 方法签名
4. ✅ 更新其他 5 个方法
5. ✅ 更新所有 docstring 示例
6. ✅ 运行 mypy 检查
7. ✅ 运行 ruff 格式化
8. ✅ 提交代码

### 预计时间
30-40 分钟

---

## 🎯 T006: 重构 WorkspaceTableClient

### 现状分析
```python
class WorkspaceTableClient:
    def __init__(self, credential_pool, retry_strategy=None):
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()
        # ❌ 未继承 BaseServiceClient
```

### 特殊注意事项
⚠️ **重要**: 所有方法都需要 `user_access_token` 参数!

```python
# Before:
def list_workspace_tables(
    self,
    app_id: str,
    user_access_token: str,  # ← 必需!
    workspace_id: str,
    ...
) -> list[WorkspaceTable]:

# After:
def list_workspace_tables(
    self,
    user_access_token: str,  # ← 保持为必需参数
    workspace_id: str,
    page_token: str | None = None,
    page_size: int = 20,
    app_id: str | None = None,  # ← 移到最后,变为可选
) -> list[WorkspaceTable]:
    resolved_app_id = self._resolve_app_id(app_id)
```

### 需要重构的方法 (10个)

#### 读取操作 (4个)
1. `list_workspace_tables()` - 列出所有表
2. `get_workspace_table()` - 获取表信息
3. `list_table_records()` - 列出记录 (带分页)
4. `get_table_record()` - 获取单个记录

#### 写入操作 (3个)
5. `create_table_record()` - 创建记录
6. `update_table_record()` - 更新记录
7. `delete_table_record()` - 删除记录

#### 批量操作 (3个)
8. `batch_create_records()` - 批量创建
9. `batch_update_records()` - 批量更新
10. `batch_delete_records()` - 批量删除

### 重构模式
```python
def method_name(
    self,
    user_access_token: str,  # ← 始终第一个 (业务必需)
    # ... 其他业务参数 ...
    app_id: str | None = None,  # ← 始终最后 (可选)
) -> ReturnType:
    resolved_app_id = self._resolve_app_id(app_id)
    # ... 使用 resolved_app_id 和 user_access_token
```

### 实施步骤
1. ✅ 修改 `__init__` 继承 BaseServiceClient
2. ✅ 更新 4 个读取方法
3. ✅ 更新 3 个写入方法
4. ✅ 更新 3 个批量方法
5. ✅ 更新所有 docstring 示例
6. ✅ 运行 mypy 检查
7. ✅ 运行 ruff 格式化
8. ✅ 提交代码

### 预计时间
40-50 分钟

---

## 🎯 T007: 集成测试补充

### 测试目标
验证 CloudDoc 和 aPaaS 客户端的应用切换功能。

### 测试文件
`tests/integration/test_app_switching_clouddoc_apaas.py`

### 测试场景

#### 1. CloudDoc 客户端测试 (5个)
```python
class TestCloudDocAppSwitching:
    def test_single_app_create_document(self):
        """测试单应用场景下创建文档"""

    def test_multi_app_factory_method(self):
        """测试工厂方法指定 app_id"""

    def test_multi_app_context_manager(self):
        """测试上下文管理器切换应用"""

    def test_method_parameter_override(self):
        """测试方法参数覆盖优先级"""

    def test_error_handling(self):
        """测试错误处理"""
```

#### 2. aPaaS 客户端测试 (5个)
```python
class TestWorkspaceTableAppSwitching:
    def test_single_app_list_tables(self):
        """测试单应用场景下列出表"""

    def test_multi_app_with_user_token(self):
        """测试多应用 + user_access_token 组合"""

    def test_context_manager_with_user_token(self):
        """测试上下文管理器 + user_access_token"""

    def test_batch_operations(self):
        """测试批量操作的 app_id 解析"""

    def test_error_handling(self):
        """测试错误处理"""
```

#### 3. 跨客户端测试 (3个)
```python
class TestCrossClientAppSwitching:
    def test_different_clients_same_pool(self):
        """测试同一个 pool 创建的不同客户端"""

    def test_nested_contexts_different_clients(self):
        """测试不同客户端的嵌套上下文"""

    def test_pool_default_affects_all_clients(self):
        """测试 pool 默认值影响所有客户端"""
```

### 实施步骤
1. ✅ 创建测试文件
2. ✅ 实现 CloudDoc 测试 (5个)
3. ✅ 实现 aPaaS 测试 (5个)
4. ✅ 实现跨客户端测试 (3个)
5. ✅ 运行所有测试确保通过
6. ✅ 提交代码

### 预计时间
30-40 分钟

---

## 🎯 T008: 文档创建和更新

### 需要创建的文档

#### 1. `docs/usage/app-management.md` (新建)
**内容结构**:
```markdown
# 应用管理指南

## 概述
## 单应用场景
### 自动检测
### 显式设置
## 多应用场景
### 工厂方法
### 上下文管理器
### 方法参数
## 优先级机制
## 调试方法
## 最佳实践
## 常见问题
```

#### 2. `docs/usage/advanced.md` (补充)
**当前状态**: 几乎为空
**需要补充**:
- 应用切换高级场景
- 嵌套上下文使用
- 多线程注意事项
- 性能优化建议
- 自定义 app_id 解析策略

#### 3. 更新现有使用指南
需要在每个模块的使用指南中添加"应用管理"章节:
- `docs/usage/messaging.md`
- `docs/usage/contact.md`
- `docs/usage/clouddoc.md`
- `docs/usage/apaas.md`

**添加内容** (统一模板):
```markdown
## 应用管理

### 单应用场景
当只有一个应用时,无需显式指定 app_id:
\`\`\`python
# 自动使用默认 app_id
client.method(param="value")
\`\`\`

### 多应用场景
详见 [应用管理指南](app-management.md)
```

### 代码示例验证
创建 `scripts/validate_docs_examples.py`:
```python
"""Validate all code examples in documentation."""
import ast
import re
from pathlib import Path

def extract_code_blocks(md_file):
    """Extract Python code blocks from markdown."""
    # ...

def validate_syntax(code):
    """Validate Python syntax."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False

# ... 遍历所有文档验证
```

### 实施步骤
1. ✅ 创建 `docs/usage/app-management.md`
2. ✅ 补充 `docs/usage/advanced.md`
3. ✅ 更新 4 个现有使用指南
4. ✅ 创建示例验证脚本
5. ✅ 运行验证确保所有示例正确
6. ✅ 生成文档审查报告
7. ✅ 提交代码

### 预计时间
40-50 分钟

---

## 📅 实施时间表

### 总体安排
```
T005 (DocClient):              30-40分钟
T006 (WorkspaceTableClient):   40-50分钟
T007 (集成测试):               30-40分钟
T008 (文档):                   40-50分钟
--------------------------------
总计:                          140-180分钟 (2.3-3小时)
```

### 详细步骤
```
0:00 - 0:40   T005 DocClient 重构
0:40 - 0:50   提交并审查
0:50 - 1:40   T006 WorkspaceTableClient 重构
1:40 - 1:50   提交并审查
1:50 - 2:30   T007 集成测试
2:30 - 2:40   提交并审查
2:40 - 3:30   T008 文档创建
3:30 - 3:40   最终审查和提交
```

---

## ✅ 成功标准

### 代码质量
- [ ] 所有客户端继承 BaseServiceClient
- [ ] 所有方法 app_id 参数改为可选
- [ ] 100% mypy strict 通过
- [ ] 100% ruff 通过
- [ ] 100% ruff-format 通过

### 测试质量
- [ ] CloudDoc 集成测试 5/5 通过
- [ ] aPaaS 集成测试 5/5 通过
- [ ] 跨客户端测试 3/3 通过
- [ ] 总计 13 个新测试全部通过

### 文档质量
- [ ] app-management.md 完整且可运行
- [ ] advanced.md 补充完成
- [ ] 4 个使用指南已更新
- [ ] 所有示例代码已验证
- [ ] 生成验证报告

---

## 🚀 开始执行

准备就绪!按照以下顺序执行:

1. **T005**: DocClient 重构 ✅
2. **T006**: WorkspaceTableClient 重构 ✅
3. **T007**: 集成测试补充 ✅
4. **T008**: 文档创建和更新 ✅

每个任务完成后:
1. 运行代码检查 (mypy, ruff)
2. 运行相关测试
3. 使用 `scripts/git-add-check.sh` 提交
4. 生成进度报告

---

**Phase 2 开始!** 🚀
