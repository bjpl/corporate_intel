"""
Tests for job configuration
"""

import pytest
import os

from src.jobs.config import (
    JobConfig,
    QueueConfig,
    RetryConfig,
    MonitorConfig,
    SchedulerConfig
)


class TestJobConfig:
    """Test JobConfig class"""

    def test_default_config(self):
        """Test default configuration"""
        config = JobConfig()

        assert config.queue.backend == "celery"
        assert config.retry.max_retries == 3
        assert config.monitor.enabled is True
        assert config.scheduler.enabled is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = JobConfig(
            queue=QueueConfig(backend="rq"),
            retry=RetryConfig(max_retries=5),
            default_priority=8
        )

        assert config.queue.backend == "rq"
        assert config.retry.max_retries == 5
        assert config.default_priority == 8

    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment"""
        monkeypatch.setenv("JOB_QUEUE_BACKEND", "rq")
        monkeypatch.setenv("JOB_MAX_RETRIES", "5")
        monkeypatch.setenv("JOB_DEFAULT_PRIORITY", "7")
        monkeypatch.setenv("JOB_LOG_LEVEL", "DEBUG")

        config = JobConfig.from_env()

        assert config.queue.backend == "rq"
        assert config.retry.max_retries == 5
        assert config.default_priority == 7
        assert config.log_level == "DEBUG"

    def test_config_to_dict(self):
        """Test configuration serialization"""
        config = JobConfig(default_priority=6)
        config_dict = config.to_dict()

        assert "queue" in config_dict
        assert "retry" in config_dict
        assert "monitor" in config_dict
        assert "scheduler" in config_dict
        assert config_dict["default_priority"] == 6

    def test_config_from_dict(self):
        """Test configuration from dictionary"""
        config_dict = {
            "queue": {"backend": "rq"},
            "retry": {"max_retries": 5},
            "default_priority": 7
        }

        config = JobConfig.from_dict(config_dict)

        assert config.queue.backend == "rq"
        assert config.retry.max_retries == 5
        assert config.default_priority == 7

    def test_config_validation_success(self):
        """Test successful configuration validation"""
        config = JobConfig()

        assert config.validate() is True

    def test_config_validation_invalid_backend(self):
        """Test validation with invalid backend"""
        config = JobConfig(queue=QueueConfig(backend="invalid"))

        with pytest.raises(ValueError, match="Invalid queue backend"):
            config.validate()

    def test_config_validation_invalid_retries(self):
        """Test validation with invalid retries"""
        config = JobConfig(retry=RetryConfig(max_retries=-1))

        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            config.validate()

    def test_config_validation_invalid_priority(self):
        """Test validation with invalid priority"""
        config = JobConfig(default_priority=15)

        with pytest.raises(ValueError, match="default_priority must be between"):
            config.validate()


class TestQueueConfig:
    """Test QueueConfig class"""

    def test_default_queue_config(self):
        """Test default queue configuration"""
        config = QueueConfig()

        assert config.backend == "celery"
        assert config.broker_url == "redis://localhost:6379/0"
        assert config.default_queue == "default"

    def test_queue_config_from_env(self, monkeypatch):
        """Test queue configuration from environment"""
        monkeypatch.setenv("JOB_QUEUE_BACKEND", "rq")
        monkeypatch.setenv("JOB_BROKER_URL", "redis://custom:6379/1")
        monkeypatch.setenv("JOB_DEFAULT_QUEUE", "custom_queue")

        config = QueueConfig.from_env()

        assert config.backend == "rq"
        assert config.broker_url == "redis://custom:6379/1"
        assert config.default_queue == "custom_queue"


class TestRetryConfig:
    """Test RetryConfig class"""

    def test_default_retry_config(self):
        """Test default retry configuration"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_backoff == 2.0
        assert config.retry_jitter is True

    def test_retry_config_from_env(self, monkeypatch):
        """Test retry configuration from environment"""
        monkeypatch.setenv("JOB_MAX_RETRIES", "5")
        monkeypatch.setenv("JOB_RETRY_DELAY", "2.5")
        monkeypatch.setenv("JOB_RETRY_BACKOFF", "3.0")
        monkeypatch.setenv("JOB_RETRY_JITTER", "false")

        config = RetryConfig.from_env()

        assert config.max_retries == 5
        assert config.retry_delay == 2.5
        assert config.retry_backoff == 3.0
        assert config.retry_jitter is False


class TestMonitorConfig:
    """Test MonitorConfig class"""

    def test_default_monitor_config(self):
        """Test default monitor configuration"""
        config = MonitorConfig()

        assert config.enabled is True
        assert config.retention_days == 7
        assert config.metrics_interval == 60

    def test_monitor_config_from_env(self, monkeypatch):
        """Test monitor configuration from environment"""
        monkeypatch.setenv("JOB_MONITOR_ENABLED", "false")
        monkeypatch.setenv("JOB_RETENTION_DAYS", "14")

        config = MonitorConfig.from_env()

        assert config.enabled is False
        assert config.retention_days == 14


class TestSchedulerConfig:
    """Test SchedulerConfig class"""

    def test_default_scheduler_config(self):
        """Test default scheduler configuration"""
        config = SchedulerConfig()

        assert config.enabled is True
        assert config.check_interval == 1.0
        assert config.timezone == "UTC"

    def test_scheduler_config_from_env(self, monkeypatch):
        """Test scheduler configuration from environment"""
        monkeypatch.setenv("JOB_SCHEDULER_ENABLED", "false")
        monkeypatch.setenv("JOB_SCHEDULER_CHECK_INTERVAL", "2.0")
        monkeypatch.setenv("JOB_SCHEDULER_TIMEZONE", "America/New_York")

        config = SchedulerConfig.from_env()

        assert config.enabled is False
        assert config.check_interval == 2.0
        assert config.timezone == "America/New_York"
