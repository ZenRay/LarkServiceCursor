"""
Token expiration monitoring and user experience optimization.

Note: This monitor is primarily for User Access Tokens (OAuth tokens) that require
user re-authorization when refresh_token expires. App Access Tokens can be automatically
refreshed using app_id + app_secret and don't need user intervention.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from prometheus_client import Counter, Gauge

from lark_service.messaging.client import MessagingClient

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token type enumeration."""

    APP_ACCESS_TOKEN = "app_access_token"  # 应用级 Token,可自动刷新  # nosec B105
    TENANT_ACCESS_TOKEN = "tenant_access_token"  # 租户级 Token,可自动刷新  # nosec B105
    USER_ACCESS_TOKEN = "user_access_token"  # 用户级 Token,需要 refresh_token  # nosec B105


# Prometheus metrics for token monitoring
TOKEN_EXPIRY_WARNING_COUNTER = Counter(
    "token_expiry_warnings_sent_total",
    "Total number of token expiry warnings sent",
    ["app_id", "token_type"],
)

TOKEN_DAYS_TO_EXPIRY = Gauge(
    "token_days_to_expiry",
    "Days until token expiry",
    ["app_id", "token_type"],
)

REFRESH_TOKEN_DAYS_TO_EXPIRY = Gauge(
    "refresh_token_days_to_expiry",
    "Days until refresh token expiry",
    ["app_id"],
)


class TokenExpiryMonitor:
    """
    Monitor token expiration and provide proactive user notifications.

    This service:
    1. Checks token expiration dates
    2. Sends proactive notifications when tokens are about to expire
    3. Provides clear instructions for token renewal
    """

    def __init__(
        self,
        messaging_client: MessagingClient,
        warning_days: int = 7,
        critical_days: int = 3,
    ):
        """
        Initialize the token expiry monitor.

        Args:
            messaging_client: Client for sending notifications
            warning_days: Days before expiry to send first warning (default: 7)
            critical_days: Days before expiry to send critical warning (default: 3)
        """
        self.messaging_client = messaging_client
        self.warning_days = warning_days
        self.critical_days = critical_days
        self._notification_history: dict[str, datetime] = {}
        logger.info(
            f"TokenExpiryMonitor initialized (warning: {warning_days}d, critical: {critical_days}d)"
        )

    def check_token_expiry(
        self,
        app_id: str,
        token_expires_at: datetime,
        token_type: TokenType = TokenType.APP_ACCESS_TOKEN,
        refresh_token_expires_at: datetime | None = None,
        admin_user_id: str | None = None,
    ) -> None:
        """
        Check if a token is about to expire and send notifications.

        For App Access Tokens: No notification needed as they auto-refresh.
        For User Access Tokens: Notify when refresh_token is about to expire.

        Args:
            app_id: Application ID
            token_expires_at: Token expiration timestamp
            token_type: Type of token (app or user)
            refresh_token_expires_at: Refresh token expiration (for user tokens)
            admin_user_id: Optional user ID to notify
        """
        now = datetime.utcnow()
        days_to_expiry = (token_expires_at - now).days

        # Update Prometheus metric
        TOKEN_DAYS_TO_EXPIRY.labels(app_id=app_id, token_type=token_type.value).set(days_to_expiry)

        # App Access Tokens and Tenant Access Tokens can auto-refresh, no need to notify
        if token_type in (TokenType.APP_ACCESS_TOKEN, TokenType.TENANT_ACCESS_TOKEN):
            logger.debug(
                f"{token_type.value} for {app_id} expires in {days_to_expiry} days "
                "(will auto-refresh)"
            )
            return

        # For User Access Tokens, check refresh_token expiry
        if token_type == TokenType.USER_ACCESS_TOKEN:
            if refresh_token_expires_at is None:
                logger.warning(f"User Access Token for {app_id} has no refresh_token expiry info")
                return

            refresh_days_to_expiry = (refresh_token_expires_at - now).days
            REFRESH_TOKEN_DAYS_TO_EXPIRY.labels(app_id=app_id).set(refresh_days_to_expiry)

            # Only notify if refresh_token is about to expire
            # (access_token can be refreshed as long as refresh_token is valid)
            days_to_expiry = refresh_days_to_expiry

        # Check if notification is needed
        notification_key = f"{app_id}:{token_expires_at.isoformat()}"
        last_notification = self._notification_history.get(notification_key)

        # Don't send notifications more than once per day
        if last_notification and (now - last_notification).days < 1:
            return

        # Determine notification level
        if days_to_expiry <= 0:
            self._send_expired_notification(app_id, admin_user_id)
        elif days_to_expiry <= self.critical_days:
            self._send_critical_warning(app_id, days_to_expiry, admin_user_id)
        elif days_to_expiry <= self.warning_days:
            self._send_warning(app_id, days_to_expiry, admin_user_id)
        else:
            return  # No notification needed

        # Record notification
        self._notification_history[notification_key] = now
        TOKEN_EXPIRY_WARNING_COUNTER.labels(app_id=app_id, token_type=token_type.value).inc()

    def _send_warning(
        self,
        app_id: str,
        days_to_expiry: int,
        admin_user_id: str | None = None,
    ) -> None:
        """
        Send a warning notification about upcoming token expiry.

        Args:
            app_id: Application ID
            days_to_expiry: Days until expiry
            admin_user_id: Optional user ID to notify
        """
        message = (
            f"⚠️ **Refresh Token Expiry Warning**\n\n"
            f"The refresh token for application `{app_id}` will expire in **{days_to_expiry} days**.\n\n"
            f"**What does this mean?**\n"
            f"After the refresh token expires, users will need to re-authorize the application.\n\n"
            f"**Action Required:**\n"
            f"1. Notify affected users to prepare for re-authorization\n"
            f"2. Ensure authorization flow is working correctly\n"
            f"3. Consider implementing automatic re-authorization reminders\n\n"
            f"**Note:** Access tokens will continue to auto-refresh until the refresh token expires.\n\n"
            f"Need help? Contact your system administrator."
        )

        try:
            if admin_user_id:
                self.messaging_client.send_text_message(
                    receiver_id=admin_user_id,
                    content=message,
                )
            logger.warning(
                f"Token expiry warning sent for {app_id}: {days_to_expiry} days remaining"
            )
        except Exception as e:
            logger.error(f"Failed to send token expiry warning: {e}")

    def _send_critical_warning(
        self,
        app_id: str,
        days_to_expiry: int,
        admin_user_id: str | None = None,
    ) -> None:
        """
        Send a critical warning notification about imminent token expiry.

        Args:
            app_id: Application ID
            days_to_expiry: Days until expiry
            admin_user_id: Optional user ID to notify
        """
        message = (
            f"🚨 **URGENT: Refresh Token Expiring Soon!**\n\n"
            f"The refresh token for application `{app_id}` will expire in **{days_to_expiry} days**!\n\n"
            f"**Critical Impact:**\n"
            f"Users will need to re-authorize the application after the refresh token expires.\n"
            f"Access tokens can no longer be automatically refreshed.\n\n"
            f"**Immediate Actions:**\n"
            f"1. **Notify all users** to re-authorize before expiry\n"
            f"2. **Test authorization flow**:\n"
            f"   - Visit: https://open.feishu.cn/app/{app_id}\n"
            f"   - Verify OAuth redirect URLs are correct\n"
            f"   - Test the complete authorization process\n"
            f"3. **Prepare user communications**:\n"
            f"   - Send email/message to affected users\n"
            f"   - Provide clear re-authorization instructions\n"
            f"4. **Monitor re-authorization rate**\n\n"
            f"**Note:** This is about refresh_token, not app_secret. "
            f"No need to regenerate app credentials.\n\n"
            f"Contact your system administrator immediately if you need assistance."
        )

        try:
            if admin_user_id:
                self.messaging_client.send_text_message(
                    receiver_id=admin_user_id,
                    content=message,
                )
            logger.error(
                f"Critical token expiry warning sent for {app_id}: {days_to_expiry} days remaining"
            )
        except Exception as e:
            logger.error(f"Failed to send critical token expiry warning: {e}")

    def _send_expired_notification(
        self,
        app_id: str,
        admin_user_id: str | None = None,
    ) -> None:
        """
        Send notification that a token has expired.

        Args:
            app_id: Application ID
            admin_user_id: Optional user ID to notify
        """
        message = (
            f"❌ **Refresh Token Expired**\n\n"
            f"The refresh token for application `{app_id}` has **EXPIRED**.\n\n"
            f"**Service Impact:**\n"
            f"- Users can no longer automatically refresh their access tokens\n"
            f"- **User re-authorization is now required**\n"
            f"- Existing access tokens will work until they expire (typically 2 hours)\n\n"
            f"**Required Actions:**\n"
            f"1. **Enable authorization flow** in your application\n"
            f"2. **Redirect users to re-authorize**:\n"
            f"   - Authorization URL: https://open.feishu.cn/open-apis/authen/v1/authorize\n"
            f"   - Include required parameters: app_id, redirect_uri, state\n"
            f"3. **Handle OAuth callback** to obtain new tokens\n"
            f"4. **Notify affected users** about re-authorization requirement\n\n"
            f"**Important:** This is NOT an app_secret issue. "
            f"Users need to go through OAuth authorization again.\n\n"
            f"**Need Help?**\n"
            f"Contact: your-support-email@example.com"
        )

        try:
            if admin_user_id:
                self.messaging_client.send_text_message(
                    receiver_id=admin_user_id,
                    content=message,
                )
            logger.critical(f"Token expired notification sent for {app_id}")
        except Exception as e:
            logger.error(f"Failed to send token expired notification: {e}")

    def get_expiry_status(self, token_expires_at: datetime) -> dict[str, Any]:
        """
        Get the expiry status of a token.

        Args:
            token_expires_at: Token expiration timestamp

        Returns:
            Dictionary with status information
        """
        now = datetime.utcnow()
        days_to_expiry = (token_expires_at - now).days
        hours_to_expiry = (token_expires_at - now).total_seconds() / 3600

        if days_to_expiry < 0:
            status = "expired"
            severity = "critical"
        elif days_to_expiry <= self.critical_days:
            status = "expiring_soon"
            severity = "critical"
        elif days_to_expiry <= self.warning_days:
            status = "expiring"
            severity = "warning"
        else:
            status = "valid"
            severity = "ok"

        return {
            "status": status,
            "severity": severity,
            "days_to_expiry": days_to_expiry,
            "hours_to_expiry": hours_to_expiry,
            "expires_at": token_expires_at.isoformat(),
        }
