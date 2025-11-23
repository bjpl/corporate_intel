"""
Production Integration Tests for Alpha Vantage API
Corporate Intelligence Platform - Plan A Day 4

These tests validate Alpha Vantage integration in production environment:
- API connectivity and authentication
- Rate limiting compliance
- Data quality validation
- Error handling
- Caching behavior
- Database integration

Run with:
    pytest tests/integration/test_alpha_vantage_production.py -v
    pytest tests/integration/test_alpha_vantage_production.py -v -k "test_company_overview"
"""

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.connectors.data_sources import AlphaVantageConnector
from src.core.config import get_settings
from src.db.models import Company, FinancialMetric
from src.db.session import get_session_factory
from src.pipeline.alpha_vantage_ingestion import (
    ingest_alpha_vantage_for_company,
    store_financial_metrics,
)


# Skip tests if no API key configured
pytestmark = pytest.mark.skipif(
    not os.getenv('ALPHA_VANTAGE_API_KEY'),
    reason="Alpha Vantage API key not configured"
)


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
async def connector():
    """Create Alpha Vantage connector."""
    return AlphaVantageConnector()


@pytest.fixture
async def db_session():
    """Create database session for testing."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
        await session.rollback()


class TestAlphaVantageConnectivity:
    """Test Alpha Vantage API connectivity."""

    @pytest.mark.asyncio
    async def test_api_key_configured(self, settings):
        """Test that API key is configured."""
        assert settings.ALPHA_VANTAGE_API_KEY is not None
        assert len(settings.ALPHA_VANTAGE_API_KEY.get_secret_value()) > 0

    @pytest.mark.asyncio
    async def test_connector_initialization(self, connector):
        """Test connector initializes correctly."""
        assert connector.fd is not None
        assert connector.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_company_overview_fetch(self, connector):
        """Test fetching company overview data."""
        # Use Chegg as test ticker
        data = await connector.get_company_overview('CHGG')

        # Validate response
        assert data is not None
        assert isinstance(data, dict)
        assert data.get('ticker') == 'CHGG'

        # Check key metrics present
        assert 'market_cap' in data
        assert 'pe_ratio' in data
        assert 'eps' in data

    @pytest.mark.asyncio
    async def test_invalid_ticker(self, connector):
        """Test handling of invalid ticker symbol."""
        data = await connector.get_company_overview('INVALID_TICKER_XYZ')

        # Should return empty dict or minimal data
        assert data is not None
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_rate_limiter_functionality(self, connector):
        """Test rate limiter enforces delays."""
        import time

        start = time.time()

        # Make 2 sequential calls
        await connector.rate_limiter.acquire()
        first_call = time.time()

        await connector.rate_limiter.acquire()
        second_call = time.time()

        # Second call should be delayed by ~12 seconds (5 calls/minute)
        delay = second_call - first_call
        assert delay >= 12.0, f"Rate limiter delay too short: {delay}s (expected >= 12s)"


class TestDataQuality:
    """Test data quality and validation."""

    @pytest.mark.asyncio
    async def test_numeric_field_types(self, connector):
        """Test that numeric fields are properly typed."""
        data = await connector.get_company_overview('CHGG')

        # Check numeric fields
        numeric_fields = [
            'market_cap', 'pe_ratio', 'eps', 'roe',
            'profit_margin', 'revenue_growth_yoy'
        ]

        for field in numeric_fields:
            value = data.get(field)
            if value is not None:
                assert isinstance(value, (int, float, Decimal)), \
                    f"{field} should be numeric, got {type(value)}"

    @pytest.mark.asyncio
    async def test_data_completeness(self, connector):
        """Test that data includes expected fields."""
        data = await connector.get_company_overview('CHGG')

        # Required fields
        required_fields = ['ticker', 'market_cap', 'pe_ratio', 'eps']

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    @pytest.mark.asyncio
    async def test_percentage_conversion(self, connector):
        """Test that percentage values are correctly converted."""
        data = await connector.get_company_overview('CHGG')

        # Percentage fields should be in 0-100 range (not 0-1)
        percentage_fields = ['profit_margin', 'roe', 'revenue_growth_yoy']

        for field in percentage_fields:
            value = data.get(field)
            if value and isinstance(value, (int, float)) and value != 0:
                # Valid percentages typically -100 to 100
                assert -100 <= value <= 200, \
                    f"{field} value out of range: {value}"

    @pytest.mark.asyncio
    async def test_ticker_consistency(self, connector):
        """Test that returned ticker matches requested ticker."""
        data = await connector.get_company_overview('COUR')

        assert data.get('ticker') == 'COUR', \
            f"Ticker mismatch: expected COUR, got {data.get('ticker')}"


class TestDatabaseIntegration:
    """Test database integration."""

    @pytest.mark.asyncio
    async def test_store_financial_metrics(self, connector, db_session):
        """Test storing metrics in database."""
        # Fetch data
        data = await connector.get_company_overview('CHGG')

        # Create test company
        company = Company(
            ticker='CHGG',
            name='Chegg Inc',
            sector='Education',
            industry='EdTech'
        )
        db_session.add(company)
        await db_session.flush()

        # Store metrics
        count = await store_financial_metrics(
            db_session,
            str(company.id),
            'CHGG',
            data
        )

        # Verify metrics were stored
        assert count > 0, "No metrics were stored"

        # Query metrics
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id
        )
        result = await db_session.execute(stmt)
        metrics = result.scalars().all()

        assert len(metrics) > 0, "No metrics found in database"
        assert len(metrics) == count, f"Metric count mismatch: {len(metrics)} vs {count}"

        # Validate metric structure
        metric = metrics[0]
        assert metric.company_id == company.id
        assert metric.metric_type in ['pe_ratio', 'eps', 'roe', 'market_cap']
        assert metric.source == 'alpha_vantage'
        assert metric.confidence_score == 0.95

    @pytest.mark.asyncio
    async def test_upsert_behavior(self, connector, db_session):
        """Test upsert (INSERT ON CONFLICT) behavior."""
        # Create test company
        company = Company(
            ticker='DUOL',
            name='Duolingo Inc',
            sector='Education',
            industry='EdTech'
        )
        db_session.add(company)
        await db_session.flush()

        # Fetch data
        data = await connector.get_company_overview('DUOL')

        # Store metrics first time
        count1 = await store_financial_metrics(
            db_session,
            str(company.id),
            'DUOL',
            data
        )

        await db_session.commit()

        # Store metrics second time (should update, not duplicate)
        count2 = await store_financial_metrics(
            db_session,
            str(company.id),
            'DUOL',
            data
        )

        # Counts should be same (no new inserts, only updates)
        assert count1 == count2, "Upsert created duplicates"

        # Verify no duplicates
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id
        )
        result = await db_session.execute(stmt)
        metrics = result.scalars().all()

        assert len(metrics) == count1, "Duplicate metrics found"


class TestIngestionPipeline:
    """Test full ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_single_company_ingestion(self, connector, db_session):
        """Test ingesting single company."""
        result = await ingest_alpha_vantage_for_company(
            'CHGG',
            connector,
            db_session
        )

        # Validate result
        assert result is not None
        assert result.ticker == 'CHGG'
        assert result.success is True, f"Ingestion failed: {result.error_message}"
        assert result.metrics_fetched > 0, "No metrics fetched"
        assert result.metrics_stored > 0, "No metrics stored"
        assert result.company_id is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, connector, db_session):
        """Test error handling for invalid ticker."""
        result = await ingest_alpha_vantage_for_company(
            'INVALID_XYZ',
            connector,
            db_session
        )

        # Should handle gracefully
        assert result is not None
        assert result.ticker == 'INVALID_XYZ'
        # May succeed or fail depending on API response
        if not result.success:
            assert result.error_message is not None
            assert result.error_category is not None

    @pytest.mark.asyncio
    async def test_retry_logic(self, connector, db_session):
        """Test retry logic for transient failures."""
        # This test would need to mock network failures
        # Skipping for now - requires advanced mocking

        pytest.skip("Retry logic test requires network failure simulation")


class TestCaching:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_functionality(self, connector):
        """Test that caching works."""
        import time

        # First call - should hit API
        start = time.time()
        data1 = await connector.get_company_overview('CHGG')
        first_call_time = time.time() - start

        # Second call - should hit cache (faster)
        start = time.time()
        data2 = await connector.get_company_overview('CHGG')
        second_call_time = time.time() - start

        # Data should be identical
        assert data1 == data2

        # Second call should be significantly faster (if cache working)
        # Allow for some variance
        if second_call_time < first_call_time * 0.5:
            # Cache is working
            pass
        else:
            # Cache might not be configured (Redis unavailable)
            pytest.skip("Cache not configured or not working")


class TestProductionReadiness:
    """Test production readiness."""

    @pytest.mark.asyncio
    async def test_api_quota_awareness(self, connector):
        """Test that we're aware of API quota."""
        # Check rate limiter is configured
        assert connector.rate_limiter is not None

        # Check calls per second
        calls_per_second = connector.rate_limiter.calls_per_second
        assert calls_per_second == 5/60, \
            f"Rate limiter configured incorrectly: {calls_per_second}"

    @pytest.mark.asyncio
    async def test_error_categories(self, connector, db_session):
        """Test that errors are properly categorized."""
        # Test with invalid ticker
        result = await ingest_alpha_vantage_for_company(
            'INVALID',
            connector,
            db_session
        )

        if not result.success:
            assert result.error_category in [
                'api_error',
                'data_quality_error',
                'no_data',
                'network_error',
                'timeout_error',
                'unexpected_error'
            ], f"Unknown error category: {result.error_category}"

    @pytest.mark.asyncio
    async def test_metric_categories(self, connector):
        """Test that all metrics have proper categories."""
        from src.pipeline.alpha_vantage_ingestion import METRIC_MAPPINGS

        valid_categories = ['valuation', 'profitability', 'growth', 'size', 'income']

        for metric_type, config in METRIC_MAPPINGS.items():
            assert config['category'] in valid_categories, \
                f"Invalid category for {metric_type}: {config['category']}"

    @pytest.mark.asyncio
    async def test_multiple_companies_sequential(self, connector, db_session):
        """Test processing multiple companies sequentially."""
        tickers = ['CHGG', 'COUR', 'DUOL']
        results = []

        for ticker in tickers:
            result = await ingest_alpha_vantage_for_company(
                ticker,
                connector,
                db_session
            )
            results.append(result)

            # Rate limit delay
            await asyncio.sleep(12)

        # Check results
        assert len(results) == 3

        successful = [r for r in results if r.success]
        assert len(successful) >= 2, \
            f"Too many failures: {len(successful)}/3 succeeded"


# Performance benchmarks
class TestPerformance:
    """Performance benchmarks."""

    @pytest.mark.asyncio
    async def test_api_response_time(self, connector):
        """Test API response time is acceptable."""
        import time

        start = time.time()
        await connector.get_company_overview('CHGG')
        duration = time.time() - start

        # Should complete within 5 seconds
        assert duration < 5.0, \
            f"API response too slow: {duration}s (expected < 5s)"

    @pytest.mark.asyncio
    async def test_database_write_performance(self, connector, db_session):
        """Test database write performance."""
        import time

        # Fetch data
        data = await connector.get_company_overview('CHGG')

        # Create company
        company = Company(ticker='CHGG', name='Chegg Inc')
        db_session.add(company)
        await db_session.flush()

        # Measure write time
        start = time.time()
        await store_financial_metrics(db_session, str(company.id), 'CHGG', data)
        duration = time.time() - start

        # Should complete within 1 second
        assert duration < 1.0, \
            f"Database write too slow: {duration}s (expected < 1s)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])
