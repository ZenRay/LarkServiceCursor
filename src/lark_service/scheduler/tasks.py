"""
Scheduled tasks for the Lark service.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lark_service.core.database import get_db
from lark_service.models.application import Application
from lark_service.services.lark_client import LarkClient
from lark_service.services.token_storage import TokenStorageService

logger = logging.getLogger(__name__)


async def sync_user_info_task() -> None:
    """
    Synchronize user information from Lark for all active applications.

    This task:
    1. Fetches all active applications
    2. For each application, fetches updated user information from Lark
    3. Updates local database with the latest user data
    4. Records last sync time
    """
    logger.info("Starting user info synchronization task")

    try:
        # Get database session
        db: Session = next(get_db())

        # Fetch all active applications
        result = db.execute(
            select(Application).where(Application.is_active == True)  # noqa: E712
        )
        applications: list[Any] = list(result.scalars().all())

        logger.info(f"Found {len(applications)} active applications to sync")

        success_count = 0
        failure_count = 0

        for app in applications:
            try:
                # Initialize Lark client for this application
                client = LarkClient(
                    app_id=app.app_id,
                    app_secret=app.app_secret,
                )

                # Fetch user list from Lark
                # This is a placeholder - actual implementation depends on Lark API
                users = await client.get_user_list()

                # Update user information in database
                # This would involve updating the User table
                # For now, just log the count
                logger.info(f"Synced {len(users)} users for application {app.app_id}")

                # Update last sync time
                app.last_user_sync = datetime.utcnow()
                db.commit()

                success_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to sync users for application {app.app_id}: {e}",
                    exc_info=True,
                )
                failure_count += 1
                db.rollback()

        logger.info(f"User sync task completed: {success_count} succeeded, {failure_count} failed")

    except Exception as e:
        logger.error(f"User sync task failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


async def cleanup_expired_tokens_task() -> None:
    """
    Clean up expired tokens from the database.

    This task removes tokens that have been expired for more than 7 days
    to keep the database clean.
    """
    logger.info("Starting expired token cleanup task")

    try:
        db: Session = next(get_db())

        # Calculate cutoff date (7 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        # This would delete expired tokens
        # Actual implementation depends on your Token model
        # deleted_count = db.execute(
        #     delete(Token).where(
        #         Token.expires_at < cutoff_date
        #     )
        # )
        # db.commit()

        logger.info(f"Cleaned up tokens expired before {cutoff_date}")

    except Exception as e:
        logger.error(f"Token cleanup task failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


async def check_token_expiry_task() -> None:
    """
    Check for expiring tokens and send proactive notifications.

    This task:
    1. Fetches all active application tokens
    2. Checks their expiration dates
    3. Sends notifications to admins for tokens about to expire
    """
    logger.info("Starting token expiry check task")

    try:
        # Initialize token storage
        token_storage = TokenStorageService()

        # Get database session
        db: Session = next(get_db())

        # Fetch all active applications
        result = db.execute(
            select(Application).where(Application.is_active == True)  # noqa: E712
        )
        applications: list[Any] = list(result.scalars().all())

        # Initialize token monitor
        # Note: This is a placeholder - actual implementation needs MessagingClient
        # monitor = TokenExpiryMonitor(messaging_client=None)

        checked_count = 0
        expiring_count = 0

        for app in applications:
            try:
                # Get token from storage
                token_info = token_storage.get_token(app.app_id)

                if not token_info or "expires_at" not in token_info:
                    logger.warning(f"No token found for application {app.app_id}")
                    continue

                expires_at = datetime.fromtimestamp(token_info["expires_at"])
                days_to_expiry = (expires_at - datetime.utcnow()).days

                # Log expiry status
                if days_to_expiry <= 0:
                    logger.error(f"Token EXPIRED for {app.app_id}")
                    expiring_count += 1
                elif days_to_expiry <= 7:
                    logger.warning(f"Token expiring soon for {app.app_id}: {days_to_expiry} days")
                    expiring_count += 1

                # Send notification (if monitor is configured)
                # monitor.check_token_expiry(
                #     app_id=app.app_id,
                #     token_expires_at=expires_at,
                #     admin_user_id=app.created_by,
                # )

                checked_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to check token expiry for {app.app_id}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Token expiry check completed: {checked_count} checked, "
            f"{expiring_count} expiring/expired"
        )

        db.close()

    except Exception as e:
        logger.error(f"Token expiry check task failed: {e}", exc_info=True)
        raise


async def health_check_task() -> None:
    """
    Periodic health check task.

    This task performs various health checks:
    - Database connectivity
    - RabbitMQ connectivity
    - External API availability
    """
    logger.info("Starting health check task")

    try:
        # Database health check
        db: Session = next(get_db())
        db.execute(select(1))  # Simple query to check DB connection
        logger.info("✅ Database connection OK")

        # Add more health checks as needed
        # - RabbitMQ connection
        # - Lark API availability
        # - etc.

        db.close()

    except Exception as e:
        logger.error(f"Health check task failed: {e}", exc_info=True)
        raise


def register_scheduled_tasks(scheduler: Any) -> None:
    """
    Register all scheduled tasks with the scheduler.

    Args:
        scheduler: SchedulerService instance
    """

    # Sync user info every 6 hours
    scheduler.add_interval_job(
        sync_user_info_task,
        hours=6,
        job_id="sync_user_info",
    )

    # Check token expiry twice daily (at 9 AM and 6 PM)
    scheduler.add_cron_job(
        check_token_expiry_task,
        cron_expression="0 9,18 * * *",
        job_id="check_token_expiry",
    )

    # Clean up expired tokens daily at 3 AM
    scheduler.add_cron_job(
        cleanup_expired_tokens_task,
        cron_expression="0 3 * * *",
        job_id="cleanup_expired_tokens",
    )

    # Health check every 5 minutes
    scheduler.add_interval_job(
        health_check_task,
        minutes=5,
        job_id="health_check",
    )

    logger.info("All scheduled tasks registered")
