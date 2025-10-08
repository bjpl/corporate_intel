"""Standalone real-world API tests without pipeline dependencies.

These tests validate API connectivity and data quality without importing
the full ingestion pipeline, avoiding Prefect/pydantic-settings dependency issues.

USAGE:
  pytest tests/integration/test_real_world_standalone.py --real-world -v

This is a workaround to test real-world API integration while dependency
issues are being resolved. Once dependencies are fixed, use the full test suite
in test_real_world_ingestion.py instead.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

import httpx
import pytest
import yfinance as yf
from sqlalchemy import select

from src.core.config import get_settings
from src.db.models import Company


@pytest.fixture
def real_world_enabled(request):
    """Check if real-world tests are enabled."""
    if not request.config.getoption("--real-world"):
        pytest.skip("Real-world tests require --real-world flag")
    return True


# ============================================================================
# SEC EDGAR STANDALONE TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
async def test_sec_api_direct_connectivity(real_world_enabled):
    """Test SEC EDGAR API directly without pipeline code.

    Validates:
    - API endpoint accessibility
    - User-Agent header requirement
    - Response format
    - Data completeness

    Expected duration: ~2 seconds
    """
    settings = get_settings()

    headers = {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Fetch company info for Duolingo (known EdTech company)
        # CIK: 1562088
        response = await client.get(
            "https://data.sec.gov/submissions/CIK0001562088.json",
            headers=headers,
            follow_redirects=True
        )

        # Validate response
        assert response.status_code == 200, f"SEC API returned {response.status_code}"

        data = response.json()

        # Validate required fields
        assert "cik" in data, "Missing CIK in response"
        assert "name" in data, "Missing company name"
        assert "sic" in data, "Missing SIC code"
        assert "filings" in data, "Missing filings data"

        # Validate company data
        assert data["name"] == "Duolingo, Inc.", f"Unexpected name: {data.get('name')}"
        # CIK may have leading zeros
        assert data["cik"] in ["1562088", "0001562088"], f"Unexpected CIK: {data.get('cik')}"

        print(f"\n✓ SEC API test passed: {data['name']} (CIK: {data['cik']})")


@pytest.mark.real_world
@pytest.mark.asyncio
async def test_sec_filings_direct_fetch(real_world_enabled):
    """Test fetching SEC filings data directly.

    Validates:
    - Filings data structure
    - Filing metadata completeness
    - Date format consistency
    - Accession number format

    Expected duration: ~2 seconds
    """
    settings = get_settings()

    headers = {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://data.sec.gov/submissions/CIK0001835631.json",
            headers=headers,
            follow_redirects=True
        )

        data = response.json()
        filings = data.get("filings", {}).get("recent", {})

        # Validate filings structure
        assert "form" in filings, "Missing form types"
        assert "filingDate" in filings, "Missing filing dates"
        assert "accessionNumber" in filings, "Missing accession numbers"

        # Validate we have filings
        form_types = filings["form"]
        assert len(form_types) > 0, "No filings found"

        # Find any SEC filing (10-K, 10-Q, or other forms like D, S-1)
        filing_idx = None
        filing_form = None
        # Prefer periodic filings but accept any form
        for preferred_forms in [["10-K", "10-Q"], ["D", "S-1", "8-K"]]:
            for i, form in enumerate(form_types):
                if form in preferred_forms:
                    filing_idx = i
                    filing_form = form
                    break
            if filing_idx is not None:
                break

        # If still no filing found, just take the first one
        if filing_idx is None and len(form_types) > 0:
            filing_idx = 0
            filing_form = form_types[0]

        assert filing_idx is not None, f"No filings found at all"

        # Validate filing data quality
        filing_date_str = filings["filingDate"][filing_idx]
        accession = filings["accessionNumber"][filing_idx]

        # Date format validation (YYYY-MM-DD)
        filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
        assert filing_date <= datetime.now(), "Filing date is in the future"

        # Accession number format (NNNNNNNNNN-NN-NNNNNN)
        parts = accession.split("-")
        assert len(parts) == 3, f"Invalid accession format: {accession}"
        assert len(parts[0]) == 10 and parts[0].isdigit(), "Invalid accession prefix"
        assert len(parts[1]) == 2 and parts[1].isdigit(), "Invalid accession middle"
        assert len(parts[2]) == 6 and parts[2].isdigit(), "Invalid accession suffix"

        print(f"\n✓ Found {filing_form} filing: {accession} dated {filing_date_str}")


@pytest.mark.real_world
@pytest.mark.asyncio
async def test_sec_rate_limiting_compliance(real_world_enabled):
    """Test SEC API rate limiting compliance.

    SEC requires maximum 10 requests per second.
    This test makes multiple requests and ensures proper delays.

    Expected duration: ~2 seconds
    """
    settings = get_settings()

    headers = {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "application/json",
    }

    # Make 5 requests with rate limiting
    start_time = datetime.now()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(5):
            # CIK: 1562088 for Duolingo
            response = await client.get(
                "https://data.sec.gov/submissions/CIK0001562088.json",
                headers=headers,
                follow_redirects=True
            )
            assert response.status_code == 200

            # Wait 100ms between requests (10 req/sec = 100ms interval)
            if i < 4:
                await asyncio.sleep(0.1)

    elapsed = (datetime.now() - start_time).total_seconds()

    # Should take at least 400ms for 5 requests with 100ms delays
    assert elapsed >= 0.4, f"Rate limiting too fast: {elapsed}s"

    print(f"\n✓ Rate limiting compliant: 5 requests in {elapsed:.2f}s")


# ============================================================================
# YAHOO FINANCE STANDALONE TESTS
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
async def test_yahoo_finance_direct_connectivity(real_world_enabled):
    """Test Yahoo Finance API directly.

    Validates:
    - yfinance library functionality
    - Data retrieval for known ticker
    - Response format and completeness

    Expected duration: ~3 seconds
    """
    # Fetch data for Duolingo
    ticker = yf.Ticker("DUOL")
    info = ticker.info

    # Validate response
    assert info is not None, "Yahoo Finance returned no data"
    assert len(info) > 0, "Yahoo Finance returned empty data"

    # Validate key fields (field names may vary)
    has_symbol = "symbol" in info or "ticker" in info
    has_name = "longName" in info or "shortName" in info

    assert has_symbol, "Missing ticker/symbol in response"
    assert has_name, "Missing company name in response"

    company_name = info.get("longName") or info.get("shortName", "Unknown")

    print(f"\n✓ Yahoo Finance test passed: {company_name}")


@pytest.mark.real_world
@pytest.mark.asyncio
async def test_yahoo_quarterly_data_quality(real_world_enabled):
    """Test Yahoo Finance quarterly data quality.

    Validates:
    - Quarterly financial data availability
    - Revenue data presence
    - Data consistency

    Expected duration: ~3 seconds
    """
    ticker = yf.Ticker("DUOL")

    # Get quarterly income statement
    quarterly_income = ticker.quarterly_income_stmt

    # Validate data availability
    assert quarterly_income is not None, "No quarterly income data"
    assert not quarterly_income.empty, "Quarterly income data is empty"

    # Validate we have multiple quarters
    num_quarters = len(quarterly_income.columns)
    assert num_quarters >= 4, f"Expected at least 4 quarters, got {num_quarters}"

    # Check for revenue data (field name may vary)
    has_revenue = any(
        field in quarterly_income.index
        for field in ["Total Revenue", "Revenue", "TotalRevenue"]
    )

    assert has_revenue, f"No revenue field found. Available: {quarterly_income.index.tolist()}"

    print(f"\n✓ Yahoo Finance data quality: {num_quarters} quarters available")


# ============================================================================
# CROSS-SOURCE CONSISTENCY
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
async def test_company_data_consistency_across_sources(real_world_enabled):
    """Test that company data is consistent between SEC and Yahoo Finance.

    Validates:
    - Company names are similar
    - No major discrepancies
    - Both sources return data for same company

    Expected duration: ~5 seconds
    """
    settings = get_settings()
    ticker = "DUOL"

    # Fetch from SEC
    headers = {
        "User-Agent": settings.SEC_USER_AGENT,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # CIK: 1562088 for Duolingo
        response = await client.get(
            "https://data.sec.gov/submissions/CIK0001562088.json",
            headers=headers,
            follow_redirects=True
        )
        sec_data = response.json()

    # Fetch from Yahoo Finance
    yf_ticker = yf.Ticker(ticker)
    yf_info = yf_ticker.info

    # Compare company names
    sec_name = sec_data.get("name", "").lower()
    yf_name = (yf_info.get("longName") or yf_info.get("shortName", "")).lower()

    # Both should contain "duolingo"
    assert "duolingo" in sec_name, f"SEC name doesn't contain 'duolingo': {sec_name}"
    assert "duolingo" in yf_name, f"Yahoo name doesn't contain 'duolingo': {yf_name}"

    print(f"\n✓ Company data consistent:")
    print(f"  SEC: {sec_data.get('name')}")
    print(f"  Yahoo: {yf_info.get('longName') or yf_info.get('shortName')}")


# ============================================================================
# DATA QUALITY SUMMARY
# ============================================================================

@pytest.mark.real_world
@pytest.mark.asyncio
async def test_generate_quick_quality_report(real_world_enabled):
    """Generate a quick data quality report.

    Validates:
    - APIs are accessible
    - Data is being returned
    - Basic quality checks pass

    Expected duration: ~10 seconds
    """
    settings = get_settings()

    report = {
        "timestamp": datetime.now().isoformat(),
        "sources_tested": ["SEC EDGAR", "Yahoo Finance"],
        "results": {}
    }

    # Test SEC
    try:
        headers = {
            "User-Agent": settings.SEC_USER_AGENT,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # CIK: 1562088 for Duolingo
            response = await client.get(
                "https://data.sec.gov/submissions/CIK0001562088.json",
                headers=headers,
                follow_redirects=True
            )

            report["results"]["SEC EDGAR"] = {
                "status": "✓ Success" if response.status_code == 200 else "✗ Failed",
                "response_time": f"{response.elapsed.total_seconds():.2f}s",
                "data_quality": "✓ Valid" if response.json().get("cik") else "✗ Invalid"
            }
    except Exception as e:
        report["results"]["SEC EDGAR"] = {
            "status": "✗ Error",
            "error": str(e)
        }

    # Test Yahoo Finance
    try:
        ticker = yf.Ticker("DUOL")
        info = ticker.info

        report["results"]["Yahoo Finance"] = {
            "status": "✓ Success" if info else "✗ Failed",
            "data_quality": "✓ Valid" if len(info) > 0 else "✗ Invalid"
        }
    except Exception as e:
        report["results"]["Yahoo Finance"] = {
            "status": "✗ Error",
            "error": str(e)
        }

    # Print report
    print("\n" + "="*60)
    print("QUICK DATA QUALITY REPORT")
    print("="*60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"\nSources Tested: {', '.join(report['sources_tested'])}")
    print("\nResults:")
    for source, result in report["results"].items():
        print(f"\n  {source}:")
        for key, value in result.items():
            print(f"    {key}: {value}")
    print("="*60)

    # Validate at least one source is working
    successful_sources = sum(
        1 for result in report["results"].values()
        if result.get("status", "").startswith("✓")
    )

    assert successful_sources > 0, "No sources are accessible"

    return report
