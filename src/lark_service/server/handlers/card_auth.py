"""Handler for card authorization callbacks.

This module provides a callback handler that integrates with CardAuthHandler
to process user authorization events from interactive cards.
"""

from typing import Any

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.utils.logger import get_logger

logger = get_logger()


def create_card_auth_handler(card_auth_handler: CardAuthHandler) -> Any:
    """Create a callback handler for card authorization events.

    This factory function creates an async handler that processes card
    action trigger callbacks related to user authorization.

    Parameters
    ----------
        card_auth_handler: CardAuthHandler instance for processing authorization

    Returns
    -------
        Async handler function for card authorization callbacks

    Example
    ----------
        >>> handler = CardAuthHandler(...)
        >>> callback_handler = create_card_auth_handler(handler)
        >>> server.register_handler("card_action_trigger", callback_handler)
    """

    async def handle_card_action_trigger(callback_data: dict[str, Any]) -> dict[str, Any]:
        """Handle card action trigger callbacks.

        Extracts relevant data from the callback and routes to CardAuthHandler.

        Parameters
        ----------
            callback_data: Callback data from Feishu

        Returns
        -------
            dict: Response to update card or show toast

        Example callback_data format:
        ----------
            {
                "type": "card_action_trigger",
                "open_id": "ou_xxx",
                "user_id": "7xxx",
                "action": {
                    "value": {
                        "session_id": "uuid",
                        "action": "authorize"
                    }
                }
            }
        """
        try:
            # Extract event data
            open_id = callback_data.get("open_id", "")
            user_id = callback_data.get("user_id", "")
            action = callback_data.get("action", {})
            action_value = action.get("value", {})

            logger.info(
                "Processing card action trigger",
                extra={
                    "open_id": open_id,
                    "action": action_value.get("action"),
                    "session_id": action_value.get("session_id"),
                },
            )

            # Transform to CardAuthHandler expected format
            event_data = {
                "operator": {
                    "open_id": open_id,
                    "user_id": user_id,
                },
                "action": {
                    "value": action_value,
                },
            }

            # Call CardAuthHandler
            response = await card_auth_handler.handle_card_auth_event(event_data)

            logger.info(
                "Card action handled successfully",
                extra={"session_id": action_value.get("session_id")},
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to handle card action: {e}",
                exc_info=True,
                extra={"callback_data": callback_data},
            )
            return {
                "toast": {
                    "type": "error",
                    "content": f"处理失败: {str(e)}",
                }
            }

    return handle_card_action_trigger
