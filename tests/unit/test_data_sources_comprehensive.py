"""Comprehensive tests for data source connectors to increase coverage.

Tests cover:
- RateLimiter async functionality
- safe_float utility function edge cases
- SECEdgarConnector methods
- YahooFinanceConnector sync and async operations
- AlphaVantageConnector with API key handling
- NewsAPIConnector with sentiment analysis
- CrunchbaseConnector API interactions
- GitHubConnector repository metrics
- DataAggregator comprehensive data fetching
- Composite score calculation
- Error handling and edge cases
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

from src.connectors.data_sources import (
    AlphaVantageConnector,
    CrunchbaseConnector,
    DataAggregator,
    GitHubConnector,
    NewsAPIConnector,
    RateLimiter,
    SECEdgarConnector,
    YahooFinanceConnector,
    safe_float,
)


# ============================================================================
# safe_float Utility Tests
# ============================================================================


class TestSafeFloat:
    """Test safe_float utility function."""

    def test_safe_float_valid_number(self):
        """Test safe_float with valid number."""
        assert safe_float("123.45") == 123.45
        assert safe_float(100) == 100.0
        assert safe_float(45.67) == 45.67

    def test_safe_float_none(self):
        """Test safe_float with None."""
        assert safe_float(None) == 0.0
        assert safe_float(None, default=99.9) == 99.9

    def test_safe_float_none_string(self):
        """Test safe_float with 'None' string."""
        assert safe_float("None") == 0.0
        assert safe_float("None", default=50.0) == 50.0

    def test_safe_float_null_string(self):
        """Test safe_float with 'null' string."""
        assert safe_float("null") == 0.0

    def test_safe_float_empty_string(self):
        """Test safe_float with empty string."""
        assert safe_float("") == 0.0
        assert safe_float("", default=42.0) == 42.0

    def test_safe_float_invalid_string(self):
        """Test safe_float with invalid string."""
        assert safe_float("not a number") == 0.0
        assert safe_float("abc", default=10.0) == 10.0

    def test_safe_float_negative_number(self):
        """Test safe_float with negative number."""
        assert safe_float("-123.45") == -123.45
        assert safe_float(-100) == -100.0

    def test_safe_float_zero(self):
        """Test safe_float with zero."""
        assert safe_float(0) == 0.0
        assert safe_float("0") == 0.0


# ============================================================================
# RateLimiter Tests
# ============================================================================


class TestRateLimiterDetailed:
    """Detailed tests for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(calls_per_second=5)

        assert limiter.calls_per_second == 5
        assert limiter.min_interval == 0.2
        assert limiter.last_call == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_calls(self):
        """Test RateLimiter with concurrent calls."""
        limiter = RateLimiter(calls_per_second=10)

        # Make 5 concurrent calls
        tasks = [limiter.acquire() for _ in range(5)]
        start = asyncio.get_event_loop().time()
        await asyncio.gather(*tasks)
        end = asyncio.get_event_loop().time()

        # Total time should be at least 0.4 seconds (4 delays of 0.1s each)
        assert (end - start) >= 0.39

    @pytest.mark.asyncio
    async def test_rate_limiter_very_slow_rate(self):
        """Test RateLimiter with very slow rate."""
        limiter = RateLimiter(calls_per_second=1)  # 1 second between calls

        await limiter.acquire()
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        end = asyncio.get_event_loop().time()

        assert (end - start) >= 0.99


# ============================================================================
# SECEdgarConnector Tests
# ============================================================================


class TestSECEdgarConnector:
    """Test SECEdgarConnector methods."""

    @pytest.mark.asyncio
    async def test_get_company_filings_success(self):
        """Test successful company filings fetch."""
        connector = SECEdgarConnector()

        mock_submissions = {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "8-K", "10-K"],
                    "filingDate": ["2024-03-15", "2024-01-10", "2024-02-05", "2023-03-10"],
                    "accessionNumber": ["0001", "0002", "0003", "0004"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm", "doc4.htm"],
                    "primaryDocDescription": ["Annual", "Quarterly", "Current", "Annual"]
                }
            }
        }

        with patch.object(connector.client, 'get_submissions', return_value=mock_submissions):
            filings = await connector.get_company_filings("DUOL", ["10-K", "10-Q"], limit=10)

            assert len(filings) == 3  # 2 10-Ks and 1 10-Q
            assert filings[0]["form"] == "10-K"
            assert filings[0]["ticker"] == "DUOL"

    @pytest.mark.asyncio
    async def test_get_company_filings_no_submissions(self):
        """Test company filings when no submissions found."""
        connector = SECEdgarConnector()

        with patch.object(connector.client, 'get_submissions', return_value=None):
            filings = await connector.get_company_filings("INVALID")

            assert filings == []

    @pytest.mark.asyncio
    async def test_get_company_filings_with_limit(self):
        """Test company filings with limit."""
        connector = SECEdgarConnector()

        mock_submissions = {
            "filings": {
                "recent": {
                    "form": ["10-K"] * 20,
                    "filingDate": ["2024-03-15"] * 20,
                    "accessionNumber": [f"000{i}" for i in range(20)],
                    "primaryDocument": [f"doc{i}.htm" for i in range(20)],
                    "primaryDocDescription": ["Annual"] * 20
                }
            }
        }

        with patch.object(connector.client, 'get_submissions', return_value=mock_submissions):
            filings = await connector.get_company_filings("DUOL", limit=5)

            assert len(filings) == 5

    @pytest.mark.asyncio
    async def test_get_company_filings_exception(self):
        """Test company filings with exception."""
        connector = SECEdgarConnector()

        with patch.object(connector.client, 'get_submissions', side_effect=Exception("API Error")):
            filings = await connector.get_company_filings("DUOL")

            assert filings == []

    @pytest.mark.asyncio
    async def test_get_filing_content_success(self):
        """Test successful filing content fetch."""
        connector = SECEdgarConnector()

        mock_filing = {"content": "This is the filing content"}

        with patch.object(connector.client, 'get_filing', return_value=mock_filing):
            content = await connector.get_filing_content("0001-24-000001", "DUOL")

            assert content == "This is the filing content"

    @pytest.mark.asyncio
    async def test_get_filing_content_no_content(self):
        """Test filing content fetch with no content."""
        connector = SECEdgarConnector()

        with patch.object(connector.client, 'get_filing', return_value={}):
            content = await connector.get_filing_content("0001-24-000001", "DUOL")

            assert content == ""

    @pytest.mark.asyncio
    async def test_get_filing_content_exception(self):
        """Test filing content fetch with exception."""
        connector = SECEdgarConnector()

        with patch.object(connector.client, 'get_filing', side_effect=Exception("Download error")):
            content = await connector.get_filing_content("0001-24-000001", "DUOL")

            assert content == ""


# ============================================================================
# YahooFinanceConnector Tests
# ============================================================================


class TestYahooFinanceConnector:
    """Test YahooFinanceConnector methods."""

    @pytest.mark.asyncio
    async def test_get_stock_info_success(self):
        """Test successful stock info fetch."""
        connector = YahooFinanceConnector()

        mock_info = {
            "longName": "Duolingo Inc.",
            "marketCap": 5000000000,
            "enterpriseValue": 4800000000,
            "trailingPE": 125.0,
            "totalRevenue": 500000000,
            "profitMargins": 0.15,
            "currentPrice": 150.00
        }

        with patch('yfinance.Ticker') as MockTicker:
            mock_ticker = Mock()
            mock_ticker.info = mock_info
            MockTicker.return_value = mock_ticker

            info = await connector.get_stock_info("DUOL")

            assert info["ticker"] == "DUOL"
            assert info["company_name"] == "Duolingo Inc."
            assert info["market_cap"] == 5000000000
            assert info["trailing_pe"] == 125.0

    @pytest.mark.asyncio
    async def test_get_stock_info_missing_fields(self):
        """Test stock info with missing fields."""
        connector = YahooFinanceConnector()

        mock_info = {
            "longName": "Test Company"
            # Missing most fields
        }

        with patch('yfinance.Ticker') as MockTicker:
            mock_ticker = Mock()
            mock_ticker.info = mock_info
            MockTicker.return_value = mock_ticker

            info = await connector.get_stock_info("TEST")

            assert info["ticker"] == "TEST"
            assert info["company_name"] == "Test Company"
            assert info["market_cap"] == 0  # Default value

    @pytest.mark.asyncio
    async def test_get_stock_info_exception(self):
        """Test stock info with exception."""
        connector = YahooFinanceConnector()

        with patch('yfinance.Ticker', side_effect=Exception("API Error")):
            info = await connector.get_stock_info("INVALID")

            assert info == {}

    @pytest.mark.asyncio
    async def test_get_quarterly_financials_success(self):
        """Test successful quarterly financials fetch."""
        connector = YahooFinanceConnector()

        # Create mock DataFrame
        mock_df = pd.DataFrame({
            "Revenue": [100000000, 95000000],
            "Net Income": [10000000, 8000000]
        })

        with patch('yfinance.Ticker') as MockTicker:
            mock_ticker = Mock()
            mock_ticker.quarterly_financials = mock_df
            MockTicker.return_value = mock_ticker

            df = await connector.get_quarterly_financials("DUOL")

            assert not df.empty
            assert "ticker" in df.columns
            assert df["ticker"].iloc[0] == "DUOL"

    @pytest.mark.asyncio
    async def test_get_quarterly_financials_empty(self):
        """Test quarterly financials with empty data."""
        connector = YahooFinanceConnector()

        with patch('yfinance.Ticker') as MockTicker:
            mock_ticker = Mock()
            mock_ticker.quarterly_financials = None
            MockTicker.return_value = mock_ticker

            df = await connector.get_quarterly_financials("DUOL")

            assert df.empty

    @pytest.mark.asyncio
    async def test_get_quarterly_financials_exception(self):
        """Test quarterly financials with exception."""
        connector = YahooFinanceConnector()

        with patch('yfinance.Ticker', side_effect=Exception("Fetch error")):
            df = await connector.get_quarterly_financials("INVALID")

            assert df.empty


# ============================================================================
# AlphaVantageConnector Tests
# ============================================================================


class TestAlphaVantageConnector:
    """Test AlphaVantageConnector methods."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = Mock(get_secret_value=lambda: "test_key")

            connector = AlphaVantageConnector()

            assert connector.fd is not None

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = None

            connector = AlphaVantageConnector()

            assert connector.fd is None

    @pytest.mark.asyncio
    async def test_get_company_overview_success(self):
        """Test successful company overview fetch."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = Mock(get_secret_value=lambda: "test_key")

            connector = AlphaVantageConnector()

            mock_data = {
                "MarketCapitalization": "5000000000",
                "PERatio": "125.5",
                "EPS": "1.50",
                "RevenueTTM": "500000000",
                "ProfitMargin": "0.15"
            }

            with patch.object(connector.fd, 'get_company_overview', return_value=(mock_data, None)):
                overview = await connector.get_company_overview("DUOL")

                assert overview["ticker"] == "DUOL"
                assert overview["market_cap"] == 5000000000.0
                assert overview["pe_ratio"] == 125.5

    @pytest.mark.asyncio
    async def test_get_company_overview_with_none_values(self):
        """Test company overview with None values."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = Mock(get_secret_value=lambda: "test_key")

            connector = AlphaVantageConnector()

            mock_data = {
                "MarketCapitalization": "None",
                "PERatio": None,
                "EPS": "",
                "RevenueTTM": "null"
            }

            with patch.object(connector.fd, 'get_company_overview', return_value=(mock_data, None)):
                overview = await connector.get_company_overview("DUOL")

                assert overview["market_cap"] == 0.0
                assert overview["pe_ratio"] == 0.0
                assert overview["eps"] == 0.0

    @pytest.mark.asyncio
    async def test_get_company_overview_no_api_key(self):
        """Test company overview without API key."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = None

            connector = AlphaVantageConnector()

            overview = await connector.get_company_overview("DUOL")

            assert overview == {}

    @pytest.mark.asyncio
    async def test_get_company_overview_exception(self):
        """Test company overview with exception."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.ALPHA_VANTAGE_API_KEY = Mock(get_secret_value=lambda: "test_key")

            connector = AlphaVantageConnector()

            with patch.object(connector.fd, 'get_company_overview', side_effect=Exception("API Error")):
                overview = await connector.get_company_overview("DUOL")

                assert overview == {}


# ============================================================================
# NewsAPIConnector Tests
# ============================================================================


class TestNewsAPIConnector:
    """Test NewsAPIConnector methods."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.NEWSAPI_KEY = "test_key"

            connector = NewsAPIConnector()

            assert connector.api_key == "test_key"

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.NEWSAPI_KEY = None

            connector = NewsAPIConnector()

            assert connector.api_key is None

    @pytest.mark.asyncio
    async def test_get_company_news_success(self):
        """Test successful company news fetch."""
        connector = NewsAPIConnector()
        connector.api_key = "test_key"

        mock_articles = [
            {
                "title": "Company shows growth",
                "description": "Positive news",
                "url": "https://news.com/article1",
                "publishedAt": "2024-03-15T10:00:00Z",
                "source": {"name": "TechNews"}
            }
        ]

        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"status": "ok", "articles": mock_articles})
            mock_session.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_response.__aenter__.return_value = mock_response
            MockSession.return_value = mock_session

            news = await connector.get_company_news("Duolingo")

            assert len(news) > 0
            assert "sentiment" in news[0]

    @pytest.mark.asyncio
    async def test_get_company_news_no_api_key(self):
        """Test company news without API key."""
        connector = NewsAPIConnector()
        connector.api_key = None

        news = await connector.get_company_news("Duolingo")

        assert news == []

    def test_analyze_sentiment_positive(self):
        """Test sentiment analysis with positive text."""
        connector = NewsAPIConnector()

        text = "Company shows strong growth and success with rising profits"
        sentiment = connector._analyze_sentiment(text)

        assert sentiment > 0

    def test_analyze_sentiment_negative(self):
        """Test sentiment analysis with negative text."""
        connector = NewsAPIConnector()

        text = "Company faces decline and loss with falling revenue"
        sentiment = connector._analyze_sentiment(text)

        assert sentiment < 0

    def test_analyze_sentiment_neutral(self):
        """Test sentiment analysis with neutral text."""
        connector = NewsAPIConnector()

        text = "Company announces quarterly report"
        sentiment = connector._analyze_sentiment(text)

        assert sentiment == 0


# ============================================================================
# DataAggregator Tests
# ============================================================================


class TestDataAggregator:
    """Test DataAggregator methods."""

    @pytest.mark.asyncio
    async def test_get_comprehensive_company_data_success(self):
        """Test successful comprehensive data aggregation."""
        aggregator = DataAggregator()

        # Mock all connector methods
        with patch.object(aggregator.sec, 'get_company_filings', new_callable=AsyncMock) as mock_sec, \
             patch.object(aggregator.yahoo, 'get_stock_info', new_callable=AsyncMock) as mock_yahoo, \
             patch.object(aggregator.alpha, 'get_company_overview', new_callable=AsyncMock) as mock_alpha, \
             patch.object(aggregator.news, 'get_company_news', new_callable=AsyncMock) as mock_news, \
             patch.object(aggregator.crunchbase, 'get_company_funding', new_callable=AsyncMock) as mock_crunchbase:

            mock_sec.return_value = [{"form": "10-K"}]
            mock_yahoo.return_value = {"market_cap": 5000000000}
            mock_alpha.return_value = {"revenue_ttm": 500000000}
            mock_news.return_value = [{"sentiment": 0.5}]
            mock_crunchbase.return_value = {"funding_total": 100000000}

            data = await aggregator.get_comprehensive_company_data("DUOL", "Duolingo Inc.")

            assert data["ticker"] == "DUOL"
            assert data["company_name"] == "Duolingo Inc."
            assert "sec_filings" in data
            assert "yahoo_finance" in data
            assert "composite_score" in data

    @pytest.mark.asyncio
    async def test_get_comprehensive_company_data_with_github(self):
        """Test comprehensive data with GitHub repo."""
        aggregator = DataAggregator()

        with patch.object(aggregator.sec, 'get_company_filings', new_callable=AsyncMock, return_value=[]), \
             patch.object(aggregator.yahoo, 'get_stock_info', new_callable=AsyncMock, return_value={}), \
             patch.object(aggregator.alpha, 'get_company_overview', new_callable=AsyncMock, return_value={}), \
             patch.object(aggregator.news, 'get_company_news', new_callable=AsyncMock, return_value=[]), \
             patch.object(aggregator.crunchbase, 'get_company_funding', new_callable=AsyncMock, return_value={}), \
             patch.object(aggregator.github, 'get_repo_metrics', new_callable=AsyncMock, return_value={"stars": 100}):

            data = await aggregator.get_comprehensive_company_data("DUOL", "Duolingo", github_repo="duolingo/duolingo")

            assert "github_metrics" in data
            assert data["github_metrics"]["stars"] == 100

    def test_calculate_composite_score_high_score(self):
        """Test composite score calculation with good metrics."""
        aggregator = DataAggregator()

        data = {
            "yahoo_finance": {"profit_margins": 0.20},
            "alpha_vantage": {"quarterly_revenue_growth_yoy": 0.30},
            "news_sentiment": [{"sentiment": 0.5}, {"sentiment": 0.3}],
            "github_metrics": {"recent_commits": 50}
        }

        score = aggregator._calculate_composite_score(data)

        assert score > 0
        assert score <= 100

    def test_calculate_composite_score_empty_data(self):
        """Test composite score with empty data."""
        aggregator = DataAggregator()

        data = {}

        score = aggregator._calculate_composite_score(data)

        assert score == 0.0
