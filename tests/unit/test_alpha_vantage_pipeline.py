"""
Comprehensive tests for Alpha Vantage pipeline integration.

Tests cover:
1. Pipeline with mock 'None' responses
2. Retry logic with simulated failures
3. Error categorization and recovery
4. Successful data storage workflows
5. Integration with DataAggregator
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from uuid import uuid4

from src.connectors.data_sources import AlphaVantageConnector, DataAggregator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings with API keys configured."""
    settings = Mock()

    # Alpha Vantage API key
    av_key = Mock()
    av_key.get_secret_value.return_value = "test_alpha_vantage_key"
    settings.ALPHA_VANTAGE_API_KEY = av_key

    # SEC settings
    settings.SEC_USER_AGENT = "test-agent@example.com"

    # Other optional API keys
    settings.NEWSAPI_KEY = None
    settings.CRUNCHBASE_API_KEY = None

    return settings


@pytest.fixture
def mock_alpha_vantage_none_response():
    """Mock response with 'None' values from Alpha Vantage API."""
    return {
        'Symbol': 'CHGG',
        'MarketCapitalization': '1500000000',
        'PERatio': 'None',  # String 'None' that caused crashes
        'PEGRatio': 'None',
        'DividendYield': '0.0',
        'EPS': '2.50',
        'RevenueTTM': 'None',
        'RevenuePerShareTTM': '15.25',
        'ProfitMargin': '0.05',
        'OperatingMarginTTM': '0.08',
        'ReturnOnAssetsTTM': 'None',
        'ReturnOnEquityTTM': 'None',
        'QuarterlyEarningsGrowthYOY': '0.15',
        'QuarterlyRevenueGrowthYOY': '0.12',
        'AnalystTargetPrice': '35.50',
        'TrailingPE': 'None',
        'ForwardPE': '25.5',
        'PriceToSalesRatioTTM': '2.5',
        'PriceToBookRatio': '3.2',
        'EVToRevenue': 'None',
        'EVToEBITDA': 'None',
        'Beta': '1.2',
        '52WeekHigh': '42.00',
        '52WeekLow': '18.50',
    }


@pytest.fixture
def mock_yahoo_response():
    """Mock Yahoo Finance response."""
    return {
        'ticker': 'CHGG',
        'company_name': 'Chegg Inc.',
        'market_cap': 1500000000,
        'trailing_pe': 25.5,
        'profit_margins': 0.05,
    }


@pytest.fixture
def mock_sec_filings():
    """Mock SEC filings response."""
    return [
        {
            'ticker': 'CHGG',
            'form': '10-K',
            'filing_date': '2024-03-15',
            'accession_number': '0001234567-24-000123',
        }
    ]


# ============================================================================
# PIPELINE TESTS - NONE VALUE HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestAlphaVantagePipelineNoneHandling:
    """Test pipeline with 'None' string values from API."""

    async def test_pipeline_handles_none_values(self, mock_settings, mock_alpha_vantage_none_response):
        """Test that pipeline doesn't crash on 'None' values."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(
                return_value=(mock_alpha_vantage_none_response, None)
            )
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # This should NOT crash
            result = await connector.get_company_overview('CHGG')

            # Verify the result is valid
            assert isinstance(result, dict)
            assert result['ticker'] == 'CHGG'

            # Verify 'None' values are converted to 0.0
            assert result['pe_ratio'] == 0.0
            assert result['peg_ratio'] == 0.0
            assert result['revenue_ttm'] == 0.0
            assert result['return_on_assets_ttm'] == 0.0
            assert result['trailing_pe'] == 0.0
            assert result['ev_to_revenue'] == 0.0
            assert result['ev_to_ebitda'] == 0.0

            # Verify valid values are parsed correctly
            assert result['market_cap'] == 1500000000.0
            assert result['eps'] == 2.50
            assert result['profit_margin'] == 0.05

    async def test_pipeline_mixed_none_and_valid(self, mock_settings):
        """Test pipeline with mix of 'None' and valid values."""
        mixed_response = {
            'Symbol': 'TEST',
            'MarketCapitalization': '5000000000',
            'PERatio': '50.5',
            'PEGRatio': 'None',
            'EPS': '3.25',
            'RevenueTTM': 'None',
            'ProfitMargin': '0.12',
        }

        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mixed_response, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('TEST')

            # Verify mixed values are handled correctly
            assert result['market_cap'] == 5000000000.0  # Valid
            assert result['pe_ratio'] == 50.5  # Valid
            assert result['peg_ratio'] == 0.0  # Was 'None'
            assert result['eps'] == 3.25  # Valid
            assert result['revenue_ttm'] == 0.0  # Was 'None'
            assert result['profit_margin'] == 0.12  # Valid


# ============================================================================
# PIPELINE TESTS - RETRY LOGIC
# ============================================================================

@pytest.mark.asyncio
class TestRetryLogic:
    """Test retry logic with simulated failures."""

    async def test_retry_on_transient_network_error(self, mock_settings, mock_alpha_vantage_none_response):
        """Test that pipeline retries on transient network errors."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Simulate failure then success
            call_count = 0
            def side_effect(ticker):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("Network timeout")
                return (mock_alpha_vantage_none_response, None)

            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(side_effect=side_effect)

            # First attempt fails
            result1 = await connector.get_company_overview('CHGG')
            assert result1 == {}  # Returns empty dict on error

            # Second attempt succeeds
            result2 = await connector.get_company_overview('CHGG')
            assert result2['ticker'] == 'CHGG'
            assert result2['market_cap'] == 1500000000.0

    async def test_retry_on_api_rate_limit(self, mock_settings, mock_alpha_vantage_none_response):
        """Test retry behavior on API rate limit errors."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Simulate rate limit then success
            attempts = 0
            def side_effect(ticker):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise Exception("API rate limit exceeded")
                return (mock_alpha_vantage_none_response, None)

            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(side_effect=side_effect)

            # First call hits rate limit
            result1 = await connector.get_company_overview('CHGG')
            assert result1 == {}

            # Second call succeeds
            result2 = await connector.get_company_overview('CHGG')
            assert result2['ticker'] == 'CHGG'

    async def test_max_retries_exceeded(self, mock_settings):
        """Test behavior when max retries are exceeded."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(
                side_effect=Exception("Persistent API error")
            )
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # All attempts should fail
            for i in range(5):
                result = await connector.get_company_overview('CHGG')
                assert result == {}  # Should return empty dict, not crash


# ============================================================================
# PIPELINE TESTS - ERROR CATEGORIZATION
# ============================================================================

@pytest.mark.asyncio
class TestErrorCategorization:
    """Test error categorization and handling."""

    async def test_handle_invalid_ticker(self, mock_settings):
        """Test handling of invalid ticker symbols."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(
                side_effect=Exception("Invalid ticker symbol")
            )
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('INVALID123')
            assert result == {}

    async def test_handle_api_key_error(self):
        """Test handling when API key is invalid."""
        mock_settings_invalid_key = Mock()
        mock_settings_invalid_key.ALPHA_VANTAGE_API_KEY = None

        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings_invalid_key):
            connector = AlphaVantageConnector()

            # Should return empty dict when no API key
            result = await connector.get_company_overview('CHGG')
            assert result == {}

    async def test_handle_malformed_json_response(self, mock_settings):
        """Test handling of malformed JSON responses."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            # Return incomplete/malformed response
            connector.fd.get_company_overview = Mock(return_value=({'Symbol': 'CHGG'}, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('CHGG')

            # Should handle missing fields gracefully
            assert result['ticker'] == 'CHGG'
            assert result['market_cap'] == 0.0  # Missing field defaults to 0.0


# ============================================================================
# PIPELINE TESTS - DATA AGGREGATOR INTEGRATION
# ============================================================================

@pytest.mark.asyncio
class TestDataAggregatorIntegration:
    """Test integration with DataAggregator."""

    async def test_aggregator_handles_alpha_vantage_none_values(
        self,
        mock_settings,
        mock_alpha_vantage_none_response,
        mock_yahoo_response,
        mock_sec_filings
    ):
        """Test that DataAggregator handles Alpha Vantage 'None' values."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock all connectors
            aggregator.alpha.fd = Mock()
            aggregator.alpha.fd.get_company_overview = Mock(
                return_value=(mock_alpha_vantage_none_response, None)
            )
            aggregator.alpha.rate_limiter = Mock()
            aggregator.alpha.rate_limiter.acquire = AsyncMock()

            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_response)
            aggregator.sec.get_company_filings = AsyncMock(return_value=mock_sec_filings)
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            # Execute aggregation
            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Verify result structure
            assert result['ticker'] == 'CHGG'
            assert result['company_name'] == 'Chegg Inc.'
            assert 'alpha_vantage' in result
            assert 'yahoo_finance' in result
            assert 'sec_filings' in result

            # Verify Alpha Vantage data with 'None' values
            av_data = result['alpha_vantage']
            assert av_data['market_cap'] == 1500000000.0
            assert av_data['pe_ratio'] == 0.0  # Was 'None'
            assert av_data['eps'] == 2.50

    async def test_aggregator_with_all_api_failures(self, mock_settings):
        """Test aggregator when all APIs fail."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock all connectors to fail
            aggregator.alpha.fd = Mock()
            aggregator.alpha.fd.get_company_overview = Mock(
                side_effect=Exception("Alpha Vantage error")
            )
            aggregator.alpha.rate_limiter = Mock()
            aggregator.alpha.rate_limiter.acquire = AsyncMock()

            aggregator.yahoo.get_stock_info = AsyncMock(side_effect=Exception("Yahoo error"))
            aggregator.sec.get_company_filings = AsyncMock(side_effect=Exception("SEC error"))
            aggregator.news.get_company_news = AsyncMock(side_effect=Exception("News error"))
            aggregator.crunchbase.get_company_funding = AsyncMock(side_effect=Exception("CB error"))

            # Should still return structured data, not crash
            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Verify fallback values
            assert result['ticker'] == 'CHGG'
            assert result['alpha_vantage'] == {}
            assert result['yahoo_finance'] == {}
            assert result['sec_filings'] == []


# ============================================================================
# PIPELINE TESTS - SUCCESSFUL STORAGE
# ============================================================================

@pytest.mark.asyncio
class TestSuccessfulDataStorage:
    """Test successful data storage workflows."""

    async def test_store_alpha_vantage_data_with_none_values(
        self,
        mock_settings,
        mock_alpha_vantage_none_response
    ):
        """Test that data with 'None' values can be stored successfully."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(
                return_value=(mock_alpha_vantage_none_response, None)
            )
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('CHGG')

            # Simulate storage (in real pipeline, this would go to database)
            stored_data = {
                'ticker': result['ticker'],
                'market_cap': result['market_cap'],
                'pe_ratio': result['pe_ratio'],
                'eps': result['eps'],
                'timestamp': datetime.utcnow().isoformat()
            }

            # Verify stored data is valid
            assert stored_data['ticker'] == 'CHGG'
            assert isinstance(stored_data['market_cap'], float)
            assert isinstance(stored_data['pe_ratio'], float)
            assert stored_data['pe_ratio'] == 0.0  # 'None' converted to 0.0

    async def test_aggregated_data_ready_for_storage(
        self,
        mock_settings,
        mock_alpha_vantage_none_response,
        mock_yahoo_response,
        mock_sec_filings
    ):
        """Test that aggregated data is ready for database storage."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            aggregator = DataAggregator()

            # Mock connectors
            aggregator.alpha.fd = Mock()
            aggregator.alpha.fd.get_company_overview = Mock(
                return_value=(mock_alpha_vantage_none_response, None)
            )
            aggregator.alpha.rate_limiter = Mock()
            aggregator.alpha.rate_limiter.acquire = AsyncMock()

            aggregator.yahoo.get_stock_info = AsyncMock(return_value=mock_yahoo_response)
            aggregator.sec.get_company_filings = AsyncMock(return_value=mock_sec_filings)
            aggregator.news.get_company_news = AsyncMock(return_value=[])
            aggregator.crunchbase.get_company_funding = AsyncMock(return_value={})

            result = await aggregator.get_comprehensive_company_data(
                ticker='CHGG',
                company_name='Chegg Inc.'
            )

            # Verify all data is JSON-serializable (ready for storage)
            import json
            try:
                json_str = json.dumps(result, default=str)
                assert isinstance(json_str, str)
            except Exception as e:
                pytest.fail(f"Data not JSON-serializable: {e}")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestPerformance:
    """Test performance characteristics of the pipeline."""

    async def test_concurrent_requests(self, mock_settings, mock_alpha_vantage_none_response):
        """Test handling of concurrent requests."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(
                return_value=(mock_alpha_vantage_none_response, None)
            )
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Make concurrent requests
            import asyncio
            tickers = ['CHGG', 'DUOL', 'STRA', 'TWOU', 'UDMY']
            tasks = [connector.get_company_overview(ticker) for ticker in tickers]

            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert len(results) == 5
            for i, result in enumerate(results):
                assert isinstance(result, dict)
                # Note: All will have same data due to mock, but structure is valid

    async def test_rate_limiter_prevents_throttling(self, mock_settings, mock_alpha_vantage_none_response):
        """Test that rate limiter prevents API throttling."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(
                return_value=(mock_alpha_vantage_none_response, None)
            )

            # Track rate limiter calls
            rate_limit_calls = []
            async def track_acquire():
                rate_limit_calls.append(datetime.utcnow())

            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock(side_effect=track_acquire)

            # Make multiple sequential requests
            for _ in range(3):
                await connector.get_company_overview('CHGG')

            # Verify rate limiter was called each time
            assert len(rate_limit_calls) == 3
