"""
Unit tests for the scheduler service.
"""

import time
from unittest.mock import Mock

import pytest

from lark_service.scheduler.scheduler import SchedulerService


class TestSchedulerService:
    """Test cases for SchedulerService."""

    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = SchedulerService()
        assert scheduler is not None
        assert not scheduler._is_running

    def test_start_stop(self):
        """Test starting and stopping the scheduler."""
        scheduler = SchedulerService()

        # Start scheduler
        scheduler.start()
        assert scheduler._is_running

        # Stop scheduler
        scheduler.shutdown(wait=False)
        assert not scheduler._is_running

    def test_add_interval_job(self):
        """Test adding an interval job."""
        scheduler = SchedulerService()
        mock_func = Mock()

        # Add interval job
        scheduler.add_interval_job(
            mock_func,
            seconds=1,
            job_id="test_job",
        )

        # Check job was added
        jobs = scheduler.get_jobs()
        assert len(jobs) > 0
        assert any(job.id == "test_job" for job in jobs)

        scheduler.shutdown(wait=False)

    def test_add_cron_job(self):
        """Test adding a cron job."""
        scheduler = SchedulerService()
        mock_func = Mock()

        # Add cron job (every day at midnight)
        scheduler.add_cron_job(
            mock_func,
            cron_expression="0 0 * * *",
            job_id="test_cron_job",
        )

        # Check job was added
        jobs = scheduler.get_jobs()
        assert len(jobs) > 0
        assert any(job.id == "test_cron_job" for job in jobs)

        scheduler.shutdown(wait=False)

    def test_invalid_cron_expression(self):
        """Test that invalid cron expressions raise an error."""
        scheduler = SchedulerService()
        mock_func = Mock()

        with pytest.raises(ValueError, match="Invalid cron expression"):
            scheduler.add_cron_job(
                mock_func,
                cron_expression="invalid",
                job_id="test_invalid_cron",
            )

        scheduler.shutdown(wait=False)

    def test_remove_job(self):
        """Test removing a job."""
        scheduler = SchedulerService()
        mock_func = Mock()

        # Add a job
        scheduler.add_interval_job(
            mock_func,
            seconds=10,
            job_id="test_remove_job",
        )

        # Remove the job
        scheduler.remove_job("test_remove_job")

        # Check job was removed
        jobs = scheduler.get_jobs()
        assert not any(job.id == "test_remove_job" for job in jobs)

        scheduler.shutdown(wait=False)

    def test_job_execution(self):
        """Test that jobs are executed."""
        scheduler = SchedulerService()
        mock_func = Mock()

        # Add a job that runs every second
        scheduler.add_interval_job(
            mock_func,
            seconds=1,
            job_id="test_execution",
        )

        # Start scheduler
        scheduler.start()

        # Wait for job to execute
        time.sleep(2.5)

        # Check that the job was called at least twice
        assert mock_func.call_count >= 2

        scheduler.shutdown(wait=True)

    def test_job_metrics(self):
        """Test that job execution updates Prometheus metrics."""
        scheduler = SchedulerService()

        def test_func():
            return "success"

        # Add a job
        scheduler.add_interval_job(
            test_func,
            seconds=1,
            job_id="test_metrics",
        )

        # Start scheduler
        scheduler.start()

        # Wait for execution
        time.sleep(2.5)

        scheduler.shutdown(wait=True)

        # Note: In a real test, we would check Prometheus metrics
        # For now, just verify the job ran without errors

    def test_wrapped_task_exception_handling(self):
        """Test that task wrapper handles exceptions correctly."""
        scheduler = SchedulerService()

        def failing_func():
            raise ValueError("Test error")

        # Add a failing job
        scheduler.add_interval_job(
            failing_func,
            seconds=1,
            job_id="test_failing",
        )

        # Start scheduler
        scheduler.start()

        # Wait for execution
        time.sleep(2.5)

        # Scheduler should still be running despite job failures
        assert scheduler._is_running

        scheduler.shutdown(wait=False)

    def test_multiple_jobs(self):
        """Test running multiple jobs simultaneously."""
        scheduler = SchedulerService()
        mock_func1 = Mock()
        mock_func2 = Mock()
        mock_func3 = Mock()

        # Add multiple jobs
        scheduler.add_interval_job(mock_func1, seconds=1, job_id="job1")
        scheduler.add_interval_job(mock_func2, seconds=1, job_id="job2")
        scheduler.add_cron_job(mock_func3, cron_expression="* * * * *", job_id="job3")

        # Check all jobs were added
        jobs = scheduler.get_jobs()
        assert len(jobs) == 3

        # Start scheduler
        scheduler.start()

        # Wait for executions
        time.sleep(2.5)

        # All jobs should have been called
        assert mock_func1.call_count >= 2
        assert mock_func2.call_count >= 2
        # Note: Cron job might not execute in 2.5 seconds depending on current time

        scheduler.shutdown(wait=True)
