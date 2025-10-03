# Docker Setup Guide - Corporate Intelligence Platform

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Building Images](#building-images)
- [Running Containers](#running-containers)
- [Development Workflow](#development-workflow)
- [Testing in Docker](#testing-in-docker)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)

## Quick Start

### For Development (Hot Reload Enabled)

```bash
# Start all services in development mode
make dev-up

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- pgAdmin: http://localhost:5050
- MinIO Console: http://localhost:9002
- Jaeger UI: http://localhost:16686
- Grafana: http://localhost:3000

### For Production

```bash
# Build and start production services
make prod-build
make prod-up

# Or manually:
docker-compose build
docker-compose up -d
```

## Prerequisites

### Required Software

1. **Docker Engine** (v20.10+)
   ```bash
   # Check version
   docker --version
   ```

2. **Docker Compose** (v2.0+)
   ```bash
   # Check version
   docker-compose --version
   ```

3. **Make** (optional, for convenience commands)
   ```bash
   # Check if installed
   make --version
   ```

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 20 GB

**Recommended:**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 50 GB (SSD preferred)

## Building Images

### Production Image (Optimized)

```bash
# Multi-stage build for minimal production image
docker-compose build

# Specific service
docker-compose build api

# No cache (fresh build)
docker-compose build --no-cache
```

**Production Image Features:**
- Multi-stage build (builder + runtime)
- Non-root user (appuser)
- Minimal base (python:3.11-slim)
- Health checks configured
- Optimized layer caching

### Development Image (Full tooling)

```bash
# Build development image with debug tools
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

# Or using Makefile
make build
```

**Development Image Features:**
- Hot reload enabled
- Debug tools included (ipdb, ipython)
- Development dependencies
- Code quality tools (black, isort, mypy)

### Build Arguments

```bash
# Custom build args
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

## Running Containers

### Production Mode

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down
```

### Development Mode

```bash
# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View API logs only
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api

# Restart API after code changes (if needed)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart api
```

### Individual Services

```bash
# Start only database
docker-compose up -d postgres

# Start API and dependencies
docker-compose up -d postgres redis minio api

# Scale workers (if applicable)
docker-compose up -d --scale worker=3
```

## Development Workflow

### 1. Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd corporate_intel

# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env

# Start development environment
make dev-up
```

### 2. Code Changes with Hot Reload

The development container automatically reloads when you modify files in `src/`:

```bash
# Edit code (your IDE/editor)
vim src/api/main.py

# Changes are automatically detected and reloaded
# No need to restart container!
```

### 3. Running Migrations

```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Or use Makefile
make migrate
```

### 4. Interactive Shell Access

```bash
# Bash shell
docker-compose exec api /bin/bash

# Python shell with app context
docker-compose exec api python -c "from src.api.main import app; import IPython; IPython.embed()"

# Database shell
docker-compose exec postgres psql -U intel_user -d corporate_intel

# Or use Makefile
make dev-shell
make db-shell
```

### 5. Installing New Dependencies

```bash
# Add to pyproject.toml, then:
docker-compose exec api pip install <package-name>

# Rebuild image to persist
docker-compose build api
```

### 6. Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api

# Since timestamp
docker-compose logs --since 2024-01-01T00:00:00 api
```

## Testing in Docker

### Unit and Integration Tests

```bash
# Run all tests
make test

# Or manually:
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
docker-compose -f docker-compose.test.yml down -v
```

### Test with Coverage

```bash
# Generate coverage report
make test-coverage

# View HTML report
open coverage_html/index.html
```

### Integration Tests Only

```bash
make test-integration
```

### E2E Tests

```bash
make test-e2e
```

### Debugging Tests

```bash
# Run tests with verbose output
docker-compose -f docker-compose.test.yml run --rm test_runner pytest -vv

# Run specific test file
docker-compose -f docker-compose.test.yml run --rm test_runner pytest tests/test_specific.py -v

# Run with pdb on failure
docker-compose -f docker-compose.test.yml run --rm test_runner pytest --pdb
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs api

# Check service health
docker-compose ps

# Verify dependencies are healthy
docker-compose exec postgres pg_isready
docker-compose exec redis redis-cli ping
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process or change port in .env
API_PORT=8001
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose exec postgres pg_isready -U intel_user

# Check connection from API container
docker-compose exec api pg_isready -h postgres -p 5432 -U intel_user

# Restart database
docker-compose restart postgres
```

### Volume Permission Issues

```bash
# Fix permissions (Linux/Mac)
sudo chown -R $USER:$USER ./logs ./cache ./data

# Or run as root (not recommended)
docker-compose exec --user root api bash
```

### Out of Disk Space

```bash
# Remove unused resources
docker system prune -af --volumes

# Remove specific volumes
docker volume rm corporate-intel-postgres-data

# Check disk usage
docker system df
```

### Image Build Fails

```bash
# Clear build cache
docker builder prune -af

# Build with no cache
docker-compose build --no-cache

# Build specific stage
docker build --target python-builder -t test-build .
```

### Network Issues

```bash
# Recreate network
docker-compose down
docker network rm corporate-intel-network
docker-compose up -d

# Inspect network
docker network inspect corporate-intel-network
```

## Performance Tuning

### Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Database Performance

```bash
# Adjust PostgreSQL settings
docker-compose exec postgres psql -U intel_user -d corporate_intel -c "
  ALTER SYSTEM SET shared_buffers = '2GB';
  ALTER SYSTEM SET effective_cache_size = '6GB';
  ALTER SYSTEM SET maintenance_work_mem = '512MB';
  ALTER SYSTEM SET work_mem = '64MB';
"

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis Performance

```yaml
redis:
  command: >
    redis-server
    --maxmemory 1gb
    --maxmemory-policy allkeys-lru
    --save ""  # Disable persistence for pure cache
```

### Build Cache Optimization

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build with inline cache
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1

# Multi-platform builds (if needed)
docker buildx build --platform linux/amd64,linux/arm64 -t myimage .
```

### Monitoring Resource Usage

```bash
# Real-time stats
docker stats

# Container resource usage
docker-compose ps -a --format json | jq

# Disk usage
docker system df -v
```

## Best Practices

### 1. Environment Variables
- Never commit `.env` files
- Use `.env.example` as template
- Rotate secrets regularly
- Use different values for dev/staging/prod

### 2. Data Persistence
- Always use named volumes for data
- Regular backups: `make db-backup`
- Test restore procedures

### 3. Security
- Run containers as non-root
- Keep images updated
- Scan for vulnerabilities: `make security-scan`
- Use secrets management (Docker Swarm/Kubernetes)

### 4. Development
- Use hot reload in development
- Keep dev and prod Dockerfiles separate
- Test in containers before production

### 5. CI/CD
- Build images in CI pipeline
- Tag with version/git hash
- Push to registry after tests pass

## Next Steps

- [Docker Compose Reference](./DOCKER_COMPOSE_REFERENCE.md) - Detailed service configuration
- [Production Deployment](./PRODUCTION_DEPLOYMENT.md) - Production deployment guide
- [Monitoring Setup](../monitoring/MONITORING_SETUP.md) - Observability configuration
