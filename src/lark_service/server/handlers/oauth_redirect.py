"""Handler for OAuth redirect callbacks.

This module provides a callback handler that processes OAuth authorization
code redirects and exchanges them for user access tokens.
"""

from typing import Any

from lark_service.auth.card_auth_handler import CardAuthHandler
from lark_service.utils.logger import get_logger

logger = get_logger()


def create_oauth_redirect_handler(card_auth_handler: CardAuthHandler) -> Any:
    """Create a callback handler for OAuth redirect.

    This factory function creates an async handler that processes OAuth
    authorization code redirects.

    Parameters
    ----------
        card_auth_handler: CardAuthHandler instance for processing authorization

    Returns
    -------
        Async handler function for OAuth redirect callbacks

    Example
    ----------
        >>> handler = CardAuthHandler(...)
        >>> oauth_handler = create_oauth_redirect_handler(handler)
        >>> server.register_handler("oauth_redirect", oauth_handler)
    """

    async def handle_oauth_redirect(callback_data: dict[str, Any]) -> dict[str, Any]:
        """Handle OAuth redirect callbacks.

        Extracts authorization code and state, then calls CardAuthHandler
        to complete the authorization flow.

        Parameters
        ----------
            callback_data: Callback data with authorization code and state

        Returns
        -------
            dict: Response indicating success or failure

        Example callback_data format:
        ----------
            {
                "type": "oauth_redirect",
                "authorization_code": "xxx",
                "state": "session_id_uuid",
                "session_id": "session_id_uuid"
            }
        """
        try:
            authorization_code = callback_data.get("authorization_code")
            session_id = callback_data.get("session_id") or callback_data.get("state")

            if not authorization_code or not session_id:
                logger.error(
                    "Missing required parameters in OAuth redirect",
                    extra={"has_code": bool(authorization_code), "has_session": bool(session_id)},
                )
                return {
                    "status": "error",
                    "message": "缺少必需参数",
                }

            logger.info(
                "Processing OAuth redirect",
                extra={
                    "session_id": session_id,
                    "has_code": bool(authorization_code),
                },
            )

            # Transform to CardAuthHandler expected format
            # We simulate a card action trigger with authorization_code
            event_data = {
                "operator": {
                    "open_id": "",  # Will be filled after token exchange
                },
                "action": {
                    "value": {
                        "session_id": session_id,
                        "action": "authorize",
                        "authorization_code": authorization_code,
                    },
                },
            }

            # Call CardAuthHandler
            await card_auth_handler.handle_card_auth_event(event_data)

            logger.info(
                "OAuth redirect handled successfully",
                extra={"session_id": session_id},
            )

            return {
                "status": "ok",
                "message": "授权成功",
            }

        except Exception as e:
            logger.error(
                f"Failed to handle OAuth redirect: {e}",
                exc_info=True,
                extra={"callback_data": callback_data},
            )
            return {
                "status": "error",
                "message": f"处理失败: {str(e)}",
            }

    return handle_oauth_redirect
