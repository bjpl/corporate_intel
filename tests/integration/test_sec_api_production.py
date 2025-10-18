"""Production integration tests for SEC EDGAR API.

These tests validate the SEC API integration in a production-like environment.
They test real API connectivity, rate limiting, error handling, and data validation.

Test Categories:
1. API Connectivity Tests
2. Rate Limiting Tests
3. Data Validation Tests
4. Error Handling Tests
5. End-to-End Flow Tests

Usage:
    # Run all production tests
    pytest tests/integration/test_sec_api_production.py -v

    # Run specific test category
    pytest tests/integration/test_sec_api_production.py -k "connectivity" -v

    # Run with production environment
    ENV=production pytest tests/integration/test_sec_api_production.py -v

Notes:
    - Tests make real API calls to SEC EDGAR (rate limited)
    - Requires valid SEC_USER_AGENT in environment
    - Tests are marked as integration tests (can be skipped in CI)
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from src.core.config import get_settings
from src.pipeline.sec_ingestion import (
    FilingRequest,
    RateLimiter,
    SECAPIClient,
    batch_sec_ingestion_flow,
    download_filing,
    fetch_company_data,
    fetch_filings,
    sec_ingestion_flow,
    validate_filing_data,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sec_client():
    """Create SEC API client for testing."""
    return SECAPIClient()


@pytest.fixture
def test_ticker():
    """Test ticker symbol (Duolingo - known EdTech company)."""
    return "DUOL"


@pytest.fixture
def test_cik():
    """Test CIK for Duolingo."""
    return "0001364612"


# ============================================================================
# API Connectivity Tests
# ============================================================================


class TestAPIConnectivity:
    """Test SEC EDGAR API connectivity and authentication."""

    @pytest.mark.asyncio
    async def test_user_agent_configured(self, sec_client):
        """Test that User-Agent header is properly configured."""
        assert "User-Agent" in sec_client.headers
        user_agent = sec_client.headers["User-Agent"]

        # Validate User-Agent format
        assert user_agent, "User-Agent header is empty"
        assert "@" in user_agent, "User-Agent should contain email address"
        assert "example.com" not in user_agent, "User-Agent contains placeholder email"

        # Validate it matches environment configuration
        settings = get_settings()
        assert user_agent == settings.SEC_USER_AGENT

    @pytest.mark.asyncio
    async def test_ticker_to_cik_mapping_fetch(self, sec_client):
        """Test fetching ticker-to-CIK mapping from SEC."""
        mapping = await sec_client.get_ticker_to_cik_mapping()

        # Validate mapping loaded
        assert isinstance(mapping, dict)
        assert len(mapping) > 0, "Ticker mapping is empty"

        # Validate known tickers exist
        known_tickers = ["DUOL", "CHGG", "AAPL", "MSFT"]
        for ticker in known_tickers:
            assert ticker in mapping, f"Ticker {ticker} not found in mapping"

        # Validate CIK format (10-digit zero-padded)
        duol_cik = mapping.get("DUOL")
        assert len(duol_cik) == 10, "CIK should be 10 digits"
        assert duol_cik.isdigit(), "CIK should be numeric"

    @pytest.mark.asyncio
    async def test_company_info_fetch(self, sec_client, test_ticker):
        """Test fetching company information from SEC."""
        company_info = await sec_client.get_company_info(test_ticker)

        # Validate response structure
        assert isinstance(company_info, dict)
        assert company_info, f"No company info returned for {test_ticker}"

        # Validate required fields
        assert "cik" in company_info
        assert "name" in company_info

        # Validate data quality
        assert "Duolingo" in company_info["name"]
        assert company_info["cik"] == "0001364612"

    @pytest.mark.asyncio
    async def test_filings_list_fetch(self, sec_client, test_cik):
        """Test fetching filing list for a company."""
        filing_types = ["10-K", "10-Q"]
        start_date = datetime(2023, 1, 1)

        filings = await sec_client.get_filings(test_cik, filing_types, start_date)

        # Validate response
        assert isinstance(filings, list)
        assert len(filings) > 0, "No filings returned"

        # Validate filing structure
        first_filing = filings[0]
        assert "form" in first_filing
        assert "filingDate" in first_filing
        assert "accessionNumber" in first_filing
        assert "primaryDocument" in first_filing

        # Validate filing type filtering
        assert first_filing["form"] in filing_types

    @pytest.mark.asyncio
    async def test_filing_content_download(self, sec_client, test_cik):
        """Test downloading filing content."""
        # First get a recent filing
        filings = await sec_client.get_filings(test_cik, ["10-K"], datetime(2023, 1, 1))
        assert len(filings) > 0, "No filings to download"

        # Download first filing
        filing = filings[0]
        content = await sec_client.download_filing_content(filing)

        # Validate content
        assert isinstance(content, str)
        assert len(content) > 0, "Filing content is empty"
        assert len(content) > 1000, "Filing content suspiciously short"

        # Validate HTML/XBRL content markers
        assert "<" in content or "<?xml" in content, "Content doesn't appear to be HTML/XML"


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Test rate limiting implementation."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(calls_per_second=10)

        assert limiter.calls_per_second == 10
        assert limiter.min_interval == 0.1  # 1/10 second
        assert limiter.last_call == 0.0

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_delay(self):
        """Test that rate limiter enforces minimum delay between calls."""
        limiter = RateLimiter(calls_per_second=10)

        # First call should be immediate
        start = time.time()
        await limiter.acquire()
        first_call_time = time.time() - start
        assert first_call_time < 0.01, "First call should be immediate"

        # Second call should be delayed
        start = time.time()
        await limiter.acquire()
        second_call_time = time.time() - start
        assert 0.09 < second_call_time < 0.12, f"Expected ~0.1s delay, got {second_call_time}s"

    @pytest.mark.asyncio
    async def test_rate_limiter_multiple_calls(self):
        """Test rate limiter with multiple sequential calls."""
        limiter = RateLimiter(calls_per_second=10)

        start = time.time()
        for _ in range(5):
            await limiter.acquire()
        total_time = time.time() - start

        # Should take at least 0.4 seconds (4 delays of 0.1s each)
        assert total_time >= 0.38, f"Expected >=0.4s for 5 calls, got {total_time}s"
        assert total_time < 0.6, f"Rate limiter too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_api_client_uses_rate_limiter(self, sec_client):
        """Test that API client uses rate limiter for requests."""
        # Verify rate limiter is configured
        assert hasattr(sec_client, "rate_limiter")
        assert sec_client.rate_limiter.calls_per_second == 10

        # Make multiple API calls and measure timing
        start = time.time()
        for _ in range(3):
            await sec_client.get_ticker_to_cik_mapping()  # Uses cache after first call
        elapsed = time.time() - start

        # First call fetches, subsequent use cache (should be fast)
        assert elapsed < 1.0, "Cached calls should be fast"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_request_rate(self, sec_client, test_cik):
        """Test that sustained requests maintain proper rate limiting.

        Note: This test makes multiple API calls and takes ~2 seconds.
        """
        # Make 20 requests (should take ~2 seconds at 10 req/sec)
        start = time.time()
        tasks = []
        for _ in range(20):
            task = sec_client.get_filings(test_cik, ["10-K"])
            tasks.append(task)

        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Should take approximately 2 seconds (allowing some variance)
        assert 1.8 < elapsed < 2.5, f"Expected ~2s for 20 requests, got {elapsed}s"


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Test data validation using Great Expectations."""

    @pytest.mark.asyncio
    async def test_valid_filing_passes_validation(self, sec_client, test_cik):
        """Test that valid filing data passes validation."""
        # Fetch and download a real filing
        filings = await sec_client.get_filings(test_cik, ["10-Q"], datetime(2024, 1, 1))
        assert len(filings) > 0

        filing = filings[0]
        content = await sec_client.download_filing_content(filing)

        # Build filing data structure
        filing_data = {
            **filing,
            "content": content,
            "content_hash": "a" * 64,  # Mock hash
            "downloaded_at": datetime.utcnow().isoformat(),
        }

        # Validate
        is_valid = validate_filing_data(filing_data)
        assert is_valid, "Valid filing should pass validation"

    def test_missing_required_fields_fails(self):
        """Test that missing required fields fail validation."""
        incomplete_filing = {
            "accessionNumber": "0001234567-89-012345",
            "form": "10-K",
            # Missing: filingDate, cik, content, content_hash, downloaded_at
        }

        is_valid = validate_filing_data(incomplete_filing)
        assert not is_valid, "Filing with missing fields should fail validation"

    def test_invalid_accession_number_format_fails(self):
        """Test that invalid accession number format fails validation."""
        invalid_filing = {
            "accessionNumber": "invalid-format",  # Wrong format
            "form": "10-K",
            "filingDate": "2024-03-15",
            "cik": "1234567890",
            "content": "Test content " * 100,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat(),
        }

        is_valid = validate_filing_data(invalid_filing)
        assert not is_valid, "Filing with invalid accession number should fail"

    def test_invalid_filing_type_fails(self):
        """Test that invalid filing type fails validation."""
        invalid_filing = {
            "accessionNumber": "0001234567-89-012345",
            "form": "INVALID-FORM",  # Invalid form type
            "filingDate": "2024-03-15",
            "cik": "1234567890",
            "content": "Test content " * 100,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat(),
        }

        is_valid = validate_filing_data(invalid_filing)
        assert not is_valid, "Filing with invalid form type should fail"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_ticker_returns_empty(self, sec_client):
        """Test that invalid ticker returns empty result."""
        company_info = await sec_client.get_company_info("INVALID_TICKER_XYZ")
        assert company_info == {}, "Invalid ticker should return empty dict"

    @pytest.mark.asyncio
    async def test_invalid_cik_returns_empty(self, sec_client):
        """Test that invalid CIK returns empty filing list."""
        filings = await sec_client.get_filings("9999999999", ["10-K"])
        assert filings == [], "Invalid CIK should return empty list"

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, sec_client):
        """Test handling of network timeouts."""
        # This test would require mocking or intentionally causing timeout
        # Skipping actual implementation as it requires network manipulation
        pass

    @pytest.mark.asyncio
    async def test_malformed_api_response(self, sec_client):
        """Test handling of malformed API responses."""
        # This test would require mocking SEC API responses
        # Skipping actual implementation as it requires response mocking
        pass


# ============================================================================
# End-to-End Flow Tests
# ============================================================================


class TestEndToEndFlows:
    """Test complete ingestion workflows."""

    @pytest.mark.asyncio
    async def test_fetch_company_data_task(self, test_ticker):
        """Test fetch_company_data Prefect task."""
        result = await fetch_company_data(test_ticker)

        assert isinstance(result, dict)
        assert result["ticker"] == test_ticker.upper()
        assert "cik" in result
        assert "name" in result
        assert "category" in result
        assert "Duolingo" in result["name"]

    @pytest.mark.asyncio
    async def test_fetch_filings_task(self, test_cik):
        """Test fetch_filings Prefect task."""
        filing_types = ["10-K", "10-Q"]
        start_date = datetime(2023, 1, 1)

        result = await fetch_filings(test_cik, filing_types, start_date)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(f["form"] in filing_types for f in result)

    @pytest.mark.asyncio
    async def test_download_filing_task(self, sec_client, test_cik):
        """Test download_filing Prefect task."""
        # Get a filing to download
        filings = await sec_client.get_filings(test_cik, ["10-Q"], datetime(2024, 1, 1))
        assert len(filings) > 0

        filing = filings[0]
        result = await download_filing(filing)

        # Validate result structure
        assert "content" in result
        assert "content_hash" in result
        assert "downloaded_at" in result
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_ingestion_flow_single_company(self, test_ticker):
        """Test complete ingestion flow for single company.

        Note: This test makes multiple API calls and may take 10+ seconds.
        """
        request = FilingRequest(
            company_ticker=test_ticker,
            filing_types=["10-K"],
            start_date=datetime(2024, 1, 1),
        )

        result = await sec_ingestion_flow(request)

        # Validate result
        assert result is not None
        assert result["ticker"] == test_ticker.upper()
        assert "cik" in result
        assert "filings_found" in result
        assert "filings_stored" in result

        # Should find at least one 10-K filing in 2024
        assert result["filings_found"] >= 1

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_batch_ingestion_flow(self):
        """Test batch ingestion for multiple companies.

        Note: This test makes many API calls and may take 30+ seconds.
        """
        test_tickers = ["DUOL", "CHGG"]  # Small batch for testing

        results = await batch_sec_ingestion_flow(test_tickers)

        # Validate results
        assert len(results) == len(test_tickers)
        assert all(r is not None for r in results)

        # Check that we got data for each company
        for result in results:
            assert "ticker" in result
            assert "filings_found" in result


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance characteristics of SEC API integration."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_caching_improves_performance(self, sec_client):
        """Test that caching reduces API call latency."""
        # First call (uncached)
        start = time.time()
        await sec_client.get_ticker_to_cik_mapping()
        first_call_time = time.time() - start

        # Second call (cached)
        start = time.time()
        await sec_client.get_ticker_to_cik_mapping()
        second_call_time = time.time() - start

        # Cached call should be significantly faster
        assert second_call_time < first_call_time / 10, (
            f"Cached call ({second_call_time}s) should be much faster than "
            f"first call ({first_call_time}s)"
        )

    @pytest.mark.asyncio
    async def test_concurrent_downloads_performance(self, sec_client, test_cik):
        """Test performance of concurrent filing downloads."""
        # Get multiple filings
        filings = await sec_client.get_filings(test_cik, ["10-K", "10-Q"], datetime(2023, 1, 1))
        filings = filings[:5]  # Limit to 5 for testing

        # Sequential downloads
        start = time.time()
        for filing in filings:
            await sec_client.download_filing_content(filing)
        sequential_time = time.time() - start

        # Concurrent downloads
        start = time.time()
        tasks = [sec_client.download_filing_content(f) for f in filings]
        await asyncio.gather(*tasks)
        concurrent_time = time.time() - start

        # Concurrent should be faster (though limited by rate limiter)
        # At 10 req/sec, 5 downloads take ~0.5s minimum
        assert concurrent_time < sequential_time


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Test production configuration loading and validation."""

    def test_sec_api_config_loaded(self):
        """Test that SEC API configuration can be loaded."""
        import yaml
        from pathlib import Path

        config_path = Path(__file__).parents[2] / "config" / "production" / "sec-api-config.yml"

        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Validate key configuration sections
            assert "api" in config
            assert "rate_limiting" in config
            assert "ingestion" in config
            assert "validation" in config

            # Validate rate limiting config
            assert config["rate_limiting"]["requests_per_second"] == 10

    def test_environment_variables_configured(self):
        """Test that required environment variables are set."""
        settings = get_settings()

        # SEC User-Agent must be configured
        assert settings.SEC_USER_AGENT
        assert "@" in settings.SEC_USER_AGENT
        assert "example.com" not in settings.SEC_USER_AGENT.lower()

        # Rate limit should match SEC requirements
        assert settings.SEC_RATE_LIMIT == 10
