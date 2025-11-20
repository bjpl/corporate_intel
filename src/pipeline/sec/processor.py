"""SEC filing data processing and storage."""

from datetime import datetime
from typing import Any, Dict

import httpx
from loguru import logger

# Make Prefect optional for testing environments
try:
    from prefect import task
    PREFECT_AVAILABLE = True
except ImportError:
    # Dummy decorator when Prefect is not available
    def task(*args, **kwargs):
        """Dummy task decorator when Prefect unavailable."""
        def decorator(func):
            return func
        return decorator if not args else decorator(args[0])
    PREFECT_AVAILABLE = False

from src.db.models import Company, SECFiling
from src.pipeline.sec.client import SECAPIClient


async def get_or_create_company(session, company_cik: str, filing_data: Dict[str, Any]) -> Company:
    """Lookup or create company by CIK and ticker.

    Lookup strategy:
    1. First try to find by CIK (most reliable identifier)
    2. If not found by CIK, try to find by ticker using SEC mappings
    3. Only create new company if neither CIK nor ticker match exists
    4. Use proper company name from SEC mappings

    Args:
        session: Database session
        company_cik: Company CIK number
        filing_data: Filing data that may contain ticker and company name

    Returns:
        Company: Existing or newly created company record
    """
    from sqlalchemy import select

    # 1. Try to find by CIK first (most reliable)
    result = await session.execute(
        select(Company).where(Company.cik == company_cik)
    )
    company = result.scalar_one_or_none()

    if company is not None:
        logger.info(f"Found existing company by CIK: {company.name} (CIK: {company_cik}, ID: {company.id})")
        return company

    # 2. Try to find by ticker using SEC mappings
    # Get ticker from SEC mappings by reverse lookup
    ticker = filing_data.get("ticker")

    # Try to get SEC company info for proper name and ticker
    client = SECAPIClient()
    ticker_mapping = await client.get_ticker_to_cik_mapping()

    # Reverse lookup: find ticker for this CIK
    cik_to_ticker = {v: k for k, v in ticker_mapping.items()}
    mapped_ticker = cik_to_ticker.get(company_cik.zfill(10))

    if mapped_ticker:
        # Check if company exists with this ticker
        result = await session.execute(
            select(Company).where(Company.ticker == mapped_ticker)
        )
        company = result.scalar_one_or_none()

        if company is not None:
            # Found by ticker - update CIK if missing
            logger.info(f"Found existing company by ticker: {company.name} (ticker: {mapped_ticker}, ID: {company.id})")
            if not company.cik:
                company.cik = company_cik
                logger.info(f"Updated company {company.id} with CIK {company_cik}")
            return company

    # 3. Company doesn't exist - create new one with proper info
    # Get company name from SEC API
    company_name = filing_data.get("companyName")

    # If no name in filing data, try to fetch from SEC
    if not company_name or company_name.startswith("Company CIK"):
        try:
            # Fetch company submissions to get proper name
            company_info_url = f"{client.BASE_URL}/submissions/CIK{company_cik.zfill(10)}.json"
            await client.rate_limiter.acquire()

            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(company_info_url, headers=client.headers)
                if response.status_code == 200:
                    company_info = response.json()
                    company_name = company_info.get("name", f"Company CIK {company_cik}")
                    logger.info(f"Retrieved company name from SEC: {company_name}")
                else:
                    company_name = f"Company CIK {company_cik}"
                    logger.warning(f"Could not retrieve company name from SEC for CIK {company_cik}")
        except Exception as e:
            logger.warning(f"Error fetching company name from SEC: {e}")
            company_name = f"Company CIK {company_cik}"

    # Create new company with proper data
    logger.info(f"Creating new company record for CIK {company_cik}: {company_name}")
    company = Company(
        cik=company_cik,
        ticker=mapped_ticker or ticker or company_cik,  # Use mapped ticker, provided ticker, or CIK as fallback
        name=company_name,
        category=filing_data.get("category", "enabling_technology"),
    )
    session.add(company)
    await session.flush()  # Get company.id without committing
    logger.info(f"Created company {company.id} for CIK {company_cik}: {company_name}")

    return company


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
            # 1. Get or create company using improved lookup logic
            company = await get_or_create_company(session, company_cik, filing_data)

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
