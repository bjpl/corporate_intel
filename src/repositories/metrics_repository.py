"""Metrics repository for financial metrics database operations.

This repository provides specialized methods for managing time-series financial
and operational metrics, including upsert operations, time-period queries, and
metric type filtering.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import FinancialMetric
from src.repositories.base_repository import BaseRepository, TransactionError


class MetricsRepository(BaseRepository[FinancialMetric]):
    """Repository for FinancialMetric model with time-series operations.

    Extends BaseRepository with metrics-specific queries including:
    - Upsert operations (insert or update)
    - Time-period filtering
    - Metric type queries
    - Aggregations and analytics

    Example:
        ```python
        async with get_db_session() as session:
            repo = MetricsRepository(session)

            # Upsert metric
            metric = await repo.upsert_metric(
                company_id=company_id,
                metric_type="revenue",
                metric_date=datetime(2024, 3, 31),
                period_type="quarterly",
                value=50000000.0,
                unit="USD"
            )

            # Get time-series data
            revenue_data = await repo.get_metrics_by_period(
                company_id,
                "revenue",
                quarters=8
            )
        ```
    """

    def __init__(self, session: AsyncSession):
        """Initialize metrics repository.

        Args:
            session: Async database session
        """
        super().__init__(FinancialMetric, session)

    async def upsert_metric(
        self,
        company_id: UUID,
        metric_type: str,
        metric_date: datetime,
        period_type: str,
        value: float,
        unit: Optional[str] = None,
        metric_category: Optional[str] = None,
        source: Optional[str] = None,
        source_document_id: Optional[UUID] = None,
        confidence_score: Optional[float] = None
    ) -> FinancialMetric:
        """Insert or update a financial metric (upsert).

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE to atomically
        insert or update based on the unique constraint
        (company_id, metric_type, metric_date, period_type).

        Args:
            company_id: Company UUID
            metric_type: Type of metric (revenue, mau, arpu, etc.)
            metric_date: Date of the metric (quarter-end, year-end, etc.)
            period_type: Period type (quarterly, annual, monthly)
            value: Metric value
            unit: Optional unit (USD, percent, count)
            metric_category: Optional category (financial, operational)
            source: Optional data source (sec_filing, api, manual)
            source_document_id: Optional source document UUID
            confidence_score: Optional confidence (0-1)

        Returns:
            FinancialMetric instance (newly created or updated)

        Example:
            ```python
            metric = await repo.upsert_metric(
                company_id=company.id,
                metric_type="revenue",
                metric_date=datetime(2024, 3, 31),
                period_type="quarterly",
                value=50000000.0,
                unit="USD",
                metric_category="financial",
                source="yahoo_finance"
            )
            ```
        """
        try:
            # Prepare insert values
            insert_values = {
                'company_id': company_id,
                'metric_type': metric_type,
                'metric_date': metric_date,
                'period_type': period_type,
                'value': value,
                'unit': unit,
                'metric_category': metric_category,
                'source': source,
                'source_document_id': source_document_id,
                'confidence_score': confidence_score,
                'created_at': func.now(),
                'updated_at': func.now(),
            }

            # Prepare update values (exclude keys used in ON CONFLICT)
            update_values = {
                'value': value,
                'unit': unit,
                'metric_category': metric_category,
                'source': source,
                'source_document_id': source_document_id,
                'confidence_score': confidence_score,
                'updated_at': func.now(),
            }

            # Remove None values
            insert_values = {k: v for k, v in insert_values.items() if v is not None}
            update_values = {k: v for k, v in update_values.items() if v is not None}

            # PostgreSQL upsert statement
            stmt = insert(FinancialMetric).values(**insert_values)

            # ON CONFLICT UPDATE (based on unique constraint)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_company_metric_period',
                set_=update_values
            )

            await self.session.execute(stmt)
            await self.session.flush()

            # Fetch the upserted record
            metric = await self.find_one_by(
                company_id=company_id,
                metric_type=metric_type,
                metric_date=metric_date,
                period_type=period_type
            )

            logger.debug(
                f"Upserted metric: {metric_type} for company {company_id} "
                f"at {metric_date} ({period_type})"
            )

            return metric

        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"Failed to upsert metric {metric_type} for company {company_id}: {e}"
            )
            raise TransactionError(f"Metric upsert failed: {str(e)}") from e

    async def get_metrics_by_period(
        self,
        company_id: UUID,
        metric_type: str,
        period_type: str = "quarterly",
        quarters: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[FinancialMetric]:
        """Get time-series metrics for a company.

        Args:
            company_id: Company UUID
            metric_type: Type of metric to fetch
            period_type: Period type (quarterly, annual, monthly)
            quarters: Optional number of recent quarters to fetch
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of FinancialMetric instances ordered by date (newest first)

        Example:
            ```python
            # Get last 8 quarters of revenue
            revenue = await repo.get_metrics_by_period(
                company_id,
                "revenue",
                quarters=8
            )

            # Get metrics in date range
            metrics = await repo.get_metrics_by_period(
                company_id,
                "mau",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2024, 12, 31)
            )
            ```
        """
        stmt = select(FinancialMetric).where(
            and_(
                FinancialMetric.company_id == company_id,
                FinancialMetric.metric_type == metric_type,
                FinancialMetric.period_type == period_type
            )
        )

        # Apply date filters
        if quarters:
            # Calculate cutoff date (quarters * ~90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=quarters * 90)
            stmt = stmt.where(FinancialMetric.metric_date >= cutoff_date)

        if start_date:
            stmt = stmt.where(FinancialMetric.metric_date >= start_date)

        if end_date:
            stmt = stmt.where(FinancialMetric.metric_date <= end_date)

        # Order by date descending (newest first)
        stmt = stmt.order_by(FinancialMetric.metric_date.desc())

        result = await self.session.execute(stmt)
        metrics = result.scalars().all()

        logger.debug(
            f"Fetched {len(metrics)} {metric_type} metrics for company {company_id}"
        )

        return list(metrics)

    async def get_latest_metric(
        self,
        company_id: UUID,
        metric_type: str,
        period_type: str = "quarterly"
    ) -> Optional[FinancialMetric]:
        """Get the most recent metric value for a company.

        Args:
            company_id: Company UUID
            metric_type: Type of metric
            period_type: Period type (quarterly, annual, monthly)

        Returns:
            Most recent FinancialMetric or None if not found

        Example:
            ```python
            latest_revenue = await repo.get_latest_metric(
                company_id,
                "revenue",
                "quarterly"
            )
            if latest_revenue:
                print(f"Latest revenue: ${latest_revenue.value:,.0f}")
            ```
        """
        stmt = select(FinancialMetric).where(
            and_(
                FinancialMetric.company_id == company_id,
                FinancialMetric.metric_type == metric_type,
                FinancialMetric.period_type == period_type
            )
        ).order_by(FinancialMetric.metric_date.desc()).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_metrics_for_company(
        self,
        company_id: UUID,
        limit: Optional[int] = None
    ) -> List[FinancialMetric]:
        """Get all metrics for a company.

        Args:
            company_id: Company UUID
            limit: Optional maximum number of results

        Returns:
            List of all FinancialMetric instances for the company

        Example:
            ```python
            all_metrics = await repo.get_all_metrics_for_company(company_id)
            ```
        """
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company_id
        ).order_by(FinancialMetric.metric_date.desc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        metrics = result.scalars().all()

        logger.debug(f"Fetched {len(metrics)} total metrics for company {company_id}")

        return list(metrics)

    async def get_metrics_by_category(
        self,
        company_id: UUID,
        metric_category: str,
        period_type: str = "quarterly",
        limit: Optional[int] = None
    ) -> List[FinancialMetric]:
        """Get metrics by category (financial, operational, edtech_specific).

        Args:
            company_id: Company UUID
            metric_category: Category filter
            period_type: Period type
            limit: Optional maximum number of results

        Returns:
            List of FinancialMetric instances matching category

        Example:
            ```python
            # Get all financial metrics
            financial = await repo.get_metrics_by_category(
                company_id,
                "financial",
                "quarterly"
            )
            ```
        """
        stmt = select(FinancialMetric).where(
            and_(
                FinancialMetric.company_id == company_id,
                FinancialMetric.metric_category == metric_category,
                FinancialMetric.period_type == period_type
            )
        ).order_by(FinancialMetric.metric_date.desc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        metrics = result.scalars().all()

        logger.debug(
            f"Fetched {len(metrics)} {metric_category} metrics for company {company_id}"
        )

        return list(metrics)

    async def delete_metrics_for_company(
        self,
        company_id: UUID,
        metric_type: Optional[str] = None
    ) -> int:
        """Delete metrics for a company.

        Args:
            company_id: Company UUID
            metric_type: Optional metric type filter (deletes all if None)

        Returns:
            Number of metrics deleted

        Example:
            ```python
            # Delete all revenue metrics
            count = await repo.delete_metrics_for_company(
                company_id,
                metric_type="revenue"
            )

            # Delete ALL metrics for company
            count = await repo.delete_metrics_for_company(company_id)
            ```
        """
        try:
            stmt = delete(FinancialMetric).where(
                FinancialMetric.company_id == company_id
            )

            if metric_type:
                stmt = stmt.where(FinancialMetric.metric_type == metric_type)

            result = await self.session.execute(stmt)
            await self.session.flush()

            deleted_count = result.rowcount

            logger.info(
                f"Deleted {deleted_count} metrics for company {company_id}"
                + (f" (type: {metric_type})" if metric_type else "")
            )

            return deleted_count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete metrics: {e}")
            raise TransactionError(f"Metric deletion failed: {str(e)}") from e

    async def bulk_upsert_metrics(
        self,
        metrics_data: List[Dict[str, Any]]
    ) -> int:
        """Bulk upsert multiple metrics.

        Args:
            metrics_data: List of metric dictionaries with required fields:
                - company_id
                - metric_type
                - metric_date
                - period_type
                - value
                Plus optional fields (unit, source, etc.)

        Returns:
            Number of metrics processed

        Example:
            ```python
            metrics = [
                {
                    "company_id": company_id,
                    "metric_type": "revenue",
                    "metric_date": datetime(2024, 3, 31),
                    "period_type": "quarterly",
                    "value": 50000000.0,
                    "unit": "USD"
                },
                # ... more metrics
            ]
            count = await repo.bulk_upsert_metrics(metrics)
            ```
        """
        try:
            for metric_data in metrics_data:
                # Prepare insert values
                insert_values = {
                    **metric_data,
                    'created_at': func.now(),
                    'updated_at': func.now(),
                }

                # Prepare update values
                update_values = {
                    k: v for k, v in metric_data.items()
                    if k not in ['company_id', 'metric_type', 'metric_date', 'period_type']
                }
                update_values['updated_at'] = func.now()

                # Upsert statement
                stmt = insert(FinancialMetric).values(**insert_values)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_company_metric_period',
                    set_=update_values
                )

                await self.session.execute(stmt)

            await self.session.flush()

            logger.info(f"Bulk upserted {len(metrics_data)} metrics")

            return len(metrics_data)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Bulk upsert failed: {e}")
            raise TransactionError(f"Bulk upsert failed: {str(e)}") from e

    async def calculate_growth_rate(
        self,
        company_id: UUID,
        metric_type: str,
        periods: int = 4
    ) -> Optional[float]:
        """Calculate growth rate (YoY or QoQ) for a metric.

        Args:
            company_id: Company UUID
            metric_type: Type of metric
            periods: Number of periods for growth (4 = YoY for quarterly)

        Returns:
            Growth rate as percentage or None if insufficient data

        Example:
            ```python
            # Calculate YoY revenue growth
            yoy_growth = await repo.calculate_growth_rate(
                company_id,
                "revenue",
                periods=4  # 4 quarters = 1 year
            )
            ```
        """
        metrics = await self.get_metrics_by_period(
            company_id,
            metric_type,
            quarters=periods + 1
        )

        if len(metrics) < periods + 1:
            logger.debug(f"Insufficient data to calculate growth rate")
            return None

        # Metrics are ordered newest first
        latest_value = metrics[0].value
        previous_value = metrics[periods].value

        if previous_value == 0:
            return None

        growth_rate = ((latest_value - previous_value) / previous_value) * 100

        logger.debug(
            f"Calculated {periods}-period growth rate: {growth_rate:.2f}%"
        )

        return growth_rate

    async def get_metric_statistics(
        self,
        company_id: UUID,
        metric_type: str,
        period_type: str = "quarterly"
    ) -> Dict[str, Any]:
        """Get statistical summary for a metric.

        Args:
            company_id: Company UUID
            metric_type: Type of metric
            period_type: Period type

        Returns:
            Dictionary with statistics:
            - count: Number of data points
            - min: Minimum value
            - max: Maximum value
            - avg: Average value
            - latest: Most recent value
            - oldest: Oldest value

        Example:
            ```python
            stats = await repo.get_metric_statistics(
                company_id,
                "revenue"
            )
            print(f"Avg revenue: ${stats['avg']:,.0f}")
            ```
        """
        metrics = await self.get_metrics_by_period(
            company_id,
            metric_type,
            period_type
        )

        if not metrics:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'latest': None,
                'oldest': None
            }

        values = [m.value for m in metrics]

        stats = {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': metrics[0].value,  # First (newest)
            'oldest': metrics[-1].value,  # Last (oldest)
        }

        logger.debug(f"Metric statistics for {metric_type}: {stats}")

        return stats
