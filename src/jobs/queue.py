"""
Queue Manager

Provides queue management with support for multiple backends (Celery, RQ)
and standardized interface for job queueing and execution.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timedelta

from src.jobs.base import BaseJob, JobResult, JobState

logger = logging.getLogger(__name__)


class QueueBackend(ABC):
    """Abstract base class for queue backends"""

    @abstractmethod
    def enqueue(self, job: BaseJob, queue: str = "default", **kwargs) -> str:
        """
        Enqueue a job for execution

        Args:
            job: Job instance to enqueue
            queue: Queue name
            **kwargs: Backend-specific options

        Returns:
            Task ID
        """
        pass

    @abstractmethod
    def get_status(self, task_id: str) -> JobState:
        """Get task status"""
        pass

    @abstractmethod
    def get_result(self, task_id: str) -> Optional[JobResult]:
        """Get task result"""
        pass

    @abstractmethod
    def cancel(self, task_id: str) -> bool:
        """Cancel a queued or running task"""
        pass

    @abstractmethod
    def get_queue_length(self, queue: str = "default") -> int:
        """Get number of jobs in queue"""
        pass


class CeleryQueue(QueueBackend):
    """
    Celery-based queue backend

    Requires: celery, redis
    """

    def __init__(self, broker_url: str = "redis://localhost:6379/0", **kwargs):
        """
        Initialize Celery queue

        Args:
            broker_url: Celery broker URL
            **kwargs: Additional Celery configuration
        """
        try:
            from celery import Celery

            self.app = Celery("jobs", broker=broker_url, **kwargs)
            self.app.conf.update(
                result_backend=broker_url,
                task_serializer='json',
                result_serializer='json',
                accept_content=['json'],
                timezone='UTC',
                enable_utc=True,
            )

            # Register job execution task
            @self.app.task(bind=True)
            def execute_job(task_self, job_dict: Dict[str, Any]):
                """Execute a job from serialized data"""
                from src.jobs.base import JobRegistry

                job_name = job_dict["name"]
                job_params = job_dict["params"]
                job_id = job_dict["job_id"]

                job = JobRegistry.create(job_name, job_id=job_id, **job_params)
                if not job:
                    raise ValueError(f"Unknown job type: {job_name}")

                result = job.run()
                return result.to_dict()

            self._execute_job = execute_job

        except ImportError:
            raise ImportError(
                "Celery is required for CeleryQueue. "
                "Install with: pip install celery redis"
            )

    def enqueue(self, job: BaseJob, queue: str = "default", **kwargs) -> str:
        """Enqueue job for Celery execution"""
        job_dict = {
            "name": job.get_name(),
            "params": job.params,
            "job_id": job.job_id
        }

        task = self._execute_job.apply_async(
            args=[job_dict],
            queue=queue,
            **kwargs
        )

        logger.info(f"Enqueued job {job.job_id} to queue '{queue}' (task: {task.id})")
        return task.id

    def get_status(self, task_id: str) -> JobState:
        """Get Celery task status"""
        result = self.app.AsyncResult(task_id)

        status_map = {
            "PENDING": JobState.PENDING,
            "STARTED": JobState.RUNNING,
            "SUCCESS": JobState.COMPLETED,
            "FAILURE": JobState.FAILED,
            "RETRY": JobState.RETRYING,
            "REVOKED": JobState.CANCELLED,
        }

        return status_map.get(result.status, JobState.PENDING)

    def get_result(self, task_id: str) -> Optional[JobResult]:
        """Get Celery task result"""
        result = self.app.AsyncResult(task_id)

        if result.ready():
            if result.successful():
                result_dict = result.get()
                return JobResult(
                    job_id=result_dict["job_id"],
                    status=JobState(result_dict["status"]),
                    data=result_dict.get("data"),
                    error=result_dict.get("error"),
                    started_at=datetime.fromisoformat(result_dict["started_at"]) if result_dict.get("started_at") else None,
                    completed_at=datetime.fromisoformat(result_dict["completed_at"]) if result_dict.get("completed_at") else None,
                    duration=result_dict.get("duration"),
                    metadata=result_dict.get("metadata", {})
                )
            else:
                return JobResult(
                    job_id=task_id,
                    status=JobState.FAILED,
                    error=str(result.info)
                )

        return None

    def cancel(self, task_id: str) -> bool:
        """Cancel Celery task"""
        self.app.control.revoke(task_id, terminate=True)
        logger.info(f"Cancelled task {task_id}")
        return True

    def get_queue_length(self, queue: str = "default") -> int:
        """Get Celery queue length"""
        inspect = self.app.control.inspect()
        active = inspect.active()
        scheduled = inspect.scheduled()

        length = 0
        if active:
            for worker_tasks in active.values():
                length += len([t for t in worker_tasks if t.get("delivery_info", {}).get("routing_key") == queue])
        if scheduled:
            for worker_tasks in scheduled.values():
                length += len([t for t in worker_tasks if t.get("delivery_info", {}).get("routing_key") == queue])

        return length


class RQQueue(QueueBackend):
    """
    RQ (Redis Queue) based queue backend

    Requires: rq, redis
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", **kwargs):
        """
        Initialize RQ queue

        Args:
            redis_url: Redis connection URL
            **kwargs: Additional Redis configuration
        """
        try:
            import redis
            from rq import Queue

            self.redis_conn = redis.from_url(redis_url, **kwargs)
            self._queues: Dict[str, Queue] = {}

        except ImportError:
            raise ImportError(
                "RQ is required for RQQueue. "
                "Install with: pip install rq redis"
            )

    def _get_queue(self, queue_name: str):
        """Get or create queue instance"""
        from rq import Queue

        if queue_name not in self._queues:
            self._queues[queue_name] = Queue(queue_name, connection=self.redis_conn)
        return self._queues[queue_name]

    def _execute_job(self, job_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Execute job function for RQ"""
        from src.jobs.base import JobRegistry

        job_name = job_dict["name"]
        job_params = job_dict["params"]
        job_id = job_dict["job_id"]

        job = JobRegistry.create(job_name, job_id=job_id, **job_params)
        if not job:
            raise ValueError(f"Unknown job type: {job_name}")

        result = job.run()
        return result.to_dict()

    def enqueue(self, job: BaseJob, queue: str = "default", **kwargs) -> str:
        """Enqueue job for RQ execution"""
        q = self._get_queue(queue)

        job_dict = {
            "name": job.get_name(),
            "params": job.params,
            "job_id": job.job_id
        }

        rq_job = q.enqueue(self._execute_job, job_dict, **kwargs)
        logger.info(f"Enqueued job {job.job_id} to queue '{queue}' (task: {rq_job.id})")
        return rq_job.id

    def get_status(self, task_id: str) -> JobState:
        """Get RQ job status"""
        from rq.job import Job

        try:
            rq_job = Job.fetch(task_id, connection=self.redis_conn)

            status_map = {
                "queued": JobState.PENDING,
                "started": JobState.RUNNING,
                "finished": JobState.COMPLETED,
                "failed": JobState.FAILED,
                "stopped": JobState.CANCELLED,
            }

            return status_map.get(rq_job.get_status(), JobState.PENDING)
        except Exception:
            return JobState.PENDING

    def get_result(self, task_id: str) -> Optional[JobResult]:
        """Get RQ job result"""
        from rq.job import Job

        try:
            rq_job = Job.fetch(task_id, connection=self.redis_conn)

            if rq_job.is_finished:
                result_dict = rq_job.result
                return JobResult(
                    job_id=result_dict["job_id"],
                    status=JobState(result_dict["status"]),
                    data=result_dict.get("data"),
                    error=result_dict.get("error"),
                    started_at=datetime.fromisoformat(result_dict["started_at"]) if result_dict.get("started_at") else None,
                    completed_at=datetime.fromisoformat(result_dict["completed_at"]) if result_dict.get("completed_at") else None,
                    duration=result_dict.get("duration"),
                    metadata=result_dict.get("metadata", {})
                )
            elif rq_job.is_failed:
                return JobResult(
                    job_id=task_id,
                    status=JobState.FAILED,
                    error=str(rq_job.exc_info)
                )
        except Exception as e:
            logger.error(f"Error fetching RQ job result: {e}")

        return None

    def cancel(self, task_id: str) -> bool:
        """Cancel RQ job"""
        from rq.job import Job

        try:
            rq_job = Job.fetch(task_id, connection=self.redis_conn)
            rq_job.cancel()
            logger.info(f"Cancelled job {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return False

    def get_queue_length(self, queue: str = "default") -> int:
        """Get RQ queue length"""
        q = self._get_queue(queue)
        return len(q)


class QueueManager:
    """
    Unified queue manager supporting multiple backends

    Usage:
        # Using Celery
        manager = QueueManager(backend="celery", broker_url="redis://localhost:6379/0")

        # Using RQ
        manager = QueueManager(backend="rq", redis_url="redis://localhost:6379/0")

        # Enqueue job
        job = MyJob(param1="value1")
        task_id = manager.enqueue(job, queue="high_priority")

        # Check status
        status = manager.get_status(task_id)

        # Get result
        result = manager.get_result(task_id)
    """

    def __init__(self, backend: str = "celery", **kwargs):
        """
        Initialize queue manager

        Args:
            backend: Backend type ("celery" or "rq")
            **kwargs: Backend-specific configuration
        """
        backends = {
            "celery": CeleryQueue,
            "rq": RQQueue,
        }

        if backend not in backends:
            raise ValueError(f"Unknown backend: {backend}. Choose from: {list(backends.keys())}")

        self.backend_type = backend
        self.backend: QueueBackend = backends[backend](**kwargs)
        logger.info(f"Initialized QueueManager with {backend} backend")

    def enqueue(self, job: BaseJob, queue: str = "default", **kwargs) -> str:
        """Enqueue a job"""
        return self.backend.enqueue(job, queue, **kwargs)

    def get_status(self, task_id: str) -> JobState:
        """Get job status"""
        return self.backend.get_status(task_id)

    def get_result(self, task_id: str) -> Optional[JobResult]:
        """Get job result"""
        return self.backend.get_result(task_id)

    def cancel(self, task_id: str) -> bool:
        """Cancel a job"""
        return self.backend.cancel(task_id)

    def get_queue_length(self, queue: str = "default") -> int:
        """Get queue length"""
        return self.backend.get_queue_length(queue)

    def wait_for_result(
        self,
        task_id: str,
        timeout: float = 60.0,
        poll_interval: float = 0.5
    ) -> Optional[JobResult]:
        """
        Wait for job result with timeout

        Args:
            task_id: Task identifier
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            JobResult or None if timeout
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self.get_result(task_id)
            if result:
                return result
            time.sleep(poll_interval)

        logger.warning(f"Timeout waiting for result of task {task_id}")
        return None
