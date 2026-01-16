"""Feishu aPaaS data space integration module.

This module provides Feishu aPaaS data space table CRUD capabilities, supporting:
- Workspace and data table queries
- Record create, query, update, delete operations
- Batch operations (batch create, batch update)
- Field definition query and parsing
- Pagination query and filtering
- user_access_token authentication

Capability Scope:
- ✅ Included: Data space table (workspace-table) CRUD operations
- ❌ Excluded: AI capability invocation, workflow triggering (not in aPaaS data platform scope)

Reference:
https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list
"""

from lark_service.apaas.client import WorkspaceTableClient
from lark_service.apaas.models import (
    FieldDefinition,
    FieldType,
    TableRecord,
    WorkspaceTable,
)

__all__ = [
    "WorkspaceTableClient",
    "WorkspaceTable",
    "TableRecord",
    "FieldDefinition",
    "FieldType",
]
