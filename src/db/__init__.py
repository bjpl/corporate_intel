"""Database models and utilities."""

from src.db.performance_monitoring import (
    get_database_statistics,
    get_index_usage,
    get_queries_with_low_cache_hit,
    get_query_plan,
    get_slow_queries,
    get_table_statistics,
    get_top_queries_by_total_time,
    reset_query_statistics,
)
from src.db.session import close_db_connections, get_db, get_async_engine

__all__ = [
    # Session management
    "get_db",
    "get_async_engine",
    "close_db_connections",
    # Performance monitoring
    "get_slow_queries",
    "get_top_queries_by_total_time",
    "get_queries_with_low_cache_hit",
    "get_database_statistics",
    "get_table_statistics",
    "get_index_usage",
    "get_query_plan",
    "reset_query_statistics",
]
