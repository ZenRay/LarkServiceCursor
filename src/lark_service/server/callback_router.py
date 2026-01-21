"""Callback router for handling different types of Feishu callbacks.

This module provides a flexible routing system for registering and dispatching
different callback handlers based on callback type.
"""

from collections.abc import Callable
from typing import Any

from lark_service.utils.logger import get_logger

logger = get_logger()


class CallbackRouter:
    """Router for dispatching Feishu callbacks to registered handlers.

    Provides a flexible system for registering callback handlers for different
    callback types (card interactions, message events, etc.) and routing
    incoming callbacks to the appropriate handler.

    Attributes
    ----------
        handlers: Dict mapping callback types to handler functions

    Example
    ----------
        >>> router = CallbackRouter()
        >>> router.register("card_action_trigger", handle_card_auth)
        >>> router.register("message_receive", handle_message)
        >>> response = await router.route({"type": "card_action_trigger", ...})
    """

    def __init__(self) -> None:
        """Initialize callback router."""
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(
        self,
        callback_type: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a callback handler for a specific callback type.

        Parameters
        ----------
            callback_type: Type of callback to handle (e.g., "card_action_trigger")
            handler: Async function to handle callbacks of this type

        Example
        ----------
            >>> async def handle_card(data: dict) -> dict:
            ...     return {"status": "ok"}
            >>> router.register("card_action_trigger", handle_card)
        """
        if callback_type in self.handlers:
            logger.warning(f"Overwriting existing handler for callback type: {callback_type}")

        self.handlers[callback_type] = handler
        logger.info(
            f"Registered callback handler for type: {callback_type}",
            extra={"callback_type": callback_type},
        )

    def unregister(self, callback_type: str) -> None:
        """Unregister a callback handler.

        Parameters
        ----------
            callback_type: Type of callback to unregister

        Example
        ----------
            >>> router.unregister("card_action_trigger")
        """
        if callback_type in self.handlers:
            del self.handlers[callback_type]
            logger.info(
                f"Unregistered callback handler for type: {callback_type}",
                extra={"callback_type": callback_type},
            )

    async def route(self, callback_data: dict[str, Any]) -> dict[str, Any]:
        """Route a callback to the appropriate handler.

        Extracts the callback type and dispatches to the registered handler.
        Returns an error response if no handler is registered for the type.

        Parameters
        ----------
            callback_data: Callback data from Feishu

        Returns
        -------
            dict: Response to send back to Feishu

        Example
        ----------
            >>> callback_data = {
            ...     "type": "card_action_trigger",
            ...     "action": {"value": {"session_id": "xxx"}},
            ... }
            >>> response = await router.route(callback_data)
        """
        callback_type = callback_data.get("type")

        if not callback_type:
            logger.error("Callback data missing 'type' field", extra={"data": callback_data})
            return {
                "error": "Missing callback type",
                "status": "error",
            }

        handler = self.handlers.get(callback_type)

        if not handler:
            logger.warning(
                f"No handler registered for callback type: {callback_type}",
                extra={
                    "callback_type": callback_type,
                    "available_handlers": list(self.handlers.keys()),
                },
            )
            return {
                "error": f"No handler for callback type: {callback_type}",
                "status": "error",
            }

        try:
            logger.info(
                f"Routing callback to handler: {callback_type}",
                extra={"callback_type": callback_type},
            )
            result: dict[str, Any] = await handler(callback_data)
            return result

        except Exception as e:
            logger.error(
                f"Handler failed for callback type: {callback_type}",
                exc_info=True,
                extra={"callback_type": callback_type, "error": str(e)},
            )
            return {
                "error": f"Handler error: {str(e)}",
                "status": "error",
            }

    def list_handlers(self) -> list[str]:
        """List all registered callback types.

        Returns
        -------
            list: List of registered callback types

        Example
        ----------
            >>> router.list_handlers()
            ['card_action_trigger', 'message_receive']
        """
        return list(self.handlers.keys())
