"""Alpha Vantage Data Ingestion Pipeline for EdTech Companies.

This script fetches fundamental financial data from Alpha Vantage API and stores it
in the financial_metrics table. It supplements Yahoo Finance data with additional
metrics like P/E ratio, PEG ratio, EPS, ROE, and profit margins.

Rate Limiting:
    - Alpha Vantage Free Tier: 5 API calls per minute (500/day)
    - Built-in rate limiter in AlphaVantageConnector: 5 calls/60 seconds
    - Sequential processing with 12-second delays between companies

Target Companies:
    Top 10 EdTech companies (same as SEC ingestion)

Metrics Stored:
    - pe_ratio: Price-to-Earnings ratio
    - peg_ratio: PEG ratio (P/E to Growth)
    - eps: Earnings Per Share
    - roe: Return on Equity
    - profit_margin: Net Profit Margin
    - revenue_growth_yoy: Year-over-Year Revenue Growth
    - market_cap: Market Capitalization
    - operating_margin: Operating Margin
    - return_on_assets: Return on Assets
"""

import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.data_sources import AlphaVantageConnector
from src.core.config import get_settings
from src.db.models import Company, FinancialMetric
from src.db.session import get_session_factory


# Top 10 EdTech companies (matching SEC ingestion)
EDTECH_TICKERS = [
    'CHGG',  # Chegg
    'COUR',  # Coursera
    'DUOL',  # Duolingo
    'ARCE',  # Arco Platform
    'LRN',   # Stride (K12)
    'UDMY',  # Udemy
    'PSO',   # Pearson
    'ATGE',  # Adtalem Global Education
    'LOPE',  # Grand Canyon Education
    'STRA',  # Strategic Education
]


# Metric mappings: Alpha Vantage field -> our metric_type
METRIC_MAPPINGS = {
    'pe_ratio': {'av_field': 'pe_ratio', 'category': 'valuation', 'unit': 'ratio'},
    'peg_ratio': {'av_field': 'peg_ratio', 'category': 'valuation', 'unit': 'ratio'},
    'eps': {'av_field': 'eps', 'category': 'profitability', 'unit': 'USD'},
    'roe': {'av_field': 'return_on_equity_ttm', 'category': 'profitability', 'unit': 'percent'},
    'profit_margin': {'av_field': 'profit_margin', 'category': 'profitability', 'unit': 'percent'},
    'revenue_growth_yoy': {'av_field': 'quarterly_revenue_growth_yoy', 'category': 'growth', 'unit': 'percent'},
    'market_cap': {'av_field': 'market_cap', 'category': 'size', 'unit': 'USD'},
    'operating_margin': {'av_field': 'operating_margin_ttm', 'category': 'profitability', 'unit': 'percent'},
    'return_on_assets': {'av_field': 'return_on_assets_ttm', 'category': 'profitability', 'unit': 'percent'},
    'dividend_yield': {'av_field': 'dividend_yield', 'category': 'income', 'unit': 'percent'},
    'trailing_pe': {'av_field': 'trailing_pe', 'category': 'valuation', 'unit': 'ratio'},
    'forward_pe': {'av_field': 'forward_pe', 'category': 'valuation', 'unit': 'ratio'},
    'price_to_book': {'av_field': 'price_to_book', 'category': 'valuation', 'unit': 'ratio'},
    'price_to_sales': {'av_field': 'price_to_sales_ttm', 'category': 'valuation', 'unit': 'ratio'},
    'ev_to_revenue': {'av_field': 'ev_to_revenue', 'category': 'valuation', 'unit': 'ratio'},
    'ev_to_ebitda': {'av_field': 'ev_to_ebitda', 'category': 'valuation', 'unit': 'ratio'},
}


class AlphaVantageIngestionResult:
    """Result container for ingestion operations."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.success = False
        self.metrics_fetched = 0
        self.metrics_stored = 0
        self.error_message: Optional[str] = None
        self.company_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'ticker': self.ticker,
            'success': self.success,
            'metrics_fetched': self.metrics_fetched,
            'metrics_stored': self.metrics_stored,
            'error_message': self.error_message,
            'company_id': str(self.company_id) if self.company_id else None,
        }


async def get_or_create_company(
    session: AsyncSession,
    ticker: str
) -> Optional[Company]:
    """Get existing company or create a new one.

    Args:
        session: Database session
        ticker: Company ticker symbol

    Returns:
        Company instance or None if creation fails
    """
    # Try to find existing company
    result = await session.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()

    if company:
        logger.debug(f"Found existing company: {ticker} (ID: {company.id})")
        return company

    # Create new company
    logger.info(f"Creating new company record for {ticker}")
    company = Company(
        ticker=ticker.upper(),
        name=f"{ticker} (Auto-created)",  # Will be updated with real name from API
        sector="Education Technology",
        category="EdTech",
    )

    session.add(company)
    await session.flush()  # Get the ID without committing

    logger.info(f"Created company: {ticker} (ID: {company.id})")
    return company


async def store_financial_metrics(
    session: AsyncSession,
    company_id: str,
    ticker: str,
    av_data: Dict[str, Any]
) -> int:
    """Store financial metrics from Alpha Vantage data.

    Uses upsert logic (INSERT ... ON CONFLICT DO UPDATE) to avoid duplicates
    while updating existing metrics if data changes.

    Args:
        session: Database session
        company_id: Company UUID
        ticker: Company ticker symbol
        av_data: Data from Alpha Vantage API

    Returns:
        Number of metrics stored
    """
    if not av_data or 'ticker' not in av_data:
        logger.warning(f"{ticker}: No data returned from Alpha Vantage")
        return 0

    # Use current timestamp for metric_date (represents when data was fetched)
    metric_date = datetime.now(timezone.utc)

    metrics_to_store = []

    # Process each metric mapping
    for metric_type, config in METRIC_MAPPINGS.items():
        av_field = config['av_field']
        value = av_data.get(av_field)

        # Skip if no value or value is 0/None
        if value is None or (isinstance(value, (int, float)) and value == 0):
            continue

        # Convert percentage values (Alpha Vantage returns as decimal)
        if config['unit'] == 'percent' and isinstance(value, float):
            value = value * 100  # Convert 0.15 -> 15.0

        metrics_to_store.append({
            'company_id': company_id,
            'metric_date': metric_date,
            'period_type': 'quarterly',  # Most Alpha Vantage data is quarterly/TTM
            'metric_type': metric_type,
            'metric_category': config['category'],
            'value': float(value),
            'unit': config['unit'],
            'source': 'alpha_vantage',
            'confidence_score': 0.95,  # High confidence for direct API data
        })

    if not metrics_to_store:
        logger.warning(f"{ticker}: No valid metrics to store")
        return 0

    # Batch upsert all metrics
    # Using PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
    stmt = insert(FinancialMetric).values(metrics_to_store)

    # Update if conflict on unique constraint (company_id, metric_type, metric_date, period_type)
    stmt = stmt.on_conflict_do_update(
        index_elements=['company_id', 'metric_type', 'metric_date', 'period_type'],
        set_={
            'value': stmt.excluded.value,
            'confidence_score': stmt.excluded.confidence_score,
            'updated_at': datetime.now(timezone.utc),
        }
    )

    await session.execute(stmt)

    logger.info(f"{ticker}: Stored {len(metrics_to_store)} financial metrics")

    return len(metrics_to_store)


async def ingest_alpha_vantage_for_company(
    ticker: str,
    connector: AlphaVantageConnector,
    session: AsyncSession
) -> AlphaVantageIngestionResult:
    """Fetch and store Alpha Vantage data for a single company.

    Args:
        ticker: Company ticker symbol
        connector: Alpha Vantage connector instance
        session: Database session

    Returns:
        AlphaVantageIngestionResult with operation details
    """
    result = AlphaVantageIngestionResult(ticker)

    try:
        # Get or create company record
        company = await get_or_create_company(session, ticker)

        if not company:
            result.error_message = "Failed to get/create company record"
            return result

        result.company_id = company.id

        # Fetch data from Alpha Vantage (respects rate limiter internally)
        logger.debug(f"{ticker}: Fetching data from Alpha Vantage API...")
        av_data = await connector.get_company_overview(ticker)

        if not av_data:
            result.error_message = "No data returned from Alpha Vantage"
            return result

        result.metrics_fetched = len([v for v in av_data.values() if v])

        # Store metrics in database
        metrics_stored = await store_financial_metrics(
            session,
            str(company.id),
            ticker,
            av_data
        )

        result.metrics_stored = metrics_stored
        result.success = metrics_stored > 0

        # Commit the transaction
        await session.commit()

    except Exception as e:
        logger.error(f"{ticker}: Error during ingestion - {str(e)}", exc_info=True)
        result.error_message = str(e)
        await session.rollback()

    return result


async def run_alpha_vantage_ingestion(
    tickers: List[str],
    delay_between_calls: int = 12
) -> Dict[str, Any]:
    """Run Alpha Vantage ingestion for multiple companies.

    Processes companies sequentially to respect API rate limits.

    Args:
        tickers: List of ticker symbols
        delay_between_calls: Seconds to wait between API calls (default: 12)

    Returns:
        Summary dictionary with results
    """
    settings = get_settings()

    # Check if API key is configured
    if not settings.ALPHA_VANTAGE_API_KEY:
        logger.error("Alpha Vantage API key not configured. Please set ALPHA_VANTAGE_API_KEY in .env")
        return {
            'total_companies': len(tickers),
            'successful_companies': 0,
            'failed_companies': tickers,
            'error': 'API key not configured',
        }

    logger.info(f"Starting Alpha Vantage ingestion for {len(tickers)} EdTech companies")
    logger.info(f"Rate limit: 5 calls/minute = 1 call every {delay_between_calls} seconds")
    logger.info("-" * 80)

    # Initialize connector and session factory
    connector = AlphaVantageConnector()
    session_factory = get_session_factory()

    results = []
    failed_companies = []
    successful_companies = []

    # Process each company sequentially
    for idx, ticker in enumerate(tickers, 1):
        logger.info(f"[{idx}/{len(tickers)}] Processing {ticker}...")

        # Create new session for each company
        async with session_factory() as session:
            result = await ingest_alpha_vantage_for_company(ticker, connector, session)
            results.append(result)

            if result.success:
                successful_companies.append(ticker)
                logger.info(
                    f"[{idx}/{len(tickers)}] {ticker}: SUCCESS - "
                    f"Fetched {result.metrics_fetched} fields, "
                    f"Stored {result.metrics_stored} metrics"
                )
            else:
                failed_companies.append(ticker)
                logger.warning(
                    f"[{idx}/{len(tickers)}] {ticker}: FAILED - "
                    f"{result.error_message or 'Unknown error'}"
                )

        # Rate limit delay between companies (except after last one)
        if idx < len(tickers):
            logger.info(f"Rate limit: Waiting {delay_between_calls} seconds before next company...")

            # Run notification hook during delay
            try:
                subprocess.run(
                    [
                        "npx", "claude-flow@alpha", "hooks", "notify",
                        "--message", f"Processed {ticker} ({idx}/{len(tickers)}) - waiting {delay_between_calls}s for rate limit"
                    ],
                    check=False,
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                pass  # Hooks are optional

            await asyncio.sleep(delay_between_calls)

    # Calculate summary statistics
    total_metrics_fetched = sum(r.metrics_fetched for r in results)
    total_metrics_stored = sum(r.metrics_stored for r in results)

    logger.info("-" * 80)
    logger.info("ALPHA VANTAGE INGESTION SUMMARY")
    logger.info("-" * 80)
    logger.info(f"Total companies processed: {len(tickers)}")
    logger.info(f"Successful: {len(successful_companies)}")
    logger.info(f"Failed: {len(failed_companies)}")
    if failed_companies:
        logger.info(f"Failed companies: {', '.join(failed_companies)}")
    logger.info(f"Total metrics fetched: {total_metrics_fetched}")
    logger.info(f"Total metrics stored: {total_metrics_stored}")
    logger.info(f"Average metrics per company: {total_metrics_stored / len(tickers):.1f}")
    logger.info("-" * 80)

    return {
        'total_companies': len(tickers),
        'successful_companies': len(successful_companies),
        'failed_companies': failed_companies,
        'total_metrics_fetched': total_metrics_fetched,
        'total_metrics_stored': total_metrics_stored,
        'results': [r.to_dict() for r in results],
    }


async def main():
    """Main entry point for Alpha Vantage ingestion."""

    # Pre-task hook
    logger.info("Running pre-task hook...")
    try:
        subprocess.run(
            [
                "npx", "claude-flow@alpha", "hooks", "pre-task",
                "--description", "Alpha Vantage ingestion for EdTech companies"
            ],
            check=False,
            capture_output=True,
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Could not run pre-task hook: {e}")

    # Run ingestion
    try:
        summary = await run_alpha_vantage_ingestion(EDTECH_TICKERS)

        # Post-task hook
        logger.info("Running post-task hook...")
        try:
            subprocess.run(
                [
                    "npx", "claude-flow@alpha", "hooks", "post-task",
                    "--task-id", "alpha-vantage-ingestion"
                ],
                check=False,
                capture_output=True,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Could not run post-task hook: {e}")

        # Exit with error code if any companies failed
        if summary['failed_companies']:
            logger.error(f"Ingestion completed with {len(summary['failed_companies'])} failures")
            sys.exit(1)

        return summary

    except Exception as e:
        logger.error(f"Alpha Vantage ingestion failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run the ingestion
    asyncio.run(main())
