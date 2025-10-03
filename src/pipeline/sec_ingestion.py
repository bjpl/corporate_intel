"""SEC EDGAR data ingestion pipeline using Prefect."""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from prefect import flow, task
from prefect.tasks import task_input_hash
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.db.models import Company, SECFiling


class FilingRequest(BaseModel):
    """SEC filing request model."""
    
    company_ticker: str
    filing_types: List[str] = Field(default=["10-K", "10-Q", "8-K"])
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SECAPIClient:
    """Client for SEC EDGAR API with rate limiting."""
    
    BASE_URL = "https://data.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    
    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "User-Agent": self.settings.SEC_USER_AGENT,
            "Accept": "application/json",
        }
        self.rate_limiter = RateLimiter(self.settings.SEC_RATE_LIMIT)
    
    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Fetch company information from SEC."""
        await self.rate_limiter.acquire()
        
        async with httpx.AsyncClient() as client:
            # Get CIK from ticker
            tickers_url = f"{self.BASE_URL}/submissions/CIK{ticker.upper()}.json"
            response = await client.get(tickers_url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch company info for {ticker}: {response.status_code}")
                return {}
    
    async def get_filings(
        self, 
        cik: str, 
        filing_types: List[str],
        start_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch SEC filings for a company."""
        await self.rate_limiter.acquire()
        
        async with httpx.AsyncClient() as client:
            # Pad CIK to 10 digits
            padded_cik = cik.zfill(10)
            url = f"{self.BASE_URL}/submissions/CIK{padded_cik}.json"
            
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch filings for CIK {cik}: {response.status_code}")
                return []
            
            data = response.json()
            filings = []
            
            # Process recent filings
            recent = data.get("filings", {}).get("recent", {})
            
            for i in range(len(recent.get("form", []))):
                form_type = recent["form"][i]
                
                if form_type in filing_types:
                    filing_date = datetime.strptime(recent["filingDate"][i], "%Y-%m-%d")
                    
                    if start_date and filing_date < start_date:
                        continue
                    
                    filings.append({
                        "form": form_type,
                        "filingDate": recent["filingDate"][i],
                        "accessionNumber": recent["accessionNumber"][i],
                        "primaryDocument": recent["primaryDocument"][i],
                        "cik": cik,
                    })
            
            return filings
    
    async def download_filing_content(self, filing: Dict[str, Any]) -> str:
        """Download the actual filing content."""
        await self.rate_limiter.acquire()
        
        cik = filing["cik"].zfill(10)
        accession = filing["accessionNumber"].replace("-", "")
        document = filing["primaryDocument"]
        
        url = f"{self.ARCHIVES_URL}/{cik}/{accession}/{document}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, follow_redirects=True)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to download filing: {url}")
                return ""


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: int):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        current = time.time()
        time_since_last = current - self.last_call
        
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        self.last_call = time.time()


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


@task
def validate_filing_data(filing_data: Dict[str, Any]) -> bool:
    """Validate filing data using Great Expectations."""
    # TODO: Implement Great Expectations validation
    # For now, basic validation
    required_fields = ["accessionNumber", "form", "filingDate", "content"]
    
    for field in required_fields:
        if field not in filing_data or not filing_data[field]:
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Check content is not empty
    if len(filing_data.get("content", "")) < 100:
        logger.warning("Filing content too short")
        return False
    
    return True


@task
async def store_filing(filing_data: Dict[str, Any], company_id: str) -> str:
    """Store filing in database."""
    # TODO: Implement database storage
    # This would use SQLAlchemy async session
    logger.info(f"Storing filing {filing_data['accessionNumber']} for company {company_id}")
    return filing_data["accessionNumber"]


def classify_edtech_company(company_info: Dict[str, Any]) -> str:
    """Classify company into EdTech category based on SIC code and description."""
    sic = company_info.get("sic", "")
    description = company_info.get("sicDescription", "").lower()
    
    # Educational services SIC codes
    if sic.startswith("82"):
        if "elementary" in description or "secondary" in description:
            return "k12"
        elif "college" in description or "university" in description:
            return "higher_education"
        else:
            return "direct_to_consumer"
    
    # Software and technology
    elif sic.startswith("73"):
        if "education" in description or "training" in description:
            return "enabling_technology"
        else:
            return "corporate_learning"
    
    # Default
    return "enabling_technology"


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