#!/bin/bash
# Resume Corporate Intel Startup After Docker Restart
# Run this after Docker Desktop is running

set -e

echo "🔄 Corporate Intel - Resume Startup"
echo "===================================="
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check infrastructure status
echo "📊 Checking infrastructure services..."
docker-compose ps

echo ""
echo "🔧 Restarting infrastructure if needed..."
docker-compose up -d postgres redis minio

echo ""
echo "⏳ Waiting for services to be healthy (30 seconds)..."
sleep 30

echo ""
echo "🏗️  Building API Docker image..."
docker-compose build api

echo ""
echo "🗄️  Running database migrations..."
docker-compose run --rm api alembic upgrade head

echo ""
echo "🚀 Starting API on port 8002..."
docker-compose up -d api

echo ""
echo "⏳ Waiting for API to start (20 seconds)..."
sleep 20

echo ""
echo "🏥 Testing API health..."
if curl -f http://localhost:8002/health 2>/dev/null; then
    echo ""
    echo "✅ SUCCESS! API is running"
    curl http://localhost:8002/health | python -m json.tool 2>/dev/null || curl http://localhost:8002/health
else
    echo "⚠️  API health check failed, checking logs..."
    docker-compose logs --tail 50 api
fi

echo ""
echo "=========================================="
echo "📍 Access Points:"
echo "   API:          http://localhost:8002"
echo "   API Docs:     http://localhost:8002/api/v1/docs"
echo "   Postgres:     localhost:5434"
echo "   Redis:        localhost:6381"
echo "   MinIO:        http://localhost:9002 (console: 9003)"
echo ""
echo "🔍 Useful Commands:"
echo "   docker-compose ps           # Check status"
echo "   docker-compose logs -f api  # View API logs"
echo "   docker-compose down         # Stop all services"
echo ""
echo "📊 Both Projects Status:"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -E "colombia_intel|corporate-intel|NAMES"
