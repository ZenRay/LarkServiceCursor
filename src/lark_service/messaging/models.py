"""
Messaging module data models.

This module defines Pydantic models for Lark messaging operations,
including message types, media assets, and related data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class MessageType(str, Enum):
    """Supported message types in Lark IM API."""

    TEXT = "text"
    RICH_TEXT = "post"
    IMAGE = "image"
    FILE = "file"
    INTERACTIVE_CARD = "interactive"


class Message(BaseModel):
    """
    Lark message data transfer object.

    This model represents a message to be sent via Lark IM API.
    It supports multiple message types including text, rich text,
    images, files, and interactive cards.

    Attributes
    ----------
        receiver_id : str
            User ID or chat ID (e.g., "ou_xxx" or "oc_xxx")
        msg_type : MessageType
            Type of message (text, post, image, file, interactive)
        content : dict
            Message content payload (structure varies by type)
        app_id : str
            Lark application ID for token isolation

    Examples
    --------
        >>> msg = Message(
        ...     receiver_id="ou_a1b2c3d4e5f6g7h8",
        ...     msg_type=MessageType.TEXT,
        ...     content={"text": "Hello, World!"},
        ...     app_id="cli_a1b2c3d4e5f6g7h8"
        ... )
    """

    receiver_id: str = Field(..., min_length=1, description="Receiver user or chat ID")
    msg_type: MessageType = Field(..., description="Message type")
    content: dict[str, Any] = Field(..., description="Message content payload")
    app_id: str = Field(..., pattern=r"^cli_[a-zA-Z0-9]{16,32}$", description="Lark app ID")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that content is not empty."""
        if not v:
            raise ValueError("Message content cannot be empty")
        return v

    model_config = {"use_enum_values": True}


class ImageAsset(BaseModel):
    """
    Uploaded image asset metadata.

    Represents an image that has been uploaded to Lark servers.
    The image_key is valid for 30 days after upload.

    Attributes
    ----------
        image_key : str
            Lark image key (e.g., "img_v2_xxxxx")
        image_type : str
            Image type (default: "message")
        file_size : int
            File size in bytes (max 10MB)
        upload_time : datetime
            Upload timestamp

    Examples
    --------
        >>> asset = ImageAsset(
        ...     image_key="img_v2_a1b2c3d4",
        ...     file_size=1048576,
        ...     upload_time=datetime.now()
        ... )
    """

    image_key: str = Field(..., description="Lark image key")
    image_type: str = Field(default="message", description="Image type")
    file_size: int = Field(..., gt=0, le=10 * 1024 * 1024, description="Size in bytes (max 10MB)")
    upload_time: datetime = Field(default_factory=datetime.now)

    @field_validator("image_key")
    @classmethod
    def validate_image_key_format(cls, v: str) -> str:
        """Validate image_key format."""
        if not v.startswith("img_v2_"):
            raise ValueError("image_key must start with 'img_v2_'")
        return v


class FileAsset(BaseModel):
    """
    Uploaded file asset metadata.

    Represents a file that has been uploaded to Lark servers.
    The file_key is valid for 30 days after upload.

    Attributes
    ----------
        file_key : str
            Lark file key (e.g., "file_v2_xxxxx")
        file_name : str
            Original filename
        file_type : str
            MIME type (e.g., "application/pdf")
        file_size : int
            File size in bytes (max 30MB)
        upload_time : datetime
            Upload timestamp

    Examples
    --------
        >>> asset = FileAsset(
        ...     file_key="file_v2_a1b2c3d4",
        ...     file_name="report.pdf",
        ...     file_type="application/pdf",
        ...     file_size=2097152,
        ...     upload_time=datetime.now()
        ... )
    """

    file_key: str = Field(..., description="Lark file key")
    file_name: str = Field(..., min_length=1, description="Original filename")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., gt=0, le=30 * 1024 * 1024, description="Size in bytes (max 30MB)")
    upload_time: datetime = Field(default_factory=datetime.now)

    @field_validator("file_key")
    @classmethod
    def validate_file_key_format(cls, v: str) -> str:
        """Validate file_key format."""
        if not v.startswith("file_v2_"):
            raise ValueError("file_key must start with 'file_v2_'")
        return v


class BatchSendResult(BaseModel):
    """
    Result for a single receiver in batch send operation.

    Attributes
    ----------
        receiver_id : str
            Receiver user or chat ID
        status : str
            Send status ("success" or "failed")
        message_id : Optional[str]
            Message ID if successful
        error : Optional[str]
            Error message if failed
    """

    receiver_id: str = Field(..., description="Receiver user or chat ID")
    status: str = Field(..., description="Send status (success/failed)")
    message_id: str | None = Field(None, description="Message ID if successful")
    error: str | None = Field(None, description="Error message if failed")


class BatchSendResponse(BaseModel):
    """
    Response for batch send operation.

    Attributes
    ----------
        total : int
            Total number of receivers
        success : int
            Number of successful sends
        failed : int
            Number of failed sends
        results : list[BatchSendResult]
            Individual results for each receiver
    """

    total: int = Field(..., ge=0, description="Total number of receivers")
    success: int = Field(..., ge=0, description="Number of successful sends")
    failed: int = Field(..., ge=0, description="Number of failed sends")
    results: list[BatchSendResult] = Field(..., description="Individual results for each receiver")

    @field_validator("total")
    @classmethod
    def validate_total_matches_results(cls, v: int, info: ValidationInfo) -> int:
        """Validate that total matches the number of results."""
        if "results" in info.data and v != len(info.data["results"]):
            raise ValueError("total must match the number of results")
        return v
