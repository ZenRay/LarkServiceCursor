"""HTTP callback server for handling Feishu callbacks.

This module provides an HTTP server for receiving and processing
Feishu callbacks, including card interactions, message events, and more.

The callback server is optional and can be enabled via environment variable:
    CALLBACK_SERVER_ENABLED=true

Example usage:
    >>> from lark_service.server import CallbackServerManager
    >>> manager = CallbackServerManager(
    ...     verification_token="v_xxx",
    ...     encrypt_key="encrypt_xxx"
    ... )
    >>> manager.register_card_auth_handler(card_auth_handler)
    >>> if manager.should_start():
    ...     manager.start()
"""

from .callback_router import CallbackRouter
from .callback_server import CallbackServer
from .manager import CallbackServerManager

__all__ = [
    "CallbackRouter",
    "CallbackServer",
    "CallbackServerManager",
]
