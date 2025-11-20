# Job Orchestration System Guide

## Overview

The job orchestration system provides a comprehensive framework for managing data pipeline jobs with:

- **Base Job Framework**: Extensible job abstraction with lifecycle hooks
- **Queue Management**: Support for Celery and RQ backends
- **Job Scheduling**: Cron-based and interval scheduling
- **Monitoring**: Real-time metrics, progress tracking, and health checks
- **Retry Logic**: Exponential backoff with configurable retries
- **Job Types**: Pre-built jobs for ingestion, processing, and analysis

## Quick Start

### 1. Installation

```bash
# Install required dependencies
pip install celery redis  # For Celery backend
# OR
pip install rq redis     # For RQ backend

# Optional dependencies
pip install croniter     # For cron scheduling
pip install sqlalchemy   # For database ingestion
pip install pandas       # For file ingestion
pip install requests     # For API ingestion
```

### 2. Basic Usage

```python
from src.jobs.base import BaseJob, JobRegistry
from src.jobs.queue import QueueManager
from src.jobs.config import JobConfig

# Create custom job
@JobRegistry.register()
class MyJob(BaseJob):
    def execute(self, **kwargs):
        # Your job logic here
        data = kwargs.get("data", [])
        result = process_data(data)
        return {"result": result}

# Initialize queue manager
config = JobConfig.from_env()
queue_manager = QueueManager(
    backend="celery",
    broker_url="redis://localhost:6379/0"
)

# Create and enqueue job
job = MyJob(data=[1, 2, 3])
task_id = queue_manager.enqueue(job, queue="default")

# Check status
status = queue_manager.get_status(task_id)
result = queue_manager.get_result(task_id)
```

## Creating Custom Jobs

### Basic Job

```python
from src.jobs.base import BaseJob, JobRegistry

@JobRegistry.register("my_custom_job")
class MyCustomJob(BaseJob):
    # Configuration
    max_retries = 3
    retry_delay = 2.0
    retry_backoff = 2.0
    timeout = 300.0

    def execute(self, **kwargs):
        """Main job logic"""
        # Process data
        data = kwargs.get("data")
        result = self.process(data)

        # Update progress
        self.set_metadata("progress", 50)

        return {"result": result}

    def on_start(self):
        """Called when job starts"""
        print(f"Starting job {self.job_id}")

    def on_success(self, result):
        """Called on success"""
        print(f"Job completed: {result.data}")

    def on_failure(self, error, result):
        """Called on failure"""
        print(f"Job failed: {error}")

    def on_retry(self, error, retry_count, delay):
        """Called on retry"""
        print(f"Retrying ({retry_count}): {error}")
```

### Job with External Services

```python
@JobRegistry.register()
class APIDataJob(BaseJob):
    max_retries = 5
    timeout = 600.0

    def execute(self, **kwargs):
        import requests

        url = kwargs.get("url")
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        # Store in database
        self.save_to_db(data)

        return {
            "records_saved": len(data),
            "source": url
        }
```

## Job Scheduling

### Interval-Based Scheduling

```python
from datetime import timedelta
from src.jobs.scheduler import JobScheduler

scheduler = JobScheduler(queue_manager)

# Run every hour
scheduler.add_schedule(
    schedule_id="hourly-sync",
    job_name="MyJob",
    job_params={"source": "api"},
    interval=timedelta(hours=1),
    queue="default"
)

scheduler.start()
```

### Cron-Based Scheduling

```python
# Run at specific times using cron expressions
scheduler.add_schedule(
    schedule_id="daily-report",
    job_name="ReportJob",
    job_params={},
    cron="0 9 * * *",  # Every day at 9 AM
    queue="reports"
)

# Every Monday at 3 AM
scheduler.add_schedule(
    schedule_id="weekly-cleanup",
    job_name="CleanupJob",
    job_params={},
    cron="0 3 * * 1",
    queue="maintenance"
)
```

### One-Time Scheduling

```python
# Run at specific time
scheduler.add_schedule(
    schedule_id="morning-job",
    job_name="MyJob",
    job_params={},
    at_time="06:00",  # Every day at 6 AM
    queue="default"
)

# Manually trigger schedule
task_id = scheduler.run_once("morning-job")
```

## Job Monitoring

### Basic Monitoring

```python
from src.jobs.monitor import JobMonitor

monitor = JobMonitor()

# Track job lifecycle
monitor.track_job_start(job)
result = job.run()
monitor.track_job_complete(job, result)

# Get job status
status = monitor.get_job_status(job.job_id)

# Update progress
monitor.update_job_progress(job.job_id, 75.0, "Processing batch 3/4")
```

### Metrics and Analytics

```python
# Get overall metrics
metrics = monitor.get_metrics()

print(f"Total jobs: {metrics.total_jobs}")
print(f"Success rate: {metrics.success_rate}%")
print(f"Average duration: {metrics.avg_duration}s")

# Get metrics for specific job type
job_metrics = monitor.get_metrics(job_type="MyJob")

# Get failed jobs
failed = monitor.get_failed_jobs(since=datetime.utcnow() - timedelta(hours=24))

# Get running jobs
running = monitor.get_running_jobs()
```

### Health Checks

```python
# Get system health
health = monitor.get_health_status()

if health["status"] == "healthy":
    print("System operational")
else:
    print(f"System degraded: {health['warnings']}")
```

## Pre-Built Job Types

### 1. API Ingestion

```python
from src.jobs.ingestion import APIIngestionJob

job = APIIngestionJob(
    url="https://api.example.com/data",
    method="GET",
    headers={"Authorization": "Bearer token"},
    rate_limit=10,  # 10 requests/second
    pagination={
        "page_param": "page",
        "page_size_param": "limit",
        "page_size": 100,
        "data_key": "results",
        "has_more_key": "has_more"
    },
    max_pages=50
)

task_id = queue_manager.enqueue(job)
```

### 2. Database Ingestion

```python
from src.jobs.ingestion import DatabaseIngestionJob

job = DatabaseIngestionJob(
    connection_string="postgresql://user:pass@localhost/db",
    query="SELECT * FROM users WHERE created_at > :since",
    params={"since": "2024-01-01"},
    batch_size=1000
)

# Or use table-based query
job = DatabaseIngestionJob(
    connection_string="postgresql://user:pass@localhost/db",
    table="users",
    where_clause="active = true",
    batch_size=1000
)
```

### 3. File Ingestion

```python
from src.jobs.ingestion import FileIngestionJob

# CSV file
job = FileIngestionJob(
    file_path="/data/file.csv",
    file_type="csv",
    delimiter=",",
    encoding="utf-8"
)

# JSON file
job = FileIngestionJob(
    file_path="/data/file.json",
    file_type="json"
)

# Excel file
job = FileIngestionJob(
    file_path="/data/file.xlsx",
    file_type="excel",
    sheet_name="Sheet1"
)
```

### 4. Data Transformation

```python
from src.jobs.processing import DataTransformJob

# Using named transformations
job = DataTransformJob(
    data=records,
    transformations=[
        {
            "type": "rename",
            "mapping": {"old_name": "new_name"}
        },
        {
            "type": "convert",
            "conversions": {"age": "int", "price": "float"}
        },
        {
            "type": "default",
            "defaults": {"status": "active", "count": 0}
        }
    ],
    batch_size=1000
)

# Using custom functions
def custom_transform(record):
    record["full_name"] = f"{record['first_name']} {record['last_name']}"
    return record

job = DataTransformJob(
    data=records,
    transformations=[custom_transform]
)
```

### 5. Data Aggregation

```python
from src.jobs.processing import DataAggregationJob

job = DataAggregationJob(
    data=records,
    group_by=["category", "region"],
    aggregations={
        "sales": "sum",
        "orders": "count",
        "price": "avg",
        "quantity": "max"
    }
)
```

### 6. Data Validation

```python
from src.jobs.processing import DataValidationJob

# Define schema
schema = {
    "email": {
        "required": True,
        "type": "string",
        "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"
    },
    "age": {
        "required": True,
        "type": "int",
        "min": 0,
        "max": 150
    },
    "status": {
        "required": True,
        "type": "string",
        "enum": ["active", "inactive", "pending"]
    }
}

# Custom validation rules
def check_unique_id(record):
    return record.get("id") not in seen_ids

job = DataValidationJob(
    data=records,
    schema=schema,
    rules=[check_unique_id],
    strict=False  # Continue on errors
)
```

### 7. Statistical Analysis

```python
from src.jobs.analysis import StatisticalAnalysisJob

job = StatisticalAnalysisJob(
    data=records,
    metrics=["mean", "median", "std", "min", "max", "count"]
)
```

### 8. Report Generation

```python
from src.jobs.analysis import ReportGenerationJob

job = ReportGenerationJob(
    data=analysis_results,
    title="Monthly Sales Report",
    format="html",  # or "json", "markdown"
    sections=[
        {
            "title": "Summary",
            "data_key": "summary"
        },
        {
            "title": "Details",
            "data_key": "details"
        }
    ]
)
```

## Configuration

### Environment Variables

```bash
# Queue configuration
export JOB_QUEUE_BACKEND=celery  # or "rq"
export JOB_BROKER_URL=redis://localhost:6379/0
export JOB_DEFAULT_QUEUE=default

# Retry configuration
export JOB_MAX_RETRIES=3
export JOB_RETRY_DELAY=1.0
export JOB_RETRY_BACKOFF=2.0

# Monitor configuration
export JOB_MONITOR_ENABLED=true
export JOB_RETENTION_DAYS=7

# Scheduler configuration
export JOB_SCHEDULER_ENABLED=true
export JOB_SCHEDULER_CHECK_INTERVAL=1.0

# Defaults
export JOB_DEFAULT_TIMEOUT=600
export JOB_DEFAULT_PRIORITY=5
export JOB_LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from src.jobs.config import JobConfig, QueueConfig, RetryConfig

config = JobConfig(
    queue=QueueConfig(
        backend="celery",
        broker_url="redis://localhost:6379/0"
    ),
    retry=RetryConfig(
        max_retries=5,
        retry_delay=2.0,
        retry_backoff=2.5
    ),
    default_timeout=300.0,
    default_priority=7,
    log_level="DEBUG"
)

# Validate configuration
config.validate()

# Setup logging
config.setup_logging()
```

## Best Practices

### 1. Job Design

- Keep jobs focused on a single responsibility
- Make jobs idempotent (safe to retry)
- Use timeouts for long-running jobs
- Implement proper error handling
- Log important events and errors

### 2. Queue Management

- Use separate queues for different priorities
- Monitor queue lengths
- Scale workers based on load
- Use dead letter queues for failed jobs

### 3. Monitoring

- Track all job executions
- Set up alerts for high failure rates
- Monitor job durations
- Clean up old job history regularly

### 4. Scheduling

- Use cron for predictable schedules
- Use intervals for recurring jobs
- Disable schedules during maintenance
- Test schedules before deployment

### 5. Error Handling

- Configure appropriate retry counts
- Use exponential backoff
- Log detailed error information
- Implement failure notifications

## Complete Example

```python
from datetime import timedelta
from src.jobs.base import JobRegistry
from src.jobs.queue import QueueManager
from src.jobs.scheduler import JobScheduler
from src.jobs.monitor import JobMonitor
from src.jobs.config import JobConfig
from src.jobs.ingestion import APIIngestionJob
from src.jobs.processing import DataTransformJob, DataValidationJob

# Initialize system
config = JobConfig.from_env()
queue_manager = QueueManager(backend="celery")
scheduler = JobScheduler(queue_manager)
monitor = JobMonitor()

# Register custom job
@JobRegistry.register()
class ProcessUserDataJob(BaseJob):
    max_retries = 3
    timeout = 600.0

    def execute(self, **kwargs):
        # Ingest from API
        api_job = APIIngestionJob(url=kwargs["api_url"])
        api_result = api_job.run()

        # Transform data
        transform_job = DataTransformJob(
            data=api_result.data["records"],
            transformations=[
                {"type": "default", "defaults": {"processed": True}}
            ]
        )
        transform_result = transform_job.run()

        # Validate
        validate_job = DataValidationJob(
            data=transform_result.data["records"],
            schema={
                "email": {"required": True, "type": "string"},
                "age": {"required": True, "type": "int", "min": 0}
            }
        )
        validate_result = validate_job.run()

        return {
            "ingested": api_result.data["total_records"],
            "transformed": transform_result.data["total_records"],
            "valid": validate_result.data["total_valid"],
            "invalid": validate_result.data["total_invalid"]
        }

# Schedule job
scheduler.add_schedule(
    schedule_id="daily-user-sync",
    job_name="ProcessUserDataJob",
    job_params={"api_url": "https://api.example.com/users"},
    cron="0 2 * * *",  # Daily at 2 AM
    queue="data-processing"
)

# Start scheduler
scheduler.start()

# Monitor jobs
metrics = monitor.get_metrics()
print(f"Success rate: {metrics.success_rate}%")
```

## Troubleshooting

### Jobs Not Processing

1. Check Redis connection
2. Verify worker is running
3. Check queue names match
4. Review worker logs

### High Failure Rate

1. Check error logs
2. Verify external service availability
3. Review timeout settings
4. Check retry configuration

### Performance Issues

1. Monitor queue lengths
2. Scale workers horizontally
3. Optimize job execution time
4. Use batch processing
5. Implement caching

## API Reference

See individual module documentation:
- `/src/jobs/base.py` - Base job framework
- `/src/jobs/queue.py` - Queue management
- `/src/jobs/scheduler.py` - Job scheduling
- `/src/jobs/monitor.py` - Job monitoring
- `/src/jobs/config.py` - Configuration management
