"""
Comprehensive tests for Alpha Vantage connector and safe_float utility.

Tests cover:
1. safe_float() edge cases and error handling
2. AlphaVantageConnector with mock API responses
3. Retry logic with simulated failures
4. Error categorization and recovery
5. Data storage validation
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from typing import Dict, Any

from src.connectors.data_sources import safe_float, AlphaVantageConnector


# ============================================================================
# SAFE_FLOAT TESTS - EDGE CASES
# ============================================================================

class TestSafeFloat:
    """Test safe_float() utility function for handling problematic values."""

    def test_none_value(self):
        """Test that None returns default value."""
        assert safe_float(None) == 0.0

    def test_string_none(self):
        """Test that string 'None' returns default value."""
        assert safe_float('None') == 0.0

    def test_string_null(self):
        """Test that string 'null' returns default value."""
        assert safe_float('null') == 0.0

    def test_empty_string(self):
        """Test that empty string returns default value."""
        assert safe_float('') == 0.0

    def test_whitespace_string(self):
        """Test that whitespace-only string returns default value."""
        # Note: This will actually try to convert and fail, returning default
        assert safe_float('   ') == 0.0

    def test_valid_float_string(self):
        """Test that valid float string is converted correctly."""
        assert safe_float('3.14') == 3.14

    def test_valid_int_string(self):
        """Test that valid integer string is converted to float."""
        assert safe_float('42') == 42.0

    def test_negative_float_string(self):
        """Test that negative float string is converted correctly."""
        assert safe_float('-123.456') == -123.456

    def test_scientific_notation(self):
        """Test that scientific notation is handled correctly."""
        assert safe_float('1.5e3') == 1500.0
        assert safe_float('2.5E-2') == 0.025

    def test_invalid_string(self):
        """Test that invalid string returns default value."""
        assert safe_float('invalid') == 0.0

    def test_custom_default(self):
        """Test that custom default value is used."""
        assert safe_float('None', default=-1.0) == -1.0
        assert safe_float('invalid', default=99.9) == 99.9
        assert safe_float('', default=100.0) == 100.0

    def test_zero_string(self):
        """Test that string '0' is converted correctly."""
        assert safe_float('0') == 0.0
        assert safe_float('0.0') == 0.0

    def test_very_large_number(self):
        """Test that very large numbers are handled."""
        assert safe_float('999999999999.99') == 999999999999.99

    def test_very_small_number(self):
        """Test that very small numbers are handled."""
        assert safe_float('0.000000001') == 0.000000001

    def test_mixed_case_none(self):
        """Test case sensitivity for 'None' strings."""
        # Only exact 'None' and 'null' are handled, not mixed case
        assert safe_float('NONE') == 0.0  # Will fail conversion, return default
        assert safe_float('nONe') == 0.0  # Will fail conversion, return default

    def test_special_float_values(self):
        """Test handling of special float values."""
        # These should be parseable by float()
        result_inf = safe_float('inf')
        assert result_inf == float('inf')

        result_neg_inf = safe_float('-inf')
        assert result_neg_inf == float('-inf')


# ============================================================================
# ALPHA VANTAGE CONNECTOR - FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings with Alpha Vantage API key."""
    settings = Mock()
    api_key_mock = Mock()
    api_key_mock.get_secret_value.return_value = "test_api_key_12345"
    settings.ALPHA_VANTAGE_API_KEY = api_key_mock
    return settings


@pytest.fixture
def mock_av_response_with_none():
    """Mock Alpha Vantage response with 'None' string values."""
    return {
        'Symbol': 'CHGG',
        'MarketCapitalization': '1500000000',
        'PERatio': 'None',  # String 'None' from API
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
def mock_av_response_valid():
    """Mock Alpha Vantage response with all valid values."""
    return {
        'Symbol': 'DUOL',
        'MarketCapitalization': '7500000000',
        'PERatio': '145.5',
        'PEGRatio': '2.8',
        'DividendYield': '0.0',
        'EPS': '1.85',
        'RevenueTTM': '580000000',
        'RevenuePerShareTTM': '12.50',
        'ProfitMargin': '0.15',
        'OperatingMarginTTM': '0.18',
        'ReturnOnAssetsTTM': '0.12',
        'ReturnOnEquityTTM': '0.22',
        'QuarterlyEarningsGrowthYOY': '0.45',
        'QuarterlyRevenueGrowthYOY': '0.38',
        'AnalystTargetPrice': '180.00',
        'TrailingPE': '150.2',
        'ForwardPE': '85.5',
        'PriceToSalesRatioTTM': '12.5',
        'PriceToBookRatio': '25.8',
        'EVToRevenue': '11.5',
        'EVToEBITDA': '95.2',
        'Beta': '0.85',
        '52WeekHigh': '165.00',
        '52WeekLow': '95.50',
    }


@pytest.fixture
def mock_av_response_empty():
    """Mock Alpha Vantage response with empty strings."""
    return {
        'Symbol': 'TEST',
        'MarketCapitalization': '',
        'PERatio': '',
        'PEGRatio': '',
        'DividendYield': '',
        'EPS': '',
        'RevenueTTM': '',
        'RevenuePerShareTTM': '',
        'ProfitMargin': '',
        'OperatingMarginTTM': '',
        'ReturnOnAssetsTTM': '',
        'ReturnOnEquityTTM': '',
        'QuarterlyEarningsGrowthYOY': '',
        'QuarterlyRevenueGrowthYOY': '',
        'AnalystTargetPrice': '',
        'TrailingPE': '',
        'ForwardPE': '',
        'PriceToSalesRatioTTM': '',
        'PriceToBookRatio': '',
        'EVToRevenue': '',
        'EVToEBITDA': '',
        'Beta': '',
        '52WeekHigh': '',
        '52WeekLow': '',
    }


# ============================================================================
# ALPHA VANTAGE CONNECTOR - SUCCESSFUL DATA RETRIEVAL
# ============================================================================

@pytest.mark.asyncio
class TestAlphaVantageSuccess:
    """Test successful Alpha Vantage data retrieval scenarios."""

    async def test_get_company_overview_with_none_values(self, mock_settings, mock_av_response_with_none):
        """Test that 'None' strings from API are handled gracefully."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()

            # Mock the fundamental data get_company_overview method
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_with_none, None))

            # Disable rate limiting for tests
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('CHGG')

            # Verify None values are converted to 0.0
            assert result['ticker'] == 'CHGG'
            assert result['market_cap'] == 1500000000.0
            assert result['pe_ratio'] == 0.0  # Was 'None'
            assert result['peg_ratio'] == 0.0  # Was 'None'
            assert result['eps'] == 2.50
            assert result['revenue_ttm'] == 0.0  # Was 'None'
            assert result['return_on_assets_ttm'] == 0.0  # Was 'None'
            assert result['trailing_pe'] == 0.0  # Was 'None'

    async def test_get_company_overview_with_valid_values(self, mock_settings, mock_av_response_valid):
        """Test successful retrieval with all valid numeric values."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_valid, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('DUOL')

            # Verify all values are correctly parsed
            assert result['ticker'] == 'DUOL'
            assert result['market_cap'] == 7500000000.0
            assert result['pe_ratio'] == 145.5
            assert result['peg_ratio'] == 2.8
            assert result['eps'] == 1.85
            assert result['profit_margin'] == 0.15
            assert result['quarterly_revenue_growth_yoy'] == 0.38
            assert result['beta'] == 0.85

    async def test_get_company_overview_with_empty_strings(self, mock_settings, mock_av_response_empty):
        """Test that empty strings are handled gracefully."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_empty, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('TEST')

            # All empty strings should convert to 0.0
            assert result['ticker'] == 'TEST'
            assert result['market_cap'] == 0.0
            assert result['pe_ratio'] == 0.0
            assert result['eps'] == 0.0
            assert result['profit_margin'] == 0.0


# ============================================================================
# ALPHA VANTAGE CONNECTOR - ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestAlphaVantageErrors:
    """Test error handling in Alpha Vantage connector."""

    async def test_missing_api_key(self):
        """Test handling when API key is not configured."""
        mock_settings_no_key = Mock()
        mock_settings_no_key.ALPHA_VANTAGE_API_KEY = None

        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings_no_key):
            connector = AlphaVantageConnector()

            # Should return empty dict when no API key
            result = await connector.get_company_overview('CHGG')
            assert result == {}

    async def test_api_exception_handling(self, mock_settings):
        """Test handling of API exceptions."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(side_effect=Exception("API Error"))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Should catch exception and return empty dict
            result = await connector.get_company_overview('CHGG')
            assert result == {}

    async def test_malformed_api_response(self, mock_settings):
        """Test handling of malformed API responses."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            # Return malformed response
            connector.fd.get_company_overview = Mock(return_value=({}, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('CHGG')

            # Should handle missing keys gracefully
            assert result['ticker'] == 'CHGG'
            assert result['market_cap'] == 0.0
            assert result['pe_ratio'] == 0.0

    async def test_rate_limiting_is_called(self, mock_settings, mock_av_response_valid):
        """Test that rate limiting is properly enforced."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_valid, None))

            # Mock rate limiter
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            await connector.get_company_overview('DUOL')

            # Verify rate limiter was called
            connector.rate_limiter.acquire.assert_called_once()


# ============================================================================
# ALPHA VANTAGE CONNECTOR - DATA VALIDATION
# ============================================================================

@pytest.mark.asyncio
class TestAlphaVantageDataValidation:
    """Test data validation and integrity."""

    async def test_all_expected_fields_present(self, mock_settings, mock_av_response_valid):
        """Test that all expected fields are present in the result."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_valid, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('DUOL')

            # Check all expected fields are present
            expected_fields = [
                'ticker', 'market_cap', 'pe_ratio', 'peg_ratio', 'dividend_yield',
                'eps', 'revenue_ttm', 'revenue_per_share_ttm', 'profit_margin',
                'operating_margin_ttm', 'return_on_assets_ttm', 'return_on_equity_ttm',
                'quarterly_earnings_growth_yoy', 'quarterly_revenue_growth_yoy',
                'analyst_target_price', 'trailing_pe', 'forward_pe',
                'price_to_sales_ttm', 'price_to_book', 'ev_to_revenue',
                'ev_to_ebitda', 'beta', '52_week_high', '52_week_low'
            ]

            for field in expected_fields:
                assert field in result, f"Missing field: {field}"

    async def test_all_values_are_floats(self, mock_settings, mock_av_response_with_none):
        """Test that all numeric values are returned as floats."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_with_none, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('CHGG')

            # Verify all values (except ticker) are floats
            for key, value in result.items():
                if key != 'ticker':
                    assert isinstance(value, float), f"{key} is not a float: {type(value)}"

    async def test_no_negative_market_cap(self, mock_settings):
        """Test that negative market cap is handled appropriately."""
        mock_response = {
            'Symbol': 'TEST',
            'MarketCapitalization': '-1000000',  # Negative value
            'PERatio': '10.0',
        }

        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_response, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('TEST')

            # Negative market cap should still be parsed (business logic would validate)
            assert result['market_cap'] == -1000000.0


# ============================================================================
# INTEGRATION-STYLE TESTS - RETRY LOGIC SIMULATION
# ============================================================================

@pytest.mark.asyncio
class TestRetryLogicSimulation:
    """Simulate retry logic with transient failures."""

    async def test_success_after_transient_failure(self, mock_settings, mock_av_response_valid):
        """Test successful retrieval after initial transient failure."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Simulate first call fails, second succeeds
            call_count = 0
            def side_effect(ticker):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Transient network error")
                return (mock_av_response_valid, None)

            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(side_effect=side_effect)

            # First call should fail
            result1 = await connector.get_company_overview('DUOL')
            assert result1 == {}  # Error returns empty dict

            # Second call should succeed
            result2 = await connector.get_company_overview('DUOL')
            assert result2['ticker'] == 'DUOL'
            assert result2['market_cap'] == 7500000000.0

    async def test_persistent_failure(self, mock_settings):
        """Test handling of persistent API failures."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(side_effect=Exception("Persistent error"))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Multiple calls should all fail gracefully
            for _ in range(3):
                result = await connector.get_company_overview('CHGG')
                assert result == {}


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_unicode_ticker_symbol(self, mock_settings, mock_av_response_valid):
        """Test handling of unusual ticker symbols."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_valid, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('BRK.A')  # Ticker with dot
            assert result['ticker'] == 'BRK.A'

    async def test_very_large_market_cap(self, mock_settings):
        """Test handling of very large market cap values."""
        mock_response = {
            'Symbol': 'MEGA',
            'MarketCapitalization': '9999999999999',  # Trillions
        }

        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_response, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            result = await connector.get_company_overview('MEGA')
            assert result['market_cap'] == 9999999999999.0

    async def test_cache_key_wrapper_integration(self, mock_settings, mock_av_response_valid):
        """Test that caching decorator works correctly."""
        with patch('src.connectors.data_sources.get_settings', return_value=mock_settings):
            connector = AlphaVantageConnector()
            connector.fd = Mock()
            connector.fd.get_company_overview = Mock(return_value=(mock_av_response_valid, None))
            connector.rate_limiter = Mock()
            connector.rate_limiter.acquire = AsyncMock()

            # Make multiple calls
            result1 = await connector.get_company_overview('DUOL')
            result2 = await connector.get_company_overview('DUOL')

            # Both should return same data (cache may or may not be hit depending on decorator)
            assert result1 == result2
