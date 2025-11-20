"""Tests for base job functionality."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.jobs.base import BaseJob, JobState, JobResult, JobRegistry


class TestJobState:
    """Test JobState enum."""

    def test_job_states(self):
        """Test all job states are defined."""
        assert JobState.PENDING.value == "pending"
        assert JobState.RUNNING.value == "running"
        assert JobState.COMPLETED.value == "completed"
        assert JobState.FAILED.value == "failed"
        assert JobState.RETRYING.value == "retrying"
        assert JobState.CANCELLED.value == "cancelled"


class TestJobResult:
    """Test JobResult container."""

    def test_job_result_creation(self):
        """Test creating job result."""
        started = datetime.utcnow()
        completed = datetime.utcnow()

        result = JobResult(
            job_id="test-job-1",
            status=JobState.COMPLETED,
            data={"count": 42},
            started_at=started,
            completed_at=completed,
            duration=1.5
        )

        assert result.job_id == "test-job-1"
        assert result.status == JobState.COMPLETED
        assert result.data["count"] == 42
        assert result.duration == 1.5

    def test_job_result_to_dict(self):
        """Test converting result to dictionary."""
        started = datetime.utcnow()
        completed = datetime.utcnow()

        result = JobResult(
            job_id="test-job-1",
            status=JobState.COMPLETED,
            data={"count": 42},
            started_at=started,
            completed_at=completed,
            duration=1.5,
            metadata={"source": "test"}
        )

        result_dict = result.to_dict()

        assert result_dict["job_id"] == "test-job-1"
        assert result_dict["status"] == "completed"
        assert result_dict["data"]["count"] == 42
        assert result_dict["metadata"]["source"] == "test"

    def test_job_result_with_error(self):
        """Test job result with error."""
        result = JobResult(
            job_id="test-job-1",
            status=JobState.FAILED,
            error="Division by zero"
        )

        assert result.status == JobState.FAILED
        assert result.error == "Division by zero"
        assert result.data == {}


class TestBaseJob:
    """Test BaseJob functionality."""

    def test_job_initialization(self):
        """Test job initialization."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {"result": "success"}

        job = TestJob(test_param="value")

        assert job.state == JobState.PENDING
        assert job.retry_count == 0
        assert job.params["test_param"] == "value"
        assert job.job_id is not None

    def test_job_with_custom_id(self):
        """Test job with custom ID."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        job = TestJob(job_id="custom-job-id")
        assert job.job_id == "custom-job-id"

    def test_successful_job_execution(self):
        """Test successful job execution."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {"count": kwargs.get("count", 0) * 2}

        job = TestJob(count=21)
        result = job.run()

        assert result.status == JobState.COMPLETED
        assert result.data["count"] == 42
        assert result.error is None
        assert job.state == JobState.COMPLETED

    def test_failed_job_execution(self):
        """Test failed job execution."""

        class FailingJob(BaseJob):
            max_retries = 0  # No retries

            def execute(self, **kwargs):
                raise ValueError("Test error")

        job = FailingJob()
        result = job.run()

        assert result.status == JobState.FAILED
        assert "ValueError: Test error" in result.error
        assert job.state == JobState.FAILED

    def test_job_with_retries(self):
        """Test job retry logic."""

        class RetryJob(BaseJob):
            max_retries = 3
            retry_delay = 0.1  # Fast retries for testing

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                if self.attempts < 3:
                    raise ValueError(f"Attempt {self.attempts} failed")
                return {"attempts": self.attempts}

        job = RetryJob()
        result = job.run()

        assert result.status == JobState.COMPLETED
        assert job.attempts == 3
        assert job.retry_count == 2

    def test_job_max_retries_exceeded(self):
        """Test job failing after max retries."""

        class AlwaysFailJob(BaseJob):
            max_retries = 2
            retry_delay = 0.05

            def execute(self, **kwargs):
                raise ValueError("Always fails")

        job = AlwaysFailJob()
        result = job.run()

        assert result.status == JobState.FAILED
        assert job.retry_count == 2
        assert "ValueError" in result.error

    def test_job_timeout(self):
        """Test job timeout."""

        class SlowJob(BaseJob):
            timeout = 0.1  # 100ms timeout

            def execute(self, **kwargs):
                time.sleep(0.2)  # Sleep longer than timeout
                return {}

        job = SlowJob()
        result = job.run()

        assert result.status == JobState.FAILED
        assert "TimeoutError" in result.error


class TestJobLifecycleHooks:
    """Test job lifecycle hooks."""

    def test_on_start_hook(self):
        """Test on_start hook is called."""

        class HookedJob(BaseJob):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.started = False

            def on_start(self):
                self.started = True

            def execute(self, **kwargs):
                return {}

        job = HookedJob()
        job.run()

        assert job.started is True

    def test_on_success_hook(self):
        """Test on_success hook is called."""

        class HookedJob(BaseJob):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.success_result = None

            def on_success(self, result):
                self.success_result = result

            def execute(self, **kwargs):
                return {"status": "done"}

        job = HookedJob()
        job.run()

        assert job.success_result is not None
        assert job.success_result.status == JobState.COMPLETED

    def test_on_failure_hook(self):
        """Test on_failure hook is called."""

        class HookedJob(BaseJob):
            max_retries = 0

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.failure_error = None

            def on_failure(self, error, result):
                self.failure_error = error

            def execute(self, **kwargs):
                raise ValueError("Test failure")

        job = HookedJob()
        job.run()

        assert job.failure_error is not None
        assert isinstance(job.failure_error, ValueError)

    def test_on_retry_hook(self):
        """Test on_retry hook is called."""

        class HookedJob(BaseJob):
            max_retries = 2
            retry_delay = 0.05

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.retry_attempts = []

            def on_retry(self, error, retry_count, delay):
                self.retry_attempts.append({
                    "count": retry_count,
                    "delay": delay
                })

            def execute(self, **kwargs):
                if len(self.retry_attempts) < 1:
                    raise ValueError("Retry me")
                return {}

        job = HookedJob()
        job.run()

        assert len(job.retry_attempts) == 1
        assert job.retry_attempts[0]["count"] == 1


class TestJobMetadata:
    """Test job metadata management."""

    def test_set_and_get_metadata(self):
        """Test setting and getting metadata."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                self.set_metadata("key", "value")
                return {}

        job = TestJob()
        job.run()

        assert job.get_metadata("key") == "value"

    def test_metadata_in_result(self):
        """Test metadata included in result."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                self.set_metadata("processed_count", 42)
                return {}

        job = TestJob()
        result = job.run()

        assert result.metadata["processed_count"] == 42

    def test_get_metadata_with_default(self):
        """Test getting metadata with default value."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        job = TestJob()
        value = job.get_metadata("missing_key", "default")

        assert value == "default"


class TestJobInformation:
    """Test job information methods."""

    def test_get_name(self):
        """Test getting job name."""

        class MyCustomJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        job = MyCustomJob()
        assert job.get_name() == "MyCustomJob"

    def test_get_description(self):
        """Test getting job description."""

        class DocumentedJob(BaseJob):
            """This is a test job for documentation."""

            def execute(self, **kwargs):
                return {}

        job = DocumentedJob()
        assert "test job" in job.get_description()

    def test_to_dict(self):
        """Test converting job to dictionary."""

        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {"result": "success"}

        job = TestJob(param1="value1")
        job.run()

        job_dict = job.to_dict()

        assert job_dict["name"] == "TestJob"
        assert job_dict["state"] == "completed"
        assert job_dict["params"]["param1"] == "value1"
        assert job_dict["result"]["status"] == "completed"


class TestJobRegistry:
    """Test job registry functionality."""

    def setUp(self):
        """Clear registry before each test."""
        JobRegistry.clear()

    def test_register_job_class(self):
        """Test registering a job class."""
        JobRegistry.clear()

        @JobRegistry.register()
        class RegisteredJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        assert "RegisteredJob" in JobRegistry.list_jobs()

    def test_register_job_with_custom_name(self):
        """Test registering job with custom name."""
        JobRegistry.clear()

        @JobRegistry.register("custom_job")
        class MyJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        assert "custom_job" in JobRegistry.list_jobs()

    def test_get_registered_job(self):
        """Test getting registered job class."""
        JobRegistry.clear()

        @JobRegistry.register()
        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        job_class = JobRegistry.get("TestJob")
        assert job_class == TestJob

    def test_create_job_instance(self):
        """Test creating job instance from registry."""
        JobRegistry.clear()

        @JobRegistry.register()
        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {"value": kwargs.get("value")}

        job = JobRegistry.create("TestJob", value=42)
        assert job is not None
        assert isinstance(job, TestJob)

        result = job.run()
        assert result.data["value"] == 42

    def test_list_registered_jobs(self):
        """Test listing all registered jobs."""
        JobRegistry.clear()

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
        """Test clearing the registry."""
        JobRegistry.clear()

        @JobRegistry.register()
        class TestJob(BaseJob):
            def execute(self, **kwargs):
                return {}

        assert len(JobRegistry.list_jobs()) > 0

        JobRegistry.clear()
        assert len(JobRegistry.list_jobs()) == 0


class TestJobParameters:
    """Test job parameter handling."""

    def test_job_with_parameters(self):
        """Test job execution with parameters."""

        class ParameterizedJob(BaseJob):
            def execute(self, **kwargs):
                a = kwargs.get("a", 0)
                b = kwargs.get("b", 0)
                return {"sum": a + b}

        job = ParameterizedJob(a=10, b=32)
        result = job.run()

        assert result.data["sum"] == 42

    def test_job_parameter_validation(self):
        """Test parameter validation in execute."""

        class ValidatingJob(BaseJob):
            def execute(self, **kwargs):
                required = kwargs.get("required_param")
                if not required:
                    raise ValueError("required_param is missing")
                return {"value": required}

        # Without required param
        job = ValidatingJob()
        result = job.run()
        assert result.status == JobState.FAILED

        # With required param
        job = ValidatingJob(required_param="value")
        result = job.run()
        assert result.status == JobState.COMPLETED


class TestJobDuration:
    """Test job duration tracking."""

    def test_job_duration_recorded(self):
        """Test that job duration is recorded."""

        class QuickJob(BaseJob):
            def execute(self, **kwargs):
                time.sleep(0.1)
                return {}

        job = QuickJob()
        result = job.run()

        assert result.duration is not None
        assert result.duration >= 0.1

    def test_failed_job_duration(self):
        """Test duration recorded for failed jobs."""

        class FailJob(BaseJob):
            max_retries = 0

            def execute(self, **kwargs):
                time.sleep(0.05)
                raise ValueError("Failed")

        job = FailJob()
        result = job.run()

        assert result.duration is not None
        assert result.duration >= 0.05


class TestJobConcurrency:
    """Test job behavior with concurrent execution."""

    def test_multiple_job_instances(self):
        """Test running multiple instances of same job."""

        class CounterJob(BaseJob):
            counter = 0

            def execute(self, **kwargs):
                CounterJob.counter += 1
                return {"count": CounterJob.counter}

        CounterJob.counter = 0

        job1 = CounterJob()
        job2 = CounterJob()

        result1 = job1.run()
        result2 = job2.run()

        assert result1.data["count"] in [1, 2]
        assert result2.data["count"] in [1, 2]
        assert CounterJob.counter == 2
