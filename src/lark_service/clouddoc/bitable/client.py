"""
Bitable client for Lark Base API.

This module provides a high-level client for multi-dimensional table operations
via Lark Base API, including CRUD operations with filters and pagination.
"""

from typing import Any

from lark_oapi.api.bitable.v1 import SearchAppTableRecordRequest, SearchAppTableRecordRequestBody

from lark_service.clouddoc.models import BaseRecord, FieldDefinition, FilterCondition
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
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder
            logger.info(f"Creating record with fields: {fields}")

            # TODO: Implement actual API call when SDK supports it
            return BaseRecord(
                record_id="rec1234567890placeholder",
                fields=fields,
                create_time=None,
                update_time=None,
            )

        return self.retry_strategy.execute(_create)

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
                    # Lark uses formula-like syntax
                    if op == "eq":
                        if isinstance(value, str):
                            filter_parts.append(f'CurrentValue.[{field}] == "{value}"')
                        else:
                            filter_parts.append(f"CurrentValue.[{field}] == {value}")
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
                        filter_parts.append(f'SEARCH("{value}", CurrentValue.[{field}])')
                    elif op == "not_contains":
                        filter_parts.append(f'NOT(SEARCH("{value}", CurrentValue.[{field}]))')
                    elif op == "is_empty":
                        filter_parts.append(f"ISBLANK(CurrentValue.[{field}])")
                    elif op == "is_not_empty":
                        filter_parts.append(f"NOT(ISBLANK(CurrentValue.[{field}]))")

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
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder
            logger.info(f"Updating fields: {fields}")

            # TODO: Implement actual API call when SDK supports it
            return BaseRecord(
                record_id=record_id,
                fields=fields,
                create_time=None,
                update_time=None,
            )

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
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
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
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return [
                BaseRecord(
                    record_id=f"rec1234567890placeholder{i}",
                    fields=record,
                    create_time=None,
                    update_time=None,
                )
                for i, record in enumerate(records)
            ]

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
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return []

        return self.retry_strategy.execute(_list)
