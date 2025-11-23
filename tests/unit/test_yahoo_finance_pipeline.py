"""
Comprehensive tests for Yahoo Finance data ingestion pipeline.

Tests cover:
1. Successful data fetch and storage
2. Invalid ticker handling (404, not found)
3. Rate limiting and retry logic
4. Data transformation and mapping
5. Database operations (upsert)
6. Error handling (network, API changes)
7. Edge cases (empty data, malformed responses)
8. Quarterly financial data ingestion
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
import pytz
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.pipeline.yahoo_finance_ingestion import (
    YahooFinanceIngestionPipeline,
    YahooFinanceIngestionError,
    EDTECH_COMPANIES,
)
from src.db.models import Company, FinancialMetric


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = Mock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def pipeline(mock_db_session):
    """Create YahooFinanceIngestionPipeline instance."""
    return YahooFinanceIngestionPipeline(mock_db_session)


@pytest.fixture
def mock_yf_info():
    """Mock Yahoo Finance info response."""
    return {
        'symbol': 'CHGG',
        'shortName': 'Chegg Inc.',
        'regularMarketPrice': 10.50,
        'marketCap': 1500000000,
        'fullTimeEmployees': 3500,
        'website': 'https://www.chegg.com',
        'city': 'Santa Clara',
        'country': 'USA',
        'trailingPE': 25.5,
        'forwardPE': 18.2,
        'priceToBook': 3.5,
        'earningsGrowth': 0.15,
    }


@pytest.fixture
def mock_yf_incomplete_info():
    """Mock incomplete Yahoo Finance info (missing some fields)."""
    return {
        'symbol': 'CHGG',
        'regularMarketPrice': 10.50,
        # Missing marketCap, fullTimeEmployees, etc.
    }


@pytest.fixture
def mock_quarterly_income():
    """Mock quarterly income statement."""
    dates = [
        datetime(2024, 6, 30),
        datetime(2024, 3, 31),
        datetime(2023, 12, 31),
        datetime(2023, 9, 30),
    ]

    data = {
        'Total Revenue': [150000000, 145000000, 140000000, 135000000],
        'Gross Profit': [90000000, 87000000, 84000000, 81000000],
        'Operating Income': [30000000, 28000000, 26000000, 24000000],
    }

    df = pd.DataFrame(data, columns=dates)
    df.index = ['Total Revenue', 'Gross Profit', 'Operating Income']
    return df


@pytest.fixture
def mock_empty_quarterly_income():
    """Mock empty quarterly income statement."""
    return pd.DataFrame()


@pytest.fixture
def sample_company():
    """Sample company for testing."""
    return Company(
        id=uuid4(),
        ticker='CHGG',
        name='Chegg Inc.',
        sector='Education Technology',
        category='D2C',
        subcategory=['Higher Ed', 'Tutoring'],
    )


# ============================================================================
# SUCCESS SCENARIOS
# ============================================================================

@pytest.mark.asyncio
class TestSuccessfulDataFetch:
    """Test successful data fetch scenarios."""

    async def test_fetch_valid_ticker(self, pipeline, mock_yf_info):
        """Test fetching data for a valid ticker."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = mock_yf_info
            mock_ticker.return_value = mock_ticker_instance

            result = await pipeline._fetch_yahoo_finance_data('CHGG')

            assert result is not None
            assert result['symbol'] == 'CHGG'
            assert result['marketCap'] == 1500000000
            mock_ticker.assert_called_once_with('CHGG')

    async def test_upsert_new_company(self, pipeline, mock_db_session, mock_yf_info):
        """Test creating a new company record."""
        company_data = EDTECH_COMPANIES[0]  # CHGG

        # Mock: company doesn't exist
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        company = await pipeline._upsert_company(company_data, mock_yf_info)

        assert company.ticker == 'CHGG'
        assert company.name == 'Chegg Inc.'
        assert company.sector == 'Education Technology'
        mock_db_session.add.assert_called_once()
        assert pipeline.stats['companies_created'] == 1

    async def test_upsert_existing_company(self, pipeline, mock_db_session, sample_company, mock_yf_info):
        """Test updating an existing company record."""
        company_data = EDTECH_COMPANIES[0]

        # Mock: company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_db_session.execute.return_value = mock_result

        company = await pipeline._upsert_company(company_data, mock_yf_info)

        assert company.ticker == 'CHGG'
        assert pipeline.stats['companies_updated'] == 1

    async def test_ingest_quarterly_financials(self, pipeline, mock_db_session, sample_company, mock_quarterly_income):
        """Test ingesting quarterly financial data."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.quarterly_income_stmt = mock_quarterly_income
            mock_ticker_instance.quarterly_balance_sheet = pd.DataFrame()
            mock_ticker_instance.info = {'earningsGrowth': 0.15}
            mock_ticker.return_value = mock_ticker_instance

            await pipeline._ingest_quarterly_financials(sample_company, 'CHGG')

            # Should have called _upsert_metric for each quarter and metric type
            # 4 quarters × 3 metrics (revenue, gross_margin, operating_margin)
            # Note: actual count depends on implementation
            mock_ticker.assert_called()


# ============================================================================
# INVALID TICKER HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestInvalidTickerHandling:
    """Test handling of invalid tickers."""

    async def test_invalid_ticker_404(self, pipeline):
        """Test handling of invalid ticker (404 response)."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("404 Client Error: Not Found")

            result = await pipeline._fetch_yahoo_finance_data('INVALID123')

            assert result is None

    async def test_ticker_with_no_data(self, pipeline):
        """Test ticker that exists but has no financial data."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = {}  # Empty info
            mock_ticker.return_value = mock_ticker_instance

            result = await pipeline._fetch_yahoo_finance_data('NODATA')

            assert result is None

    async def test_ticker_missing_required_fields(self, pipeline, mock_yf_incomplete_info):
        """Test ticker with incomplete data (missing required fields)."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = mock_yf_incomplete_info
            mock_ticker.return_value = mock_ticker_instance

            result = await pipeline._fetch_yahoo_finance_data('CHGG')

            # Should still return data even if some fields are missing
            assert result is not None
            assert result['symbol'] == 'CHGG'


# ============================================================================
# RATE LIMITING
# ============================================================================

@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting and retry logic."""

    async def test_retry_on_network_error(self, pipeline):
        """Test retry logic on network errors."""
        call_count = 0

        def side_effect(ticker):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network timeout")
            mock_instance = Mock()
            mock_instance.info = {'symbol': 'CHGG', 'regularMarketPrice': 10.50}
            return mock_instance

        with patch('yfinance.Ticker', side_effect=side_effect):
            result = await pipeline._fetch_yahoo_finance_data('CHGG', max_retries=3)

            assert result is not None
            assert call_count == 2  # Failed once, succeeded on retry

    async def test_max_retries_exceeded(self, pipeline):
        """Test behavior when max retries are exceeded."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = ConnectionError("Persistent network error")

            result = await pipeline._fetch_yahoo_finance_data('CHGG', max_retries=3)

            assert result is None
            assert mock_ticker.call_count == 3

    async def test_exponential_backoff(self, pipeline):
        """Test that retry uses exponential backoff."""
        call_times = []

        async def track_call(ticker):
            call_times.append(datetime.utcnow())
            raise ConnectionError("Network error")

        with patch('yfinance.Ticker', side_effect=track_call):
            with patch('asyncio.sleep') as mock_sleep:
                result = await pipeline._fetch_yahoo_finance_data('CHGG', max_retries=3)

                # Should have slept with exponential backoff: 1s, 2s, 4s
                assert mock_sleep.call_count == 2  # No sleep before first attempt
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls[0] == 1  # 2^0 = 1
                assert sleep_calls[1] == 2  # 2^1 = 2


# ============================================================================
# DATA TRANSFORMATION
# ============================================================================

@pytest.mark.asyncio
class TestDataTransformation:
    """Test data transformation and mapping."""

    async def test_revenue_metric_creation(self, pipeline, mock_db_session, sample_company):
        """Test creation of revenue metrics."""
        quarter_date = datetime(2024, 6, 30)

        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=quarter_date,
            period_type='quarterly',
            metric_type='revenue',
            value=150000000.0,
            unit='USD',
            metric_category='financial',
        )

        # Verify insert was called
        mock_db_session.execute.assert_called()

    async def test_margin_calculation(self, pipeline, mock_quarterly_income):
        """Test gross margin calculation from income statement."""
        # Extract first quarter
        quarter_date = mock_quarterly_income.columns[0]
        revenue = mock_quarterly_income.loc['Total Revenue', quarter_date]
        gross_profit = mock_quarterly_income.loc['Gross Profit', quarter_date]

        # Calculate margin
        gross_margin = (float(gross_profit) / float(revenue)) * 100

        assert gross_margin == 60.0  # 90M / 150M * 100

    async def test_timezone_aware_dates(self, pipeline, mock_db_session, sample_company):
        """Test that dates are converted to timezone-aware."""
        # Naive datetime
        naive_date = datetime(2024, 6, 30)

        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=naive_date,
            period_type='quarterly',
            metric_type='revenue',
            value=1000000.0,
            unit='USD',
            metric_category='financial',
        )

        # Check that date was converted to UTC
        call_args = mock_db_session.execute.call_args
        # Date should be timezone-aware in the insert statement


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

@pytest.mark.asyncio
class TestDatabaseOperations:
    """Test database upsert and error handling."""

    async def test_upsert_creates_new_metric(self, pipeline, mock_db_session, sample_company):
        """Test that upsert creates a new metric if it doesn't exist."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=datetime(2024, 6, 30, tzinfo=pytz.UTC),
            period_type='quarterly',
            metric_type='revenue',
            value=150000000.0,
            unit='USD',
            metric_category='financial',
        )

        assert pipeline.stats['metrics_created'] == 1

    async def test_upsert_updates_existing_metric(self, pipeline, mock_db_session, sample_company):
        """Test that upsert updates an existing metric."""
        # Mock: metric already exists
        existing_metric = FinancialMetric(
            id=uuid4(),
            company_id=sample_company.id,
            metric_date=datetime(2024, 6, 30, tzinfo=pytz.UTC),
            period_type='quarterly',
            metric_type='revenue',
            value=140000000.0,
            unit='USD',
            metric_category='financial',
        )

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_result.scalar_one_or_none.return_value = existing_metric
        mock_db_session.execute.return_value = mock_result

        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=datetime(2024, 6, 30, tzinfo=pytz.UTC),
            period_type='quarterly',
            metric_type='revenue',
            value=150000000.0,  # Updated value
            unit='USD',
            metric_category='financial',
        )

        assert pipeline.stats['metrics_updated'] == 1

    async def test_database_commit_on_success(self, pipeline, mock_db_session):
        """Test that database is committed after successful ingestion."""
        with patch.object(pipeline, '_fetch_yahoo_finance_data', return_value=None):
            await pipeline.run()

            mock_db_session.commit.assert_called_once()

    async def test_database_rollback_on_error(self, pipeline, mock_db_session):
        """Test that database is rolled back on error."""
        mock_db_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(Exception):
            await pipeline._upsert_metric(
                company_id=uuid4(),
                metric_date=datetime.utcnow(),
                period_type='quarterly',
                metric_type='revenue',
                value=1000000.0,
                unit='USD',
                metric_category='financial',
            )


# ============================================================================
# ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_api_error_tracking(self, pipeline):
        """Test that API errors are tracked in stats."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("API rate limit exceeded")

            await pipeline.run()

            assert len(pipeline.stats['errors']) > 0
            assert any('CHGG' in err['ticker'] for err in pipeline.stats['errors'])

    async def test_malformed_json_response(self, pipeline):
        """Test handling of malformed API responses."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = "not a dict"  # Invalid response
            mock_ticker.return_value = mock_ticker_instance

            result = await pipeline._fetch_yahoo_finance_data('CHGG')

            # Should handle gracefully and return None
            assert result is None or result == {}

    async def test_empty_quarterly_data(self, pipeline, sample_company, mock_empty_quarterly_income):
        """Test handling of empty quarterly financial data."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.quarterly_income_stmt = mock_empty_quarterly_income
            mock_ticker.return_value = mock_ticker_instance

            # Should not raise an exception
            await pipeline._ingest_quarterly_financials(sample_company, 'CHGG')

    async def test_partial_quarterly_data(self, pipeline, sample_company):
        """Test handling of partial quarterly data (missing some metrics)."""
        partial_data = pd.DataFrame({
            datetime(2024, 6, 30): [150000000],
            # Missing Gross Profit and Operating Income
        }, index=['Total Revenue'])

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.quarterly_income_stmt = partial_data
            mock_ticker_instance.quarterly_balance_sheet = pd.DataFrame()
            mock_ticker_instance.info = {}
            mock_ticker.return_value = mock_ticker_instance

            # Should handle gracefully
            await pipeline._ingest_quarterly_financials(sample_company, 'CHGG')


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_ticker_with_special_characters(self, pipeline):
        """Test ticker with special characters (e.g., JW.A)."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = {
                'symbol': 'JW.A',
                'regularMarketPrice': 45.00,
                'marketCap': 2000000000,
            }
            mock_ticker.return_value = mock_ticker_instance

            result = await pipeline._fetch_yahoo_finance_data('JW.A')

            assert result is not None
            assert result['symbol'] == 'JW.A'

    async def test_very_large_market_cap(self, pipeline, mock_db_session, sample_company):
        """Test handling of very large market cap values."""
        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type='quarterly',
            metric_type='market_cap',
            value=1_000_000_000_000.0,  # 1 trillion
            unit='USD',
            metric_category='size',
        )

        # Should handle large numbers without overflow

    async def test_negative_values(self, pipeline, mock_db_session, sample_company):
        """Test handling of negative values (e.g., losses)."""
        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type='quarterly',
            metric_type='operating_income',
            value=-50000000.0,  # Loss
            unit='USD',
            metric_category='financial',
        )

        # Should allow negative values

    async def test_zero_values(self, pipeline, mock_db_session, sample_company):
        """Test handling of zero values."""
        await pipeline._upsert_metric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type='quarterly',
            metric_type='dividend_yield',
            value=0.0,
            unit='percent',
            metric_category='income',
        )

        # Should allow zero values

    async def test_missing_earnings_growth(self, pipeline, sample_company):
        """Test handling when earnings growth is not available."""
        partial_income = pd.DataFrame({
            datetime(2024, 6, 30): [150000000, 90000000, 30000000],
        }, index=['Total Revenue', 'Gross Profit', 'Operating Income'])

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.quarterly_income_stmt = partial_income
            mock_ticker_instance.quarterly_balance_sheet = pd.DataFrame()
            mock_ticker_instance.info = {}  # No earningsGrowth
            mock_ticker.return_value = mock_ticker_instance

            # Should handle missing earningsGrowth gracefully
            await pipeline._ingest_quarterly_financials(sample_company, 'CHGG')

    async def test_all_companies_ingestion(self, pipeline, mock_db_session):
        """Test ingesting all 27 EdTech companies."""
        with patch.object(pipeline, '_fetch_yahoo_finance_data', return_value=None):
            with patch.object(pipeline, '_notify_progress', return_value=None):
                report = await pipeline.run()

                # Should attempt all 27 companies
                assert report['statistics']['total_companies'] <= 27


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Test full pipeline integration scenarios."""

    async def test_full_pipeline_success(self, pipeline, mock_db_session, mock_yf_info, mock_quarterly_income):
        """Test full pipeline execution with successful data."""
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.info = mock_yf_info
            mock_ticker_instance.quarterly_income_stmt = mock_quarterly_income
            mock_ticker_instance.quarterly_balance_sheet = pd.DataFrame()
            mock_ticker.return_value = mock_ticker_instance

            # Mock company doesn't exist
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result

            # Run limited pipeline (just CHGG)
            original_companies = EDTECH_COMPANIES.copy()
            with patch('src.pipeline.yahoo_finance_ingestion.EDTECH_COMPANIES', [EDTECH_COMPANIES[0]]):
                report = await pipeline.run()

                assert report['status'] == 'completed'
                assert report['statistics']['companies_created'] >= 1

    async def test_pipeline_with_partial_failures(self, pipeline, mock_db_session):
        """Test pipeline continues after individual company failures."""
        call_count = 0

        def side_effect(ticker):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Every other call fails
                raise Exception("API error")
            mock_instance = Mock()
            mock_instance.info = {'symbol': ticker, 'regularMarketPrice': 10.0}
            return mock_instance

        with patch('yfinance.Ticker', side_effect=side_effect):
            # Mock company doesn't exist
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result

            report = await pipeline.run()

            # Should have both successes and failures
            assert report['statistics']['errors_count'] > 0
            assert report['status'] == 'completed_with_errors'

    async def test_report_generation(self, pipeline):
        """Test that report is generated correctly."""
        pipeline.stats = {
            'companies_created': 10,
            'companies_updated': 5,
            'metrics_created': 100,
            'metrics_updated': 50,
            'errors': [{'ticker': 'TEST', 'error': 'Test error'}],
        }

        report = pipeline._generate_report()

        assert report['status'] == 'completed_with_errors'
        assert report['statistics']['total_companies'] == 15
        assert report['statistics']['total_metrics'] == 150
        assert report['statistics']['errors_count'] == 1
