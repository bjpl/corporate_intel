"""Health check and system status DTOs for API endpoints.

This module provides DTOs for health monitoring and system status:
- Basic health checks
- Detailed component health
- Platform metrics
- Readiness and liveness probes
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from src.dto.base import BaseDTO


class HealthDTO(BaseDTO):
    """Basic health check response DTO.

    Lightweight health status for quick checks and load balancer probes.
    """

    status: str = Field(
        ...,
        pattern="^(healthy|degraded|unhealthy)$",
        description="Overall system health status"
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp when health check was performed"
    )
    version: str = Field(
        ...,
        description="API version"
    )
    environment: str = Field(
        ...,
        description="Deployment environment (production, staging, development)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2025-11-20T10:00:00Z",
                "version": "0.1.0",
                "environment": "production"
            }
        }
    }


class ComponentHealthDTO(BaseDTO):
    """Health status for individual system components.

    Provides detailed health information for each component.
    """

    status: str = Field(
        ...,
        pattern="^(healthy|degraded|unhealthy)$",
        description="Component health status"
    )
    response_time_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Component response time in milliseconds"
    )
    message: Optional[str] = Field(
        None,
        description="Additional status message or error details"
    )
    last_check: Optional[datetime] = Field(
        None,
        description="When the component was last checked"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional component-specific details"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "response_time_ms": 15.3,
                "message": "Database connection successful",
                "last_check": "2025-11-20T10:00:00Z",
                "details": {
                    "pool_size": 10,
                    "active_connections": 3,
                    "idle_connections": 7
                }
            }
        }
    }


class PlatformMetricsDTO(BaseDTO):
    """Platform-wide metrics and statistics.

    Provides insights into data volume and system activity.
    """

    companies_tracked: int = Field(
        ...,
        ge=0,
        description="Total number of companies being tracked"
    )
    total_metrics: int = Field(
        ...,
        ge=0,
        description="Total number of metrics in the system"
    )
    total_filings: Optional[int] = Field(
        None,
        ge=0,
        description="Total number of SEC filings processed"
    )
    total_intelligence: Optional[int] = Field(
        None,
        ge=0,
        description="Total number of intelligence items"
    )
    last_ingestion: Optional[datetime] = Field(
        None,
        description="Timestamp of last data ingestion"
    )
    data_warehouse: Optional[Dict[str, Any]] = Field(
        None,
        description="Data warehouse statistics"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "companies_tracked": 27,
                "total_metrics": 1500,
                "total_filings": 324,
                "total_intelligence": 156,
                "last_ingestion": "2025-11-20T09:00:00Z",
                "data_warehouse": {
                    "companies": 27,
                    "last_refresh": "2025-11-20T08:00:00Z",
                    "freshness_hours": 2
                }
            }
        }
    }


class DetailedHealthDTO(BaseDTO):
    """Comprehensive health check with all system components.

    Includes detailed status of all components and platform metrics.
    """

    status: str = Field(
        ...,
        pattern="^(healthy|degraded|unhealthy)$",
        description="Overall system health status"
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp when health check was performed"
    )
    version: str = Field(
        ...,
        description="API version"
    )
    environment: str = Field(
        ...,
        description="Deployment environment"
    )
    components: Dict[str, ComponentHealthDTO] = Field(
        ...,
        description="Health status of individual components"
    )
    metrics: PlatformMetricsDTO = Field(
        ...,
        description="Platform-wide metrics and statistics"
    )
    uptime_seconds: Optional[float] = Field(
        None,
        ge=0,
        description="Application uptime in seconds"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2025-11-20T10:00:00Z",
                "version": "0.1.0",
                "environment": "production",
                "components": {
                    "database": {
                        "status": "healthy",
                        "response_time_ms": 15.3,
                        "message": "Connected"
                    },
                    "cache": {
                        "status": "healthy",
                        "response_time_ms": 2.1,
                        "message": "Redis operational"
                    },
                    "storage": {
                        "status": "healthy",
                        "response_time_ms": 45.0,
                        "message": "MinIO accessible"
                    }
                },
                "metrics": {
                    "companies_tracked": 27,
                    "total_metrics": 1500,
                    "last_ingestion": "2025-11-20T09:00:00Z"
                },
                "uptime_seconds": 3600.0
            }
        }
    }


class ReadinessDTO(BaseDTO):
    """Kubernetes readiness probe response.

    Indicates whether the service is ready to accept traffic.
    """

    status: str = Field(
        ...,
        pattern="^(ready|not_ready)$",
        description="Service readiness status"
    )
    database: str = Field(
        ...,
        pattern="^(connected|disconnected)$",
        description="Database connection status"
    )
    response_time_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Database response time in milliseconds"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if not ready"
    )
    checks_passed: Optional[int] = Field(
        None,
        ge=0,
        description="Number of readiness checks passed"
    )
    checks_total: Optional[int] = Field(
        None,
        ge=0,
        description="Total number of readiness checks"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "ready",
                    "database": "connected",
                    "response_time_ms": 12.5,
                    "checks_passed": 3,
                    "checks_total": 3
                },
                {
                    "status": "not_ready",
                    "database": "disconnected",
                    "error": "Database connection timeout",
                    "checks_passed": 0,
                    "checks_total": 3
                }
            ]
        }
    }


class LivenessDTO(BaseDTO):
    """Kubernetes liveness probe response.

    Indicates whether the service is alive and should not be restarted.
    """

    status: str = Field(
        ...,
        pattern="^(alive|dead)$",
        description="Service liveness status"
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp of liveness check"
    )
    uptime_seconds: Optional[float] = Field(
        None,
        ge=0,
        description="Application uptime in seconds"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "alive",
                "timestamp": "2025-11-20T10:00:00Z",
                "uptime_seconds": 7200.0
            }
        }
    }


class PingDTO(BaseDTO):
    """Ultra-lightweight ping response for load balancers."""

    ping: str = Field(
        default="pong",
        description="Ping response"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ping": "pong"
            }
        }
    }


class ServiceInfoDTO(BaseDTO):
    """Detailed service information DTO.

    Provides comprehensive information about the service.
    """

    name: str = Field(
        ...,
        description="Service name"
    )
    version: str = Field(
        ...,
        description="Service version"
    )
    environment: str = Field(
        ...,
        description="Deployment environment"
    )
    build_time: Optional[datetime] = Field(
        None,
        description="When the service was built"
    )
    git_commit: Optional[str] = Field(
        None,
        description="Git commit SHA"
    )
    python_version: Optional[str] = Field(
        None,
        description="Python runtime version"
    )
    dependencies: Optional[Dict[str, str]] = Field(
        None,
        description="Key dependencies and versions"
    )
    features: Optional[Dict[str, bool]] = Field(
        None,
        description="Feature flags and capabilities"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "corporate-intel-api",
                "version": "0.1.0",
                "environment": "production",
                "build_time": "2025-11-20T00:00:00Z",
                "git_commit": "abc123def456",
                "python_version": "3.11.5",
                "dependencies": {
                    "fastapi": "0.104.1",
                    "sqlalchemy": "2.0.23",
                    "pydantic": "2.5.0"
                },
                "features": {
                    "caching": True,
                    "vector_search": True,
                    "real_time_updates": False
                }
            }
        }
    }
