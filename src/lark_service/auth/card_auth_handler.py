"""Card-based authentication handler.

This module provides the CardAuthHandler class for managing card-based
user authorization flow, including sending authorization cards and handling
callback events.
"""

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp

from lark_service.auth.exceptions import (
    AuthorizationCodeExpiredError,
    TokenRefreshFailedError,
)
from lark_service.auth.session_manager import AuthSessionManager
from lark_service.auth.types import AuthCardOptions, UserInfo
from lark_service.monitoring import auth_failure_total
from lark_service.utils.logger import get_logger

logger = get_logger()


class CardAuthHandler:
    """Handler for card-based user authorization.

    Manages the complete authorization flow including:
    - Sending authorization cards to users
    - Handling card callback events
    - Exchanging authorization codes for tokens
    - Fetching user information

    Attributes
    ----------
        session_manager: AuthSessionManager for session lifecycle
        messaging_client: MessagingClient for sending cards
        app_id: Feishu application ID
        app_secret: Feishu application secret

    Example
    ----------
        >>> handler = CardAuthHandler(
        ...     session_manager=session_manager,
        ...     messaging_client=messaging_client,
        ...     app_id="cli_xxx",
        ...     app_secret="secret_xxx"
        ... )
        >>> # Send authorization card
        >>> message_id = await handler.send_auth_card(
        ...     user_id="ou_xxx",
        ...     options=AuthCardOptions(include_detailed_description=True)
        ... )
        >>> # Handle callback event
        >>> response = await handler.handle_card_auth_event(event)
    """

    def __init__(
        self,
        session_manager: AuthSessionManager,
        messaging_client: Any,
        app_id: str,
        app_secret: str | None = None,
    ) -> None:
        """Initialize CardAuthHandler.

        Parameters
        ----------
            session_manager: AuthSessionManager instance
            messaging_client: MessagingClient instance
            app_id: Feishu application ID
            app_secret: Feishu application secret (optional, for token exchange)
        """
        self.session_manager = session_manager
        self.messaging_client = messaging_client
        self.app_id = app_id
        self.app_secret = app_secret

    async def send_auth_card(
        self,
        user_id: str,
        options: AuthCardOptions | None = None,
    ) -> str:
        """Send authorization card to user.

        Creates a new authorization session and sends an interactive card
        to the user requesting authorization.

        Parameters
        ----------
            user_id: Feishu user ID (open_id)
            options: Card customization options

        Returns
        ----------
            str: Message ID of sent card

        Example
        ----------
            >>> message_id = await handler.send_auth_card(
            ...     user_id="ou_test_user_123",
            ...     options=AuthCardOptions(include_detailed_description=True)
            ... )
        """
        options = options or AuthCardOptions()

        # Create new authorization session
        session = self.session_manager.create_session(
            app_id=self.app_id,
            user_id=user_id,
            auth_method="websocket_card",
        )

        logger.info(
            f"Created auth session for user {user_id}",
            extra={
                "session_id": session.session_id,
                "user_id": user_id,
                "app_id": self.app_id,
            },
        )

        # Build authorization card
        card_content = self._build_auth_card(session.session_id, options)

        # Send card to user
        response = self.messaging_client.send_card_message(
            app_id=self.app_id,
            receiver_id=user_id,
            card_content=card_content,
            receive_id_type="open_id",
        )

        message_id: str = response["message_id"]

        # Update session with message_id for later card updates
        self.session_manager.update_session_message_id(session.session_id, message_id)

        logger.info(
            f"Sent auth card to user {user_id}",
            extra={
                "message_id": message_id,
                "session_id": session.session_id,
                "user_id": user_id,
            },
        )

        return message_id

    def _build_auth_card(
        self,
        session_id: str,
        options: AuthCardOptions,
    ) -> dict[str, Any]:
        """Build authorization card content.

        Parameters
        ----------
            session_id: Authorization session ID
            options: Card customization options

        Returns
        ----------
            dict: Card JSON structure
        """
        # Build card elements
        elements = []

        # Add description
        if options.include_detailed_description:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**授权说明**\n\n"
                        "为了使用高级功能(如 AI 助手、工作流触发等),需要获取您的用户授权。\n\n"
                        "授权后,系统将能够:\n"
                        "- 代表您调用飞书 API\n"
                        "- 访问您的基本信息(姓名、邮箱)\n"
                        "- 使用 AI 能力处理您的请求",
                    },
                }
            )
        else:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "点击下方按钮完成授权,解锁高级功能。",
                    },
                }
            )

        # Add custom message if provided
        if options.custom_message:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": options.custom_message,
                    },
                }
            )

        # Add authorization button
        # HTTP 回调 + OAuth 授权流程：
        #
        # 流程说明：
        # 1. 用户点击"授权"按钮 → 跳转到飞书 OAuth 授权页面
        # 2. 用户在授权页面点击"同意"
        # 3. 飞书通过 HTTP POST 发送回调到我们的服务器
        # 4. 回调中包含 authorization_code
        # 5. 服务端用 code 换取 user_access_token
        #
        # 重要配置：
        # - 必须在飞书开放平台配置 HTTP 回调地址
        # - 必须配置 redirect_uri: https://open.feishu.cn/
        # - 卡片交互事件通过 HTTP 回调，不是 WebSocket
        action_element: dict[str, Any] = {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "授权"},
                    "type": "primary",
                    "value": {
                        "session_id": session_id,
                        "action": "authorize",
                    },
                    "url": f"https://open.feishu.cn/open-apis/authen/v1/authorize?"
                    f"app_id={self.app_id}&"
                    f"redirect_uri=http://localhost:8000/callback&"
                    f"state={session_id}",
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "取消"},
                    "type": "default",
                    "value": {
                        "session_id": session_id,
                        "action": "reject",
                    },
                },
            ],
        }
        elements.append(action_element)

        # Add privacy policy link if provided
        if options.privacy_policy_url:
            note_element: dict[str, Any] = {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"查看隐私政策: {options.privacy_policy_url}",
                    }
                ],
            }
            elements.append(note_element)

        # Build complete card
        card = {
            "header": {
                "title": {"tag": "plain_text", "content": "用户授权请求"},
                "template": "blue",
            },
            "elements": elements,
        }

        return card

    async def handle_card_auth_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Handle card authorization callback event.

        Processes the callback event when user clicks authorization button,
        exchanges authorization code for token, and completes the session.

        Parameters
        ----------
            event: Card callback event data

        Returns
        ----------
            dict: Response to update card or show toast

        Example
        ----------
            >>> event = {
            ...     "operator": {"open_id": "ou_xxx"},
            ...     "action": {
            ...         "value": {
            ...             "session_id": "sess_123",
            ...             "authorization_code": "auth_code_xyz"
            ...         }
            ...     }
            ... }
            >>> response = await handler.handle_card_auth_event(event)
        """
        start_time = time.time()
        session_id = None

        try:
            # Extract event data
            operator = event.get("operator", {})
            open_id = operator.get("open_id")
            action_value = event.get("action", {}).get("value", {})
            session_id = action_value.get("session_id")
            action = action_value.get("action")

            # Handle rejection
            if action == "reject":
                logger.info(
                    f"User {open_id} rejected authorization",
                    extra={"session_id": session_id, "user_id": open_id},
                )
                auth_failure_total.labels(
                    app_id=self.app_id, auth_method="websocket_card", reason="user_rejected"
                ).inc()
                return {
                    "toast": {
                        "type": "info",
                        "content": "已取消授权",
                    }
                }

            # 检查是否有 authorization_code (OAuth 模式)
            authorization_code = action_value.get("authorization_code")

            if authorization_code:
                # OAuth 模式：使用 authorization_code 交换 token
                logger.info(
                    "Using OAuth mode: exchanging authorization code for token",
                    extra={"session_id": session_id, "user_id": open_id},
                )
                token_data = await self._exchange_token(authorization_code)
            else:
                # Callback 模式：用户点击授权按钮，我们需要触发授权流程
                # 由于无法通过 callback 直接获取 user_access_token，
                # 我们返回一个包含 OAuth 授权链接的响应，引导用户完成授权
                logger.info(
                    "Using callback mode: sending authorization URL to user",
                    extra={"session_id": session_id, "user_id": open_id},
                )

                # 构建授权 URL（需要在飞书开放平台配置 redirect_uri）
                auth_url = (
                    f"https://open.feishu.cn/open-apis/authen/v1/authorize?"
                    f"app_id={self.app_id}&"
                    f"redirect_uri=http://localhost:8000/callback&"
                    f"state={session_id}"
                )

                return {
                    "toast": {
                        "type": "info",
                        "content": "请点击链接完成授权",
                    },
                    "card": {
                        "header": {
                            "title": {"tag": "plain_text", "content": "完成授权"},
                            "template": "blue",
                        },
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"请点击下方链接完成授权:\n\n[点击授权]({auth_url})",
                                },
                            }
                        ],
                    },
                }

            # Continue with OAuth flow if we have the code

            # Fetch user information
            user_access_token = token_data["access_token"]
            expires_in = token_data["expires_in"]

            logger.info(
                "Fetching user information",
                extra={"session_id": session_id, "user_id": open_id},
            )
            user_info = await self._fetch_user_info(user_access_token)

            # Complete authorization session
            token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
                seconds=expires_in
            )

            self.session_manager.complete_session(
                session_id=session_id,
                user_access_token=user_access_token,
                token_expires_at=token_expires_at,
                user_info=user_info,
                start_time=start_time,
            )

            logger.info(
                "Authorization completed successfully",
                extra={
                    "session_id": session_id,
                    "user_id": open_id,
                    "user_name": user_info.user_name,
                },
            )

            # TODO: Update the original message card to show success
            # This requires implementing update_message in MessagingClient
            # For now, we skip this step to avoid blocking the authorization flow

            # Return success response (for card interaction flow)
            return {
                "toast": {
                    "type": "success",
                    "content": "授权成功!",
                },
                "card": self._build_success_card(user_info),
            }

        except AuthorizationCodeExpiredError as e:
            logger.warning(
                "Authorization code expired",
                extra={"session_id": session_id, "error": str(e)},
            )
            auth_failure_total.labels(
                app_id=self.app_id, auth_method="websocket_card", reason="code_expired"
            ).inc()
            return {
                "toast": {
                    "type": "error",
                    "content": "授权码已过期,请重新授权",
                }
            }

        except Exception as e:
            logger.error(
                "Authorization failed",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            auth_failure_total.labels(
                app_id=self.app_id, auth_method="websocket_card", reason="unknown_error"
            ).inc()
            return {
                "toast": {
                    "type": "error",
                    "content": "授权失败,请重试",
                }
            }

    def _build_success_card(self, user_info: UserInfo) -> dict[str, Any]:
        """Build success card after authorization.

        Parameters
        ----------
            user_info: User information

        Returns
        ----------
            dict: Success card JSON structure
        """
        return {
            "header": {
                "title": {"tag": "plain_text", "content": "授权成功"},
                "template": "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{user_info.user_name}**,您已成功完成授权!\n\n"
                        "现在可以使用高级功能了。",
                    },
                }
            ],
        }

    async def _exchange_token(self, authorization_code: str) -> dict[str, Any]:
        """Exchange authorization code for user access token.

        Calls Feishu OIDC token endpoint to exchange temporary authorization
        code for user access token.

        Parameters
        ----------
            authorization_code: Temporary authorization code from callback

        Returns
        ----------
            dict: Token data including access_token and expires_in

        Raises
        ----------
            AuthorizationCodeExpiredError: If authorization code expired
            TokenRefreshFailedError: If token exchange fails
        """
        url = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"

        # First, get app_access_token for authentication
        app_token_url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"  # nosec B105
        app_token_payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        async with (
            aiohttp.ClientSession() as token_session,
            token_session.post(
                app_token_url, json=app_token_payload, headers={"Content-Type": "application/json"}
            ) as token_response,
        ):
            token_data = await token_response.json()
            if token_data.get("code") != 0:
                raise TokenRefreshFailedError(
                    f"Failed to get app_access_token: {token_data.get('msg')}"
                )
            app_access_token = token_data["app_access_token"]

        # Now exchange authorization code for user access token
        payload = {
            "grant_type": "authorization_code",
            "code": authorization_code,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_access_token}",
        }

        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=payload, headers=headers) as response,
        ):
            data = await response.json()

            if data.get("code") == 0:
                return data["data"]  # type: ignore[no-any-return]
            elif data.get("code") == 10014:  # Authorization code expired
                raise AuthorizationCodeExpiredError(
                    f"Authorization code expired: {data.get('msg')}"
                )
            else:
                raise TokenRefreshFailedError(f"Token exchange failed: {data.get('msg')}")

    async def _fetch_user_info(self, user_access_token: str) -> UserInfo:
        """Fetch user information using user access token.

        Calls Feishu user info endpoint to get user profile data.

        Parameters
        ----------
            user_access_token: User access token

        Returns
        ----------
            UserInfo: User profile information

        Raises
        ----------
            TokenRefreshFailedError: If user info fetch fails
        """
        url = "https://open.feishu.cn/open-apis/authen/v1/user_info"

        headers = {
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json",
        }

        async with (
            aiohttp.ClientSession() as session,
            session.get(url, headers=headers) as response,
        ):
            if response.status != 200:
                raise TokenRefreshFailedError(f"Failed to fetch user info: HTTP {response.status}")

            data = await response.json()

            if data.get("code") != 0:
                raise TokenRefreshFailedError(f"Failed to fetch user info: {data.get('msg')}")

            # The data structure might be data["data"] directly without nested "user"
            user_data = data.get("data", {})

            # Handle both formats: data["data"]["user"] and data["data"]
            if "user" in user_data:
                user_data = user_data["user"]

            return UserInfo(
                user_id=user_data.get("user_id"),
                open_id=user_data.get("open_id"),
                union_id=user_data.get("union_id"),
                user_name=user_data.get("name"),
                mobile=user_data.get("mobile"),
                email=user_data.get("email"),
            )
