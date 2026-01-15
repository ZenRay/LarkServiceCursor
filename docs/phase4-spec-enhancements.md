# Phase 4 需求补充文档 - CloudDoc & Contact

**版本**: v1.0
**创建日期**: 2026-01-15
**基于**: Phase 4 需求评审报告
**补充范围**: 数据结构、限制、错误码、性能需求、安全需求等

本文档补充 Phase 4 需求文档中缺失的技术细节,作为 `spec.md` 的附件。

---

## 目录

- [CloudDoc 模块补充](#clouddoc-模块补充)
- [Contact 模块补充](#contact-模块补充)
- [错误码体系](#错误码体系)
- [非功能性需求](#非功能性需求)
- [数据验证规范](#数据验证规范)

---

## CloudDoc 模块补充

### 0. 知识库文档特殊说明 ⚠️

#### 0.1 知识库 (Wiki) vs 云空间 (Drive)

飞书的云文档可以存放在两个位置,token 获取方式不同:

| 存放位置 | 文档标识 | 获取方式 | API 路径 |
|---------|---------|---------|---------|
| **云空间 (Drive)** | `doc_token` | 直接使用文档链接中的 token | `/docx/v1/documents/{document_id}` |
| **知识库 (Wiki)** | `node_token` | 需要先通过知识库 API 获取 | `/wiki/v2/spaces/{space_id}/nodes/{node_token}` |

#### 0.2 知识库文档的访问流程

```python
# 1. 通过知识库 API 获取节点信息
def get_wiki_node_info(space_id: str, node_token: str) -> dict:
    """获取知识库节点信息

    Args:
        space_id: 知识空间 ID
        node_token: 节点 token (从知识库链接获取)

    Returns:
        节点信息,包含 obj_token (实际的文档 token)
    """
    response = client.wiki.v2.space_node.get(
        space_id=space_id,
        node_token=node_token
    )

    # 2. 从响应中获取实际的文档 token
    obj_token = response.data.node.obj_token
    obj_type = response.data.node.obj_type  # "doc", "sheet", "bitable" 等

    return {
        "obj_token": obj_token,  # 实际的文档 token
        "obj_type": obj_type,    # 文档类型
        "node_token": node_token # 知识库节点 token
    }

# 3. 使用 obj_token 访问文档内容
def get_wiki_document_content(space_id: str, node_token: str) -> dict:
    """获取知识库文档内容"""
    # 先获取节点信息
    node_info = get_wiki_node_info(space_id, node_token)
    obj_token = node_info["obj_token"]

    # 使用 obj_token 访问文档
    if node_info["obj_type"] == "doc":
        return get_document_content(obj_token)
    elif node_info["obj_type"] == "docx":
        return get_docx_content(obj_token)
    # ... 其他类型
```

#### 0.3 知识库链接格式识别

```python
class WikiLinkParser:
    """知识库链接解析器"""

    # 知识库链接格式
    WIKI_LINK_PATTERN = r'https://[^/]+/wiki/([^/]+)/([^/?]+)'

    # 云空间链接格式
    DRIVE_LINK_PATTERN = r'https://[^/]+/(docx|sheets|base)/([^/?]+)'

    @staticmethod
    def parse_link(url: str) -> dict:
        """解析飞书文档链接

        Returns:
            {
                "type": "wiki" | "drive",
                "space_id": str,  # 仅 wiki
                "node_token": str,  # 仅 wiki
                "doc_token": str   # 仅 drive
            }
        """
        import re

        # 尝试匹配知识库链接
        wiki_match = re.match(WikiLinkParser.WIKI_LINK_PATTERN, url)
        if wiki_match:
            return {
                "type": "wiki",
                "space_id": wiki_match.group(1),
                "node_token": wiki_match.group(2)
            }

        # 尝试匹配云空间链接
        drive_match = re.match(WikiLinkParser.DRIVE_LINK_PATTERN, url)
        if drive_match:
            return {
                "type": "drive",
                "doc_type": drive_match.group(1),  # docx, sheets, base
                "doc_token": drive_match.group(2)
            }

        raise ValueError(f"无法识别的飞书文档链接: {url}")
```

#### 0.4 统一的文档访问接口

```python
class UnifiedDocClient:
    """统一的文档访问客户端"""

    def get_document_by_url(self, url: str) -> Document:
        """通过 URL 获取文档 (自动识别知识库/云空间)"""
        link_info = WikiLinkParser.parse_link(url)

        if link_info["type"] == "wiki":
            # 知识库文档: 先获取 obj_token
            node_info = self.get_wiki_node_info(
                space_id=link_info["space_id"],
                node_token=link_info["node_token"]
            )
            doc_token = node_info["obj_token"]
        else:
            # 云空间文档: 直接使用 doc_token
            doc_token = link_info["doc_token"]

        # 使用 doc_token 获取文档内容
        return self.get_document_content(doc_token)
```

#### 0.5 知识库相关数据模型

```python
class WikiNode(BaseModel):
    """知识库节点"""
    space_id: str = Field(pattern=r'^[0-9]+$')
    node_token: str = Field(pattern=r'^[a-zA-Z0-9_-]+$')
    obj_token: str  # 实际的文档 token
    obj_type: Literal["doc", "docx", "sheet", "mindnote", "bitable", "file"]
    parent_node_token: str | None = None
    node_type: Literal["origin", "shortcut"]
    origin_node_token: str | None = None  # 快捷方式指向的原始节点
    has_child: bool = False
    title: str
    obj_create_time: int  # Unix timestamp
    obj_edit_time: int
    node_create_time: int
    creator: str  # open_id
    owner: str  # open_id

class WikiSpace(BaseModel):
    """知识空间"""
    space_id: str = Field(pattern=r'^[0-9]+$')
    name: str
    description: str | None = None
    space_type: Literal["team", "personal"]
    visibility: Literal["public", "private"]
```

#### 0.6 知识库 API 端点

需要在 `contracts/clouddoc.yaml` 中补充:

```yaml
paths:
  # 知识库节点操作
  /wiki/v2/spaces/{space_id}/nodes/{node_token}:
    get:
      summary: 获取知识库节点信息
      operationId: getWikiNode
      tags:
        - Wiki
      parameters:
        - name: space_id
          in: path
          required: true
          schema:
            type: string
        - name: node_token
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                  msg:
                    type: string
                  data:
                    type: object
                    properties:
                      node:
                        $ref: '#/components/schemas/WikiNode'
```

#### 0.7 使用场景示例

```python
# 场景 1: 用户提供知识库链接
wiki_url = "https://example.feishu.cn/wiki/space123/node456"

# 自动识别并获取文档
client = UnifiedDocClient(credential_pool, retry_strategy)
document = client.get_document_by_url(wiki_url)

# 场景 2: 已知 space_id 和 node_token
space_id = "7123456789"
node_token = "wikcnAbCdEfGhIjKlMnOpQr"

# 获取节点信息
node_info = client.get_wiki_node_info(space_id, node_token)
print(f"文档类型: {node_info['obj_type']}")
print(f"文档 token: {node_info['obj_token']}")

# 获取文档内容
document = client.get_document_content(node_info["obj_token"])
```

#### 0.8 注意事项

1. **权限要求**:
   - 访问知识库文档需要 `wiki:wiki:readonly` 权限
   - 访问云空间文档需要 `drive:drive:readonly` 权限

2. **token 格式差异**:
   - 知识库 `node_token`: 可能包含 `-` 和 `_`
   - 云空间 `doc_token`: 通常是纯字母数字

3. **快捷方式处理**:
   - 知识库支持快捷方式 (shortcut)
   - 需要通过 `origin_node_token` 获取实际文档

4. **缓存策略**:
   - 建议缓存 `node_token` → `obj_token` 的映射
   - TTL: 1 小时 (知识库结构变化较少)

**参考文档**: [获取知识空间节点信息 - 飞书开放平台](https://open.feishu.cn/document/server-docs/docs/wiki-v2/space-node/get_node?appId=cli_a8c8dc731cb9900e)

---

### 1. 文档内容结构定义

#### 1.1 ContentBlock 数据结构

```python
class ContentBlock(BaseModel):
    """文档内容块"""
    block_id: str | None = Field(None, pattern=r'^blk_[a-zA-Z0-9]{16}$')
    type: Literal["paragraph", "heading", "image", "table", "code", "list", "divider"]
    content: str | dict[str, Any]
    attributes: BlockAttributes | None = None

class BlockAttributes(BaseModel):
    """Block 属性"""
    style: Literal["normal", "bold", "italic", "underline"] = "normal"
    level: int | None = Field(None, ge=1, le=6)  # 标题级别 (heading 专用)
    language: str | None = None  # 代码语言 (code 专用)
    color: str | None = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
```

#### 1.2 支持的 Block 类型

| 类型 | 说明 | content 类型 | 属性 |
|------|------|-------------|------|
| `paragraph` | 段落 | `str` | `style`, `color` |
| `heading` | 标题 | `str` | `level` (1-6), `style` |
| `image` | 图片 | `{"file_token": str, "width": int, "height": int}` | - |
| `table` | 表格 | `{"rows": int, "cols": int, "cells": list}` | - |
| `code` | 代码块 | `str` | `language` |
| `list` | 列表 | `{"items": list[str], "ordered": bool}` | - |
| `divider` | 分隔线 | `None` | - |

#### 1.3 文档内容限制

```python
class DocumentLimits:
    """文档限制"""
    MAX_BLOCKS_PER_DOCUMENT = 10000  # 单个文档最大 block 数
    MAX_BLOCKS_PER_APPEND = 100      # 单次追加最大 block 数
    MAX_BLOCK_SIZE = 102400          # 单个 block 最大大小 (100 KB)
    MAX_TITLE_LENGTH = 255           # 标题最大长度
    MAX_CONTENT_LENGTH = 1048576     # 单个 block 内容最大长度 (1 MB)
```

---

### 2. Bitable 过滤器语法

#### 2.1 QueryFilter 数据结构

```python
class QueryFilter(BaseModel):
    """查询过滤器"""
    conjunction: Literal["and", "or"] = "and"
    conditions: list[FilterCondition] = Field(min_length=1, max_length=20)

class FilterCondition(BaseModel):
    """过滤条件"""
    field_name: str = Field(min_length=1, max_length=100)
    operator: FilterOperator
    value: Any | None = None  # is_empty/is_not_empty 时为 None

class FilterOperator(str, Enum):
    """过滤操作符"""
    IS = "is"                    # 等于
    IS_NOT = "is_not"            # 不等于
    CONTAINS = "contains"        # 包含 (字符串)
    NOT_CONTAINS = "not_contains"  # 不包含
    GT = "gt"                    # 大于 (数值/日期)
    LT = "lt"                    # 小于
    GTE = "gte"                  # 大于等于
    LTE = "lte"                  # 小于等于
    IS_EMPTY = "is_empty"        # 为空
    IS_NOT_EMPTY = "is_not_empty"  # 不为空
```

#### 2.2 过滤器示例

```python
# 示例 1: 查询状态为 active 的记录
filter = QueryFilter(
    conjunction="and",
    conditions=[
        FilterCondition(
            field_name="status",
            operator=FilterOperator.IS,
            value="active"
        )
    ]
)

# 示例 2: 查询创建时间在某个范围内的记录
filter = QueryFilter(
    conjunction="and",
    conditions=[
        FilterCondition(
            field_name="created_at",
            operator=FilterOperator.GTE,
            value="2026-01-01"
        ),
        FilterCondition(
            field_name="created_at",
            operator=FilterOperator.LTE,
            value="2026-01-31"
        )
    ]
)

# 示例 3: 查询名称包含特定关键词或描述不为空的记录
filter = QueryFilter(
    conjunction="or",
    conditions=[
        FilterCondition(
            field_name="name",
            operator=FilterOperator.CONTAINS,
            value="重要"
        ),
        FilterCondition(
            field_name="description",
            operator=FilterOperator.IS_NOT_EMPTY
        )
    ]
)
```

#### 2.3 分页参数

```python
class PaginationParams(BaseModel):
    """分页参数"""
    page_size: int = Field(default=100, ge=1, le=500)
    page_token: str | None = None
    sort: list[SortField] | None = None

class SortField(BaseModel):
    """排序字段"""
    field_name: str
    desc: bool = False  # True: 降序, False: 升序
```

---

### 3. Sheet 范围格式规范

#### 3.1 范围表示法

```python
class SheetRange(BaseModel):
    """Sheet 范围"""
    range: str = Field(pattern=r'^([A-Z]+[0-9]+:[A-Z]+[0-9]+|[A-Z]+:[A-Z]+|[0-9]+:[0-9]+|[A-Z]+[0-9]+)$')
    sheet_name: str | None = None  # 跨 sheet 时需要

# 支持的格式:
# 1. 单元格范围: "A1:B10"
# 2. 整列: "A:C"
# 3. 整行: "3:5"
# 4. 单个单元格: "A1"
# 5. 跨 sheet: "Sheet1!A1:B10"
```

#### 3.2 范围限制

```python
class SheetLimits:
    """Sheet 限制"""
    MAX_ROWS = 1000000           # 最大行数
    MAX_COLS = 18278             # 最大列数 (ZZZ)
    MAX_CELLS_PER_READ = 100000  # 单次读取最大单元格数
    MAX_CELLS_PER_UPDATE = 10000 # 单次更新最大单元格数
    MAX_MERGE_CELLS = 1000       # 单次合并最大单元格数
    MAX_FREEZE_ROWS = 100        # 冻结窗格最大行数
    MAX_FREEZE_COLS = 100        # 冻结窗格最大列数
```

---

### 4. 媒体上传限制

#### 4.1 图片上传限制

```python
class ImageUploadLimits:
    """图片上传限制"""
    SUPPORTED_FORMATS = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp"
    }
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_WIDTH = 4096              # 最大宽度 (像素)
    MAX_HEIGHT = 4096             # 最大高度 (像素)
```

#### 4.2 文件上传限制

```python
class FileUploadLimits:
    """文件上传限制"""
    SUPPORTED_FORMATS = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".zip": "application/zip",
        ".rar": "application/x-rar-compressed",
        ".7z": "application/x-7z-compressed"
    }
    MAX_SIZE = 30 * 1024 * 1024  # 30 MB
```

---

### 5. 权限管理

#### 5.1 权限类型定义

```python
class PermissionType(str, Enum):
    """权限类型"""
    READ = "read"        # 可阅读: 查看文档内容
    WRITE = "write"      # 可编辑: 修改文档内容
    COMMENT = "comment"  # 可评论: 添加评论,不能修改内容
    MANAGE = "manage"    # 可管理: 修改权限,删除文档

# 权限层级: manage > write > comment > read
```

#### 5.2 权限授予对象

```python
class PermissionMember(BaseModel):
    """权限成员"""
    member_type: Literal["user", "department", "group", "anyone"]
    member_id: str | None = None  # anyone 时为 None
    member_name: str | None = None

class Permission(BaseModel):
    """权限"""
    member: PermissionMember
    permission: PermissionType
    granted_by: str | None = None  # 授予者 ID
    granted_at: datetime | None = None
```

---

### 6. 批量操作限制

```python
class BatchOperationLimits:
    """批量操作限制"""
    # Bitable
    BITABLE_BATCH_CREATE_MAX = 500   # 批量创建最大记录数
    BITABLE_BATCH_UPDATE_MAX = 500   # 批量更新最大记录数
    BITABLE_BATCH_DELETE_MAX = 500   # 批量删除最大记录数
    BITABLE_QUERY_MAX = 500          # 单次查询最大返回数

    # Sheet
    SHEET_BATCH_UPDATE_CELLS_MAX = 10000  # 批量更新最大单元格数
    SHEET_BATCH_FORMAT_CELLS_MAX = 1000   # 批量格式化最大单元格数
    SHEET_BATCH_MERGE_MAX = 100           # 批量合并最大区域数
```

---

## Contact 模块补充

### 1. 用户 ID 类型说明

#### 1.1 ID 类型对比

| ID 类型 | 作用域 | 格式 | 使用场景 | 稳定性 |
|---------|--------|------|----------|--------|
| `open_id` | 应用内 | `ou_xxx` (16位) | 消息发送、权限管理 | 应用级稳定 |
| `user_id` | 租户内 | 数字字符串 | 通讯录查询、组织架构 | 租户级稳定 |
| `union_id` | 跨租户 | `on_xxx` (16位) | 多租户用户关联 | 全局稳定 |

#### 1.2 ID 转换规则

- 同一用户在不同应用有**不同** `open_id`
- 同一用户在同一租户有**唯一** `user_id`
- 同一用户跨租户有**唯一** `union_id`

#### 1.3 推荐使用策略

```python
# 1. 消息发送: 使用 open_id
client.messaging.send_text_message(
    receiver_id="ou_abc123...",  # open_id
    receive_id_type="open_id"
)

# 2. 缓存存储: 使用 union_id 作为主键
cache_key = f"user:{app_id}:{union_id}"

# 3. 组织架构: 使用 user_id
department_users = contact.get_department_users(dept_id)
for user in department_users:
    print(user.user_id)  # 租户内唯一
```

---

### 2. 缓存策略详细定义

#### 2.1 缓存刷新行为

```python
def get_user_by_email(email: str, app_id: str) -> User:
    """获取用户 (同步刷新策略)"""
    # 1. 检查缓存
    cached = check_cache(email, app_id)
    if cached and not is_expired(cached):
        logger.info("Cache hit", extra={"email": email})
        return cached

    # 2. 缓存未命中或已过期,同步调用 API
    try:
        user = fetch_from_lark_api(email, app_id)
        update_cache(user)
        return user
    except APIError as e:
        # 3. API 调用失败,如果有过期缓存则返回
        if cached:
            logger.warning("API failed, using expired cache", extra={"error": str(e)})
            return cached
        raise
```

#### 2.2 缓存失效策略

```python
class CacheInvalidationStrategy:
    """缓存失效策略"""

    # 1. TTL 过期失效 (自动)
    TTL = 86400  # 24 小时

    # 2. 主动失效 (用户信息更新时)
    def invalidate_on_update(self, union_id: str, app_id: str):
        cache_key = f"user:{app_id}:{union_id}"
        redis.delete(cache_key)

    # 3. 强制失效 (管理员操作)
    def force_invalidate(self, union_id: str, app_id: str):
        cache_key = f"user:{app_id}:{union_id}"
        redis.delete(cache_key)

    # 4. 容量淘汰 (LRU)
    MAX_CACHE_SIZE = 100000  # 最大缓存 100,000 条记录
```

#### 2.3 缓存 key 命名规则

```python
# 用户缓存
f"user:{app_id}:{union_id}"

# 部门缓存
f"dept:{app_id}:{dept_id}"

# 群组缓存
f"chat:{app_id}:{chat_id}"

# 权限缓存
f"perm:{app_id}:{doc_id}:{user_id}"
```

---

### 3. 批量操作限制

```python
class ContactBatchLimits:
    """Contact 批量操作限制"""
    BATCH_QUERY_USERS_MAX = 200      # 批量查询用户最大数
    BATCH_UPDATE_CACHE_MAX = 1000    # 批量更新缓存最大数
    DEPARTMENT_USERS_MAX = 1000      # 单个部门最大用户数
```

---

## 错误码体系

### 1. CloudDoc 错误码

```python
class CloudDocErrorCode(IntEnum):
    """CloudDoc 错误码"""
    # 40xxx - 客户端错误
    DOCUMENT_NOT_FOUND = 40001       # 文档不存在
    PERMISSION_DENIED = 40002        # 权限不足
    CONTENT_TOO_LARGE = 40003        # 文档内容过大
    INVALID_BLOCK_ID = 40004         # block_id 无效
    UNSUPPORTED_FILE_TYPE = 40005    # 文件类型不支持
    FILE_SIZE_EXCEEDED = 40006       # 文件大小超限
    INVALID_RANGE = 40007            # Sheet 范围无效
    INVALID_FILTER = 40008           # Bitable 过滤器无效

    # 50xxx - 服务端错误
    DOCUMENT_CREATE_FAILED = 50001   # 文档创建失败
    CONTENT_APPEND_FAILED = 50002    # 内容追加失败
    MEDIA_UPLOAD_FAILED = 50003      # 媒体上传失败
    PERMISSION_GRANT_FAILED = 50004  # 权限授予失败
```

### 2. Contact 错误码

```python
class ContactErrorCode(IntEnum):
    """Contact 错误码"""
    # 40xxx - 客户端错误
    USER_NOT_FOUND = 40101           # 用户不存在
    INVALID_EMAIL = 40102            # 邮箱格式错误
    DEPARTMENT_NOT_FOUND = 40103     # 部门不存在
    CHAT_NOT_FOUND = 40104           # 群组不存在
    PERMISSION_DENIED = 40105        # 权限不足
    INVALID_MOBILE = 40106           # 手机号格式错误

    # 50xxx - 服务端错误
    CACHE_WRITE_FAILED = 50101       # 缓存写入失败
    API_TIMEOUT = 50102              # API 调用超时
    CACHE_VERSION_CONFLICT = 50103   # 缓存版本冲突
```

### 3. 错误响应格式

```python
class ErrorResponse(BaseModel):
    """错误响应"""
    code: int                        # 错误码
    message: str                     # 错误消息
    details: dict[str, Any] | None = None  # 错误详情
    request_id: str                  # 请求 ID

# 示例
{
    "code": 40001,
    "message": "文档不存在",
    "details": {
        "doc_id": "doc_abc123",
        "suggestion": "请检查文档 ID 是否正确"
    },
    "request_id": "req_xyz789"
}
```

---

## 非功能性需求

### 1. 性能需求

#### 1.1 CloudDoc 性能要求

```python
class CloudDocPerformance:
    """CloudDoc 性能要求"""
    DOCUMENT_CREATE_TIMEOUT = 2.0    # 文档创建 < 2 秒
    CONTENT_READ_TIMEOUT = 1.0       # 内容读取 < 1 秒
    CONTENT_APPEND_TIMEOUT = 3.0     # 内容追加 < 3 秒
    BITABLE_QUERY_TIMEOUT = 2.0      # Bitable 查询 < 2 秒
    MEDIA_UPLOAD_TIMEOUT = 30.0      # 媒体上传 (10MB) < 30 秒
    SHEET_READ_TIMEOUT = 2.0         # Sheet 读取 < 2 秒
    SHEET_UPDATE_TIMEOUT = 3.0       # Sheet 更新 < 3 秒

    # 并发性能
    CONCURRENT_OPERATIONS_PER_SECOND = 50  # 支持每秒 50 次并发操作
```

#### 1.2 Contact 性能要求

```python
class ContactPerformance:
    """Contact 性能要求"""
    CACHE_HIT_RESPONSE_TIME = 0.1    # 缓存命中 < 100 ms
    CACHE_MISS_RESPONSE_TIME = 2.0   # 缓存未命中 < 2 秒
    BATCH_QUERY_TIMEOUT = 5.0        # 批量查询 (200 用户) < 5 秒
    CACHE_REFRESH_TIMEOUT = 3.0      # 缓存刷新 < 3 秒

    # 并发性能
    CONCURRENT_QUERIES_PER_SECOND = 100  # 支持每秒 100 次并发查询

    # 缓存性能
    CACHE_HIT_RATE_TARGET = 0.8      # 缓存命中率目标 > 80%
```

---

### 2. 安全需求

#### 2.1 权限验证

```python
class SecurityRequirements:
    """安全需求"""

    # 1. 权限验证时机
    VERIFY_PERMISSION_ON_EVERY_OPERATION = True  # 每次操作前验证权限

    # 2. 权限缓存
    PERMISSION_CACHE_TTL = 300  # 权限缓存 5 分钟

    # 3. 权限变更同步
    INVALIDATE_PERMISSION_CACHE_ON_CHANGE = True  # 权限变更后立即失效缓存
```

#### 2.2 数据隐私

```python
class DataPrivacy:
    """数据隐私"""

    # 1. 缓存数据加密
    ENCRYPT_CACHE_DATA = True  # 使用 AES-256 加密

    # 2. 敏感字段脱敏
    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏: z***@example.com"""
        parts = email.split("@")
        return f"{parts[0][0]}***@{parts[1]}"

    @staticmethod
    def mask_mobile(mobile: str) -> str:
        """手机号脱敏: 138****5678"""
        return f"{mobile[:3]}****{mobile[-4:]}"

    # 3. 日志脱敏
    LOG_MASK_SENSITIVE_FIELDS = True  # 日志中不记录完整邮箱和手机号
```

#### 2.3 审计日志

```python
class AuditLog:
    """审计日志"""

    # 记录内容
    AUDIT_PERMISSION_CHANGES = True   # 记录所有权限变更
    AUDIT_SENSITIVE_DATA_ACCESS = True  # 记录敏感数据访问

    # 日志保留
    LOG_RETENTION_DAYS = 90  # 日志保留 90 天
```

---

### 3. 可靠性需求

#### 3.1 重试策略

```python
class RetryStrategy:
    """重试策略"""

    # CloudDoc 重试
    CLOUDDOC_RETRYABLE_OPERATIONS = ["read", "query"]  # 可重试操作
    CLOUDDOC_NON_RETRYABLE_OPERATIONS = ["create", "delete"]  # 不可重试操作

    # Contact 重试
    CONTACT_RETRYABLE_OPERATIONS = ["query", "get"]  # 可重试操作

    # 幂等性保证
    USE_IDEMPOTENCY_KEY = True  # 使用 idempotency_key 保证幂等性
```

#### 3.2 缓存一致性

```python
class CacheConsistency:
    """缓存一致性"""

    # 1. 缓存更新使用事务
    USE_TRANSACTION_FOR_CACHE_UPDATE = True

    # 2. 并发更新使用乐观锁
    USE_OPTIMISTIC_LOCK = True  # 使用 version 字段

    # 3. 冲突检测和重试
    MAX_RETRY_ON_CONFLICT = 3
```

#### 3.3 数据持久化

```python
class DataPersistence:
    """数据持久化"""

    # 数据库写入重试
    DB_WRITE_MAX_RETRY = 3

    # 事务边界
    USE_DATABASE_TRANSACTION = True

    # 数据备份
    BACKUP_CACHE_DATA_DAILY = True  # 每日备份缓存数据
```

---

## 数据验证规范

### 1. ID 格式验证

```python
class IDValidation:
    """ID 格式验证"""

    # 正则表达式
    DOC_ID_PATTERN = r'^doc_[a-zA-Z0-9]{16}$'
    TABLE_ID_PATTERN = r'^tbl_[a-zA-Z0-9]{16}$'
    SHEET_ID_PATTERN = r'^sht_[a-zA-Z0-9]{16}$'
    RECORD_ID_PATTERN = r'^rec_[a-zA-Z0-9]{16}$'
    FILE_TOKEN_PATTERN = r'^file_v2_[a-zA-Z0-9]{32}$'
    BLOCK_ID_PATTERN = r'^blk_[a-zA-Z0-9]{16}$'

    OPEN_ID_PATTERN = r'^ou_[a-zA-Z0-9]{16}$'
    UNION_ID_PATTERN = r'^on_[a-zA-Z0-9]{16}$'
    DEPT_ID_PATTERN = r'^dept_[a-zA-Z0-9]{16}$'
    CHAT_ID_PATTERN = r'^oc_[a-zA-Z0-9]{16}$'
```

### 2. 邮箱和手机号验证

```python
class ContactValidation:
    """联系方式验证"""

    # 邮箱验证
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # 手机号验证 (E.164 格式)
    MOBILE_PATTERN = r'^\+?[1-9]\d{1,14}$'

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        import re
        return bool(re.match(ContactValidation.EMAIL_PATTERN, email))

    @staticmethod
    def validate_mobile(mobile: str) -> bool:
        """验证手机号格式"""
        import re
        return bool(re.match(ContactValidation.MOBILE_PATTERN, mobile))
```

### 3. 内容验证

```python
class ContentValidation:
    """内容验证"""

    # 文档标题
    TITLE_MIN_LENGTH = 1
    TITLE_MAX_LENGTH = 255

    # Block 内容
    BLOCK_COUNT_MIN = 1
    BLOCK_COUNT_MAX = 100  # 单次追加
    BLOCK_CONTENT_MAX_SIZE = 102400  # 100 KB

    # Bitable 字段
    FIELD_NAME_MIN_LENGTH = 1
    FIELD_NAME_MAX_LENGTH = 100
    FIELD_VALUE_MAX_SIZE = 10240  # 10 KB
```

---

## 数据模型完整定义

### 1. CloudDoc 数据模型

```python
# Document 模型
class Document(BaseModel):
    doc_id: str = Field(pattern=r'^doc_[a-zA-Z0-9]{16}$')
    title: str = Field(min_length=1, max_length=255)
    folder_id: str | None = Field(None, pattern=r'^fld_[a-zA-Z0-9]{16}$')
    owner_id: str = Field(pattern=r'^ou_[a-zA-Z0-9]{16}$')
    created_at: datetime
    updated_at: datetime
    url: str
    block_count: int = Field(default=0, ge=0)

# BaseRecord 模型 (Bitable)
class BaseRecord(BaseModel):
    record_id: str = Field(pattern=r'^rec_[a-zA-Z0-9]{16}$')
    fields: dict[str, Any]
    created_by: str
    created_time: int  # Unix timestamp
    last_modified_by: str
    last_modified_time: int

# SheetRange 模型
class SheetRange(BaseModel):
    range: str = Field(pattern=r'^([A-Z]+[0-9]+:[A-Z]+[0-9]+|[A-Z]+:[A-Z]+|[0-9]+:[0-9]+|[A-Z]+[0-9]+)$')
    sheet_name: str | None = None

# MediaAsset 模型
class MediaAsset(BaseModel):
    file_token: str = Field(pattern=r'^file_v2_[a-zA-Z0-9]{32}$')
    file_name: str = Field(max_length=255)
    file_type: str
    size: int = Field(ge=1, le=31457280)  # 最大 30 MB
    url: str | None = None

# Permission 模型
class Permission(BaseModel):
    member_type: Literal["user", "department", "group", "anyone"]
    member_id: str | None = None
    member_name: str | None = None
    permission: Literal["read", "write", "comment", "manage"]
    granted_by: str | None = None
    granted_at: datetime | None = None
```

### 2. Contact 数据模型

```python
# User 模型
class User(BaseModel):
    open_id: str = Field(pattern=r'^ou_[a-zA-Z0-9]{16}$')
    user_id: str
    union_id: str = Field(pattern=r'^on_[a-zA-Z0-9]{16}$')
    name: str = Field(min_length=1, max_length=100)
    en_name: str | None = Field(None, max_length=100)
    email: str | None = None
    mobile: str | None = None
    avatar: str | None = None
    department_ids: list[str] = []
    status: Literal[1, 2, 4, 5]  # 1:正常, 2:停用, 4:未激活, 5:退出
    employee_type: Literal[1, 2, 3, 4, 5] | None = None
    join_time: int | None = None

# UserCache 模型
class UserCache(BaseModel):
    app_id: str = Field(pattern=r'^cli_[a-z0-9]{16}$')
    union_id: str = Field(pattern=r'^on_[a-zA-Z0-9]{16}$')
    open_id: str = Field(pattern=r'^ou_[a-zA-Z0-9]{16}$')
    user_id: str
    name: str
    email: str | None = None
    mobile: str | None = None
    avatar: str | None = None
    department_ids: list[str] = []
    cached_at: datetime
    ttl: int = 86400  # 24 hours
    version: int = 1

    def is_expired(self) -> bool:
        return (datetime.now() - self.cached_at).total_seconds() > self.ttl

# Department 模型
class Department(BaseModel):
    department_id: str = Field(pattern=r'^dept_[a-zA-Z0-9]{16}$')
    name: str = Field(min_length=1, max_length=100)
    parent_department_id: str
    leader_user_id: str | None = None
    member_count: int = Field(ge=0)
    status: Literal[1, 2]  # 1:正常, 2:停用
    order: int | None = None

# ChatGroup 模型
class ChatGroup(BaseModel):
    chat_id: str = Field(pattern=r'^oc_[a-zA-Z0-9]{16}$')
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    owner_id: str
    avatar: str | None = None
    member_count: int = Field(ge=0)
    chat_type: Literal["private", "public"]
    created_at: datetime
```

---

## 参考资料

- [Phase 4 需求评审报告](./phase4-requirements-review.md)
- [Phase 4 检查清单](../specs/001-lark-service-core/checklists/phase4-requirements-quality.md)
- [CloudDoc API 契约](../specs/001-lark-service-core/contracts/clouddoc.yaml)
- [Contact API 契约](../specs/001-lark-service-core/contracts/contact.yaml)
- [飞书开放平台文档](https://open.feishu.cn/document/)

---

**文档版本**: v1.0
**最后更新**: 2026-01-15
**维护者**: Lark Service Team
