@echo off
REM Resume Corporate Intel Startup After Docker Restart (Windows)
REM Run this after Docker Desktop is running

echo.
echo 🔄 Corporate Intel - Resume Startup
echo ====================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo ✅ Docker is running
echo.

echo 📊 Checking infrastructure services...
docker-compose ps

echo.
echo 🔧 Restarting infrastructure if needed...
docker-compose up -d postgres redis minio

echo.
echo ⏳ Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo 🏗️  Building API Docker image...
docker-compose build api

echo.
echo 🗄️  Running database migrations...
docker-compose run --rm api alembic upgrade head

echo.
echo 🚀 Starting API on port 8002...
docker-compose up -d api

echo.
echo ⏳ Waiting for API to start (20 seconds)...
timeout /t 20 /nobreak >nul

echo.
echo 🏥 Testing API health...
curl -f http://localhost:8002/health
if errorlevel 1 (
    echo ⚠️  API health check failed, checking logs...
    docker-compose logs --tail 50 api
) else (
    echo.
    echo ✅ SUCCESS! API is running
)

echo.
echo ==========================================
echo 📍 Access Points:
echo    API:          http://localhost:8002
echo    API Docs:     http://localhost:8002/api/v1/docs
echo    Postgres:     localhost:5434
echo    Redis:        localhost:6381
echo    MinIO:        http://localhost:9002 (console: 9003)
echo.
echo 🔍 Useful Commands:
echo    docker-compose ps           # Check status
echo    docker-compose logs -f api  # View API logs
echo    docker-compose down         # Stop all services
echo.
echo 📊 Service Status:
docker-compose ps

pause
