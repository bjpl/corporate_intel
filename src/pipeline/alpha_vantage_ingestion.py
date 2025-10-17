"""Alpha Vantage Data Ingestion Pipeline for EdTech Companies.

This script fetches fundamental financial data from Alpha Vantage API and stores it
in the financial_metrics table. It supplements Yahoo Finance data with additional
metrics like P/E ratio, PEG ratio, EPS, ROE, and profit margins.

Rate Limiting:
    - Alpha Vantage Free Tier: 5 API calls per minute (500/day)
    - Built-in rate limiter in AlphaVantageConnector: 5 calls/60 seconds
    - Sequential processing with 12-second delays between companies

Target Companies:
    All 27 EdTech companies (expanded watchlist coverage)

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

import aiohttp
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.data_sources import AlphaVantageConnector
from src.core.config import get_settings
from src.db.models import Company
from src.db.session import get_session_factory
from src.pipeline.common import (
    get_or_create_company,
    upsert_financial_metric,
    run_coordination_hook,
)


# All 27 EdTech companies (matching expanded watchlist)
EDTECH_TICKERS = [
    # Online Learning & EdTech Platforms
    'CHGG',  # Chegg Inc.
    'COUR',  # Coursera Inc.
    'DUOL',  # Duolingo Inc.
    'TWOU',  # 2U Inc.
    'ARCE',  # Arco Platform Limited
    'LAUR',  # Laureate Education Inc.
    'LRN',   # Stride Inc.
    'UDMY',  # Udemy Inc.
    # Publishers & Educational Content
    'PSO',   # Pearson PLC
    'JW.A',  # John Wiley & Sons Inc.
    'SCHL',  # Scholastic Corporation
    'MH',    # McGraw Hill
    # Higher Education Institutions
    'ATGE',  # Adtalem Global Education Inc.
    'LOPE',  # Grand Canyon Education Inc.
    'STRA',  # Strategic Education Inc.
    'PRDO',  # Perdoceo Education Corporation
    'APEI',  # American Public Education Inc.
    # Career & Technical Training
    'UTI',   # Universal Technical Institute Inc.
    'LINC',  # Lincoln Educational Services Corporation
    'AFYA',  # Afya Limited
    # Early Childhood & Supplemental
    'BFAM',  # Bright Horizons Family Solutions Inc.
    # Corporate Training
    'FC',    # Franklin Covey Co.
    'GHC',   # Graham Holdings Company
    # Chinese Education Companies
    'TAL',   # TAL Education Group
    'EDU',   # New Oriental Education & Technology Group
    'GOTU',  # Gaotu Techedu Inc.
    'COE',   # China Online Education Group
    'FHS',   # First High-School Education Group
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
        self.error_category: Optional[str] = None
        self.company_id: Optional[str] = None
        self.retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'ticker': self.ticker,
            'success': self.success,
            'metrics_fetched': self.metrics_fetched,
            'metrics_stored': self.metrics_stored,
            'error_message': self.error_message,
            'error_category': self.error_category,
            'company_id': str(self.company_id) if self.company_id else None,
            'retry_count': self.retry_count,
        }


# Removed: get_or_create_company now imported from src.pipeline.common


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

    # Use end of most recent quarter for metric_date (Alpha Vantage provides TTM/current data)
    # Calculate the last completed quarter-end date
    now = datetime.now(timezone.utc)
    current_month = now.month
    # Quarter ends: Mar 31 (Q1), Jun 30 (Q2), Sep 30 (Q3), Dec 31 (Q4)
    if current_month <= 3:
        quarter_end = datetime(now.year - 1, 12, 31, tzinfo=timezone.utc)
    elif current_month <= 6:
        quarter_end = datetime(now.year, 3, 31, tzinfo=timezone.utc)
    elif current_month <= 9:
        quarter_end = datetime(now.year, 6, 30, tzinfo=timezone.utc)
    else:  # current_month <= 12
        quarter_end = datetime(now.year, 9, 30, tzinfo=timezone.utc)

    metric_date = quarter_end

    metrics_stored = 0

    # Process each metric mapping using common utility
    for metric_type, config in METRIC_MAPPINGS.items():
        av_field = config['av_field']
        value = av_data.get(av_field)

        # Skip if no value or value is 0/None
        if value is None or (isinstance(value, (int, float)) and value == 0):
            continue

        # Convert percentage values (Alpha Vantage returns as decimal)
        if config['unit'] == 'percent' and isinstance(value, float):
            value = value * 100  # Convert 0.15 -> 15.0

        # Use common utility for upsert
        await upsert_financial_metric(
            session,
            company_id=company_id,
            metric_date=metric_date,
            period_type='quarterly',
            metric_type=metric_type,
            value=float(value),
            unit=config['unit'],
            metric_category=config['category'],
            source='alpha_vantage',
            confidence_score=0.95,
        )
        metrics_stored += 1

    if metrics_stored == 0:
        logger.warning(f"{ticker}: No valid metrics to store")
    else:
        logger.info(f"{ticker}: Stored {metrics_stored} financial metrics")

    return metrics_stored


async def ingest_alpha_vantage_for_company(
    ticker: str,
    connector: AlphaVantageConnector,
    session: AsyncSession,
    _retry_state: Optional[Dict[str, int]] = None
) -> AlphaVantageIngestionResult:
    """Fetch and store Alpha Vantage data for a single company.

    Implements retry logic with exponential backoff for transient failures:
    - Max 3 attempts
    - Wait time: 4s, 8s, 16s (exponential backoff)
    - Retries on network errors (ClientError, TimeoutError)
    - Does NOT retry on data quality issues (ValueError)

    Args:
        ticker: Company ticker symbol
        connector: Alpha Vantage connector instance
        session: Database session
        _retry_state: Internal state for tracking retries (used internally)

    Returns:
        AlphaVantageIngestionResult with operation details
    """
    # Initialize retry state if not provided
    if _retry_state is None:
        _retry_state = {'attempt': 0}

    result = AlphaVantageIngestionResult(ticker)
    result.retry_count = _retry_state['attempt']

    try:
        # Get or create company record
        company = await get_or_create_company(session, ticker)

        if not company:
            result.error_message = "Failed to get/create company record"
            result.error_category = "database_error"
            return result

        result.company_id = company.id

        # Fetch data from Alpha Vantage (respects rate limiter internally)
        logger.debug(f"{ticker}: Fetching data from Alpha Vantage API...")
        av_data = await connector.get_company_overview(ticker)

        # Validate API response format
        if not av_data or not isinstance(av_data, dict):
            result.error_message = "Invalid API response format (empty or not a dict)"
            result.error_category = "api_format_error"
            return result

        # Validate ticker match
        if av_data.get('ticker') and av_data.get('ticker') != ticker.upper():
            logger.warning(
                f"{ticker}: API returned data for wrong ticker: "
                f"expected {ticker.upper()}, got {av_data.get('ticker')}"
            )
            result.error_message = f"Ticker mismatch: expected {ticker.upper()}, got {av_data.get('ticker')}"
            result.error_category = "data_validation_error"
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

        # Check if we got any valid data to store
        if result.metrics_fetched == 0 or metrics_stored == 0:
            result.error_message = "No valid metrics returned from API or stored"
            result.error_category = "no_data"
            await session.rollback()
            return result

        result.success = metrics_stored > 0

        # Commit the transaction
        await session.commit()

        if result.success and result.retry_count > 0:
            logger.info(f"{ticker}: Succeeded after {result.retry_count} retries")

    except ValueError as e:
        # Data quality/conversion errors - don't retry
        if "'None'" in str(e) or "None" in str(e):
            result.error_message = "API returned 'None' values (data quality issue)"
            result.error_category = "data_quality_error"
        else:
            result.error_message = f"Value conversion error: {str(e)}"
            result.error_category = "conversion_error"
        logger.error(f"{ticker}: {result.error_category} - {result.error_message}")
        await session.rollback()

    except aiohttp.ClientError as e:
        # Network errors - will be retried manually
        result.error_message = f"Network error: {str(e)}"
        result.error_category = "network_error"
        await session.rollback()

        # Retry logic
        _retry_state['attempt'] += 1
        if _retry_state['attempt'] < 3:
            wait_time = min(4 * (2 ** (_retry_state['attempt'] - 1)), 60)  # 4s, 8s, 16s
            logger.warning(f"{ticker}: Network error (attempt {_retry_state['attempt']}/3) - {str(e)}, retrying in {wait_time}s")
            await asyncio.sleep(wait_time)
            return await ingest_alpha_vantage_for_company(ticker, connector, session, _retry_state)
        else:
            logger.error(f"{ticker}: Network error after {_retry_state['attempt']} attempts - {str(e)}")
            result.retry_count = _retry_state['attempt']
            raise  # Max retries exceeded

    except asyncio.TimeoutError as e:
        # Timeout errors - will be retried manually
        result.error_message = f"Request timeout: {str(e)}"
        result.error_category = "timeout_error"
        await session.rollback()

        # Retry logic
        _retry_state['attempt'] += 1
        if _retry_state['attempt'] < 3:
            wait_time = min(4 * (2 ** (_retry_state['attempt'] - 1)), 60)  # 4s, 8s, 16s
            logger.warning(f"{ticker}: Timeout (attempt {_retry_state['attempt']}/3), retrying in {wait_time}s")
            await asyncio.sleep(wait_time)
            return await ingest_alpha_vantage_for_company(ticker, connector, session, _retry_state)
        else:
            logger.error(f"{ticker}: Timeout after {_retry_state['attempt']} attempts")
            result.retry_count = _retry_state['attempt']
            raise  # Max retries exceeded

    except Exception as e:
        # Unexpected errors
        result.error_message = f"Unexpected error: {str(e)}"
        result.error_category = "unexpected_error"
        logger.error(f"{ticker}: Unexpected error during ingestion - {str(e)}", exc_info=True)
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
    total_retries = sum(r.retry_count for r in results)
    companies_with_retries = [r.ticker for r in results if r.retry_count > 0]
    succeeded_after_retry = [r.ticker for r in results if r.success and r.retry_count > 0]

    # Categorize failures
    failure_categories = {}
    for r in results:
        if not r.success and r.error_category:
            failure_categories[r.error_category] = failure_categories.get(r.error_category, 0) + 1

    logger.info("-" * 80)
    logger.info("ALPHA VANTAGE INGESTION SUMMARY")
    logger.info("-" * 80)
    logger.info(f"Total companies processed: {len(tickers)}")
    logger.info(f"Successful: {len(successful_companies)}")
    logger.info(f"Failed: {len(failed_companies)}")
    if failed_companies:
        logger.info(f"Failed companies: {', '.join(failed_companies)}")

    # Retry statistics
    logger.info("-" * 80)
    logger.info("RETRY STATISTICS")
    logger.info(f"Total retry attempts: {total_retries}")
    logger.info(f"Companies requiring retries: {len(companies_with_retries)}")
    if companies_with_retries:
        logger.info(f"Companies with retries: {', '.join(companies_with_retries)}")
    logger.info(f"Companies succeeded after retry: {len(succeeded_after_retry)}")
    if succeeded_after_retry:
        logger.info(f"Recovered via retry: {', '.join(succeeded_after_retry)}")

    # Failure analysis
    if failure_categories:
        logger.info("-" * 80)
        logger.info("FAILURE CATEGORIES")
        for category, count in sorted(failure_categories.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {category}: {count} companies")

    # Metrics summary
    logger.info("-" * 80)
    logger.info("METRICS SUMMARY")
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
    await run_coordination_hook("pre-task", description="Alpha Vantage ingestion for EdTech companies")

    # Run ingestion
    try:
        summary = await run_alpha_vantage_ingestion(EDTECH_TICKERS)

        # Post-task hook
        logger.info("Running post-task hook...")
        await run_coordination_hook("post-task", task_id="alpha-vantage-ingestion")

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
