#!/bin/bash
# Corporate Intel - Path A Startup Script
# Stops conflicting containers and starts corporate_intel

set -e  # Exit on error

echo "🚀 Corporate Intel Platform - Quick Start (Path A)"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ====================================
# STEP 1: Check if colombia containers exist
# ====================================
echo -e "${YELLOW}Step 1: Checking for conflicting containers...${NC}"
COLOMBIA_CONTAINERS=$(docker ps -a --filter "name=colombia_intel" --format "{{.Names}}" | tr '\n' ' ')

if [ -z "$COLOMBIA_CONTAINERS" ]; then
    echo -e "${GREEN}✓ No conflicting containers found${NC}"
else
    echo -e "${YELLOW}Found colombia_intel containers: $COLOMBIA_CONTAINERS${NC}"
    read -p "Stop these containers? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stop $COLOMBIA_CONTAINERS
        echo -e "${GREEN}✓ Stopped colombia_intel containers${NC}"
    else
        echo -e "${RED}✗ Cannot proceed with ports in use${NC}"
        exit 1
    fi
fi

echo ""

# ====================================
# STEP 2: Start infrastructure
# ====================================
echo -e "${YELLOW}Step 2: Starting infrastructure (Postgres + Redis)...${NC}"
docker-compose up -d postgres redis

echo -e "${YELLOW}Waiting for services to be healthy (30 seconds)...${NC}"
sleep 10
echo -e "${YELLOW}20 seconds remaining...${NC}"
sleep 10
echo -e "${YELLOW}10 seconds remaining...${NC}"
sleep 10

# Check health
if docker ps --filter "name=corporate-intel-postgres" --filter "health=healthy" | grep -q postgres; then
    echo -e "${GREEN}✓ PostgreSQL is healthy${NC}"
else
    echo -e "${RED}⚠ PostgreSQL not healthy yet, continuing anyway...${NC}"
fi

if docker ps --filter "name=corporate-intel-redis" --filter "health=healthy" | grep -q redis; then
    echo -e "${GREEN}✓ Redis is healthy${NC}"
else
    echo -e "${RED}⚠ Redis not healthy yet, continuing anyway...${NC}"
fi

echo ""

# ====================================
# STEP 3: Build API
# ====================================
echo -e "${YELLOW}Step 3: Building API Docker image...${NC}"
docker-compose build api

echo -e "${GREEN}✓ API image built${NC}"
echo ""

# ====================================
# STEP 4: Run database migrations
# ====================================
echo -e "${YELLOW}Step 4: Running database migrations...${NC}"

# Check if init-db.sql exists
if [ -f "./scripts/init-db.sql" ]; then
    echo "Initializing database extensions..."
    docker exec corporate-intel-postgres psql -U intel_user -d corporate_intel < scripts/init-db.sql
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${YELLOW}⚠ init-db.sql not found, skipping...${NC}"
fi

# Run Alembic migrations
echo "Running Alembic migrations..."
docker-compose run --rm api alembic upgrade head
echo -e "${GREEN}✓ Migrations complete${NC}"

echo ""

# ====================================
# STEP 5: Start API
# ====================================
echo -e "${YELLOW}Step 5: Starting FastAPI application...${NC}"
docker-compose up -d api

echo -e "${YELLOW}Waiting for API to start (20 seconds)...${NC}"
sleep 10
echo -e "${YELLOW}10 seconds remaining...${NC}"
sleep 10

echo ""

# ====================================
# STEP 6: Health checks
# ====================================
echo -e "${YELLOW}Step 6: Verifying deployment...${NC}"

# Test API health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
    curl http://localhost:8000/health | python -m json.tool
else
    echo -e "${RED}✗ API health check failed${NC}"
    echo "Check logs with: docker-compose logs api"
fi

echo ""

# ====================================
# Summary
# ====================================
echo "=================================================="
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=================================================="
echo ""
echo "📍 Access Points:"
echo "   API:          http://localhost:8000"
echo "   API Docs:     http://localhost:8000/api/v1/docs"
echo "   Health:       http://localhost:8000/health"
echo ""
echo "🔍 Useful Commands:"
echo "   View logs:    docker-compose logs -f api"
echo "   Stop all:     docker-compose down"
echo "   Restart:      docker-compose restart api"
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "✅ Ready to use! Visit http://localhost:8000/api/v1/docs"
