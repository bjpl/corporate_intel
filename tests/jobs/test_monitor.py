"""
Tests for job monitoring
"""

import pytest
from datetime import datetime, timedelta

from src.jobs.base import BaseJob, JobResult, JobState
from src.jobs.monitor import JobMonitor


class DummyJob(BaseJob):
    """Dummy job for testing"""

    def execute(self, **kwargs):
        return {"data": "test"}


class TestJobMonitor:
    """Test JobMonitor class"""

    def setup_method(self):
        """Create monitor before each test"""
        self.monitor = JobMonitor(retention_period=timedelta(days=1))

    def test_track_job_start(self):
        """Test tracking job start"""
        job = DummyJob()
        self.monitor.track_job_start(job)

        status = self.monitor.get_job_status(job.job_id)

        assert status is not None
        assert status["job_id"] == job.job_id
        assert status["state"] == JobState.RUNNING
        assert status["started_at"] is not None

    def test_track_job_complete(self):
        """Test tracking job completion"""
        job = DummyJob()
        self.monitor.track_job_start(job)

        result = JobResult(
            job_id=job.job_id,
            status=JobState.COMPLETED,
            data={"result": "success"},
            duration=1.5
        )

        self.monitor.track_job_complete(job, result)

        status = self.monitor.get_job_status(job.job_id)

        assert status["state"] == JobState.COMPLETED
        assert status["duration"] == 1.5
        assert status["result"] is not None

    def test_track_job_retry(self):
        """Test tracking job retry"""
        job = DummyJob()
        self.monitor.track_job_start(job)
        self.monitor.track_job_retry(job, 1)

        status = self.monitor.get_job_status(job.job_id)

        assert status["retry_count"] == 1
        assert status["state"] == JobState.RETRYING

    def test_update_job_progress(self):
        """Test updating job progress"""
        job = DummyJob()
        self.monitor.track_job_start(job)
        self.monitor.update_job_progress(job.job_id, 50.0, "Halfway done")

        status = self.monitor.get_job_status(job.job_id)

        assert status["metadata"]["progress"] == 50.0
        assert status["metadata"]["progress_message"] == "Halfway done"

    def test_get_running_jobs(self):
        """Test getting running jobs"""
        job1 = DummyJob()
        job2 = DummyJob()

        self.monitor.track_job_start(job1)
        self.monitor.track_job_start(job2)

        running = self.monitor.get_running_jobs()

        assert len(running) == 2
        assert all(j["state"] == JobState.RUNNING for j in running)

    def test_get_failed_jobs(self):
        """Test getting failed jobs"""
        job = DummyJob()
        self.monitor.track_job_start(job)

        result = JobResult(
            job_id=job.job_id,
            status=JobState.FAILED,
            error="Test error"
        )

        self.monitor.track_job_complete(job, result)

        failed = self.monitor.get_failed_jobs()

        assert len(failed) == 1
        assert failed[0]["state"] == JobState.FAILED

    def test_get_metrics(self):
        """Test getting aggregated metrics"""
        # Create and complete some jobs
        for i in range(5):
            job = DummyJob()
            self.monitor.track_job_start(job)

            if i < 3:
                # Successful jobs
                result = JobResult(
                    job_id=job.job_id,
                    status=JobState.COMPLETED,
                    duration=float(i + 1)
                )
            else:
                # Failed jobs
                result = JobResult(
                    job_id=job.job_id,
                    status=JobState.FAILED,
                    error="Error"
                )

            self.monitor.track_job_complete(job, result)

        metrics = self.monitor.get_metrics()

        assert metrics.total_jobs == 5
        assert metrics.completed_jobs == 3
        assert metrics.failed_jobs == 2
        assert metrics.success_rate == 60.0
        assert metrics.failure_rate == 40.0

    def test_get_job_history(self):
        """Test getting job history"""
        jobs = [DummyJob() for _ in range(10)]

        for job in jobs:
            self.monitor.track_job_start(job)

        history = self.monitor.get_job_history(limit=5)

        assert len(history) == 5

    def test_cleanup_old_jobs(self):
        """Test cleaning up old jobs"""
        job = DummyJob()
        self.monitor.track_job_start(job)

        result = JobResult(
            job_id=job.job_id,
            status=JobState.COMPLETED
        )

        self.monitor.track_job_complete(job, result)

        # Manually set old completion time
        job_data = self.monitor._jobs[job.job_id]
        job_data["completed_at"] = datetime.utcnow() - timedelta(days=2)

        removed = self.monitor.cleanup_old_jobs()

        assert removed == 1
        assert self.monitor.get_job_status(job.job_id) is None

    def test_health_status(self):
        """Test getting health status"""
        health = self.monitor.get_health_status()

        assert "status" in health
        assert "uptime_seconds" in health
        assert "total_jobs" in health
        assert health["status"] == "healthy"

    def test_clear(self):
        """Test clearing all jobs"""
        job = DummyJob()
        self.monitor.track_job_start(job)

        assert len(self.monitor._jobs) > 0

        self.monitor.clear()

        assert len(self.monitor._jobs) == 0
