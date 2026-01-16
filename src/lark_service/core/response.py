"""Standard response model for Lark Service.

This module defines the standardized response structure for all API operations.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail information.

    Attributes
    ----------
        code: Error code
        message: Error message
        field: Field name (for validation errors)
        details: Additional error details
    """

    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] | None = None


class StandardResponse(BaseModel, Generic[T]):
    """Standardized response structure for all operations.

    Provides consistent response format with status code, message,
    request tracking, and optional data/error information.

    Attributes
    ----------
        code: Response status code (0 for success, non-zero for errors)
        message: Human-readable message
        request_id: Unique request identifier for tracking
        data: Response data (generic type)
        error: Error details (present when code != 0)

    Example
    ----------
        >>> # Success response
        >>> response = StandardResponse.success(
        ...     data={"user_id": "123"},
        ...     message="User retrieved successfully",
        ...     request_id="req_xxx"
        ... )
        >>> print(response.code)
        0
        >>> print(response.data)
        {'user_id': '123'}

        >>> # Error response
        >>> response = StandardResponse.error(
        ...     code=1001,
        ...     message="Token acquisition failed",
        ...     error=ErrorDetail(code="TOKEN_ERROR", message="Invalid app_id"),
        ...     request_id="req_yyy"
        ... )
        >>> print(response.code)
        1001
    """

    code: int = Field(..., description="Status code (0 = success, non-zero = error)")
    message: str = Field(..., description="Human-readable message")
    request_id: str | None = Field(None, description="Request tracking ID")
    data: T | None = Field(None, description="Response data")
    error_detail: ErrorDetail | None = Field(None, description="Error details")

    @classmethod
    def success(
        cls,
        data: T | None = None,
        message: str = "Success",
        request_id: str | None = None,
    ) -> "StandardResponse[T]":
        """Create a success response.

        Parameters
        ----------
            data: Response data
            message: Success message
            request_id: Request tracking ID

        Returns
        ----------
            StandardResponse with code=0
        """
        return cls(code=0, message=message, request_id=request_id, data=data, error_detail=None)

    @classmethod
    def error(
        cls,
        code: int,
        message: str,
        error_detail: ErrorDetail | None = None,
        request_id: str | None = None,
    ) -> "StandardResponse[T]":
        """Create an error response.

        Parameters
        ----------
            code: Error code (non-zero)
            message: Error message
            error_detail: Detailed error information
            request_id: Request tracking ID

        Returns
        ----------
            StandardResponse with non-zero code
        """
        if code == 0:
            raise ValueError("Error code must be non-zero")

        return cls(
            code=code, message=message, request_id=request_id, data=None, error_detail=error_detail
        )

    def is_success(self) -> bool:
        """Check if response indicates success.

        Returns
        ----------
            True if code is 0, False otherwise
        """
        return self.code == 0

    def is_error(self) -> bool:
        """Check if response indicates error.

        Returns
        ----------
            True if code is non-zero, False otherwise
        """
        return self.code != 0
