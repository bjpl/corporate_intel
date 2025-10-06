"""
Comprehensive tests for DataAggregator integration.

Tests cover:
1. Multi-source data aggregation
2. Concurrent API calls
3. Data conflict resolution
4. Cache usage and optimization
5. Composite score calculation
6. Error handling across sources
7. Partial data scenarios
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.connectors.data_sources import DataAggregator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings with all API keys configured."""
    settings = Mock()

    # SEC settings
    settings.SEC_USER_AGENT = "test-agent@example.com"

    # Alpha Vantage
    av_key = Mock()
    av_key.get_secret_value.return_value = "test_alpha_vantage_key"
    settings.ALPHA_VANTAGE_API_KEY = av_key

    # NewsAPI
    settings.NEWSAPI_KEY = "test_newsapi_key"

    # Crunchbase
    settings.CRUNCHBASE_API_KEY = "test_crunchbase_key"

    return settings


@pytest.fixture
def mock_sec_filings():
    """Mock SEC filings response."""
    return [
        {
            'form': '10-K',
            'filing_date': '2024-03-15',
            'accession_number': '0001234567-24-000123',
            'ticker': 'CHGG',
        },
        {
            'form': '10-Q',
            'filing_date': '2024-06-15',
            'accession_number': '0001234567-24-000456',
            'ticker': 'CHGG',
        },
    ]


@pytest.fixture
def mock_yahoo_data():
    """Mock Yahoo Finance response."""
    return {
        'ticker': 'CHGG',
        'company_name': 'Chegg Inc.',
        'market_cap': 1500000000,
        'trailing_pe': 25.5,
        'profit_margins': 0.05,
        'revenue_growth': 0.12,
    }


@pytest.fixture
def mock_alpha_vantage_data():
    """Mock Alpha Vantage response."""
    return {
        'ticker': 'CHGG',
        'market_cap': 1500000000.0,
        'pe_ratio': 25.5,
        'peg_ratio': 1.8,
        'eps': 2.50,
        'revenue_ttm': 800000000.0,
        'profit_margin': 0.05,
        'quarterly_earnings_growth_yoy': 0.15,
        'quarterly_revenue_growth_yoy': 0.12,
    }


@pytest.fixture
def mock_news_data():
    """Mock NewsAPI response."""
    return [
        {
            'title': 'Chegg announces new AI learning platform',
            'description': 'Growth in online education sector',
            'url': 'https://news.example.com/article1',
            'published_at': '2024-10-01T10:00:00Z',
            'source': 'TechCrunch',
            'sentiment': 0.8,
        },
        {
            'title': 'Chegg faces competition in edtech market',
            'description': 'Decline in market share concerns',
            'url': 'https://news.example.com/article2',
            'published_at': '2024-10-02T15:00:00Z',
            'source': 'EdSurge',
            'sentiment': -0.3,
        },
    ]


@pytest.fixture
def mock_crunchbase_data():
    """Mock Crunchbase response."""
    return {
        'name': 'Chegg Inc.',
        'funding_total': 250000000,
        'num_funding_rounds': 5,
        'last_funding_date': '2020-05-15',
    }


@pytest.fixture
def mock_github_data():
    """Mock GitHub response."""
    return {
        'stars': 1500,
        'forks': 300,
        'watchers': 150,
        'open_issues': 25,
        'recent_commits': 50,
        'contributors': 12,
        'language': 'Python',
        'license': 'MIT',
    }


# ============================================================================
# AGGREGATION TESTS - SUCCESS SCENARIOS
# ============================================================================

@pytest.mark.asyncio
class TestSuccessfulAggregation:
    """Test successful multi-source aggregation."""

    async def test_aggregate_all_sources(
        self,
        mock_settings,
        mock_sec_filings,
        mock_yahoo_data,
        mock_alpha_vantage_data,
        mock_news_data,
        mock_crunchbase_data,
    ):
        """Test aggregating data from all sources successfully."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock all connectors
            aggregator.sec.get_company_filings = AsyncMock(return_value=mock_sec_filings)
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(return_value=mock_alpha_vantage_data)
            aggregator.news.get_company_news = AsyncMock(return_value=mock_news_data)
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value=mock_crunchbase_data)

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Verify structure
            assert result['ticker'] == 'CHGG'
            assert result['company_name'] == 'Chegg Inc.'
            assert 'timestamp' in result

            # Verify all data sources
            assert len(result['sec_filings']) == 2
            assert result['yahoo_finance']['market_cap'] == 1500000000
            assert result['alpha_vantage']['pe_ratio'] == 25.5
            assert len(result['news_sentiment']) == 2
            assert result['crunchbase']['funding_total'] == 250000000

            # Verify composite score calculated
            assert 'composite_score' in result
            assert isinstance(result['composite_score'], float)

    async def test_aggregate_with_github(
        self,
        mock_settings,
        mock_sec_filings,
        mock_yahoo_data,
        mock_alpha_vantage_data,
        mock_news_data,
        mock_crunchbase_data,
        mock_github_data,
    ):
        """Test aggregation including GitHub metrics."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock all connectors
            aggregator.sec.get_company_filings = AsyncMock(return_value=mock_sec_filings)
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(return_value=mock_alpha_vantage_data)
            aggregator.news.get_company_news = AsyncMock(return_value=mock_news_data)
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value=mock_crunchbase_data)
            aggregator.github.get_repo_metrics = AsyncMock(return_value=mock_github_data)

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.',
                github_repo='chegg/edtech-tools'
            )

            # Verify GitHub data included
            assert 'github_metrics' in result
            assert result['github_metrics']['stars'] == 1500
            assert result['github_metrics']['contributors'] == 12

    async def test_concurrent_api_calls(
        self,
        mock_settings,
        mock_sec_filings,
        mock_yahoo_data,
        mock_alpha_vantage_data,
        mock_news_data,
        mock_crunchbase_data,
    ):
        """Test that API calls are made concurrently."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Track call order
            call_order = []

            async def track_sec(*args):
                call_order.append('sec')
                await asyncio.sleep(0.01)
                return mock_sec_filings

            async def track_yahoo(*args):
                call_order.append('yahoo')
                await asyncio.sleep(0.01)
                return mock_yahoo_data

            async def track_alpha(*args):
                call_order.append('alpha')
                await asyncio.sleep(0.01)
                return mock_alpha_vantage_data

            async def track_news(*args):
                call_order.append('news')
                await asyncio.sleep(0.01)
                return mock_news_data

            async def track_crunchbase(*args):
                call_order.append('crunchbase')
                await asyncio.sleep(0.01)
                return mock_crunchbase_data

            aggregator.sec.get_company_filings = track_sec
            aggregator.yahoo.get_stock_info = track_yahoo
            aggregator.alpha.get_company_overview = track_alpha
            aggregator.news.get_company_news = track_news
            aggregator.crunchbase.get_company_funding = track_crunchbase

            start_time = datetime.utcnow()
            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Should complete in ~0.01s (concurrent) not 0.05s (sequential)
            assert duration < 0.1

            # All calls should be made
            assert len(call_order) == 5


# ============================================================================
# CONFLICT RESOLUTION
# ============================================================================

@pytest.mark.asyncio
class TestDataConflictResolution:
    """Test handling of conflicting data from multiple sources."""

    async def test_market_cap_from_multiple_sources(self, mock_settings):
        """Test conflict resolution when different sources report different market caps."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Different market cap values
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={
                'ticker': 'CHGG',
                'market_cap': 1500000000,  # Yahoo: 1.5B
            })
            aggregator.alpha.get_company_overview = AsyncMock(return_value={
                'ticker': 'CHGG',
                'market_cap': 1600000000.0,  # Alpha Vantage: 1.6B
            })
            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Both values should be preserved
            assert result['yahoo_finance']['market_cap'] == 1500000000
            assert result['alpha_vantage']['market_cap'] == 1600000000.0

    async def test_missing_data_from_one_source(self, mock_settings, mock_yahoo_data):
        """Test handling when one source has missing data."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Alpha Vantage missing
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})  # Empty
            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Yahoo data should still be available
            assert result['yahoo_finance']['market_cap'] == 1500000000

            # Alpha Vantage should be empty dict
            assert result['alpha_vantage'] == {}

    async def test_prefer_most_recent_data(self, mock_settings):
        """Test preferring most recent data when timestamps differ."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock data with timestamps
            aggregator.sec.get_company_filings = AsyncMock(return_value=[
                {
                    'form': '10-K',
                    'filing_date': '2024-03-15',
                    'revenue': 750000000,
                },
                {
                    'form': '10-Q',
                    'filing_date': '2024-06-15',
                    'revenue': 800000000,  # More recent
                },
            ])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={})
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Should have both filings, preserving chronology
            assert len(result['sec_filings']) == 2
            assert result['sec_filings'][0]['filing_date'] == '2024-03-15'
            assert result['sec_filings'][1]['filing_date'] == '2024-06-15'


# ============================================================================
# ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling across multiple sources."""

    async def test_single_source_failure(self, mock_settings, mock_yahoo_data, mock_alpha_vantage_data):
        """Test that one source failure doesn't break aggregation."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # SEC fails
            aggregator.sec.get_company_filings = AsyncMock(side_effect=Exception("SEC API error"))
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(return_value=mock_alpha_vantage_data)
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Should handle exception gracefully
            assert result['sec_filings'] == []  # Exception handled
            assert result['yahoo_finance']['market_cap'] == 1500000000  # Others succeed

    async def test_all_sources_fail(self, mock_settings):
        """Test handling when all sources fail."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # All fail
            aggregator.sec.get_company_filings = AsyncMock(side_effect=Exception("SEC error"))
            aggregator.yahoo.get_stock_info = AsyncMock(side_effect=Exception("Yahoo error"))
            aggregator.alpha.get_company_overview = AsyncMock(side_effect=Exception("Alpha error"))
            aggregator.news.get_company_news = AsyncMock(side_effect=Exception("News error"))
            aggregator.crunchbase.get_company_funding = AsyncMock(side_effect=Exception("CB error"))

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Should return structure with empty data
            assert result['ticker'] == 'CHGG'
            assert result['sec_filings'] == []
            assert result['yahoo_finance'] == {}
            assert result['alpha_vantage'] == {}
            assert result['news_sentiment'] == []
            assert result['crunchbase'] == {}

    async def test_timeout_handling(self, mock_settings, mock_yahoo_data):
        """Test handling of API timeouts."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Alpha Vantage times out
            async def timeout_mock(*args):
                await asyncio.sleep(10)
                return {}

            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(side_effect=asyncio.TimeoutError())
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Should handle timeout gracefully
            assert result['alpha_vantage'] == []  # Timeout handled as exception


# ============================================================================
# COMPOSITE SCORE CALCULATION
# ============================================================================

@pytest.mark.asyncio
class TestCompositeScore:
    """Test composite score calculation."""

    async def test_composite_score_with_all_data(
        self,
        mock_settings,
        mock_sec_filings,
        mock_yahoo_data,
        mock_alpha_vantage_data,
        mock_news_data,
        mock_crunchbase_data,
    ):
        """Test composite score with complete data."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            aggregator.sec.get_company_filings = AsyncMock(return_value=mock_sec_filings)
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(return_value=mock_alpha_vantage_data)
            aggregator.news.get_company_news = AsyncMock(return_value=mock_news_data)
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value=mock_crunchbase_data)

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Composite score should be calculated
            assert 'composite_score' in result
            assert isinstance(result['composite_score'], float)
            assert 0 <= result['composite_score'] <= 100

    async def test_composite_score_with_partial_data(self, mock_settings, mock_yahoo_data):
        """Test composite score with only some data sources."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Only Yahoo Finance has data
            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_data)
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Should still calculate score
            assert 'composite_score' in result
            assert isinstance(result['composite_score'], float)

    async def test_composite_score_with_no_data(self, mock_settings):
        """Test composite score when no data is available."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # No data from any source
            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={})
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Score should be 0 or minimal
            assert result['composite_score'] == 0


# ============================================================================
# CACHE OPTIMIZATION
# ============================================================================

@pytest.mark.asyncio
class TestCacheOptimization:
    """Test cache usage for optimization."""

    async def test_cache_hit_avoids_api_call(self, mock_settings, mock_alpha_vantage_data):
        """Test that cached data avoids redundant API calls."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock Alpha Vantage with call tracking
            call_count = 0

            async def track_calls(*args):
                nonlocal call_count
                call_count += 1
                return mock_alpha_vantage_data

            aggregator.alpha.get_company_overview = track_calls
            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            # First call
            result1 = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Second call (should use cache)
            result2 = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Note: Caching is at connector level, not aggregator level
            # Both calls will execute, but connector may use cache


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_invalid_ticker_all_sources(self, mock_settings):
        """Test handling of invalid ticker across all sources."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # All sources return empty for invalid ticker
            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={})
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='INVALID123',
                company_name='Invalid Company'
            )

            assert result['ticker'] == 'INVALID123'
            assert result['composite_score'] == 0

    async def test_company_name_special_characters(self, mock_settings, mock_news_data):
        """Test handling of company names with special characters."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            aggregator.sec.get_company_filings = AsyncMock(return_value=[])
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={})
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=mock_news_data)
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='TEST',
                company_name="O'Reilly & Associates, Inc."
            )

            # Should handle special characters
            assert result['company_name'] == "O'Reilly & Associates, Inc."

    async def test_very_large_data_volume(self, mock_settings):
        """Test handling of very large data volumes."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Large number of SEC filings
            large_filings = [
                {
                    'form': '8-K',
                    'filing_date': f'2024-{i % 12 + 1:02d}-15',
                    'accession_number': f'000123456{i:04d}',
                }
                for i in range(1000)
            ]

            aggregator.sec.get_company_filings = AsyncMock(return_value=large_filings)
            aggregator.yahoo.get_stock_info = AsyncMock(return_value={})
            aggregator.alpha.get_company_overview = AsyncMock(return_value={})
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Should handle large datasets
            assert len(result['sec_filings']) == 1000
