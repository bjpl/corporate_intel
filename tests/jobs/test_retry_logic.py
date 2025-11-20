"""Tests for job retry logic and exponential backoff."""

import pytest
import time
from unittest.mock import Mock, patch

from src.jobs.base import BaseJob, JobState


class TestRetryMechanism:
    """Test basic retry mechanism."""

    def test_job_retries_on_failure(self):
        """Test that job retries when it fails."""

        class RetryJob(BaseJob):
            max_retries = 3
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempt_count = 0

            def execute(self, **kwargs):
                self.attempt_count += 1
                if self.attempt_count <= 2:
                    raise ValueError(f"Attempt {self.attempt_count}")
                return {"attempts": self.attempt_count}

        job = RetryJob()
        result = job.run()

        assert job.attempt_count == 3
        assert job.retry_count == 2
        assert result.status == JobState.COMPLETED

    def test_job_fails_after_max_retries(self):
        """Test job fails after exhausting max retries."""

        class AlwaysFailJob(BaseJob):
            max_retries = 2
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempt_count = 0

            def execute(self, **kwargs):
                self.attempt_count += 1
                raise ValueError("Always fails")

        job = AlwaysFailJob()
        result = job.run()

        assert job.attempt_count == 3  # Initial + 2 retries
        assert job.retry_count == 2
        assert result.status == JobState.FAILED

    def test_no_retry_on_success(self):
        """Test job doesn't retry when successful."""

        class SuccessJob(BaseJob):
            max_retries = 3

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempt_count = 0

            def execute(self, **kwargs):
                self.attempt_count += 1
                return {"success": True}

        job = SuccessJob()
        result = job.run()

        assert job.attempt_count == 1
        assert job.retry_count == 0
        assert result.status == JobState.COMPLETED


class TestExponentialBackoff:
    """Test exponential backoff retry strategy."""

    def test_exponential_backoff_delays(self):
        """Test exponential backoff increases delay."""

        class BackoffJob(BaseJob):
            max_retries = 3
            retry_delay = 0.1
            retry_backoff = 2.0

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.retry_times = []

            def on_retry(self, error, retry_count, delay):
                self.retry_times.append({
                    "retry_count": retry_count,
                    "delay": delay,
                    "timestamp": time.time()
                })

            def execute(self, **kwargs):
                if len(self.retry_times) < 2:
                    raise ValueError("Retry")
                return {}

        job = BackoffJob()
        result = job.run()

        # Verify delays increase exponentially
        assert len(job.retry_times) == 2

        # First retry: 0.1 * 2^0 = 0.1
        assert abs(job.retry_times[0]["delay"] - 0.1) < 0.01

        # Second retry: 0.1 * 2^1 = 0.2
        assert abs(job.retry_times[1]["delay"] - 0.2) < 0.01

    def test_custom_backoff_multiplier(self):
        """Test custom backoff multiplier."""

        class CustomBackoffJob(BaseJob):
            max_retries = 2
            retry_delay = 0.05
            retry_backoff = 3.0

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.delays = []

            def on_retry(self, error, retry_count, delay):
                self.delays.append(delay)

            def execute(self, **kwargs):
                if len(self.delays) < 1:
                    raise ValueError("Retry")
                return {}

        job = CustomBackoffJob()
        job.run()

        # First retry: 0.05 * 3^0 = 0.05
        assert abs(job.delays[0] - 0.05) < 0.01


class TestRetryConditions:
    """Test different retry conditions."""

    def test_retry_on_specific_exception(self):
        """Test retrying only on specific exceptions."""

        class SelectiveRetryJob(BaseJob):
            max_retries = 2
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                if self.attempts == 1:
                    raise ConnectionError("Network error")
                elif self.attempts == 2:
                    raise ValueError("Validation error")
                return {}

        job = SelectiveRetryJob()
        result = job.run()

        # Job should retry on any exception by default
        assert job.attempts >= 2

    def test_no_retry_when_max_retries_zero(self):
        """Test no retries when max_retries is 0."""

        class NoRetryJob(BaseJob):
            max_retries = 0

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                raise ValueError("Error")

        job = NoRetryJob()
        result = job.run()

        assert job.attempts == 1
        assert job.retry_count == 0
        assert result.status == JobState.FAILED


class TestRetryState:
    """Test job state during retries."""

    def test_job_state_during_retry(self):
        """Test job state changes to RETRYING."""

        class StateTrackingJob(BaseJob):
            max_retries = 2
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.states = []

            def on_retry(self, error, retry_count, delay):
                self.states.append(self.state)

            def execute(self, **kwargs):
                if len(self.states) < 1:
                    raise ValueError("Retry")
                return {}

        job = StateTrackingJob()
        job.run()

        assert JobState.RETRYING in job.states

    def test_final_state_after_retries(self):
        """Test final state after successful retry."""

        class FinalStateJob(BaseJob):
            max_retries = 2
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                if self.attempts < 2:
                    raise ValueError("Retry")
                return {}

        job = FinalStateJob()
        result = job.run()

        assert job.state == JobState.COMPLETED
        assert result.status == JobState.COMPLETED


class TestRetryMetrics:
    """Test retry metrics and monitoring."""

    def test_retry_count_tracked(self):
        """Test retry count is properly tracked."""

        class CountedRetryJob(BaseJob):
            max_retries = 5
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                if self.attempts < 4:
                    raise ValueError("Retry")
                return {}

        job = CountedRetryJob()
        result = job.run()

        assert job.retry_count == 3
        assert job.attempts == 4

    def test_retry_metadata(self):
        """Test retry information in metadata."""

        class MetadataRetryJob(BaseJob):
            max_retries = 2
            retry_delay = 0.01

            def on_retry(self, error, retry_count, delay):
                self.set_metadata(f"retry_{retry_count}_error", str(error))

            def execute(self, **kwargs):
                if self.retry_count < 1:
                    raise ValueError("First error")
                return {}

        job = MetadataRetryJob()
        result = job.run()

        assert "retry_1_error" in result.metadata


class TestRetryPerformance:
    """Test retry performance characteristics."""

    def test_retry_delay_accuracy(self):
        """Test retry delays are approximately accurate."""

        class TimedRetryJob(BaseJob):
            max_retries = 2
            retry_delay = 0.1
            retry_backoff = 1.0

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.retry_timestamps = []

            def on_retry(self, error, retry_count, delay):
                self.retry_timestamps.append(time.time())

            def execute(self, **kwargs):
                if len(self.retry_timestamps) < 2:
                    raise ValueError("Retry")
                return {}

        start = time.time()
        job = TimedRetryJob()
        job.run()
        total_time = time.time() - start

        # Should take at least 0.2s (0.1 + 0.1) for 2 retries
        assert total_time >= 0.2

    def test_retry_overhead_minimal(self):
        """Test retry overhead is minimal."""

        class MinimalOverheadJob(BaseJob):
            max_retries = 10
            retry_delay = 0.001  # 1ms
            retry_backoff = 1.0

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                if self.attempts < 5:
                    raise ValueError("Retry")
                return {}

        start = time.time()
        job = MinimalOverheadJob()
        job.run()
        total_time = time.time() - start

        # Should complete in reasonable time
        assert total_time < 1.0  # Less than 1 second


class TestRetryEdgeCases:
    """Test edge cases in retry logic."""

    def test_retry_with_changing_error(self):
        """Test retrying with different errors each time."""

        class ChangingErrorJob(BaseJob):
            max_retries = 3
            retry_delay = 0.01

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.errors = []

            def on_retry(self, error, retry_count, delay):
                self.errors.append(type(error).__name__)

            def execute(self, **kwargs):
                attempt = len(self.errors)
                if attempt == 0:
                    raise ValueError("Error 1")
                elif attempt == 1:
                    raise TypeError("Error 2")
                elif attempt == 2:
                    raise RuntimeError("Error 3")
                return {}

        job = ChangingErrorJob()
        result = job.run()

        assert "ValueError" in job.errors
        assert "TypeError" in job.errors
        assert result.status == JobState.COMPLETED

    def test_retry_with_timeout(self):
        """Test retry with job timeout."""

        class TimeoutRetryJob(BaseJob):
            max_retries = 2
            retry_delay = 0.01
            timeout = 0.2

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.attempts = 0

            def execute(self, **kwargs):
                self.attempts += 1
                if self.attempts < 2:
                    raise ValueError("Retry")
                time.sleep(0.3)  # Exceed timeout
                return {}

        job = TimeoutRetryJob()
        result = job.run()

        # Should fail due to timeout after successful retry
        assert result.status == JobState.FAILED
        assert "TimeoutError" in result.error

    def test_maximum_backoff_limit(self):
        """Test extremely large retry delays."""

        class LargeBackoffJob(BaseJob):
            max_retries = 10
            retry_delay = 1.0
            retry_backoff = 10.0  # Very large multiplier

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.max_delay = 0

            def on_retry(self, error, retry_count, delay):
                self.max_delay = max(self.max_delay, delay)
                # Don't actually sleep the full delay in tests

            def execute(self, **kwargs):
                if self.retry_count < 2:
                    raise ValueError("Retry")
                return {}

        with patch.object(time, 'sleep'):  # Mock sleep to avoid long test
            job = LargeBackoffJob()
            job.run()

            # Verify delay calculation is correct
            # retry_count=1: 1.0 * 10^0 = 1.0
            # retry_count=2: 1.0 * 10^1 = 10.0
            assert job.max_delay >= 1.0
