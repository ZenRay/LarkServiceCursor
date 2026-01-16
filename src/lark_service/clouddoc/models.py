"""CloudDoc module data models.

This module defines Pydantic models for cloud document operations:
- Document: Document information
- ContentBlock: Document content block
- BaseRecord: Bitable record
- SheetRange: Spreadsheet range
- MediaAsset: Media asset (image/file)
- FieldDefinition: Field definition
- DocumentInfo: Document URL resolution result
- WikiNode: Wiki knowledge base node
- WikiSpace: Wiki knowledge base space
- QueryFilter: Query filter

Reference:
- docs/phase4-spec-enhancements.md
- specs/001-lark-service-core/contracts/clouddoc.yaml
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from lark_service.utils.logger import get_logger

logger = get_logger()

# ==================== Document Models ====================


class ContentBlock(BaseModel):
    """Document content block.

    Supports 7 content types:
    - paragraph: Paragraph (content: str)
    - heading: Heading (content: str, level: 1-6)
    - image: Image (content: str = file_token)
    - table: Table (content: list[list[str]])
    - code: Code block (content: str, language: str)
    - list: List (content: list[str], ordered: bool)
    - divider: Divider (content: None)

    Limits:
    - Max 100 KB per block
    - Max 100 blocks per append
    """

    block_id: str | None = Field(
        None,
        description="Block ID (required for update, auto-generated for create)",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",
    )

    block_type: Literal["paragraph", "heading", "image", "table", "code", "list", "divider"] = (
        Field(..., description="Content type")
    )

    content: str | list[Any] | None = Field(
        ...,
        description="Content (type depends on block_type)",
    )

    attributes: dict[str, Any] | None = Field(
        None,
        description="Block attributes (style, alignment, color, etc.)",
    )

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: Any) -> Any:
        """Validate content size does not exceed 100 KB."""
        if v is None:
            return v

        # Estimate size (simplified)
        import sys

        size = sys.getsizeof(v)
        if size > 100 * 1024:  # 100 KB
            raise ValueError(f"Content block size {size} bytes exceeds 100 KB limit")

        return v


class BlockAttributes(BaseModel):
    """Content block attributes.

    Used to set content block styles and formats.
    """

    # Text styles
    bold: bool | None = Field(None, description="Bold")
    italic: bool | None = Field(None, description="Italic")
    underline: bool | None = Field(None, description="Underline")
    strikethrough: bool | None = Field(None, description="Strikethrough")

    # Colors
    text_color: str | None = Field(
        None, description="Text color (hex)", pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    background_color: str | None = Field(
        None, description="Background color (hex)", pattern=r"^#[0-9A-Fa-f]{6}$"
    )

    # Alignment
    align: Literal["left", "center", "right", "justify"] | None = Field(
        None, description="Alignment"
    )

    # Heading level
    heading_level: Literal[1, 2, 3, 4, 5, 6] | None = Field(None, description="Heading level (1-6)")

    # Code language
    code_language: str | None = Field(None, description="Code language")

    # List type
    list_ordered: bool | None = Field(None, description="Is ordered list")


class Document(BaseModel):
    """Document information.

    Represents a Feishu document (Doc/Docx).
    """

    doc_id: str = Field(
        ...,
        description="Document ID or Token",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",  # Support both doc_id and doc_token formats
    )

    title: str = Field("", description="Document title (may be empty)", max_length=255)

    owner_id: str | None = Field(None, description="Owner ID (open_id)")

    create_time: datetime | None = Field(None, description="Create time")

    update_time: datetime | None = Field(None, description="Update time")

    content_blocks: list[ContentBlock] | None = Field(
        None,
        description="Document content blocks",
        max_length=100,  # Max 100 blocks per append
    )


# ==================== Bitable Models ====================


class FieldDefinition(BaseModel):
    """Bitable field definition."""

    field_id: str = Field(..., description="Field ID")

    field_name: str = Field(..., description="Field name", max_length=100)

    field_type: Literal[
        "text", "number", "date", "checkbox", "select", "multi_select", "user", "url", "attachment"
    ] = Field(..., description="Field type")

    is_required: bool = Field(False, description="Is required field")

    options: list[str] | None = Field(None, description="Options (for select/multi_select)")


class FilterCondition(BaseModel):
    """Query filter condition.

    Supports 10 operators:
    - eq: Equal
    - ne: Not equal
    - gt: Greater than
    - gte: Greater than or equal
    - lt: Less than
    - lte: Less than or equal
    - contains: Contains
    - not_contains: Not contains
    - is_empty: Is empty
    - is_not_empty: Is not empty
    """

    field_name: str = Field(..., description="Field name")

    operator: Literal[
        "eq", "ne", "gt", "gte", "lt", "lte", "contains", "not_contains", "is_empty", "is_not_empty"
    ] = Field(..., description="Operator")

    value: Any | None = Field(None, description="Comparison value (None for is_empty/is_not_empty)")


class QueryFilter(BaseModel):
    """Query filter.

    Limits:
    - Max 20 conditions
    - Max 500 records per query
    """

    conditions: list[FilterCondition] = Field(
        ...,
        description="Filter conditions",
        max_length=20,  # Max 20 conditions
    )

    logic: Literal["and", "or"] = Field("and", description="Condition logic (and/or)")


class TableField(BaseModel):
    """Bitable 表字段信息."""

    field_id: str = Field(..., description="字段 ID", pattern=r"^fld[a-zA-Z0-9]+$")
    field_name: str = Field(..., description="字段名称", min_length=1, max_length=100)
    type: int = Field(..., description="字段类型代码", ge=1, le=25)
    type_name: str | None = Field(None, description="字段类型名称")
    description: str | None = Field(None, description="字段描述")
    property: dict[str, Any] | None = Field(None, description="字段属性")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: int) -> int:
        """Validate field type."""
        # 常见的字段类型
        valid_types = {1, 2, 3, 4, 5, 7, 11, 13, 15, 17, 18, 20, 21, 22, 23}
        if v not in valid_types:
            logger.warning(f"Unknown field type: {v}")
        return v


class BaseRecord(BaseModel):
    """Bitable record."""

    record_id: str | None = Field(
        None,
        description="Record ID (required for update, auto-generated for create)",
        pattern=r"^rec[a-zA-Z0-9]+$",
    )

    fields: dict[str, Any] = Field(..., description="Field values (field_name -> value)")

    create_time: datetime | None = Field(None, description="Create time")

    update_time: datetime | None = Field(None, description="Update time")


# ==================== Sheet Models ====================


class SheetInfo(BaseModel):
    """Sheet 工作表信息."""

    sheet_id: str = Field(..., description="工作表 ID", pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(..., description="工作表标题", min_length=1, max_length=100)
    index: int = Field(..., description="工作表索引", ge=0)
    row_count: int | None = Field(None, description="行数", ge=0)
    column_count: int | None = Field(None, description="列数", ge=0)
    hidden: bool | None = Field(None, description="是否隐藏")
    resource_type: str | None = Field(None, description="资源类型")


class SheetRange(BaseModel):
    """Spreadsheet range.

    Supports 4 range formats:
    1. A1 notation: "A1:B10"
    2. Row-column index: "R1C1:R10C2"
    3. Named range: "SalesData"
    4. Entire column/row: "A:A", "1:1"

    Limits:
    - Max 100,000 cells for read
    - Max 10,000 cells for update
    - Max 1,000 cells for merge
    """

    sheet_id: str = Field(
        ...,
        description="Sheet ID",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )

    range_notation: str = Field(
        ...,
        description="Range notation (A1:B10, R1C1:R10C2, SalesData, A:A, 1:1)",
        max_length=100,
    )

    @field_validator("range_notation")
    @classmethod
    def validate_range_format(cls, v: str) -> str:
        """Validate range format."""
        import re

        # A1 notation
        a1_pattern = r"^[A-Z]+\d+:[A-Z]+\d+$"
        # Row-column index
        rc_pattern = r"^R\d+C\d+:R\d+C\d+$"
        # Entire column/row
        col_pattern = r"^[A-Z]+:[A-Z]+$"
        row_pattern = r"^\d+:\d+$"
        # Named range (alphanumeric and underscore)
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
    """Cell data."""

    value: str | int | float | bool | None = Field(None, description="Cell value")

    formula: str | None = Field(None, description="Formula (starts with =)")

    # Formatting
    number_format: str | None = Field(None, description="Number format (e.g. 0.00, #,##0)")
    font_size: int | None = Field(None, description="Font size", ge=8, le=72)
    font_color: str | None = Field(
        None, description="Font color (hex)", pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    background_color: str | None = Field(
        None, description="Background color (hex)", pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    bold: bool | None = Field(None, description="Bold")
    italic: bool | None = Field(None, description="Italic")
    underline: bool | None = Field(None, description="Underline")
    align: Literal["left", "center", "right"] | None = Field(
        None, description="Horizontal alignment"
    )
    vertical_align: Literal["top", "middle", "bottom"] | None = Field(
        None, description="Vertical alignment"
    )


# ==================== Media Asset Models ====================


class MediaAsset(BaseModel):
    """Media asset (image/file).

    Image limits:
    - Max 10 MB
    - Supported formats: jpg, jpeg, png, gif, bmp, webp
    - Max dimensions: 4096 x 4096

    File limits:
    - Max 30 MB
    - Supported formats: pdf, doc, docx, xls, xlsx, ppt, pptx, txt, zip
    """

    file_token: str = Field(
        ...,
        description="File token (returned after upload)",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",
    )

    file_name: str = Field(..., description="File name", max_length=255)

    file_size: int = Field(..., description="File size (bytes)", ge=0)

    mime_type: str = Field(..., description="MIME type")

    file_type: Literal["image", "file"] = Field(..., description="File type")

    # Image-specific fields
    width: int | None = Field(None, description="Image width", ge=1, le=4096)
    height: int | None = Field(None, description="Image height", ge=1, le=4096)

    # Metadata
    upload_time: datetime | None = Field(None, description="Upload time")
    uploader_id: str | None = Field(None, description="Uploader ID")

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int, info: Any) -> int:
        """Validate file size."""
        file_type = info.data.get("file_type")

        if file_type == "image" and v > 10 * 1024 * 1024:  # 10 MB
            raise ValueError(f"Image size {v} bytes exceeds 10 MB limit")

        if file_type == "file" and v > 30 * 1024 * 1024:  # 30 MB
            raise ValueError(f"File size {v} bytes exceeds 30 MB limit")

        return v


# ==================== URL Resolution Models ====================


class DocumentInfo(BaseModel):
    """Document URL resolution result.

    Used by DocumentUrlResolver to return document information.
    """

    doc_type: Literal["docx", "sheet", "bitable", "doc", "mindnote", "file"] = Field(
        ..., description="Document type"
    )

    doc_token: str = Field(..., description="Actual usable document token")

    source_type: Literal["wiki", "drive"] = Field(..., description="Source type")

    # Wiki-specific fields
    space_id: str | None = Field(None, description="Wiki space ID")
    node_token: str | None = Field(None, description="Wiki node token")

    # Metadata
    title: str | None = Field(None, description="Document title")
    owner: str | None = Field(None, description="Owner")


class WikiNode(BaseModel):
    """Wiki knowledge base node.

    Represents a node in the wiki knowledge base (document, folder, etc.).
    """

    space_id: str = Field(..., description="Wiki space ID", pattern=r"^\d+$")

    node_token: str = Field(
        ...,
        description="Node token",
        pattern=r"^wik[a-zA-Z0-9]{20,}$",
    )

    obj_token: str = Field(
        ...,
        description="Actual object token (doc_token)",
        pattern=r"^[a-zA-Z0-9_-]{20,}$",
    )

    obj_type: Literal["doc", "docx", "sheet", "bitable", "mindnote", "file"] = Field(
        ..., description="Object type"
    )

    parent_node_token: str | None = Field(None, description="Parent node token")

    node_type: Literal["origin", "shortcut"] = Field(..., description="Node type")

    # Metadata
    title: str | None = Field(None, description="Node title")
    owner_id: str | None = Field(None, description="Owner ID")
    create_time: datetime | None = Field(None, description="Create time")
    update_time: datetime | None = Field(None, description="Update time")


class WikiSpace(BaseModel):
    """Wiki knowledge base space."""

    space_id: str = Field(..., description="Wiki space ID", pattern=r"^\d+$")

    name: str = Field(..., description="Space name", max_length=255)

    description: str | None = Field(None, description="Space description", max_length=1000)

    owner_id: str | None = Field(None, description="Owner ID")

    # Metadata
    create_time: datetime | None = Field(None, description="Create time")
    update_time: datetime | None = Field(None, description="Update time")


# ==================== Permission Models ====================


class Permission(BaseModel):
    """Document permission.

    Supports four permission types:
    - read: Can read
    - write: Can edit
    - comment: Can comment
    - manage: Can manage
    """

    permission_id: str | None = Field(None, description="Permission ID")

    doc_id: str = Field(..., description="Document ID")

    member_type: Literal["user", "department", "group", "public"] = Field(
        ..., description="Member type"
    )

    member_id: str | None = Field(None, description="Member ID (None for public)")

    permission_type: Literal["read", "write", "comment", "manage"] = Field(
        ..., description="Permission type"
    )

    grant_time: datetime | None = Field(None, description="Grant time")

    granter_id: str | None = Field(None, description="Granter ID")
