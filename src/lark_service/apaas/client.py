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

logger = get_logger()

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


class WorkspaceTableClient:
    """
    High-level client for Lark aPaaS workspace table operations.

    Provides convenient methods for workspace table CRUD operations via Lark aPaaS API,
    with automatic error handling and retry. All operations require user_access_token.

    Capability Scope:
    - ✅ Included: Data space table CRUD operations
    - ❌ Excluded: AI capabilities, workflow triggering

    Reference:
    https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> client = WorkspaceTableClient(credential_pool)
        >>> tables = client.list_workspace_tables(
        ...     app_id="cli_xxx",
        ...     user_access_token="u-xxx",
        ...     workspace_id="ws_001"
        ... )
        >>> for table in tables:
        ...     print(table.name)
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize workspace table client.

        Args
        ----------
            credential_pool: Credential pool for token management
            retry_strategy: Retry strategy for API calls (optional)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def _handle_api_error(self, result: dict[str, Any], method_name: str) -> None:
        """
        Handle API error responses and raise appropriate exceptions.

        Args
        ----------
            result: API response dictionary
            method_name: Name of the method that called the API

        Raises
        ----------
            PermissionDeniedError: Permission denied error
            NotFoundError: Resource not found error
            InvalidParameterError: Invalid parameter error
            APIError: Generic API error
        """
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

    def list_workspace_tables(
        self,
        app_id: str,
        user_access_token: str,
        workspace_id: str,
    ) -> list[WorkspaceTable]:
        """
        List all data tables in a workspace.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            workspace_id: Workspace ID, format: ws_xxx

        Returns
        ----------
            List of workspace tables

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If workspace not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails

        Example
        --------
            >>> tables = client.list_workspace_tables(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     workspace_id="ws_001"
            ... )
            >>> print(f"Found {len(tables)} tables")
        """
        # Note: workspace_id format varies, not always "ws_" prefix
        if not workspace_id:
            raise InvalidParameterError("workspace_id cannot be empty")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(workspace_id, "workspace_id")

        logger.info(
            "Listing workspace tables",
            extra={"workspace_id": workspace_id, "app_id": app_id},
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/workspaces/{workspace_id}/tables"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "list_workspace_tables")

            # Parse response data
            tables_data = result.get("data", {}).get("tables", [])
            tables = []

            for table_data in tables_data:
                table = WorkspaceTable(
                    table_id=table_data.get("table_id", ""),
                    workspace_id=workspace_id,
                    name=table_data.get("name", ""),
                    description=table_data.get("description"),
                    field_count=table_data.get("field_count"),
                )
                tables.append(table)

            logger.info(
                f"Successfully listed {len(tables)} tables",
                extra={"workspace_id": workspace_id, "count": len(tables)},
            )

            return tables

        except requests.RequestException as e:
            logger.error(f"Network error listing workspace tables: {e}")
            raise APIError(f"Failed to list workspace tables: {e}") from e

    def list_fields(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
    ) -> list[FieldDefinition]:
        """
        Get field definitions for a data table.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx

        Returns
        ----------
            List of field definitions

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails

        Example
        --------
            >>> fields = client.list_fields(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001"
            ... )
            >>> for field in fields:
            ...     print(f"{field.field_name}: {field.field_type}")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")

        logger.info(
            "Listing table fields",
            extra={"table_id": table_id, "app_id": app_id},
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/fields"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "list_fields")

            # Parse response data
            fields_data = result.get("data", {}).get("fields", [])
            fields = []

            for field_data in fields_data:
                field_type_code = field_data.get("type", 1)
                field_type = FIELD_TYPE_MAP.get(field_type_code, FieldType.TEXT)

                # Parse options for select fields
                options = None
                if field_type in (FieldType.SINGLE_SELECT, FieldType.MULTI_SELECT):
                    options_data = field_data.get("options", [])
                    from lark_service.apaas.models import SelectOption

                    options = [
                        SelectOption(
                            id=opt.get("id", ""),
                            name=opt.get("name", ""),
                            color=opt.get("color"),
                        )
                        for opt in options_data
                    ]

                field = FieldDefinition(
                    field_id=field_data.get("field_id", ""),
                    field_name=field_data.get("field_name", ""),
                    field_type=field_type,
                    is_required=field_data.get("is_required", False),
                    description=field_data.get("description"),
                    options=options,
                )
                fields.append(field)

            logger.info(
                f"Successfully listed {len(fields)} fields",
                extra={"table_id": table_id, "count": len(fields)},
            )

            return fields

        except requests.RequestException as e:
            logger.error(f"Network error listing table fields: {e}")
            raise APIError(f"Failed to list table fields: {e}") from e

    def query_records(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        filter_expr: str | None = None,
        page_token: str | None = None,
        page_size: int = 20,
    ) -> tuple[list[TableRecord], str | None, bool]:
        """
        Query records from a data table with filtering and pagination.

        Filter expression format: CurrentValue.[field_name] = "value"
        Supports operators: =, !=, >, >=, <, <=, contains
        Supports logical operators: && (AND), || (OR)

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx
            filter_expr: Filter expression string (optional)
            page_token: Page token for pagination (optional)
            page_size: Number of records per page (default: 20, max: 500)

        Returns
        ----------
            Tuple of (records list, next page token, has more flag)

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails

        Example
        --------
            >>> records, next_token, has_more = client.query_records(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001",
            ...     filter_expr='CurrentValue.[Status] = "Active"',
            ...     page_size=50
            ... )
            >>> print(f"Found {len(records)} records")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        if page_size < 1 or page_size > 500:
            raise InvalidParameterError("page_size must be between 1 and 500")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_negative_int(page_size, "page_size", min_value=1, max_value=500)

        logger.info(
            "Querying table records",
            extra={
                "table_id": table_id,
                "app_id": app_id,
                "has_filter": filter_expr is not None,
                "page_size": page_size,
            },
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/records/query"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            # Build request body
            body: dict[str, Any] = {"page_size": page_size}

            if filter_expr:
                # URL encode the filter expression as per API requirements
                body["filter"] = urllib.parse.quote(filter_expr)

            if page_token:
                body["page_token"] = page_token

            response = requests.post(url, headers=headers, json=body, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "query_records")

            # Parse response data
            data = result.get("data", {})
            records_data = data.get("records", [])
            next_page_token = data.get("page_token")
            has_more = data.get("has_more", False)

            records = []
            for record_data in records_data:
                record = TableRecord(
                    record_id=record_data.get("record_id", ""),
                    table_id=table_id,
                    fields=record_data.get("fields", {}),
                )
                records.append(record)

            logger.info(
                f"Successfully queried {len(records)} records",
                extra={
                    "table_id": table_id,
                    "count": len(records),
                    "has_more": has_more,
                },
            )

            return (records, next_page_token, has_more)

        except requests.RequestException as e:
            logger.error(f"Network error querying records: {e}")
            raise APIError(f"Failed to query records: {e}") from e

    def create_record(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        fields: dict[str, Any],
    ) -> TableRecord:
        """
        Create a new record in a data table.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx
            fields: Field values mapping (field_name -> value)

        Returns
        ----------
            Created table record with record_id

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails (e.g., required field missing, type mismatch)

        Example
        --------
            >>> record = client.create_record(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001",
            ...     fields={"Name": "John Doe", "Age": 30, "Status": "Active"}
            ... )
            >>> print(f"Created record: {record.record_id}")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        if not fields:
            raise InvalidParameterError("fields cannot be empty")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")

        logger.info(
            "Creating table record",
            extra={"table_id": table_id, "app_id": app_id, "field_count": len(fields)},
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            body = {"fields": fields}

            response = requests.post(url, headers=headers, json=body, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "create_record")

            # Parse response data
            record_data = result.get("data", {}).get("record", {})
            record = TableRecord(
                record_id=record_data.get("record_id", ""),
                table_id=table_id,
                fields=record_data.get("fields", {}),
            )

            logger.info(
                f"Successfully created record: {record.record_id}",
                extra={"table_id": table_id, "record_id": record.record_id},
            )

            return record

        except requests.RequestException as e:
            logger.error(f"Network error creating record: {e}")
            raise APIError(f"Failed to create record: {e}") from e

    def update_record(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        record_id: str,
        fields: dict[str, Any],
    ) -> TableRecord:
        """
        Update an existing record (supports partial update).

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx
            record_id: Record ID, format: rec_xxx
            fields: Field values to update (field_name -> value)

        Returns
        ----------
            Updated table record

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table or record not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails (e.g., field not found, type mismatch)

        Example
        --------
            >>> record = client.update_record(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001",
            ...     record_id="rec_001",
            ...     fields={"Status": "Completed"}
            ... )
            >>> print(f"Updated record: {record.record_id}")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        # Note: record_id format varies
        if not record_id:
            raise InvalidParameterError("record_id cannot be empty")

        if not fields:
            raise InvalidParameterError("fields cannot be empty")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_empty_string(record_id, "record_id")

        logger.info(
            "Updating table record",
            extra={
                "table_id": table_id,
                "record_id": record_id,
                "app_id": app_id,
                "field_count": len(fields),
            },
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            body = {"fields": fields}

            response = requests.put(url, headers=headers, json=body, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "update_record")

            # Parse response data
            record_data = result.get("data", {}).get("record", {})
            record = TableRecord(
                record_id=record_data.get("record_id", record_id),
                table_id=table_id,
                fields=record_data.get("fields", {}),
            )

            logger.info(
                f"Successfully updated record: {record.record_id}",
                extra={"table_id": table_id, "record_id": record.record_id},
            )

            return record

        except requests.RequestException as e:
            logger.error(f"Network error updating record: {e}")
            raise APIError(f"Failed to update record: {e}") from e

    def delete_record(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        record_id: str,
    ) -> None:
        """
        Delete a record from a data table.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx
            record_id: Record ID, format: rec_xxx

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table or record not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails

        Example
        --------
            >>> client.delete_record(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001",
            ...     record_id="rec_001"
            ... )
            >>> print("Record deleted successfully")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        # Note: record_id format varies
        if not record_id:
            raise InvalidParameterError("record_id cannot be empty")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_empty_string(record_id, "record_id")

        logger.info(
            "Deleting table record",
            extra={"table_id": table_id, "record_id": record_id, "app_id": app_id},
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            response = requests.delete(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "delete_record")

            logger.info(
                f"Successfully deleted record: {record_id}",
                extra={"table_id": table_id, "record_id": record_id},
            )

        except requests.RequestException as e:
            logger.error(f"Network error deleting record: {e}")
            raise APIError(f"Failed to delete record: {e}") from e

    def batch_create_records(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        records: list[dict[str, Any]],
    ) -> list[TableRecord]:
        """
        Batch create multiple records (max 500 records).

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx
            records: List of field value mappings (max 500)

        Returns
        ----------
            List of created table records

        Raises
        ----------
            InvalidParameterError: If parameters are invalid or records exceed limit
            NotFoundError: If table not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails (partial success supported)

        Example
        --------
            >>> records = client.batch_create_records(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001",
            ...     records=[
            ...         {"Name": "Alice", "Age": 25},
            ...         {"Name": "Bob", "Age": 30},
            ...     ]
            ... )
            >>> print(f"Created {len(records)} records")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        if not records:
            raise InvalidParameterError("records cannot be empty")

        if len(records) > 500:
            raise InvalidParameterError("Batch create supports max 500 records")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")

        logger.info(
            "Batch creating table records",
            extra={"table_id": table_id, "app_id": app_id, "record_count": len(records)},
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/records/batch"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            # Build request body with records list
            body = {"records": [{"fields": record} for record in records]}

            response = requests.post(url, headers=headers, json=body, timeout=60)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "batch_create_records")

            # Parse response data
            records_data = result.get("data", {}).get("records", [])
            created_records = []

            for record_data in records_data:
                record = TableRecord(
                    record_id=record_data.get("record_id", ""),
                    table_id=table_id,
                    fields=record_data.get("fields", {}),
                )
                created_records.append(record)

            logger.info(
                f"Successfully batch created {len(created_records)} records",
                extra={"table_id": table_id, "count": len(created_records)},
            )

            return created_records

        except requests.RequestException as e:
            logger.error(f"Network error batch creating records: {e}")
            raise APIError(f"Failed to batch create records: {e}") from e

    def batch_update_records(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        records: list[tuple[str, dict[str, Any]]],
    ) -> list[TableRecord]:
        """
        Batch update multiple records (max 500 records).

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table ID, format: tbl_xxx
            records: List of (record_id, fields) tuples (max 500)

        Returns
        ----------
            List of updated table records

        Raises
        ----------
            InvalidParameterError: If parameters are invalid or records exceed limit
            NotFoundError: If table or some records not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails (partial success supported)

        Example
        --------
            >>> records = client.batch_update_records(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="tbl_001",
            ...     records=[
            ...         ("rec_001", {"Status": "Completed"}),
            ...         ("rec_002", {"Status": "In Progress"}),
            ...     ]
            ... )
            >>> print(f"Updated {len(records)} records")
        """
        # Note: table_id format varies, not always "tbl_" prefix
        if not table_id:
            raise InvalidParameterError("table_id cannot be empty")

        if not records:
            raise InvalidParameterError("records cannot be empty")

        if len(records) > 500:
            raise InvalidParameterError("Batch update supports max 500 records")

        # Validate record_id format
        for record_id, _ in records:
            if not record_id:
                raise InvalidParameterError("record_id cannot be empty")

        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")

        logger.info(
            "Batch updating table records",
            extra={"table_id": table_id, "app_id": app_id, "record_count": len(records)},
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/tables/{table_id}/records/batch"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            # Build request body with record updates
            body = {
                "records": [
                    {"record_id": record_id, "fields": fields} for record_id, fields in records
                ]
            }

            response = requests.put(url, headers=headers, json=body, timeout=60)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "batch_update_records")

            # Parse response data
            records_data = result.get("data", {}).get("records", [])
            updated_records = []

            for record_data in records_data:
                record = TableRecord(
                    record_id=record_data.get("record_id", ""),
                    table_id=table_id,
                    fields=record_data.get("fields", {}),
                )
                updated_records.append(record)

            logger.info(
                f"Successfully batch updated {len(updated_records)} records",
                extra={"table_id": table_id, "count": len(updated_records)},
            )

            return updated_records

        except requests.RequestException as e:
            logger.error(f"Network error batch updating records: {e}")
            raise APIError(f"Failed to batch update records: {e}") from e
