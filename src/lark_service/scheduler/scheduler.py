"""
Scheduler service using APScheduler.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics for scheduled tasks
SCHEDULED_TASK_COUNTER = Counter(
    "scheduled_task_executions_total",
    "Total number of scheduled task executions",
    ["task_name", "status"],
)

SCHEDULED_TASK_DURATION = Histogram(
    "scheduled_task_duration_seconds",
    "Duration of scheduled task executions",
    ["task_name"],
)


class SchedulerService:
    """
    Service for managing scheduled tasks using APScheduler.

    This service provides a centralized way to register and manage
    periodic tasks in the application.
    """

    def __init__(self) -> None:
        """Initialize the scheduler service."""
        self.scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,  # Combine multiple pending executions
                "max_instances": 1,  # Only one instance per job at a time
                "misfire_grace_time": 60,  # Allow 60s grace for missed jobs
            },
        )
        self._is_running = False
        logger.info("Scheduler service initialized")

    def start(self) -> None:
        """Start the scheduler."""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Scheduler service started")

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the scheduler.

        Args:
            wait: If True, wait for all jobs to complete before shutting down.
        """
        if self._is_running:
            self.scheduler.shutdown(wait=wait)
            self._is_running = False
            logger.info("Scheduler service stopped")

    def add_interval_job(
        self,
        func: Callable[..., Any],
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a job that runs at fixed intervals.

        Args:
            func: The function to execute
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            job_id: Unique identifier for the job
            **kwargs: Additional arguments passed to the scheduler
        """
        trigger = IntervalTrigger(
            seconds=seconds or 0,
            minutes=minutes or 0,
            hours=hours or 0,
        )

        wrapped_func = self._wrap_task(func, job_id or func.__name__)

        self.scheduler.add_job(
            wrapped_func,
            trigger=trigger,
            id=job_id,
            **kwargs,
        )
        logger.info(
            f"Added interval job: {job_id or func.__name__} "
            f"(every {hours or 0}h {minutes or 0}m {seconds or 0}s)"
        )

    def add_cron_job(
        self,
        func: Callable[..., Any],
        cron_expression: str,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a job with cron-style scheduling.

        Args:
            func: The function to execute
            cron_expression: Cron expression (e.g., "0 2 * * *" for 2 AM daily)
            job_id: Unique identifier for the job
            **kwargs: Additional arguments passed to the scheduler
        """
        # Parse cron expression: minute hour day month day_of_week
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression: {cron_expression}. "
                "Expected format: 'minute hour day month day_of_week'"
            )

        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone="Asia/Shanghai",
        )

        wrapped_func = self._wrap_task(func, job_id or func.__name__)

        self.scheduler.add_job(
            wrapped_func,
            trigger=trigger,
            id=job_id,
            **kwargs,
        )
        logger.info(f"Added cron job: {job_id or func.__name__} ({cron_expression})")

    def remove_job(self, job_id: str) -> None:
        """
        Remove a scheduled job.

        Args:
            job_id: The ID of the job to remove
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")

    def get_jobs(self) -> list[Any]:
        """Get all scheduled jobs."""
        return list(self.scheduler.get_jobs())

    def _wrap_task(self, func: Callable[..., Any], task_name: str) -> Callable[..., Any]:
        """
        Wrap a task function with logging and metrics.

        Args:
            func: The function to wrap
            task_name: Name of the task for logging/metrics

        Returns:
            Wrapped function
        """

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(f"Starting scheduled task: {task_name}")
            start_time = datetime.now()

            try:
                with SCHEDULED_TASK_DURATION.labels(task_name=task_name).time():
                    result = func(*args, **kwargs)

                SCHEDULED_TASK_COUNTER.labels(task_name=task_name, status="success").inc()

                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Completed scheduled task: {task_name} (duration: {duration:.2f}s)")
                return result

            except Exception as e:
                SCHEDULED_TASK_COUNTER.labels(task_name=task_name, status="failure").inc()
                logger.error(
                    f"Failed scheduled task: {task_name}: {e}",
                    exc_info=True,
                )
                raise

        return wrapper


# Global scheduler instance
scheduler_service = SchedulerService()
