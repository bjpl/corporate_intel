# Quick Start: PostgreSQL Query Performance Monitoring

## 5-Minute Setup

### 1. Apply Migration

```bash
# Development
docker-compose exec api alembic upgrade head

# Production
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 2. Restart PostgreSQL

```bash
# Development
docker-compose restart postgres

# Production
docker-compose -f docker-compose.prod.yml restart postgres
```

### 3. Verify Installation

```bash
docker-compose exec postgres psql -U intel_user -d corporate_intel -c "SELECT COUNT(*) FROM pg_stat_statements;"
```

You should see a number (0 or more) indicating the extension is working.

## Common Use Cases

### Find Slow Queries

**Python:**
```python
from src.db import get_db, get_slow_queries

async with get_db() as db:
    slow = await get_slow_queries(db, min_duration_ms=1000)
    for q in slow[:5]:
        print(f"{q['query'][:80]}... - {q['avg_time_ms']:.0f}ms avg")
```

**REST API:**
```bash
curl "http://localhost:8000/api/v1/admin/performance/slow-queries?min_duration_ms=1000&limit=10"
```

**SQL:**
```sql
SELECT * FROM slow_queries LIMIT 10;
```

### Identify High-Impact Queries

**Python:**
```python
from src.db import get_db, get_top_queries_by_total_time

async with get_db() as db:
    top = await get_top_queries_by_total_time(db, limit=10)
    for q in top:
        total_sec = q['total_time_ms'] / 1000
        print(f"Total: {total_sec:.1f}s, Calls: {q['calls']}, Avg: {q['avg_time_ms']:.0f}ms")
```

**REST API:**
```bash
curl "http://localhost:8000/api/v1/admin/performance/top-queries?limit=10"
```

### Check Cache Efficiency

**Python:**
```python
from src.db import get_db, get_queries_with_low_cache_hit

async with get_db() as db:
    low_cache = await get_queries_with_low_cache_hit(db, max_cache_ratio=90)
    for q in low_cache[:5]:
        print(f"Cache hit: {q['cache_hit_ratio']:.1f}% - {q['query'][:80]}...")
```

**REST API:**
```bash
curl "http://localhost:8000/api/v1/admin/performance/low-cache-hit?max_cache_ratio=90"
```

### Get Overall Statistics

**Python:**
```python
from src.db import get_db, get_database_statistics

async with get_db() as db:
    stats = await get_database_statistics(db)
    print(f"Total queries: {stats['total_queries']}")
    print(f"Cache hit ratio: {stats['cache_hit_ratio']:.1f}%")
```

**REST API:**
```bash
curl "http://localhost:8000/api/v1/admin/performance/database-stats"
```

## Example Analysis Script

Run the provided example:

```bash
docker-compose exec api python /app/docs/examples/query_performance_example.py
```

This will show:
- Overall database statistics
- Slow queries (>1 second)
- High-impact queries
- Cache efficiency issues
- Table access patterns
- Index usage analysis

## Troubleshooting

### "Extension does not exist"

```bash
# Verify migration was applied
docker-compose exec api alembic current

# Should show: 003 (head)
# If not, run: docker-compose exec api alembic upgrade head
```

### "No data in pg_stat_statements"

```bash
# Check if extension is loaded
docker-compose exec postgres psql -U intel_user -d corporate_intel -c "SHOW shared_preload_libraries;"

# Should include: pg_stat_statements
# If not, restart PostgreSQL: docker-compose restart postgres
```

### "Permission denied"

The monitoring views and functions require database access. Ensure your database user has SELECT permission on `pg_stat_statements`.

## Next Steps

- Read full documentation: `/docs/performance-monitoring.md`
- Review example code: `/docs/examples/query_performance_example.py`
- Set up regular monitoring (daily/weekly)
- Configure alerts for slow queries
- Integrate with Grafana (optional)

## Quick Reference

### Python Functions

```python
from src.db import (
    get_slow_queries,              # Slow query analysis
    get_top_queries_by_total_time, # High-impact queries
    get_queries_with_low_cache_hit,# Cache efficiency
    get_database_statistics,        # Overall stats
    get_table_statistics,           # Table access patterns
    get_index_usage,                # Index utilization
    get_query_plan,                 # EXPLAIN a query
    reset_query_statistics,         # Reset tracking
)
```

### REST Endpoints

- `/admin/performance/slow-queries` - Slow queries
- `/admin/performance/top-queries` - High-impact queries
- `/admin/performance/low-cache-hit` - Cache issues
- `/admin/performance/database-stats` - Overall stats
- `/admin/performance/table-stats` - Table patterns
- `/admin/performance/index-usage` - Index analysis

### SQL Views

- `slow_queries` - Queries averaging >1s
- `top_queries_by_total_time` - Highest total time
- `queries_low_cache_hit` - Poor cache efficiency

### Configuration

Edit `docker-compose.yml` or `docker-compose.prod.yml`:

```yaml
command: >
  postgres
  -c log_min_duration_statement=500  # Log queries >500ms
  -c pg_stat_statements.max=20000    # Track 20k queries
```

Then restart: `docker-compose restart postgres`
