"""
Messaging client for Lark IM API.

This module provides a high-level client for sending messages via Lark IM API,
including text, rich text, images, files, and interactive cards.
"""

from pathlib import Path
from typing import Any

from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

from lark_service.core.base_service_client import BaseServiceClient
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, RetryableError
from lark_service.core.retry import RetryStrategy
from lark_service.messaging.media_uploader import MediaUploader
from lark_service.messaging.models import (
    BatchSendResponse,
    BatchSendResult,
)
from lark_service.utils.logger import get_logger

logger = get_logger()


class MessagingClient(BaseServiceClient):
    """
    High-level client for Lark messaging operations.

    Provides convenient methods for sending various types of messages
    via Lark IM API, with automatic media upload and error handling.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        media_uploader : MediaUploader
            Media uploader for images and files
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> client = MessagingClient(credential_pool)
        >>> response = client.send_text_message(
        ...     app_id="cli_xxx",
        ...     receiver_id="ou_xxx",
        ...     content="Hello, World!"
        ... )
        >>> print(response["message_id"])
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        app_id: str | None = None,
        media_uploader: MediaUploader | None = None,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize MessagingClient.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            app_id : str | None
                Optional default app_id for this client (layer 3 in priority)
            media_uploader : MediaUploader | None
                Media uploader (default: creates new instance)
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)

        Examples
        --------
        Single-app scenario (no app_id needed):

        >>> pool = CredentialPool(...)
        >>> pool.set_default_app_id("cli_xxx")
        >>> client = MessagingClient(pool)
        >>> client.send_text_message(receiver_id="ou_xxx", text="Hello")

        Multi-app scenario with client-level default:

        >>> pool = CredentialPool(...)
        >>> client = MessagingClient(pool, app_id="cli_app1")
        >>> client.send_text_message(receiver_id="ou_xxx", text="Hello")
        """
        # Initialize base class
        super().__init__(credential_pool, app_id)

        self.retry_strategy = retry_strategy or RetryStrategy()
        self.media_uploader = media_uploader or MediaUploader(credential_pool, self.retry_strategy)

    def _send_message(
        self,
        receiver_id: str,
        msg_type: str,
        content: str | dict[str, Any],
        receive_id_type: str = "open_id",
        app_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Internal method to send a message via Lark IM API.

        Parameters
        ----------
            receiver_id : str
                Receiver user or chat ID
            msg_type : str
                Message type (text, post, image, file, interactive)
            content : str | dict[str, Any]
                Message content (string or dict depending on type)
            receive_id_type : str
                Receiver ID type (default: "open_id")
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

        Returns
        -------
            dict[str, Any]
                Response containing message_id and other metadata

        Raises
        ------
            RetryableError
                If message send fails after retries
        """
        # Resolve app_id using priority mechanism
        resolved_app_id = self._resolve_app_id(app_id)

        # Get SDK client
        client = self.credential_pool._get_sdk_client(resolved_app_id)

        logger.debug(f"Sending message using app_id: {resolved_app_id}")

        # Prepare content string
        if isinstance(content, dict):
            import json

            content_str = json.dumps(content)
        else:
            content_str = content

        # Create request
        request = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receiver_id)
                .msg_type(msg_type)
                .content(content_str)
                .build()
            )
            .build()
        )

        # Send with retry
        try:
            response = self.retry_strategy.execute(
                lambda **kwargs: client.im.v1.message.create(request),
                operation_name=f"send_{msg_type}_message",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to send {msg_type} message: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "receiver_id": receiver_id,
                    },
                )

            # Extract response data
            message_id = response.data.message_id
            create_time = response.data.create_time

            logger.info(
                f"{msg_type.capitalize()} message sent successfully: {message_id}",
                extra={
                    "app_id": app_id,
                    "receiver_id": receiver_id,
                    "message_id": message_id,
                    "msg_type": msg_type,
                },
            )

            return {
                "message_id": message_id,
                "create_time": create_time,
                "receiver_id": receiver_id,
                "msg_type": msg_type,
            }

        except Exception as e:
            logger.error(
                f"Failed to send {msg_type} message: {e}",
                extra={"app_id": app_id, "receiver_id": receiver_id},
                exc_info=True,
            )
            raise

    def send_text_message(
        self,
        receiver_id: str,
        content: str,
        receive_id_type: str = "open_id",
        app_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a text message.

        Parameters
        ----------
            receiver_id : str
                Receiver user or chat ID
            content : str
                Text message content
            receive_id_type : str
                Receiver ID type (default: "open_id")
            app_id : str | None
                Optional app_id (uses resolution priority if not provided)

        Returns
        -------
            dict[str, Any]
                Response containing message_id and metadata

        Raises
        ------
            InvalidParameterError
                If content is empty
            RetryableError
                If message send fails after retries

        Examples
        --------
        Single-app scenario (no app_id needed):

            >>> pool = CredentialPool(...)
            >>> pool.set_default_app_id("cli_xxx")
            >>> client = MessagingClient(pool)
            >>> response = client.send_text_message(
            ...     receiver_id="ou_xxx",
            ...     content="Hello, World!"
            ... )
            >>> print(response["message_id"])

        Multi-app scenario with explicit app_id:

            >>> response = client.send_text_message(
            ...     receiver_id="ou_xxx",
            ...     content="Hello",
            ...     app_id="cli_xxx"
            ... )
        """
        if not content or not content.strip():
            raise InvalidParameterError(
                "Message content cannot be empty",
                details={"content": content},
            )

        # Prepare content
        content_dict = {"text": content}

        return self._send_message(
            receiver_id=receiver_id,
            msg_type="text",
            content=content_dict,
            receive_id_type=receive_id_type,
            app_id=app_id,
        )

    def send_rich_text_message(
        self,
        app_id: str,
        receiver_id: str,
        content: dict[str, Any],
        receive_id_type: str = "open_id",
    ) -> dict[str, Any]:
        """
        Send a rich text (post) message.

        Rich text messages support formatting like bold, italic, links, and @mentions.

        Parameters
        ----------
            app_id : str
                Lark application ID
            receiver_id : str
                Receiver user or chat ID
            content : dict[str, Any]
                Rich text content structure (with language keys like "zh_cn", "en_us")
            receive_id_type : str
                Receiver ID type (default: "open_id")

        Returns
        -------
            dict[str, Any]
                Response containing message_id and metadata

        Raises
        ------
            InvalidParameterError
                If content is empty or invalid
            RetryableError
                If message send fails after retries

        Examples
        --------
            >>> content = {
            ...     "zh_cn": {
            ...         "title": "通知",
            ...         "content": [
            ...             [{"tag": "text", "text": "重要提醒"}],
            ...             [{"tag": "a", "text": "点击查看", "href": "https://example.com"}]
            ...         ]
            ...     }
            ... }
            >>> response = client.send_rich_text_message(
            ...     app_id="cli_xxx",
            ...     receiver_id="ou_xxx",
            ...     content=content
            ... )
        """
        if not content:
            raise InvalidParameterError(
                "Rich text content cannot be empty",
                details={"content": content},
            )

        # Wrap content in post structure
        post_content = {"post": content}

        return self._send_message(
            app_id=app_id,
            receiver_id=receiver_id,
            msg_type="post",
            content=post_content,
            receive_id_type=receive_id_type,
        )

    def send_image_message(
        self,
        app_id: str,
        receiver_id: str,
        image_path: str | Path | None = None,
        image_key: str | None = None,
        receive_id_type: str = "open_id",
    ) -> dict[str, Any]:
        """
        Send an image message.

        Either provide image_path (will auto-upload) or image_key (already uploaded).

        Parameters
        ----------
            app_id : str
                Lark application ID
            receiver_id : str
                Receiver user or chat ID
            image_path : str | Path | None
                Path to image file (will be uploaded automatically)
            image_key : str | None
                Pre-uploaded image key (e.g., "img_v2_xxx")
            receive_id_type : str
                Receiver ID type (default: "open_id")

        Returns
        -------
            dict[str, Any]
                Response containing message_id and metadata

        Raises
        ------
            InvalidParameterError
                If neither image_path nor image_key is provided
            RetryableError
                If upload or message send fails after retries

        Examples
        --------
            >>> # Auto-upload image
            >>> response = client.send_image_message(
            ...     app_id="cli_xxx",
            ...     receiver_id="ou_xxx",
            ...     image_path="/path/to/image.jpg"
            ... )

            >>> # Use pre-uploaded image
            >>> response = client.send_image_message(
            ...     app_id="cli_xxx",
            ...     receiver_id="ou_xxx",
            ...     image_key="img_v2_a1b2c3d4"
            ... )
        """
        if not image_path and not image_key:
            raise InvalidParameterError(
                "Either image_path or image_key must be provided",
                details={"image_path": image_path, "image_key": image_key},
            )

        # Upload image if path is provided
        if image_path:
            asset = self.media_uploader.upload_image(app_id, image_path)
            image_key = asset.image_key

        # Prepare content
        content_dict = {"image_key": image_key}

        return self._send_message(
            app_id=app_id,
            receiver_id=receiver_id,
            msg_type="image",
            content=content_dict,
            receive_id_type=receive_id_type,
        )

    def send_file_message(
        self,
        app_id: str,
        receiver_id: str,
        file_path: str | Path | None = None,
        file_key: str | None = None,
        receive_id_type: str = "open_id",
    ) -> dict[str, Any]:
        """
        Send a file message.

        Either provide file_path (will auto-upload) or file_key (already uploaded).

        Parameters
        ----------
            app_id : str
                Lark application ID
            receiver_id : str
                Receiver user or chat ID
            file_path : str | Path | None
                Path to file (will be uploaded automatically)
            file_key : str | None
                Pre-uploaded file key (e.g., "file_v2_xxx")
            receive_id_type : str
                Receiver ID type (default: "open_id")

        Returns
        -------
            dict[str, Any]
                Response containing message_id and metadata

        Raises
        ------
            InvalidParameterError
                If neither file_path nor file_key is provided
            RetryableError
                If upload or message send fails after retries

        Examples
        --------
            >>> # Auto-upload file
            >>> response = client.send_file_message(
            ...     app_id="cli_xxx",
            ...     receiver_id="ou_xxx",
            ...     file_path="/path/to/document.pdf"
            ... )

            >>> # Use pre-uploaded file
            >>> response = client.send_file_message(
            ...     app_id="cli_xxx",
            ...     receiver_id="ou_xxx",
            ...     file_key="file_v2_a1b2c3d4"
            ... )
        """
        if not file_path and not file_key:
            raise InvalidParameterError(
                "Either file_path or file_key must be provided",
                details={"file_path": file_path, "file_key": file_key},
            )

        # Upload file if path is provided
        if file_path:
            asset = self.media_uploader.upload_file(app_id, file_path)
            file_key = asset.file_key

        # Prepare content
        content_dict = {"file_key": file_key}

        return self._send_message(
            app_id=app_id,
            receiver_id=receiver_id,
            msg_type="file",
            content=content_dict,
            receive_id_type=receive_id_type,
        )

    def send_card_message(
        self,
        app_id: str,
        receiver_id: str,
        card_content: dict[str, Any],
        receive_id_type: str = "open_id",
    ) -> dict[str, Any]:
        """
        Send an interactive card message.

        Card content should be built using CardKit builder module.

        Parameters
        ----------
            app_id : str
                Lark application ID
            receiver_id : str
                Receiver user or chat ID
            card_content : dict[str, Any]
                Card JSON structure (built by CardKit)
            receive_id_type : str
                Receiver ID type (default: "open_id")

        Returns
        -------
            dict[str, Any]
                Response containing message_id and metadata

        Raises
        ------
            InvalidParameterError
                If card_content is empty or invalid
            RetryableError
                If message send fails after retries

        Examples
        --------
            >>> card = {
            ...     "header": {"title": {"tag": "plain_text", "content": "Approval"}},
            ...     "elements": [
            ...         {"tag": "div", "text": {"tag": "lark_md", "content": "**Name**: John"}},
            ...         {"tag": "action", "actions": [...]}
            ...     ]
            ... }
            >>> response = client.send_card_message(
            ...     app_id="cli_xxx",
            ...     receiver_id="ou_xxx",
            ...     card_content=card
            ... )
        """
        if not card_content:
            raise InvalidParameterError(
                "Card content cannot be empty",
                details={"card_content": card_content},
            )

        return self._send_message(
            app_id=app_id,
            receiver_id=receiver_id,
            msg_type="interactive",
            content=card_content,
            receive_id_type=receive_id_type,
        )

    def send_batch_messages(
        self,
        app_id: str,
        receiver_ids: list[str],
        msg_type: str,
        content: str | dict[str, Any],
        receive_id_type: str = "open_id",
        continue_on_error: bool = True,
    ) -> BatchSendResponse:
        """
        Send the same message to multiple receivers.

        Sends messages sequentially to each receiver, tracking success/failure
        for each one. By default, continues sending even if some fail.

        Parameters
        ----------
            app_id : str
                Lark application ID
            receiver_ids : list[str]
                List of receiver user or chat IDs
            msg_type : str
                Message type (text, post, image, file, interactive)
            content : str | dict[str, Any]
                Message content (same for all receivers)
            receive_id_type : str
                Receiver ID type (default: "open_id")
            continue_on_error : bool
                Continue sending to remaining receivers if one fails (default: True)

        Returns
        -------
            BatchSendResponse
                Response containing total, success, failed counts and individual results

        Raises
        ------
            InvalidParameterError
                If receiver_ids is empty or exceeds maximum limit (200)

        Examples
        --------
            >>> response = client.send_batch_messages(
            ...     app_id="cli_xxx",
            ...     receiver_ids=["ou_user1", "ou_user2", "ou_user3"],
            ...     msg_type="text",
            ...     content={"text": "System maintenance notice"}
            ... )
            >>> print(f"Success: {response.success}/{response.total}")
        """
        if not receiver_ids:
            raise InvalidParameterError(
                "Receiver IDs list cannot be empty",
                details={"receiver_ids": receiver_ids},
            )

        if len(receiver_ids) > 200:
            raise InvalidParameterError(
                "Receiver IDs list exceeds maximum limit of 200",
                details={"count": len(receiver_ids), "max": 200},
            )

        results: list[BatchSendResult] = []
        success_count = 0
        failed_count = 0

        logger.info(
            f"Starting batch send to {len(receiver_ids)} receivers",
            extra={
                "app_id": app_id,
                "total_receivers": len(receiver_ids),
                "msg_type": msg_type,
            },
        )

        for receiver_id in receiver_ids:
            try:
                response = self._send_message(
                    app_id=app_id,
                    receiver_id=receiver_id,
                    msg_type=msg_type,
                    content=content,
                    receive_id_type=receive_id_type,
                )

                results.append(
                    BatchSendResult(
                        receiver_id=receiver_id,
                        status="success",
                        message_id=response["message_id"],
                        error=None,
                    )
                )
                success_count += 1

            except Exception as e:
                error_msg = str(e)
                results.append(
                    BatchSendResult(
                        receiver_id=receiver_id,
                        status="failed",
                        message_id=None,
                        error=error_msg,
                    )
                )
                failed_count += 1

                logger.warning(
                    f"Failed to send message to {receiver_id}: {error_msg}",
                    extra={
                        "app_id": app_id,
                        "receiver_id": receiver_id,
                        "error": error_msg,
                    },
                )

                # Stop if continue_on_error is False
                if not continue_on_error:
                    logger.error(
                        "Stopping batch send due to error (continue_on_error=False)",
                        extra={"app_id": app_id, "processed": len(results)},
                    )
                    break

        logger.info(
            f"Batch send completed: {success_count} success, {failed_count} failed",
            extra={
                "app_id": app_id,
                "total": len(receiver_ids),
                "success": success_count,
                "failed": failed_count,
            },
        )

        return BatchSendResponse(
            total=len(receiver_ids),
            success=success_count,
            failed=failed_count,
            results=results,
        )

    def update_message(
        self,
        app_id: str,
        message_id: str,
        content: str,
        msg_type: str = "interactive",
    ) -> dict[str, Any]:
        """Update an existing message.

        Updates the content of a previously sent message.
        Commonly used to update interactive cards.

        Parameters
        ----------
            app_id : str
                Lark application ID
            message_id : str
                The message ID to update
            content : str
                New message content (JSON string for interactive cards)
            msg_type : str
                Message type (default: "interactive")

        Returns
        -------
            dict[str, Any]
                Update response from Lark API

        Raises
        ------
            InvalidParameterError
                If message_id or content is invalid
            RetryableError
                If API call fails after retries

        Examples
        --------
            >>> # Update an interactive card
            >>> client.update_message(
            ...     app_id="cli_xxx",
            ...     message_id="om_xxx",
            ...     content='{"elements": [...]}',
            ...     msg_type="interactive"
            ... )
        """
        if not message_id:
            raise InvalidParameterError("message_id cannot be empty")

        if not content:
            raise InvalidParameterError("content cannot be empty")

        # Import here to avoid circular dependency
        from lark_oapi.api.im.v1 import (
            PatchMessageRequest,
            PatchMessageRequestBody,
        )

        logger.info(
            f"Updating message {message_id}",
            extra={"app_id": app_id, "message_id": message_id, "msg_type": msg_type},
        )

        # Get SDK client
        sdk_client = self.credential_pool._get_sdk_client(app_id)

        # Build request
        # Note: PatchMessage only updates content, msg_type is inferred from original message
        request = (
            PatchMessageRequest.builder()
            .message_id(message_id)
            .request_body(PatchMessageRequestBody.builder().content(content).build())
            .build()
        )

        # Execute with retry
        def _update() -> dict[str, Any]:
            response = sdk_client.im.v1.message.patch(request)

            if not response.success():
                error_msg = f"Failed to update message: {response.code} - {response.msg}"
                logger.error(error_msg, extra={"app_id": app_id, "message_id": message_id})
                raise RetryableError(error_msg)

            logger.info(
                f"Message {message_id} updated successfully",
                extra={"app_id": app_id, "message_id": message_id},
            )

            return {"message_id": message_id, "success": True}

        return self.retry_strategy.execute(_update)
