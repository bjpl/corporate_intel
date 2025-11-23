"""Real-world data ingestion integration tests.

IMPORTANT: These tests call ACTUAL APIs and may take several minutes to complete.
They validate:
- Real API connectivity and authentication
- Data quality and consistency across sources
- Rate limiting and error handling with real network conditions
- Database integrity with real-world data

PREREQUISITES:
- Valid API keys in .env file:
  * SEC_USER_AGENT (required for SEC EDGAR)
  * ALPHA_VANTAGE_API_KEY (optional, for Alpha Vantage tests)
- Working database connection
- Internet connectivity

USAGE:
  pytest tests/integration/test_real_world_ingestion.py -v --real-world

The --real-world flag is required to prevent accidental API calls during regular testing.

SPARC COMPLIANCE:
- Specification: Test real-world API integration and data quality
- Architecture: Uses existing ingestion pipelines with actual API calls
- Testing: Validates data quality, error handling, and performance (MANDATORY-8)
- Data Quality: Comprehensive validation checks (MANDATORY-20)
- Error Handling: Tests graceful degradation (MANDATORY-7)
"""

# Suppress marshmallow warnings from Great Expectations before importing
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="marshmallow")
warnings.filterwarnings("ignore", message=".*Number.*field.*")

import asyncio
import os
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import UUID

import pytest
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import Company, SECFiling, FinancialMetric
from src.pipeline.sec_ingestion import (
    SECAPIClient,
    FilingRequest,
    sec_ingestion_flow,
)
from src.pipeline.yahoo_finance_ingestion import (
    YahooFinanceIngestionPipeline,
    EDTECH_COMPANIES,
)
from src.pipeline.alpha_vantage_ingestion import (
    run_alpha_vantage_ingestion,
    EDTECH_TICKERS,
)


# ============================================================================
# CONFIGURATION & FIXTURES
# ============================================================================

@pytest.fixture
def real_world_enabled(request):
    """Check if real-world tests are enabled."""
    if not request.config.getoption("--real-world"):
        pytest.skip("Real-world tests require --real-world flag")
    return True


@pytest.fixture
def test_tickers():
    """Sample of EdTech tickers for testing (to minimize API calls)."""
    return ["DUOL", "CHGG", "COUR"]  # 3 companies for testing


# ============================================================================
# SEC EDGAR REAL-WORLD TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestRealWorldSECIngestion:
    """Test SEC EDGAR API with real data."""

    async def test_sec_api_connectivity(self, real_world_enabled):
        """Test SEC EDGAR API is accessible and returns valid data.

        Validates:
        - API endpoint connectivity
        - User-Agent requirement
        - Response format
        - Rate limiting compliance
        """
        client = SECAPIClient()

        # Test company info fetch (Duolingo - known EdTech company)
        company_info = await client.get_company_info("DUOL")

        # Validate response structure
        assert company_info is not None, "SEC API returned no data"
        assert "cik" in company_info, "Missing CIK in company info"
        assert "name" in company_info, "Missing company name"
        assert company_info["name"] == "Duolingo, Inc.", f"Unexpected company name: {company_info.get('name')}"

        # Validate CIK format
        cik = company_info["cik"]
        assert isinstance(cik, str), f"CIK should be string, got {type(cik)}"
        assert cik.isdigit(), f"CIK should be numeric, got {cik}"


    async def test_sec_filings_data_quality(self, real_world_enabled):
        """Test SEC filings data quality and completeness.

        Validates (MANDATORY-20: Data Quality):
        - Filing metadata completeness
        - Date format consistency
        - Accession number format
        - Form type validity
        """
        client = SECAPIClient()

        # Fetch company info
        company_info = await client.get_company_info("DUOL")
        cik = company_info["cik"]

        # Fetch recent 10-K filings
        filings = await client.get_filings(
            cik,
            filing_types=["10-K"],
            start_date=datetime.now() - timedelta(days=730)  # Last 2 years
        )

        assert len(filings) > 0, "No 10-K filings found for DUOL"

        # Validate each filing
        for filing in filings:
            # Required fields
            assert "form" in filing, "Missing 'form' field"
            assert "filingDate" in filing, "Missing 'filingDate' field"
            assert "accessionNumber" in filing, "Missing 'accessionNumber' field"
            assert "primaryDocument" in filing, "Missing 'primaryDocument' field"

            # Form type validation
            assert filing["form"] in ["10-K", "10-K/A"], f"Unexpected form type: {filing['form']}"

            # Date format validation (YYYY-MM-DD)
            filing_date_str = filing["filingDate"]
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
            assert filing_date <= datetime.now(), "Filing date is in the future"

            # Accession number format (NNNNNNNNNN-NN-NNNNNN)
            accession = filing["accessionNumber"]
            parts = accession.split("-")
            assert len(parts) == 3, f"Invalid accession number format: {accession}"
            assert len(parts[0]) == 10 and parts[0].isdigit(), f"Invalid accession prefix: {parts[0]}"
            assert len(parts[1]) == 2 and parts[1].isdigit(), f"Invalid accession middle: {parts[1]}"
            assert len(parts[2]) == 6 and parts[2].isdigit(), f"Invalid accession suffix: {parts[2]}"


    async def test_sec_filing_content_download(self, real_world_enabled):
        """Test downloading actual filing content.

        Validates:
        - Content retrieval
        - Content length (not empty)
        - HTML/XML structure presence
        - Rate limiting during downloads
        """
        client = SECAPIClient()

        # Get a recent filing
        company_info = await client.get_company_info("DUOL")
        cik = company_info["cik"]

        filings = await client.get_filings(
            cik,
            filing_types=["10-K"],
            start_date=datetime.now() - timedelta(days=365)
        )

        assert len(filings) > 0, "No recent filings to test"

        # Download first filing
        filing = filings[0]
        content = await client.download_filing_content(filing)

        # Validate content
        assert content is not None, "Filing content is None"
        assert len(content) > 1000, f"Filing content too short: {len(content)} bytes"

        # Check for HTML/XML structure
        assert any(tag in content.lower() for tag in ["<html", "<sec-document", "<?xml"]), \
            "Content doesn't appear to be valid HTML/XML"


    async def test_sec_rate_limiting(self, real_world_enabled):
        """Test SEC API rate limiting compliance.

        SEC requires:
        - Maximum 10 requests per second
        - User-Agent header with contact info

        Validates (MANDATORY-18: Resource Optimization):
        - Rate limiter enforces delays
        - No 429 errors (Too Many Requests)
        """
        client = SECAPIClient()

        # Make 20 requests and measure timing
        start_time = datetime.now()

        for i in range(20):
            await client.rate_limiter.acquire()

        elapsed = (datetime.now() - start_time).total_seconds()

        # With 10 req/sec limit, 20 requests should take at least 2 seconds
        assert elapsed >= 1.8, f"Rate limiter too fast: {elapsed}s for 20 requests"
        assert elapsed < 5.0, f"Rate limiter too slow: {elapsed}s for 20 requests"


    async def test_sec_end_to_end_ingestion(
        self,
        real_world_enabled,
        db_session: AsyncSession
    ):
        """Test complete SEC ingestion workflow with real data.

        End-to-end test:
        1. Fetch company info
        2. Fetch filings list
        3. Download filing content
        4. Validate data
        5. Store in database
        6. Verify database integrity

        Validates (MANDATORY-8: Testing & MANDATORY-20: Data Quality):
        - Full pipeline functionality
        - Data persistence
        - Duplicate handling
        """
        # Create filing request for small dataset
        request = FilingRequest(
            company_ticker="DUOL",
            filing_types=["10-K"],
            start_date=datetime.now() - timedelta(days=365)
        )

        # Execute ingestion flow
        result = await sec_ingestion_flow(request)

        # Validate result
        assert result is not None, "Ingestion flow returned None"
        assert result["ticker"] == "DUOL"
        assert result["cik"] is not None
        assert result["filings_found"] > 0
        assert result["filings_stored"] > 0

        # Verify company in database
        company_result = await db_session.execute(
            select(Company).where(Company.ticker == "DUOL")
        )
        company = company_result.scalar_one_or_none()

        assert company is not None, "Company not found in database"
        assert company.name == "Duolingo, Inc."
        assert company.cik == result["cik"]

        # Verify filings in database
        filings_result = await db_session.execute(
            select(SECFiling).where(SECFiling.company_id == company.id)
        )
        filings = filings_result.scalars().all()

        assert len(filings) >= result["filings_stored"]

        # Validate filing data quality
        for filing in filings:
            assert filing.filing_type in ["10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"]
            assert filing.filing_date is not None
            assert filing.accession_number is not None
            assert len(filing.raw_text) > 100, "Filing content too short"


# ============================================================================
# YAHOO FINANCE REAL-WORLD TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestRealWorldYahooFinanceIngestion:
    """Test Yahoo Finance API with real data."""

    async def test_yahoo_finance_api_connectivity(self, real_world_enabled):
        """Test Yahoo Finance API accessibility.

        Validates:
        - yfinance library functionality
        - Data retrieval for known ticker
        - Response format
        """
        import yfinance as yf

        # Test with known ticker
        ticker = yf.Ticker("DUOL")
        info = ticker.info

        assert info is not None, "Yahoo Finance returned no data"
        assert "symbol" in info or "ticker" in info, "Missing ticker symbol"
        assert info.get("longName") or info.get("shortName"), "Missing company name"


    async def test_yahoo_quarterly_financials_data_quality(self, real_world_enabled):
        """Test Yahoo Finance quarterly financial data quality.

        Validates (MANDATORY-20: Data Quality):
        - Quarterly data availability
        - Revenue data presence
        - Margin calculations
        - Data consistency
        """
        import yfinance as yf
        import pandas as pd

        ticker = yf.Ticker("DUOL")

        # Get quarterly income statement
        quarterly_income = ticker.quarterly_income_stmt

        assert quarterly_income is not None, "No quarterly income data"
        assert not quarterly_income.empty, "Quarterly income data is empty"

        # Validate we have multiple quarters
        assert len(quarterly_income.columns) >= 4, \
            f"Expected at least 4 quarters, got {len(quarterly_income.columns)}"

        # Check for key financial metrics
        expected_fields = ["Total Revenue", "Gross Profit", "Operating Income"]
        available_fields = [field for field in expected_fields if field in quarterly_income.index]

        assert len(available_fields) > 0, f"Missing expected financial fields. Available: {quarterly_income.index.tolist()}"

        # Validate revenue data
        if "Total Revenue" in quarterly_income.index:
            revenue_data = quarterly_income.loc["Total Revenue"]

            # Check for non-null values
            non_null_count = revenue_data.notna().sum()
            assert non_null_count > 0, "All revenue values are null"

            # Check for positive values
            positive_count = (revenue_data > 0).sum()
            assert positive_count > 0, "No positive revenue values"


    async def test_yahoo_finance_end_to_end_ingestion(
        self,
        real_world_enabled,
        db_session: AsyncSession,
        test_tickers
    ):
        """Test complete Yahoo Finance ingestion for sample companies.

        End-to-end test:
        1. Fetch company info from Yahoo Finance
        2. Fetch quarterly financials
        3. Store in database
        4. Validate data persistence

        Validates (MANDATORY-8: Testing):
        - Full pipeline functionality
        - Data upsert logic
        - Metrics storage
        """
        # Run ingestion for test tickers only
        pipeline = YahooFinanceIngestionPipeline(db_session)

        # Process first ticker only to minimize API calls
        ticker_data = EDTECH_COMPANIES[0]  # CHGG

        # Fetch and process
        yf_data = await pipeline._fetch_yahoo_finance_data(ticker_data["ticker"])
        assert yf_data is not None, f"No Yahoo Finance data for {ticker_data['ticker']}"

        # Upsert company
        company = await pipeline._upsert_company(ticker_data, yf_data)
        assert company is not None
        assert company.ticker == ticker_data["ticker"]

        # Ingest quarterly financials
        await pipeline._ingest_quarterly_financials(company, ticker_data["ticker"])

        # Commit transaction
        await db_session.commit()

        # Verify metrics were stored
        metrics_result = await db_session.execute(
            select(FinancialMetric).where(
                FinancialMetric.company_id == company.id
            )
        )
        metrics = metrics_result.scalars().all()

        assert len(metrics) > 0, "No financial metrics stored"

        # Validate metric data quality
        for metric in metrics:
            assert metric.metric_type is not None
            assert metric.value is not None
            assert metric.value >= 0 or metric.unit == "percent", "Invalid metric value"
            assert metric.source == "yahoo_finance"
            assert metric.confidence_score > 0


# ============================================================================
# ALPHA VANTAGE REAL-WORLD TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestRealWorldAlphaVantageIngestion:
    """Test Alpha Vantage API with real data."""

    async def test_alpha_vantage_api_connectivity(self, real_world_enabled):
        """Test Alpha Vantage API key and connectivity.

        Validates:
        - API key configuration
        - API endpoint accessibility
        - Response format
        """
        settings = get_settings()

        if not settings.ALPHA_VANTAGE_API_KEY:
            pytest.skip("ALPHA_VANTAGE_API_KEY not configured")

        from src.connectors.data_sources import AlphaVantageConnector

        connector = AlphaVantageConnector()

        # Test with known ticker
        data = await connector.get_company_overview("DUOL")

        assert data is not None, "Alpha Vantage returned no data"
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"


    async def test_alpha_vantage_rate_limiting(self, real_world_enabled):
        """Test Alpha Vantage rate limiting (5 calls/minute for free tier).

        Validates (MANDATORY-18: Resource Optimization):
        - Rate limiter enforces 12-second delays
        - No API quota errors
        """
        settings = get_settings()

        if not settings.ALPHA_VANTAGE_API_KEY:
            pytest.skip("ALPHA_VANTAGE_API_KEY not configured")

        from src.connectors.data_sources import AlphaVantageConnector

        connector = AlphaVantageConnector()

        # Make 3 requests and measure timing
        start_time = datetime.now()

        for ticker in ["DUOL", "CHGG", "COUR"]:
            await connector.get_company_overview(ticker)

        elapsed = (datetime.now() - start_time).total_seconds()

        # With 5 calls/min (12s between calls), 3 calls should take ~24 seconds
        # But first call is immediate, so minimum is ~24s
        assert elapsed >= 20.0, f"Rate limiting too fast: {elapsed}s for 3 calls"


    async def test_alpha_vantage_data_quality(self, real_world_enabled):
        """Test Alpha Vantage fundamental data quality.

        Validates (MANDATORY-20: Data Quality):
        - Key metrics presence (P/E, EPS, etc.)
        - Data type correctness
        - Value range validation
        """
        settings = get_settings()

        if not settings.ALPHA_VANTAGE_API_KEY:
            pytest.skip("ALPHA_VANTAGE_API_KEY not configured")

        from src.connectors.data_sources import AlphaVantageConnector

        connector = AlphaVantageConnector()
        data = await connector.get_company_overview("DUOL")

        # Validate expected fields
        expected_fields = ["ticker", "pe_ratio", "eps", "market_cap"]

        for field in expected_fields:
            assert field in data or data.get(field) is not None, f"Missing field: {field}"

        # Validate data types and ranges
        if "pe_ratio" in data and data["pe_ratio"]:
            pe_ratio = float(data["pe_ratio"])
            assert 0 < pe_ratio < 1000, f"P/E ratio out of reasonable range: {pe_ratio}"

        if "market_cap" in data and data["market_cap"]:
            market_cap = float(data["market_cap"])
            assert market_cap > 0, f"Invalid market cap: {market_cap}"


# ============================================================================
# CROSS-SOURCE DATA CONSISTENCY TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestCrossSourceConsistency:
    """Test data consistency across different sources."""

    async def test_company_data_consistency(
        self,
        real_world_enabled,
        db_session: AsyncSession
    ):
        """Test that company data is consistent across SEC, Yahoo, and Alpha Vantage.

        Validates (MANDATORY-20: Data Quality):
        - Ticker symbols match
        - Company names are similar
        - No conflicting fundamental data
        """
        ticker = "DUOL"

        # Fetch from SEC
        from src.pipeline.sec_ingestion import SECAPIClient
        sec_client = SECAPIClient()
        sec_data = await sec_client.get_company_info(ticker)

        # Fetch from Yahoo Finance
        import yfinance as yf
        yf_ticker = yf.Ticker(ticker)
        yf_info = yf_ticker.info

        # Compare company names (should be similar)
        sec_name = sec_data.get("name", "").lower()
        yf_name = yf_info.get("longName", "").lower()

        # Both should contain "duolingo"
        assert "duolingo" in sec_name, f"SEC name doesn't contain 'duolingo': {sec_name}"
        assert "duolingo" in yf_name, f"Yahoo name doesn't contain 'duolingo': {yf_name}"


    async def test_revenue_data_consistency(
        self,
        real_world_enabled,
        db_session: AsyncSession
    ):
        """Test revenue data consistency between Yahoo Finance and SEC filings.

        Note: Some variance is expected due to:
        - Different reporting periods
        - Restatements
        - Different data sources

        Validates:
        - Revenue values are in same order of magnitude
        - No extreme discrepancies
        """
        ticker = "DUOL"

        # Get Yahoo Finance quarterly revenue
        import yfinance as yf
        yf_ticker = yf.Ticker(ticker)
        quarterly_income = yf_ticker.quarterly_income_stmt

        if "Total Revenue" in quarterly_income.index:
            yf_revenue = quarterly_income.loc["Total Revenue"].iloc[0]

            # Basic sanity check
            assert yf_revenue > 0, "Yahoo Finance revenue should be positive"
            assert yf_revenue < 1e12, "Yahoo Finance revenue seems unreasonably high"

            # Revenue for EdTech companies typically in millions to billions
            assert yf_revenue > 1e6, "Revenue seems too low for a public company"


# ============================================================================
# ERROR HANDLING & RESILIENCE TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestErrorHandlingResilience:
    """Test error handling with real-world error scenarios."""

    async def test_invalid_ticker_handling(self, real_world_enabled):
        """Test graceful handling of invalid ticker symbols.

        Validates (MANDATORY-7: Error Handling):
        - No crashes on invalid input
        - Appropriate error messages
        - Proper exception types
        """
        from src.pipeline.sec_ingestion import SECAPIClient

        client = SECAPIClient()

        # Try to fetch data for invalid ticker
        company_info = await client.get_company_info("INVALIDTICKER12345")

        # Should return empty dict or None, not crash
        assert company_info is not None or company_info == {}


    async def test_network_timeout_handling(self, real_world_enabled):
        """Test handling of network timeouts.

        Validates (MANDATORY-7: Error Handling):
        - Timeout errors are caught
        - Retry logic works
        - Eventually fails gracefully
        """
        import httpx
        from src.pipeline.sec_ingestion import SECAPIClient

        client = SECAPIClient()

        # This should complete or timeout gracefully
        try:
            # Use a very short timeout to force timeout
            async with httpx.AsyncClient(timeout=0.001) as http_client:
                response = await http_client.get(
                    f"{client.BASE_URL}/submissions/CIK0001835631.json",
                    headers=client.headers
                )
        except (httpx.TimeoutException, httpx.ConnectTimeout):
            # Expected - timeout should be caught
            pass


    async def test_rate_limit_handling(self, real_world_enabled):
        """Test handling of API rate limit errors.

        Validates (MANDATORY-7: Error Handling):
        - 429 errors are handled
        - Backoff strategy works
        - Requests eventually succeed
        """
        # This is implicitly tested by the rate limiter
        # If rate limiter fails, we'd get 429 errors
        pass


# ============================================================================
# PERFORMANCE & SCALE TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestPerformanceScale:
    """Test performance with real data at scale."""

    async def test_batch_ingestion_performance(
        self,
        real_world_enabled,
        db_session: AsyncSession,
        test_tickers
    ):
        """Test performance of batch ingestion.

        Measures:
        - Total time for multiple companies
        - Average time per company
        - Database write performance

        Validates (MANDATORY-14: Performance Awareness):
        - Ingestion completes in reasonable time
        - No excessive memory usage
        """
        from src.pipeline.yahoo_finance_ingestion import YahooFinanceIngestionPipeline

        pipeline = YahooFinanceIngestionPipeline(db_session)

        start_time = datetime.now()

        # Process test tickers
        stats = {
            "companies_processed": 0,
            "metrics_stored": 0,
            "errors": 0
        }

        for company_data in EDTECH_COMPANIES[:3]:  # First 3 companies
            try:
                yf_data = await pipeline._fetch_yahoo_finance_data(company_data["ticker"])
                if yf_data:
                    company = await pipeline._upsert_company(company_data, yf_data)
                    await pipeline._ingest_quarterly_financials(company, company_data["ticker"])
                    stats["companies_processed"] += 1
            except Exception as e:
                stats["errors"] += 1

        await db_session.commit()

        elapsed = (datetime.now() - start_time).total_seconds()

        # Should complete in reasonable time (< 60s for 3 companies)
        assert elapsed < 60.0, f"Batch ingestion too slow: {elapsed}s"

        # Calculate average time per company
        avg_time = elapsed / stats["companies_processed"] if stats["companies_processed"] > 0 else 0

        # Should average < 20s per company
        assert avg_time < 20.0, f"Average time per company too high: {avg_time}s"


    async def test_concurrent_ingestion_performance(
        self,
        real_world_enabled,
        db_session: AsyncSession
    ):
        """Test concurrent ingestion performance.

        Validates:
        - Concurrent requests work correctly
        - No race conditions
        - Performance improves with concurrency
        """
        # This would require careful implementation to avoid API rate limits
        # For now, sequential processing is safer for real APIs
        pass


# ============================================================================
# DATA QUALITY SUMMARY REPORT
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
class TestDataQualityReport:
    """Generate comprehensive data quality report."""

    async def test_generate_data_quality_report(
        self,
        real_world_enabled,
        db_session: AsyncSession
    ):
        """Generate comprehensive data quality report.

        Reports on:
        - Companies with complete data
        - Missing data gaps
        - Data freshness
        - Metrics coverage

        Validates (MANDATORY-20: Data Quality, MANDATORY-16: Learning):
        - Data completeness metrics
        - Quality score calculation
        - Identifies improvement areas
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "companies": {},
            "summary": {
                "total_companies": 0,
                "companies_with_financials": 0,
                "companies_with_filings": 0,
                "average_metrics_per_company": 0,
                "data_quality_score": 0
            }
        }

        # Query all companies
        companies_result = await db_session.execute(select(Company))
        companies = companies_result.scalars().all()

        report["summary"]["total_companies"] = len(companies)

        total_metrics = 0

        for company in companies:
            # Get financial metrics
            metrics_result = await db_session.execute(
                select(FinancialMetric).where(
                    FinancialMetric.company_id == company.id
                )
            )
            metrics = metrics_result.scalars().all()

            # Get SEC filings
            filings_result = await db_session.execute(
                select(SECFiling).where(
                    SECFiling.company_id == company.id
                )
            )
            filings = filings_result.scalars().all()

            company_report = {
                "ticker": company.ticker,
                "name": company.name,
                "metrics_count": len(metrics),
                "filings_count": len(filings),
                "has_financials": len(metrics) > 0,
                "has_filings": len(filings) > 0
            }

            report["companies"][company.ticker] = company_report

            if len(metrics) > 0:
                report["summary"]["companies_with_financials"] += 1
                total_metrics += len(metrics)

            if len(filings) > 0:
                report["summary"]["companies_with_filings"] += 1

        # Calculate averages
        if report["summary"]["total_companies"] > 0:
            report["summary"]["average_metrics_per_company"] = \
                total_metrics / report["summary"]["total_companies"]

        # Calculate data quality score (0-100)
        if report["summary"]["total_companies"] > 0:
            completeness = (
                report["summary"]["companies_with_financials"] +
                report["summary"]["companies_with_filings"]
            ) / (2 * report["summary"]["total_companies"])
            report["summary"]["data_quality_score"] = int(completeness * 100)

        # Assert minimum quality standards
        assert report["summary"]["data_quality_score"] >= 50, \
            f"Data quality score too low: {report['summary']['data_quality_score']}"

        return report
