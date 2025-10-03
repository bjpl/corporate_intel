# Docker Build Instructions

## Files Created

All Docker-related configuration files have been successfully created:

### 1. C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\Dockerfile
**Multi-stage production Dockerfile** with:
- **Stage 1 (python-builder)**: Builds Python dependencies with all required packages
- **Stage 2 (production)**: Minimal runtime image with security hardening
- Non-root user (appuser:1000)
- Health check endpoint
- Optimized Gunicorn configuration with 4 workers
- Security labels and metadata

### 2. C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\.dockerignore
**Comprehensive exclusion list** including:
- Git files and version control
- Python bytecode and caches
- Environment files and secrets (.env, .key, .pem)
- Development dependencies and test files
- Docker and CI/CD configurations
- IDE and temporary files

### 3. C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\docker-compose.yml
**Complete local development stack** with:
- **PostgreSQL + TimescaleDB**: Port 5432, persistent volumes, health checks
- **Redis**: Port 6379, AOF persistence, 512MB memory limit
- **MinIO**: Ports 9000/9001, object storage for documents/reports
- **API Service**: Port 8000, depends on all infrastructure services
- **Jaeger**: Port 16686, distributed tracing (observability profile)
- **Prometheus**: Port 9090, metrics collection (observability profile)
- **Grafana**: Port 3000, visualization dashboards (observability profile)

### 4. C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\scripts\docker-security-scan.sh
**Comprehensive security scanning script** supporting:
- Trivy vulnerability scanning
- Grype container analysis
- Snyk security testing
- Dive image efficiency analysis
- Gitleaks secrets detection
- CIS Docker Benchmark compliance
- Automated report generation

### 5. C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\docs\docker-deployment.md
**Complete deployment documentation** covering:
- Prerequisites and setup
- Build instructions
- Docker Compose profiles
- Security scanning procedures
- Database migrations
- Monitoring and troubleshooting
- Production deployment best practices

## Quick Start

### 1. Build the Docker Image

```bash
# Navigate to project directory
cd /c/Users/brand/Development/Project_Workspace/active-development/corporate_intel

# Build with BuildKit (recommended)
DOCKER_BUILDKIT=1 docker build \
  --tag corporate-intel-api:latest \
  --tag corporate-intel-api:1.0.0 \
  --file Dockerfile \
  .
```

### 2. Start Development Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Verify Deployment

```bash
# API health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/api/v1/docs

# MinIO console
open http://localhost:9001

# Prometheus metrics
curl http://localhost:8000/metrics
```

### 4. Run Security Scan

```bash
# Make script executable
chmod +x scripts/docker-security-scan.sh

# Run comprehensive security scan
./scripts/docker-security-scan.sh corporate-intel-api:latest

# View reports
ls -la security-reports/
```

## Production Build

### Optimized Production Build

```bash
# Build with all optimizations
DOCKER_BUILDKIT=1 docker build \
  --tag corporate-intel-api:1.0.0 \
  --tag corporate-intel-api:latest \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --file Dockerfile \
  .

# Tag for registry
docker tag corporate-intel-api:1.0.0 registry.example.com/corporate-intel-api:1.0.0

# Push to registry
docker push registry.example.com/corporate-intel-api:1.0.0
```

### Multi-platform Build

```bash
# Create buildx builder
docker buildx create --name multiplatform --use

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag corporate-intel-api:1.0.0 \
  --push \
  .
```

## Environment Configuration

### Required Environment Variables

```bash
# Security (CRITICAL)
SECRET_KEY=<generate-secure-random-32-char-string>
ENVIRONMENT=production
DEBUG=false

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=corporate_intel

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<minio-access-key>
MINIO_SECRET_KEY=<minio-secret-key>

# External APIs (Optional)
ALPHA_VANTAGE_API_KEY=<your-api-key>
NEWSAPI_KEY=<your-api-key>
SEC_USER_AGENT=Corporate Intel Platform/1.0 (your-email@example.com)

# Observability (Optional)
SENTRY_DSN=<your-sentry-dsn>
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

## Database Migrations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Check migration status
docker-compose exec api alembic current

# Rollback migration
docker-compose exec api alembic downgrade -1
```

## Service Management

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# Start with observability stack
docker-compose --profile observability up -d

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Restart specific service
docker-compose restart api

# Scale API service
docker-compose up -d --scale api=3
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail 100 api

# Since timestamp
docker-compose logs --since 2024-01-01T00:00:00 api
```

### Execute Commands

```bash
# Run command in container
docker-compose exec api python -c "print('Hello')"

# Open shell
docker-compose exec api bash

# Run one-off command
docker-compose run --rm api python scripts/init_db.py
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# PostgreSQL health
docker-compose exec postgres pg_isready -U intel_user

# Redis health
docker-compose exec redis redis-cli ping

# All services status
docker-compose ps
```

### Metrics and Performance

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Container stats
docker stats

# Disk usage
docker system df

# Volume information
docker volume ls
docker volume inspect corporate-intel-postgres-data
```

### Observability Stack

```bash
# Access Jaeger UI (distributed tracing)
open http://localhost:16686

# Access Prometheus (metrics)
open http://localhost:9090

# Access Grafana (dashboards)
open http://localhost:3000
# Default credentials: admin / admin
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Change port in docker-compose.yml
API_PORT=8001 docker-compose up -d
```

#### 2. Database Connection Failed

```bash
# Check postgres logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U intel_user -d corporate_intel

# Reset database (WARNING: deletes data)
docker-compose down -v
docker-compose up -d postgres
docker-compose exec api alembic upgrade head
```

#### 3. Out of Memory

```bash
# Check memory usage
docker stats --no-stream

# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory (8GB recommended)

# Reduce Gunicorn workers
# Edit Dockerfile: change --workers from 4 to 2
```

#### 4. Build Failures

```bash
# Clean build without cache
docker-compose build --no-cache api

# Remove old images
docker image prune -a

# Check disk space
df -h
docker system df
```

### Debug Mode

```bash
# Enable debug logging
DEBUG=true docker-compose up

# Run with verbose output
docker-compose --verbose up

# Check container details
docker inspect corporate-intel-api
```

## Security Best Practices

1. **Never commit .env files** - Use .env.example as template
2. **Scan regularly** - Run security scans before each deployment
3. **Update dependencies** - Keep base images and packages current
4. **Use secrets management** - Docker secrets, Vault, or cloud provider
5. **Limit privileges** - Run as non-root user (already configured)
6. **Network isolation** - Use Docker networks (already configured)
7. **Resource limits** - Set memory and CPU limits in production
8. **Regular backups** - Backup volumes and databases daily

## Backup and Restore

### Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U intel_user corporate_intel > backup-$(date +%Y%m%d).sql

# Backup all volumes
docker run --rm \
  -v corporate-intel-postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/volumes-backup-$(date +%Y%m%d).tar.gz /data
```

### Restore

```bash
# Restore PostgreSQL
docker-compose exec -T postgres psql -U intel_user corporate_intel < backup.sql

# Restore volumes
docker run --rm \
  -v corporate-intel-postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/volumes-backup.tar.gz -C /
```

## Performance Optimization

### Build Optimization

```bash
# Use BuildKit cache
DOCKER_BUILDKIT=1 docker build --cache-from corporate-intel-api:latest .

# Multi-stage build (already implemented)
# Leverages layer caching for faster rebuilds
```

### Runtime Optimization

```bash
# Adjust workers based on CPU cores
# Formula: (2 × CPU cores) + 1
# Edit Dockerfile CMD: --workers X

# Use tmpfs for temporary files
docker-compose.yml:
  tmpfs:
    - /app/tmp:size=1G
```

## Next Steps

1. **Configure environment** - Edit .env with your credentials
2. **Start services** - Run `docker-compose up -d`
3. **Run migrations** - Execute `docker-compose exec api alembic upgrade head`
4. **Security scan** - Run `./scripts/docker-security-scan.sh corporate-intel-api:latest`
5. **Test endpoints** - Access http://localhost:8000/api/v1/docs
6. **Enable monitoring** - Start with observability profile
7. **Configure backups** - Set up automated backup scripts
8. **Review logs** - Monitor `docker-compose logs -f`

## Support and Documentation

- **Docker Deployment**: C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\docs\docker-deployment.md
- **API Documentation**: http://localhost:8000/api/v1/docs (after starting)
- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Reference**: https://docs.docker.com/compose/

## Summary

All Docker configuration files have been successfully created and are production-ready:

- Multi-stage Dockerfile with security hardening
- Comprehensive .dockerignore for clean builds
- Complete docker-compose.yml with all infrastructure services
- Automated security scanning script
- Full deployment documentation

The platform is ready for:
- Local development with hot-reload
- Production deployment with security hardening
- Automated security scanning and compliance
- Comprehensive monitoring and observability
- Scalable multi-worker architecture

**All files are located at:**
- Dockerfile: `/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/Dockerfile`
- .dockerignore: `/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/.dockerignore`
- docker-compose.yml: `/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docker-compose.yml`
- Security scan script: `/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/scripts/docker-security-scan.sh`
- Deployment guide: `/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docs/docker-deployment.md`
