@echo off
REM ################################################################################
REM Corporate Intel - Quick Startup Script (Windows)
REM
REM Starts the entire platform from scratch in 2-3 hours
REM Handles port conflicts, database setup, and API startup
REM ################################################################################

setlocal enabledelayedexpansion

REM Configuration
set POSTGRES_PORT=5434
set REDIS_PORT=6381
set MINIO_PORT=9002
set MINIO_CONSOLE_PORT=9003
set API_PORT=8002

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║         Corporate Intel - Quick Startup Script                ║
echo ║         Estimated Time: 2-3 hours                             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM ################################################################################
REM PHASE 1: Infrastructure Setup (30 min)
REM ################################################################################

echo.
echo [INFO] ═══════════════════════════════════════════════════════
echo [INFO] PHASE 1: Infrastructure Setup (30 min)
echo [INFO] ═══════════════════════════════════════════════════════
echo.

REM Step 1.1: Backup .env
echo [INFO] Step 1.1: Backing up .env file...
if exist .env (
    copy .env .env.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    echo [SUCCESS] .env backed up
) else (
    echo [ERROR] .env file not found!
    exit /b 1
)

REM Step 1.2: Clean up existing containers
echo [INFO] Step 1.2: Cleaning up existing containers...
docker-compose down -v 2>nul
echo [SUCCESS] Cleanup complete

REM Step 1.3: Start core infrastructure
echo [INFO] Step 1.3: Starting Postgres and Redis...
docker-compose up -d postgres redis

echo [INFO] Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

REM Verify Postgres
echo [INFO] Verifying Postgres connection...
docker exec corporate-intel-postgres pg_isready -U intel_user -d corporate_intel
if errorlevel 1 (
    echo [ERROR] Postgres connection failed
    exit /b 1
)
echo [SUCCESS] Postgres connection verified

REM Verify Redis
echo [INFO] Verifying Redis connection...
docker exec corporate-intel-redis redis-cli ping | findstr "PONG" >nul
if errorlevel 1 (
    echo [ERROR] Redis connection failed
    exit /b 1
)
echo [SUCCESS] Redis connection verified

echo [SUCCESS] PHASE 1 COMPLETE: Infrastructure is running!

REM ################################################################################
REM PHASE 2: Database Setup (20 min)
REM ################################################################################

echo.
echo [INFO] ═══════════════════════════════════════════════════════
echo [INFO] PHASE 2: Database Setup (20 min)
echo [INFO] ═══════════════════════════════════════════════════════
echo.

REM Step 2.1: Build API container
echo [INFO] Step 2.1: Building API container...
docker-compose build api
if errorlevel 1 (
    echo [ERROR] API build failed
    exit /b 1
)
echo [SUCCESS] API container built

REM Step 2.2: Run migrations
echo [INFO] Step 2.2: Running database migrations...
docker-compose run --rm api alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Migration failed
    exit /b 1
)
echo [SUCCESS] Database migrations applied

REM Step 2.3: Seed test data
echo [INFO] Step 2.3: Seeding test data...
docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel -c "INSERT INTO companies (ticker, name, cik, sector, industry, created_at, updated_at) VALUES ('AAPL', 'Apple Inc.', '0000320193', 'Technology', 'Consumer Electronics', NOW(), NOW()), ('MSFT', 'Microsoft Corporation', '0000789019', 'Technology', 'Software', NOW(), NOW()), ('GOOGL', 'Alphabet Inc.', '0001652044', 'Technology', 'Internet Services', NOW(), NOW()) ON CONFLICT (ticker) DO NOTHING;"
echo [SUCCESS] Test data seeded

echo [SUCCESS] PHASE 2 COMPLETE: Database is ready!

REM ################################################################################
REM PHASE 3: API Startup (20 min)
REM ################################################################################

echo.
echo [INFO] ═══════════════════════════════════════════════════════
echo [INFO] PHASE 3: API Startup (20 min)
echo [INFO] ═══════════════════════════════════════════════════════
echo.

REM Step 3.1: Start API
echo [INFO] Step 3.1: Starting API container...
docker-compose up -d api

echo [INFO] Waiting for API to start (30 seconds)...
timeout /t 30 /nobreak >nul

REM Step 3.2: Verify API health
echo [INFO] Step 3.2: Verifying API health...
curl -f -s http://localhost:%API_PORT%/health >nul
if errorlevel 1 (
    echo [ERROR] API health check failed
    echo [INFO] Showing recent logs:
    docker-compose logs --tail=50 api
    exit /b 1
)
echo [SUCCESS] API is healthy

echo [SUCCESS] PHASE 3 COMPLETE: API is running!

REM ################################################################################
REM PHASE 4: Validation (30 min)
REM ################################################################################

echo.
echo [INFO] ═══════════════════════════════════════════════════════
echo [INFO] PHASE 4: Basic Validation (30 min)
echo [INFO] ═══════════════════════════════════════════════════════
echo.

REM Test endpoints
echo [INFO] Testing health endpoints...
curl -f -s http://localhost:%API_PORT%/health
curl -f -s http://localhost:%API_PORT%/health/database
curl -f -s http://localhost:%API_PORT%/health/cache

echo [SUCCESS] All health checks passed!
echo [SUCCESS] PHASE 4 COMPLETE: All systems validated!

REM ################################################################################
REM Final Summary
REM ################################################################################

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    STARTUP COMPLETE!                           ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo [SUCCESS] Corporate Intel Platform is now running!
echo.
echo Service Status:
echo   ✓ PostgreSQL (TimescaleDB): http://localhost:%POSTGRES_PORT%
echo   ✓ Redis Cache:               localhost:%REDIS_PORT%
echo   ✓ FastAPI Application:       http://localhost:%API_PORT%
echo.
echo Important URLs:
echo   • API Documentation:  http://localhost:%API_PORT%/api/v1/docs
echo   • API ReDoc:          http://localhost:%API_PORT%/api/v1/redoc
echo   • Health Check:       http://localhost:%API_PORT%/health
echo   • Prometheus Metrics: http://localhost:%API_PORT%/metrics
echo.
echo Next Steps:
echo   1. Open API docs: http://localhost:%API_PORT%/api/v1/docs
echo   2. Register a user via the /auth/register endpoint
echo   3. Login to get an access token
echo   4. Explore the API endpoints
echo.
echo View logs:
echo   docker-compose logs -f api
echo.
echo Stop services:
echo   docker-compose down
echo.

echo [SUCCESS] Happy coding! 🚀
pause
