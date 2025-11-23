@echo off
REM Corporate Intel Platform - Docker Services Startup Script
REM This script starts all required Docker services for development

echo =========================================
echo Corporate Intel Platform
echo Docker Services Startup
echo =========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running!
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

echo Starting infrastructure services...
echo - PostgreSQL (TimescaleDB + pgvector)
echo - Redis
echo - MinIO
echo.

REM Start infrastructure services
docker-compose up -d postgres redis minio

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start infrastructure services!
    pause
    exit /b 1
)

echo.
echo Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo Checking service health...
docker-compose ps

echo.
echo =========================================
echo Services Started Successfully!
echo =========================================
echo.
echo PostgreSQL: localhost:5434
echo Redis: localhost:6381
echo MinIO: http://localhost:9002
echo.
echo Next steps:
echo 1. Verify database: docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel
echo 2. Run data ingestion: python -m src.pipeline.yahoo_finance_ingestion
echo 3. Run dbt models: cd dbt ^&^& dbt run --profiles-dir .
echo 4. Start dashboard: python -m src.visualization.dash_app
echo.
pause
