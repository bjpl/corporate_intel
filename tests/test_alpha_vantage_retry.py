"""
Test suite for Alpha Vantage retry logic with exponential backoff.

This test verifies:
1. Retry decorator configuration
2. Error categorization
3. Response validation
4. Retry count tracking
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.pipeline.alpha_vantage_ingestion import (
    AlphaVantageIngestionResult,
    ingest_alpha_vantage_for_company,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_connector():
    """Create a mock Alpha Vantage connector."""
    connector = MagicMock()
    connector.get_company_overview = AsyncMock()
    return connector


@pytest.mark.asyncio
async def test_successful_ingestion_no_retry(mock_session, mock_connector):
    """Test successful ingestion on first attempt (no retry needed)."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Mock successful API response
    mock_connector.get_company_overview.return_value = {
        'ticker': 'TEST',
        'pe_ratio': 15.5,
        'eps': 2.50,
        'market_cap': 1000000000,
        'profit_margin': 0.15,
    }

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is True
    assert result.retry_count == 0
    assert result.error_category is None
    assert result.metrics_fetched == 5
    assert mock_session.commit.called
    assert not mock_session.rollback.called


@pytest.mark.asyncio
async def test_network_error_with_retry(mock_session, mock_connector):
    """Test retry logic for network errors."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Simulate network error on first 2 attempts, success on 3rd
    mock_connector.get_company_overview.side_effect = [
        aiohttp.ClientError("Connection failed"),
        aiohttp.ClientError("Connection failed"),
        {
            'ticker': 'TEST',
            'pe_ratio': 15.5,
            'eps': 2.50,
        }
    ]

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is True
    assert result.retry_count == 2
    assert mock_connector.get_company_overview.call_count == 3


@pytest.mark.asyncio
async def test_network_error_max_retries_exceeded(mock_session, mock_connector):
    """Test that retries stop after max attempts."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Simulate persistent network error
    mock_connector.get_company_overview.side_effect = aiohttp.ClientError("Connection failed")

    with pytest.raises(aiohttp.ClientError):
        await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    # Should attempt 3 times (initial + 2 retries)
    assert mock_connector.get_company_overview.call_count == 3


@pytest.mark.asyncio
async def test_timeout_error_with_retry(mock_session, mock_connector):
    """Test retry logic for timeout errors."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Simulate timeout on first attempt, success on second
    mock_connector.get_company_overview.side_effect = [
        asyncio.TimeoutError(),
        {
            'ticker': 'TEST',
            'pe_ratio': 15.5,
        }
    ]

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is True
    assert result.retry_count == 1
    assert mock_connector.get_company_overview.call_count == 2


@pytest.mark.asyncio
async def test_data_quality_error_no_retry(mock_session, mock_connector):
    """Test that data quality errors do NOT trigger retry."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Simulate data with 'None' string values (data quality issue)
    mock_connector.get_company_overview.side_effect = ValueError("could not convert string 'None' to float")

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is False
    assert result.error_category == "data_quality_error"
    assert result.retry_count == 0
    assert "data quality issue" in result.error_message.lower()
    # Should only attempt once (no retry for data quality errors)
    assert mock_connector.get_company_overview.call_count == 1


@pytest.mark.asyncio
async def test_invalid_response_format(mock_session, mock_connector):
    """Test validation for invalid API response format."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Return empty dict (invalid)
    mock_connector.get_company_overview.return_value = {}

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is False
    assert result.error_category == "api_format_error"
    assert "Invalid API response format" in result.error_message


@pytest.mark.asyncio
async def test_ticker_mismatch_validation(mock_session, mock_connector):
    """Test validation for ticker mismatch in response."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Return data for wrong ticker
    mock_connector.get_company_overview.return_value = {
        'ticker': 'WRONG',
        'pe_ratio': 15.5,
    }

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is False
    assert result.error_category == "data_validation_error"
    assert "Ticker mismatch" in result.error_message


@pytest.mark.asyncio
async def test_no_valid_metrics(mock_session, mock_connector):
    """Test handling of response with no valid metrics."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Return data with only ticker, no metrics
    mock_connector.get_company_overview.return_value = {
        'ticker': 'TEST',
    }

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is False
    assert result.error_category == "no_data"
    assert "No valid metrics" in result.error_message


@pytest.mark.asyncio
async def test_database_error_categorization(mock_session, mock_connector):
    """Test proper categorization of database errors."""
    # Mock failed company lookup
    mock_session.execute.side_effect = Exception("Database connection failed")

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is False
    assert result.error_category == "unexpected_error"
    assert "Unexpected error" in result.error_message


@pytest.mark.asyncio
async def test_result_dict_includes_retry_info(mock_session, mock_connector):
    """Test that result dictionary includes retry information."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Simulate one retry
    mock_connector.get_company_overview.side_effect = [
        aiohttp.ClientError("Connection failed"),
        {
            'ticker': 'TEST',
            'pe_ratio': 15.5,
        }
    ]

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)
    result_dict = result.to_dict()

    assert 'retry_count' in result_dict
    assert result_dict['retry_count'] == 1
    assert 'error_category' in result_dict


@pytest.mark.asyncio
async def test_conversion_error_categorization(mock_session, mock_connector):
    """Test proper categorization of value conversion errors."""
    # Mock company lookup
    mock_company = MagicMock()
    mock_company.id = "test-company-id"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_company
    mock_session.execute.return_value = mock_result

    # Simulate conversion error (not 'None' related)
    mock_connector.get_company_overview.side_effect = ValueError("invalid literal for float()")

    result = await ingest_alpha_vantage_for_company('TEST', mock_connector, mock_session)

    assert result.success is False
    assert result.error_category == "conversion_error"
    assert "Value conversion error" in result.error_message
    assert result.retry_count == 0  # No retry for conversion errors
