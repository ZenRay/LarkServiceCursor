"""
Media uploader for Lark messaging.

This module provides functionality to upload images and files to Lark servers,
with validation for file size, type, and format.
"""

import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Literal

from lark_oapi.api.im.v1 import CreateFileRequest, CreateImageRequest

from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import (
    InvalidParameterError,
    RetryableError,
)
from lark_service.core.retry import RetryStrategy
from lark_service.messaging.models import FileAsset, ImageAsset
from lark_service.utils.logger import get_logger

logger = get_logger()

# File size limits (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB

# Supported file types
SUPPORTED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
}

SUPPORTED_VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
}

SUPPORTED_AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
}

SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
}


class MediaUploader:
    """
    Media uploader for Lark messaging.

    Handles uploading images and files to Lark servers with validation
    for file size, type, and format.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> uploader = MediaUploader(credential_pool, retry_strategy)
        >>> asset = uploader.upload_image("cli_xxx", "/path/to/image.jpg")
        >>> print(asset.image_key)
        img_v2_a1b2c3d4
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize MediaUploader.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : Optional[RetryStrategy]
                Retry strategy for API calls (default: None, uses default strategy)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def _validate_file_size(self, file_path: Path, max_size: int, file_type: str) -> None:
        """
        Validate file size.

        Parameters
        ----------
            file_path : Path
                Path to the file
            max_size : int
                Maximum allowed size in bytes
            file_type : str
                Type of file (for error message)

        Raises
        ------
            InvalidParameterError
                If file size exceeds the limit or file is empty
        """
        file_size = file_path.stat().st_size

        if file_size == 0:
            raise InvalidParameterError(
                f"Cannot upload empty {file_type}",
                details={"file_path": str(file_path), "file_size": 0},
            )

        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            actual_size_mb = file_size / (1024 * 1024)
            raise InvalidParameterError(
                f"{file_type.capitalize()} size exceeds maximum limit of {max_size_mb}MB",
                details={
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "max_size": max_size,
                    "actual_size_mb": f"{actual_size_mb:.2f}",
                    "max_size_mb": f"{max_size_mb:.2f}",
                },
            )

    def _validate_file_type(
        self,
        file_path: Path,
        allowed_types: dict[str, str],
        file_category: str,
    ) -> str:
        """
        Validate file type using both extension and MIME type.

        Parameters
        ----------
            file_path : Path
                Path to the file
            allowed_types : dict[str, str]
                Dictionary of allowed extensions and their MIME types
            file_category : str
                Category of file (for error message)

        Returns
        -------
            str
                MIME type of the file

        Raises
        ------
            InvalidParameterError
                If file type is not supported
        """
        file_ext = file_path.suffix.lower()

        # Check extension
        if file_ext not in allowed_types:
            supported_types = ", ".join(allowed_types.keys())
            raise InvalidParameterError(
                f"Unsupported {file_category} format: {file_ext}",
                details={
                    "file_path": str(file_path),
                    "file_extension": file_ext,
                    "supported_types": supported_types,
                },
            )

        # Get MIME type from extension
        mime_type = allowed_types[file_ext]

        # Double-check with mimetypes module (if available)
        guessed_type = mimetypes.guess_type(str(file_path))[0]
        if guessed_type and guessed_type != mime_type:
            logger.warning(
                f"MIME type mismatch: extension suggests {mime_type}, "
                f"but file content suggests {guessed_type}. Using extension-based type."
            )

        return mime_type

    def upload_image(
        self,
        app_id: str,
        image_path: str | Path,
        image_type: Literal["message", "avatar"] = "message",
    ) -> ImageAsset:
        """
        Upload an image to Lark servers.

        Parameters
        ----------
            app_id : str
                Lark application ID
            image_path : str | Path
                Path to the image file
            image_type : Literal["message", "avatar"]
                Type of image (default: "message")

        Returns
        -------
            ImageAsset
                Uploaded image asset with image_key

        Raises
        ------
            InvalidParameterError
                If file size or type is invalid
            RetryableError
                If upload fails after retries
            RequestTimeoutError
                If upload times out

        Examples
        --------
            >>> asset = uploader.upload_image("cli_xxx", "/path/to/image.jpg")
            >>> print(asset.image_key)
            img_v2_a1b2c3d4
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise InvalidParameterError(
                f"Image file not found: {image_path}",
                details={"file_path": str(image_path)},
            )

        # Validate file size
        self._validate_file_size(image_path, MAX_IMAGE_SIZE, "image")

        # Validate file type
        mime_type = self._validate_file_type(image_path, SUPPORTED_IMAGE_TYPES, "image")

        # Get SDK client (token is managed internally)
        client = self.credential_pool._get_sdk_client(app_id)

        # Create upload request
        with open(image_path, "rb") as image_file:
            request = (
                CreateImageRequest.builder()
                .request_body(
                    CreateImageRequest.RequestBody.builder()
                    .image_type(image_type)
                    .image(image_file)
                    .build()
                )
                .build()
            )

        # Upload with retry
        try:
            response = self.retry_strategy.execute(
                lambda: client.im.v1.image.create(request),
                operation_name=f"upload_image_{image_path.name}",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to upload image: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "file_path": str(image_path),
                    },
                )

            # Extract image_key from response
            image_key = response.data.image_key
            file_size = image_path.stat().st_size

            logger.info(
                f"Image uploaded successfully: {image_key}",
                extra={
                    "app_id": app_id,
                    "image_key": image_key,
                    "file_size": file_size,
                    "mime_type": mime_type,
                },
            )

            return ImageAsset(
                image_key=image_key,
                image_type=image_type,
                file_size=file_size,
                upload_time=datetime.now(),
            )

        except Exception as e:
            logger.error(
                f"Failed to upload image: {e}",
                extra={"app_id": app_id, "file_path": str(image_path)},
                exc_info=True,
            )
            raise

    def upload_file(
        self,
        app_id: str,
        file_path: str | Path,
        file_type: Literal["opus", "mp4", "pdf", "doc", "xls", "ppt", "stream"] = "stream",
    ) -> FileAsset:
        """
        Upload a file to Lark servers.

        Parameters
        ----------
            app_id : str
                Lark application ID
            file_path : str | Path
                Path to the file
            file_type : Literal["opus", "mp4", "pdf", "doc", "xls", "ppt", "stream"]
                Type of file (default: "stream" for generic files)

        Returns
        -------
            FileAsset
                Uploaded file asset with file_key

        Raises
        ------
            InvalidParameterError
                If file size or type is invalid
            RetryableError
                If upload fails after retries
            RequestTimeoutError
                If upload times out

        Examples
        --------
            >>> asset = uploader.upload_file("cli_xxx", "/path/to/document.pdf")
            >>> print(asset.file_key)
            file_v2_a1b2c3d4
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise InvalidParameterError(
                f"File not found: {file_path}",
                details={"file_path": str(file_path)},
            )

        # Validate file size
        self._validate_file_size(file_path, MAX_FILE_SIZE, "file")

        # Determine file category and validate type
        file_ext = file_path.suffix.lower()
        if file_ext in SUPPORTED_VIDEO_TYPES:
            mime_type = self._validate_file_type(file_path, SUPPORTED_VIDEO_TYPES, "video")
        elif file_ext in SUPPORTED_AUDIO_TYPES:
            mime_type = self._validate_file_type(file_path, SUPPORTED_AUDIO_TYPES, "audio")
        elif file_ext in SUPPORTED_DOCUMENT_TYPES:
            mime_type = self._validate_file_type(file_path, SUPPORTED_DOCUMENT_TYPES, "document")
        else:
            # Generic file type
            guessed_mime = mimetypes.guess_type(str(file_path))[0]
            mime_type = guessed_mime if guessed_mime else "application/octet-stream"

        # Get SDK client (token is managed internally)
        client = self.credential_pool._get_sdk_client(app_id)

        # Create upload request
        with open(file_path, "rb") as file:
            request = (
                CreateFileRequest.builder()
                .request_body(
                    CreateFileRequest.RequestBody.builder()
                    .file_type(file_type)
                    .file_name(file_path.name)
                    .file(file)
                    .build()
                )
                .build()
            )

        # Upload with retry
        try:
            response = self.retry_strategy.execute(
                lambda: client.im.v1.file.create(request),
                operation_name=f"upload_file_{file_path.name}",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to upload file: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "file_path": str(file_path),
                    },
                )

            # Extract file_key from response
            file_key = response.data.file_key
            file_size = file_path.stat().st_size

            logger.info(
                f"File uploaded successfully: {file_key}",
                extra={
                    "app_id": app_id,
                    "file_key": file_key,
                    "file_name": file_path.name,
                    "file_size": file_size,
                    "mime_type": mime_type,
                },
            )

            return FileAsset(
                file_key=file_key,
                file_name=file_path.name,
                file_type=mime_type,
                file_size=file_size,
                upload_time=datetime.now(),
            )

        except Exception as e:
            logger.error(
                f"Failed to upload file: {e}",
                extra={"app_id": app_id, "file_path": str(file_path)},
                exc_info=True,
            )
            raise
