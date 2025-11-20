"""Example usage of PostgreSQL query performance monitoring.

This example demonstrates how to use the performance monitoring utilities
to identify and analyze database bottlenecks.
"""

import asyncio
from typing import List, Dict, Any

from src.db import (
    get_db,
    get_slow_queries,
    get_top_queries_by_total_time,
    get_queries_with_low_cache_hit,
    get_database_statistics,
    get_table_statistics,
    get_index_usage,
    get_query_plan,
)


async def analyze_slow_queries(min_duration_ms: int = 1000) -> None:
    """Identify and report slow queries."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print(f"SLOW QUERIES (avg execution time > {min_duration_ms}ms)")
        print(f"{'='*80}\n")

        slow_queries = await get_slow_queries(
            db,
            min_duration_ms=min_duration_ms,
            limit=10
        )

        if not slow_queries:
            print("✅ No slow queries found!")
            return

        for i, query in enumerate(slow_queries, 1):
            print(f"{i}. Query (truncated):")
            print(f"   {query['query'][:100]}...")
            print(f"   Calls: {query['calls']}")
            print(f"   Avg time: {query['avg_time_ms']:.2f}ms")
            print(f"   Max time: {query['max_time_ms']:.2f}ms")
            print(f"   Cache hit ratio: {query.get('cache_hit_ratio', 0):.1f}%")
            print()


async def analyze_high_impact_queries() -> None:
    """Find queries consuming the most total time."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print("HIGH IMPACT QUERIES (sorted by total execution time)")
        print(f"{'='*80}\n")

        top_queries = await get_top_queries_by_total_time(db, limit=10)

        for i, query in enumerate(top_queries, 1):
            total_time_sec = query['total_time_ms'] / 1000
            print(f"{i}. Query (truncated):")
            print(f"   {query['query'][:100]}...")
            print(f"   Total time: {total_time_sec:.2f}s ({query['calls']} calls)")
            print(f"   Avg time: {query['avg_time_ms']:.2f}ms")
            print(f"   Cache hit ratio: {query.get('cache_hit_ratio', 0):.1f}%")
            print()


async def analyze_cache_efficiency() -> None:
    """Identify queries with poor cache hit ratios."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print("QUERIES WITH LOW CACHE HIT RATIO (heavy disk I/O)")
        print(f"{'='*80}\n")

        low_cache_queries = await get_queries_with_low_cache_hit(
            db,
            max_cache_ratio=90.0,
            limit=10
        )

        if not low_cache_queries:
            print("✅ All queries have good cache hit ratios!")
            return

        for i, query in enumerate(low_cache_queries, 1):
            print(f"{i}. Query (truncated):")
            print(f"   {query['query'][:100]}...")
            print(f"   Cache hit ratio: {query['cache_hit_ratio']:.1f}%")
            print(f"   Blocks from cache: {query['shared_blks_hit']}")
            print(f"   Blocks from disk: {query['shared_blks_read']}")
            print(f"   Avg time: {query['avg_time_ms']:.2f}ms")
            print()


async def show_database_statistics() -> None:
    """Display overall database performance statistics."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print("OVERALL DATABASE STATISTICS")
        print(f"{'='*80}\n")

        stats = await get_database_statistics(db)

        print(f"Total unique queries tracked: {stats.get('total_queries', 0)}")
        print(f"Total query executions: {stats.get('total_calls', 0)}")
        print(f"Total execution time: {stats.get('total_time_ms', 0) / 1000:.2f}s")
        print(f"Average query time: {stats.get('avg_time_ms', 0):.2f}ms")
        print(f"Overall cache hit ratio: {stats.get('cache_hit_ratio', 0):.1f}%")
        print()


async def analyze_table_access_patterns() -> None:
    """Identify tables that may need indexes."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print("TABLE ACCESS PATTERNS")
        print(f"{'='*80}\n")

        tables = await get_table_statistics(db)

        print("Tables with high sequential scan counts (may need indexes):\n")

        for table in tables[:10]:
            seq_scans = table.get('seq_scans', 0)
            idx_scans = table.get('idx_scans', 0) or 0

            if seq_scans > 100 and seq_scans > idx_scans:
                print(f"⚠️  {table['table_name']}")
                print(f"   Sequential scans: {seq_scans}")
                print(f"   Index scans: {idx_scans}")
                print(f"   Live rows: {table.get('live_rows', 0)}")
                print()


async def analyze_index_usage() -> None:
    """Identify unused or rarely used indexes."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print("INDEX USAGE ANALYSIS")
        print(f"{'='*80}\n")

        indexes = await get_index_usage(db)

        unused = [idx for idx in indexes if idx.get('scans', 0) == 0]
        rarely_used = [idx for idx in indexes if 0 < idx.get('scans', 0) < 10]

        if unused:
            print(f"Unused indexes ({len(unused)}):\n")
            for idx in unused[:10]:
                print(f"❌ {idx['index_name']} on {idx['table_name']}")
            print()

        if rarely_used:
            print(f"Rarely used indexes ({len(rarely_used)}):\n")
            for idx in rarely_used[:10]:
                print(f"⚠️  {idx['index_name']} on {idx['table_name']}")
                print(f"   Scans: {idx['scans']}")
            print()

        heavily_used = sorted(
            [idx for idx in indexes if idx.get('scans', 0) > 1000],
            key=lambda x: x.get('scans', 0),
            reverse=True
        )

        if heavily_used:
            print(f"Heavily used indexes (top 10):\n")
            for idx in heavily_used[:10]:
                print(f"✅ {idx['index_name']} on {idx['table_name']}")
                print(f"   Scans: {idx['scans']}")
            print()


async def explain_query(query_text: str) -> None:
    """Show the execution plan for a specific query."""
    async with get_db() as db:
        print(f"\n{'='*80}")
        print("QUERY EXECUTION PLAN")
        print(f"{'='*80}\n")

        print(f"Query: {query_text}\n")
        print("Execution Plan:")
        print("-" * 80)

        plan = await get_query_plan(db, query_text, analyze=False)
        print(plan)
        print()


async def main() -> None:
    """Run a comprehensive performance analysis."""
    print("\n" + "="*80)
    print("PostgreSQL Query Performance Analysis")
    print("="*80)

    try:
        # Overall statistics first
        await show_database_statistics()

        # Identify slow queries
        await analyze_slow_queries(min_duration_ms=1000)

        # Find high-impact queries
        await analyze_high_impact_queries()

        # Check cache efficiency
        await analyze_cache_efficiency()

        # Analyze table access patterns
        await analyze_table_access_patterns()

        # Review index usage
        await analyze_index_usage()

        # Example: Explain a specific query
        # await explain_query("SELECT * FROM companies WHERE ticker = 'AAPL'")

        print("\n" + "="*80)
        print("Analysis complete!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        raise


if __name__ == "__main__":
    # Run the analysis
    asyncio.run(main())
