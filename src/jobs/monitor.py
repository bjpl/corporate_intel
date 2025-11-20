"""
Job Monitor

Provides job monitoring, metrics collection, progress tracking, and observability.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from threading import Lock

from src.jobs.base import BaseJob, JobResult, JobState

logger = logging.getLogger(__name__)


class JobMetrics:
    """Container for job execution metrics"""

    def __init__(self):
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.running_jobs = 0
        self.total_duration = 0.0
        self.avg_duration = 0.0
        self.min_duration = float('inf')
        self.max_duration = 0.0
        self.success_rate = 0.0
        self.failure_rate = 0.0
        self.retry_count = 0
        self.jobs_by_state: Dict[JobState, int] = defaultdict(int)
        self.jobs_by_type: Dict[str, int] = defaultdict(int)
        self.errors: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "running_jobs": self.running_jobs,
            "total_duration": self.total_duration,
            "avg_duration": self.avg_duration,
            "min_duration": self.min_duration if self.min_duration != float('inf') else 0,
            "max_duration": self.max_duration,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "retry_count": self.retry_count,
            "jobs_by_state": {k.value: v for k, v in self.jobs_by_state.items()},
            "jobs_by_type": dict(self.jobs_by_type),
            "recent_errors": self.errors[-10:]  # Last 10 errors
        }


class JobMonitor:
    """
    Job monitoring and metrics collection system

    Features:
    - Real-time job tracking
    - Metrics collection and aggregation
    - Progress tracking
    - Error logging
    - Performance monitoring
    - Health checks

    Usage:
        monitor = JobMonitor()

        # Track job
        monitor.track_job_start(job)
        result = job.run()
        monitor.track_job_complete(job, result)

        # Get metrics
        metrics = monitor.get_metrics()

        # Get job status
        status = monitor.get_job_status(job_id)
    """

    def __init__(self, retention_period: timedelta = timedelta(days=7)):
        """
        Initialize job monitor

        Args:
            retention_period: How long to retain job history
        """
        self.retention_period = retention_period
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._start_time = datetime.utcnow()

    def track_job_start(self, job: BaseJob) -> None:
        """
        Track job start

        Args:
            job: Job instance starting execution
        """
        with self._lock:
            self._jobs[job.job_id] = {
                "job_id": job.job_id,
                "job_name": job.get_name(),
                "state": JobState.RUNNING,
                "started_at": datetime.utcnow(),
                "completed_at": None,
                "duration": None,
                "result": None,
                "retry_count": 0,
                "params": job.params,
                "metadata": {}
            }

        logger.info(f"Tracking job start: {job.job_id} ({job.get_name()})")

    def track_job_complete(self, job: BaseJob, result: JobResult) -> None:
        """
        Track job completion

        Args:
            job: Job instance
            result: Job result
        """
        with self._lock:
            if job.job_id in self._jobs:
                job_data = self._jobs[job.job_id]
                job_data.update({
                    "state": result.status,
                    "completed_at": datetime.utcnow(),
                    "duration": result.duration,
                    "result": result.to_dict(),
                    "retry_count": job.retry_count
                })

        logger.info(
            f"Tracking job complete: {job.job_id} "
            f"(status: {result.status.value}, duration: {result.duration:.2f}s)"
        )

    def track_job_retry(self, job: BaseJob, retry_count: int) -> None:
        """
        Track job retry

        Args:
            job: Job instance
            retry_count: Current retry count
        """
        with self._lock:
            if job.job_id in self._jobs:
                self._jobs[job.job_id]["retry_count"] = retry_count
                self._jobs[job.job_id]["state"] = JobState.RETRYING

        logger.info(f"Tracking job retry: {job.job_id} (attempt {retry_count})")

    def update_job_progress(self, job_id: str, progress: float, message: str = "") -> None:
        """
        Update job progress

        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            message: Progress message
        """
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["metadata"]["progress"] = progress
                self._jobs[job_id]["metadata"]["progress_message"] = message
                self._jobs[job_id]["metadata"]["last_update"] = datetime.utcnow().isoformat()

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status

        Args:
            job_id: Job identifier

        Returns:
            Job status dictionary or None
        """
        with self._lock:
            return self._jobs.get(job_id)

    def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get all running jobs"""
        with self._lock:
            return [
                job for job in self._jobs.values()
                if job["state"] == JobState.RUNNING
            ]

    def get_failed_jobs(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get failed jobs

        Args:
            since: Only return jobs failed after this time

        Returns:
            List of failed jobs
        """
        with self._lock:
            failed = [
                job for job in self._jobs.values()
                if job["state"] == JobState.FAILED
            ]

            if since:
                failed = [
                    job for job in failed
                    if job["completed_at"] and job["completed_at"] > since
                ]

            return failed

    def get_metrics(self, job_type: Optional[str] = None) -> JobMetrics:
        """
        Get aggregated metrics

        Args:
            job_type: Optional job type filter

        Returns:
            JobMetrics instance
        """
        metrics = JobMetrics()

        with self._lock:
            jobs = list(self._jobs.values())

            # Filter by job type if specified
            if job_type:
                jobs = [j for j in jobs if j["job_name"] == job_type]

            metrics.total_jobs = len(jobs)

            for job in jobs:
                state = job["state"]
                job_name = job["job_name"]

                # State counts
                metrics.jobs_by_state[state] += 1
                metrics.jobs_by_type[job_name] += 1

                # Status counts
                if state == JobState.COMPLETED:
                    metrics.completed_jobs += 1
                elif state == JobState.FAILED:
                    metrics.failed_jobs += 1

                    # Track errors
                    if job.get("result") and job["result"].get("error"):
                        metrics.errors.append({
                            "job_id": job["job_id"],
                            "job_name": job_name,
                            "error": job["result"]["error"],
                            "timestamp": job["completed_at"].isoformat() if job["completed_at"] else None
                        })
                elif state == JobState.RUNNING:
                    metrics.running_jobs += 1

                # Retry tracking
                metrics.retry_count += job.get("retry_count", 0)

                # Duration metrics
                duration = job.get("duration")
                if duration is not None:
                    metrics.total_duration += duration
                    metrics.min_duration = min(metrics.min_duration, duration)
                    metrics.max_duration = max(metrics.max_duration, duration)

            # Calculate rates and averages
            if metrics.total_jobs > 0:
                completed = metrics.completed_jobs + metrics.failed_jobs
                if completed > 0:
                    metrics.success_rate = (metrics.completed_jobs / completed) * 100
                    metrics.failure_rate = (metrics.failed_jobs / completed) * 100
                    metrics.avg_duration = metrics.total_duration / completed

        return metrics

    def get_job_history(
        self,
        limit: int = 100,
        job_type: Optional[str] = None,
        state: Optional[JobState] = None
    ) -> List[Dict[str, Any]]:
        """
        Get job history

        Args:
            limit: Maximum number of jobs to return
            job_type: Filter by job type
            state: Filter by state

        Returns:
            List of jobs sorted by start time (newest first)
        """
        with self._lock:
            jobs = list(self._jobs.values())

            # Apply filters
            if job_type:
                jobs = [j for j in jobs if j["job_name"] == job_type]
            if state:
                jobs = [j for j in jobs if j["state"] == state]

            # Sort by start time (newest first)
            jobs.sort(key=lambda x: x["started_at"], reverse=True)

            return jobs[:limit]

    def cleanup_old_jobs(self) -> int:
        """
        Remove jobs older than retention period

        Returns:
            Number of jobs removed
        """
        cutoff = datetime.utcnow() - self.retention_period
        removed = 0

        with self._lock:
            jobs_to_remove = [
                job_id for job_id, job in self._jobs.items()
                if job["completed_at"] and job["completed_at"] < cutoff
            ]

            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old jobs")

        return removed

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get monitor health status

        Returns:
            Health status dictionary
        """
        metrics = self.get_metrics()
        uptime = (datetime.utcnow() - self._start_time).total_seconds()

        # Health checks
        high_failure_rate = metrics.failure_rate > 50
        many_running_jobs = metrics.running_jobs > 100

        health = "healthy"
        if high_failure_rate or many_running_jobs:
            health = "degraded"

        return {
            "status": health,
            "uptime_seconds": uptime,
            "total_jobs": metrics.total_jobs,
            "running_jobs": metrics.running_jobs,
            "failed_jobs": metrics.failed_jobs,
            "success_rate": metrics.success_rate,
            "failure_rate": metrics.failure_rate,
            "warnings": {
                "high_failure_rate": high_failure_rate,
                "many_running_jobs": many_running_jobs
            }
        }

    def clear(self) -> None:
        """Clear all tracked jobs (useful for testing)"""
        with self._lock:
            self._jobs.clear()
        logger.info("Cleared all tracked jobs")
