# Phase 5 aPaaS 实现任务交接文档

## 📋 任务概述

**目标**: 完成 Phase 5 - aPaaS 数据空间集成的真实 API 调用实现

**当前状态**: 基础架构完成 100%,真实 API 实现进行中

**预计完成时间**: 30-45 分钟

---

## ✅ 已完成工作

### 1. 基础设施 (100%)
- ✅ aPaaS 数据模型 (`WorkspaceTable`, `TableRecord`, `FieldDefinition`)
- ✅ FieldType 枚举 (14种字段类型)
- ✅ API 契约 (`specs/001-lark-service-core/contracts/apaas.yaml` v0.2.0)
- ✅ 单元测试框架 (26个测试 - `tests/unit/apaas/test_client.py`)
- ✅ 契约测试 (28个测试 - `tests/contract/test_apaas_contract.py`)
- ✅ 集成测试框架 (8个测试 - `tests/integration/test_apaas_e2e.py`)
- ✅ 安全配置 (`.env.apaas` + `.gitignore`)
- ✅ 中文文档 (`docs/apaas-test-guide.md`)

### 2. 验证函数 (100% - Commit 81fadce)
- ✅ `validate_non_empty_string()` - 验证非空字符串
- ✅ `validate_non_negative_int()` - 验证非负整数(支持min/max)
- ✅ 已导出到 `src/lark_service/utils/__init__.py`
- ✅ 通过所有代码质量检查 (ruff, mypy, bandit)

### 3. 配置和文档
- ✅ `.env.apaas` 配置已验证(用户已填写实际值)
- ✅ `apaas-test-guide.md` 已转为中文(符合宪章原则IX)
- ✅ 测试框架已验证可运行

---

## 🎯 待完成任务

### 核心任务: 实现 WorkspaceTableClient 的 8 个 API 方法

**文件**: `src/lark_service/apaas/client.py` (当前520行,所有方法都是 `NotImplementedError` 占位符)

**需要实现的方法**:

1. **`list_workspace_tables()`** - 列出工作空间的所有表
   - API: `GET /apaas/v1/workspaces/{workspace_id}/tables`
   - 参数验证: `app_id`, `user_access_token`, `workspace_id`

2. **`list_fields()`** - 获取表的字段定义
   - API: `GET /apaas/v1/tables/{table_id}/fields`
   - 参数验证: `app_id`, `user_access_token`, `table_id`

3. **`query_records()`** - 查询记录(支持过滤和分页)
   - API: `POST /apaas/v1/tables/{table_id}/records/query`
   - 参数: `filter_expr` (URL编码), `page_token`, `page_size`
   - 返回: `(records, next_page_token, has_more)`

4. **`create_record()`** - 创建单条记录
   - API: `POST /apaas/v1/tables/{table_id}/records`
   - Body: `{"fields": {...}}`

5. **`update_record()`** - 更新单条记录
   - API: `PUT /apaas/v1/tables/{table_id}/records/{record_id}`
   - Body: `{"fields": {...}}`

6. **`delete_record()`** - 删除单条记录
   - API: `DELETE /apaas/v1/tables/{table_id}/records/{record_id}`

7. **`batch_create_records()`** - 批量创建记录(最多500条)
   - API: `POST /apaas/v1/tables/{table_id}/records/batch`
   - Body: `{"records": [{"fields": {...}}, ...]}`

8. **`batch_update_records()`** - 批量更新记录(最多500条)
   - API: `PUT /apaas/v1/tables/{table_id}/records/batch`
   - Body: `{"records": [{"record_id": "xxx", "fields": {...}}, ...]}`

---

## 🔧 技术实现要点

### 1. 必需的导入

```python
import urllib.parse
from typing import Any

import requests

from lark_service.apaas.models import (
    FieldDefinition,
    FieldType,
    TableRecord,
    WorkspaceTable,
)
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
    PermissionDeniedError,
)
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger
from lark_service.utils.validators import (
    validate_app_id,
    validate_non_empty_string,
    validate_non_negative_int,
)
```

### 2. 常量定义

```python
# Feishu aPaaS API base URL
APAAS_API_BASE = "https://open.feishu.cn/open-apis"

# Field type mapping from API response to FieldType enum
FIELD_TYPE_MAP = {
    1: FieldType.TEXT,
    2: FieldType.NUMBER,
    3: FieldType.SINGLE_SELECT,
    4: FieldType.MULTI_SELECT,
    5: FieldType.DATE,
    6: FieldType.DATETIME,
    7: FieldType.CHECKBOX,
    11: FieldType.PERSON,
    13: FieldType.PHONE,
    15: FieldType.EMAIL,
    17: FieldType.URL,
    18: FieldType.ATTACHMENT,
    19: FieldType.LINK,
    20: FieldType.FORMULA,
    21: FieldType.LOOKUP,
}
```

### 3. 辅助方法

需要在 `WorkspaceTableClient` 类中添加:

```python
def _handle_api_error(self, result: dict[str, Any], method_name: str) -> None:
    """Handle API error responses and raise appropriate exceptions."""
    code = result.get("code", -1)
    msg = result.get("msg", "Unknown error")

    logger.error(
        f"aPaaS API error in {method_name}",
        extra={"code": code, "msg": msg, "method": method_name},
    )

    # Map Feishu error codes to custom exceptions
    if code in (99991400, 99991401, 99991663):  # Authentication/permission errors
        raise PermissionDeniedError(f"Permission denied: {msg}")
    if code in (99991404, 230002):  # Not found errors
        raise NotFoundError(f"Resource not found: {msg}")
    if code in (99991402, 99991403):  # Invalid parameter errors
        raise InvalidParameterError(f"Invalid parameter: {msg}")

    # Generic API error
    raise APIError(f"aPaaS API error ({code}): {msg}")
```

### 4. HTTP 请求模板

```python
try:
    url = f"{APAAS_API_BASE}/apaas/v1/..."
    headers = {
        "Authorization": f"Bearer {user_access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get/post/put/delete(url, headers=headers, json=body, timeout=30)
    result = response.json()

    if result.get("code") != 0:
        self._handle_api_error(result, "method_name")

    # Process response data...

except requests.RequestException as e:
    logger.error(f"Network error: {e}")
    raise APIError(f"Failed to ...: {e}") from e
```

### 5. 参数验证模式

```python
validate_app_id(app_id)
validate_non_empty_string(user_access_token, "user_access_token")
validate_non_empty_string(table_id, "table_id")
validate_non_negative_int(page_size, "page_size", min_value=1, max_value=500)
```

---

## 📝 实现步骤建议

### 步骤 1: 准备工作
1. 检查 `client.py` 当前状态
2. 添加必需的导入和常量
3. 添加 `_handle_api_error` 辅助方法

### 步骤 2: 实现方法 (按顺序)
1. 实现 `list_workspace_tables()` (最简单,用于验证流程)
2. 实现 `list_fields()` (类似的GET请求)
3. 实现 `query_records()` (POST请求,处理分页)
4. 实现 `create_record()` (POST请求,返回单个记录)
5. 实现 `update_record()` (PUT请求)
6. 实现 `delete_record()` (DELETE请求,无返回值)
7. 实现 `batch_create_records()` (批量POST)
8. 实现 `batch_update_records()` (批量PUT)

### 步骤 3: 代码质量检查
```bash
ruff format src/lark_service/apaas/client.py
ruff check src/lark_service/apaas/client.py --fix
mypy src/lark_service/apaas/client.py
```

### 步骤 4: 运行集成测试
```bash
pytest tests/integration/test_apaas_e2e.py -v
```

### 步骤 5: 修复问题并重测

### 步骤 6: 提交代码
```bash
git add src/lark_service/apaas/client.py
git commit -m "feat(apaas): implement WorkspaceTableClient real API calls"
```

---

## 🧪 测试验证

### 集成测试配置
- 配置文件: `.env.apaas`
- 测试文件: `tests/integration/test_apaas_e2e.py`
- 当前所有测试都是 `@pytest.mark.skip` 状态

### 预期测试结果
实现完成后,所有8个集成测试应该能够运行:
- 4个读操作测试
- 2个写操作测试
- 2个批量操作测试

### 可能的问题
1. **API 端点可能不完全匹配** - 需要参考飞书最新文档调整
2. **字段类型映射** - `FIELD_TYPE_MAP` 可能需要补充
3. **错误码映射** - 可能需要添加更多飞书错误码
4. **数据格式** - API 响应格式可能与预期不同

---

## 📚 参考资料

### 官方文档
- 飞书 aPaaS API 文档: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list
- 工作空间表操作: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/records_query

### 项目文档
- API 契约: `specs/001-lark-service-core/contracts/apaas.yaml`
- 规格说明: `specs/001-lark-service-core/spec.md` (FR-071 到 FR-089)
- 测试指南: `docs/apaas-test-guide.md`
- 研究文档: `specs/001-lark-service-core/research.md` (第7章)

### 代码参考
- Bitable 实现: `src/lark_service/clouddoc/bitable/client.py` (类似的HTTP调用模式)
- CloudDoc 实现: `src/lark_service/clouddoc/client.py` (错误处理参考)

---

## 🎯 成功标准

完成后应满足:
- ✅ 所有8个方法实现完成(无 `NotImplementedError`)
- ✅ 通过代码质量检查 (ruff, mypy)
- ✅ 至少部分集成测试能够运行(根据实际API可用性)
- ✅ 代码已提交到 Git
- ✅ 生成 Phase 5 完成报告

---

## 🚀 下一会话启动 Prompt

```
继续 Phase 5 aPaaS 功能开发。

当前状态:
- 基础架构已完成(模型、测试、文档、配置)
- Validators 已实现并提交 (Commit: 81fadce)
- 需要实现 WorkspaceTableClient 的8个API方法

请执行:
1. 阅读 @docs/phase5-implementation-handoff.md 了解详细任务
2. 实现 @src/lark_service/apaas/client.py 的8个方法
3. 运行集成测试 tests/integration/test_apaas_e2e.py
4. 修复问题并提交代码

参考:
- 技术要点见交接文档
- API 文档: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list
- 测试配置: .env.apaas 已填写实际值
```

---

## 📌 注意事项

1. **Token使用** - 确保使用 `user_access_token` (不是 `tenant_access_token`)
2. **URL编码** - `filter_expr` 需要使用 `urllib.parse.quote()`
3. **超时设置** - 普通请求30秒,批量请求60秒
4. **日志记录** - 每个方法都需要记录关键信息
5. **宪章合规** - 遵循原则II(代码质量)和原则XI(Git提交规范)

---

**文档版本**: 1.0
**创建时间**: 2026-01-17
**最后更新**: 2026-01-17
**创建者**: AI Assistant
**下次会话**: 继续实现真实API调用
