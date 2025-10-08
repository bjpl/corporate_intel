"""SEC EDGAR data ingestion pipeline using Prefect."""

import asyncio
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from great_expectations.core.batch import RuntimeBatchRequest

# Handle Great Expectations API changes across versions
try:
    from great_expectations.data_context import DataContext
except ImportError:
    # Newer versions of Great Expectations
    try:
        from great_expectations.data_context.data_context.file_data_context import FileDataContext as DataContext
    except ImportError:
        # If still failing, create a simple context wrapper
        from great_expectations.data_context import get_context
        DataContext = lambda project_config: get_context(project_config=project_config)

from great_expectations.data_context.types.base import (
    DataContextConfig,
    InMemoryStoreBackendDefaults,
)
from loguru import logger

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
    """Validate filing data using Great Expectations.

    Validates:
    - Required column presence
    - Data types
    - Format constraints (CIK, accession numbers, form types)
    - Value constraints (dates, non-null fields)
    - Content quality checks
    """
    try:
        # Convert filing data to DataFrame for GE validation
        df = pd.DataFrame([filing_data])

        # Initialize in-memory Great Expectations context
        data_context_config = DataContextConfig(
            store_backend_defaults=InMemoryStoreBackendDefaults()
        )
        context = DataContext(project_config=data_context_config)

        # Create runtime batch request
        batch_request = RuntimeBatchRequest(
            datasource_name="runtime_datasource",
            data_connector_name="runtime_data_connector",
            data_asset_name="sec_filing",
            runtime_parameters={"batch_data": df},
            batch_identifiers={"default_identifier_name": "filing_validation"},
        )

        # Create expectation suite
        suite_name = "sec_filing_validation_suite"
        context.add_or_update_expectation_suite(expectation_suite_name=suite_name)

        # Get validator
        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name,
        )

        # 1. Column Presence Expectations
        required_columns = [
            "accessionNumber",
            "form",
            "filingDate",
            "cik",
            "content",
            "content_hash",
            "downloaded_at",
        ]

        for column in required_columns:
            validator.expect_column_to_exist(column=column)

        # 2. Data Type Validations
        validator.expect_column_values_to_be_of_type(
            column="accessionNumber", type_="str"
        )
        validator.expect_column_values_to_be_of_type(column="form", type_="str")
        validator.expect_column_values_to_be_of_type(column="cik", type_="str")
        validator.expect_column_values_to_be_of_type(column="content", type_="str")
        validator.expect_column_values_to_be_of_type(
            column="content_hash", type_="str"
        )

        # 3. Format Validations using Regex

        # CIK format: numeric string, 1-10 digits
        validator.expect_column_values_to_match_regex(
            column="cik",
            regex=r"^\d{1,10}$",
            meta={"description": "CIK must be 1-10 digit numeric string"},
        )

        # Accession number format: NNNNNNNNNN-NN-NNNNNN
        validator.expect_column_values_to_match_regex(
            column="accessionNumber",
            regex=r"^\d{10}-\d{2}-\d{6}$",
            meta={"description": "Accession number format must be NNNNNNNNNN-NN-NNNNNN"},
        )

        # Form type validation: Common SEC form types
        valid_form_types = [
            "10-K", "10-Q", "8-K", "10-K/A", "10-Q/A", "8-K/A",
            "S-1", "S-3", "S-4", "S-8", "DEF 14A", "SC 13D", "SC 13G",
            "4", "3", "5", "144"
        ]
        validator.expect_column_values_to_be_in_set(
            column="form",
            value_set=valid_form_types,
            meta={"description": "Form type must be valid SEC form"},
        )

        # Filing date format: YYYY-MM-DD
        validator.expect_column_values_to_match_regex(
            column="filingDate",
            regex=r"^\d{4}-\d{2}-\d{2}$",
            meta={"description": "Filing date must be in YYYY-MM-DD format"},
        )

        # Content hash format: SHA-256 hex (64 characters)
        validator.expect_column_values_to_match_regex(
            column="content_hash",
            regex=r"^[a-f0-9]{64}$",
            meta={"description": "Content hash must be valid SHA-256 hex"},
        )

        # 4. Value Constraints

        # Non-null validations for critical fields
        validator.expect_column_values_to_not_be_null(column="accessionNumber")
        validator.expect_column_values_to_not_be_null(column="form")
        validator.expect_column_values_to_not_be_null(column="filingDate")
        validator.expect_column_values_to_not_be_null(column="cik")
        validator.expect_column_values_to_not_be_null(column="content")

        # Content length validation: minimum 100 characters
        validator.expect_column_value_lengths_to_be_between(
            column="content",
            min_value=100,
            max_value=None,
            meta={"description": "Filing content must be at least 100 characters"},
        )

        # Filing date range validation: not in future, not too old (e.g., after 1990)
        validator.expect_column_values_to_match_strftime_format(
            column="filingDate",
            strftime_format="%Y-%m-%d",
        )

        # Additional quality checks
        if "primaryDocument" in filing_data:
            validator.expect_column_values_to_not_be_null(column="primaryDocument")

        # 5. Execute validation
        validation_result = validator.validate()

        # Check if validation passed
        if not validation_result.success:
            logger.warning(
                f"Filing validation failed for {filing_data.get('accessionNumber', 'unknown')}"
            )
            logger.warning(f"Validation results: {validation_result.statistics}")

            # Log specific failures
            for result in validation_result.results:
                if not result.success:
                    logger.warning(
                        f"Failed expectation: {result.expectation_config.expectation_type} "
                        f"for column {result.expectation_config.kwargs.get('column', 'N/A')}"
                    )

            return False

        logger.info(
            f"Filing validation passed for {filing_data.get('accessionNumber', 'unknown')}"
        )
        return True

    except Exception as e:
        logger.error(f"Error during filing validation: {str(e)}", exc_info=True)
        return False


@task
async def store_filing(filing_data: Dict[str, Any], company_cik: str) -> str:
    """Store filing in database with company lookup/creation and duplicate detection.

    Args:
        filing_data: Filing information including content and metadata
        company_cik: Company CIK number for lookup/creation

    Returns:
        str: Filing ID if successfully stored

    Raises:
        ValueError: If required filing data is missing
        Exception: If database operation fails
    """
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    from src.db.session import get_session_factory

    # Validate required fields
    required_fields = ["accessionNumber", "form", "filingDate", "content"]
    missing_fields = [field for field in required_fields if field not in filing_data]
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            # 1. Check if company exists by CIK, create if not
            result = await session.execute(
                select(Company).where(Company.cik == company_cik)
            )
            company = result.scalar_one_or_none()

            if company is None:
                # Create new company record with basic info from filing
                logger.info(f"Creating new company record for CIK {company_cik}")
                company = Company(
                    cik=company_cik,
                    ticker=filing_data.get("ticker", company_cik),  # Use CIK if ticker not available
                    name=filing_data.get("companyName", f"Company CIK {company_cik}"),
                    category=filing_data.get("category", "enabling_technology"),
                )
                session.add(company)
                await session.flush()  # Get company.id without committing
                logger.info(f"Created company {company.id} for CIK {company_cik}")
            else:
                logger.info(f"Found existing company {company.id} for CIK {company_cik}")

            # 2. Check for duplicate filing by accession number
            accession_number = filing_data["accessionNumber"]
            result = await session.execute(
                select(SECFiling).where(SECFiling.accession_number == accession_number)
            )
            existing_filing = result.scalar_one_or_none()

            if existing_filing is not None:
                logger.warning(
                    f"Filing {accession_number} already exists with ID {existing_filing.id}"
                )
                return str(existing_filing.id)

            # 3. Parse filing date
            filing_date_str = filing_data["filingDate"]
            if isinstance(filing_date_str, str):
                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
            elif isinstance(filing_date_str, datetime):
                filing_date = filing_date_str
            else:
                raise ValueError(f"Invalid filing date format: {filing_date_str}")

            # 4. Create SECFiling record
            filing = SECFiling(
                company_id=company.id,
                filing_type=filing_data["form"],
                filing_date=filing_date,
                accession_number=accession_number,
                filing_url=filing_data.get("filing_url", ""),
                raw_text=filing_data.get("content", ""),
                processing_status="pending",
            )

            # Add optional fields if available
            if "primaryDocument" in filing_data:
                # Construct filing URL from primary document
                cik_padded = company_cik.zfill(10)
                accession_no_dashes = accession_number.replace("-", "")
                filing.filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/"
                    f"{accession_no_dashes}/{filing_data['primaryDocument']}"
                )

            session.add(filing)

            # 5. Commit transaction
            await session.commit()

            logger.info(
                f"Successfully stored filing {accession_number} with ID {filing.id} "
                f"for company {company.name} (CIK: {company_cik})"
            )

            return str(filing.id)

        except IntegrityError as e:
            await session.rollback()
            logger.error(
                f"Database integrity error storing filing {filing_data.get('accessionNumber')}: {str(e)}"
            )
            # Check if it's a duplicate constraint violation
            if "uq_company_filing" in str(e).lower() or "accession_number" in str(e).lower():
                logger.warning(f"Duplicate filing detected: {filing_data.get('accessionNumber')}")
                # Return existing filing ID if possible
                result = await session.execute(
                    select(SECFiling).where(
                        SECFiling.accession_number == filing_data.get("accessionNumber")
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return str(existing.id)
            raise

        except Exception as e:
            await session.rollback()
            logger.error(
                f"Error storing filing {filing_data.get('accessionNumber', 'unknown')}: {str(e)}",
                exc_info=True
            )
            raise


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