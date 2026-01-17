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
        error_msg = result.get("msg", "Unknown error")

        logger.error(
            f"aPaaS API error in {method_name}",
            extra={"error_code": code, "error_msg": error_msg, "method": method_name},
        )

        # Map Feishu error codes to custom exceptions
        if code in (99991400, 99991401, 99991663):  # Authentication/permission errors
            raise PermissionDeniedError(f"Permission denied: {error_msg}")
        if code in (99991404, 230002):  # Not found errors
            raise NotFoundError(f"Resource not found: {error_msg}")
        if code in (99991402, 99991403):  # Invalid parameter errors
            raise InvalidParameterError(f"Invalid parameter: {error_msg}")

        # Generic API error
        raise APIError(f"aPaaS API error ({code}): {error_msg}")

    def _map_data_type_to_field_type(self, data_type: str) -> FieldType:
        """
        Map aPaaS database column type to FieldType enum.

        Args
        ----------
            data_type: Database column type (uuid, varchar, timestamptz, etc.)

        Returns
        ----------
            Corresponding FieldType enum value
        """
        # Map common database types to FieldType
        type_mapping = {
            "varchar": FieldType.TEXT,
            "text": FieldType.TEXT,
            "uuid": FieldType.TEXT,
            "int4": FieldType.NUMBER,
            "int8": FieldType.NUMBER,
            "float4": FieldType.NUMBER,
            "float8": FieldType.NUMBER,
            "numeric": FieldType.NUMBER,
            "bool": FieldType.CHECKBOX,
            "timestamptz": FieldType.DATETIME,
            "timestamp": FieldType.DATETIME,
            "date": FieldType.DATE,
            "user_profile": FieldType.PERSON,
        }

        return type_mapping.get(data_type.lower(), FieldType.TEXT)

    def _format_sql_value(self, value: Any) -> str:
        """
        Format a Python value for SQL statement.

        Args
        ----------
            value: Python value to format

        Returns
        ----------
            SQL-formatted string
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int | float)):
            return str(value)
        if isinstance(value, dict):
            # For complex types like user_profile, convert to JSON string
            import json as jsonlib

            json_str = jsonlib.dumps(value, ensure_ascii=False)
            # Escape single quotes for SQL
            escaped = json_str.replace("'", "''")
            return f"'{escaped}'"
        if isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        # Default: convert to string and quote
        str_value = str(value).replace("'", "''")
        return f"'{str_value}'"

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

            # Parse response data - aPaaS returns 'items' not 'tables'
            tables_data = result.get("data", {}).get("items", [])
            tables = []

            for table_data in tables_data:
                table = WorkspaceTable(
                    table_id=table_data.get("name", ""),  # aPaaS uses table name as ID
                    workspace_id=workspace_id,
                    name=table_data.get("name", ""),
                    description=table_data.get("description"),
                    field_count=len(table_data.get("columns", [])),  # Count columns
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
        workspace_id: str,
    ) -> list[FieldDefinition]:
        """
        Get field definitions for a data table.

        Note: aPaaS doesn't have a separate fields endpoint. This method
        fetches table information and extracts column definitions.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table name (e.g., "follow_ups")
            workspace_id: Workspace ID where the table exists

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
            ...     table_id="follow_ups",
            ...     workspace_id="workspace_xxx"
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
            # aPaaS doesn't have separate fields endpoint, get from table list
            url = f"{APAAS_API_BASE}/apaas/v1/workspaces/{workspace_id}/tables"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "list_fields")

            # Find the specified table
            tables_data = result.get("data", {}).get("items", [])
            target_table = None
            for table_data in tables_data:
                if table_data.get("name") == table_id:
                    target_table = table_data
                    break

            if not target_table:
                raise NotFoundError(f"Table not found: {table_id}")

            # Parse columns from table data
            columns_data = target_table.get("columns", [])
            fields = []

            for col_data in columns_data:
                # Map database column type to FieldType
                data_type = col_data.get("data_type", "text")
                field_type = self._map_data_type_to_field_type(data_type)

                field = FieldDefinition(
                    field_id=col_data.get("name", ""),  # Use column name as field_id
                    field_name=col_data.get("name", ""),
                    field_type=field_type,
                    is_required=not col_data.get("is_allow_null", True),
                    description=col_data.get("description"),
                    options=None,  # aPaaS columns don't have select options
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

    def sql_query(
        self,
        app_id: str,
        user_access_token: str,
        workspace_id: str,
        sql: str,
    ) -> list[dict[str, Any]]:
        """
        Execute SQL SELECT query on workspace tables.

        This method uses the aPaaS SQL Commands API to execute read-only
        SQL queries. Currently only SELECT statements are fully supported.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            workspace_id: Workspace ID to execute query in
            sql: SQL SELECT statement

        Returns
        ----------
            List of result records as dictionaries

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails or SQL syntax error

        Example
        --------
            >>> results = client.sql_query(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     workspace_id="workspace_xxx",
            ...     sql="SELECT id, name, stage FROM customers WHERE stage = '潜在客户' LIMIT 10"
            ... )
            >>> for row in results:
            ...     print(row['name'], row['stage'])

        Notes
        -----
            - Only SELECT queries are recommended
            - INSERT/UPDATE/DELETE have syntax limitations
            - SQL follows PostgreSQL syntax
            - Refer to: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace/sql_commands
        """
        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(workspace_id, "workspace_id")
        validate_non_empty_string(sql, "sql")

        logger.info(
            "Executing SQL query",
            extra={
                "workspace_id": workspace_id,
                "app_id": app_id,
                "sql_preview": sql[:100],
            },
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/workspaces/{workspace_id}/sql_commands"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            payload = {"sql": sql}

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "sql_query")

            # Parse nested JSON response
            import json as jsonlib

            data = result.get("data", {})
            result_str = data.get("result", "[]")

            # Result is a JSON string containing an array with one element (another JSON string)
            outer_array = jsonlib.loads(result_str)
            records: list[dict[str, Any]] = (
                jsonlib.loads(outer_array[0]) if outer_array and len(outer_array) > 0 else []
            )

            logger.info(
                f"Successfully executed SQL query, {len(records)} records returned",
                extra={"workspace_id": workspace_id, "count": len(records)},
            )

            return records

        except requests.RequestException as e:
            logger.error(f"Network error executing SQL query: {e}")
            raise APIError(f"Failed to execute SQL query: {e}") from e
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse SQL query response: {e}")
            raise APIError(f"Failed to parse SQL response: {e}") from e

    def query_records(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        workspace_id: str,
        filter_expr: str | None = None,
        page_token: str | None = None,
        page_size: int = 20,
    ) -> tuple[list[TableRecord], str | None, bool]:
        """
        Query records from a data table with pagination.

        Note: Uses aPaaS GET /records endpoint. Filter expressions are not
        supported by this API - use sql_query() for filtering.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table name (e.g., "follow_ups")
            workspace_id: Workspace ID where the table exists
            filter_expr: Filter expression (not supported, will be ignored)
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
            ...     table_id="follow_ups",
            ...     workspace_id="workspace_xxx",
            ...     page_size=50
            ... )
            >>> print(f"Found {len(records)} records")
        """
        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_empty_string(workspace_id, "workspace_id")
        validate_non_negative_int(page_size, "page_size", min_value=1, max_value=500)

        if filter_expr:
            logger.warning(
                "filter_expr is not supported by aPaaS GET records API, "
                "use sql_query() method instead for filtering"
            )

        logger.info(
            "Querying table records",
            extra={
                "table_id": table_id,
                "workspace_id": workspace_id,
                "app_id": app_id,
                "page_size": page_size,
            },
        )

        try:
            url = f"{APAAS_API_BASE}/apaas/v1/workspaces/{workspace_id}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json",
            }

            # Build query parameters
            params: dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            response = requests.get(url, headers=headers, params=params, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                self._handle_api_error(result, "query_records")

            # Parse response data
            import json as jsonlib

            data = result.get("data", {})
            items = data.get("items")

            # aPaaS returns items as JSON string, need to parse
            if isinstance(items, str):
                items = jsonlib.loads(items)

            next_page_token = data.get("page_token")
            has_more = data.get("has_more", False)
            total = data.get("total", 0)

            # Convert to TableRecord objects
            records = []
            for item in items:
                # Extract record_id (usually 'id' field)
                record_id = item.get("id", "")

                # Remove system fields and keep user fields
                fields = {k: v for k, v in item.items() if not k.startswith("_") and k != "id"}

                record = TableRecord(
                    record_id=record_id,
                    table_id=table_id,
                    fields=fields,
                )
                records.append(record)

            logger.info(
                f"Successfully queried {len(records)} records (total: {total})",
                extra={
                    "table_id": table_id,
                    "count": len(records),
                    "total": total,
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
        workspace_id: str,
        fields: dict[str, Any],
    ) -> str:
        """
        Create a new record in a data table using SQL INSERT.

        Note: Uses SQL Commands API. Requires correct data types for fields
        (e.g., UUID format for uuid columns, proper timestamps for timestamptz).

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table name (e.g., "follow_ups")
            workspace_id: Workspace ID where the table exists
            fields: Field values mapping (field_name -> value)

        Returns
        ----------
            Created record ID

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails (e.g., required field missing, type mismatch)

        Example
        --------
            >>> record_id = client.create_record(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="follow_ups",
            ...     workspace_id="workspace_xxx",
            ...     fields={
            ...         "customer_id": "9f837291-5bb9-4200-b8c6-ae3909b5b7f0",
            ...         "followup_date": "2026-01-17T10:00:00+08:00",
            ...         "channel": "电话",
            ...         "content": "客户沟通记录"
            ...     }
            ... )
            >>> print(f"Created record: {record_id}")
        """
        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_empty_string(workspace_id, "workspace_id")

        if not fields:
            raise InvalidParameterError("fields cannot be empty")

        logger.info(
            "Creating table record via SQL",
            extra={"table_id": table_id, "workspace_id": workspace_id, "field_count": len(fields)},
        )

        try:
            # Build SQL INSERT statement
            columns = ", ".join(fields.keys())
            placeholders = ", ".join(self._format_sql_value(v) for v in fields.values())

            sql = f"""  # nosec B608
                INSERT INTO {table_id} ({columns})
                VALUES ({placeholders})
                RETURNING id
            """

            # Execute via SQL Commands API
            result_records = self.sql_query(
                app_id=app_id,
                user_access_token=user_access_token,
                workspace_id=workspace_id,
                sql=sql,
            )

            if not result_records or len(result_records) == 0:
                raise APIError("Failed to create record: no ID returned")

            record_id: str = result_records[0].get("id", "")

            logger.info(
                f"Successfully created record: {record_id}",
                extra={"table_id": table_id, "record_id": record_id},
            )

            return record_id

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Error creating record: {e}")
            raise APIError(f"Failed to create record: {e}") from e

    def update_record(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        workspace_id: str,
        record_id: str,
        fields: dict[str, Any],
    ) -> bool:
        """
        Update an existing record using SQL UPDATE.

        Note: Uses SQL Commands API with WHERE id = clause.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table name (e.g., "follow_ups")
            workspace_id: Workspace ID where the table exists
            record_id: Record ID to update
            fields: Field values to update (field_name -> value)

        Returns
        ----------
            True if update successful

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table or record not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails

        Example
        --------
            >>> success = client.update_record(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="follow_ups",
            ...     workspace_id="workspace_xxx",
            ...     record_id="df390b9d-a444-482a-8074-6d47bd3231f6",
            ...     fields={"content": "更新的内容", "stage": "进行中"}
            ... )
            >>> print(f"Update successful: {success}")
        """
        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_empty_string(workspace_id, "workspace_id")
        validate_non_empty_string(record_id, "record_id")

        if not fields:
            raise InvalidParameterError("fields cannot be empty")

        logger.info(
            "Updating table record via SQL",
            extra={
                "table_id": table_id,
                "workspace_id": workspace_id,
                "record_id": record_id,
                "field_count": len(fields),
            },
        )

        try:
            # Build SQL UPDATE statement
            set_clauses = [
                f"{key} = {self._format_sql_value(value)}" for key, value in fields.items()
            ]
            set_clause = ", ".join(set_clauses)

            sql = f"""  # nosec B608
                UPDATE {table_id}
                SET {set_clause}
                WHERE id = '{record_id}'
            """

            # Execute via SQL Commands API
            self.sql_query(
                app_id=app_id,
                user_access_token=user_access_token,
                workspace_id=workspace_id,
                sql=sql,
            )

            logger.info(
                f"Successfully updated record: {record_id}",
                extra={"table_id": table_id, "record_id": record_id},
            )

            return True

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Error updating record: {e}")
            raise APIError(f"Failed to update record: {e}") from e

    def delete_record(
        self,
        app_id: str,
        user_access_token: str,
        table_id: str,
        workspace_id: str,
        record_id: str,
    ) -> bool:
        """
        Delete a record from a data table using SQL DELETE.

        Note: Uses SQL Commands API with WHERE id = clause.

        Args
        ----------
            app_id: Application ID
            user_access_token: User access token for authentication
            table_id: Table name (e.g., "follow_ups")
            workspace_id: Workspace ID where the table exists
            record_id: Record ID to delete

        Returns
        ----------
            True if delete successful

        Raises
        ----------
            InvalidParameterError: If parameters are invalid
            NotFoundError: If table or record not found
            PermissionDeniedError: If user lacks permission
            APIError: If API call fails

        Example
        --------
            >>> success = client.delete_record(
            ...     app_id="cli_xxx",
            ...     user_access_token="u-xxx",
            ...     table_id="follow_ups",
            ...     workspace_id="workspace_xxx",
            ...     record_id="df390b9d-a444-482a-8074-6d47bd3231f6"
            ... )
            >>> print(f"Delete successful: {success}")
        """
        validate_app_id(app_id)
        validate_non_empty_string(user_access_token, "user_access_token")
        validate_non_empty_string(table_id, "table_id")
        validate_non_empty_string(workspace_id, "workspace_id")
        validate_non_empty_string(record_id, "record_id")

        logger.info(
            "Deleting table record via SQL",
            extra={"table_id": table_id, "workspace_id": workspace_id, "record_id": record_id},
        )

        try:
            # Build SQL DELETE statement
            sql = f"""  # nosec B608
                DELETE FROM {table_id}
                WHERE id = '{record_id}'
            """

            # Execute via SQL Commands API
            self.sql_query(
                app_id=app_id,
                user_access_token=user_access_token,
                workspace_id=workspace_id,
                sql=sql,
            )

            logger.info(
                f"Successfully deleted record: {record_id}",
                extra={"table_id": table_id, "record_id": record_id},
            )

            return True

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Error deleting record: {e}")
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
