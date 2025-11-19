"""Admin endpoints for database performance monitoring.

These endpoints provide access to query performance statistics and
database monitoring tools. Should be protected with admin-only authentication.
"""

from typing import Dict, List, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import (
    get_database_statistics,
    get_db,
    get_index_usage,
    get_queries_with_low_cache_hit,
    get_slow_queries,
    get_table_statistics,
    get_top_queries_by_total_time,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/performance/slow-queries")
async def get_slow_queries_endpoint(
    min_duration_ms: int = Query(default=1000, ge=100, description="Minimum average execution time in milliseconds"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of queries to return"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get slow queries from pg_stat_statements.

    Returns queries that are averaging above the specified duration threshold.
    Use this to identify performance bottlenecks.

    Args:
        min_duration_ms: Minimum average execution time in milliseconds (default: 1000ms)
        limit: Maximum number of queries to return (default: 50, max: 200)

    Returns:
        List of slow queries with execution statistics

    Example response:
        [
            {
                "query": "SELECT * FROM companies WHERE...",
                "calls": 1523,
                "total_time_ms": 45230.5,
                "avg_time_ms": 29.7,
                "max_time_ms": 156.2,
                "cache_hit_ratio": 94.5
            }
        ]
    """
    return await get_slow_queries(db, min_duration_ms=min_duration_ms, limit=limit)


@router.get("/performance/top-queries")
async def get_top_queries_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of queries to return"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get queries consuming the most total execution time.

    These are high-impact queries that may be called frequently or run slowly.
    Optimizing these queries provides the most performance benefit.

    Args:
        limit: Maximum number of queries to return (default: 50, max: 200)

    Returns:
        List of queries sorted by total execution time

    Example response:
        [
            {
                "query": "SELECT * FROM financial_metrics...",
                "calls": 5421,
                "total_time_ms": 125340.2,
                "avg_time_ms": 23.1,
                "cache_hit_ratio": 89.3
            }
        ]
    """
    return await get_top_queries_by_total_time(db, limit=limit)


@router.get("/performance/low-cache-hit")
async def get_low_cache_hit_endpoint(
    max_cache_ratio: float = Query(default=90.0, ge=0.0, le=100.0, description="Maximum cache hit ratio"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of queries to return"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get queries with low cache hit ratios (heavy disk I/O).

    These queries are reading a lot of data from disk instead of cache.
    Consider adding indexes or adjusting PostgreSQL configuration.

    Args:
        max_cache_ratio: Maximum cache hit ratio to include (default: 90%)
        limit: Maximum number of queries to return (default: 50, max: 200)

    Returns:
        List of queries with low cache hit ratios

    Example response:
        [
            {
                "query": "SELECT * FROM documents...",
                "calls": 234,
                "avg_time_ms": 45.6,
                "shared_blks_hit": 1200,
                "shared_blks_read": 800,
                "cache_hit_ratio": 60.0
            }
        ]
    """
    return await get_queries_with_low_cache_hit(
        db, max_cache_ratio=max_cache_ratio, limit=limit
    )


@router.get("/performance/database-stats")
async def get_database_stats_endpoint(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get overall database performance statistics.

    Provides a high-level overview of database query performance,
    including total queries tracked, execution times, and cache efficiency.

    Returns:
        Dictionary containing database-wide statistics

    Example response:
        {
            "total_queries": 156,
            "total_calls": 45230,
            "total_time_ms": 1234567.8,
            "avg_time_ms": 27.3,
            "cache_hit_ratio": 92.5
        }
    """
    return await get_database_statistics(db)


@router.get("/performance/table-stats")
async def get_table_stats_endpoint(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get statistics about table access patterns.

    Shows how tables are being accessed (sequential scans vs index scans),
    which can help identify missing indexes or inefficient queries.

    Returns:
        List of table statistics sorted by sequential scans

    Example response:
        [
            {
                "table_name": "public.companies",
                "seq_scans": 1234,
                "seq_rows_read": 456789,
                "idx_scans": 5678,
                "idx_rows_fetched": 234567,
                "inserts": 100,
                "updates": 50,
                "deletes": 5
            }
        ]
    """
    return await get_table_statistics(db)


@router.get("/performance/index-usage")
async def get_index_usage_endpoint(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get statistics about index usage.

    Identifies unused or rarely used indexes that may be candidates for removal,
    as well as heavily used indexes that are critical for performance.

    Returns:
        List of index usage statistics

    Example response:
        [
            {
                "table_name": "public.financial_metrics",
                "index_name": "idx_metric_time",
                "scans": 5234,
                "rows_read": 123456,
                "rows_fetched": 98765
            }
        ]
    """
    return await get_index_usage(db)
