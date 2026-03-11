# 云文档服务

云文档模块包含三类客户端：

- `DocClient`：云文档（文档创建、内容追加、权限管理）
- `SheetClient`：电子表格（读写、格式、冻结等）
- `BitableClient`：多维表格（记录 CRUD、字段、查询）

## 快速开始

```python
from lark_service.clouddoc import DocClient, SheetClient, BitableClient

doc_client = DocClient(credential_pool=credential_pool)
sheet_client = SheetClient(credential_pool=credential_pool)
bitable_client = BitableClient(credential_pool=credential_pool)
```

## 常用方法参数速查

### DocClient

| 方法 | 关键参数 | 返回值 |
| --- | --- | --- |
| `create_document()` | `title`, `folder_token?`, `app_id?` | `Document` |
| `append_content()` | `doc_id`, `blocks(<=100)`, `location?`, `app_id?` | `bool` |
| `get_document()` / `get_document_content()` | `doc_id`, `app_id?` | `Document` |
| `update_block()` | `doc_id`, `block_id`, `block`, `app_id?` | `bool` |
| `grant_permission()` | `doc_id`, `member_type`, `member_id`, `permission_type`, `app_id?` | `Permission` |
| `revoke_permission()` | `doc_id`, `permission_id`, `app_id?` | `bool` |
| `list_permissions()` | `doc_id`, `app_id?` | `list[Permission]` |

### SheetClient

| 方法 | 关键参数 | 返回值 |
| --- | --- | --- |
| `get_sheet_info()` | `app_id`, `spreadsheet_token` | `list[dict]` |
| `get_sheet_data()` | `app_id`, `spreadsheet_token`, `sheet_id`, `range_str` | `list[list[CellData]]` |
| `update_sheet_data()` | `app_id`, `spreadsheet_token`, `sheet_id`, `range_str`, `values` | `bool` |
| `append_data()` | `app_id`, `spreadsheet_token`, `sheet_id`, `range_str`, `values` | `bool` |
| `format_cells()` | `app_id`, `spreadsheet_token`, `sheet_id`, `range_str`, 样式参数 | `bool` |
| `merge_cells()` / `unmerge_cells()` | `app_id`, `spreadsheet_token`, `sheet_id`, `range_str` | `bool` |
| `set_column_width()` | `app_id`, `spreadsheet_token`, `sheet_id`, `start_column`, `end_column`, `width` | `bool` |
| `set_row_height()` | `app_id`, `spreadsheet_token`, `sheet_id`, `start_row`, `end_row`, `height` | `bool` |
| `freeze_panes()` / `unfreeze_panes()` | `app_id`, `spreadsheet_token`, `sheet_id` | `bool` |

### BitableClient

| 方法 | 关键参数 | 返回值 |
| --- | --- | --- |
| `create_record()` | `app_id`, `app_token`, `table_id`, `fields` | `BaseRecord` |
| `update_record()` | `app_id`, `app_token`, `table_id`, `record_id`, `fields` | `BaseRecord` |
| `delete_record()` | `app_id`, `app_token`, `table_id`, `record_id` | `bool` |
| `query_records()` | `app_id`, `app_token`, `table_id`, `filter_conditions?`, `page_size?`, `page_token?` | `(list[BaseRecord], next_page_token)` |
| `query_records_structured()` | `app_id`, `app_token`, `table_id`, `filter_info?`, `page_size?`, `page_token?` | `(list[BaseRecord], next_page_token)` |
| `batch_create_records()` | `app_id`, `app_token`, `table_id`, `records(<=500)` | `list[BaseRecord]` |
| `batch_update_records()` | `app_id`, `app_token`, `table_id`, `records(<=500)` | `list[BaseRecord]` |
| `batch_delete_records()` | `app_id`, `app_token`, `table_id`, `record_ids(<=500)` | `bool` |
| `get_table_fields()` / `list_fields()` | `app_id`, `app_token`, `table_id` | `list[dict]` / `list[FieldDefinition]` |

## 关键返回字段

| 返回模型 | 关键字段 | 说明 |
| --- | --- | --- |
| `Document` | `doc_id`, `title`, `owner_id`, `create_time`, `update_time` | 文档基础信息 |
| `Permission` | `doc_id`, `member_type`, `member_id`, `permission_type` | 文档权限记录 |
| `CellData` | `value`, `formula`, `number_format` | 表格单元格数据 |
| `BaseRecord` | `record_id`, `fields` | 多维表格记录 |
| `FieldDefinition` | `field_id`, `field_name`, `type` | 字段定义 |

## 文档（DocClient）

### 1) 创建文档

```python
doc = doc_client.create_document(
    title="项目周报",
    app_id="cli_xxx"
)
print(doc.doc_id, doc.title)
```

### 2) 追加内容

```python
from lark_service.clouddoc.models import ContentBlock

blocks = [
    ContentBlock(block_type="heading_1", content="本周进展"),
    ContentBlock(block_type="paragraph", content="已完成接口联调与回归验证。"),
]

ok = doc_client.append_content(
    doc_id="doxcn_xxx",
    blocks=blocks,
    app_id="cli_xxx"
)
print(ok)
```

### 3) 获取文档信息 / 内容

```python
doc = doc_client.get_document(doc_id="doxcn_xxx", app_id="cli_xxx")
print(doc.title)
```

### 4) 更新块内容

```python
from lark_service.clouddoc.models import ContentBlock

ok = doc_client.update_block(
    doc_id="doxcn_xxx",
    block_id="blk_xxx",
    block=ContentBlock(block_type="paragraph", content="这是更新后的内容"),
    app_id="cli_xxx"
)
print(ok)
```

### 5) 权限管理

```python
perm = doc_client.grant_permission(
    doc_id="doxcn_xxx",
    member_type="user",
    member_id="ou_xxx",
    permission_type="read",
    app_id="cli_xxx"
)
print(perm.permission_type)

permissions = doc_client.list_permissions(
    doc_id="doxcn_xxx",
    app_id="cli_xxx"
)
print(len(permissions))

# permission_id 以实际返回值为准
ok = doc_client.revoke_permission(
    doc_id="doxcn_xxx",
    permission_id="perm_xxx",
    app_id="cli_xxx"
)
print(ok)
```

## 电子表格（SheetClient）

### 1) 读取工作表元信息

```python
sheets = sheet_client.get_sheet_info(
    app_id="cli_xxx",
    spreadsheet_token="shtcn_xxx"
)
print(sheets[0]["sheet_id"], sheets[0]["title"])
```

### 2) 读取 / 更新 / 追加数据

```python
data = sheet_client.get_sheet_data(
    app_id="cli_xxx",
    spreadsheet_token="shtcn_xxx",
    sheet_id="a3fb01",
    range_str="A1:C10"
)
print(len(data))

ok = sheet_client.update_sheet_data(
    app_id="cli_xxx",
    spreadsheet_token="shtcn_xxx",
    sheet_id="a3fb01",
    range_str="A1:B2",
    values=[["Name", "Age"], ["Ray", 30]]
)
print(ok)

ok = sheet_client.append_data(
    app_id="cli_xxx",
    spreadsheet_token="shtcn_xxx",
    sheet_id="a3fb01",
    range_str="A1:B1",
    values=[["Alice", 28], ["Bob", 31]]
)
print(ok)
```

### 3) 常见格式与视图操作

```python
# 单元格格式
sheet_client.format_cells(
    app_id="cli_xxx",
    spreadsheet_token="shtcn_xxx",
    sheet_id="a3fb01",
    range_str="A1:B1",
    bold=True,
    font_size=12
)

# 合并 / 取消合并
sheet_client.merge_cells("cli_xxx", "shtcn_xxx", "a3fb01", "A1:B1")
sheet_client.unmerge_cells("cli_xxx", "shtcn_xxx", "a3fb01", "A1:B1")

# 行高列宽
sheet_client.set_column_width("cli_xxx", "shtcn_xxx", "a3fb01", 0, 2, 120)
sheet_client.set_row_height("cli_xxx", "shtcn_xxx", "a3fb01", 0, 0, 32)

# 冻结 / 取消冻结
sheet_client.freeze_panes("cli_xxx", "shtcn_xxx", "a3fb01", 1, 1)
sheet_client.unfreeze_panes("cli_xxx", "shtcn_xxx", "a3fb01")
```

## 多维表格（BitableClient）

### 1) 字段与记录基础操作

```python
fields = bitable_client.get_table_fields(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx"
)
print(fields[0]["field_name"])

record = bitable_client.create_record(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    fields={"Name": "Ray", "Status": "Active"}
)
print(record.record_id)

updated = bitable_client.update_record(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    record_id=record.record_id,
    fields={"Status": "Done"}
)
print(updated.record_id)

ok = bitable_client.delete_record(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    record_id=record.record_id
)
print(ok)
```

### 2) 查询（普通 / 结构化）

```python
from lark_service.clouddoc.models import FilterCondition

records, next_token = bitable_client.query_records(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    filter_conditions=[
        FilterCondition(field_name="Status", operator="eq", value="Active")
    ],
    page_size=100
)
print(len(records), next_token)
```

```python
from lark_service.clouddoc.models import StructuredFilterCondition, StructuredFilterInfo

filter_info = StructuredFilterInfo(
    conjunction="and",
    conditions=[
        StructuredFilterCondition(field_name="Status", operator="is", value=["Active"])
    ]
)

records, next_token = bitable_client.query_records_structured(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    filter_info=filter_info,
    page_size=100
)
print(len(records), next_token)
```

### 3) 批量操作

```python
created = bitable_client.batch_create_records(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    records=[
        {"Name": "Alice", "Status": "New"},
        {"Name": "Bob", "Status": "New"},
    ]
)
print(len(created))

updated = bitable_client.batch_update_records(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    records=[
        ("rec_xxx1", {"Status": "Done"}),
        ("rec_xxx2", {"Status": "Done"}),
    ]
)
print(len(updated))

ok = bitable_client.batch_delete_records(
    app_id="cli_xxx",
    app_token="bascn_xxx",
    table_id="tbl_xxx",
    record_ids=["rec_xxx1", "rec_xxx2"]
)
print(ok)
```

## 常见易错点

- `DocClient` 的文档 ID 与权限 API 的参数要对应同一文档
- `SheetClient` 的 `range_str` 必须是合法区间（如 `A1:B10`）
- `query_records` 的 `operator` 使用实现支持的操作符（如 `eq`、`gt`、`contains`）
- `query_records_structured` 建议用于复杂过滤，且优先校验字段名/字段 ID

## 应用管理

云文档服务同样支持多应用切换，详见 [应用管理文档](app-management.md)。

更多参考：
- [5 层 app_id 解析优先级](app-management.md)
- [多应用场景](app-management.md)
- [动态切换应用](app-management.md)
- [高级用法](advanced.md)
