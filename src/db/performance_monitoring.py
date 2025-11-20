"""PostgreSQL query performance monitoring utilities.

This module provides utilities to query pg_stat_statements and analyze
database query performance to identify bottlenecks in production.
"""

from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_slow_queries(
    db: AsyncSession,
    min_duration_ms: int = 1000,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Fetch queries slower than threshold from pg_stat_statements.

    Args:
        db: Database session
        min_duration_ms: Minimum average execution time in milliseconds (default: 1000ms = 1s)
        limit: Maximum number of queries to return (default: 50)

    Returns:
        List of dictionaries containing slow query information:
        - query: SQL query text (normalized, parameters removed)
        - calls: Number of times executed
        - total_time_ms: Total execution time in milliseconds
        - avg_time_ms: Average execution time in milliseconds
        - max_time_ms: Maximum execution time in milliseconds
        - min_time_ms: Minimum execution time in milliseconds
        - rows: Total number of rows returned
        - cache_hit_ratio: Percentage of blocks read from cache vs disk

    Example:
        >>> async with get_db() as db:
        ...     slow = await get_slow_queries(db, min_duration_ms=500)
        ...     for query_info in slow:
        ...         print(f"Query: {query_info['query'][:100]}...")
        ...         print(f"Avg time: {query_info['avg_time_ms']:.2f}ms")
    """
    query = text("""
        SELECT
            query,
            calls,
            total_exec_time AS total_time_ms,
            mean_exec_time AS avg_time_ms,
            max_exec_time AS max_time_ms,
            min_exec_time AS min_time_ms,
            stddev_exec_time AS stddev_time_ms,
            rows,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
        FROM pg_stat_statements
        WHERE mean_exec_time >= :min_duration
        ORDER BY mean_exec_time DESC
        LIMIT :limit
    """)

    result = await db.execute(
        query,
        {"min_duration": min_duration_ms, "limit": limit}
    )

    return [dict(row._mapping) for row in result]


async def get_top_queries_by_total_time(
    db: AsyncSession,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get queries consuming the most total execution time.

    These are high-impact queries that may be called frequently or run slowly.
    Optimizing these queries provides the most benefit.

    Args:
        db: Database session
        limit: Maximum number of queries to return (default: 50)

    Returns:
        List of dictionaries containing query information sorted by total time

    Example:
        >>> async with get_db() as db:
        ...     top = await get_top_queries_by_total_time(db, limit=10)
        ...     for i, q in enumerate(top, 1):
        ...         print(f"{i}. Total time: {q['total_time_ms']:.0f}ms, Calls: {q['calls']}")
    """
    query = text("""
        SELECT
            query,
            calls,
            total_exec_time AS total_time_ms,
            mean_exec_time AS avg_time_ms,
            max_exec_time AS max_time_ms,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
        FROM pg_stat_statements
        ORDER BY total_exec_time DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"limit": limit})
    return [dict(row._mapping) for row in result]


async def get_queries_with_low_cache_hit(
    db: AsyncSession,
    max_cache_ratio: float = 90.0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get queries with low cache hit ratios (heavy disk I/O).

    These queries are reading a lot of data from disk instead of cache,
    which can cause performance issues. Consider adding indexes or
    adjusting work_mem settings.

    Args:
        db: Database session
        max_cache_ratio: Maximum cache hit ratio to include (default: 90%)
        limit: Maximum number of queries to return (default: 50)

    Returns:
        List of dictionaries containing query information sorted by cache hit ratio

    Example:
        >>> async with get_db() as db:
        ...     low_cache = await get_queries_with_low_cache_hit(db)
        ...     for q in low_cache:
        ...         print(f"Cache hit: {q['cache_hit_ratio']:.1f}%")
        ...         print(f"Query: {q['query'][:100]}...")
    """
    query = text("""
        SELECT
            query,
            calls,
            mean_exec_time AS avg_time_ms,
            shared_blks_hit,
            shared_blks_read,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
        FROM pg_stat_statements
        WHERE shared_blks_read > 0
            AND 100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) < :max_ratio
        ORDER BY cache_hit_ratio ASC
        LIMIT :limit
    """)

    result = await db.execute(
        query,
        {"max_ratio": max_cache_ratio, "limit": limit}
    )
    return [dict(row._mapping) for row in result]


async def get_database_statistics(db: AsyncSession) -> Dict[str, Any]:
    """Get overall database performance statistics.

    Args:
        db: Database session

    Returns:
        Dictionary containing database-wide statistics:
        - total_queries: Total number of different queries tracked
        - total_calls: Total number of query executions
        - total_time_ms: Total execution time across all queries
        - avg_time_ms: Average execution time across all queries
        - cache_hit_ratio: Overall cache hit ratio

    Example:
        >>> async with get_db() as db:
        ...     stats = await get_database_statistics(db)
        ...     print(f"Total queries tracked: {stats['total_queries']}")
        ...     print(f"Overall cache hit ratio: {stats['cache_hit_ratio']:.1f}%")
    """
    query = text("""
        SELECT
            COUNT(*) AS total_queries,
            SUM(calls) AS total_calls,
            SUM(total_exec_time) AS total_time_ms,
            AVG(mean_exec_time) AS avg_time_ms,
            100.0 * SUM(shared_blks_hit) / NULLIF(SUM(shared_blks_hit + shared_blks_read), 0) AS cache_hit_ratio
        FROM pg_stat_statements
    """)

    result = await db.execute(query)
    row = result.first()

    if row:
        return dict(row._mapping)
    return {}


async def reset_query_statistics(db: AsyncSession) -> None:
    """Reset pg_stat_statements statistics.

    This clears all accumulated query statistics. Use this after
    making performance optimizations to measure their impact.

    Args:
        db: Database session

    Note:
        Requires superuser privileges or pg_stat_statements_reset() grant.

    Example:
        >>> async with get_db() as db:
        ...     await reset_query_statistics(db)
        ...     print("Query statistics reset")
    """
    await db.execute(text("SELECT pg_stat_statements_reset()"))
    await db.commit()


async def get_query_plan(
    db: AsyncSession,
    query_text: str,
    analyze: bool = False
) -> str:
    """Get the execution plan for a query.

    Args:
        db: Database session
        query_text: SQL query to explain
        analyze: If True, actually execute the query and show real timing (default: False)

    Returns:
        Query execution plan as formatted text

    Warning:
        Setting analyze=True will actually execute the query, which may modify data
        or take a long time for slow queries. Use with caution.

    Example:
        >>> async with get_db() as db:
        ...     plan = await get_query_plan(db, "SELECT * FROM companies WHERE ticker = 'AAPL'")
        ...     print(plan)
    """
    explain_query = f"EXPLAIN {'ANALYZE ' if analyze else ''}{query_text}"
    result = await db.execute(text(explain_query))

    # Combine all plan rows into a single string
    plan_lines = [row[0] for row in result]
    return "\n".join(plan_lines)


async def get_table_statistics(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get statistics about table access patterns.

    Args:
        db: Database session

    Returns:
        List of dictionaries containing table statistics:
        - table_name: Name of the table
        - seq_scans: Number of sequential scans
        - seq_rows_read: Number of rows read by sequential scans
        - idx_scans: Number of index scans
        - idx_rows_fetched: Number of rows fetched by index scans
        - inserts: Number of rows inserted
        - updates: Number of rows updated
        - deletes: Number of rows deleted

    Example:
        >>> async with get_db() as db:
        ...     tables = await get_table_statistics(db)
        ...     for table in tables:
        ...         if table['seq_scans'] > 1000:
        ...             print(f"Table {table['table_name']} has many sequential scans - consider indexing")
    """
    query = text("""
        SELECT
            schemaname || '.' || tablename AS table_name,
            seq_scan AS seq_scans,
            seq_tup_read AS seq_rows_read,
            idx_scan AS idx_scans,
            idx_tup_fetch AS idx_rows_fetched,
            n_tup_ins AS inserts,
            n_tup_upd AS updates,
            n_tup_del AS deletes,
            n_live_tup AS live_rows,
            n_dead_tup AS dead_rows
        FROM pg_stat_user_tables
        ORDER BY seq_scan DESC
    """)

    result = await db.execute(query)
    return [dict(row._mapping) for row in result]


async def get_index_usage(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get statistics about index usage.

    Identifies unused or rarely used indexes that may be candidates for removal.

    Args:
        db: Database session

    Returns:
        List of dictionaries containing index usage statistics:
        - table_name: Name of the table
        - index_name: Name of the index
        - scans: Number of times the index was used
        - rows_read: Number of rows read using the index
        - rows_fetched: Number of rows actually fetched

    Example:
        >>> async with get_db() as db:
        ...     indexes = await get_index_usage(db)
        ...     for idx in indexes:
        ...         if idx['scans'] == 0:
        ...             print(f"Unused index: {idx['index_name']} on {idx['table_name']}")
    """
    query = text("""
        SELECT
            schemaname || '.' || tablename AS table_name,
            indexname AS index_name,
            idx_scan AS scans,
            idx_tup_read AS rows_read,
            idx_tup_fetch AS rows_fetched
        FROM pg_stat_user_indexes
        ORDER BY idx_scan ASC
    """)

    result = await db.execute(query)
    return [dict(row._mapping) for row in result]
