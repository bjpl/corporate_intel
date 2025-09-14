"""FastAPI application for Corporate Intelligence Platform."""

from contextlib import asynccontextmanager
from typing import Any, Dict

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import make_asgi_app
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from src.api.v1 import companies, filings, intelligence, metrics, reports
from src.core.config import get_settings
from src.core.exceptions import CorporateIntelException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Corporate Intelligence Platform API")
    
    # Initialize observability
    setup_observability()
    
    # Initialize database connection pool
    # await init_database()
    
    # Initialize Redis cache
    # await init_cache()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Corporate Intelligence Platform API")
    # await close_database()
    # await close_cache()


def setup_observability():
    """Configure observability stack."""
    settings = get_settings()
    
    # Sentry for error tracking
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized")
    
    # OpenTelemetry for distributed tracing
    if settings.OTEL_TRACES_ENABLED:
        resource = Resource.create(
            {
                "service.name": settings.OTEL_SERVICE_NAME,
                "service.version": settings.APP_VERSION,
                "deployment.environment": settings.ENVIRONMENT,
            }
        )
        
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        logger.info("OpenTelemetry tracing initialized")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    @app.exception_handler(CorporateIntelException)
    async def corporate_intel_exception_handler(request: Request, exc: CorporateIntelException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": exc.error_code},
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )
    
    # Health check
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    
    # Mount Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    # Include API routers
    app.include_router(
        companies.router,
        prefix=f"{settings.API_V1_PREFIX}/companies",
        tags=["companies"],
    )
    app.include_router(
        filings.router,
        prefix=f"{settings.API_V1_PREFIX}/filings",
        tags=["filings"],
    )
    app.include_router(
        metrics.router,
        prefix=f"{settings.API_V1_PREFIX}/metrics",
        tags=["metrics"],
    )
    app.include_router(
        intelligence.router,
        prefix=f"{settings.API_V1_PREFIX}/intelligence",
        tags=["intelligence"],
    )
    app.include_router(
        reports.router,
        prefix=f"{settings.API_V1_PREFIX}/reports",
        tags=["reports"],
    )
    
    # Instrument with OpenTelemetry
    if settings.OTEL_TRACES_ENABLED:
        FastAPIInstrumentor.instrument_app(app)
    
    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )