# Multi-stage production Dockerfile for Corporate Intelligence Platform
# Optimized for security, size, and performance

# ============================================================================
# Stage 1: Python dependencies builder
# ============================================================================
FROM python:3.11-slim as python-builder

# Metadata
LABEL stage=builder \
      description="Python dependencies builder stage"

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    cmake \
    curl \
    git \
    postgresql-client \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set build-time environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using pip (since we have pyproject.toml)
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    gunicorn>=21.2.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    sqlalchemy>=2.0.0 \
    asyncpg>=0.29.0 \
    psycopg2-binary>=2.9.0 \
    alembic>=1.12.0 \
    pgvector>=0.2.4 \
    pandas>=2.1.0 \
    numpy>=1.24.0 \
    redis>=5.0.0 \
    aiocache[redis]>=0.12.0 \
    minio>=7.2.0 \
    opentelemetry-api>=1.21.0 \
    opentelemetry-sdk>=1.21.0 \
    opentelemetry-instrumentation-fastapi>=0.42b0 \
    prometheus-client>=0.19.0 \
    loguru>=0.7.0 \
    sentry-sdk[fastapi]>=1.39.0 \
    pypdf>=3.17.0 \
    pdfplumber>=0.10.0 \
    python-docx>=1.1.0 \
    beautifulsoup4>=4.12.0 \
    yfinance>=0.2.33 \
    plotly>=5.18.0 \
    dash>=2.14.0 \
    httpx>=0.25.0 \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    pytest-cov>=4.1.0

# ============================================================================
# Stage 2: Final production image
# ============================================================================
FROM python:3.11-slim

# Metadata
LABEL maintainer="brandon.lambert87@gmail.com" \
      version="1.0.0" \
      description="Corporate Intelligence Platform - Production Image" \
      org.opencontainers.image.source="https://github.com/brandonjplambert/corporate-intel"

# Create non-root user for security
RUN groupadd -r appuser --gid 1000 && \
    useradd -r -g appuser --uid 1000 --home-dir /app appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/usr/local/bin:$PATH" \
    ENVIRONMENT=production \
    # Security headers
    PYTHONHASHSEED=random \
    # Disable Python buffering for better logging
    PYTHONIOENCODING=UTF-8

# Create app directory structure
WORKDIR /app

# Copy Python packages from builder
COPY --from=python-builder /install /usr/local

# Copy application code with proper ownership
COPY --chown=appuser:appuser ./src ./src
COPY --chown=appuser:appuser ./dbt ./dbt
COPY --chown=appuser:appuser ./alembic ./alembic
COPY --chown=appuser:appuser ./alembic.ini ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/cache /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Health check with proper endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Production server command with optimized workers
# Workers = (2 x CPU cores) + 1, adjust based on your infrastructure
CMD ["gunicorn", "src.api.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--worker-tmp-dir", "/dev/shm"]