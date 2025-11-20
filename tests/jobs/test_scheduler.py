"""
Tests for job scheduler
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.jobs.base import BaseJob, JobRegistry
from src.jobs.scheduler import Schedule, JobScheduler
from src.jobs.queue import QueueManager


class TestJob(BaseJob):
    """Test job"""

    def execute(self, **kwargs):
        return {"executed": True}


class TestSchedule:
    """Test Schedule class"""

    def test_schedule_creation(self):
        """Test schedule creation"""
        schedule = Schedule(
            job_name="test_job",
            job_params={"param": "value"},
            interval=timedelta(hours=1)
        )

        assert schedule.job_name == "test_job"
        assert schedule.job_params == {"param": "value"}
        assert schedule.interval == timedelta(hours=1)
        assert schedule.enabled is True

    def test_schedule_with_cron(self):
        """Test schedule with cron expression"""
        schedule = Schedule(
            job_name="test_job",
            job_params={},
            cron="0 * * * *"  # Hourly
        )

        assert schedule.cron == "0 * * * *"
        assert schedule.next_run is not None

    def test_schedule_with_interval(self):
        """Test schedule with interval"""
        schedule = Schedule(
            job_name="test_job",
            job_params={},
            interval=timedelta(minutes=30)
        )

        assert schedule.next_run is not None
        assert schedule.should_run() is True

    def test_schedule_with_time(self):
        """Test schedule with specific time"""
        schedule = Schedule(
            job_name="test_job",
            job_params={},
            at_time="15:00"
        )

        assert schedule.at_time == "15:00"
        assert schedule.next_run is not None

    def test_schedule_should_run(self):
        """Test schedule should_run check"""
        # Schedule that should run immediately
        schedule = Schedule(
            job_name="test_job",
            job_params={},
            interval=timedelta(seconds=1)
        )

        assert schedule.should_run() is True

    def test_schedule_mark_run(self):
        """Test marking schedule as run"""
        schedule = Schedule(
            job_name="test_job",
            job_params={},
            interval=timedelta(hours=1)
        )

        initial_next_run = schedule.next_run
        schedule.mark_run()

        assert schedule.last_run is not None
        assert schedule.run_count == 1
        assert schedule.next_run != initial_next_run

    def test_schedule_disabled(self):
        """Test disabled schedule"""
        schedule = Schedule(
            job_name="test_job",
            job_params={},
            interval=timedelta(seconds=1),
            enabled=False
        )

        assert schedule.should_run() is False

    def test_schedule_to_dict(self):
        """Test schedule serialization"""
        schedule = Schedule(
            job_name="test_job",
            job_params={"key": "value"},
            interval=timedelta(hours=1),
            queue="custom_queue"
        )

        schedule_dict = schedule.to_dict()

        assert schedule_dict["job_name"] == "test_job"
        assert schedule_dict["job_params"] == {"key": "value"}
        assert schedule_dict["queue"] == "custom_queue"


class TestJobScheduler:
    """Test JobScheduler class"""

    def setup_method(self):
        """Setup before each test"""
        JobRegistry.clear()
        JobRegistry.register()(TestJob)

        # Mock queue manager
        self.mock_queue = Mock(spec=QueueManager)
        self.mock_queue.enqueue = Mock(return_value="task-123")

        self.scheduler = JobScheduler(self.mock_queue)

    def teardown_method(self):
        """Cleanup after each test"""
        if self.scheduler.is_running():
            self.scheduler.stop()

    def test_add_schedule(self):
        """Test adding a schedule"""
        schedule = self.scheduler.add_schedule(
            schedule_id="test-schedule",
            job_name="TestJob",
            job_params={"param": "value"},
            interval=timedelta(hours=1)
        )

        assert schedule is not None
        assert schedule.job_name == "TestJob"
        assert "test-schedule" in self.scheduler.schedules

    def test_remove_schedule(self):
        """Test removing a schedule"""
        self.scheduler.add_schedule(
            schedule_id="test-schedule",
            job_name="TestJob",
            job_params={},
            interval=timedelta(hours=1)
        )

        removed = self.scheduler.remove_schedule("test-schedule")

        assert removed is True
        assert "test-schedule" not in self.scheduler.schedules

    def test_enable_disable_schedule(self):
        """Test enabling and disabling schedules"""
        self.scheduler.add_schedule(
            schedule_id="test-schedule",
            job_name="TestJob",
            job_params={},
            interval=timedelta(hours=1)
        )

        # Disable
        self.scheduler.disable_schedule("test-schedule")
        schedule = self.scheduler.get_schedule("test-schedule")
        assert schedule.enabled is False

        # Enable
        self.scheduler.enable_schedule("test-schedule")
        schedule = self.scheduler.get_schedule("test-schedule")
        assert schedule.enabled is True

    def test_list_schedules(self):
        """Test listing schedules"""
        self.scheduler.add_schedule(
            schedule_id="schedule-1",
            job_name="TestJob",
            job_params={},
            interval=timedelta(hours=1)
        )

        self.scheduler.add_schedule(
            schedule_id="schedule-2",
            job_name="TestJob",
            job_params={},
            interval=timedelta(hours=2)
        )

        schedules = self.scheduler.list_schedules()

        assert len(schedules) == 2

    def test_start_stop_scheduler(self):
        """Test starting and stopping scheduler"""
        assert self.scheduler.is_running() is False

        self.scheduler.start()
        assert self.scheduler.is_running() is True

        self.scheduler.stop()
        assert self.scheduler.is_running() is False

    def test_run_once(self):
        """Test running schedule once"""
        self.scheduler.add_schedule(
            schedule_id="test-schedule",
            job_name="TestJob",
            job_params={"param": "value"},
            interval=timedelta(hours=1)
        )

        task_id = self.scheduler.run_once("test-schedule")

        assert task_id == "task-123"
        self.mock_queue.enqueue.assert_called_once()

    def test_schedule_execution(self):
        """Test automatic schedule execution"""
        # Add schedule that should run immediately
        self.scheduler.add_schedule(
            schedule_id="test-schedule",
            job_name="TestJob",
            job_params={},
            interval=timedelta(seconds=1)
        )

        # Check schedule manually
        self.scheduler._check_schedules()

        # Verify job was enqueued
        self.mock_queue.enqueue.assert_called()
