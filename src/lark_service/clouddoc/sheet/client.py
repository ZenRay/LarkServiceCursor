"""
Sheet client for Lark Sheets API.

This module provides a high-level client for spreadsheet operations
via Lark Sheets API, including reading, updating, formatting, and managing cells.
"""

from lark_service.clouddoc.models import CellData
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


class SheetClient:
    """
    High-level client for Lark Sheet operations.

    Provides convenient methods for managing spreadsheets
    via Lark Sheets API, with automatic error handling and retry.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> client = SheetClient(credential_pool)
        >>> data = client.get_sheet_data(
        ...     app_id="cli_xxx",
        ...     spreadsheet_token="shtcn123",
        ...     sheet_id="sheet1",
        ...     range_str="A1:B10"
        ... )
        >>> print(len(data))
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize SheetClient.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def get_sheet_data(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        range_str: str,
    ) -> list[list[CellData]]:
        """
        Get sheet data within specified range.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            range_str : str
                Range string (e.g., "A1:B10")

        Returns
        -------
            list[list[CellData]]
                2D array of cell data

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> data = client.get_sheet_data(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     range_str="A1:B10"
            ... )
            >>> for row in data:
            ...     for cell in row:
            ...         print(cell.value)
        """
        if not range_str:
            raise InvalidParameterError("Range string cannot be empty")

        logger.info(f"Getting sheet data: {sheet_id}!{range_str}")

        def _get() -> list[list[CellData]]:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return []

        return self.retry_strategy.execute(_get)

    def update_sheet_data(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        range_str: str,
        values: list[list[str | int | float | bool]],
    ) -> bool:
        """
        Update sheet data within specified range.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            range_str : str
                Range string (e.g., "A1:B10")
            values : list[list]
                2D array of values to update

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> values = [
            ...     ["Name", "Age"],
            ...     ["John", 30],
            ...     ["Jane", 25]
            ... ]
            >>> client.update_sheet_data(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     range_str="A1:B3",
            ...     values=values
            ... )
        """
        if not range_str:
            raise InvalidParameterError("Range string cannot be empty")

        if not values:
            raise InvalidParameterError("Values cannot be empty")

        logger.info(f"Updating sheet data: {sheet_id}!{range_str}")

        def _update() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder
            logger.info(f"Updating {len(values)} rows")

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_update)

    def format_cells(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        range_str: str,
        font_size: int | None = None,
        font_color: str | None = None,
        background_color: str | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        align: str | None = None,
        vertical_align: str | None = None,
    ) -> bool:
        """
        Format cells within specified range.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            range_str : str
                Range string (e.g., "A1:B10")
            font_size : int | None
                Font size (8-72)
            font_color : str | None
                Font color (hex, e.g., "#FF0000")
            background_color : str | None
                Background color (hex)
            bold : bool | None
                Bold text
            italic : bool | None
                Italic text
            underline : bool | None
                Underline text
            align : str | None
                Horizontal alignment (left, center, right)
            vertical_align : str | None
                Vertical alignment (top, middle, bottom)

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.format_cells(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     range_str="A1:B1",
            ...     bold=True,
            ...     font_size=14,
            ...     background_color="#EEEEEE"
            ... )
        """
        if not range_str:
            raise InvalidParameterError("Range string cannot be empty")

        if font_size is not None and (font_size < 8 or font_size > 72):
            raise InvalidParameterError(f"Invalid font_size: {font_size} (8-72)")

        if align is not None and align not in {"left", "center", "right"}:
            raise InvalidParameterError(f"Invalid align: {align}")

        if vertical_align is not None and vertical_align not in {"top", "middle", "bottom"}:
            raise InvalidParameterError(f"Invalid vertical_align: {vertical_align}")

        logger.info(f"Formatting cells: {sheet_id}!{range_str}")

        def _format() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_format)

    def merge_cells(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        range_str: str,
        merge_type: str = "merge_all",
    ) -> bool:
        """
        Merge cells within specified range.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            range_str : str
                Range string (e.g., "A1:B2")
            merge_type : str
                Merge type (merge_all, merge_rows, merge_columns)

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.merge_cells(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     range_str="A1:B2",
            ...     merge_type="merge_all"
            ... )
        """
        if not range_str:
            raise InvalidParameterError("Range string cannot be empty")

        valid_merge_types = {"merge_all", "merge_rows", "merge_columns"}
        if merge_type not in valid_merge_types:
            raise InvalidParameterError(f"Invalid merge_type: {merge_type}")

        logger.info(f"Merging cells: {sheet_id}!{range_str} ({merge_type})")

        def _merge() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_merge)

    def unmerge_cells(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        range_str: str,
    ) -> bool:
        """
        Unmerge cells within specified range.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            range_str : str
                Range string (e.g., "A1:B2")

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.unmerge_cells(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     range_str="A1:B2"
            ... )
        """
        if not range_str:
            raise InvalidParameterError("Range string cannot be empty")

        logger.info(f"Unmerging cells: {sheet_id}!{range_str}")

        def _unmerge() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_unmerge)

    def set_column_width(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        start_column: int,
        end_column: int,
        width: int,
    ) -> bool:
        """
        Set column width.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            start_column : int
                Start column index (0-based)
            end_column : int
                End column index (0-based, inclusive)
            width : int
                Column width in pixels (20-1000)

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.set_column_width(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     start_column=0,
            ...     end_column=2,
            ...     width=150
            ... )
        """
        if start_column < 0 or end_column < start_column:
            raise InvalidParameterError(f"Invalid column range: {start_column}-{end_column}")

        if width < 20 or width > 1000:
            raise InvalidParameterError(f"Invalid width: {width} (20-1000)")

        logger.info(f"Setting column width: columns {start_column}-{end_column} to {width}px")

        def _set_width() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_set_width)

    def set_row_height(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        start_row: int,
        end_row: int,
        height: int,
    ) -> bool:
        """
        Set row height.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            start_row : int
                Start row index (0-based)
            end_row : int
                End row index (0-based, inclusive)
            height : int
                Row height in pixels (20-500)

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.set_row_height(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     start_row=0,
            ...     end_row=0,
            ...     height=30
            ... )
        """
        if start_row < 0 or end_row < start_row:
            raise InvalidParameterError(f"Invalid row range: {start_row}-{end_row}")

        if height < 20 or height > 500:
            raise InvalidParameterError(f"Invalid height: {height} (20-500)")

        logger.info(f"Setting row height: rows {start_row}-{end_row} to {height}px")

        def _set_height() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_set_height)

    def freeze_panes(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
        freeze_row_count: int = 0,
        freeze_column_count: int = 0,
    ) -> bool:
        """
        Freeze rows and columns.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID
            freeze_row_count : int
                Number of rows to freeze from top (0-100)
            freeze_column_count : int
                Number of columns to freeze from left (0-26)

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            InvalidParameterError
                If parameters are invalid
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.freeze_panes(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1",
            ...     freeze_row_count=1,
            ...     freeze_column_count=1
            ... )
        """
        if freeze_row_count < 0 or freeze_row_count > 100:
            raise InvalidParameterError(f"Invalid freeze_row_count: {freeze_row_count} (0-100)")

        if freeze_column_count < 0 or freeze_column_count > 26:
            raise InvalidParameterError(
                f"Invalid freeze_column_count: {freeze_column_count} (0-26)"
            )

        logger.info(f"Freezing panes: {freeze_row_count} rows, {freeze_column_count} columns")

        def _freeze() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_freeze)

    def unfreeze_panes(
        self,
        app_id: str,
        spreadsheet_token: str,
        sheet_id: str,
    ) -> bool:
        """
        Unfreeze all frozen panes.

        Parameters
        ----------
            app_id : str
                Lark application ID
            spreadsheet_token : str
                Spreadsheet token
            sheet_id : str
                Sheet ID

        Returns
        -------
            bool
                True if successful

        Raises
        ------
            NotFoundError
                If sheet not found
            PermissionDeniedError
                If user has no permission

        Examples
        --------
            >>> client.unfreeze_panes(
            ...     app_id="cli_xxx",
            ...     spreadsheet_token="shtcn123",
            ...     sheet_id="sheet1"
            ... )
        """
        logger.info("Unfreezing all panes")

        def _unfreeze() -> bool:
            # Note: Actual API call depends on SDK implementation
            # This is a placeholder

            # TODO: Implement actual API call when SDK supports it
            return True

        return self.retry_strategy.execute(_unfreeze)
