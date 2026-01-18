"""Feishu aPaaS data space model definitions.

This module defines data models for aPaaS data space integration:
- WorkspaceTable: Data space table object
- TableRecord: Data space table record object
- FieldDefinition: Field definition object
- FieldType: Field type enumeration

All models use Pydantic for data validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Field type enumeration.

    Supported field types include:
    - Basic types: text, number, date/datetime, checkbox
    - Option types: single select, multi select
    - Contact types: person, phone, email, URL
    - Relation types: attachment, link
    - Computed types: formula, lookup

    Reference:
    https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/field-types
    """

    TEXT = "text"
    NUMBER = "number"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    DATETIME = "datetime"
    CHECKBOX = "checkbox"
    PERSON = "person"
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    ATTACHMENT = "attachment"
    LINK = "link"
    FORMULA = "formula"
    LOOKUP = "lookup"


class SelectOption(BaseModel):
    """Select option object.

    Used for option definitions in single_select and multi_select field types.

    Attributes:
    ----------
        id: Option ID
        name: Option name
        color: Option color (optional)
    """

    id: str = Field(..., description="Option ID")
    name: str = Field(..., description="Option name")
    color: str | None = Field(None, description="Option color")


class FieldDefinition(BaseModel):
    """Field definition object.

    Represents field metadata in a data table, including field ID, name, type,
    required flag, and option list.

    Attributes:
    ----------
        field_id: Field ID, format: fld_xxx
        field_name: Field name
        field_type: Field type, see FieldType enum
        is_required: Whether required, default False
        description: Field description (optional)
        options: Option list, only valid for single_select and multi_select types

    Example:
    ----------
        >>> field = FieldDefinition(
        ...     field_id="fld_001",
        ...     field_name="Status",
        ...     field_type=FieldType.SINGLE_SELECT,
        ...     is_required=True,
        ...     options=[
        ...         SelectOption(id="opt_1", name="In Progress", color="blue"),
        ...         SelectOption(id="opt_2", name="Completed", color="green"),
        ...     ]
        ... )
    """

    field_id: str = Field(
        ..., description="Field ID, format: fld_xxx", examples=["fld_a1b2c3d4e5f6g7h8"]
    )
    field_name: str = Field(..., description="Field name", examples=["Customer Name"])
    field_type: FieldType = Field(..., description="Field type")
    is_required: bool = Field(default=False, description="Whether required")
    description: str | None = Field(None, description="Field description")
    options: list[SelectOption] | None = Field(
        None, description="Option list (only for single_select and multi_select types)"
    )


class WorkspaceTable(BaseModel):
    """Workspace table object.

    Represents a data table in the aPaaS workspace, including table ID, name,
    description and other basic information.

    Attributes:
    ----------
        table_id: Data table ID, format: tbl_xxx
        workspace_id: Workspace ID, format: ws_xxx (optional)
        name: Table name
        description: Table description (optional)
        field_count: Number of fields (optional)

    Example:
    ----------
        >>> table = WorkspaceTable(
        ...     table_id="tbl_001",
        ...     workspace_id="ws_001",
        ...     name="Customer Info",
        ...     description="Store customer basic information",
        ...     field_count=10
        ... )
    """

    table_id: str = Field(
        ..., description="Data table ID, format: tbl_xxx", examples=["tbl_a1b2c3d4e5f6g7h8"]
    )
    workspace_id: str | None = Field(
        None, description="Workspace ID, format: ws_xxx", examples=["ws_a1b2c3d4e5f6g7h8"]
    )
    name: str = Field(..., description="Table name", examples=["Customer Info Table"])
    description: str | None = Field(None, description="Table description")
    field_count: int | None = Field(None, description="Number of fields", ge=0)


class TableRecord(BaseModel):
    """Table record object.

    Represents a row of data in the data table, including record ID, table ID,
    field value mapping and other information.

    Field value mapping is Dict[str, Any] type, where key is field name and value
    is field value. Value formats for different field types:
    - text: str
    - number: int | float
    - date: str (ISO 8601 date format)
    - datetime: str (ISO 8601 datetime format)
    - checkbox: bool
    - single_select: str (option name)
    - multi_select: list[str] (option name list)
    - person: list[dict] (person info list)
    - attachment: list[dict] (attachment info list)

    Attributes:
    ----------
        record_id: Record ID, format: rec_xxx
        table_id: Data table ID, format: tbl_xxx (optional)
        fields: Field value mapping, key is field name, value is field value
        created_at: Creation time (optional)
        updated_at: Update time (optional)

    Example:
    ----------
        >>> record = TableRecord(
        ...     record_id="rec_001",
        ...     table_id="tbl_001",
        ...     fields={
        ...         "Name": "John Doe",
        ...         "Age": 30,
        ...         "Email": "john@example.com",
        ...         "Status": "Active"
        ...     }
        ... )
    """

    record_id: str = Field(
        ..., description="Record ID, format: rec_xxx", examples=["rec_a1b2c3d4e5f6g7h8"]
    )
    table_id: str | None = Field(
        None, description="Data table ID, format: tbl_xxx", examples=["tbl_a1b2c3d4e5f6g7h8"]
    )
    fields: dict[str, Any] = Field(..., description="Field value mapping (field_name -> value)")
    created_at: datetime | None = Field(None, description="Creation time")
    updated_at: datetime | None = Field(None, description="Update time")
