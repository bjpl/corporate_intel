"""
Test script for Yahoo Finance ingestion pipeline.

This script validates the pipeline can fetch data without
actually writing to the database.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
import yfinance as yf

from src.pipeline.yahoo_finance_ingestion import EDTECH_COMPANIES


async def test_yahoo_finance_connectivity():
    """Test that we can fetch data from Yahoo Finance."""
    logger.info("Testing Yahoo Finance connectivity...")

    test_ticker = "CHGG"

    try:
        loop = asyncio.get_event_loop()
        stock = await loop.run_in_executor(None, yf.Ticker, test_ticker)
        info = await loop.run_in_executor(None, lambda: stock.info)

        if info and "regularMarketPrice" in info:
            logger.info(f"✓ Successfully fetched data for {test_ticker}")
            logger.info(f"  Company: {info.get('longName', 'N/A')}")
            logger.info(f"  Price: ${info.get('regularMarketPrice', 0):.2f}")
            logger.info(f"  Market Cap: ${info.get('marketCap', 0):,}")
            return True
        else:
            logger.error(f"✗ No data returned for {test_ticker}")
            return False

    except Exception as e:
        logger.error(f"✗ Error fetching data: {e}")
        return False


async def test_quarterly_financials():
    """Test fetching quarterly financial data."""
    logger.info("\nTesting quarterly financials retrieval...")

    test_ticker = "DUOL"

    try:
        loop = asyncio.get_event_loop()
        stock = await loop.run_in_executor(None, yf.Ticker, test_ticker)
        quarterly_income = await loop.run_in_executor(None, lambda: stock.quarterly_income_stmt)

        if quarterly_income is not None and not quarterly_income.empty:
            quarters = len(quarterly_income.columns)
            logger.info(f"✓ Successfully fetched {quarters} quarters of data for {test_ticker}")

            # Show available metrics
            logger.info(f"  Available metrics: {len(quarterly_income.index)}")
            logger.info(f"  Sample metrics: {list(quarterly_income.index[:5])}")

            # Check for key metrics
            if "Total Revenue" in quarterly_income.index:
                logger.info("  ✓ Total Revenue available")
            if "Gross Profit" in quarterly_income.index:
                logger.info("  ✓ Gross Profit available")
            if "Operating Income" in quarterly_income.index:
                logger.info("  ✓ Operating Income available")

            return True
        else:
            logger.error(f"✗ No quarterly data available for {test_ticker}")
            return False

    except Exception as e:
        logger.error(f"✗ Error fetching quarterly data: {e}")
        return False


async def test_all_companies():
    """Test data availability for all target companies."""
    logger.info(f"\nTesting data availability for all {len(EDTECH_COMPANIES)} companies...")

    results = []

    for idx, company_data in enumerate(EDTECH_COMPANIES, 1):
        ticker = company_data["ticker"]

        try:
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            info = await loop.run_in_executor(None, lambda: stock.info)

            if info and "regularMarketPrice" in info:
                logger.info(f"  ✓ [{idx:2d}/10] {ticker:6s} - {company_data['name']:40s} - OK")
                results.append((ticker, True, None))
            else:
                logger.warning(f"  ✗ [{idx:2d}/10] {ticker:6s} - {company_data['name']:40s} - No data")
                results.append((ticker, False, "No data available"))

        except Exception as e:
            logger.error(f"  ✗ [{idx:2d}/10] {ticker:6s} - {company_data['name']:40s} - Error: {e}")
            results.append((ticker, False, str(e)))

        # Small delay to be respectful to API
        await asyncio.sleep(0.5)

    # Summary
    successful = sum(1 for _, success, _ in results if success)
    logger.info(f"\nSummary: {successful}/{len(EDTECH_COMPANIES)} companies have data available")

    return successful == len(EDTECH_COMPANIES)


async def main():
    """Run all validation tests."""
    logger.info("=" * 80)
    logger.info("Yahoo Finance Ingestion Pipeline - Validation Tests")
    logger.info("=" * 80)

    all_passed = True

    # Test 1: Basic connectivity
    if not await test_yahoo_finance_connectivity():
        all_passed = False

    # Test 2: Quarterly financials
    if not await test_quarterly_financials():
        all_passed = False

    # Test 3: All companies
    if not await test_all_companies():
        all_passed = False

    # Final report
    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("✓ ALL TESTS PASSED - Pipeline is ready to run")
        logger.info("=" * 80)
        logger.info("\nTo run the ingestion pipeline:")
        logger.info("  python -m src.pipeline.yahoo_finance_ingestion")
        return 0
    else:
        logger.warning("✗ SOME TESTS FAILED - Review errors above")
        logger.info("=" * 80)
        return 1


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
