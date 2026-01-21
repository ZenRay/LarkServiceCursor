"""
Token expiration monitoring and user experience optimization.
"""

import logging
from datetime import datetime
from typing import Any

from prometheus_client import Counter, Gauge

from lark_service.messaging.client import MessagingClient

logger = logging.getLogger(__name__)

# Prometheus metrics for token monitoring
TOKEN_EXPIRY_WARNING_COUNTER = Counter(
    "token_expiry_warnings_sent_total",
    "Total number of token expiry warnings sent",
    ["app_id"],
)

TOKEN_DAYS_TO_EXPIRY = Gauge(
    "token_days_to_expiry",
    "Days until token expiry",
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
        admin_user_id: str | None = None,
    ) -> None:
        """
        Check if a token is about to expire and send notifications.

        Args:
            app_id: Application ID
            token_expires_at: Token expiration timestamp
            admin_user_id: Optional user ID to notify
        """
        now = datetime.utcnow()
        days_to_expiry = (token_expires_at - now).days

        # Update Prometheus metric
        TOKEN_DAYS_TO_EXPIRY.labels(app_id=app_id).set(days_to_expiry)

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
        TOKEN_EXPIRY_WARNING_COUNTER.labels(app_id=app_id).inc()

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
            f"⚠️ **Token Expiry Warning**\n\n"
            f"Your access token for application `{app_id}` will expire in **{days_to_expiry} days**.\n\n"
            f"**Action Required:**\n"
            f"1. Go to Lark Open Platform\n"
            f"2. Navigate to your application settings\n"
            f"3. Regenerate your app credentials\n"
            f"4. Update the configuration in this service\n\n"
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
            f"🚨 **URGENT: Token Expiring Soon!**\n\n"
            f"Your access token for application `{app_id}` will expire in **{days_to_expiry} days**!\n\n"
            f"**Immediate Action Required:**\n"
            f"Service functionality will be disrupted if the token expires.\n\n"
            f"**Steps to Renew:**\n"
            f"1. Visit [Lark Open Platform](https://open.feishu.cn/app)\n"
            f"2. Select application `{app_id}`\n"
            f"3. Navigate to 'Credentials & Basic Info'\n"
            f"4. Regenerate App Secret\n"
            f"5. Update configuration:\n"
            f"   ```bash\n"
            f"   lark-service-cli app update {app_id} --app-secret <new_secret>\n"
            f"   ```\n\n"
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
            f"❌ **Token Expired**\n\n"
            f"The access token for application `{app_id}` has **EXPIRED**.\n\n"
            f"**Service Impact:**\n"
            f"All API calls using this token will fail until renewed.\n\n"
            f"**Required Actions:**\n"
            f"1. Visit [Lark Open Platform](https://open.feishu.cn/app)\n"
            f"2. Regenerate app credentials for `{app_id}`\n"
            f"3. Update configuration immediately:\n"
            f"   ```bash\n"
            f"   lark-service-cli app update {app_id} \\\n"
            f"     --app-id <app_id> \\\n"
            f"     --app-secret <new_secret>\n"
            f"   ```\n"
            f"4. Restart the service\n\n"
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
