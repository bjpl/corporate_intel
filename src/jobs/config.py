"""
Job Configuration

Provides configuration management for jobs, including default settings,
environment-based configuration, and validation.
"""

import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueueConfig:
    """Queue configuration"""
    backend: str = "celery"  # celery or rq
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    default_queue: str = "default"
    task_serializer: str = "json"
    result_serializer: str = "json"
    timezone: str = "UTC"

    @classmethod
    def from_env(cls) -> "QueueConfig":
        """Create config from environment variables"""
        return cls(
            backend=os.getenv("JOB_QUEUE_BACKEND", "celery"),
            broker_url=os.getenv("JOB_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=os.getenv("JOB_RESULT_BACKEND", "redis://localhost:6379/0"),
            default_queue=os.getenv("JOB_DEFAULT_QUEUE", "default"),
            task_serializer=os.getenv("JOB_TASK_SERIALIZER", "json"),
            result_serializer=os.getenv("JOB_RESULT_SERIALIZER", "json"),
            timezone=os.getenv("JOB_TIMEZONE", "UTC"),
        )


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_backoff: float = 2.0  # exponential multiplier
    retry_jitter: bool = True  # add randomness to retry delays

    @classmethod
    def from_env(cls) -> "RetryConfig":
        """Create config from environment variables"""
        return cls(
            max_retries=int(os.getenv("JOB_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("JOB_RETRY_DELAY", "1.0")),
            retry_backoff=float(os.getenv("JOB_RETRY_BACKOFF", "2.0")),
            retry_jitter=os.getenv("JOB_RETRY_JITTER", "true").lower() == "true",
        )


@dataclass
class MonitorConfig:
    """Monitoring configuration"""
    enabled: bool = True
    retention_days: int = 7
    metrics_interval: int = 60  # seconds
    health_check_interval: int = 30  # seconds

    @classmethod
    def from_env(cls) -> "MonitorConfig":
        """Create config from environment variables"""
        return cls(
            enabled=os.getenv("JOB_MONITOR_ENABLED", "true").lower() == "true",
            retention_days=int(os.getenv("JOB_RETENTION_DAYS", "7")),
            metrics_interval=int(os.getenv("JOB_METRICS_INTERVAL", "60")),
            health_check_interval=int(os.getenv("JOB_HEALTH_CHECK_INTERVAL", "30")),
        )


@dataclass
class SchedulerConfig:
    """Scheduler configuration"""
    enabled: bool = True
    check_interval: float = 1.0  # seconds
    timezone: str = "UTC"

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        """Create config from environment variables"""
        return cls(
            enabled=os.getenv("JOB_SCHEDULER_ENABLED", "true").lower() == "true",
            check_interval=float(os.getenv("JOB_SCHEDULER_CHECK_INTERVAL", "1.0")),
            timezone=os.getenv("JOB_SCHEDULER_TIMEZONE", "UTC"),
        )


@dataclass
class JobConfig:
    """
    Comprehensive job system configuration

    Usage:
        # From environment variables
        config = JobConfig.from_env()

        # Custom configuration
        config = JobConfig(
            queue=QueueConfig(backend="rq"),
            retry=RetryConfig(max_retries=5)
        )

        # Get specific config
        queue_config = config.queue
    """

    queue: QueueConfig = field(default_factory=QueueConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

    # Job defaults
    default_timeout: Optional[float] = None  # seconds
    default_priority: int = 5  # 1-10, 10 is highest

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def from_env(cls) -> "JobConfig":
        """
        Create configuration from environment variables

        Environment variables:
            # Queue
            JOB_QUEUE_BACKEND: Queue backend (celery/rq)
            JOB_BROKER_URL: Message broker URL
            JOB_RESULT_BACKEND: Result backend URL
            JOB_DEFAULT_QUEUE: Default queue name

            # Retry
            JOB_MAX_RETRIES: Maximum retry attempts
            JOB_RETRY_DELAY: Initial retry delay
            JOB_RETRY_BACKOFF: Retry backoff multiplier
            JOB_RETRY_JITTER: Enable retry jitter

            # Monitor
            JOB_MONITOR_ENABLED: Enable monitoring
            JOB_RETENTION_DAYS: Job history retention
            JOB_METRICS_INTERVAL: Metrics collection interval

            # Scheduler
            JOB_SCHEDULER_ENABLED: Enable scheduler
            JOB_SCHEDULER_CHECK_INTERVAL: Schedule check interval

            # Defaults
            JOB_DEFAULT_TIMEOUT: Default job timeout
            JOB_DEFAULT_PRIORITY: Default job priority
            JOB_LOG_LEVEL: Logging level
        """
        return cls(
            queue=QueueConfig.from_env(),
            retry=RetryConfig.from_env(),
            monitor=MonitorConfig.from_env(),
            scheduler=SchedulerConfig.from_env(),
            default_timeout=float(os.getenv("JOB_DEFAULT_TIMEOUT")) if os.getenv("JOB_DEFAULT_TIMEOUT") else None,
            default_priority=int(os.getenv("JOB_DEFAULT_PRIORITY", "5")),
            log_level=os.getenv("JOB_LOG_LEVEL", "INFO"),
            log_format=os.getenv("JOB_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "JobConfig":
        """Create configuration from dictionary"""
        return cls(
            queue=QueueConfig(**config_dict.get("queue", {})),
            retry=RetryConfig(**config_dict.get("retry", {})),
            monitor=MonitorConfig(**config_dict.get("monitor", {})),
            scheduler=SchedulerConfig(**config_dict.get("scheduler", {})),
            default_timeout=config_dict.get("default_timeout"),
            default_priority=config_dict.get("default_priority", 5),
            log_level=config_dict.get("log_level", "INFO"),
            log_format=config_dict.get("log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "queue": asdict(self.queue),
            "retry": asdict(self.retry),
            "monitor": asdict(self.monitor),
            "scheduler": asdict(self.scheduler),
            "default_timeout": self.default_timeout,
            "default_priority": self.default_priority,
            "log_level": self.log_level,
            "log_format": self.log_format,
        }

    def validate(self) -> bool:
        """
        Validate configuration

        Returns:
            True if valid, raises ValueError otherwise
        """
        # Validate queue backend
        if self.queue.backend not in ["celery", "rq"]:
            raise ValueError(f"Invalid queue backend: {self.queue.backend}")

        # Validate retry config
        if self.retry.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry.retry_delay <= 0:
            raise ValueError("retry_delay must be > 0")
        if self.retry.retry_backoff < 1:
            raise ValueError("retry_backoff must be >= 1")

        # Validate monitor config
        if self.monitor.retention_days < 1:
            raise ValueError("retention_days must be >= 1")
        if self.monitor.metrics_interval < 1:
            raise ValueError("metrics_interval must be >= 1")

        # Validate scheduler config
        if self.scheduler.check_interval <= 0:
            raise ValueError("check_interval must be > 0")

        # Validate priority
        if not 1 <= self.default_priority <= 10:
            raise ValueError("default_priority must be between 1 and 10")

        logger.info("Job configuration validated successfully")
        return True

    def setup_logging(self) -> None:
        """Configure logging based on config"""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=self.log_format
        )
        logger.info(f"Logging configured with level: {self.log_level}")
