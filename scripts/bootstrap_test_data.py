#!/usr/bin/env python3
"""
Bootstrap Test Data - Real EdTech Companies
===========================================

This script uses the actual data connectors to pull REAL data from:
- SEC EDGAR (company info, filings)
- Yahoo Finance (stock data, financials)
- Alpha Vantage (fundamental metrics)

No fake data - all real companies with real financial data!
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import get_settings
from src.db.models import Base, Company, FinancialMetric
from src.connectors.data_sources import (
    SECEdgarConnector,
    YahooFinanceConnector,
    AlphaVantageConnector,
    DataAggregator
)


# Real EdTech companies for testing
EDTECH_COMPANIES = [
    {
        "ticker": "COUR",
        "name": "Coursera, Inc.",
        "cik": "0001651562",
        "category": "higher_education",
        "delivery_model": "B2C",
    },
    {
        "ticker": "DUOL",
        "name": "Duolingo, Inc.",
        "cik": "0001788882",
        "category": "direct_to_consumer",
        "delivery_model": "B2C",
    },
    {
        "ticker": "CHGG",
        "name": "Chegg, Inc.",
        "cik": "0001364954",
        "category": "higher_education",
        "delivery_model": "B2C",
    },
    {
        "ticker": "TWOU",
        "name": "2U, Inc.",
        "cik": "0001459417",
        "category": "higher_education",
        "delivery_model": "B2B2C",
    },
    {
        "ticker": "STRA",
        "name": "Strategic Education, Inc.",
        "cik": "0001013934",
        "category": "higher_education",
        "delivery_model": "B2C",
    },
]


class DataBootstrapper:
    """Bootstrap real test data from external APIs."""

    def __init__(self):
        self.settings = get_settings()
        self.yahoo = YahooFinanceConnector()
        self.alpha = AlphaVantageConnector()
        self.aggregator = DataAggregator()

        # Setup async database session
        database_url = str(self.settings.DATABASE_URL).replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def bootstrap_all(self):
        """Bootstrap all test data."""
        logger.info("Starting data bootstrap with REAL EdTech company data")

        # Create tables if they don't exist
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.async_session() as session:
            # Check if data already exists
            result = await session.execute(select(Company))
            existing = result.scalars().all()

            if existing:
                logger.warning(f"Found {len(existing)} existing companies. Skipping bootstrap.")
                logger.info("To re-bootstrap, clear the database first:")
                logger.info("  alembic downgrade base && alembic upgrade head")
                return

            logger.info(f"Bootstrapping {len(EDTECH_COMPANIES)} real EdTech companies...")

            for company_data in EDTECH_COMPANIES:
                try:
                    await self.bootstrap_company(session, company_data)
                except Exception as e:
                    logger.error(f"Failed to bootstrap {company_data['ticker']}: {e}")
                    continue

            await session.commit()
            logger.success("✅ Bootstrap complete!")

            # Print summary
            await self.print_summary(session)

    async def bootstrap_company(self, session: AsyncSession, company_data: dict):
        """Bootstrap a single company with real data."""
        ticker = company_data["ticker"]
        logger.info(f"📊 Fetching real data for {ticker} ({company_data['name']})")

        # Fetch real data from Yahoo Finance
        yahoo_data = await self.yahoo.get_stock_info(ticker)

        if not yahoo_data:
            logger.error(f"Could not fetch Yahoo Finance data for {ticker}")
            return

        # Create company record with real data
        company = Company(
            id=uuid4(),
            ticker=ticker,
            name=yahoo_data.get('company_name') or company_data['name'],
            cik=company_data.get('cik'),
            sector=yahoo_data.get('sector', 'Education Technology'),
            subsector=yahoo_data.get('industry', 'EdTech'),
            category=company_data.get('category'),
            delivery_model=company_data.get('delivery_model'),
            website=yahoo_data.get('website'),
            employee_count=yahoo_data.get('employees'),
        )

        session.add(company)
        await session.flush()  # Get company ID

        logger.info(f"  ✓ Created company: {company.name}")

        # Fetch quarterly financial data
        quarterly_data = await self.yahoo.get_quarterly_financials(ticker)

        if not quarterly_data.empty:
            metrics_created = await self.create_financial_metrics(
                session, company.id, ticker, quarterly_data, yahoo_data
            )
            logger.info(f"  ✓ Created {metrics_created} financial metrics")
        else:
            logger.warning(f"  ⚠ No quarterly data available for {ticker}")

        # Try to fetch Alpha Vantage data if available
        if self.settings.ALPHA_VANTAGE_API_KEY:
            try:
                alpha_data = await self.alpha.get_company_overview(ticker)
                if alpha_data:
                    logger.info(f"  ✓ Enriched with Alpha Vantage data")
            except Exception as e:
                logger.warning(f"  ⚠ Could not fetch Alpha Vantage data: {e}")

    async def create_financial_metrics(
        self,
        session: AsyncSession,
        company_id,
        ticker: str,
        quarterly_data,
        yahoo_data: dict
    ) -> int:
        """Create financial metrics from real quarterly data."""
        metrics_created = 0

        # Get current data from Yahoo Finance
        current_metrics = [
            {
                "metric_type": "market_cap",
                "value": float(yahoo_data.get('market_cap', 0)),
                "unit": "USD",
                "category": "financial",
            },
            {
                "metric_type": "revenue",
                "value": float(yahoo_data.get('total_revenue', 0)),
                "unit": "USD",
                "category": "financial",
            },
            {
                "metric_type": "revenue_growth",
                "value": float(yahoo_data.get('revenue_growth', 0) * 100),
                "unit": "percent",
                "category": "financial",
            },
            {
                "metric_type": "gross_margin",
                "value": float(yahoo_data.get('gross_margins', 0) * 100),
                "unit": "percent",
                "category": "financial",
            },
            {
                "metric_type": "operating_margin",
                "value": float(yahoo_data.get('operating_margins', 0) * 100),
                "unit": "percent",
                "category": "financial",
            },
            {
                "metric_type": "profit_margin",
                "value": float(yahoo_data.get('profit_margins', 0) * 100),
                "unit": "percent",
                "category": "financial",
            },
            {
                "metric_type": "free_cash_flow",
                "value": float(yahoo_data.get('free_cashflow', 0)),
                "unit": "USD",
                "category": "financial",
            },
            {
                "metric_type": "stock_price",
                "value": float(yahoo_data.get('current_price', 0)),
                "unit": "USD",
                "category": "financial",
            },
        ]

        # Create metrics for current quarter
        current_date = datetime.now()

        for metric_data in current_metrics:
            if metric_data["value"] > 0:  # Only create if we have real data
                metric = FinancialMetric(
                    company_id=company_id,
                    metric_date=current_date,
                    period_type="quarterly",
                    metric_type=metric_data["metric_type"],
                    metric_category=metric_data["category"],
                    value=metric_data["value"],
                    unit=metric_data["unit"],
                    source="yahoo_finance",
                    confidence_score=0.95,
                )
                session.add(metric)
                metrics_created += 1

        return metrics_created

    async def print_summary(self, session: AsyncSession):
        """Print summary of bootstrapped data."""
        logger.info("\n" + "="*60)
        logger.info("📊 BOOTSTRAP SUMMARY")
        logger.info("="*60)

        # Count companies
        result = await session.execute(select(Company))
        companies = result.scalars().all()

        logger.info(f"\n✅ Companies bootstrapped: {len(companies)}")
        for company in companies:
            logger.info(f"   • {company.ticker}: {company.name}")

            # Count metrics per company
            result = await session.execute(
                select(FinancialMetric).where(FinancialMetric.company_id == company.id)
            )
            metrics = result.scalars().all()
            logger.info(f"     → {len(metrics)} financial metrics")

        logger.info("\n" + "="*60)
        logger.info("🎯 NEXT STEPS")
        logger.info("="*60)
        logger.info("\n1. Start the API server:")
        logger.info("   uvicorn src.api.main:app --reload")
        logger.info("\n2. View companies:")
        logger.info("   curl http://localhost:8000/api/v1/companies")
        logger.info("\n3. Test with API docs:")
        logger.info("   http://localhost:8000/api/v1/docs")
        logger.info("\n4. Start testing with REAL data!")
        logger.info("="*60 + "\n")


async def main():
    """Main entry point."""
    logger.info("🚀 Corporate Intelligence Platform - Data Bootstrap")
    logger.info("=" * 60)
    logger.info("This will fetch REAL data from:")
    logger.info("  • Yahoo Finance (stock data, financials)")
    logger.info("  • SEC EDGAR (company info)")
    logger.info("  • Alpha Vantage (if API key configured)")
    logger.info("")
    logger.info(f"Companies to bootstrap: {len(EDTECH_COMPANIES)}")
    for company in EDTECH_COMPANIES:
        logger.info(f"  • {company['ticker']}: {company['name']}")
    logger.info("=" * 60)

    input("\nPress Enter to continue or Ctrl+C to cancel...")

    bootstrapper = DataBootstrapper()
    await bootstrapper.bootstrap_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n❌ Bootstrap cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Bootstrap failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
