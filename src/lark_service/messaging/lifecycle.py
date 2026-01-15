"""
Message lifecycle management for Lark IM API.

This module provides functionality for managing message lifecycle operations
including recall, edit, and reply.
"""

from typing import Any

from lark_oapi.api.im.v1 import (
    DeleteMessageRequest,
    PatchMessageRequest,
    PatchMessageRequestBody,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, RetryableError
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


class MessageLifecycleManager:
    """
    Manager for message lifecycle operations.

    Provides methods for recalling, editing, and replying to messages
    via Lark IM API.

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> manager = MessageLifecycleManager(credential_pool)
        >>> manager.recall_message(
        ...     app_id="cli_xxx",
        ...     message_id="om_xxx"
        ... )
        >>> manager.edit_message(
        ...     app_id="cli_xxx",
        ...     message_id="om_xxx",
        ...     content="Updated text"
        ... )
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize MessageLifecycleManager.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def recall_message(
        self,
        app_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        """
        Recall (delete) a message.

        Only messages sent by the current app can be recalled.
        There may be time limits on how long after sending a message can be recalled.

        Parameters
        ----------
            app_id : str
                Lark application ID
            message_id : str
                Message ID to recall (e.g., "om_xxx")

        Returns
        -------
            dict[str, Any]
                Response containing success status

        Raises
        ------
            InvalidParameterError
                If message_id is empty
            RetryableError
                If recall fails after retries

        Examples
        --------
            >>> result = manager.recall_message(
            ...     app_id="cli_xxx",
            ...     message_id="om_abc123"
            ... )
            >>> print(result["success"])
        """
        if not message_id or not message_id.strip():
            raise InvalidParameterError(
                "Message ID cannot be empty",
                details={"message_id": message_id},
            )

        # Get SDK client
        client = self.credential_pool._get_sdk_client(app_id)

        # Create request
        request = DeleteMessageRequest.builder().message_id(message_id).build()

        # Execute with retry
        try:
            response = self.retry_strategy.execute(
                lambda: client.im.v1.message.delete(request),
                operation_name="recall_message",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to recall message: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "message_id": message_id,
                    },
                )

            logger.info(
                f"Message recalled successfully: {message_id}",
                extra={
                    "app_id": app_id,
                    "message_id": message_id,
                },
            )

            return {
                "success": True,
                "message_id": message_id,
            }

        except Exception as e:
            logger.error(
                f"Failed to recall message: {e}",
                extra={"app_id": app_id, "message_id": message_id},
                exc_info=True,
            )
            raise

    def edit_message(
        self,
        app_id: str,
        message_id: str,
        content: str,
    ) -> dict[str, Any]:
        """
        Edit a text message.

        Only text messages can be edited. The message must have been sent
        by the current app.

        Parameters
        ----------
            app_id : str
                Lark application ID
            message_id : str
                Message ID to edit (e.g., "om_xxx")
            content : str
                New text content

        Returns
        -------
            dict[str, Any]
                Response containing success status

        Raises
        ------
            InvalidParameterError
                If message_id or content is empty
            RetryableError
                If edit fails after retries

        Examples
        --------
            >>> result = manager.edit_message(
            ...     app_id="cli_xxx",
            ...     message_id="om_abc123",
            ...     content="This is the updated text"
            ... )
            >>> print(result["success"])
        """
        if not message_id or not message_id.strip():
            raise InvalidParameterError(
                "Message ID cannot be empty",
                details={"message_id": message_id},
            )

        if not content or not content.strip():
            raise InvalidParameterError(
                "Message content cannot be empty",
                details={"content": content},
            )

        # Get SDK client
        client = self.credential_pool._get_sdk_client(app_id)

        # Prepare content
        import json

        content_dict = {"text": content}
        content_str = json.dumps(content_dict)

        # Create request
        request = (
            PatchMessageRequest.builder()
            .message_id(message_id)
            .request_body(PatchMessageRequestBody.builder().content(content_str).build())
            .build()
        )

        # Execute with retry
        try:
            response = self.retry_strategy.execute(
                lambda: client.im.v1.message.patch(request),
                operation_name="edit_message",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to edit message: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "message_id": message_id,
                    },
                )

            logger.info(
                f"Message edited successfully: {message_id}",
                extra={
                    "app_id": app_id,
                    "message_id": message_id,
                },
            )

            return {
                "success": True,
                "message_id": message_id,
            }

        except Exception as e:
            logger.error(
                f"Failed to edit message: {e}",
                extra={"app_id": app_id, "message_id": message_id},
                exc_info=True,
            )
            raise

    def reply_message(
        self,
        app_id: str,
        message_id: str,
        msg_type: str,
        content: str | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Reply to a message.

        Sends a new message as a reply to an existing message.

        Parameters
        ----------
            app_id : str
                Lark application ID
            message_id : str
                Message ID to reply to (e.g., "om_xxx")
            msg_type : str
                Reply message type (text, post, image, file, interactive)
            content : str | dict[str, Any]
                Reply message content

        Returns
        -------
            dict[str, Any]
                Response containing reply message_id and metadata

        Raises
        ------
            InvalidParameterError
                If message_id is empty
            RetryableError
                If reply fails after retries

        Examples
        --------
            >>> # Reply with text
            >>> result = manager.reply_message(
            ...     app_id="cli_xxx",
            ...     message_id="om_abc123",
            ...     msg_type="text",
            ...     content={"text": "Thanks for your message!"}
            ... )
            >>> print(result["reply_message_id"])
        """
        if not message_id or not message_id.strip():
            raise InvalidParameterError(
                "Message ID cannot be empty",
                details={"message_id": message_id},
            )

        # Get SDK client
        client = self.credential_pool._get_sdk_client(app_id)

        # Prepare content string
        if isinstance(content, dict):
            import json

            content_str = json.dumps(content)
        else:
            content_str = content

        # Create request
        request = (
            ReplyMessageRequest.builder()
            .message_id(message_id)
            .request_body(
                ReplyMessageRequestBody.builder().msg_type(msg_type).content(content_str).build()
            )
            .build()
        )

        # Execute with retry
        try:
            response = self.retry_strategy.execute(
                lambda: client.im.v1.message.reply(request),
                operation_name="reply_message",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to reply to message: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "message_id": message_id,
                    },
                )

            # Extract response data
            reply_message_id = response.data.message_id
            create_time = response.data.create_time

            logger.info(
                f"Reply sent successfully: {reply_message_id}",
                extra={
                    "app_id": app_id,
                    "original_message_id": message_id,
                    "reply_message_id": reply_message_id,
                    "msg_type": msg_type,
                },
            )

            return {
                "reply_message_id": reply_message_id,
                "create_time": create_time,
                "original_message_id": message_id,
                "msg_type": msg_type,
            }

        except Exception as e:
            logger.error(
                f"Failed to reply to message: {e}",
                extra={"app_id": app_id, "message_id": message_id},
                exc_info=True,
            )
            raise
