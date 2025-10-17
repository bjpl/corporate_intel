"""Shared utility functions for data ingestion pipelines.

This module provides reusable functions for common pipeline operations:
- Company record management (get or create)
- Financial metric upsert with conflict resolution
- Retry logic with exponential backoff
- Coordination hook execution and progress notifications

Usage:
    from src.pipeline.common import (
        get_or_create_company,
        upsert_financial_metric,
        retry_with_backoff,
    )
"""

import asyncio
import functools
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from uuid import UUID

import pandas as pd
import pytz
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company, FinancialMetric


# Type variables for generic retry decorator
T = TypeVar('T')


async def get_or_create_company(
    session: AsyncSession,
    ticker: str,
    name: Optional[str] = None,
    sector: str = "Education Technology",
    category: str = "EdTech",
    **extra_fields
) -> Optional[Company]:
    """Get existing company or create a new one.

    This function handles the common pattern of checking if a company exists
    and creating it if not. Used across all ingestion pipelines.

    Args:
        session: Database session
        ticker: Company ticker symbol (will be uppercased)
        name: Company name (auto-generated if not provided)
        sector: Business sector (default: Education Technology)
        category: Company category (default: EdTech)
        **extra_fields: Additional fields (website, employee_count, headquarters, subcategory)

    Returns:
        Company instance or None if creation fails

    Example:
        company = await get_or_create_company(
            session,
            ticker="CHGG",
            name="Chegg Inc.",
            website="https://www.chegg.com",
            employee_count=3000
        )
    """
    ticker_upper = ticker.upper()

    # Try to find existing company
    result = await session.execute(
        select(Company).where(Company.ticker == ticker_upper)
    )
    company = result.scalar_one_or_none()

    if company:
        logger.debug(f"Found existing company: {ticker_upper} (ID: {company.id})")
        return company

    # Create new company
    logger.info(f"Creating new company record for {ticker_upper}")

    company_data = {
        "ticker": ticker_upper,
        "name": name or f"{ticker_upper} (Auto-created)",
        "sector": sector,
        "category": category,
    }

    # Add extra fields if provided
    for field in ["website", "employee_count", "headquarters", "subcategory"]:
        if field in extra_fields:
            company_data[field] = extra_fields[field]

    company = Company(**company_data)
    session.add(company)
    await session.flush()  # Get the ID without committing

    logger.info(f"Created company: {ticker_upper} (ID: {company.id})")
    return company


async def upsert_financial_metric(
    session: AsyncSession,
    company_id: Union[UUID, str],
    metric_date: Union[datetime, pd.Timestamp],
    period_type: str,
    metric_type: str,
    value: float,
    unit: str,
    metric_category: str,
    source: str = "manual",
    confidence_score: float = 0.95,
) -> None:
    """Insert or update a financial metric with conflict resolution.

    Uses PostgreSQL's INSERT ... ON CONFLICT DO UPDATE for atomic upserts.
    Handles timezone-aware datetime conversion automatically.

    Args:
        session: Database session
        company_id: Company UUID or string representation
        metric_date: Date of the metric (naive datetimes converted to UTC)
        period_type: Type of period (quarterly, annual, monthly)
        metric_type: Type of metric (revenue, margin, etc.)
        value: Metric value
        unit: Unit of measurement (USD, percent, ratio)
        metric_category: Category (financial, operational, valuation, etc.)
        source: Data source (yahoo_finance, alpha_vantage, sec_edgar)
        confidence_score: Confidence in the data quality (0.0-1.0)

    Example:
        await upsert_financial_metric(
            session,
            company_id=company.id,
            metric_date=datetime(2024, 3, 31),
            period_type="quarterly",
            metric_type="revenue",
            value=150000000.0,
            unit="USD",
            metric_category="financial",
            source="yahoo_finance"
        )
    """
    # Convert company_id to UUID if string
    if isinstance(company_id, str):
        from uuid import UUID as UUIDType
        company_id = UUIDType(company_id)

    # Ensure metric_date is timezone-aware (PostgreSQL requirement)
    if isinstance(metric_date, pd.Timestamp):
        # Convert pandas Timestamp to timezone-aware datetime
        if metric_date.tzinfo is None:
            metric_date = metric_date.tz_localize('UTC').to_pydatetime()
        else:
            metric_date = metric_date.to_pydatetime()
    elif isinstance(metric_date, datetime):
        # Convert naive datetime to timezone-aware
        if metric_date.tzinfo is None:
            metric_date = metric_date.replace(tzinfo=pytz.UTC)

    # Create insert statement with ON CONFLICT DO UPDATE
    stmt = insert(FinancialMetric).values(
        company_id=company_id,
        metric_date=metric_date,
        period_type=period_type,
        metric_type=metric_type,
        metric_category=metric_category,
        value=value,
        unit=unit,
        source=source,
        confidence_score=confidence_score,
    )

    # On conflict, update the value and metadata
    stmt = stmt.on_conflict_do_update(
        index_elements=["company_id", "metric_type", "metric_date", "period_type"],
        set_={
            "value": stmt.excluded.value,
            "unit": stmt.excluded.unit,
            "source": stmt.excluded.source,
            "confidence_score": stmt.excluded.confidence_score,
            "updated_at": datetime.utcnow(),
        }
    )

    await session.execute(stmt)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exponential: bool = True,
    retry_on: tuple = (Exception,),
    no_retry_on: tuple = (ValueError,),
):
    """Decorator for retrying async functions with exponential backoff.

    Implements robust retry logic for transient failures:
    - Configurable retry count and delay
    - Exponential or linear backoff
    - Selective exception handling
    - Logging of retry attempts

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds (default: 2.0)
        max_delay: Maximum delay cap (default: 60.0)
        exponential: Use exponential backoff (default: True)
        retry_on: Tuple of exceptions to retry on (default: all)
        no_retry_on: Tuple of exceptions to never retry (default: ValueError)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, base_delay=4.0)
        async def fetch_data(ticker: str):
            return await api.get(ticker)

        # Will retry network errors but not validation errors
        @retry_with_backoff(
            max_retries=5,
            retry_on=(aiohttp.ClientError, asyncio.TimeoutError),
            no_retry_on=(ValueError,)
        )
        async def risky_operation():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)

                except no_retry_on as e:
                    # Don't retry these exceptions
                    logger.error(f"{func.__name__}: Non-retryable error - {str(e)}")
                    raise

                except retry_on as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # Calculate delay
                        if exponential:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                        else:
                            delay = min(base_delay * (attempt + 1), max_delay)

                        logger.warning(
                            f"{func.__name__}: Attempt {attempt + 1}/{max_retries} failed - {str(e)}, "
                            f"retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__}: Failed after {max_retries} attempts - {str(e)}"
                        )
                        raise

                except Exception as e:
                    # Unexpected exception type
                    logger.error(f"{func.__name__}: Unexpected error - {str(e)}", exc_info=True)
                    raise

            # This should never be reached, but satisfy type checker
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


async def run_coordination_hook(
    hook_type: str,
    timeout: float = 10.0,
    **hook_params: str
) -> bool:
    """Execute coordination hook with error handling.

    Runs claude-flow hooks for coordination without failing the pipeline
    if hooks are unavailable.

    Args:
        hook_type: Hook type (pre-task, post-task, post-edit, notify)
        timeout: Command timeout in seconds (default: 10.0)
        **hook_params: Hook parameters (description, task-id, message, file, memory-key)

    Returns:
        True if hook succeeded, False otherwise

    Example:
        # Pre-task hook
        await run_coordination_hook(
            "pre-task",
            description="Ingesting financial data"
        )

        # Post-edit hook
        await run_coordination_hook(
            "post-edit",
            file="src/pipeline/ingestion.py",
            memory_key="swarm/coder/ingestion"
        )
    """
    try:
        cmd = ["npx", "claude-flow@alpha", "hooks", hook_type]

        # Add parameters
        for key, value in hook_params.items():
            param_name = f"--{key.replace('_', '-')}"
            cmd.extend([param_name, value])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            if process.returncode == 0:
                logger.debug(f"Coordination hook '{hook_type}' succeeded")
                return True
            else:
                logger.debug(
                    f"Coordination hook '{hook_type}' failed: {stderr.decode()}"
                )
                return False

        except asyncio.TimeoutError:
            process.kill()
            logger.debug(f"Coordination hook '{hook_type}' timed out")
            return False

    except Exception as e:
        logger.debug(f"Could not run coordination hook '{hook_type}': {e}")
        return False


async def notify_progress(message: str) -> None:
    """Send progress notification via coordination hooks.

    Convenience wrapper around run_coordination_hook for notifications.
    Never fails the calling pipeline if notification fails.

    Args:
        message: Progress message to send

    Example:
        await notify_progress("Processed 10/27 companies")
    """
    await run_coordination_hook("notify", message=message)
