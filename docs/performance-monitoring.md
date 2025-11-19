# PostgreSQL Query Performance Monitoring

This guide explains how to use the PostgreSQL query performance monitoring features to identify and resolve production bottlenecks.

## Overview

The system uses PostgreSQL's `pg_stat_statements` extension to track query execution statistics. This allows you to:

- Identify slow queries
- Find queries consuming the most total time
- Detect queries with poor cache hit ratios
- Analyze table and index usage patterns
- Monitor overall database performance

## Setup

### 1. Apply Database Migration

Run the Alembic migration to enable the extension:

```bash
# Development
docker-compose exec api alembic upgrade head

# Production
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

This migration creates:
- `pg_stat_statements` extension
- Helper views for common queries:
  - `slow_queries` - Queries averaging >1 second
  - `top_queries_by_total_time` - Queries consuming most time
  - `queries_low_cache_hit` - Queries with poor cache efficiency

### 2. Restart PostgreSQL

The monitoring requires PostgreSQL to be started with `shared_preload_libraries='pg_stat_statements'`. This is already configured in the docker-compose files.

```bash
# Development
docker-compose restart postgres

# Production
docker-compose -f docker-compose.prod.yml restart postgres
```

### 3. Verify Installation

Check that the extension is enabled:

```sql
SELECT * FROM pg_available_extensions WHERE name = 'pg_stat_statements';
```

## Configuration

### PostgreSQL Settings

The following settings are configured in docker-compose files:

```yaml
command: >
  postgres
  -c shared_preload_libraries='pg_stat_statements'
  -c pg_stat_statements.track=all          # Track all queries (top-level and nested)
  -c pg_stat_statements.max=10000          # Track up to 10,000 different queries
  -c log_min_duration_statement=1000       # Log queries slower than 1 second
  -c log_statement=none                    # Don't log all statements (too verbose)
  -c log_line_prefix='%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

### Customization

Adjust these settings based on your needs:

- **log_min_duration_statement**: Lower to catch faster slow queries (e.g., 500ms)
- **pg_stat_statements.max**: Increase if tracking more than 10,000 unique queries
- **pg_stat_statements.track**: Options are `none`, `top`, or `all`

## Usage

### Python API

Use the utility functions from `src.db.performance_monitoring`:

```python
from src.db import get_db, get_slow_queries, get_database_statistics

async with get_db() as db:
    # Get slow queries (averaging >1 second)
    slow = await get_slow_queries(db, min_duration_ms=1000)
    for query_info in slow:
        print(f"Query: {query_info['query'][:100]}...")
        print(f"Avg time: {query_info['avg_time_ms']:.2f}ms")
        print(f"Calls: {query_info['calls']}")
        print(f"Cache hit ratio: {query_info['cache_hit_ratio']:.1f}%")
        print()

    # Get overall statistics
    stats = await get_database_statistics(db)
    print(f"Total queries tracked: {stats['total_queries']}")
    print(f"Overall cache hit ratio: {stats['cache_hit_ratio']:.1f}%")
```

### REST API Endpoints

Access monitoring data through the admin API:

```bash
# Get slow queries
curl http://localhost:8000/api/v1/admin/performance/slow-queries?min_duration_ms=500&limit=20

# Get top queries by total time
curl http://localhost:8000/api/v1/admin/performance/top-queries?limit=20

# Get queries with low cache hit ratio
curl http://localhost:8000/api/v1/admin/performance/low-cache-hit?max_cache_ratio=80

# Get overall database statistics
curl http://localhost:8000/api/v1/admin/performance/database-stats

# Get table access patterns
curl http://localhost:8000/api/v1/admin/performance/table-stats

# Get index usage statistics
curl http://localhost:8000/api/v1/admin/performance/index-usage
```

### Direct SQL Queries

Query the views directly:

```sql
-- Slow queries (averaging >1 second)
SELECT * FROM slow_queries LIMIT 10;

-- Queries consuming most total time
SELECT * FROM top_queries_by_total_time LIMIT 10;

-- Queries with poor cache hit ratios
SELECT * FROM queries_low_cache_hit LIMIT 10;

-- All statistics from pg_stat_statements
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

## Analyzing Performance Issues

### 1. Identify Slow Queries

Start by finding queries that are slow on average:

```python
slow = await get_slow_queries(db, min_duration_ms=500, limit=20)
```

Look for:
- High `avg_time_ms` or `max_time_ms` values
- Queries called frequently (`calls`) with moderate execution times
- Full table scans (check with EXPLAIN)

### 2. Find High-Impact Queries

Queries that consume the most total time have the biggest impact:

```python
top = await get_top_queries_by_total_time(db, limit=20)
```

These are prime candidates for optimization because they affect overall system performance the most.

### 3. Check Cache Hit Ratios

Low cache hit ratios indicate heavy disk I/O:

```python
low_cache = await get_queries_with_low_cache_hit(db, max_cache_ratio=90)
```

Solutions:
- Add appropriate indexes
- Increase `shared_buffers` in PostgreSQL config
- Optimize query to reduce data accessed
- Consider partitioning large tables

### 4. Analyze Table Access Patterns

Identify missing indexes:

```python
tables = await get_table_statistics(db)
for table in tables:
    if table['seq_scans'] > 1000 and table['seq_scans'] > table['idx_scans']:
        print(f"Table {table['table_name']} may need indexes")
        print(f"  Sequential scans: {table['seq_scans']}")
        print(f"  Index scans: {table['idx_scans']}")
```

### 5. Review Index Usage

Find unused indexes:

```python
indexes = await get_index_usage(db)
for idx in indexes:
    if idx['scans'] == 0:
        print(f"Unused index: {idx['index_name']} on {idx['table_name']}")
        print("  Consider dropping to improve write performance")
```

## Common Optimization Patterns

### Add Missing Indexes

If table scans dominate:

```sql
CREATE INDEX idx_company_ticker ON companies(ticker);
CREATE INDEX idx_filing_date ON sec_filings(filing_date);
```

### Optimize Queries

Use EXPLAIN ANALYZE to understand query plans:

```python
from src.db import get_query_plan

plan = await get_query_plan(
    db,
    "SELECT * FROM companies WHERE ticker = 'AAPL'",
    analyze=False  # Set to True to actually run the query
)
print(plan)
```

### Adjust PostgreSQL Configuration

For production workloads:

```yaml
-c shared_buffers=4GB              # Cache more data in memory
-c effective_cache_size=12GB       # Tell planner about system cache
-c work_mem=64MB                   # Memory for sorts/joins
-c maintenance_work_mem=1GB        # Memory for VACUUM/CREATE INDEX
```

## Monitoring Best Practices

### Regular Reviews

Schedule regular performance reviews:

1. **Daily**: Check for new slow queries
2. **Weekly**: Review top queries by total time
3. **Monthly**: Analyze table and index usage patterns

### Reset Statistics

After making optimizations, reset statistics to measure impact:

```python
from src.db import reset_query_statistics

await reset_query_statistics(db)
```

Then monitor the same queries to verify improvement.

### Set Alerts

Configure alerts for:
- Queries averaging >5 seconds
- Cache hit ratio <80%
- High number of sequential scans on large tables

### Log Analysis

PostgreSQL logs queries slower than 1 second. Review logs:

```bash
docker-compose logs postgres | grep "duration:"
```

## Troubleshooting

### Extension Not Found

If `pg_stat_statements` is not available:

1. Verify TimescaleDB image includes it (it does by default)
2. Check PostgreSQL version (requires 9.4+)
3. Restart PostgreSQL after adding to `shared_preload_libraries`

### No Statistics Collected

If `pg_stat_statements` shows no data:

1. Verify extension is created: `SELECT * FROM pg_stat_statements;`
2. Check configuration: `SHOW shared_preload_libraries;`
3. Restart PostgreSQL if you just enabled it
4. Run some queries to populate statistics

### Views Not Found

If helper views don't exist:

```bash
docker-compose exec api alembic current
docker-compose exec api alembic upgrade head
```

## Performance Impact

The monitoring has minimal overhead:

- CPU: <1% additional CPU usage
- Memory: ~10-20MB for tracking 10,000 queries
- I/O: Negligible (statistics are in memory)

Safe for production use.

## References

- [PostgreSQL pg_stat_statements Documentation](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [TimescaleDB Performance Tuning](https://docs.timescale.com/timescaledb/latest/how-to-guides/configuration/about-configuration/)
- [PostgreSQL Performance Optimization](https://wiki.postgresql.org/wiki/Performance_Optimization)
