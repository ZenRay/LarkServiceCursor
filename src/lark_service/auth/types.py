"""Type definitions for user authentication module.

This module defines dataclasses and type aliases for authentication operations.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuthCardOptions:
    """Options for customizing authorization card appearance.

    Controls the content and layout of the interactive card
    sent to users for authorization.

    Attributes
    ----------
        include_detailed_description: Show detailed explanation of permissions
        auth_card_template_id: Custom card template ID from Feishu platform
        custom_message: Additional message to display to user
        privacy_policy_url: Link to privacy policy (optional)

    Example
    ----------
        >>> options = AuthCardOptions(
        ...     include_detailed_description=True,
        ...     custom_message="Please authorize to unlock AI features"
        ... )
    """

    include_detailed_description: bool = True
    auth_card_template_id: str | None = None
    custom_message: str | None = None
    privacy_policy_url: str | None = None


@dataclass
class UserInfo:
    """User information from Feishu platform.

    Contains basic user profile data fetched during
    the authorization process.

    Attributes
    ----------
        user_id: Feishu user ID (encrypted)
        open_id: Feishu open ID for the current app
        union_id: Feishu union ID across all apps in the same org
        user_name: User's display name
        mobile: User's mobile number (optional, encrypted)
        email: User's email address (optional)

    Example
    ----------
        >>> user_info = UserInfo(
        ...     user_id="ou_xxx",
        ...     open_id="on_xxx",
        ...     union_id="un_xxx",
        ...     user_name="张三",
        ...     email="zhangsan@example.com"
        ... )
    """

    user_id: str
    open_id: str
    union_id: str | None
    user_name: str
    mobile: str | None = None
    email: str | None = None


@dataclass
class AuthSession:
    """Authorization session data.

    Represents an active or completed authorization session.

    Attributes
    ----------
        session_id: Unique session identifier
        app_id: Feishu app ID
        user_id: User ID (available after authorization)
        open_id: User open ID (available after authorization)
        union_id: User union ID (optional)
        user_name: User display name (optional)
        mobile: User mobile number (optional, encrypted)
        email: User email address (optional)
        auth_method: Authorization method (websocket_card/link/card)
        state: Session state (pending/completed/expired)
        user_access_token: User access token (encrypted, optional)
        token_expires_at: Token expiration timestamp (optional)
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
        completed_at: Session completion timestamp (optional)

    Example
    ----------
        >>> session = AuthSession(
        ...     session_id="sess_123",
        ...     app_id="cli_xxx",
        ...     auth_method="websocket_card",
        ...     state="pending",
        ...     created_at=datetime.now(),
        ...     expires_at=datetime.now() + timedelta(minutes=10)
        ... )
    """

    session_id: str
    app_id: str
    auth_method: str
    state: str
    created_at: datetime
    expires_at: datetime
    user_id: str | None = None
    open_id: str | None = None
    union_id: str | None = None
    user_name: str | None = None
    mobile: str | None = None
    email: str | None = None
    user_access_token: str | None = None
    token_expires_at: datetime | None = None
    completed_at: datetime | None = None
