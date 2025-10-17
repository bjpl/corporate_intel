"""Common utilities for data ingestion pipelines.

This module provides shared functions used across multiple ingestion pipelines
to reduce code duplication and ensure consistency in database operations.
"""

import asyncio
import subprocess
from datetime import datetime
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company
from src.repositories import CompanyRepository, MetricsRepository


async def get_or_create_company(
    session: AsyncSession,
    ticker: str,
    defaults: Optional[dict] = None
) -> Optional[Company]:
    """Get existing company or create a new one using CompanyRepository.

    Args:
        session: Database session
        ticker: Company ticker symbol
        defaults: Optional default values for creation

    Returns:
        Company instance or None if creation fails
    """
    try:
        repo = CompanyRepository(session)
        company, created = await repo.get_or_create_by_ticker(ticker, defaults=defaults)

        if created:
            logger.info(f"Created new company record for {ticker}")
        else:
            logger.debug(f"Found existing company: {ticker} (ID: {company.id})")

        return company

    except Exception as e:
        logger.error(f"Failed to get/create company {ticker}: {e}")
        return None


async def upsert_financial_metric(
    session: AsyncSession,
    company_id: UUID,
    metric_date: datetime,
    period_type: str,
    metric_type: str,
    value: float,
    unit: Optional[str] = None,
    metric_category: Optional[str] = None,
    source: Optional[str] = None,
    confidence_score: Optional[float] = None
) -> bool:
    """Upsert a financial metric using MetricsRepository.

    Args:
        session: Database session
        company_id: Company UUID
        metric_date: Date of the metric
        period_type: Period type (quarterly, annual, monthly)
        metric_type: Type of metric
        value: Metric value
        unit: Optional unit
        metric_category: Optional category
        source: Optional data source
        confidence_score: Optional confidence score

    Returns:
        True if successful, False otherwise
    """
    try:
        repo = MetricsRepository(session)

        await repo.upsert_metric(
            company_id=company_id,
            metric_type=metric_type,
            metric_date=metric_date,
            period_type=period_type,
            value=value,
            unit=unit,
            metric_category=metric_category,
            source=source,
            confidence_score=confidence_score
        )

        logger.debug(
            f"Upserted metric: {metric_type} for company {company_id} "
            f"at {metric_date} ({period_type})"
        )

        return True

    except Exception as e:
        logger.error(
            f"Failed to upsert metric {metric_type} for company {company_id}: {e}"
        )
        return False


async def run_coordination_hook(
    hook_type: str,
    description: Optional[str] = None,
    task_id: Optional[str] = None,
    file_path: Optional[str] = None,
    memory_key: Optional[str] = None,
    message: Optional[str] = None,
    timeout: int = 5
) -> bool:
    """Run a coordination hook (pre-task, post-task, notify, etc.).

    Args:
        hook_type: Type of hook (pre-task, post-task, notify, post-edit)
        description: Optional task description (for pre-task)
        task_id: Optional task ID (for post-task)
        file_path: Optional file path (for post-edit)
        memory_key: Optional memory key (for post-edit)
        message: Optional message (for notify)
        timeout: Command timeout in seconds

    Returns:
        True if hook succeeded, False otherwise
    """
    try:
        cmd = ["npx", "claude-flow@alpha", "hooks", hook_type]

        if description:
            cmd.extend(["--description", description])
        if task_id:
            cmd.extend(["--task-id", task_id])
        if file_path:
            cmd.extend(["--file", file_path])
        if memory_key:
            cmd.extend(["--memory-key", memory_key])
        if message:
            cmd.extend(["--message", message])

        # Run in background with timeout
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            await asyncio.wait_for(result.wait(), timeout=timeout)
            return result.returncode == 0
        except asyncio.TimeoutError:
            result.kill()
            logger.warning(f"Coordination hook {hook_type} timed out after {timeout}s")
            return False

    except Exception as e:
        logger.debug(f"Coordination hook {hook_type} failed: {e}")
        return False
