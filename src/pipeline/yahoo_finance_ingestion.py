"""
Yahoo Finance Data Ingestion Pipeline for EdTech Companies
===========================================================

SPARC SPECIFICATION:
-------------------
Purpose: Ingest financial data from Yahoo Finance for 27 EdTech companies
Target: 5 years of quarterly financial data (20 quarters)
Output: Populated companies and financial_metrics tables

ARCHITECTURE:
- Async data fetching from Yahoo Finance API
- Upsert logic for idempotent ingestion
- TimescaleDB hypertable support
- Comprehensive logging and error handling
- Retry logic with exponential backoff
- Progress tracking via coordination hooks

IMPLEMENTATION NOTES:
- Uses yfinance library for data fetching
- SQLAlchemy async sessions for database operations
- Handles duplicate data gracefully with unique constraints
- Extracts: revenue, MAU (if available), margins, growth metrics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd
import pytz
import yfinance as yf
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import Company, FinancialMetric
from src.db.session import get_session_factory


# All 27 EdTech Companies to Ingest
EDTECH_COMPANIES = [
    # Online Learning & EdTech Platforms
    {
        "ticker": "CHGG",
        "name": "Chegg Inc.",
        "sector": "Education Technology",
        "category": "D2C",
        "subcategory": ["Higher Ed", "Tutoring"],
    },
    {
        "ticker": "COUR",
        "name": "Coursera Inc.",
        "sector": "Education Technology",
        "category": "D2C",
        "subcategory": ["Higher Ed", "Online Learning"],
    },
    {
        "ticker": "DUOL",
        "name": "Duolingo Inc.",
        "sector": "Education Technology",
        "category": "D2C",
        "subcategory": ["Language Learning", "Mobile-First"],
    },
    {
        "ticker": "TWOU",
        "name": "2U Inc.",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["Online Programs", "Degree Partnerships"],
    },
    {
        "ticker": "ARCE",
        "name": "Arco Platform Limited",
        "sector": "Education Technology",
        "category": "K12",
        "subcategory": ["K-12", "Brazil Market"],
    },
    {
        "ticker": "LAUR",
        "name": "Laureate Education Inc.",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["International", "University Network"],
    },
    {
        "ticker": "LRN",
        "name": "Stride Inc.",
        "sector": "Education Technology",
        "category": "K12",
        "subcategory": ["K-12", "Virtual Schools"],
    },
    {
        "ticker": "UDMY",
        "name": "Udemy Inc.",
        "sector": "Education Technology",
        "category": "Marketplace",
        "subcategory": ["Corporate Learning", "Skills Training"],
    },
    # Publishers & Educational Content
    {
        "ticker": "PSO",
        "name": "Pearson PLC",
        "sector": "Education Technology",
        "category": "B2B",
        "subcategory": ["Higher Ed", "Assessment", "Publishing"],
    },
    {
        "ticker": "JW.A",
        "name": "John Wiley & Sons Inc.",
        "sector": "Education Technology",
        "category": "B2B",
        "subcategory": ["Publishing", "Higher Ed"],
    },
    {
        "ticker": "SCHL",
        "name": "Scholastic Corporation",
        "sector": "Education Technology",
        "category": "K12",
        "subcategory": ["Publishing", "K-12"],
    },
    {
        "ticker": "MH",
        "name": "McGraw Hill",
        "sector": "Education Technology",
        "category": "B2B",
        "subcategory": ["Publishing", "Higher Ed"],
    },
    # Higher Education Institutions
    {
        "ticker": "ATGE",
        "name": "Adtalem Global Education Inc.",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["Healthcare Education", "Online Programs"],
    },
    {
        "ticker": "LOPE",
        "name": "Grand Canyon Education Inc.",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["Online Programs", "Traditional Campus"],
    },
    {
        "ticker": "STRA",
        "name": "Strategic Education Inc.",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["Career Education", "Online Programs"],
    },
    {
        "ticker": "PRDO",
        "name": "Perdoceo Education Corporation",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["Career College", "Online Programs"],
    },
    {
        "ticker": "APEI",
        "name": "American Public Education Inc.",
        "sector": "Education Technology",
        "category": "Higher Ed",
        "subcategory": ["Military Education", "Online Programs"],
    },
    # Career & Technical Training
    {
        "ticker": "UTI",
        "name": "Universal Technical Institute Inc.",
        "sector": "Education Technology",
        "category": "Career Training",
        "subcategory": ["Automotive", "Technical"],
    },
    {
        "ticker": "LINC",
        "name": "Lincoln Educational Services Corporation",
        "sector": "Education Technology",
        "category": "Career Training",
        "subcategory": ["Automotive", "Healthcare"],
    },
    {
        "ticker": "AFYA",
        "name": "Afya Limited",
        "sector": "Education Technology",
        "category": "Medical Education",
        "subcategory": ["Brazil", "Medical Schools"],
    },
    # Early Childhood & Supplemental
    {
        "ticker": "BFAM",
        "name": "Bright Horizons Family Solutions Inc.",
        "sector": "Education Technology",
        "category": "Early Childhood",
        "subcategory": ["Daycare", "Corporate Childcare"],
    },
    # Corporate Training
    {
        "ticker": "FC",
        "name": "Franklin Covey Co.",
        "sector": "Education Technology",
        "category": "Corporate Training",
        "subcategory": ["Leadership", "Professional Development"],
    },
    {
        "ticker": "GHC",
        "name": "Graham Holdings Company",
        "sector": "Education Technology",
        "category": "Diversified",
        "subcategory": ["Kaplan", "Corporate Training"],
    },
    # Chinese Education Companies
    {
        "ticker": "TAL",
        "name": "TAL Education Group",
        "sector": "Education Technology",
        "category": "K12 China",
        "subcategory": ["K-12", "Tutoring"],
    },
    {
        "ticker": "EDU",
        "name": "New Oriental Education & Technology Group",
        "sector": "Education Technology",
        "category": "K12 China",
        "subcategory": ["K-12", "Test Prep"],
    },
    {
        "ticker": "GOTU",
        "name": "Gaotu Techedu Inc.",
        "sector": "Education Technology",
        "category": "Online China",
        "subcategory": ["K-12", "Online Tutoring"],
    },
    {
        "ticker": "COE",
        "name": "China Online Education Group",
        "sector": "Education Technology",
        "category": "Online China",
        "subcategory": ["K-12", "Online Learning"],
    },
    {
        "ticker": "FHS",
        "name": "First High-School Education Group",
        "sector": "Education Technology",
        "category": "K12 China",
        "subcategory": ["K-12", "Private Schools"],
    },
]


class YahooFinanceIngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


class YahooFinanceIngestionPipeline:
    """Pipeline for ingesting Yahoo Finance data into the database."""

    def __init__(self, session: AsyncSession):
        """Initialize the ingestion pipeline.

        Args:
            session: Async SQLAlchemy database session
        """
        self.session = session
        self.settings = get_settings()
        self.stats = {
            "companies_created": 0,
            "companies_updated": 0,
            "metrics_created": 0,
            "metrics_updated": 0,
            "errors": [],
        }

    async def run(self) -> Dict[str, Any]:
        """Execute the full ingestion pipeline.

        Returns:
            Dict containing ingestion statistics and results
        """
        logger.info("Starting Yahoo Finance data ingestion pipeline")
        logger.info(f"Target: {len(EDTECH_COMPANIES)} companies, 5 years quarterly data")

        for idx, company_data in enumerate(EDTECH_COMPANIES, 1):
            ticker = company_data["ticker"]

            try:
                logger.info(f"[{idx}/{len(EDTECH_COMPANIES)}] Processing {ticker} - {company_data['name']}")

                # Fetch data from Yahoo Finance
                yf_data = await self._fetch_yahoo_finance_data(ticker)

                if not yf_data:
                    logger.warning(f"No data available for {ticker}")
                    self.stats["errors"].append({
                        "ticker": ticker,
                        "error": "No data available from Yahoo Finance"
                    })
                    continue

                # Upsert company record
                company = await self._upsert_company(company_data, yf_data)

                # Fetch and insert quarterly financials
                await self._ingest_quarterly_financials(company, ticker)

                # Update progress via coordination hooks
                await self._notify_progress(f"Completed {idx}/{len(EDTECH_COMPANIES)} companies")

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                self.stats["errors"].append({
                    "ticker": ticker,
                    "error": str(e)
                })
                continue

        await self.session.commit()
        logger.info("Yahoo Finance ingestion pipeline completed")

        return self._generate_report()

    async def _fetch_yahoo_finance_data(self, ticker: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Fetch comprehensive data from Yahoo Finance with retry logic.

        Args:
            ticker: Stock ticker symbol
            max_retries: Maximum number of retry attempts

        Returns:
            Dict containing Yahoo Finance data or None if failed
        """
        for attempt in range(max_retries):
            try:
                # Run synchronous yfinance call in executor to avoid blocking
                loop = asyncio.get_event_loop()
                stock = await loop.run_in_executor(None, yf.Ticker, ticker)
                info = await loop.run_in_executor(None, lambda: stock.info)

                if not info or "regularMarketPrice" not in info:
                    logger.warning(f"Incomplete data for {ticker}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None

                return info

            except Exception as e:
                logger.error(f"Error fetching data for {ticker} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None

        return None

    async def _upsert_company(self, company_data: Dict[str, Any], yf_data: Dict[str, Any]) -> Company:
        """Insert or update company record.

        Args:
            company_data: Company metadata from EDTECH_COMPANIES
            yf_data: Yahoo Finance data

        Returns:
            Company model instance
        """
        ticker = company_data["ticker"]

        # Check if company exists
        result = await self.session.execute(
            select(Company).where(Company.ticker == ticker)
        )
        existing_company = result.scalar_one_or_none()

        # Prepare company data
        company_values = {
            "ticker": ticker,
            "name": company_data["name"],
            "sector": company_data["sector"],
            "category": company_data["category"],
            "subcategory": company_data["subcategory"],
            "website": yf_data.get("website", ""),
            "employee_count": yf_data.get("fullTimeEmployees", 0),
            "headquarters": f"{yf_data.get('city', '')}, {yf_data.get('country', '')}".strip(", "),
        }

        if existing_company:
            # Update existing company
            for key, value in company_values.items():
                setattr(existing_company, key, value)

            self.stats["companies_updated"] += 1
            logger.info(f"Updated company: {ticker}")
            return existing_company
        else:
            # Create new company
            company = Company(**company_values)
            self.session.add(company)
            await self.session.flush()  # Get the ID

            self.stats["companies_created"] += 1
            logger.info(f"Created company: {ticker}")
            return company

    async def _ingest_quarterly_financials(self, company: Company, ticker: str) -> None:
        """Fetch and ingest quarterly financial data.

        Args:
            company: Company model instance
            ticker: Stock ticker symbol
        """
        try:
            # Fetch quarterly financials from Yahoo Finance
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)

            # Get quarterly income statement
            quarterly_income = await loop.run_in_executor(None, lambda: stock.quarterly_income_stmt)

            # Get quarterly balance sheet
            quarterly_balance = await loop.run_in_executor(None, lambda: stock.quarterly_balance_sheet)

            # Get additional info
            info = await loop.run_in_executor(None, lambda: stock.info)

            if quarterly_income is None or quarterly_income.empty:
                logger.warning(f"No quarterly financials available for {ticker}")
                return

            # Process each quarter (up to 20 quarters = 5 years)
            quarters_to_process = min(20, len(quarterly_income.columns))

            for i in range(quarters_to_process):
                quarter_date = quarterly_income.columns[i]

                # Extract metrics for this quarter
                metrics_to_insert = []

                # Revenue (Total Revenue)
                if "Total Revenue" in quarterly_income.index:
                    revenue = quarterly_income.loc["Total Revenue", quarter_date]
                    if revenue and not pd.isna(revenue):
                        metrics_to_insert.append({
                            "metric_type": "revenue",
                            "value": float(revenue),
                            "unit": "USD",
                            "metric_category": "financial",
                        })

                # Gross Profit for margin calculation
                if "Gross Profit" in quarterly_income.index and "Total Revenue" in quarterly_income.index:
                    gross_profit = quarterly_income.loc["Gross Profit", quarter_date]
                    total_revenue = quarterly_income.loc["Total Revenue", quarter_date]
                    if gross_profit and total_revenue and not pd.isna(gross_profit) and not pd.isna(total_revenue):
                        gross_margin = (float(gross_profit) / float(total_revenue)) * 100
                        metrics_to_insert.append({
                            "metric_type": "gross_margin",
                            "value": gross_margin,
                            "unit": "percent",
                            "metric_category": "financial",
                        })

                # Operating Income for operating margin
                if "Operating Income" in quarterly_income.index and "Total Revenue" in quarterly_income.index:
                    operating_income = quarterly_income.loc["Operating Income", quarter_date]
                    total_revenue = quarterly_income.loc["Total Revenue", quarter_date]
                    if operating_income and total_revenue and not pd.isna(operating_income) and not pd.isna(total_revenue):
                        operating_margin = (float(operating_income) / float(total_revenue)) * 100
                        metrics_to_insert.append({
                            "metric_type": "operating_margin",
                            "value": operating_margin,
                            "unit": "percent",
                            "metric_category": "financial",
                        })

                # Earnings growth (from info if available)
                if "earningsGrowth" in info and info["earningsGrowth"]:
                    earnings_growth = info["earningsGrowth"] * 100  # Convert to percentage
                    metrics_to_insert.append({
                        "metric_type": "earnings_growth",
                        "value": float(earnings_growth),
                        "unit": "percent",
                        "metric_category": "financial",
                    })

                # Insert all metrics for this quarter
                for metric_data in metrics_to_insert:
                    await self._upsert_metric(
                        company_id=company.id,
                        metric_date=quarter_date,
                        period_type="quarterly",
                        **metric_data
                    )

            logger.info(f"Ingested {quarters_to_process} quarters of financial data for {ticker}")

        except Exception as e:
            logger.error(f"Error ingesting quarterly financials for {ticker}: {e}")
            raise

    async def _upsert_metric(
        self,
        company_id: UUID,
        metric_date: datetime,
        period_type: str,
        metric_type: str,
        value: float,
        unit: str,
        metric_category: str,
        source: str = "yahoo_finance",
        confidence_score: float = 0.95,
    ) -> None:
        """Insert or update a financial metric with conflict resolution.

        Args:
            company_id: Company UUID
            metric_date: Date of the metric
            period_type: Type of period (quarterly, annual, monthly)
            metric_type: Type of metric (revenue, margin, etc.)
            value: Metric value
            unit: Unit of measurement
            metric_category: Category (financial, operational, etc.)
            source: Data source
            confidence_score: Confidence in the data quality
        """
        # Ensure metric_date is timezone-aware (PostgreSQL TIMESTAMP WITH TIME ZONE requirement)
        if isinstance(metric_date, pd.Timestamp):
            # Convert pandas Timestamp to timezone-aware datetime
            if metric_date.tzinfo is None:
                metric_date = metric_date.tz_localize('UTC').to_pydatetime()
            else:
                metric_date = metric_date.to_pydatetime()
        elif isinstance(metric_date, datetime):
            # Convert naive datetime to timezone-aware
            if metric_date.tzinfo is None:
                metric_date = metric_date.replace(tzinfo=pytz.UTC)

        # Create insert statement with ON CONFLICT DO UPDATE
        stmt = insert(FinancialMetric).values(
            company_id=company_id,
            metric_date=metric_date,
            period_type=period_type,
            metric_type=metric_type,
            metric_category=metric_category,
            value=value,
            unit=unit,
            source=source,
            confidence_score=confidence_score,
        )

        # On conflict, update the value and metadata
        stmt = stmt.on_conflict_do_update(
            index_elements=["company_id", "metric_type", "metric_date", "period_type"],
            set_={
                "value": stmt.excluded.value,
                "unit": stmt.excluded.unit,
                "source": stmt.excluded.source,
                "confidence_score": stmt.excluded.confidence_score,
                "updated_at": datetime.utcnow(),
            }
        )

        result = await self.session.execute(stmt)

        # Track whether this was an insert or update
        if result.rowcount > 0:
            # Check if this was an update by querying
            check_result = await self.session.execute(
                select(FinancialMetric).where(
                    and_(
                        FinancialMetric.company_id == company_id,
                        FinancialMetric.metric_type == metric_type,
                        FinancialMetric.metric_date == metric_date,
                        FinancialMetric.period_type == period_type,
                    )
                )
            )

            if check_result.scalar_one_or_none():
                self.stats["metrics_updated"] += 1
            else:
                self.stats["metrics_created"] += 1

    async def _notify_progress(self, message: str) -> None:
        """Send progress notification via coordination hooks.

        Args:
            message: Progress message
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "npx", "claude-flow@alpha", "hooks", "notify",
                "--message", message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception as e:
            # Don't fail ingestion if notification fails
            logger.debug(f"Could not send progress notification: {e}")

    def _generate_report(self) -> Dict[str, Any]:
        """Generate ingestion report.

        Returns:
            Dict containing statistics and summary
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed" if not self.stats["errors"] else "completed_with_errors",
            "statistics": {
                "companies_created": self.stats["companies_created"],
                "companies_updated": self.stats["companies_updated"],
                "total_companies": self.stats["companies_created"] + self.stats["companies_updated"],
                "metrics_created": self.stats["metrics_created"],
                "metrics_updated": self.stats["metrics_updated"],
                "total_metrics": self.stats["metrics_created"] + self.stats["metrics_updated"],
                "errors_count": len(self.stats["errors"]),
            },
            "errors": self.stats["errors"],
        }

        return report


async def run_ingestion() -> Dict[str, Any]:
    """Main entry point for Yahoo Finance data ingestion.

    Returns:
        Dict containing ingestion results and statistics
    """
    logger.info("=" * 80)
    logger.info("Yahoo Finance Data Ingestion Pipeline")
    logger.info("=" * 80)

    # Create database session
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            # Initialize and run pipeline
            pipeline = YahooFinanceIngestionPipeline(session)
            report = await pipeline.run()

            # Log summary
            logger.info("=" * 80)
            logger.info("INGESTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Companies Created: {report['statistics']['companies_created']}")
            logger.info(f"Companies Updated: {report['statistics']['companies_updated']}")
            logger.info(f"Metrics Created: {report['statistics']['metrics_created']}")
            logger.info(f"Metrics Updated: {report['statistics']['metrics_updated']}")
            logger.info(f"Total Errors: {report['statistics']['errors_count']}")

            if report["errors"]:
                logger.warning("\nErrors encountered:")
                for error in report["errors"]:
                    logger.warning(f"  - {error['ticker']}: {error['error']}")

            logger.info("=" * 80)

            # Run post-task hook
            try:
                process = await asyncio.create_subprocess_exec(
                    "npx", "claude-flow@alpha", "hooks", "post-task",
                    "--task-id", "yahoo-ingestion",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            except Exception as e:
                logger.debug(f"Could not run post-task hook: {e}")

            return report

        except Exception as e:
            logger.error(f"Fatal error in ingestion pipeline: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    """Run the ingestion pipeline when executed as a script."""
    import sys

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run the async ingestion pipeline
    result = asyncio.run(run_ingestion())

    # Exit with appropriate code
    if result["statistics"]["errors_count"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
