"""
File Ingestion Job

Ingests data from files (CSV, JSON, Parquet, etc.) with support for local and remote files.
"""

from typing import Any, Dict, List, Optional
import logging
import os

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("file_ingestion")
class FileIngestionJob(BaseJob):
    """
    Ingest data from files

    Parameters:
        file_path: Path to file (local or remote URL)
        file_type: File type (csv, json, parquet, excel)
        encoding: File encoding
        delimiter: CSV delimiter
        sheet_name: Excel sheet name
        compression: Compression type (gzip, bz2, zip)
        chunksize: Read file in chunks
    """

    max_retries = 3
    retry_delay = 2.0
    retry_backoff = 2.0
    timeout = 600.0  # 10 minutes

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute file ingestion"""
        file_path = kwargs.get("file_path")
        file_type = kwargs.get("file_type", "csv").lower()
        encoding = kwargs.get("encoding", "utf-8")
        delimiter = kwargs.get("delimiter", ",")
        sheet_name = kwargs.get("sheet_name", 0)
        compression = kwargs.get("compression", "infer")
        chunksize = kwargs.get("chunksize")

        if not file_path:
            raise ValueError("file_path is required")

        self.set_metadata("file_path", file_path)
        self.set_metadata("file_type", file_type)

        # Import pandas (lazy import)
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required. Install with: pip install pandas")

        logger.info(f"Starting file ingestion from {file_path}")

        # Read file based on type
        try:
            if file_type == "csv":
                if chunksize:
                    # Read in chunks
                    chunks = []
                    for chunk in pd.read_csv(
                        file_path,
                        encoding=encoding,
                        delimiter=delimiter,
                        compression=compression,
                        chunksize=chunksize
                    ):
                        chunks.append(chunk)
                        self.set_metadata("chunks_processed", len(chunks))
                        logger.info(f"Processed chunk {len(chunks)}")

                    df = pd.concat(chunks, ignore_index=True)
                else:
                    df = pd.read_csv(
                        file_path,
                        encoding=encoding,
                        delimiter=delimiter,
                        compression=compression
                    )

            elif file_type == "json":
                df = pd.read_json(
                    file_path,
                    encoding=encoding,
                    compression=compression
                )

            elif file_type == "parquet":
                df = pd.read_parquet(file_path)

            elif file_type == "excel":
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name
                )

            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Convert to records
            records = df.to_dict("records")

            # Get file info
            file_size = None
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

        logger.info(
            f"File ingestion completed: {len(records)} records from {file_path}"
        )

        return {
            "records": records,
            "total_records": len(records),
            "columns": list(df.columns),
            "file_path": file_path,
            "file_type": file_type,
            "file_size": file_size,
            "shape": df.shape
        }

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting file ingestion job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        total_records = result.data.get("total_records", 0)
        file_path = result.data.get("file_path", "unknown")
        logger.info(
            f"File ingestion job {self.job_id} completed: "
            f"{total_records} records from {file_path}"
        )

    def on_failure(self, error: Exception, result: JobResult) -> None:
        """Called on failure"""
        logger.error(
            f"File ingestion job {self.job_id} failed: {error}",
            exc_info=True
        )

    def on_retry(self, error: Exception, retry_count: int, delay: float) -> None:
        """Called on retry"""
        logger.warning(
            f"File ingestion job {self.job_id} retrying "
            f"(attempt {retry_count}/{self.max_retries}) after {delay}s: {error}"
        )
