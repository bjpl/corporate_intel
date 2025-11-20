"""Admin and database monitoring DTOs for API endpoints.

This module provides DTOs for administrative and monitoring endpoints:
- Database performance statistics
- Query performance metrics
- Table and index usage statistics
- System health monitoring
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.dto.base import BaseDTO


class QueryPerformanceDTO(BaseDTO):
    """DTO for query performance statistics.

    Used to report slow queries and execution metrics from pg_stat_statements.
    """

    query: str = Field(
        ...,
        description="SQL query text (may be truncated or normalized)"
    )
    calls: int = Field(
        ...,
        ge=0,
        description="Number of times the query was executed"
    )
    total_time_ms: float = Field(
        ...,
        ge=0,
        description="Total execution time in milliseconds"
    )
    avg_time_ms: float = Field(
        ...,
        ge=0,
        description="Average execution time in milliseconds"
    )
    max_time_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum execution time in milliseconds"
    )
    min_time_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum execution time in milliseconds"
    )
    stddev_time_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Standard deviation of execution time"
    )
    cache_hit_ratio: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Cache hit ratio percentage (0-100)"
    )
    shared_blks_hit: Optional[int] = Field(
        None,
        ge=0,
        description="Number of shared blocks hit in cache"
    )
    shared_blks_read: Optional[int] = Field(
        None,
        ge=0,
        description="Number of shared blocks read from disk"
    )
    rows_returned: Optional[int] = Field(
        None,
        ge=0,
        description="Total number of rows returned by query"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "SELECT * FROM companies WHERE category = $1",
                "calls": 1523,
                "total_time_ms": 45230.5,
                "avg_time_ms": 29.7,
                "max_time_ms": 156.2,
                "min_time_ms": 12.3,
                "stddev_time_ms": 18.4,
                "cache_hit_ratio": 94.5,
                "shared_blks_hit": 12340,
                "shared_blks_read": 720,
                "rows_returned": 15230
            }
        }
    }


class DatabaseStatsDTO(BaseDTO):
    """DTO for overall database statistics.

    Provides high-level database performance metrics.
    """

    total_queries: int = Field(
        ...,
        ge=0,
        description="Total number of unique queries tracked"
    )
    total_calls: int = Field(
        ...,
        ge=0,
        description="Total number of query executions"
    )
    total_time_ms: float = Field(
        ...,
        ge=0,
        description="Total execution time across all queries (ms)"
    )
    avg_time_ms: float = Field(
        ...,
        ge=0,
        description="Average query execution time (ms)"
    )
    cache_hit_ratio: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Overall cache hit ratio percentage"
    )
    database_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="Total database size in bytes"
    )
    connections_active: Optional[int] = Field(
        None,
        ge=0,
        description="Number of active database connections"
    )
    connections_max: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum allowed database connections"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_queries": 156,
                "total_calls": 45230,
                "total_time_ms": 1234567.8,
                "avg_time_ms": 27.3,
                "cache_hit_ratio": 92.5,
                "database_size_bytes": 5368709120,
                "connections_active": 12,
                "connections_max": 100
            }
        }
    }


class TableStatsDTO(BaseDTO):
    """DTO for table access statistics.

    Shows how tables are being accessed and modified.
    """

    table_name: str = Field(
        ...,
        description="Full table name (schema.table)"
    )
    seq_scans: int = Field(
        ...,
        ge=0,
        description="Number of sequential scans performed"
    )
    seq_rows_read: int = Field(
        ...,
        ge=0,
        description="Number of rows read via sequential scans"
    )
    idx_scans: Optional[int] = Field(
        None,
        ge=0,
        description="Number of index scans performed"
    )
    idx_rows_fetched: Optional[int] = Field(
        None,
        ge=0,
        description="Number of rows fetched via index scans"
    )
    inserts: int = Field(
        ...,
        ge=0,
        description="Number of insert operations"
    )
    updates: int = Field(
        ...,
        ge=0,
        description="Number of update operations"
    )
    deletes: int = Field(
        ...,
        ge=0,
        description="Number of delete operations"
    )
    live_rows: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated number of live rows"
    )
    dead_rows: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated number of dead rows (needs vacuuming)"
    )
    table_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="Table size in bytes"
    )
    index_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="Total index size in bytes"
    )
    last_vacuum: Optional[str] = Field(
        None,
        description="Timestamp of last vacuum operation"
    )
    last_analyze: Optional[str] = Field(
        None,
        description="Timestamp of last analyze operation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "table_name": "public.companies",
                "seq_scans": 1234,
                "seq_rows_read": 456789,
                "idx_scans": 5678,
                "idx_rows_fetched": 234567,
                "inserts": 100,
                "updates": 50,
                "deletes": 5,
                "live_rows": 1500,
                "dead_rows": 23,
                "table_size_bytes": 524288,
                "index_size_bytes": 262144,
                "last_vacuum": "2025-11-20T02:00:00Z",
                "last_analyze": "2025-11-20T02:15:00Z"
            }
        }
    }


class IndexUsageDTO(BaseDTO):
    """DTO for index usage statistics.

    Shows index utilization patterns to identify unused indexes.
    """

    table_name: str = Field(
        ...,
        description="Table name the index belongs to"
    )
    index_name: str = Field(
        ...,
        description="Index name"
    )
    scans: int = Field(
        ...,
        ge=0,
        description="Number of index scans performed"
    )
    rows_read: Optional[int] = Field(
        None,
        ge=0,
        description="Number of index entries read"
    )
    rows_fetched: Optional[int] = Field(
        None,
        ge=0,
        description="Number of live table rows fetched"
    )
    index_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="Index size in bytes"
    )
    is_unique: Optional[bool] = Field(
        None,
        description="Whether the index enforces uniqueness"
    )
    is_primary: Optional[bool] = Field(
        None,
        description="Whether this is the primary key index"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "table_name": "public.financial_metrics",
                "index_name": "idx_metric_time",
                "scans": 5234,
                "rows_read": 123456,
                "rows_fetched": 98765,
                "index_size_bytes": 1048576,
                "is_unique": False,
                "is_primary": False
            }
        }
    }


class SlowQueryListDTO(BaseDTO):
    """Response DTO for slow queries endpoint."""

    queries: List[QueryPerformanceDTO] = Field(
        ...,
        description="List of slow queries"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of slow queries found"
    )
    min_duration_ms: float = Field(
        ...,
        ge=0,
        description="Minimum duration threshold used"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "queries": [
                    {
                        "query": "SELECT * FROM companies WHERE category = $1",
                        "calls": 1523,
                        "total_time_ms": 45230.5,
                        "avg_time_ms": 29.7,
                        "cache_hit_ratio": 94.5
                    }
                ],
                "total": 12,
                "min_duration_ms": 1000
            }
        }
    }


class TableStatsListDTO(BaseDTO):
    """Response DTO for table statistics endpoint."""

    tables: List[TableStatsDTO] = Field(
        ...,
        description="List of table statistics"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of tables"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tables": [
                    {
                        "table_name": "public.companies",
                        "seq_scans": 1234,
                        "idx_scans": 5678,
                        "inserts": 100,
                        "updates": 50,
                        "deletes": 5
                    }
                ],
                "total": 10
            }
        }
    }


class IndexUsageListDTO(BaseDTO):
    """Response DTO for index usage endpoint."""

    indexes: List[IndexUsageDTO] = Field(
        ...,
        description="List of index usage statistics"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of indexes"
    )
    unused_indexes: int = Field(
        ...,
        ge=0,
        description="Number of indexes with zero scans"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "indexes": [
                    {
                        "table_name": "public.financial_metrics",
                        "index_name": "idx_metric_time",
                        "scans": 5234
                    }
                ],
                "total": 25,
                "unused_indexes": 3
            }
        }
    }


class PerformanceRecommendationDTO(BaseDTO):
    """DTO for performance optimization recommendations.

    Provides actionable recommendations based on performance analysis.
    """

    category: str = Field(
        ...,
        description="Recommendation category (index, query, configuration, vacuum)",
        examples=["index", "query", "configuration"]
    )
    severity: str = Field(
        ...,
        pattern="^(low|medium|high|critical)$",
        description="Severity level of the issue"
    )
    title: str = Field(
        ...,
        description="Recommendation title"
    )
    description: str = Field(
        ...,
        description="Detailed description of the issue"
    )
    action: str = Field(
        ...,
        description="Recommended action to take"
    )
    affected_objects: Optional[List[str]] = Field(
        None,
        description="List of affected tables, indexes, or queries"
    )
    estimated_impact: Optional[str] = Field(
        None,
        description="Estimated performance impact if implemented"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "index",
                "severity": "high",
                "title": "Missing index on frequently queried column",
                "description": "The companies.category column is frequently used in WHERE clauses but lacks an index",
                "action": "CREATE INDEX idx_company_category ON companies(category);",
                "affected_objects": ["public.companies"],
                "estimated_impact": "30-50% reduction in query time for category filters"
            }
        }
    }
