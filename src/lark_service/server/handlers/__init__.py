"""Callback handlers for different Feishu callback types.

This module provides handlers for various Feishu callbacks:
- Card action triggers (authorization, form submissions, etc.)
- OAuth redirect callbacks (authorization code exchange)
- Message events (future)
- Contact events (future)
"""

from .card_auth import create_card_auth_handler
from .oauth_redirect import create_oauth_redirect_handler

__all__ = [
    "create_card_auth_handler",
    "create_oauth_redirect_handler",
]
