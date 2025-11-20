"""SEC ingestion pipeline orchestration using Prefect."""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

# Make Prefect optional for testing environments
try:
    from prefect import flow, task
    from prefect.tasks import task_input_hash
    PREFECT_AVAILABLE = True
except ImportError:
    # Dummy decorators when Prefect is not available (for testing)
    def flow(*args, **kwargs):
        """Dummy flow decorator when Prefect unavailable."""
        def decorator(func):
            return func
        return decorator if not args else decorator(args[0])

    def task(*args, **kwargs):
        """Dummy task decorator when Prefect unavailable."""
        def decorator(func):
            return func
        return decorator if not args else decorator(args[0])

    def task_input_hash(*args, **kwargs):
        """Dummy task_input_hash when Prefect unavailable."""
        return None

    PREFECT_AVAILABLE = False
    logger.warning("Prefect not available - flows will run as regular functions")

from src.pipeline.sec.client import SECAPIClient
from src.pipeline.sec.parser import classify_edtech_company, validate_filing_data
from src.pipeline.sec.processor import store_filing


class FilingRequest(BaseModel):
    """SEC filing request model."""

    company_ticker: str
    filing_types: List[str] = Field(default=["10-K", "10-Q", "8-K"])
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@task(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
async def fetch_company_data(ticker: str) -> Dict[str, Any]:
    """Fetch company data from SEC EDGAR."""
    client = SECAPIClient()

    logger.info(f"Fetching company data for {ticker}")
    company_info = await client.get_company_info(ticker)

    if not company_info:
        raise ValueError(f"Could not fetch company info for {ticker}")

    return {
        "ticker": ticker,
        "cik": company_info.get("cik"),
        "name": company_info.get("name"),
        "sic": company_info.get("sic"),
        "sicDescription": company_info.get("sicDescription"),
        "category": classify_edtech_company(company_info),
    }


@task(retries=3, retry_delay_seconds=60)
async def fetch_filings(
    cik: str,
    filing_types: List[str],
    start_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Fetch SEC filings for a company."""
    client = SECAPIClient()

    logger.info(f"Fetching filings for CIK {cik}: {filing_types}")
    filings = await client.get_filings(cik, filing_types, start_date)

    logger.info(f"Found {len(filings)} filings for CIK {cik}")
    return filings


@task(retries=2, retry_delay_seconds=120)
async def download_filing(filing: Dict[str, Any]) -> Dict[str, Any]:
    """Download and process a single filing."""
    client = SECAPIClient()

    logger.info(f"Downloading filing: {filing['accessionNumber']}")
    content = await client.download_filing_content(filing)

    if content:
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        return {
            **filing,
            "content": content,
            "content_hash": content_hash,
            "downloaded_at": datetime.utcnow().isoformat(),
        }

    return filing


@flow(
    name="sec-ingestion-pipeline",
    description="Ingest SEC filings for EdTech companies",
    retries=2,
    retry_delay_seconds=300,
)
async def sec_ingestion_flow(request: FilingRequest):
    """Main SEC ingestion flow."""
    logger.info(f"Starting SEC ingestion for {request.company_ticker}")

    # Fetch company data
    company_data = await fetch_company_data(request.company_ticker)

    if not company_data.get("cik"):
        logger.error(f"No CIK found for {request.company_ticker}")
        return

    # Fetch filings
    filings = await fetch_filings(
        company_data["cik"],
        request.filing_types,
        request.start_date
    )

    # Download filings in parallel (with concurrency limit)
    download_tasks = []
    for filing in filings[:10]:  # Limit for testing
        download_tasks.append(download_filing(filing))

    downloaded_filings = await asyncio.gather(*download_tasks)

    # Validate and store filings
    stored_count = 0
    for filing_data in downloaded_filings:
        if validate_filing_data(filing_data):
            await store_filing(filing_data, company_data["cik"])
            stored_count += 1

    logger.info(f"Successfully stored {stored_count} filings for {request.company_ticker}")

    return {
        "ticker": request.company_ticker,
        "cik": company_data["cik"],
        "filings_found": len(filings),
        "filings_stored": stored_count,
    }


@flow(
    name="batch-sec-ingestion",
    description="Batch ingestion for multiple EdTech companies",
)
async def batch_sec_ingestion_flow(tickers: List[str]):
    """Batch process multiple companies."""
    logger.info(f"Starting batch SEC ingestion for {len(tickers)} companies")

    # Create filing requests
    requests = [
        FilingRequest(
            company_ticker=ticker,
            start_date=datetime.now() - timedelta(days=365)  # Last year
        )
        for ticker in tickers
    ]

    # Process in parallel with limited concurrency
    results = []
    for request in requests:
        result = await sec_ingestion_flow(request)
        results.append(result)

    # Summary
    total_filings = sum(r.get("filings_stored", 0) for r in results if r)
    logger.info(f"Batch ingestion complete: {total_filings} total filings stored")

    return results
