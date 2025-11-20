"""
Database Ingestion Job

Ingests data from databases with support for various database engines.
"""

from typing import Any, Dict, List, Optional
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("database_ingestion")
class DatabaseIngestionJob(BaseJob):
    """
    Ingest data from databases

    Parameters:
        connection_string: Database connection string
        query: SQL query to execute
        params: Query parameters
        batch_size: Number of rows to fetch at once
        table: Table name (alternative to query)
        where_clause: WHERE clause for table queries
    """

    max_retries = 3
    retry_delay = 5.0
    retry_backoff = 2.0
    timeout = 600.0  # 10 minutes

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute database ingestion"""
        connection_string = kwargs.get("connection_string")
        query = kwargs.get("query")
        params = kwargs.get("params", {})
        batch_size = kwargs.get("batch_size", 1000)
        table = kwargs.get("table")
        where_clause = kwargs.get("where_clause")

        if not connection_string:
            raise ValueError("connection_string is required")

        if not query and not table:
            raise ValueError("Either query or table must be provided")

        # Build query if table is provided
        if table and not query:
            query = f"SELECT * FROM {table}"
            if where_clause:
                query += f" WHERE {where_clause}"

        self.set_metadata("query", query)
        self.set_metadata("database", connection_string.split("://")[0])

        # Import SQLAlchemy (lazy import)
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            raise ImportError(
                "SQLAlchemy required. Install with: pip install sqlalchemy"
            )

        logger.info(f"Starting database ingestion")

        # Create database connection
        engine = create_engine(connection_string)

        try:
            with engine.connect() as conn:
                # Execute query
                result = conn.execute(text(query), params)

                # Fetch data in batches
                all_rows = []
                batch_count = 0

                while True:
                    rows = result.fetchmany(batch_size)
                    if not rows:
                        break

                    batch_count += 1
                    all_rows.extend([dict(row._mapping) for row in rows])

                    # Update progress
                    self.set_metadata("rows_fetched", len(all_rows))
                    self.set_metadata("batches_processed", batch_count)

                    logger.info(
                        f"Fetched batch {batch_count}, "
                        f"total rows: {len(all_rows)}"
                    )

        finally:
            engine.dispose()

        logger.info(
            f"Database ingestion completed: {len(all_rows)} rows, "
            f"{batch_count} batches"
        )

        return {
            "records": all_rows,
            "total_records": len(all_rows),
            "batches_processed": batch_count,
            "query": query
        }

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting database ingestion job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        total_records = result.data.get("total_records", 0)
        logger.info(
            f"Database ingestion job {self.job_id} completed: "
            f"{total_records} records ingested"
        )

    def on_failure(self, error: Exception, result: JobResult) -> None:
        """Called on failure"""
        logger.error(
            f"Database ingestion job {self.job_id} failed: {error}",
            exc_info=True
        )

    def on_retry(self, error: Exception, retry_count: int, delay: float) -> None:
        """Called on retry"""
        logger.warning(
            f"Database ingestion job {self.job_id} retrying "
            f"(attempt {retry_count}/{self.max_retries}) after {delay}s: {error}"
        )
