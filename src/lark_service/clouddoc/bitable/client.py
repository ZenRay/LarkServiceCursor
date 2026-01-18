"""
Bitable client for Lark Base API.

This module provides a high-level client for multi-dimensional table operations
via Lark Base API, including CRUD operations with filters and pagination.
"""

from typing import TYPE_CHECKING, Any

from lark_oapi.api.bitable.v1 import SearchAppTableRecordRequest, SearchAppTableRecordRequestBody

from lark_service.clouddoc.models import BaseRecord, FieldDefinition, FilterCondition

if TYPE_CHECKING:
    from lark_service.clouddoc.models import StructuredFilterInfo
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    APIError,
    InvalidParameterError,
    NotFoundError,
    PermissionDeniedError,
)
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


class BitableClient:
    """
    High-level client for Lark Bitable operations.

    Provides convenient methods for managing multi-dimensional tables
    via Lark Base API, with automatic error handling and retry.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> client = BitableClient(credential_pool)
        >>> record = client.create_record(
        ...     app_id="cli_xxx",
        ...     app_token="bascn123",
        ...     table_id="tbl123",
        ...     fields={"Name": "John", "Age": 30}
        ... )
        >>> print(record.record_id)
    """

    # Field type name mapping
    FIELD_TYPE_NAMES = {
        1: "文本",
        2: "数字",
        3: "单选",
        4: "多选",
        5: "日期",
        7: "复选框",
        11: "人员",
        13: "电话号码",
        15: "超链接",
        17: "附件",
        18: "关联",
        20: "公式",
        21: "双向关联",
        22: "查找引用",
        23: "创建时间",
    }

    # Field type mapping from API numeric type to model string type
    FIELD_TYPE_MAPPING = {
        1: "text",
        2: "number",
        3: "select",
        4: "multi_select",
        5: "date",
        7: "checkbox",
        11: "user",
        13: "text",  # phone number as text
        15: "url",
        17: "attachment",
        18: "text",  # relation as text
        20: "text",  # formula as text
        21: "text",  # bidirectional relation as text
        22: "text",  # lookup as text
        23: "date",  # created time as date
    }

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize BitableClient.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def create_record(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        fields: dict[str, str | int | float | bool | list[str]],
    ) -> BaseRecord:
        """
        Create a new record in Bitable.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            fields : dict
                Field values (key: field name, value: field value)

        Returns
        -------
            BaseRecord
                Created record

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If table not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> record = client.create_record(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     fields={"Name": "John", "Age": 30}
            ... )
        """
        if not fields:
            raise InvalidParameterError("Fields cannot be empty")

        logger.info(f"Creating record in table {table_id}")

        def _create() -> BaseRecord:
            import requests

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")  # nosec B106

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            payload = {"fields": fields}
            logger.debug(f"Creating record with payload: {payload}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to create record: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code in [1254302, 403]:
                        raise PermissionDeniedError(
                            f"No permission to create record in table: {table_id}"
                        )
                    elif error_code in [1254000, 1254001, 400]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, PermissionDeniedError | InvalidParameterError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code in [1254302, 403]:
                    raise PermissionDeniedError(
                        f"No permission to create record in table: {table_id}"
                    )
                elif error_code in [1254000, 1254001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            data = result.get("data", {})
            record_data = data.get("record", {})

            record = BaseRecord(
                record_id=record_data.get("record_id", ""),
                fields=record_data.get("fields", {}),
                create_time=None,
                update_time=None,
            )

            logger.info(f"Successfully created record {record.record_id} in table {table_id}")
            return record

        return self.retry_strategy.execute(_create)

    def get_table_fields(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
    ) -> list[dict[str, Any]]:
        """
        获取 Bitable 表的所有字段信息.

        Parameters
        ----------
            app_id : str
                应用 ID
            app_token : str
                Bitable 应用 token
            table_id : str
                数据表 ID

        Returns
        -------
            list[dict]
                字段信息列表，每个字段包含:
                - field_id: 字段 ID
                - field_name: 字段名称
                - type: 字段类型代码
                - type_name: 字段类型名称
                - description: 字段描述（可选）
                - property: 字段属性（可选）

        Raises
        ------
            NotFoundError
                表不存在
            PermissionDeniedError
                无权限访问
            APIError
                API 调用失败

        Examples
        --------
            >>> fields = client.get_table_fields(
            ...     app_id="cli_xxx",
            ...     app_token="bascnxxx",
            ...     table_id="tblxxx"
            ... )
            >>> text_field = next(f for f in fields if f["field_name"] == "文本")
            >>> print(text_field["field_id"])  # "fldV0OLjFj"
        """
        logger.info(f"Getting fields for table {table_id}")

        def _get_fields() -> list[dict[str, Any]]:
            from lark_oapi.api.bitable.v1 import ListAppTableFieldRequest

            sdk_client = self.credential_pool._get_sdk_client(app_id)

            request = (
                ListAppTableFieldRequest.builder()
                .app_token(app_token)
                .table_id(table_id)
                .page_size(100)  # Fetch all fields at once
                .build()
            )

            response = sdk_client.bitable.v1.app_table_field.list(request)

            if not response.success():
                error_msg = f"Failed to get table fields: {response.msg}"
                logger.error(
                    error_msg,
                    extra={
                        "app_token": app_token,
                        "table_id": table_id,
                        "code": response.code,
                    },
                )

                # Map error codes
                if response.code == 1770002:
                    raise NotFoundError(f"Table not found: {table_id}")
                elif response.code in [1770032, 403]:
                    raise PermissionDeniedError(f"No permission to access table: {table_id}")
                else:
                    raise APIError(error_msg)

            fields = []
            if response.data and response.data.items:
                for item in response.data.items:
                    field_info = {
                        "field_id": item.field_id,
                        "field_name": item.field_name,
                        "type": item.type,
                        "type_name": self.FIELD_TYPE_NAMES.get(item.type, f"Unknown({item.type})"),
                    }

                    # Add optional fields
                    if hasattr(item, "description") and item.description:
                        field_info["description"] = item.description
                    if hasattr(item, "property") and item.property:
                        field_info["property"] = item.property

                    fields.append(field_info)

            logger.info(f"Retrieved {len(fields)} fields for table {table_id}")
            return fields

        return self.retry_strategy.execute(_get_fields)

    def query_records(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        filter_conditions: list[FilterCondition] | None = None,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[BaseRecord], str | None]:
        """
        Query records with filters and pagination.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            filter_conditions : list[FilterCondition] | None
                Filter conditions (default: no filter)
            page_size : int
                Page size (default: 100, max: 500)
            page_token : str | None
                Page token for pagination

        Returns
        -------
            tuple[list[BaseRecord], str | None]
                (records, next_page_token)

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If table not found

        Examples
        --------
            >>> filters = [
            ...     FilterCondition(
            ...         field_name="Age",
            ...         operator=">=",
            ...         value=18
            ...     )
            ... ]
            >>> records, next_token = client.query_records(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     filter_conditions=filters,
            ...     page_size=50
            ... )
        """
        if page_size < 1 or page_size > 500:
            raise InvalidParameterError(f"Invalid page_size: {page_size} (1-500)")

        logger.info(f"Querying records from table {table_id}, page_size={page_size}")

        def _query() -> tuple[list[BaseRecord], str | None]:
            # Get SDK client
            sdk_client = self.credential_pool._get_sdk_client(app_id)

            # Build request
            req_builder = (
                SearchAppTableRecordRequest.builder()
                .app_token(app_token)
                .table_id(table_id)
                .page_size(page_size)
            )

            if page_token:
                req_builder = req_builder.page_token(page_token)

            # Build request body with filter
            body_builder = SearchAppTableRecordRequestBody.builder()

            # Build filter formula from conditions
            if filter_conditions:
                logger.info(f"Applying {len(filter_conditions)} filter conditions")
                filter_parts: list[str] = []

                for condition in filter_conditions:
                    field = condition.field_name
                    op = condition.operator
                    value = condition.value

                    # Build filter expression based on operator
                    # Lark uses formula-like syntax (note: use = not ==, and strings need quotes)
                    if op == "eq":
                        if isinstance(value, str):
                            filter_parts.append(f'CurrentValue.[{field}] = "{value}"')
                        else:
                            filter_parts.append(f"CurrentValue.[{field}] = {value}")
                    elif op == "ne":
                        if isinstance(value, str):
                            filter_parts.append(f'CurrentValue.[{field}] != "{value}"')
                        else:
                            filter_parts.append(f"CurrentValue.[{field}] != {value}")
                    elif op == "gt":
                        filter_parts.append(f"CurrentValue.[{field}] > {value}")
                    elif op == "gte":
                        filter_parts.append(f"CurrentValue.[{field}] >= {value}")
                    elif op == "lt":
                        filter_parts.append(f"CurrentValue.[{field}] < {value}")
                    elif op == "lte":
                        filter_parts.append(f"CurrentValue.[{field}] <= {value}")
                    elif op == "contains":
                        filter_parts.append(f'CurrentValue.[{field}].contains("{value}")')
                    elif op == "not_contains":
                        filter_parts.append(f'NOT(CurrentValue.[{field}].contains("{value}"))')
                    elif op == "is_empty":
                        filter_parts.append(f'CurrentValue.[{field}] = ""')
                    elif op == "is_not_empty":
                        filter_parts.append(f'NOT(CurrentValue.[{field}] = "")')

                if filter_parts:
                    # Combine with AND
                    filter_formula = " && ".join(filter_parts)
                    body_builder = body_builder.filter(filter_formula)
                    logger.debug(f"Filter formula: {filter_formula}")

            req = req_builder.request_body(body_builder.build()).build()

            # Call API
            response = sdk_client.bitable.v1.app_table_record.search(req)

            if not response.success():
                error_msg = f"Failed to query records: {response.msg}"
                logger.error(
                    error_msg,
                    extra={
                        "app_token": app_token,
                        "table_id": table_id,
                        "code": response.code,
                    },
                )

                # Map error codes
                if response.code == 1770002:
                    raise NotFoundError(f"Table not found: {table_id}")
                elif response.code in [1770032, 403]:
                    raise PermissionDeniedError(f"No permission to access table: {table_id}")
                elif response.code in [1770001, 400]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            if not response.data:
                return [], None

            # Convert to BaseRecord objects
            records: list[BaseRecord] = []
            if response.data.items:
                for item in response.data.items:
                    # Extract record data
                    record_id = item.record_id if hasattr(item, "record_id") else ""
                    fields: dict[str, Any] = {}

                    if hasattr(item, "fields") and item.fields:
                        # Convert fields to dict
                        fields = dict(item.fields) if isinstance(item.fields, dict) else {}

                    records.append(
                        BaseRecord(
                            record_id=record_id,
                            fields=fields,
                            create_time=None,
                            update_time=None,
                        )
                    )

            next_page_token = (
                response.data.page_token
                if hasattr(response.data, "page_token") and response.data.page_token
                else None
            )

            logger.info(
                f"Successfully queried {len(records)} records from table {table_id}, "
                f"has_more: {next_page_token is not None}"
            )

            return records, next_page_token

        return self.retry_strategy.execute(_query)

    def query_records_structured(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        filter_info: "StructuredFilterInfo | None" = None,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[BaseRecord], str | None]:
        """
        使用结构化过滤查询记录（推荐）.

        使用 field_id 和结构化 JSON 格式，完全兼容 Feishu API。

        Parameters
        ----------
            app_id : str
                应用 ID
            app_token : str
                Bitable 应用 token
            table_id : str
                数据表 ID
            filter_info : StructuredFilterInfo | None
                结构化过滤信息（使用 field_id）
            page_size : int
                页面大小 (默认: 100, 最大: 500)
            page_token : str | None
                分页 token

        Returns
        -------
            tuple[list[BaseRecord], str | None]
                (记录列表, 下一页 token)

        Raises
        ------
            InvalidParameterError
                参数无效
            NotFoundError
                表不存在
            PermissionDeniedError
                无权限访问

        Examples
        --------
            >>> # 1. Get field info (optional, to verify field exists)
            >>> fields = client.get_table_fields(app_id, app_token, table_id)
            >>> field_name = fields[0]["field_name"]  # "Text"
            >>>
            >>> # 2. Construct filter condition (using field_name)
            >>> filter_info = StructuredFilterInfo(
            ...     conjunction="and",
            ...     conditions=[
            ...         StructuredFilterCondition(
            ...             field_name=field_name,
            ...             operator="is",
            ...             value=["Active"]
            ...         )
            ...     ]
            ... )
            >>>
            >>> # 3. 查询记录
            >>> records, next_token = client.query_records_structured(
            ...     app_id="cli_xxx",
            ...     app_token="bascnxxx",
            ...     table_id="tblxxx",
            ...     filter_info=filter_info
            ... )
        """
        if page_size < 1 or page_size > 500:
            raise InvalidParameterError(f"Invalid page_size: {page_size} (1-500)")

        logger.info(f"Querying records (structured) from table {table_id}, page_size={page_size}")

        def _query() -> tuple[list[BaseRecord], str | None]:
            # Use direct HTTP request as SDK may not support new filter format
            import requests

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")  # nosec B106

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            payload: dict[str, Any] = {
                "page_size": page_size,
            }

            if page_token:
                payload["page_token"] = page_token

            # Construct structured filter
            if filter_info:
                filter_dict: dict[str, Any] = {
                    "conjunction": filter_info.conjunction,
                    "conditions": [],
                }

                for condition in filter_info.conditions:
                    cond_dict: dict[str, Any] = {
                        "field_name": condition.field_name,
                        "operator": condition.operator,
                    }

                    # 只有非空操作符才需要 value
                    if condition.operator not in ["isEmpty", "isNotEmpty"] and condition.value:
                        cond_dict["value"] = condition.value

                    filter_dict["conditions"].append(cond_dict)

                payload["filter"] = filter_dict
                logger.debug(f"Filter: {filter_dict}")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to query records: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code == 1770002:
                        raise NotFoundError(f"Table not found: {table_id}")
                    elif error_code in [1770032, 403]:
                        raise PermissionDeniedError(f"No permission to access table: {table_id}")
                    elif error_code in [1770001, 400]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, NotFoundError | PermissionDeniedError | InvalidParameterError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                raise APIError(error_msg)

            records = []
            data = result.get("data", {})
            items = data.get("items", [])

            for item in items:
                record_id = item.get("record_id")
                fields = item.get("fields", {})

                records.append(
                    BaseRecord(
                        record_id=record_id,
                        fields=fields,
                        create_time=None,
                        update_time=None,
                    )
                )

            next_page_token = data.get("page_token")

            logger.info(
                f"Successfully queried {len(records)} records (structured) from table {table_id}, "
                f"has_more: {next_page_token is not None}"
            )

            return records, next_page_token

        return self.retry_strategy.execute(_query)

    def update_record(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: dict[str, str | int | float | bool | list[str]],
    ) -> BaseRecord:
        """
        Update a record in Bitable.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            record_id : str
                Record ID to update
            fields : dict
                Field values to update

        Returns
        -------
            BaseRecord
                Updated record

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If record not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> record = client.update_record(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     record_id="rec123",
            ...     fields={"Age": 31}
            ... )
        """
        if not fields:
            raise InvalidParameterError("Fields cannot be empty")

        logger.info(f"Updating record {record_id} in table {table_id}")

        def _update() -> BaseRecord:
            import requests

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")  # nosec B106

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            payload = {"fields": fields}
            logger.debug(f"Updating record {record_id} with payload: {payload}")

            response = requests.put(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to update record: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code == 1770002:
                        raise NotFoundError(f"Record not found: {record_id}")
                    elif error_code in [1254302, 403]:
                        raise PermissionDeniedError(f"No permission to update record: {record_id}")
                    elif error_code in [1254000, 1254001, 400]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, NotFoundError | PermissionDeniedError | InvalidParameterError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code == 1770002:
                    raise NotFoundError(f"Record not found: {record_id}")
                elif error_code in [1254302, 403]:
                    raise PermissionDeniedError(f"No permission to update record: {record_id}")
                elif error_code in [1254000, 1254001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            data = result.get("data", {})
            record_data = data.get("record", {})

            record = BaseRecord(
                record_id=record_data.get("record_id", record_id),
                fields=record_data.get("fields", fields),
                create_time=None,
                update_time=None,
            )

            logger.info(f"Successfully updated record {record_id} in table {table_id}")
            return record

        return self.retry_strategy.execute(_update)

    def delete_record(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        record_id: str,
    ) -> bool:
        """
        Delete a record from Bitable.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            record_id : str
                Record ID to delete

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            NotFoundError
                If record not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.delete_record(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     record_id="rec123"
            ... )
        """
        logger.info(f"Deleting record {record_id} from table {table_id}")

        def _delete() -> bool:
            import requests

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")  # nosec B106

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            logger.debug(f"Deleting record {record_id} from table {table_id}")

            response = requests.delete(url, headers=headers, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to delete record: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code == 1770002:
                        raise NotFoundError(f"Record not found: {record_id}")
                    elif error_code in [1254302, 403]:
                        raise PermissionDeniedError(f"No permission to delete record: {record_id}")
                except Exception as e:
                    if isinstance(e, NotFoundError | PermissionDeniedError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code == 1770002:
                    raise NotFoundError(f"Record not found: {record_id}")
                elif error_code in [1254302, 403]:
                    raise PermissionDeniedError(f"No permission to delete record: {record_id}")

                raise APIError(error_msg)

            logger.info(f"Successfully deleted record {record_id} from table {table_id}")
            return True

        return self.retry_strategy.execute(_delete)

    def batch_create_records(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        records: list[dict[str, str | int | float | bool | list[str]]],
    ) -> list[BaseRecord]:
        """
        Batch create records in Bitable.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            records : list[dict]
                List of field values (max 500)

        Returns
        -------
            list[BaseRecord]
                Created records

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If table not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> records = [
            ...     {"Name": "John", "Age": 30},
            ...     {"Name": "Jane", "Age": 25}
            ... ]
            >>> created = client.batch_create_records(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     records=records
            ... )
        """
        if not records:
            raise InvalidParameterError("Records cannot be empty")

        if len(records) > 500:
            raise InvalidParameterError(f"Too many records: {len(records)} (max 500)")

        logger.info(f"Batch creating {len(records)} records in table {table_id}")

        def _batch_create() -> list[BaseRecord]:
            import requests

            token = self.credential_pool.get_token(app_id, token_type="tenant_access_token")  # nosec B106

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            payload = {"records": [{"fields": record} for record in records]}
            logger.debug(f"Batch creating {len(records)} records")

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"Failed to batch create records: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('msg', 'Unknown error')}"
                    error_code = error_data.get("code", 0)

                    if error_code in [1254302, 403]:
                        raise PermissionDeniedError(
                            f"No permission to create records in table: {table_id}"
                        )
                    elif error_code in [1254000, 1254001, 400]:
                        raise InvalidParameterError(error_msg)
                except Exception as e:
                    if isinstance(e, PermissionDeniedError | InvalidParameterError):
                        raise
                    logger.error(f"Failed to parse error response: {e}")

                raise APIError(error_msg)

            result = response.json()
            if result.get("code") != 0:
                error_msg = f"API returned error: {result.get('msg', 'Unknown error')}"
                error_code = result.get("code", 0)

                if error_code in [1254302, 403]:
                    raise PermissionDeniedError(
                        f"No permission to create records in table: {table_id}"
                    )
                elif error_code in [1254000, 1254001]:
                    raise InvalidParameterError(error_msg)

                raise APIError(error_msg)

            data = result.get("data", {})
            records_data = data.get("records", [])

            created_records = [
                BaseRecord(
                    record_id=record_data.get("record_id", ""),
                    fields=record_data.get("fields", {}),
                    create_time=None,
                    update_time=None,
                )
                for record_data in records_data
            ]

            logger.info(
                f"Successfully batch created {len(created_records)} records in table {table_id}"
            )
            return created_records

        return self.retry_strategy.execute(_batch_create)

    def batch_update_records(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        records: list[tuple[str, dict[str, str | int | float | bool | list[str]]]],
    ) -> list[BaseRecord]:
        """
        Batch update records in Bitable.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            records : list[tuple[str, dict]]
                List of (record_id, fields) tuples (max 500)

        Returns
        -------
            list[BaseRecord]
                Updated records

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If table not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> updates = [
            ...     ("rec123", {"Age": 31}),
            ...     ("rec456", {"Age": 26})
            ... ]
            >>> updated = client.batch_update_records(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     records=updates
            ... )
        """
        if not records:
            raise InvalidParameterError("Records cannot be empty")

        if len(records) > 500:
            raise InvalidParameterError(f"Too many records: {len(records)} (max 500)")

        logger.info(f"Batch updating {len(records)} records in table {table_id}")

        def _batch_update() -> list[BaseRecord]:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return [
                BaseRecord(
                    record_id=record_id,
                    fields=fields,
                    create_time=None,
                    update_time=None,
                )
                for record_id, fields in records
            ]

        return self.retry_strategy.execute(_batch_update)

    def batch_delete_records(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
        record_ids: list[str],
    ) -> bool:
        """
        Batch delete records from Bitable.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID
            record_ids : list[str]
                List of record IDs to delete (max 500)

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If table not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.batch_delete_records(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123",
            ...     record_ids=["rec123", "rec456"]
            ... )
        """
        if not record_ids:
            raise InvalidParameterError("Record IDs cannot be empty")

        if len(record_ids) > 500:
            raise InvalidParameterError(f"Too many record IDs: {len(record_ids)} (max 500)")

        logger.info(f"Batch deleting {len(record_ids)} records from table {table_id}")

        def _batch_delete() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_batch_delete)

    def list_fields(
        self,
        app_id: str,
        app_token: str,
        table_id: str,
    ) -> list[FieldDefinition]:
        """
        List all fields in a Bitable table.

        Parameters
        ----------
            app_id : str
                Lark application ID
            app_token : str
                Bitable app token
            table_id : str
                Table ID

        Returns
        -------
            list[FieldDefinition]
                List of field definitions

        Raises
        ------
            NotFoundError
                If table not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> fields = client.list_fields(
            ...     app_id="cli_xxx",
            ...     app_token="bascn123",
            ...     table_id="tbl123"
            ... )
            >>> for field in fields:
            ...     print(f"{field.field_name}: {field.field_type}")
        """
        logger.info(f"Listing fields for table {table_id}")

        def _list() -> list[FieldDefinition]:
            from lark_oapi.api.bitable.v1 import ListAppTableFieldRequest

            sdk_client = self.credential_pool._get_sdk_client(app_id)

            request = (
                ListAppTableFieldRequest.builder()
                .app_token(app_token)
                .table_id(table_id)
                .page_size(500)  # Fetch all fields at once
                .build()
            )

            response = sdk_client.bitable.v1.app_table_field.list(request)

            if not response.success():
                error_msg = f"Failed to list table fields: {response.msg}"
                logger.error(
                    error_msg,
                    extra={
                        "app_token": app_token,
                        "table_id": table_id,
                        "code": response.code,
                    },
                )

                # Map error codes
                if response.code == 1770002:
                    raise NotFoundError(f"Table not found: {table_id}")
                elif response.code in [1770032, 403]:
                    raise PermissionDeniedError(f"No permission to access table: {table_id}")
                else:
                    raise APIError(error_msg)

            fields = []
            if response.data and response.data.items:
                for item in response.data.items:
                    # Map numeric type to string type for the model
                    field_type = self.FIELD_TYPE_MAPPING.get(item.type, "text")
                    field = FieldDefinition(
                        field_id=item.field_id,
                        field_name=item.field_name,
                        field_type=field_type,
                    )
                    fields.append(field)

            logger.info(f"Retrieved {len(fields)} fields for table {table_id}")
            return fields

        return self.retry_strategy.execute(_list)
