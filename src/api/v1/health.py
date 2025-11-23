"""Health check and system status endpoints for monitoring and observability."""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session
from loguru import logger

from src.core.config import get_settings
from src.db.base import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    environment: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "healthy",
            "timestamp": "2025-10-08T10:00:00Z",
            "version": "0.1.0",
            "environment": "production"
        }
    })


class DetailedHealthResponse(BaseModel):
    """Detailed health check with component status."""

    status: str
    timestamp: datetime
    version: str
    environment: str
    components: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "healthy",
            "timestamp": "2025-10-08T10:00:00Z",
            "version": "0.1.0",
            "environment": "production",
            "components": {
                "database": {"status": "healthy", "response_time_ms": 15},
                "cache": {"status": "healthy", "response_time_ms": 2}
            },
            "metrics": {
                "companies_tracked": 27,
                "total_metrics": 1500,
                "last_ingestion": "2025-10-08T09:00:00Z"
            }
        }
    })


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns a simple status indicating the API is running.
    This endpoint does not check dependencies (database, cache, etc.).
    Use /health/detailed for comprehensive health checks.
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.ENVIRONMENT,
    )


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """Ultra-lightweight ping endpoint for load balancers.

    Returns immediately without any processing.
    Ideal for Kubernetes liveness probes or ALB health checks.
    """
    return {"ping": "pong"}


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db: Session = Depends(get_db),
) -> DetailedHealthResponse:
    """Comprehensive health check including all system components.

    Checks:
    - API server status
    - Database connectivity and performance
    - Data freshness and metrics
    - Cache availability (future)

    This endpoint is more expensive than /health and should be called
    less frequently (e.g., every 30s instead of every 5s).
    """
    settings = get_settings()
    components = {}
    metrics = {}
    overall_status = "healthy"

    # Check database
    db_status, db_time = await _check_database(db)
    components["database"] = {
        "status": db_status,
        "response_time_ms": db_time,
    }

    if db_status != "healthy":
        overall_status = "degraded"

    # Get platform metrics if database is healthy
    if db_status == "healthy":
        try:
            platform_metrics = await _get_platform_metrics(db)
            metrics.update(platform_metrics)
        except Exception as e:
            logger.warning(f"Failed to get platform metrics: {e}")
            metrics["error"] = "Failed to retrieve metrics"

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        components=components,
        metrics=metrics,
    )


@router.get("/readiness")
async def readiness_check(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if the service is not ready (e.g., database unavailable).

    This is different from liveness - a service can be alive but not ready.
    """
    db_status, db_time = await _check_database(db)

    if db_status == "healthy":
        return {
            "status": "ready",
            "database": "connected",
            "response_time_ms": db_time,
        }
    else:
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": "Database connection failed",
        }, status.HTTP_503_SERVICE_UNAVAILABLE


async def _check_database(db: Session) -> tuple[str, float]:
    """Check database connectivity and measure response time.

    Returns:
        Tuple of (status, response_time_ms)
    """
    try:
        start_time = datetime.utcnow()

        # Simple query to test connection
        result = db.execute(text("SELECT 1"))
        result.fetchone()

        end_time = datetime.utcnow()
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        return "healthy", round(response_time_ms, 2)

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "unhealthy", 0.0


async def _get_platform_metrics(db: Session) -> Dict[str, Any]:
    """Get platform-wide metrics from the database.

    Returns:
        Dictionary of platform metrics
    """
    try:
        # Query company count
        company_result = db.execute(
            text("SELECT COUNT(*) FROM public.companies")
        )
        companies_count = company_result.scalar()

        # Query metrics count
        metrics_result = db.execute(
            text("SELECT COUNT(*) FROM public.financial_metrics")
        )
        metrics_count = metrics_result.scalar()

        # Query last ingestion time
        last_ingestion_result = db.execute(
            text("""
                SELECT MAX(created_at)
                FROM public.financial_metrics
            """)
        )
        last_ingestion = last_ingestion_result.scalar()

        # Query data warehouse freshness
        mart_result = db.execute(
            text("""
                SELECT
                    COUNT(DISTINCT ticker) as companies_in_mart,
                    MAX(refreshed_at) as last_mart_refresh
                FROM public_marts.mart_company_performance
            """)
        )
        mart_row = mart_result.fetchone()

        return {
            "companies_tracked": companies_count or 0,
            "total_metrics": metrics_count or 0,
            "last_ingestion": last_ingestion.isoformat() if last_ingestion else None,
            "data_warehouse": {
                "companies": mart_row[0] if mart_row else 0,
                "last_refresh": mart_row[1].isoformat() if mart_row and mart_row[1] else None,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get platform metrics: {e}", exc_info=True)
        return {
            "error": "Failed to retrieve metrics",
            "companies_tracked": 0,
            "total_metrics": 0,
        }
