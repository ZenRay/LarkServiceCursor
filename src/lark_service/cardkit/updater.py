"""
Card updater for Lark CardKit.

This module provides functionality for updating interactive card content,
both proactively and in response to callbacks.
"""

from typing import Any

from lark_oapi.api.im.v1 import PatchMessageRequest, PatchMessageRequestBody

from lark_service.cardkit.models import CardConfig
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.exceptions import InvalidParameterError, RetryableError
from lark_service.core.retry import RetryStrategy
from lark_service.utils.logger import get_logger

logger = get_logger()


class CardUpdater:
    """
    Updater for interactive card content.

    Provides methods for updating card content both proactively
    (via API) and reactively (via callback responses).

    Attributes
    ----------
        credential_pool : CredentialPool
            Credential pool for token management
        retry_strategy : RetryStrategy
            Retry strategy for API calls

    Examples
    --------
        >>> updater = CardUpdater(credential_pool)
        >>> updater.update_card_content(
        ...     app_id="cli_xxx",
        ...     message_id="om_xxx",
        ...     card_content={"header": {...}, "elements": [...]}
        ... )
    """

    def __init__(
        self,
        credential_pool: CredentialPool,
        retry_strategy: RetryStrategy | None = None,
    ) -> None:
        """
        Initialize CardUpdater.

        Parameters
        ----------
            credential_pool : CredentialPool
                Credential pool for token management
            retry_strategy : RetryStrategy | None
                Retry strategy (default: creates new instance)
        """
        self.credential_pool = credential_pool
        self.retry_strategy = retry_strategy or RetryStrategy()

    def update_card_content(
        self,
        app_id: str,
        message_id: str,
        card_content: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update card content proactively via API.

        Updates an existing card's content by calling Lark IM API.
        The card must have been sent by the current app.

        Parameters
        ----------
            app_id : str
                Lark application ID
            message_id : str
                Message ID of the card to update (e.g., "om_xxx")
            card_content : dict[str, Any]
                New card content (header, elements, etc.)

        Returns
        -------
            dict[str, Any]
                Response containing success status

        Raises
        ------
            InvalidParameterError
                If message_id or card_content is empty
            RetryableError
                If update fails after retries

        Examples
        --------
            >>> new_card = {
            ...     "header": {"title": {"tag": "plain_text", "content": "Updated"}},
            ...     "elements": [{"tag": "div", "text": {...}}]
            ... }
            >>> result = updater.update_card_content(
            ...     app_id="cli_xxx",
            ...     message_id="om_abc123",
            ...     card_content=new_card
            ... )
        """
        if not message_id or not message_id.strip():
            raise InvalidParameterError(
                "Message ID cannot be empty",
                details={"message_id": message_id},
            )

        if not card_content:
            raise InvalidParameterError(
                "Card content cannot be empty",
                details={"card_content": card_content},
            )

        # Validate card content using Pydantic model
        try:
            card_config = CardConfig(**card_content)
        except Exception as e:
            raise InvalidParameterError(
                f"Invalid card content: {e}",
                details={"card_content": card_content},
            ) from e

        # Get SDK client
        client = self.credential_pool._get_sdk_client(app_id)

        # Prepare content
        import json

        content_str = json.dumps(card_config.model_dump(exclude_none=True))

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
                lambda **kwargs: client.im.v1.message.patch(request),
                operation_name="update_card_content",
            )

            if not response.success():
                raise RetryableError(
                    f"Failed to update card: {response.msg}",
                    details={
                        "code": response.code,
                        "msg": response.msg,
                        "message_id": message_id,
                    },
                )

            logger.info(
                f"Card updated successfully: {message_id}",
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
                f"Failed to update card: {e}",
                extra={"app_id": app_id, "message_id": message_id},
                exc_info=True,
            )
            raise

    def build_update_response(
        self,
        card_content: dict[str, Any],
        toast_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a callback response to update card content.

        Used in callback handlers to update the card that triggered the callback.
        The response is returned to Lark servers, which will update the card.

        Parameters
        ----------
            card_content : dict[str, Any]
                New card content (header, elements, etc.)
            toast_message : str | None
                Optional toast message to show to user

        Returns
        -------
            dict[str, Any]
                Callback response with card update

        Raises
        ------
            InvalidParameterError
                If card_content is invalid

        Examples
        --------
            >>> # In a callback handler
            >>> def handle_approve(event: CallbackEvent) -> dict:
            ...     # Update card to show approval status
            ...     new_card = {
            ...         "header": {"title": {"tag": "plain_text", "content": "Approved"}},
            ...         "elements": [{"tag": "div", "text": {...}}]
            ...     }
            ...     return updater.build_update_response(
            ...         card_content=new_card,
            ...         toast_message="Approval successful!"
            ...     )
        """
        if not card_content:
            raise InvalidParameterError(
                "Card content cannot be empty",
                details={"card_content": card_content},
            )

        # Validate card content using Pydantic model
        try:
            card_config = CardConfig(**card_content)
        except Exception as e:
            raise InvalidParameterError(
                f"Invalid card content: {e}",
                details={"card_content": card_content},
            ) from e

        # Build response
        response: dict[str, Any] = {
            "card": card_config.model_dump(exclude_none=True),
        }

        if toast_message:
            response["toast"] = {
                "type": "success",
                "content": toast_message,
            }

        logger.debug(
            "Built card update response",
            extra={"has_toast": bool(toast_message)},
        )

        return response
