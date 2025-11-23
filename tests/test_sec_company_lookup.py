"""Test SEC company lookup and deduplication logic."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company
from src.pipeline.sec_ingestion import get_or_create_company


@pytest.fixture
def sample_filing_data():
    """Sample filing data for testing."""
    return {
        "accessionNumber": "0001234567-23-000001",
        "form": "10-K",
        "filingDate": "2023-12-31",
        "content": "Sample filing content",
        "ticker": "AAPL",
        "companyName": "Apple Inc.",
        "category": "enabling_technology",
    }


@pytest.fixture
def mock_sec_client():
    """Mock SEC API client."""
    client = MagicMock()
    client.BASE_URL = "https://data.sec.gov"
    client.headers = {"User-Agent": "test"}
    client.rate_limiter = MagicMock()
    client.rate_limiter.acquire = AsyncMock()

    # Mock ticker mapping
    ticker_mapping = {
        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "GOOGL": "0001652044",
    }

    async def get_ticker_mapping():
        return ticker_mapping

    client.get_ticker_to_cik_mapping = get_ticker_mapping
    return client


@pytest.mark.asyncio
async def test_company_lookup_by_cik(mock_session, sample_filing_data, mock_sec_client):
    """Test that existing company is found by CIK."""
    # Create existing company
    existing_company = Company(
        cik="0000320193",
        ticker="AAPL",
        name="Apple Inc.",
        category="enabling_technology",
    )

    # Mock session execute to return existing company
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_company
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.pipeline.sec_ingestion.SECAPIClient", return_value=mock_sec_client):
        company = await get_or_create_company(
            mock_session, "0000320193", sample_filing_data
        )

    assert company == existing_company
    assert company.cik == "0000320193"
    assert company.name == "Apple Inc."
    # Should not add new company
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_company_lookup_by_ticker(mock_session, sample_filing_data, mock_sec_client):
    """Test that existing company is found by ticker when CIK lookup fails."""
    existing_company = Company(
        cik=None,  # No CIK initially
        ticker="AAPL",
        name="Apple Inc.",
        category="enabling_technology",
    )

    # Mock session execute to:
    # 1. Return None for CIK lookup
    # 2. Return existing company for ticker lookup
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None

    mock_result_found = MagicMock()
    mock_result_found.scalar_one_or_none.return_value = existing_company

    mock_session.execute = AsyncMock(
        side_effect=[mock_result_none, mock_result_found]
    )

    with patch("src.pipeline.sec_ingestion.SECAPIClient", return_value=mock_sec_client):
        company = await get_or_create_company(
            mock_session, "0000320193", sample_filing_data
        )

    assert company == existing_company
    assert company.ticker == "AAPL"
    # Should update CIK
    assert company.cik == "0000320193"
    # Should not add new company
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_company_creation_with_sec_name(
    mock_session, sample_filing_data, mock_sec_client
):
    """Test that new company is created with proper name from SEC."""
    # Mock session execute to return None (no existing company)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Mock SEC API response for company name
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "sic": "3571",
    }

    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    with patch("src.pipeline.sec_ingestion.SECAPIClient", return_value=mock_sec_client):
        with patch("httpx.AsyncClient", return_value=mock_http_client):
            company = await get_or_create_company(
                mock_session, "0000320193", sample_filing_data
            )

    # Should create new company with SEC name
    mock_session.add.assert_called_once()
    created_company = mock_session.add.call_args[0][0]
    assert created_company.cik == "0000320193"
    assert created_company.ticker == "AAPL"
    assert created_company.name == "Apple Inc."
    assert "Company CIK" not in created_company.name


@pytest.mark.asyncio
async def test_no_duplicate_company_on_rerun(
    mock_session, sample_filing_data, mock_sec_client
):
    """Test that running script again doesn't create duplicates."""
    # Simulate first run - company created
    existing_company = Company(
        cik="0000320193",
        ticker="AAPL",
        name="Apple Inc.",
        category="enabling_technology",
    )

    # Mock session to return existing company
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_company
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.pipeline.sec_ingestion.SECAPIClient", return_value=mock_sec_client):
        # First call
        company1 = await get_or_create_company(
            mock_session, "0000320193", sample_filing_data
        )

        # Second call (simulating rerun)
        company2 = await get_or_create_company(
            mock_session, "0000320193", sample_filing_data
        )

    # Should return same company both times
    assert company1 == company2
    assert company1.cik == "0000320193"
    # Should not add new company on second run
    mock_session.add.assert_not_called()


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
