"""
Job Scheduler

Provides job scheduling with cron support, recurring jobs, and schedule management.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from threading import Thread, Event
import time

from src.jobs.base import BaseJob, JobRegistry
from src.jobs.queue import QueueManager

logger = logging.getLogger(__name__)


class Schedule:
    """Represents a job schedule"""

    def __init__(
        self,
        job_name: str,
        job_params: Dict[str, Any],
        cron: Optional[str] = None,
        interval: Optional[timedelta] = None,
        at_time: Optional[str] = None,
        queue: str = "default",
        enabled: bool = True
    ):
        """
        Create a job schedule

        Args:
            job_name: Name of registered job to schedule
            job_params: Parameters to pass to job
            cron: Cron expression (e.g., "0 * * * *" for hourly)
            interval: Time interval for recurring execution
            at_time: Specific time to run (HH:MM format)
            queue: Queue to enqueue job in
            enabled: Whether schedule is enabled
        """
        self.job_name = job_name
        self.job_params = job_params
        self.cron = cron
        self.interval = interval
        self.at_time = at_time
        self.queue = queue
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0

        self._calculate_next_run()

    def _calculate_next_run(self) -> None:
        """Calculate next run time based on schedule type"""
        now = datetime.utcnow()

        if self.cron:
            # Parse cron expression and calculate next run
            self.next_run = self._calculate_cron_next_run(now)
        elif self.interval:
            # Interval-based scheduling
            if self.last_run:
                self.next_run = self.last_run + self.interval
            else:
                self.next_run = now
        elif self.at_time:
            # Specific time scheduling
            self.next_run = self._calculate_time_next_run(now)
        else:
            # One-time execution
            self.next_run = now

    def _calculate_cron_next_run(self, from_time: datetime) -> datetime:
        """Calculate next run from cron expression"""
        try:
            from croniter import croniter

            cron = croniter(self.cron, from_time)
            return cron.get_next(datetime)
        except ImportError:
            logger.warning("croniter not installed, using interval fallback")
            return from_time + timedelta(hours=1)
        except Exception as e:
            logger.error(f"Error parsing cron expression '{self.cron}': {e}")
            return from_time + timedelta(hours=1)

    def _calculate_time_next_run(self, from_time: datetime) -> datetime:
        """Calculate next run for specific time"""
        hour, minute = map(int, self.at_time.split(":"))
        next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If time has passed today, schedule for tomorrow
        if next_run <= from_time:
            next_run += timedelta(days=1)

        return next_run

    def should_run(self) -> bool:
        """Check if schedule should run now"""
        if not self.enabled or not self.next_run:
            return False

        return datetime.utcnow() >= self.next_run

    def mark_run(self) -> None:
        """Mark schedule as run and calculate next run"""
        self.last_run = datetime.utcnow()
        self.run_count += 1
        self._calculate_next_run()

    def to_dict(self) -> Dict[str, Any]:
        """Convert schedule to dictionary"""
        return {
            "job_name": self.job_name,
            "job_params": self.job_params,
            "cron": self.cron,
            "interval": str(self.interval) if self.interval else None,
            "at_time": self.at_time,
            "queue": self.queue,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count
        }


class JobScheduler:
    """
    Job scheduler with cron support and recurring jobs

    Usage:
        scheduler = JobScheduler(queue_manager)

        # Schedule job to run every hour
        scheduler.add_schedule(
            "my_job",
            {"param1": "value1"},
            cron="0 * * * *"
        )

        # Schedule job with interval
        scheduler.add_schedule(
            "another_job",
            {},
            interval=timedelta(minutes=30)
        )

        # Schedule job at specific time
        scheduler.add_schedule(
            "daily_job",
            {},
            at_time="03:00"
        )

        # Start scheduler
        scheduler.start()
    """

    def __init__(self, queue_manager: QueueManager):
        """
        Initialize job scheduler

        Args:
            queue_manager: Queue manager for job execution
        """
        self.queue_manager = queue_manager
        self.schedules: Dict[str, Schedule] = {}
        self._running = False
        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._check_interval = 1.0  # seconds

    def add_schedule(
        self,
        schedule_id: str,
        job_name: str,
        job_params: Dict[str, Any],
        cron: Optional[str] = None,
        interval: Optional[timedelta] = None,
        at_time: Optional[str] = None,
        queue: str = "default",
        enabled: bool = True
    ) -> Schedule:
        """
        Add a job schedule

        Args:
            schedule_id: Unique schedule identifier
            job_name: Name of registered job
            job_params: Job parameters
            cron: Cron expression
            interval: Time interval
            at_time: Specific time (HH:MM)
            queue: Queue name
            enabled: Whether enabled

        Returns:
            Created schedule
        """
        schedule = Schedule(
            job_name=job_name,
            job_params=job_params,
            cron=cron,
            interval=interval,
            at_time=at_time,
            queue=queue,
            enabled=enabled
        )

        self.schedules[schedule_id] = schedule
        logger.info(f"Added schedule '{schedule_id}' for job '{job_name}'")
        return schedule

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            logger.info(f"Removed schedule '{schedule_id}'")
            return True
        return False

    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = True
            logger.info(f"Enabled schedule '{schedule_id}'")
            return True
        return False

    def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = False
            logger.info(f"Disabled schedule '{schedule_id}'")
            return True
        return False

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID"""
        return self.schedules.get(schedule_id)

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all schedules"""
        return [s.to_dict() for s in self.schedules.values()]

    def start(self) -> None:
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Job scheduler started")

    def stop(self) -> None:
        """Stop the scheduler"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5.0)

        logger.info("Job scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                self._check_schedules()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            # Wait for check interval or stop event
            self._stop_event.wait(self._check_interval)

    def _check_schedules(self) -> None:
        """Check and execute due schedules"""
        for schedule_id, schedule in self.schedules.items():
            if schedule.should_run():
                try:
                    self._execute_schedule(schedule_id, schedule)
                except Exception as e:
                    logger.error(f"Error executing schedule '{schedule_id}': {e}", exc_info=True)

    def _execute_schedule(self, schedule_id: str, schedule: Schedule) -> None:
        """Execute a scheduled job"""
        # Create job instance
        job = JobRegistry.create(schedule.job_name, **schedule.job_params)
        if not job:
            logger.error(f"Cannot create job '{schedule.job_name}' for schedule '{schedule_id}'")
            return

        # Enqueue job
        task_id = self.queue_manager.enqueue(job, queue=schedule.queue)

        # Mark as run
        schedule.mark_run()

        logger.info(
            f"Executed schedule '{schedule_id}' "
            f"(job: {schedule.job_name}, task: {task_id}, "
            f"run_count: {schedule.run_count})"
        )

    def run_once(self, schedule_id: str) -> Optional[str]:
        """
        Run a schedule immediately (one-time)

        Args:
            schedule_id: Schedule to run

        Returns:
            Task ID or None if schedule not found
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            logger.error(f"Schedule '{schedule_id}' not found")
            return None

        job = JobRegistry.create(schedule.job_name, **schedule.job_params)
        if not job:
            logger.error(f"Cannot create job '{schedule.job_name}'")
            return None

        task_id = self.queue_manager.enqueue(job, queue=schedule.queue)
        logger.info(f"Manually executed schedule '{schedule_id}' (task: {task_id})")
        return task_id

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running
