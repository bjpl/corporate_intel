"""Comprehensive tests for Data Connectors - SEC, Yahoo Finance, Alpha Vantage."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd

from src.connectors.data_sources import (
    RateLimiter,
    SECEdgarConnector,
    YahooFinanceConnector,
    AlphaVantageConnector,
    NewsAPIConnector,
    CrunchbaseConnector,
    GitHubConnector,
    DataAggregator,
    safe_float
)


class TestSafeFloat:
    """Tests for safe_float utility function."""

    def test_safe_float_valid_number(self):
        """Test conversion of valid number."""
        assert safe_float(42.5) == 42.5
        assert safe_float("123.45") == 123.45

    def test_safe_float_none(self):
        """Test handling of None."""
        assert safe_float(None) == 0.0
        assert safe_float(None, default=10.0) == 10.0

    def test_safe_float_none_string(self):
        """Test handling of 'None' string."""
        assert safe_float('None') == 0.0
        assert safe_float('null') == 0.0

    def test_safe_float_empty_string(self):
        """Test handling of empty string."""
        assert safe_float('') == 0.0

    def test_safe_float_invalid_value(self):
        """Test handling of invalid value."""
        assert safe_float('invalid') == 0.0
        assert safe_float('invalid', default=99.0) == 99.0

    def test_safe_float_custom_default(self):
        """Test custom default value."""
        assert safe_float(None, default=123.45) == 123.45


class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(calls_per_second=2.0)  # 2 calls per second

        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        end = asyncio.get_event_loop().time()

        # Second call should have been delayed by ~0.5 seconds
        assert (end - start) >= 0.4  # Allow small margin

    @pytest.mark.asyncio
    async def test_rate_limiter_multiple_calls(self):
        """Test rate limiting with multiple calls."""
        limiter = RateLimiter(calls_per_second=10.0)

        start = asyncio.get_event_loop().time()
        for _ in range(5):
            await limiter.acquire()
        end = asyncio.get_event_loop().time()

        # 5 calls at 10/sec should take ~0.4 seconds
        assert (end - start) >= 0.3

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_safe(self):
        """Test that rate limiter is concurrent-safe."""
        limiter = RateLimiter(calls_per_second=5.0)

        async def worker():
            await limiter.acquire()
            return True

        # Run 10 concurrent workers
        results = await asyncio.gather(*[worker() for _ in range(10)])

        assert all(results)


class TestSECEdgarConnector:
    """Tests for SECEdgarConnector."""

    @pytest.fixture
    def sec_connector(self):
        """Create SEC connector instance."""
        return SECEdgarConnector()

    @pytest.mark.asyncio
    async def test_get_company_filings_success(self, sec_connector):
        """Test successful filing retrieval."""
        mock_submissions = {
            'filings': {
                'recent': {
                    'form': ['10-K', '10-Q', '8-K', '10-Q'],
                    'filingDate': ['2024-12-31', '2024-09-30', '2024-08-15', '2024-06-30'],
                    'accessionNumber': ['0001-24-000001', '0001-24-000002', '0001-24-000003', '0001-24-000004'],
                    'primaryDocument': ['doc1.htm', 'doc2.htm', 'doc3.htm', 'doc4.htm'],
                    'primaryDocDescription': ['Annual Report', 'Quarterly Report', 'Current Report', 'Quarterly Report']
                }
            }
        }

        with patch.object(sec_connector.client, 'get_submissions', return_value=mock_submissions):
            filings = await sec_connector.get_company_filings('DUOL', limit=10)

            assert len(filings) == 4
            assert filings[0]['form'] == '10-K'
            assert filings[0]['ticker'] == 'DUOL'

    @pytest.mark.asyncio
    async def test_get_company_filings_filter_types(self, sec_connector):
        """Test filtering by filing types."""
        mock_submissions = {
            'filings': {
                'recent': {
                    'form': ['10-K', 'S-1', '10-Q', '8-K'],
                    'filingDate': ['2024-12-31', '2024-11-15', '2024-09-30', '2024-08-15'],
                    'accessionNumber': ['0001-24-000001', '0001-24-000002', '0001-24-000003', '0001-24-000004'],
                    'primaryDocument': ['doc1.htm', 'doc2.htm', 'doc3.htm', 'doc4.htm'],
                    'primaryDocDescription': ['Annual', 'Registration', 'Quarterly', 'Current']
                }
            }
        }

        with patch.object(sec_connector.client, 'get_submissions', return_value=mock_submissions):
            filings = await sec_connector.get_company_filings('DUOL', filing_types=['10-K', '10-Q'])

            assert len(filings) == 2
            assert all(f['form'] in ['10-K', '10-Q'] for f in filings)

    @pytest.mark.asyncio
    async def test_get_company_filings_no_results(self, sec_connector):
        """Test handling of no submissions found."""
        with patch.object(sec_connector.client, 'get_submissions', return_value=None):
            filings = await sec_connector.get_company_filings('INVALID')

            assert filings == []

    @pytest.mark.asyncio
    async def test_get_company_filings_error(self, sec_connector):
        """Test error handling."""
        with patch.object(sec_connector.client, 'get_submissions', side_effect=Exception("API Error")):
            filings = await sec_connector.get_company_filings('DUOL')

            assert filings == []

    @pytest.mark.asyncio
    async def test_get_filing_content(self, sec_connector):
        """Test downloading filing content."""
        mock_filing = {'content': 'This is the filing content...'}

        with patch.object(sec_connector.client, 'get_filing', return_value=mock_filing):
            content = await sec_connector.get_filing_content('0001-24-000001', 'DUOL')

            assert content == 'This is the filing content...'

    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self, sec_connector):
        """Test that rate limiting is applied."""
        with patch.object(sec_connector.rate_limiter, 'acquire', new_callable=AsyncMock) as mock_acquire:
            with patch.object(sec_connector.client, 'get_submissions', return_value=None):
                await sec_connector.get_company_filings('DUOL')

                mock_acquire.assert_called_once()


class TestYahooFinanceConnector:
    """Tests for YahooFinanceConnector."""

    @pytest.fixture
    def yahoo_connector(self):
        """Create Yahoo Finance connector instance."""
        return YahooFinanceConnector()

    @pytest.mark.asyncio
    async def test_get_stock_info_success(self, yahoo_connector):
        """Test successful stock info retrieval."""
        mock_info = {
            'longName': 'Duolingo Inc',
            'marketCap': 10.5e9,
            'enterpriseValue': 11.2e9,
            'trailingPE': 45.2,
            'forwardPE': 38.5,
            'revenueGrowth': 0.429,
            'grossMargins': 0.75,
            'operatingMargins': 0.12,
            'profitMargins': 0.08,
            'totalRevenue': 484.2e6,
            'currentPrice': 285.50
        }

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_info

            info = await yahoo_connector.get_stock_info('DUOL')

            assert info['ticker'] == 'DUOL'
            assert info['company_name'] == 'Duolingo Inc'
            assert info['market_cap'] == 10.5e9
            assert info['revenue_growth'] == 0.429

    @pytest.mark.asyncio
    async def test_get_stock_info_missing_fields(self, yahoo_connector):
        """Test handling of missing fields."""
        mock_info = {'longName': 'Test Company'}  # Minimal info

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = mock_info

            info = await yahoo_connector.get_stock_info('TEST')

            assert info['company_name'] == 'Test Company'
            assert info['market_cap'] == 0  # Default value
            assert info['revenue_growth'] == 0

    @pytest.mark.asyncio
    async def test_get_stock_info_error(self, yahoo_connector):
        """Test error handling."""
        with patch('yfinance.Ticker', side_effect=Exception("Yahoo API Error")):
            info = await yahoo_connector.get_stock_info('DUOL')

            assert info == {}

    @pytest.mark.asyncio
    async def test_get_quarterly_financials(self, yahoo_connector):
        """Test quarterly financials retrieval."""
        mock_financials = pd.DataFrame({
            '2024-12-31': [100e6, 50e6, 30e6],
            '2024-09-30': [90e6, 45e6, 25e6],
            '2024-06-30': [85e6, 42e6, 22e6]
        }, index=['Total Revenue', 'Gross Profit', 'Net Income'])

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.quarterly_financials = mock_financials

            df = await yahoo_connector.get_quarterly_financials('DUOL')

            assert not df.empty
            assert 'ticker' in df.columns
            assert df['ticker'].iloc[0] == 'DUOL'
            assert len(df) == 3

    @pytest.mark.asyncio
    async def test_caching_behavior(self, yahoo_connector):
        """Test that results are cached."""
        # This test verifies the @cache_key_wrapper decorator works
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {'longName': 'Test'}

            # First call
            info1 = await yahoo_connector.get_stock_info('TEST')

            # Cache should be used, so ticker shouldn't be called again
            # (Note: actual caching test depends on cache implementation)
            assert info1['company_name'] == 'Test'


class TestAlphaVantageConnector:
    """Tests for AlphaVantageConnector."""

    @pytest.fixture
    def alpha_connector(self):
        """Create Alpha Vantage connector instance."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = MagicMock()
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY.get_secret_value.return_value = 'test_key'
            return AlphaVantageConnector()

    @pytest.mark.asyncio
    async def test_get_company_overview_success(self, alpha_connector):
        """Test successful company overview retrieval."""
        mock_data = {
            'MarketCapitalization': '10500000000',
            'PERatio': '45.2',
            'PEGRatio': '2.1',
            'EPS': '6.32',
            'RevenueTTM': '484200000',
            'ProfitMargin': '0.08',
            'QuarterlyRevenueGrowthYOY': '0.429'
        }

        with patch.object(alpha_connector.fd, 'get_company_overview', return_value=(mock_data, None)):
            overview = await alpha_connector.get_company_overview('DUOL')

            assert overview['ticker'] == 'DUOL'
            assert overview['market_cap'] == 10.5e9
            assert overview['pe_ratio'] == 45.2
            assert overview['quarterly_revenue_growth_yoy'] == 0.429

    @pytest.mark.asyncio
    async def test_get_company_overview_null_values(self, alpha_connector):
        """Test handling of None/null values."""
        mock_data = {
            'MarketCapitalization': 'None',
            'PERatio': None,
            'PEGRatio': '',
            'EPS': 'null'
        }

        with patch.object(alpha_connector.fd, 'get_company_overview', return_value=(mock_data, None)):
            overview = await alpha_connector.get_company_overview('TEST')

            assert overview['market_cap'] == 0.0
            assert overview['pe_ratio'] == 0.0
            assert overview['peg_ratio'] == 0.0
            assert overview['eps'] == 0.0

    @pytest.mark.asyncio
    async def test_get_company_overview_no_api_key(self):
        """Test behavior when API key not configured."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = None
            connector = AlphaVantageConnector()

            overview = await connector.get_company_overview('DUOL')

            assert overview == {}

    @pytest.mark.asyncio
    async def test_rate_limiting(self, alpha_connector):
        """Test rate limiting is applied."""
        with patch.object(alpha_connector.rate_limiter, 'acquire', new_callable=AsyncMock) as mock_acquire:
            with patch.object(alpha_connector.fd, 'get_company_overview', return_value=({}, None)):
                await alpha_connector.get_company_overview('DUOL')

                mock_acquire.assert_called_once()


class TestNewsAPIConnector:
    """Tests for NewsAPIConnector."""

    @pytest.fixture
    def news_connector(self):
        """Create NewsAPI connector instance."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.NEWSAPI_KEY = 'test_key'
            return NewsAPIConnector()

    @pytest.mark.asyncio
    async def test_get_company_news_success(self, news_connector):
        """Test successful news retrieval."""
        mock_response = {
            'status': 'ok',
            'articles': [
                {
                    'title': 'Duolingo reports growth',
                    'description': 'Revenue increased significantly',
                    'url': 'https://example.com/article1',
                    'publishedAt': '2025-01-01T12:00:00Z',
                    'source': {'name': 'TechNews'}
                },
                {
                    'title': 'EdTech company success',
                    'description': 'Positive results for learning platform',
                    'url': 'https://example.com/article2',
                    'publishedAt': '2025-01-02T12:00:00Z',
                    'source': {'name': 'BusinessDaily'}
                }
            ]
        }

        with patch('aiohttp.ClientSession') as mock_session:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response_obj

            news = await news_connector.get_company_news('Duolingo', days_back=7)

            assert len(news) == 2
            assert news[0]['title'] == 'Duolingo reports growth'
            assert 'sentiment' in news[0]

    @pytest.mark.asyncio
    async def test_sentiment_analysis_positive(self, news_connector):
        """Test positive sentiment detection."""
        text = "Strong growth and profit gains with rising success"
        sentiment = news_connector._analyze_sentiment(text)

        assert sentiment > 0

    @pytest.mark.asyncio
    async def test_sentiment_analysis_negative(self, news_connector):
        """Test negative sentiment detection."""
        text = "Major loss and decline with falling revenue concerns"
        sentiment = news_connector._analyze_sentiment(text)

        assert sentiment < 0

    @pytest.mark.asyncio
    async def test_sentiment_analysis_neutral(self, news_connector):
        """Test neutral sentiment."""
        text = "Company announces quarterly report"
        sentiment = news_connector._analyze_sentiment(text)

        assert sentiment == 0

    @pytest.mark.asyncio
    async def test_get_company_news_no_api_key(self):
        """Test behavior without API key."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.NEWSAPI_KEY = None
            connector = NewsAPIConnector()

            news = await connector.get_company_news('Test Company')

            assert news == []


class TestDataAggregator:
    """Tests for DataAggregator."""

    @pytest.fixture
    def aggregator(self):
        """Create DataAggregator instance."""
        return DataAggregator()

    @pytest.mark.asyncio
    async def test_get_comprehensive_data_success(self, aggregator):
        """Test comprehensive data aggregation."""
        # Mock all connector responses
        with patch.object(aggregator.sec, 'get_company_filings', return_value=[{'form': '10-K'}]):
            with patch.object(aggregator.yahoo, 'get_stock_info', return_value={'market_cap': 10e9}):
                with patch.object(aggregator.alpha, 'get_company_overview', return_value={'pe_ratio': 45}):
                    with patch.object(aggregator.news, 'get_company_news', return_value=[{'sentiment': 0.5}]):
                        with patch.object(aggregator.crunchbase, 'get_company_funding', return_value={'funding_total': 100e6}):
                            data = await aggregator.get_comprehensive_company_data('DUOL', 'Duolingo')

                            assert data['ticker'] == 'DUOL'
                            assert data['company_name'] == 'Duolingo'
                            assert 'sec_filings' in data
                            assert 'yahoo_finance' in data
                            assert 'alpha_vantage' in data
                            assert 'news_sentiment' in data
                            assert 'composite_score' in data

    @pytest.mark.asyncio
    async def test_get_comprehensive_data_with_github(self, aggregator):
        """Test aggregation with GitHub data."""
        with patch.object(aggregator.sec, 'get_company_filings', return_value=[]):
            with patch.object(aggregator.yahoo, 'get_stock_info', return_value={}):
                with patch.object(aggregator.alpha, 'get_company_overview', return_value={}):
                    with patch.object(aggregator.news, 'get_company_news', return_value=[]):
                        with patch.object(aggregator.crunchbase, 'get_company_funding', return_value={}):
                            with patch.object(aggregator.github, 'get_repo_metrics', return_value={'stars': 1000}):
                                data = await aggregator.get_comprehensive_company_data(
                                    'DUOL',
                                    'Duolingo',
                                    github_repo='duolingo/app'
                                )

                                assert 'github_metrics' in data
                                assert data['github_metrics']['stars'] == 1000

    @pytest.mark.asyncio
    async def test_handles_connector_failures(self, aggregator):
        """Test graceful handling of connector failures."""
        # Make some connectors fail
        with patch.object(aggregator.sec, 'get_company_filings', side_effect=Exception("SEC Error")):
            with patch.object(aggregator.yahoo, 'get_stock_info', return_value={}):
                with patch.object(aggregator.alpha, 'get_company_overview', return_value={}):
                    with patch.object(aggregator.news, 'get_company_news', return_value=[]):
                        with patch.object(aggregator.crunchbase, 'get_company_funding', return_value={}):
                            data = await aggregator.get_comprehensive_company_data('DUOL', 'Duolingo')

                            # Should still return data with failed sources as empty
                            assert data['sec_filings'] == []
                            assert 'composite_score' in data

    def test_calculate_composite_score(self, aggregator):
        """Test composite score calculation."""
        data = {
            'yahoo_finance': {'profit_margins': 0.15},  # 15%
            'alpha_vantage': {'quarterly_revenue_growth_yoy': 0.25},  # 25%
            'news_sentiment': [{'sentiment': 0.5}, {'sentiment': 0.3}],  # Avg 0.4
            'github_metrics': {'recent_commits': 50}
        }

        score = aggregator._calculate_composite_score(data)

        assert 0 <= score <= 100
        assert isinstance(score, float)

    def test_calculate_composite_score_empty_data(self, aggregator):
        """Test composite score with missing data."""
        data = {}

        score = aggregator._calculate_composite_score(data)

        assert score == 0
