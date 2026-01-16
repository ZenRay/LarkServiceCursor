# 表结构查询功能规范

## 概述

为了更好地支持 Bitable 和 Sheet 的操作，需要添加表结构查询功能。这样可以：

1. **获取正确的 field_name** - Bitable 过滤需要使用 field_name（注意：实际 API 使用 field_name 而不是 field_id）
2. **验证字段是否存在** - 在操作前验证字段，提供更好的错误提示
3. **了解字段类型** - 根据字段类型构造正确的数据
4. **获取 sheet_id** - Sheet 操作需要正确的 sheet_id

## Bitable 表结构查询

### 新增 API 方法

#### `get_table_fields(app_id, app_token, table_id) -> list[TableField]`

获取 Bitable 表的所有字段信息。

**参数:**
- `app_id` (str): 应用 ID
- `app_token` (str): Bitable 应用 token
- `table_id` (str): 数据表 ID

**返回:**
```python
[
    {
        "field_id": "fldV0OLjFj",      # 字段 ID（用于识别）
        "field_name": "文本",           # 字段名称（用于过滤）
        "field_name": "文本",           # 字段名称（显示用）
        "type": 1,                      # 字段类型
        "type_name": "文本",            # 类型名称
        "description": "文本字段",      # 字段描述（可选）
        "property": {...}               # 字段属性（可选）
    },
    ...
]
```

**字段类型映射:**
| type | type_name | 说明 |
|------|-----------|------|
| 1 | 文本 | 单行文本 |
| 2 | 数字 | 数字 |
| 3 | 单选 | 单选 |
| 4 | 多选 | 多选 |
| 5 | 日期 | 日期 |
| 7 | 复选框 | 复选框 |
| 11 | 人员 | 人员 |
| 13 | 电话号码 | 电话号码 |
| 15 | 超链接 | 超链接 |
| 17 | 附件 | 附件 |
| 18 | 关联 | 关联其他表 |
| 20 | 公式 | 公式 |
| 21 | 双向关联 | 双向关联 |

**API 端点:**
```
GET https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields
```

**错误处理:**
- `NotFoundError`: 表不存在
- `PermissionDeniedError`: 无权限访问
- `APIError`: API 调用失败

### 重构过滤功能

#### 新的过滤数据结构

使用结构化 JSON 而不是公式字符串：

```python
class StructuredFilterCondition(BaseModel):
    """Bitable 过滤条件（结构化）"""
    field_name: str        # 字段名称（注意：使用 field_name 而不是 field_id！）
    operator: Literal[
        "is",              # 等于
        "isNot",           # 不等于
        "contains",        # 包含
        "doesNotContain",  # 不包含
        "isEmpty",         # 为空
        "isNotEmpty",      # 不为空
        "isGreater",       # 大于
        "isGreaterEqual",  # 大于等于
        "isLess",          # 小于
        "isLessEqual",     # 小于等于
    ]
    value: list[Any]       # 值（必须是数组）

class StructuredFilterInfo(BaseModel):
    """Bitable 过滤信息"""
    conjunction: Literal["and", "or"] = "and"
    conditions: list[StructuredFilterCondition]
```

#### 新增的 `query_records_structured()` 方法

```python
def query_records_structured(
    app_id: str,
    app_token: str,
    table_id: str,
    filter_info: StructuredFilterInfo | None = None,  # 使用结构化对象
    page_size: int = 100,
    page_token: str | None = None,
) -> tuple[list[BaseRecord], str | None]:
    """查询记录（使用结构化过滤，推荐）"""
    pass
```

**使用示例:**

```python
# 1. 先获取字段信息
fields = bitable_client.get_table_fields(
    app_id="cli_xxx",
    app_token="bascnxxx",
    table_id="tblxxx"
)

# 2. 找到目标字段的 field_id
text_field = next(f for f in fields if f["field_name"] == "文本")
field_id = text_field["field_id"]  # "fldV0OLjFj"

# 3. 构造过滤条件
filter_info = FilterInfo(
    conjunction="and",
    conditions=[
        FilterCondition(
            field_id=field_id,
            operator="is",
            value=["Active"]
        )
    ]
)

# 4. 查询记录
records, next_token = bitable_client.query_records(
    app_id="cli_xxx",
    app_token="bascnxxx",
    table_id="tblxxx",
    filter_info=filter_info
)
```

## Sheet 表结构查询

### 新增 API 方法

#### `get_sheet_info(app_id, spreadsheet_token) -> list[SheetInfo]`

获取电子表格的所有工作表信息。

**参数:**
- `app_id` (str): 应用 ID
- `spreadsheet_token` (str): 电子表格 token

**返回:**
```python
[
    {
        "sheet_id": "a3fb01",           # 工作表 ID（用于数据操作）
        "title": "Sheet1",              # 工作表标题
        "index": 0,                     # 工作表索引
        "row_count": 200,               # 行数
        "column_count": 20,             # 列数
        "hidden": False,                # 是否隐藏
        "resource_type": "sheet"        # 资源类型
    },
    ...
]
```

**API 端点:**
```
GET https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query
```

**错误处理:**
- `NotFoundError`: 电子表格不存在
- `PermissionDeniedError`: 无权限访问
- `APIError`: API 调用失败

**使用示例:**

```python
# 1. 获取工作表信息
sheets = sheet_client.get_sheet_info(
    app_id="cli_xxx",
    spreadsheet_token="shtcnxxx"
)

# 2. 选择目标工作表
sheet = sheets[0]  # 第一个工作表
sheet_id = sheet["sheet_id"]  # "a3fb01"

# 3. 读取数据
data = sheet_client.get_sheet_data(
    app_id="cli_xxx",
    spreadsheet_token="shtcnxxx",
    sheet_id=sheet_id,
    range_str="A1:C10"
)
```

## 实现计划

### Phase 1: 添加表结构查询 API

**Bitable:**
1. ✅ 添加 `TableField` 数据模型
2. ✅ 实现 `get_table_fields()` 方法
3. ✅ 添加字段类型映射
4. ✅ 添加单元测试

**Sheet:**
1. ✅ 添加 `SheetInfo` 数据模型
2. ✅ 实现 `get_sheet_info()` 方法
3. ✅ 添加单元测试

### Phase 2: 重构过滤功能

**Bitable:**
1. ✅ 添加新的 `StructuredFilterCondition` 和 `StructuredFilterInfo` 模型
2. ✅ 新增 `query_records_structured()` 使用结构化过滤
3. ✅ 保留旧的 `query_records()` API（向后兼容）
4. ✅ 更新单元测试
5. ✅ 更新集成测试

### Phase 3: 更新文档和测试

1. ✅ 更新 API 文档
2. ✅ 添加使用示例
3. ✅ 更新集成测试以使用新 API
4. ✅ 添加错误处理测试

## 测试策略

### 单元测试

**Bitable:**
- `test_get_table_fields_success` - 成功获取字段
- `test_get_table_fields_not_found` - 表不存在
- `test_query_records_with_structured_filter` - 使用结构化过滤
- `test_filter_condition_validation` - 过滤条件验证

**Sheet:**
- `test_get_sheet_info_success` - 成功获取工作表
- `test_get_sheet_info_not_found` - 电子表格不存在
- `test_get_sheet_info_multiple_sheets` - 多个工作表

### 集成测试

**Bitable:**
1. 获取表字段信息
2. 使用 field_name 构造过滤条件（注意：实际 API 需要 field_name 而不是 field_id）
3. 查询记录并验证结果
4. 测试多个过滤条件的组合

**Sheet:**
1. 获取工作表信息
2. 使用正确的 sheet_id 读取数据
3. 测试多个工作表的场景

## API 兼容性

### 向后兼容

为了保持向后兼容，旧的 `query_records()` API 仍然可用，但会在文档中标记为 deprecated：

```python
# 旧 API（deprecated）
def query_records(
    app_id: str,
    app_token: str,
    table_id: str,
    filter_conditions: list[FilterCondition] | None = None,  # 旧格式
    ...
) -> tuple[list[BaseRecord], str | None]:
    """
    查询记录

    Warning:
        filter_conditions 参数已废弃，请使用 filter_info 参数。
        旧的 filter_conditions 使用 field_name，新的 filter_info 使用 field_id。
    """
    pass
```

### 迁移指南

**从旧 API 迁移到新 API:**

```python
# 旧方式（不推荐）
filter_conditions = [
    FilterCondition(field_name="文本", operator="eq", value="Active")
]
records, _ = bitable_client.query_records(
    app_id=app_id,
    app_token=app_token,
    table_id=table_id,
    filter_conditions=filter_conditions  # 使用字段名
)

# 新方式（推荐）
# 1. 获取字段信息
fields = bitable_client.get_table_fields(app_id, app_token, table_id)
field_name = next(f["field_name"] for f in fields if f["field_name"] == "文本")

# 2. 使用 field_name 构造过滤
filter_info = StructuredFilterInfo(
    conjunction="and",
    conditions=[
        StructuredFilterCondition(field_name=field_name, operator="is", value=["Active"])
    ]
)

# 3. 查询
records, _ = bitable_client.query_records_structured(
    app_id=app_id,
    app_token=app_token,
    table_id=table_id,
    filter_info=filter_info  # 使用 field_name
)
```

## 参考文档

- [Bitable 列出字段 API](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list)
- [Bitable 查询记录 API](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/search)
- [Sheet 查询工作表 API](https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet-sheet/query)
- [Bitable 更新数据表 API](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/patch?appId=cli_a8d27f9bf635500e)
