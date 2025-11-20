"""
Tests for base job framework
"""

import pytest
import time
from datetime import datetime

from src.jobs.base import BaseJob, JobRegistry, JobState, JobResult


class SimpleJob(BaseJob):
    """Simple test job"""

    def execute(self, **kwargs):
        value = kwargs.get("value", 0)
        return {"result": value * 2}


class FailingJob(BaseJob):
    """Job that always fails"""

    max_retries = 2
    retry_delay = 0.1

    def execute(self, **kwargs):
        raise ValueError("Intentional failure")


class TimeoutJob(BaseJob):
    """Job that times out"""

    timeout = 0.5

    def execute(self, **kwargs):
        time.sleep(1.0)
        return {}


class TestBaseJob:
    """Test BaseJob class"""

    def test_job_creation(self):
        """Test job instance creation"""
        job = SimpleJob(value=5)

        assert job.job_id is not None
        assert job.state == JobState.PENDING
        assert job.params == {"value": 5}
        assert job.retry_count == 0

    def test_job_execution_success(self):
        """Test successful job execution"""
        job = SimpleJob(value=10)
        result = job.run()

        assert result.status == JobState.COMPLETED
        assert result.data["result"] == 20
        assert result.error is None
        assert result.duration is not None
        assert result.duration > 0

    def test_job_execution_failure(self):
        """Test job execution failure with retries"""
        job = FailingJob()
        result = job.run()

        assert result.status == JobState.FAILED
        assert result.error is not None
        assert "Intentional failure" in result.error
        assert job.retry_count == job.max_retries

    def test_job_timeout(self):
        """Test job timeout"""
        job = TimeoutJob()
        result = job.run()

        assert result.status == JobState.FAILED
        assert "timeout" in result.error.lower()

    def test_job_metadata(self):
        """Test job metadata management"""
        job = SimpleJob()

        job.set_metadata("key1", "value1")
        job.set_metadata("key2", 123)

        assert job.get_metadata("key1") == "value1"
        assert job.get_metadata("key2") == 123
        assert job.get_metadata("nonexistent", "default") == "default"

    def test_job_lifecycle_hooks(self):
        """Test job lifecycle hooks"""
        hook_calls = []

        class HookJob(BaseJob):
            def execute(self, **kwargs):
                return {"data": "test"}

            def on_start(self):
                hook_calls.append("start")

            def on_success(self, result):
                hook_calls.append("success")

            def on_failure(self, error, result):
                hook_calls.append("failure")

        job = HookJob()
        job.run()

        assert "start" in hook_calls
        assert "success" in hook_calls
        assert "failure" not in hook_calls

    def test_job_to_dict(self):
        """Test job serialization"""
        job = SimpleJob(value=5)
        job.run()

        job_dict = job.to_dict()

        assert job_dict["job_id"] == job.job_id
        assert job_dict["name"] == "SimpleJob"
        assert job_dict["state"] == JobState.COMPLETED.value
        assert job_dict["params"] == {"value": 5}
        assert job_dict["result"] is not None


class TestJobRegistry:
    """Test JobRegistry class"""

    def setup_method(self):
        """Clear registry before each test"""
        JobRegistry.clear()

    def test_job_registration_decorator(self):
        """Test job registration via decorator"""

        @JobRegistry.register()
        class TestJob1(BaseJob):
            def execute(self, **kwargs):
                return {}

        assert "TestJob1" in JobRegistry.list_jobs()
        assert JobRegistry.get("TestJob1") == TestJob1

    def test_job_registration_with_custom_name(self):
        """Test job registration with custom name"""

        @JobRegistry.register("custom_name")
        class TestJob2(BaseJob):
            def execute(self, **kwargs):
                return {}

        assert "custom_name" in JobRegistry.list_jobs()
        assert JobRegistry.get("custom_name") == TestJob2

    def test_job_creation_by_name(self):
        """Test job instance creation by name"""

        @JobRegistry.register()
        class TestJob3(BaseJob):
            def execute(self, **kwargs):
                return kwargs

        job = JobRegistry.create("TestJob3", param1="value1")

        assert job is not None
        assert isinstance(job, TestJob3)
        assert job.params == {"param1": "value1"}

    def test_job_list(self):
        """Test listing registered jobs"""

        @JobRegistry.register()
        class Job1(BaseJob):
            def execute(self, **kwargs):
                return {}

        @JobRegistry.register()
        class Job2(BaseJob):
            def execute(self, **kwargs):
                return {}

        jobs = JobRegistry.list_jobs()

        assert "Job1" in jobs
        assert "Job2" in jobs

    def test_registry_clear(self):
        """Test clearing registry"""

        @JobRegistry.register()
        class TempJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        assert len(JobRegistry.list_jobs()) > 0

        JobRegistry.clear()

        assert len(JobRegistry.list_jobs()) == 0


class TestJobResult:
    """Test JobResult class"""

    def test_result_creation(self):
        """Test result creation"""
        result = JobResult(
            job_id="test-123",
            status=JobState.COMPLETED,
            data={"key": "value"},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration=1.5
        )

        assert result.job_id == "test-123"
        assert result.status == JobState.COMPLETED
        assert result.data == {"key": "value"}
        assert result.duration == 1.5

    def test_result_to_dict(self):
        """Test result serialization"""
        now = datetime.utcnow()
        result = JobResult(
            job_id="test-123",
            status=JobState.COMPLETED,
            data={"key": "value"},
            started_at=now,
            completed_at=now,
            duration=1.5,
            metadata={"meta": "data"}
        )

        result_dict = result.to_dict()

        assert result_dict["job_id"] == "test-123"
        assert result_dict["status"] == "completed"
        assert result_dict["data"] == {"key": "value"}
        assert result_dict["duration"] == 1.5
        assert result_dict["metadata"] == {"meta": "data"}
