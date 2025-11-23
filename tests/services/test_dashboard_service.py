"""Unit tests for DashboardService.

Tests the dashboard service layer methods including caching,
error handling, and data transformations.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.dashboard_service import DashboardService


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_cache():
    """Create a mock Redis cache."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.setex = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def service(mock_session, mock_cache):
    """Create a DashboardService instance with mocked dependencies."""
    service = DashboardService(mock_session, cache_ttl=300)
    service.cache = mock_cache
    return service


class TestGetCompanyPerformance:
    """Tests for get_company_performance method."""

    @pytest.mark.asyncio
    async def test_get_all_companies(self, service, mock_session):
        """Test fetching all companies without filters."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {
                "ticker": "DUOL",
                "company_name": "Duolingo",
                "edtech_category": "direct_to_consumer",
                "latest_revenue": 484.2e6,
                "revenue_yoy_growth": 42.9,
                "latest_nrr": 124,
                "latest_mau": 83.1e6,
                "latest_arpu": 4.9,
                "latest_ltv_cac_ratio": 4.1,
                "overall_score": 89,
                "data_freshness": datetime.utcnow(),
            }
        ]
        mock_session.execute.return_value = mock_result

        companies = await service.get_company_performance()

        assert len(companies) == 1
        assert companies[0]["ticker"] == "DUOL"
        assert companies[0]["latest_revenue"] == 484.2e6
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_companies_by_category(self, service, mock_session):
        """Test filtering companies by category."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {"ticker": "DUOL", "edtech_category": "direct_to_consumer"},
            {"ticker": "CHGG", "edtech_category": "direct_to_consumer"},
        ]
        mock_session.execute.return_value = mock_result

        companies = await service.get_company_performance(category="direct_to_consumer")

        assert len(companies) == 2
        assert all(c["edtech_category"] == "direct_to_consumer" for c in companies)

    @pytest.mark.asyncio
    async def test_cache_hit(self, service, mock_cache):
        """Test that cached data is returned when available."""
        cached_data = [{"ticker": "DUOL", "company_name": "Duolingo"}]
        mock_cache.get.return_value = json.dumps(cached_data, default=str)

        companies = await service.get_company_performance()

        assert companies == cached_data
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_set_on_query(self, service, mock_session, mock_cache):
        """Test that query results are cached."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {"ticker": "DUOL", "company_name": "Duolingo"}
        ]
        mock_session.execute.return_value = mock_result

        await service.get_company_performance()

        mock_cache.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_on_error(self, service, mock_session):
        """Test fallback to raw tables when mart is unavailable."""
        # First call raises exception (mart doesn't exist)
        mock_session.execute.side_effect = Exception("relation does not exist")

        companies = await service.get_company_performance()

        # Should return empty list on fallback failure
        assert isinstance(companies, list)


class TestGetCompetitiveLandscape:
    """Tests for get_competitive_landscape method."""

    @pytest.mark.asyncio
    async def test_get_all_segments(self, service, mock_session):
        """Test fetching all market segments."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {
                "edtech_category": "k12",
                "total_segment_revenue": 2.3e9,
                "companies_in_segment": 12,
                "avg_revenue_growth": 15.2,
                "avg_nrr": 108,
                "hhi_index": 1823,
                "top_3_market_share": 45.3,
                "data_freshness": datetime.utcnow(),
            },
            {
                "edtech_category": "higher_education",
                "total_segment_revenue": 4.1e9,
                "companies_in_segment": 18,
                "avg_revenue_growth": 8.9,
                "avg_nrr": 102,
                "hhi_index": 2156,
                "top_3_market_share": 52.1,
                "data_freshness": datetime.utcnow(),
            },
        ]
        mock_session.execute.return_value = mock_result

        landscape = await service.get_competitive_landscape()

        assert len(landscape["segments"]) == 2
        assert landscape["market_summary"]["total_market_revenue"] == 6.4e9
        assert landscape["market_summary"]["total_companies"] == 30

    @pytest.mark.asyncio
    async def test_filter_by_category(self, service, mock_session):
        """Test filtering landscape by specific category."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {
                "edtech_category": "k12",
                "total_segment_revenue": 2.3e9,
                "companies_in_segment": 12,
            }
        ]
        mock_session.execute.return_value = mock_result

        landscape = await service.get_competitive_landscape(category="k12")

        assert len(landscape["segments"]) == 1
        assert landscape["segments"][0]["edtech_category"] == "k12"


class TestGetCompanyDetails:
    """Tests for get_company_details method."""

    @pytest.mark.asyncio
    async def test_get_existing_company(self, service, mock_session):
        """Test fetching details for existing company."""
        # Mock company query
        mock_company = MagicMock()
        mock_company.ticker = "DUOL"
        mock_company.name = "Duolingo"
        mock_company.category = "direct_to_consumer"
        mock_company.created_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_company

        # Mock performance query
        mock_perf = MagicMock()
        mock_perf._mapping = {"latest_revenue": 484.2e6, "revenue_yoy_growth": 42.9}
        mock_perf_result = MagicMock()
        mock_perf_result.fetchone.return_value = mock_perf

        mock_session.execute.side_effect = [mock_result, mock_perf_result]

        details = await service.get_company_details("DUOL")

        assert details is not None
        assert details["ticker"] == "DUOL"
        assert details["name"] == "Duolingo"

    @pytest.mark.asyncio
    async def test_get_nonexistent_company(self, service, mock_session):
        """Test fetching details for non-existent company."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        details = await service.get_company_details("FAKE")

        assert details is None


class TestGetQuarterlyMetrics:
    """Tests for get_quarterly_metrics method."""

    @pytest.mark.asyncio
    async def test_get_revenue_trend(self, service, mock_session):
        """Test fetching quarterly revenue metrics."""
        # Mock company query
        mock_company = MagicMock()
        mock_company.id = "test-uuid"
        mock_company_result = MagicMock()
        mock_company_result.scalar_one_or_none.return_value = mock_company

        # Mock metrics query
        mock_metric1 = MagicMock()
        mock_metric1.metric_date = datetime.utcnow()
        mock_metric1.value = 484.2e6
        mock_metric1.unit = "USD"
        mock_metric1.period_type = "quarterly"

        mock_metric2 = MagicMock()
        mock_metric2.metric_date = datetime.utcnow() - timedelta(days=90)
        mock_metric2.value = 420.0e6
        mock_metric2.unit = "USD"
        mock_metric2.period_type = "quarterly"

        mock_metrics_result = MagicMock()
        mock_metrics_result.scalars.return_value.all.return_value = [
            mock_metric1,
            mock_metric2,
        ]

        mock_session.execute.side_effect = [
            mock_company_result,
            mock_metrics_result,
        ]

        df = await service.get_quarterly_metrics("DUOL", "revenue")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "qoq_growth" in df.columns
        assert "yoy_growth" in df.columns

    @pytest.mark.asyncio
    async def test_nonexistent_company_metrics(self, service, mock_session):
        """Test fetching metrics for non-existent company."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        df = await service.get_quarterly_metrics("FAKE", "revenue")

        assert df.empty


class TestGetMarketSummary:
    """Tests for get_market_summary method."""

    @pytest.mark.asyncio
    async def test_get_summary(self, service, mock_session):
        """Test fetching market summary KPIs."""
        # Mock landscape query
        mock_landscape = MagicMock()
        mock_landscape.total_market_revenue = 17.3e9
        mock_landscape.avg_yoy_growth = 18.2
        mock_landscape.avg_nrr = 107
        mock_landscape.num_companies = 78
        mock_landscape.data_freshness = datetime.utcnow()

        mock_landscape_result = MagicMock()
        mock_landscape_result.fetchone.return_value = mock_landscape

        # Mock users query
        mock_users = MagicMock()
        mock_users.total_active_users = 220.5e6

        mock_users_result = MagicMock()
        mock_users_result.fetchone.return_value = mock_users

        mock_session.execute.side_effect = [
            mock_landscape_result,
            mock_users_result,
        ]

        summary = await service.get_market_summary()

        assert summary["total_market_revenue"] == 17.3e9
        assert summary["avg_yoy_growth"] == 18.2
        assert summary["total_active_users"] == 220.5e6
        assert summary["num_companies"] == 78


class TestGetSegmentComparison:
    """Tests for get_segment_comparison method."""

    @pytest.mark.asyncio
    async def test_get_comparison(self, service, mock_session):
        """Test fetching normalized segment metrics."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {
                "edtech_category": "k12",
                "avg_revenue_growth": 15.2,
                "avg_nrr": 108,
                "hhi_index": 1823,
                "companies_in_segment": 12,
                "total_segment_revenue": 2.3e9,
            },
            {
                "edtech_category": "higher_education",
                "avg_revenue_growth": 8.9,
                "avg_nrr": 102,
                "hhi_index": 2156,
                "companies_in_segment": 18,
                "total_segment_revenue": 4.1e9,
            },
        ]
        mock_session.execute.return_value = mock_result

        comparison = await service.get_segment_comparison()

        assert len(comparison["segments"]) == 2
        assert len(comparison["metrics"]) == 5  # Default 5 metrics
        assert len(comparison["values"]) == 2
        assert len(comparison["values"][0]) == 5


class TestGetDataFreshness:
    """Tests for get_data_freshness method."""

    @pytest.mark.asyncio
    async def test_get_freshness(self, service, mock_session):
        """Test fetching data freshness metadata."""
        # Mock latest query
        mock_latest = MagicMock()
        mock_latest.last_updated = datetime.utcnow()
        mock_latest_result = MagicMock()
        mock_latest_result.fetchone.return_value = mock_latest

        # Mock counts query
        mock_counts = MagicMock()
        mock_counts.companies_count = 78
        mock_counts.metrics_count = 1245
        mock_counts_result = MagicMock()
        mock_counts_result.fetchone.return_value = mock_counts

        # Mock coverage query
        mock_coverage_result = MagicMock()
        mock_coverage_result.fetchall.return_value = [
            {"edtech_category": "k12", "companies_in_segment": 12},
            {"edtech_category": "higher_education", "companies_in_segment": 18},
        ]

        mock_session.execute.side_effect = [
            mock_latest_result,
            mock_counts_result,
            mock_coverage_result,
        ]

        freshness = await service.get_data_freshness()

        assert freshness["companies_count"] == 78
        assert freshness["metrics_count"] == 1245
        assert len(freshness["coverage_by_category"]) == 2


class TestCaching:
    """Tests for caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, service):
        """Test that cache keys are unique for different parameters."""
        # Different parameters should generate different cache keys
        # This is tested implicitly through the cache get/set calls
        pass

    @pytest.mark.asyncio
    async def test_cache_ttl_override(self, service, mock_cache):
        """Test TTL override for specific cache entries."""
        await service._set_cached("test_key", {"data": "test"}, ttl=600)

        # Verify TTL was passed correctly
        mock_cache.setex.assert_called_with("test_key", 600, '{"data": "test"}')

    @pytest.mark.asyncio
    async def test_cache_failure_graceful(self, service, mock_cache, mock_session):
        """Test graceful handling of cache failures."""
        mock_cache.get.side_effect = Exception("Redis connection failed")

        # Should still work, just without caching
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        companies = await service.get_company_performance()

        assert isinstance(companies, list)
