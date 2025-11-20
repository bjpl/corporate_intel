"""Yahoo Finance data processing and database operations."""

from typing import Any, Dict
from uuid import UUID

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company
from src.pipeline.common import get_or_create_company, upsert_financial_metric
from src.pipeline.yahoo.client import YahooFinanceClient
from src.pipeline.yahoo.parser import extract_financial_metrics, parse_company_data


async def upsert_company(
    session: AsyncSession,
    company_data: Dict[str, Any],
    yf_data: Dict[str, Any]
) -> Company:
    """Insert or update company record.

    Args:
        session: Database session
        company_data: Company metadata from EDTECH_COMPANIES
        yf_data: Yahoo Finance data

    Returns:
        Company model instance
    """
    ticker = company_data["ticker"]

    # Check if company exists
    result = await session.execute(
        select(Company).where(Company.ticker == ticker)
    )
    existing_company = result.scalar_one_or_none()

    if existing_company:
        # Update existing company with new data
        existing_company.name = company_data["name"]
        existing_company.sector = company_data["sector"]
        existing_company.category = company_data["category"]
        existing_company.subcategory = company_data["subcategory"]
        existing_company.website = yf_data.get("website", "")
        existing_company.employee_count = yf_data.get("fullTimeEmployees", 0)
        existing_company.headquarters = f"{yf_data.get('city', '')}, {yf_data.get('country', '')}".strip(", ")

        logger.info(f"Updated company: {ticker}")
        return existing_company
    else:
        # Use common utility for company creation
        parsed_data = parse_company_data(company_data, yf_data)
        company = await get_or_create_company(
            session,
            **parsed_data
        )

        logger.info(f"Created company: {ticker}")
        return company


async def ingest_quarterly_financials(
    session: AsyncSession,
    company: Company,
    ticker: str
) -> int:
    """Fetch and ingest quarterly financial data.

    Protected by circuit breaker to prevent cascading failures.

    Args:
        session: Database session
        company: Company model instance
        ticker: Stock ticker symbol

    Returns:
        Number of metrics created
    """
    metrics_created = 0

    try:
        client = YahooFinanceClient()

        # Get quarterly income statement
        quarterly_income_data = await client.fetch_quarterly_financials(ticker)
        if quarterly_income_data is None or quarterly_income_data.empty:
            logger.warning(f"No quarterly financials available for {ticker}")
            return 0

        # Get quarterly balance sheet
        quarterly_balance_data = await client.fetch_quarterly_balance_sheet(ticker)

        # Get additional info
        info_data = await client.fetch_stock_info(ticker)
        if not info_data:
            info_data = {}

        # Process each quarter (up to 20 quarters = 5 years)
        quarters_to_process = min(20, len(quarterly_income_data.columns))

        for i in range(quarters_to_process):
            quarter_date = quarterly_income_data.columns[i]

            # Extract metrics for this quarter
            metrics_to_insert = extract_financial_metrics(
                quarterly_income_data,
                quarterly_balance_data if quarterly_balance_data is not None else pd.DataFrame(),
                info_data,
                quarter_date
            )

            # Insert all metrics for this quarter using common utility
            for metric_data in metrics_to_insert:
                await upsert_financial_metric(
                    session,
                    company_id=company.id,
                    metric_date=quarter_date,
                    period_type="quarterly",
                    source="yahoo_finance",
                    confidence_score=0.95,
                    **metric_data
                )
                metrics_created += 1

        logger.info(f"Ingested {quarters_to_process} quarters of financial data for {ticker}")
        return metrics_created

    except Exception as e:
        logger.error(f"Error ingesting quarterly financials for {ticker}: {e}")
        raise
