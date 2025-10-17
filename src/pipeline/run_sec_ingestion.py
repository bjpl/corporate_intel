"""SEC Filings Ingestion Orchestrator for All 28 EdTech Companies.

This script orchestrates the batch ingestion of SEC filings using the existing
SEC pipeline. It fetches 10-K and 10-Q filings from the past 5 years for all
28 EdTech companies in the watchlist.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

from loguru import logger

from src.pipeline.sec_ingestion import batch_sec_ingestion_flow, FilingRequest
from src.pipeline.common import run_coordination_hook


# Top 10 EdTech companies
EDTECH_TICKERS = [
    'CHGG',  # Chegg
    'COUR',  # Coursera
    'DUOL',  # Duolingo
    'ARCE',  # Arco Platform
    'LRN',   # Stride (K12)
    'UDMY',  # Udemy
    'PSO',   # Pearson
    'ATGE',  # Adtalem Global Education
    'LOPE',  # Grand Canyon Education
    'STRA',  # Strategic Education
]


async def run_sec_ingestion_with_progress(tickers: List[str]) -> Dict[str, Any]:
    """Run SEC ingestion with progress tracking for each company.

    Args:
        tickers: List of company ticker symbols

    Returns:
        Dict containing summary statistics
    """
    logger.info(f"Starting SEC filings ingestion for {len(tickers)} EdTech companies")
    logger.info(f"Target filings: 10-K, 10-Q from past 5 years")
    logger.info("-" * 80)

    # Create filing requests for past 5 years
    requests = [
        FilingRequest(
            company_ticker=ticker,
            filing_types=["10-K", "10-Q"],
            start_date=datetime.now() - timedelta(days=1825)  # 5 years
        )
        for ticker in tickers
    ]

    results = []
    failed_companies = []

    # Process each company sequentially with progress tracking
    for idx, request in enumerate(requests, 1):
        ticker = request.company_ticker

        try:
            logger.info(f"[{idx}/{len(tickers)}] Processing {ticker}...")

            # Import and run the existing flow
            from src.pipeline.sec_ingestion import sec_ingestion_flow

            result = await sec_ingestion_flow(request)

            if result:
                results.append(result)
                logger.info(
                    f"[{idx}/{len(tickers)}] {ticker}: "
                    f"Found {result.get('filings_found', 0)} filings, "
                    f"Stored {result.get('filings_stored', 0)} filings"
                )
            else:
                logger.warning(f"[{idx}/{len(tickers)}] {ticker}: No results returned")
                failed_companies.append(ticker)

        except Exception as e:
            logger.error(
                f"[{idx}/{len(tickers)}] {ticker}: Error - {str(e)}"
            )
            failed_companies.append(ticker)
            continue

    # Calculate summary statistics
    total_found = sum(r.get("filings_found", 0) for r in results if r)
    total_stored = sum(r.get("filings_stored", 0) for r in results if r)
    successful_companies = len(results)

    logger.info("-" * 80)
    logger.info("SEC FILINGS INGESTION SUMMARY")
    logger.info("-" * 80)
    logger.info(f"Total companies processed: {len(tickers)}")
    logger.info(f"Successful: {successful_companies}")
    logger.info(f"Failed: {len(failed_companies)}")
    if failed_companies:
        logger.info(f"Failed companies: {', '.join(failed_companies)}")
    logger.info(f"Total filings found: {total_found}")
    logger.info(f"Total filings stored: {total_stored}")
    logger.info("-" * 80)

    return {
        "total_companies": len(tickers),
        "successful_companies": successful_companies,
        "failed_companies": failed_companies,
        "total_filings_found": total_found,
        "total_filings_stored": total_stored,
        "results": results,
    }


async def main():
    """Main entry point for SEC ingestion orchestrator."""

    # Run hooks: pre-task
    logger.info("Running pre-task hook...")
    await run_coordination_hook("pre-task", description="SEC filings ingestion for 10 EdTech companies")

    # Run the ingestion
    try:
        summary = await run_sec_ingestion_with_progress(EDTECH_TICKERS)

        # Run hooks: post-task notification
        logger.info("Running post-task hook...")
        await run_coordination_hook("post-task", task_id="sec-ingestion")

        return summary

    except Exception as e:
        logger.error(f"SEC ingestion failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run the orchestrator
    asyncio.run(main())
