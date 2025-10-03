"""
Unit Tests for Integration Services

Tests SEC EDGAR API integration, Yahoo Finance integration,
rate limiting logic, and error retry mechanisms.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import time
import requests

from app.services.integrations import (
    SECEdgarClient,
    YahooFinanceClient,
    RateLimiter,
    RetryManager,
    APIClient
)
from app.core.exceptions import (
    APIError,
    RateLimitError,
    AuthenticationError,
    DataNotFoundError
)


class TestSECEdgarClient:
    """Test suite for SEC EDGAR API integration"""

    @pytest.fixture
    def client(self):
        """Create SEC EDGAR client instance"""
        return SECEdgarClient(user_agent='test@example.com')

    def test_fetch_company_filings_success(self, client):
        """Test successful company filings retrieval"""
        # Arrange
        cik = '0000320193'  # Apple Inc.
        mock_response = {
            'filings': {
                'recent': {
                    'accessionNumber': ['0001193125-24-001234'],
                    'filingDate': ['2024-01-15'],
                    'form': ['10-K'],
                    'primaryDocument': ['aapl-20231230.htm']
                }
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            filings = client.get_company_filings(cik)

            # Assert
            assert len(filings) > 0
            assert filings[0]['form'] == '10-K'
            assert 'filingDate' in filings[0]

    def test_fetch_company_filings_with_form_filter(self, client):
        """Test company filings retrieval with form type filter"""
        # Arrange
        cik = '0000320193'
        form_type = '10-Q'

        mock_response = {
            'filings': {
                'recent': {
                    'accessionNumber': ['0001193125-24-001234', '0001193125-24-005678'],
                    'filingDate': ['2024-01-15', '2024-04-15'],
                    'form': ['10-Q', '8-K'],
                    'primaryDocument': ['doc1.htm', 'doc2.htm']
                }
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            filings = client.get_company_filings(cik, form_type=form_type)

            # Assert
            assert all(f['form'] == form_type for f in filings)

    def test_fetch_filing_document(self, client):
        """Test fetching specific filing document"""
        # Arrange
        accession_number = '0001193125-24-001234'
        mock_html = '<html><body>Filing content</body></html>'

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = mock_html

            # Act
            document = client.get_filing_document(accession_number)

            # Assert
            assert document == mock_html
            assert '<body>' in document

    def test_parse_10k_filing(self, client):
        """Test parsing 10-K filing structure"""
        # Arrange
        filing_html = """
        <html>
            <body>
                <div>Item 1. Business</div>
                <div>Item 1A. Risk Factors</div>
                <div>Item 7. MD&A</div>
                <div>Item 8. Financial Statements</div>
            </body>
        </html>
        """

        # Act
        parsed = client.parse_10k(filing_html)

        # Assert
        assert 'business' in parsed
        assert 'risk_factors' in parsed
        assert 'mda' in parsed
        assert 'financial_statements' in parsed

    def test_handle_api_rate_limit(self, client):
        """Test handling of SEC API rate limit"""
        # Arrange
        cik = '0000320193'

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 429
            mock_get.return_value.headers = {'Retry-After': '5'}

            # Act & Assert
            with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                client.get_company_filings(cik)

    def test_handle_company_not_found(self, client):
        """Test handling of non-existent company CIK"""
        # Arrange
        cik = '9999999999'

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 404

            # Act & Assert
            with pytest.raises(DataNotFoundError, match="Company not found"):
                client.get_company_filings(cik)

    def test_search_companies_by_name(self, client):
        """Test company search by name"""
        # Arrange
        company_name = 'Apple'
        mock_response = {
            'data': [
                ['APPLE INC', '0000320193', 'AAPL']
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            results = client.search_company(company_name)

            # Assert
            assert len(results) > 0
            assert 'APPLE' in results[0]['name']

    def test_validate_user_agent_required(self, client):
        """Test that user agent is required for SEC API"""
        # Arrange
        with patch('requests.get') as mock_get:
            # Act
            client.get_company_filings('0000320193')

            # Assert
            call_args = mock_get.call_args
            assert 'User-Agent' in call_args[1]['headers']


class TestYahooFinanceClient:
    """Test suite for Yahoo Finance API integration"""

    @pytest.fixture
    def client(self):
        """Create Yahoo Finance client instance"""
        return YahooFinanceClient()

    def test_fetch_stock_quote(self, client):
        """Test fetching current stock quote"""
        # Arrange
        ticker = 'AAPL'
        mock_response = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 175.50,
                        'regularMarketVolume': 50000000,
                        'marketCap': 2800000000000
                    }
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            quote = client.get_quote(ticker)

            # Assert
            assert quote['price'] == 175.50
            assert quote['volume'] == 50000000
            assert 'marketCap' in quote

    def test_fetch_historical_data(self, client):
        """Test fetching historical price data"""
        # Arrange
        ticker = 'AAPL'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        mock_response = {
            'chart': {
                'result': [{
                    'timestamp': [1704067200, 1704153600],
                    'indicators': {
                        'quote': [{
                            'open': [175.0, 176.0],
                            'high': [177.0, 178.0],
                            'low': [174.0, 175.0],
                            'close': [176.0, 177.0],
                            'volume': [50000000, 51000000]
                        }]
                    }
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            history = client.get_historical_data(ticker, start_date, end_date)

            # Assert
            assert len(history) == 2
            assert history[0]['close'] == 176.0

    def test_fetch_company_info(self, client):
        """Test fetching company information"""
        # Arrange
        ticker = 'AAPL'
        mock_response = {
            'quoteSummary': {
                'result': [{
                    'assetProfile': {
                        'industry': 'Consumer Electronics',
                        'sector': 'Technology',
                        'employees': 164000
                    },
                    'summaryDetail': {
                        'marketCap': {'raw': 2800000000000},
                        'trailingPE': {'raw': 28.5}
                    }
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            info = client.get_company_info(ticker)

            # Assert
            assert info['industry'] == 'Consumer Electronics'
            assert info['employees'] == 164000

    def test_fetch_financial_statements(self, client):
        """Test fetching financial statements"""
        # Arrange
        ticker = 'AAPL'
        mock_response = {
            'quoteSummary': {
                'result': [{
                    'incomeStatementHistory': {
                        'incomeStatementHistory': [{
                            'totalRevenue': {'raw': 383285000000},
                            'netIncome': {'raw': 96995000000}
                        }]
                    }
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            # Act
            financials = client.get_financials(ticker)

            # Assert
            assert 'totalRevenue' in financials
            assert financials['totalRevenue'] == 383285000000

    def test_handle_invalid_ticker(self, client):
        """Test handling of invalid ticker symbol"""
        # Arrange
        ticker = 'INVALID123'

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 404

            # Act & Assert
            with pytest.raises(DataNotFoundError, match="Ticker not found"):
                client.get_quote(ticker)

    def test_handle_api_error(self, client):
        """Test handling of Yahoo Finance API errors"""
        # Arrange
        ticker = 'AAPL'

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 500

            # Act & Assert
            with pytest.raises(APIError, match="API request failed"):
                client.get_quote(ticker)


class TestRateLimiter:
    """Test suite for rate limiting logic"""

    @pytest.fixture
    def limiter(self):
        """Create rate limiter instance"""
        return RateLimiter(max_requests=10, time_window=60)

    def test_allow_request_within_limit(self, limiter):
        """Test allowing requests within rate limit"""
        # Act
        for i in range(10):
            allowed = limiter.allow_request('test-endpoint')
            # Assert
            assert allowed == True

    def test_block_request_exceeding_limit(self, limiter):
        """Test blocking requests exceeding rate limit"""
        # Arrange
        for i in range(10):
            limiter.allow_request('test-endpoint')

        # Act
        allowed = limiter.allow_request('test-endpoint')

        # Assert
        assert allowed == False

    def test_reset_after_time_window(self, limiter):
        """Test rate limit reset after time window expires"""
        # Arrange
        limiter = RateLimiter(max_requests=5, time_window=1)

        for i in range(5):
            limiter.allow_request('test-endpoint')

        # Act - Wait for time window to expire
        time.sleep(1.1)
        allowed = limiter.allow_request('test-endpoint')

        # Assert
        assert allowed == True

    def test_different_endpoints_separate_limits(self, limiter):
        """Test that different endpoints have separate rate limits"""
        # Arrange
        for i in range(10):
            limiter.allow_request('endpoint-1')

        # Act
        allowed_endpoint_2 = limiter.allow_request('endpoint-2')

        # Assert
        assert allowed_endpoint_2 == True

    def test_get_retry_after_time(self, limiter):
        """Test getting retry-after time when rate limited"""
        # Arrange
        for i in range(10):
            limiter.allow_request('test-endpoint')

        # Act
        retry_after = limiter.get_retry_after('test-endpoint')

        # Assert
        assert retry_after > 0
        assert retry_after <= 60

    def test_token_bucket_algorithm(self):
        """Test token bucket rate limiting algorithm"""
        # Arrange
        limiter = RateLimiter(
            max_requests=10,
            time_window=60,
            algorithm='token_bucket'
        )

        # Act - Burst of requests
        results = [limiter.allow_request('test') for _ in range(15)]

        # Assert
        assert sum(results) == 10  # Only 10 requests allowed


class TestRetryManager:
    """Test suite for error retry mechanisms"""

    @pytest.fixture
    def retry_manager(self):
        """Create retry manager instance"""
        return RetryManager(max_retries=3, backoff_factor=2)

    def test_retry_transient_error_success(self, retry_manager):
        """Test successful retry after transient error"""
        # Arrange
        mock_func = Mock(side_effect=[
            Exception("Transient error"),
            Exception("Transient error"),
            "Success"
        ])

        # Act
        result = retry_manager.execute_with_retry(mock_func)

        # Assert
        assert result == "Success"
        assert mock_func.call_count == 3

    def test_retry_exhaustion(self, retry_manager):
        """Test retry exhaustion after max attempts"""
        # Arrange
        mock_func = Mock(side_effect=Exception("Persistent error"))

        # Act & Assert
        with pytest.raises(Exception, match="Persistent error"):
            retry_manager.execute_with_retry(mock_func)

        assert mock_func.call_count == 4  # Initial + 3 retries

    def test_exponential_backoff(self, retry_manager):
        """Test exponential backoff between retries"""
        # Arrange
        mock_func = Mock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "Success"
        ])

        start_time = time.time()

        # Act
        retry_manager.execute_with_retry(mock_func)

        elapsed_time = time.time() - start_time

        # Assert
        # Should wait: 2^0 + 2^1 = 3 seconds minimum
        assert elapsed_time >= 3

    def test_retry_with_jitter(self, retry_manager):
        """Test retry with jitter to prevent thundering herd"""
        # Arrange
        retry_manager.enable_jitter = True
        mock_func = Mock(side_effect=[Exception("Error"), "Success"])

        # Act
        result = retry_manager.execute_with_retry(mock_func)

        # Assert
        assert result == "Success"

    def test_retry_only_retriable_errors(self, retry_manager):
        """Test that only retriable errors are retried"""
        # Arrange
        retriable_errors = [ConnectionError, TimeoutError]
        retry_manager.retriable_errors = retriable_errors

        # Non-retriable error
        mock_func = Mock(side_effect=ValueError("Non-retriable"))

        # Act & Assert
        with pytest.raises(ValueError):
            retry_manager.execute_with_retry(mock_func)

        assert mock_func.call_count == 1  # No retries

    def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for failing services"""
        # Arrange
        retry_manager = RetryManager(
            max_retries=3,
            circuit_breaker=True,
            failure_threshold=5
        )

        mock_func = Mock(side_effect=Exception("Service down"))

        # Act - Trigger circuit breaker
        for i in range(6):
            try:
                retry_manager.execute_with_retry(mock_func)
            except:
                pass

        # Assert - Circuit should be open
        assert retry_manager.circuit_state == 'open'


class TestAPIClient:
    """Integration tests for base API client"""

    @pytest.fixture
    def client(self):
        """Create API client instance"""
        return APIClient(
            base_url='https://api.example.com',
            rate_limiter=RateLimiter(max_requests=10, time_window=60),
            retry_manager=RetryManager(max_retries=3)
        )

    def test_request_with_rate_limiting(self, client):
        """Test API request with rate limiting"""
        # Arrange
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'data': 'test'}

            # Act
            result = client.get('/endpoint')

            # Assert
            assert result == {'data': 'test'}

    def test_request_with_retry_on_failure(self, client):
        """Test API request with automatic retry"""
        # Arrange
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                requests.exceptions.ConnectionError(),
                requests.exceptions.Timeout(),
                Mock(status_code=200, json=lambda: {'data': 'success'})
            ]

            # Act
            result = client.get('/endpoint')

            # Assert
            assert result == {'data': 'success'}
            assert mock_get.call_count == 3

    def test_handle_authentication_error(self, client):
        """Test handling of authentication errors"""
        # Arrange
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 401

            # Act & Assert
            with pytest.raises(AuthenticationError):
                client.get('/endpoint')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
