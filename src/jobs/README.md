# Job Orchestration System

Production-ready job orchestration framework for data pipelines with comprehensive monitoring, scheduling, and error handling.

## Features

- **Base Job Framework**: Extensible job abstraction with lifecycle hooks
- **Queue Management**: Support for Celery and RQ backends
- **Job Scheduling**: Cron-based and interval-based scheduling
- **Monitoring & Metrics**: Real-time job tracking, metrics collection, and health checks
- **Retry Logic**: Exponential backoff with configurable retry policies
- **Job Types**: Pre-built jobs for data ingestion, processing, and analysis
- **Configuration**: Environment-based and programmatic configuration
- **Observability**: Comprehensive logging, progress tracking, and error reporting

## Quick Start

### Installation

```bash
# Core dependencies
pip install celery redis  # For Celery backend
# OR
pip install rq redis      # For RQ backend

# Optional dependencies for job types
pip install pandas sqlalchemy requests croniter
```

### Basic Example

```python
from src.jobs.base import BaseJob, JobRegistry
from src.jobs.queue import QueueManager

# Define custom job
@JobRegistry.register()
class MyDataJob(BaseJob):
    max_retries = 3
    timeout = 300.0

    def execute(self, **kwargs):
        data = kwargs.get("data", [])
        # Process data
        result = self.process_data(data)
        return {"processed": len(result), "data": result}

# Initialize queue
queue = QueueManager(backend="celery", broker_url="redis://localhost:6379/0")

# Create and enqueue job
job = MyDataJob(data=[1, 2, 3, 4, 5])
task_id = queue.enqueue(job)

# Check status
status = queue.get_status(task_id)
result = queue.get_result(task_id)
```

## Architecture

```
src/jobs/
├── __init__.py           # Package exports
├── base.py               # BaseJob, JobRegistry, JobState
├── queue.py              # QueueManager, CeleryQueue, RQQueue
├── scheduler.py          # JobScheduler, Schedule
├── monitor.py            # JobMonitor, JobMetrics
├── config.py             # JobConfig, configuration management
├── ingestion/            # Data ingestion jobs
│   ├── api_ingestion.py
│   ├── database_ingestion.py
│   └── file_ingestion.py
├── processing/           # Data processing jobs
│   ├── transform.py
│   ├── aggregation.py
│   └── validation.py
└── analysis/             # Data analysis jobs
    ├── statistical.py
    └── reporting.py
```

## Core Components

### 1. BaseJob

All jobs inherit from `BaseJob` and implement the `execute()` method:

```python
from src.jobs.base import BaseJob, JobRegistry

@JobRegistry.register()
class ProcessDataJob(BaseJob):
    # Configuration
    max_retries = 3
    retry_delay = 1.0
    retry_backoff = 2.0
    timeout = 600.0

    def execute(self, **kwargs):
        """Main job logic"""
        data = kwargs.get("data")
        # Process data
        return {"result": processed_data}

    # Lifecycle hooks (optional)
    def on_start(self):
        """Called when job starts"""
        pass

    def on_success(self, result):
        """Called on successful completion"""
        pass

    def on_failure(self, error, result):
        """Called on failure after all retries"""
        pass

    def on_retry(self, error, retry_count, delay):
        """Called before each retry"""
        pass
```

### 2. Queue Manager

Manage job execution with pluggable queue backends:

```python
from src.jobs.queue import QueueManager

# Celery backend
queue = QueueManager(
    backend="celery",
    broker_url="redis://localhost:6379/0"
)

# RQ backend
queue = QueueManager(
    backend="rq",
    redis_url="redis://localhost:6379/0"
)

# Enqueue job
task_id = queue.enqueue(job, queue="high_priority")

# Monitor
status = queue.get_status(task_id)
result = queue.get_result(task_id)
queue.cancel(task_id)
```

### 3. Job Scheduler

Schedule jobs with cron or interval-based triggers:

```python
from datetime import timedelta
from src.jobs.scheduler import JobScheduler

scheduler = JobScheduler(queue_manager)

# Interval-based
scheduler.add_schedule(
    "hourly-sync",
    job_name="DataSyncJob",
    job_params={"source": "api"},
    interval=timedelta(hours=1)
)

# Cron-based
scheduler.add_schedule(
    "daily-report",
    job_name="ReportJob",
    job_params={},
    cron="0 9 * * *"  # 9 AM daily
)

scheduler.start()
```

### 4. Job Monitor

Track job execution and collect metrics:

```python
from src.jobs.monitor import JobMonitor

monitor = JobMonitor()

# Track jobs
monitor.track_job_start(job)
result = job.run()
monitor.track_job_complete(job, result)

# Get metrics
metrics = monitor.get_metrics()
print(f"Success rate: {metrics.success_rate}%")
print(f"Average duration: {metrics.avg_duration}s")

# Health check
health = monitor.get_health_status()
```

## Pre-Built Job Types

### Data Ingestion

**API Ingestion:**
```python
from src.jobs.ingestion import APIIngestionJob

job = APIIngestionJob(
    url="https://api.example.com/data",
    method="GET",
    rate_limit=10,
    pagination={"page_param": "page", "page_size": 100}
)
```

**Database Ingestion:**
```python
from src.jobs.ingestion import DatabaseIngestionJob

job = DatabaseIngestionJob(
    connection_string="postgresql://user:pass@localhost/db",
    query="SELECT * FROM users WHERE active = true",
    batch_size=1000
)
```

**File Ingestion:**
```python
from src.jobs.ingestion import FileIngestionJob

job = FileIngestionJob(
    file_path="/data/file.csv",
    file_type="csv",
    delimiter=","
)
```

### Data Processing

**Transform:**
```python
from src.jobs.processing import DataTransformJob

job = DataTransformJob(
    data=records,
    transformations=[
        {"type": "rename", "mapping": {"old": "new"}},
        {"type": "convert", "conversions": {"age": "int"}},
        {"type": "default", "defaults": {"status": "active"}}
    ]
)
```

**Aggregation:**
```python
from src.jobs.processing import DataAggregationJob

job = DataAggregationJob(
    data=records,
    group_by=["category"],
    aggregations={"sales": "sum", "orders": "count"}
)
```

**Validation:**
```python
from src.jobs.processing import DataValidationJob

job = DataValidationJob(
    data=records,
    schema={
        "email": {"required": True, "type": "string"},
        "age": {"required": True, "type": "int", "min": 0}
    }
)
```

### Data Analysis

**Statistical Analysis:**
```python
from src.jobs.analysis import StatisticalAnalysisJob

job = StatisticalAnalysisJob(
    data=records,
    metrics=["mean", "median", "std", "min", "max"]
)
```

**Report Generation:**
```python
from src.jobs.analysis import ReportGenerationJob

job = ReportGenerationJob(
    data=results,
    title="Monthly Report",
    format="html"
)
```

## Configuration

### Environment Variables

```bash
# Queue
JOB_QUEUE_BACKEND=celery
JOB_BROKER_URL=redis://localhost:6379/0
JOB_DEFAULT_QUEUE=default

# Retry
JOB_MAX_RETRIES=3
JOB_RETRY_DELAY=1.0
JOB_RETRY_BACKOFF=2.0

# Monitor
JOB_MONITOR_ENABLED=true
JOB_RETENTION_DAYS=7

# Scheduler
JOB_SCHEDULER_ENABLED=true
```

### Programmatic

```python
from src.jobs.config import JobConfig

config = JobConfig.from_env()
config.validate()
config.setup_logging()
```

## Testing

Run the test suite:

```bash
pytest tests/jobs/
```

## Documentation

See `/docs/job-orchestration-guide.md` for comprehensive documentation.

## Best Practices

1. **Make jobs idempotent** - Safe to retry
2. **Use timeouts** - Prevent hanging jobs
3. **Implement proper error handling** - Catch and log errors
4. **Monitor everything** - Track all executions
5. **Use separate queues** - Prioritize workloads
6. **Clean up resources** - In lifecycle hooks
7. **Test thoroughly** - Unit and integration tests

## License

See project LICENSE file.
