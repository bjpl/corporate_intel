"""
Base Job Framework

Provides the core job abstraction with lifecycle hooks, state management,
and job registry for all data pipeline jobs.
"""

import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import uuid4


class JobState(Enum):
    """Job execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobResult:
    """Container for job execution results"""

    def __init__(
        self,
        job_id: str,
        status: JobState,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id
        self.status = status
        self.data = data or {}
        self.error = error
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration = duration
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "metadata": self.metadata
        }


class BaseJob(ABC):
    """
    Base class for all jobs in the orchestration system.

    Provides:
    - Lifecycle hooks (on_start, on_success, on_failure, on_retry)
    - State management
    - Retry logic with exponential backoff
    - Result storage
    - Metrics collection
    """

    # Job configuration
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_backoff: float = 2.0  # exponential multiplier
    timeout: Optional[float] = None  # seconds

    def __init__(self, job_id: Optional[str] = None, **kwargs):
        """
        Initialize job instance

        Args:
            job_id: Unique job identifier (auto-generated if not provided)
            **kwargs: Job-specific parameters
        """
        self.job_id = job_id or str(uuid4())
        self.params = kwargs
        self.state = JobState.PENDING
        self.retry_count = 0
        self.result: Optional[JobResult] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self._metadata: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the job's main logic.

        This method must be implemented by all job subclasses.

        Args:
            **kwargs: Job execution parameters

        Returns:
            Dict containing job execution results

        Raises:
            Exception: Any error during job execution
        """
        pass

    def run(self) -> JobResult:
        """
        Run the job with full lifecycle management.

        Returns:
            JobResult: Job execution result
        """
        try:
            # Start job
            self.state = JobState.RUNNING
            self.started_at = datetime.utcnow()
            self.on_start()

            # Execute job with timeout if configured
            start_time = time.time()
            data = self.execute(**self.params)
            duration = time.time() - start_time

            # Check timeout
            if self.timeout and duration > self.timeout:
                raise TimeoutError(f"Job exceeded timeout of {self.timeout}s")

            # Job succeeded
            self.state = JobState.COMPLETED
            self.completed_at = datetime.utcnow()
            self.result = JobResult(
                job_id=self.job_id,
                status=JobState.COMPLETED,
                data=data,
                started_at=self.started_at,
                completed_at=self.completed_at,
                duration=duration,
                metadata=self._metadata
            )
            self.on_success(self.result)
            return self.result

        except Exception as e:
            # Job failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            error_trace = traceback.format_exc()

            # Check if we should retry
            if self.retry_count < self.max_retries:
                self.state = JobState.RETRYING
                self.retry_count += 1
                delay = self.retry_delay * (self.retry_backoff ** (self.retry_count - 1))

                self.on_retry(e, self.retry_count, delay)
                time.sleep(delay)
                return self.run()  # Retry

            # Max retries exceeded
            self.state = JobState.FAILED
            self.completed_at = datetime.utcnow()
            duration = time.time() - start_time if 'start_time' in locals() else None

            self.result = JobResult(
                job_id=self.job_id,
                status=JobState.FAILED,
                error=error_msg,
                started_at=self.started_at,
                completed_at=self.completed_at,
                duration=duration,
                metadata={**self._metadata, "error_trace": error_trace}
            )
            self.on_failure(e, self.result)
            return self.result

    # Lifecycle hooks (can be overridden by subclasses)

    def on_start(self) -> None:
        """Called when job starts executing"""
        pass

    def on_success(self, result: JobResult) -> None:
        """Called when job completes successfully"""
        pass

    def on_failure(self, error: Exception, result: JobResult) -> None:
        """Called when job fails after all retries"""
        pass

    def on_retry(self, error: Exception, retry_count: int, delay: float) -> None:
        """Called when job is being retried"""
        pass

    # Metadata management

    def set_metadata(self, key: str, value: Any) -> None:
        """Set job metadata"""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get job metadata"""
        return self._metadata.get(key, default)

    # Job information

    def get_name(self) -> str:
        """Get job name (class name by default)"""
        return self.__class__.__name__

    def get_description(self) -> str:
        """Get job description"""
        return self.__doc__ or "No description available"

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary representation"""
        return {
            "job_id": self.job_id,
            "name": self.get_name(),
            "state": self.state.value,
            "params": self.params,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self._metadata,
            "result": self.result.to_dict() if self.result else None
        }


class JobRegistry:
    """
    Registry for managing job types and instances.

    Provides:
    - Job type registration via decorator
    - Job instantiation by name
    - Job type discovery
    """

    _jobs: Dict[str, Type[BaseJob]] = {}

    @classmethod
    def register(cls, name: Optional[str] = None) -> Callable:
        """
        Decorator to register a job type.

        Usage:
            @JobRegistry.register()
            class MyJob(BaseJob):
                pass

            @JobRegistry.register("custom_name")
            class AnotherJob(BaseJob):
                pass

        Args:
            name: Optional custom name for the job (uses class name if not provided)

        Returns:
            Decorator function
        """
        def decorator(job_class: Type[BaseJob]) -> Type[BaseJob]:
            job_name = name or job_class.__name__
            cls._jobs[job_name] = job_class
            return job_class
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseJob]]:
        """Get a registered job type by name"""
        return cls._jobs.get(name)

    @classmethod
    def create(cls, name: str, **kwargs) -> Optional[BaseJob]:
        """Create a job instance by name"""
        job_class = cls.get(name)
        if job_class:
            return job_class(**kwargs)
        return None

    @classmethod
    def list_jobs(cls) -> List[str]:
        """List all registered job names"""
        return list(cls._jobs.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered jobs (useful for testing)"""
        cls._jobs.clear()
