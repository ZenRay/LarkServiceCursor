"""Contact module for Lark Service.

This module provides contact management capabilities including:
- User lookup (by email, mobile, user_id)
- Department operations
- User and department search
- Contact cache with TTL
"""

from lark_service.contact.cache import ContactCacheManager
from lark_service.contact.client import ContactClient

__all__ = [
    "ContactClient",
    "ContactCacheManager",
]
