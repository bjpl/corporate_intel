"""Dashboard service layer for querying dbt marts and providing data to visualizations.

This service provides a clean interface between the dashboard and the database,
querying dbt-transformed mart tables and returning data in formats expected by the
dashboard components. All queries are cached using Redis for performance.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache_manager import get_cache
from src.db.models import Company, FinancialMetric
from src.repositories import CompanyRepository, MetricsRepository


class DashboardService:
    """Service for dashboard data queries with caching and error handling.

    This service queries dbt mart tables (mart_company_performance and
    mart_competitive_landscape) and provides data in formats suitable for
    dashboard visualizations. All queries include Redis caching with
    configurable TTL.

    Attributes:
        session: Async database session for queries
        cache_ttl: Default cache TTL in seconds (default: 300 = 5 minutes)

    Example:
        ```python
        async with get_db() as session:
            service = DashboardService(session)
            companies = await service.get_company_performance(category="k12")
        ```
    """

    def __init__(self, session: AsyncSession, cache_ttl: int = 300):
        """Initialize dashboard service.

        Args:
            session: Async SQLAlchemy session
            cache_ttl: Cache time-to-live in seconds (default: 300)
        """
        self.session = session
        self.cache_ttl = cache_ttl
        self.cache = None

    async def _init_cache(self):
        """Initialize Redis cache connection if not already initialized."""
        if self.cache is None:
            self.cache = await get_cache()

    async def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache with JSON deserialization.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        await self._init_cache()
        if self.cache is None:
            return None

        try:
            cached_value = await self.cache.get(key)
            if cached_value:
                return json.loads(cached_value)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")

        return None

    async def _set_cached(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with JSON serialization.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (uses default if not provided)

        Returns:
            True if successful, False otherwise
        """
        await self._init_cache()
        if self.cache is None:
            return False

        try:
            ttl = ttl or self.cache_ttl
            serialized = json.dumps(value, default=str)  # default=str handles datetime
            await self.cache.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    async def get_company_performance(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        min_revenue: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get company performance data from mart_company_performance.

        This method queries the dbt mart table that aggregates company metrics
        including revenue, growth rates, retention, and EdTech-specific KPIs.

        Args:
            category: Filter by EdTech category (k12, higher_education, etc.)
            limit: Maximum number of companies to return (default: all)
            min_revenue: Minimum latest revenue filter in USD

        Returns:
            List of dictionaries containing company performance metrics:
            - ticker: Company stock ticker
            - company_name: Company name
            - edtech_category: EdTech market segment
            - latest_revenue: Most recent quarterly/annual revenue (USD)
            - revenue_yoy_growth: Year-over-year revenue growth (%)
            - latest_nrr: Net revenue retention (%)
            - latest_mau: Monthly active users
            - latest_arpu: Average revenue per user (USD)
            - latest_ltv_cac_ratio: Customer lifetime value / acquisition cost
            - overall_score: Composite performance score (0-100)
            - data_freshness: Timestamp of latest data point

        Example:
            ```python
            # Get all K-12 companies
            k12_companies = await service.get_company_performance(category="k12")

            # Get top 10 companies by revenue
            top_companies = await service.get_company_performance(limit=10)
            ```
        """
        cache_key = f"dashboard:company_performance:{category}:{limit}:{min_revenue}"

        # Try cache first
        cached_data = await self._get_cached(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data

        try:
            # Query the dbt mart table
            # Note: This assumes mart_company_performance exists from dbt transformations
            query = text("""
                SELECT
                    ticker,
                    company_name,
                    edtech_category,
                    latest_revenue,
                    revenue_yoy_growth,
                    latest_nrr,
                    latest_mau,
                    latest_arpu,
                    latest_ltv_cac_ratio,
                    overall_score,
                    data_freshness
                FROM mart_company_performance
                WHERE 1=1
                    AND (:category IS NULL OR edtech_category = :category)
                    AND (:min_revenue IS NULL OR latest_revenue >= :min_revenue)
                ORDER BY latest_revenue DESC NULLS LAST
                LIMIT :limit_val
            """)

            params = {
                "category": category,
                "min_revenue": min_revenue,
                "limit_val": limit or 1000  # Default high limit
            }

            result = await self.session.execute(query, params)
            rows = result.fetchall()

            # Convert to list of dicts
            data = [dict(row._mapping) for row in rows]

            # Cache the result
            await self._set_cached(cache_key, data)

            logger.info(f"Fetched {len(data)} companies from mart_company_performance")
            return data

        except Exception as e:
            logger.error(f"Error fetching company performance: {e}")
            # Fallback to raw tables if mart doesn't exist yet
            return await self._get_company_performance_fallback(category, limit, min_revenue)

    async def _get_company_performance_fallback(
        self,
        category: Optional[str],
        limit: Optional[int],
        min_revenue: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Fallback method to query raw tables if mart doesn't exist yet.

        Uses CompanyRepository for cleaner data access abstraction.
        """
        logger.warning("Using fallback query - mart_company_performance not available")

        try:
            # Use repository pattern for cleaner data access
            company_repo = CompanyRepository(self.session)

            # Get companies based on filters
            if category:
                companies = await company_repo.find_by_category(category, limit=limit)
            else:
                companies = await company_repo.get_all(limit=limit, order_by="name")

            # Return basic company info
            data = [
                {
                    "ticker": c.ticker,
                    "company_name": c.name,
                    "edtech_category": c.category,
                    "latest_revenue": None,
                    "revenue_yoy_growth": None,
                    "latest_nrr": None,
                    "latest_mau": None,
                    "latest_arpu": None,
                    "latest_ltv_cac_ratio": None,
                    "overall_score": None,
                    "data_freshness": None,
                }
                for c in companies
            ]

            return data

        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
            return []

    async def get_competitive_landscape(
        self,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get competitive landscape metrics from mart_competitive_landscape.

        This method queries aggregated market segment data including total revenue,
        company counts, growth rates, and concentration metrics.

        Args:
            category: Filter by EdTech category or None for all segments

        Returns:
            Dictionary containing competitive landscape data:
            - segments: List of segment dictionaries with:
                - edtech_category: Market segment name
                - total_segment_revenue: Total revenue in segment (USD)
                - companies_in_segment: Number of companies
                - avg_revenue_growth: Average YoY growth (%)
                - avg_nrr: Average net revenue retention (%)
                - hhi_index: Herfindahl-Hirschman Index (market concentration)
                - top_3_market_share: Combined market share of top 3 (%)
                - data_freshness: Timestamp of latest data
            - market_summary: Overall market aggregates

        Example:
            ```python
            landscape = await service.get_competitive_landscape()
            for segment in landscape['segments']:
                print(f"{segment['edtech_category']}: {segment['total_segment_revenue']}")
            ```
        """
        cache_key = f"dashboard:competitive_landscape:{category}"

        # Try cache first
        cached_data = await self._get_cached(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data

        try:
            # Query the dbt mart table
            query = text("""
                SELECT
                    edtech_category,
                    total_segment_revenue,
                    companies_in_segment,
                    avg_revenue_growth,
                    avg_nrr,
                    hhi_index,
                    top_3_market_share,
                    data_freshness
                FROM mart_competitive_landscape
                WHERE :category IS NULL OR edtech_category = :category
                ORDER BY total_segment_revenue DESC
            """)

            result = await self.session.execute(query, {"category": category})
            rows = result.fetchall()

            segments = [dict(row._mapping) for row in rows]

            # Calculate market summary
            total_revenue = sum(s['total_segment_revenue'] or 0 for s in segments)
            total_companies = sum(s['companies_in_segment'] or 0 for s in segments)

            data = {
                "segments": segments,
                "market_summary": {
                    "total_market_revenue": total_revenue,
                    "total_companies": total_companies,
                    "num_segments": len(segments),
                    "data_freshness": datetime.utcnow().isoformat()
                }
            }

            # Cache the result
            await self._set_cached(cache_key, data)

            logger.info(f"Fetched competitive landscape for {len(segments)} segments")
            return data

        except Exception as e:
            logger.error(f"Error fetching competitive landscape: {e}")
            # Return empty structure on error
            return {
                "segments": [],
                "market_summary": {
                    "total_market_revenue": 0,
                    "total_companies": 0,
                    "num_segments": 0,
                    "data_freshness": datetime.utcnow().isoformat()
                }
            }

    async def get_company_details(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific company.

        Args:
            ticker: Company stock ticker symbol

        Returns:
            Dictionary with company details:
            - Basic info: ticker, name, sector, category
            - Metadata: founded_year, headquarters, website
            - Latest metrics: revenue, growth, retention, users
            - Historical data availability
            None if company not found

        Example:
            ```python
            company = await service.get_company_details("DUOL")
            if company:
                print(f"{company['name']} revenue: ${company['latest_revenue']}")
            ```
        """
        cache_key = f"dashboard:company_details:{ticker}"

        # Try cache first
        cached_data = await self._get_cached(cache_key)
        if cached_data:
            return cached_data

        try:
            # Use repository for cleaner data access
            company_repo = CompanyRepository(self.session)
            company = await company_repo.find_by_ticker(ticker)

            if not company:
                logger.warning(f"Company {ticker} not found")
                return None

            # Get latest metrics from performance mart
            perf_query = text("""
                SELECT
                    latest_revenue,
                    revenue_yoy_growth,
                    latest_nrr,
                    latest_mau,
                    latest_arpu,
                    latest_ltv_cac_ratio,
                    overall_score,
                    data_freshness
                FROM mart_company_performance
                WHERE ticker = :ticker
            """)

            perf_result = await self.session.execute(perf_query, {"ticker": ticker})
            perf_row = perf_result.fetchone()

            # Build comprehensive details
            details = {
                "ticker": company.ticker,
                "name": company.name,
                "cik": company.cik,
                "sector": company.sector,
                "subsector": company.subsector,
                "category": company.category,
                "subcategory": company.subcategory,
                "delivery_model": company.delivery_model,
                "monetization_strategy": company.monetization_strategy,
                "founded_year": company.founded_year,
                "headquarters": company.headquarters,
                "website": company.website,
                "employee_count": company.employee_count,
                "latest_metrics": dict(perf_row._mapping) if perf_row else {},
                "created_at": company.created_at.isoformat() if company.created_at else None,
                "updated_at": company.updated_at.isoformat() if company.updated_at else None,
            }

            # Cache for longer period (1 hour) since company details change less frequently
            await self._set_cached(cache_key, details, ttl=3600)

            return details

        except Exception as e:
            logger.error(f"Error fetching company details for {ticker}: {e}")
            return None

    async def get_quarterly_metrics(
        self,
        ticker: str,
        metric_type: str,
        quarters: int = 8
    ) -> pd.DataFrame:
        """Get time-series quarterly metrics for a company.

        Args:
            ticker: Company stock ticker
            metric_type: Type of metric (revenue, mau, arpu, nrr, etc.)
            quarters: Number of quarters to retrieve (default: 8 = 2 years)

        Returns:
            DataFrame with columns:
            - metric_date: Quarter end date
            - value: Metric value
            - unit: Value unit (USD, percent, count)
            - yoy_growth: Year-over-year growth percentage
            - qoq_growth: Quarter-over-quarter growth percentage

        Example:
            ```python
            revenue_df = await service.get_quarterly_metrics("DUOL", "revenue")
            print(revenue_df[['metric_date', 'value', 'yoy_growth']])
            ```
        """
        cache_key = f"dashboard:quarterly_metrics:{ticker}:{metric_type}:{quarters}"

        # Try cache first
        cached_data = await self._get_cached(cache_key)
        if cached_data:
            return pd.DataFrame(cached_data)

        try:
            # Use repositories for cleaner data access
            company_repo = CompanyRepository(self.session)
            metrics_repo = MetricsRepository(self.session)

            # Get company
            company = await company_repo.find_by_ticker(ticker)

            if not company:
                logger.warning(f"Company {ticker} not found")
                return pd.DataFrame()

            # Get quarterly metrics using repository
            metrics = await metrics_repo.get_metrics_by_period(
                company.id,
                metric_type,
                period_type="quarterly",
                quarters=quarters
            )

            if not metrics:
                logger.info(f"No metrics found for {ticker} - {metric_type}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    "metric_date": m.metric_date,
                    "value": m.value,
                    "unit": m.unit,
                    "period_type": m.period_type,
                }
                for m in metrics
            ])

            # Calculate growth rates
            df = df.sort_values("metric_date")
            df["qoq_growth"] = df["value"].pct_change() * 100
            df["yoy_growth"] = df["value"].pct_change(periods=4) * 100  # 4 quarters = 1 year

            # Cache the result as dict
            data_dict = df.to_dict(orient="records")
            await self._set_cached(cache_key, data_dict)

            logger.info(f"Fetched {len(df)} quarterly metrics for {ticker} - {metric_type}")
            return df

        except Exception as e:
            logger.error(f"Error fetching quarterly metrics: {e}")
            return pd.DataFrame()

    async def get_market_summary(self) -> Dict[str, Any]:
        """Get high-level market KPIs for dashboard cards.

        Returns:
            Dictionary containing market-wide KPIs:
            - total_market_revenue: Total market revenue (USD)
            - avg_yoy_growth: Market average YoY growth (%)
            - avg_nrr: Market average NRR (%)
            - total_active_users: Total MAU across all companies
            - num_companies: Number of companies tracked
            - data_freshness: Timestamp of latest data

        Example:
            ```python
            summary = await service.get_market_summary()
            print(f"Market size: ${summary['total_market_revenue'] / 1e9:.1f}B")
            ```
        """
        cache_key = "dashboard:market_summary"

        # Try cache first
        cached_data = await self._get_cached(cache_key)
        if cached_data:
            return cached_data

        try:
            # Aggregate from competitive landscape mart
            query = text("""
                SELECT
                    SUM(total_segment_revenue) as total_market_revenue,
                    AVG(avg_revenue_growth) as avg_yoy_growth,
                    AVG(avg_nrr) as avg_nrr,
                    SUM(companies_in_segment) as num_companies,
                    MAX(data_freshness) as data_freshness
                FROM mart_competitive_landscape
            """)

            result = await self.session.execute(query)
            row = result.fetchone()

            # Get total users from company performance mart
            users_query = text("""
                SELECT SUM(latest_mau) as total_active_users
                FROM mart_company_performance
            """)

            users_result = await self.session.execute(users_query)
            users_row = users_result.fetchone()

            summary = {
                "total_market_revenue": float(row.total_market_revenue or 0),
                "avg_yoy_growth": float(row.avg_yoy_growth or 0),
                "avg_nrr": float(row.avg_nrr or 0),
                "total_active_users": float(users_row.total_active_users or 0),
                "num_companies": int(row.num_companies or 0),
                "data_freshness": row.data_freshness.isoformat() if row.data_freshness else None,
            }

            # Cache for 5 minutes
            await self._set_cached(cache_key, summary)

            logger.info("Fetched market summary")
            return summary

        except Exception as e:
            logger.error(f"Error fetching market summary: {e}")
            return {
                "total_market_revenue": 0.0,
                "avg_yoy_growth": 0.0,
                "avg_nrr": 0.0,
                "total_active_users": 0.0,
                "num_companies": 0,
                "data_freshness": None,
            }

    async def get_segment_comparison(
        self,
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Get normalized metrics for radar chart comparison across segments.

        Args:
            metrics: List of metric names to include (default: all key metrics)

        Returns:
            Dictionary with segment-level normalized metrics (0-100 scale):
            - segments: List of segment names
            - metrics: List of metric names
            - values: 2D array of normalized values [segment][metric]

        Example:
            ```python
            comparison = await service.get_segment_comparison()
            # Use in create_segment_comparison_radar()
            ```
        """
        cache_key = f"dashboard:segment_comparison:{metrics}"

        # Try cache first
        cached_data = await self._get_cached(cache_key)
        if cached_data:
            return cached_data

        # Default metrics for comparison
        if not metrics:
            metrics = [
                "avg_revenue_growth",
                "avg_nrr",
                "avg_ltv_cac_ratio",
                "market_concentration",
                "segment_maturity"
            ]

        try:
            query = text("""
                SELECT
                    edtech_category,
                    avg_revenue_growth,
                    avg_nrr,
                    hhi_index,
                    companies_in_segment,
                    total_segment_revenue
                FROM mart_competitive_landscape
                ORDER BY edtech_category
            """)

            result = await self.session.execute(query)
            rows = result.fetchall()

            segments = []
            values = []

            for row in rows:
                segments.append(row.edtech_category)

                # Normalize metrics to 0-100 scale
                segment_values = {
                    "avg_revenue_growth": min(100, (row.avg_revenue_growth or 0)),
                    "avg_nrr": (row.avg_nrr or 0),
                    "avg_ltv_cac_ratio": min(100, (row.avg_revenue_growth or 0) * 3),  # Proxy
                    "market_concentration": 100 - min(100, (row.hhi_index or 0) / 100),
                    "segment_maturity": min(100, (row.companies_in_segment or 0) * 5)
                }

                values.append([segment_values[m] for m in metrics])

            comparison = {
                "segments": segments,
                "metrics": metrics,
                "values": values,
            }

            await self._set_cached(cache_key, comparison)

            return comparison

        except Exception as e:
            logger.error(f"Error fetching segment comparison: {e}")
            return {
                "segments": [],
                "metrics": metrics,
                "values": [],
            }

    async def get_data_freshness(self) -> Dict[str, Any]:
        """Get metadata about data freshness and availability.

        Returns:
            Dictionary with data freshness information:
            - last_updated: Timestamp of most recent data update
            - companies_count: Number of companies with data
            - metrics_count: Number of metric records
            - oldest_data: Timestamp of oldest data point
            - coverage_by_category: Data coverage per EdTech category

        Example:
            ```python
            freshness = await service.get_data_freshness()
            print(f"Data last updated: {freshness['last_updated']}")
            ```
        """
        cache_key = "dashboard:data_freshness"

        cached_data = await self._get_cached(cache_key)
        if cached_data:
            return cached_data

        try:
            # Get latest data timestamp
            latest_query = text("""
                SELECT MAX(data_freshness) as last_updated
                FROM mart_company_performance
            """)
            latest_result = await self.session.execute(latest_query)
            latest_row = latest_result.fetchone()

            # Get counts
            counts_query = text("""
                SELECT
                    COUNT(DISTINCT ticker) as companies_count,
                    COUNT(*) as metrics_count
                FROM mart_company_performance
            """)
            counts_result = await self.session.execute(counts_query)
            counts_row = counts_result.fetchone()

            # Get category coverage
            coverage_query = text("""
                SELECT
                    edtech_category,
                    companies_in_segment
                FROM mart_competitive_landscape
            """)
            coverage_result = await self.session.execute(coverage_query)
            coverage_rows = coverage_result.fetchall()

            freshness = {
                "last_updated": latest_row.last_updated.isoformat() if latest_row.last_updated else None,
                "companies_count": int(counts_row.companies_count or 0),
                "metrics_count": int(counts_row.metrics_count or 0),
                "coverage_by_category": {
                    row.edtech_category: int(row.companies_in_segment or 0)
                    for row in coverage_rows
                }
            }

            await self._set_cached(cache_key, freshness, ttl=60)  # Cache for 1 minute

            return freshness

        except Exception as e:
            logger.error(f"Error fetching data freshness: {e}")
            return {
                "last_updated": None,
                "companies_count": 0,
                "metrics_count": 0,
                "coverage_by_category": {}
            }
