"""CloudDoc 模块数据模型

本模块定义云文档操作相关的 Pydantic 模型,包括:
- Document: 文档信息
- ContentBlock: 文档内容块
- BaseRecord: 多维表格记录
- SheetRange: 电子表格范围
- MediaAsset: 媒体资产
- FieldDefinition: 字段定义
- DocumentInfo: 文档 URL 解析结果
- WikiNode: 知识库节点
- WikiSpace: 知识库空间
- QueryFilter: 查询过滤器

参考文档:
- docs/phase4-spec-enhancements.md
- specs/001-lark-service-core/contracts/clouddoc.yaml
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ==================== 文档相关模型 ====================


class ContentBlock(BaseModel):
    """文档内容块

    支持 7 种内容类型:
    - paragraph: 段落 (content: str)
    - heading: 标题 (content: str, level: 1-6)
    - image: 图片 (content: str = file_token)
    - table: 表格 (content: list[list[str]])
    - code: 代码块 (content: str, language: str)
    - list: 列表 (content: list[str], ordered: bool)
    - divider: 分隔线 (content: None)

    限制:
    - 单个 block 最大 100 KB
    - 单次追加最多 100 个 blocks
    """

    block_id: str | None = Field(
        None,
        description="块 ID (更新时必填,创建时自动生成)",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",
    )

    block_type: Literal[
        "paragraph", "heading", "image", "table", "code", "list", "divider"
    ] = Field(..., description="内容类型")

    content: str | list[Any] | None = Field(
        ...,
        description="内容 (类型取决于 block_type)",
    )

    attributes: dict[str, Any] | None = Field(
        None,
        description="块属性 (样式、对齐、颜色等)",
    )

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: Any) -> Any:
        """验证内容大小不超过 100 KB"""
        if v is None:
            return v

        # 估算大小 (简化版)
        import sys

        size = sys.getsizeof(v)
        if size > 100 * 1024:  # 100 KB
            raise ValueError(f"Content block size {size} bytes exceeds 100 KB limit")

        return v


class BlockAttributes(BaseModel):
    """内容块属性

    用于设置内容块的样式和格式。
    """

    # 文本样式
    bold: bool | None = Field(None, description="粗体")
    italic: bool | None = Field(None, description="斜体")
    underline: bool | None = Field(None, description="下划线")
    strikethrough: bool | None = Field(None, description="删除线")

    # 颜色
    text_color: str | None = Field(None, description="文本颜色 (hex)", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: str | None = Field(
        None, description="背景颜色 (hex)", pattern=r"^#[0-9A-Fa-f]{6}$"
    )

    # 对齐
    align: Literal["left", "center", "right", "justify"] | None = Field(
        None, description="对齐方式"
    )

    # 标题级别
    heading_level: Literal[1, 2, 3, 4, 5, 6] | None = Field(None, description="标题级别 (1-6)")

    # 代码语言
    code_language: str | None = Field(None, description="代码语言")

    # 列表类型
    list_ordered: bool | None = Field(None, description="是否有序列表")


class Document(BaseModel):
    """文档信息

    表示一个飞书文档 (Doc/Docx)。
    """

    doc_id: str = Field(
        ...,
        description="文档 ID",
        pattern=r"^(doxcn|doccn)[a-zA-Z0-9]{20,}$",
    )

    title: str = Field(..., description="文档标题", max_length=255)

    owner_id: str | None = Field(None, description="所有者 ID (open_id)")

    create_time: datetime | None = Field(None, description="创建时间")

    update_time: datetime | None = Field(None, description="更新时间")

    content_blocks: list[ContentBlock] | None = Field(
        None,
        description="文档内容块列表",
        max_length=100,  # 单次追加最多 100 个 blocks
    )


# ==================== 多维表格相关模型 ====================


class FieldDefinition(BaseModel):
    """多维表格字段定义"""

    field_id: str = Field(..., description="字段 ID")

    field_name: str = Field(..., description="字段名称", max_length=100)

    field_type: Literal[
        "text", "number", "date", "checkbox", "select", "multi_select", "user", "url", "attachment"
    ] = Field(..., description="字段类型")

    is_required: bool = Field(False, description="是否必填")

    options: list[str] | None = Field(None, description="选项列表 (select/multi_select 类型)")


class FilterCondition(BaseModel):
    """查询过滤条件

    支持 10 种操作符:
    - eq: 等于
    - ne: 不等于
    - gt: 大于
    - gte: 大于等于
    - lt: 小于
    - lte: 小于等于
    - contains: 包含
    - not_contains: 不包含
    - is_empty: 为空
    - is_not_empty: 不为空
    """

    field_name: str = Field(..., description="字段名称")

    operator: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte", "contains", "not_contains", "is_empty", "is_not_empty"
    ] = Field(..., description="操作符")

    value: Any | None = Field(None, description="比较值 (is_empty/is_not_empty 时为 None)")


class QueryFilter(BaseModel):
    """查询过滤器

    限制:
    - 最多 20 个条件
    - 单次查询最多返回 500 条记录
    """

    conditions: list[FilterCondition] = Field(
        ...,
        description="过滤条件列表",
        max_length=20,  # 最多 20 个条件
    )

    logic: Literal["and", "or"] = Field("and", description="条件逻辑 (and/or)")


class BaseRecord(BaseModel):
    """多维表格记录"""

    record_id: str | None = Field(
        None,
        description="记录 ID (更新时必填,创建时自动生成)",
        pattern=r"^rec[a-zA-Z0-9]{20,}$",
    )

    fields: dict[str, Any] = Field(..., description="字段值字典 (field_name -> value)")

    create_time: datetime | None = Field(None, description="创建时间")

    update_time: datetime | None = Field(None, description="更新时间")


# ==================== 电子表格相关模型 ====================


class SheetRange(BaseModel):
    """电子表格范围

    支持 4 种范围格式:
    1. A1 表示法: "A1:B10"
    2. 行列索引: "R1C1:R10C2"
    3. 命名范围: "SalesData"
    4. 整列/整行: "A:A", "1:1"

    限制:
    - 读取最大 100,000 单元格
    - 更新最大 10,000 单元格
    - 合并最大 1,000 单元格
    """

    sheet_id: str = Field(
        ...,
        description="工作表 ID",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )

    range_notation: str = Field(
        ...,
        description="范围表示 (A1:B10, R1C1:R10C2, SalesData, A:A, 1:1)",
        max_length=100,
    )

    @field_validator("range_notation")
    @classmethod
    def validate_range_format(cls, v: str) -> str:
        """验证范围格式"""
        import re

        # A1 表示法
        a1_pattern = r"^[A-Z]+\d+:[A-Z]+\d+$"
        # 行列索引
        rc_pattern = r"^R\d+C\d+:R\d+C\d+$"
        # 整列/整行
        col_pattern = r"^[A-Z]+:[A-Z]+$"
        row_pattern = r"^\d+:\d+$"
        # 命名范围 (字母数字下划线)
        named_pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"

        if not (
            re.match(a1_pattern, v)
            or re.match(rc_pattern, v)
            or re.match(col_pattern, v)
            or re.match(row_pattern, v)
            or re.match(named_pattern, v)
        ):
            raise ValueError(
                f"Invalid range notation: {v}. "
                f"Supported formats: A1:B10, R1C1:R10C2, SalesData, A:A, 1:1"
            )

        return v


class CellData(BaseModel):
    """单元格数据"""

    value: str | int | float | bool | None = Field(None, description="单元格值")

    formula: str | None = Field(None, description="公式 (以 = 开头)")

    # 格式
    number_format: str | None = Field(None, description="数字格式 (如 0.00, #,##0)")
    font_size: int | None = Field(None, description="字体大小", ge=8, le=72)
    font_color: str | None = Field(None, description="字体颜色 (hex)", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: str | None = Field(
        None, description="背景颜色 (hex)", pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    bold: bool | None = Field(None, description="粗体")
    italic: bool | None = Field(None, description="斜体")
    underline: bool | None = Field(None, description="下划线")
    align: Literal["left", "center", "right"] | None = Field(None, description="水平对齐")
    vertical_align: Literal["top", "middle", "bottom"] | None = Field(None, description="垂直对齐")


# ==================== 媒体资产相关模型 ====================


class MediaAsset(BaseModel):
    """媒体资产 (图片/文件)

    图片限制:
    - 最大 10 MB
    - 支持格式: jpg, jpeg, png, gif, bmp, webp
    - 最大尺寸: 4096 x 4096

    文件限制:
    - 最大 30 MB
    - 支持格式: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, zip
    """

    file_token: str = Field(
        ...,
        description="文件 token (上传后返回)",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",
    )

    file_name: str = Field(..., description="文件名", max_length=255)

    file_size: int = Field(..., description="文件大小 (bytes)", ge=0)

    mime_type: str = Field(..., description="MIME 类型")

    file_type: Literal["image", "file"] = Field(..., description="文件类型")

    # 图片特有字段
    width: int | None = Field(None, description="图片宽度", ge=1, le=4096)
    height: int | None = Field(None, description="图片高度", ge=1, le=4096)

    # 元数据
    upload_time: datetime | None = Field(None, description="上传时间")
    uploader_id: str | None = Field(None, description="上传者 ID")

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int, info: Any) -> int:
        """验证文件大小"""
        file_type = info.data.get("file_type")

        if file_type == "image" and v > 10 * 1024 * 1024:  # 10 MB
            raise ValueError(f"Image size {v} bytes exceeds 10 MB limit")

        if file_type == "file" and v > 30 * 1024 * 1024:  # 30 MB
            raise ValueError(f"File size {v} bytes exceeds 30 MB limit")

        return v


# ==================== URL 解析相关模型 ====================


class DocumentInfo(BaseModel):
    """文档 URL 解析结果

    用于 DocumentUrlResolver 返回的文档信息。
    """

    doc_type: Literal["docx", "sheet", "bitable", "doc", "mindnote", "file"] = Field(
        ..., description="文档类型"
    )

    doc_token: str = Field(..., description="实际可用的文档 token")

    source_type: Literal["wiki", "drive"] = Field(..., description="来源类型")

    # 知识库特有字段
    space_id: str | None = Field(None, description="知识空间 ID")
    node_token: str | None = Field(None, description="知识库节点 token")

    # 元数据
    title: str | None = Field(None, description="文档标题")
    owner: str | None = Field(None, description="所有者")


class WikiNode(BaseModel):
    """知识库节点

    表示知识库中的一个节点 (文档、文件夹等)。
    """

    space_id: str = Field(..., description="知识空间 ID", pattern=r"^\d+$")

    node_token: str = Field(
        ...,
        description="节点 token",
        pattern=r"^wik[a-zA-Z0-9]{20,}$",
    )

    obj_token: str = Field(
        ...,
        description="实际对象 token (doc_token)",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",
    )

    obj_type: Literal["doc", "docx", "sheet", "bitable", "mindnote", "file"] = Field(
        ..., description="对象类型"
    )

    parent_node_token: str | None = Field(None, description="父节点 token")

    node_type: Literal["origin", "shortcut"] = Field(..., description="节点类型")

    # 元数据
    title: str | None = Field(None, description="节点标题")
    owner_id: str | None = Field(None, description="所有者 ID")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="更新时间")


class WikiSpace(BaseModel):
    """知识库空间"""

    space_id: str = Field(..., description="知识空间 ID", pattern=r"^\d+$")

    name: str = Field(..., description="空间名称", max_length=255)

    description: str | None = Field(None, description="空间描述", max_length=1000)

    owner_id: str | None = Field(None, description="所有者 ID")

    # 元数据
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="更新时间")


# ==================== 权限相关模型 ====================


class Permission(BaseModel):
    """文档权限

    支持四种权限类型:
    - read: 可阅读
    - write: 可编辑
    - comment: 可评论
    - manage: 可管理
    """

    permission_id: str | None = Field(None, description="权限 ID")

    doc_id: str = Field(..., description="文档 ID")

    member_type: Literal["user", "department", "group", "public"] = Field(
        ..., description="成员类型"
    )

    member_id: str | None = Field(None, description="成员 ID (public 时为 None)")

    permission_type: Literal["read", "write", "comment", "manage"] = Field(
        ..., description="权限类型"
    )

    grant_time: datetime | None = Field(None, description="授予时间")

    granter_id: str | None = Field(None, description="授予者 ID")
