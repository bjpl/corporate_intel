"""Enable PostgreSQL query performance monitoring

Revision ID: 003
Revises: 002
Create Date: 2025-11-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pg_stat_statements extension for query performance monitoring."""

    # ====================
    # 1. ENABLE pg_stat_statements EXTENSION
    # ====================

    # Enable pg_stat_statements for query performance tracking
    # NOTE: This requires shared_preload_libraries='pg_stat_statements' in postgresql.conf
    # See docker-compose.yml for the PostgreSQL configuration
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_stat_statements')

    # ====================
    # 2. CREATE VIEW FOR EASY QUERY ANALYSIS
    # ====================

    # Create a view to simplify access to slow queries
    op.execute("""
        CREATE OR REPLACE VIEW slow_queries AS
        SELECT
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            max_exec_time,
            min_exec_time,
            stddev_exec_time,
            rows,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
        FROM pg_stat_statements
        WHERE mean_exec_time > 1000  -- Queries averaging > 1 second
        ORDER BY mean_exec_time DESC
        LIMIT 100
    """)

    # Create a view for queries by total time (high impact queries)
    op.execute("""
        CREATE OR REPLACE VIEW top_queries_by_total_time AS
        SELECT
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            max_exec_time,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
        FROM pg_stat_statements
        ORDER BY total_exec_time DESC
        LIMIT 50
    """)

    # Create a view for queries with low cache hit ratio
    op.execute("""
        CREATE OR REPLACE VIEW queries_low_cache_hit AS
        SELECT
            query,
            calls,
            mean_exec_time,
            shared_blks_hit,
            shared_blks_read,
            100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
        FROM pg_stat_statements
        WHERE shared_blks_read > 0
        ORDER BY cache_hit_ratio ASC
        LIMIT 50
    """)

    print("✅ Query performance monitoring enabled successfully")
    print("   - pg_stat_statements extension created")
    print("   - Slow query tracking views created")
    print("   - Configure PostgreSQL with shared_preload_libraries='pg_stat_statements'")


def downgrade() -> None:
    """Disable query performance monitoring."""

    # Drop views
    op.execute('DROP VIEW IF EXISTS queries_low_cache_hit')
    op.execute('DROP VIEW IF EXISTS top_queries_by_total_time')
    op.execute('DROP VIEW IF EXISTS slow_queries')

    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS pg_stat_statements')

    print("✅ Query performance monitoring disabled successfully")
