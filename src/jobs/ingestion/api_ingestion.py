"""
API Ingestion Job

Ingests data from external APIs with rate limiting, pagination, and error handling.
"""

import time
from typing import Any, Dict, List, Optional
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("api_ingestion")
class APIIngestionJob(BaseJob):
    """
    Ingest data from external APIs

    Parameters:
        url: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        headers: Request headers
        params: Query parameters
        data: Request body data
        auth: Authentication credentials
        rate_limit: Requests per second limit
        pagination: Pagination configuration
        max_pages: Maximum pages to fetch
    """

    max_retries = 5
    retry_delay = 2.0
    retry_backoff = 2.0
    timeout = 300.0  # 5 minutes

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute API ingestion"""
        url = kwargs.get("url")
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        params = kwargs.get("params", {})
        data = kwargs.get("data")
        auth = kwargs.get("auth")
        rate_limit = kwargs.get("rate_limit", 10)  # requests per second
        pagination = kwargs.get("pagination", {})
        max_pages = kwargs.get("max_pages", 100)

        if not url:
            raise ValueError("URL is required for API ingestion")

        self.set_metadata("url", url)
        self.set_metadata("method", method)

        # Import requests (lazy import)
        try:
            import requests
        except ImportError:
            raise ImportError("requests library required. Install with: pip install requests")

        all_data = []
        page = 1
        total_requests = 0
        request_interval = 1.0 / rate_limit if rate_limit > 0 else 0

        logger.info(f"Starting API ingestion from {url}")

        while page <= max_pages:
            # Rate limiting
            if request_interval > 0:
                time.sleep(request_interval)

            # Prepare request
            request_params = params.copy()
            if pagination:
                # Handle pagination
                page_param = pagination.get("page_param", "page")
                page_size_param = pagination.get("page_size_param", "limit")
                page_size = pagination.get("page_size", 100)

                request_params[page_param] = page
                request_params[page_size_param] = page_size

            # Make request
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=request_params,
                    json=data if method in ["POST", "PUT", "PATCH"] else None,
                    auth=tuple(auth) if auth else None,
                    timeout=30
                )
                response.raise_for_status()

                # Parse response
                response_data = response.json()
                total_requests += 1

                # Extract data based on pagination config
                if pagination:
                    data_key = pagination.get("data_key", "results")
                    page_data = response_data.get(data_key, [])

                    if not page_data:
                        # No more data
                        break

                    all_data.extend(page_data)

                    # Check if there are more pages
                    has_more_key = pagination.get("has_more_key", "has_more")
                    if not response_data.get(has_more_key, True):
                        break
                else:
                    # No pagination - single request
                    all_data = response_data
                    break

                # Update progress
                self.set_metadata("pages_fetched", page)
                self.set_metadata("records_fetched", len(all_data))

                logger.info(f"Fetched page {page}, total records: {len(all_data)}")
                page += 1

            except requests.RequestException as e:
                logger.error(f"API request failed: {e}")
                raise

        logger.info(
            f"API ingestion completed: {total_requests} requests, "
            f"{len(all_data)} records"
        )

        return {
            "records": all_data,
            "total_records": len(all_data),
            "total_requests": total_requests,
            "pages_fetched": page - 1,
            "source": url
        }

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting API ingestion job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        total_records = result.data.get("total_records", 0)
        logger.info(
            f"API ingestion job {self.job_id} completed successfully: "
            f"{total_records} records ingested"
        )

    def on_failure(self, error: Exception, result: JobResult) -> None:
        """Called on failure"""
        logger.error(
            f"API ingestion job {self.job_id} failed: {error}",
            exc_info=True
        )

    def on_retry(self, error: Exception, retry_count: int, delay: float) -> None:
        """Called on retry"""
        logger.warning(
            f"API ingestion job {self.job_id} retrying "
            f"(attempt {retry_count}/{self.max_retries}) after {delay}s: {error}"
        )
