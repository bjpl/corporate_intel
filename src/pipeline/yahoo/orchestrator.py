"""Yahoo Finance ingestion pipeline orchestration."""

import asyncio
import sys
from datetime import datetime
from typing import Any, Dict

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session_factory
from src.pipeline.common import notify_progress, run_coordination_hook
from src.pipeline.yahoo.constants import EDTECH_COMPANIES
from src.pipeline.yahoo.client import YahooFinanceClient
from src.pipeline.yahoo.processor import upsert_company, ingest_quarterly_financials


class YahooFinanceIngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


class YahooFinanceIngestionPipeline:
    """Pipeline for ingesting Yahoo Finance data into the database."""

    def __init__(self, session: AsyncSession):
        """Initialize the ingestion pipeline.

        Args:
            session: Async SQLAlchemy database session
        """
        self.session = session
        self.client = YahooFinanceClient()
        self.stats = {
            "companies_created": 0,
            "companies_updated": 0,
            "metrics_created": 0,
            "metrics_updated": 0,
            "errors": [],
        }

    async def run(self) -> Dict[str, Any]:
        """Execute the full ingestion pipeline.

        Returns:
            Dict containing ingestion statistics and results
        """
        logger.info("Starting Yahoo Finance data ingestion pipeline")
        logger.info(f"Target: {len(EDTECH_COMPANIES)} companies, 5 years quarterly data")

        for idx, company_data in enumerate(EDTECH_COMPANIES, 1):
            ticker = company_data["ticker"]

            try:
                logger.info(f"[{idx}/{len(EDTECH_COMPANIES)}] Processing {ticker} - {company_data['name']}")

                # Fetch data from Yahoo Finance
                yf_data = await self.client.fetch_stock_info(ticker)

                if not yf_data:
                    logger.warning(f"No data available for {ticker}")
                    self.stats["errors"].append({
                        "ticker": ticker,
                        "error": "No data available from Yahoo Finance"
                    })
                    continue

                # Upsert company record
                company = await upsert_company(self.session, company_data, yf_data)

                # Track if this was a new company
                result = await self.session.execute(
                    f"SELECT id FROM companies WHERE ticker = '{ticker}'"
                )
                is_new = result.scalar_one_or_none() is None

                if is_new:
                    self.stats["companies_created"] += 1
                else:
                    self.stats["companies_updated"] += 1

                # Fetch and insert quarterly financials
                metrics_count = await ingest_quarterly_financials(self.session, company, ticker)
                self.stats["metrics_created"] += metrics_count

                # Update progress via coordination hooks
                await notify_progress(f"Completed {idx}/{len(EDTECH_COMPANIES)} companies")

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                self.stats["errors"].append({
                    "ticker": ticker,
                    "error": str(e)
                })
                continue

        await self.session.commit()
        logger.info("Yahoo Finance ingestion pipeline completed")

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """Generate ingestion report.

        Returns:
            Dict containing statistics and summary
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed" if not self.stats["errors"] else "completed_with_errors",
            "statistics": {
                "companies_created": self.stats["companies_created"],
                "companies_updated": self.stats["companies_updated"],
                "total_companies": self.stats["companies_created"] + self.stats["companies_updated"],
                "metrics_created": self.stats["metrics_created"],
                "metrics_updated": self.stats["metrics_updated"],
                "total_metrics": self.stats["metrics_created"] + self.stats["metrics_updated"],
                "errors_count": len(self.stats["errors"]),
            },
            "errors": self.stats["errors"],
        }

        return report


async def run_ingestion() -> Dict[str, Any]:
    """Main entry point for Yahoo Finance data ingestion.

    Returns:
        Dict containing ingestion results and statistics
    """
    logger.info("=" * 80)
    logger.info("Yahoo Finance Data Ingestion Pipeline")
    logger.info("=" * 80)

    # Create database session
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            # Initialize and run pipeline
            pipeline = YahooFinanceIngestionPipeline(session)
            report = await pipeline.run()

            # Log summary
            logger.info("=" * 80)
            logger.info("INGESTION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Companies Created: {report['statistics']['companies_created']}")
            logger.info(f"Companies Updated: {report['statistics']['companies_updated']}")
            logger.info(f"Metrics Created: {report['statistics']['metrics_created']}")
            logger.info(f"Metrics Updated: {report['statistics']['metrics_updated']}")
            logger.info(f"Total Errors: {report['statistics']['errors_count']}")

            if report["errors"]:
                logger.warning("\nErrors encountered:")
                for error in report["errors"]:
                    logger.warning(f"  - {error['ticker']}: {error['error']}")

            logger.info("=" * 80)

            # Run post-task hook
            await run_coordination_hook("post-task", task_id="yahoo-ingestion")

            return report

        except Exception as e:
            logger.error(f"Fatal error in ingestion pipeline: {e}")
            await session.rollback()
            raise


def main():
    """Run the ingestion pipeline when executed as a script."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run the async ingestion pipeline
    result = asyncio.run(run_ingestion())

    # Exit with appropriate code
    if result["statistics"]["errors_count"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
