# Docker Deployment Guide

## Overview

This guide covers building, deploying, and managing the Corporate Intelligence Platform using Docker and Docker Compose.

## Prerequisites

- Docker 24.0+ with BuildKit enabled
- Docker Compose 2.20+
- Minimum 4GB RAM allocated to Docker
- 20GB free disk space

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

### 2. Build and Run

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Access Services

- API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs
- MinIO Console: http://localhost:9001
- Jaeger UI: http://localhost:16686 (if observability profile enabled)
- Grafana: http://localhost:3000 (if observability profile enabled)

## Building the Image

### Production Build

```bash
# Build with BuildKit optimizations
DOCKER_BUILDKIT=1 docker build \
  --tag corporate-intel-api:latest \
  --tag corporate-intel-api:1.0.0 \
  --file Dockerfile \
  .
```

### Multi-platform Build

```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag corporate-intel-api:latest \
  --push \
  .
```

### Development Build

```bash
# Build with cache mount for faster rebuilds
docker build \
  --tag corporate-intel-api:dev \
  --target python-builder \
  .
```

## Docker Compose Profiles

### Development (Default)

```bash
# Start core services only
docker-compose up -d
```

### With Observability

```bash
# Start with Jaeger, Prometheus, and Grafana
docker-compose --profile observability up -d
```

## Service Configuration

### PostgreSQL with TimescaleDB

- Automatic TimescaleDB extension installation
- Persistent data in named volume
- Health checks enabled
- Custom initialization scripts in `scripts/init-db.sql`

### Redis

- Configured with persistence (AOF)
- 512MB memory limit with LRU eviction
- Health checks enabled

### MinIO

- Object storage for documents and reports
- Web console on port 9001
- Buckets created automatically on first run

### API Service

- Multi-worker Gunicorn with Uvicorn workers
- Health check endpoint at `/health`
- Automatic restart on failure
- Volume mounts for logs, cache, and data

## Security Scanning

### Run Security Scan

```bash
# Make script executable (first time only)
chmod +x scripts/docker-security-scan.sh

# Run full security scan
./scripts/docker-security-scan.sh corporate-intel-api:latest

# View reports
ls -la security-reports/
```

### Install Security Tools

```bash
# Trivy (vulnerability scanner)
brew install trivy

# Grype (vulnerability scanner)
brew install grype

# Snyk (container security)
npm install -g snyk

# Dive (image analysis)
brew install dive

# Gitleaks (secrets detection)
brew install gitleaks
```

## Database Migrations

### Run Migrations

```bash
# Using docker-compose
docker-compose exec api alembic upgrade head

# Using docker run
docker run --rm \
  --network corporate-intel-network \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/corporate_intel \
  corporate-intel-api:latest \
  alembic upgrade head
```

### Create Migration

```bash
docker-compose exec api alembic revision --autogenerate -m "Description"
```

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail 100 api
```

### Health Checks

```bash
# Check all services
docker-compose ps

# API health endpoint
curl http://localhost:8000/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Detailed volume info
docker volume ls
docker volume inspect corporate-intel-postgres-data
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs api

# Rebuild without cache
docker-compose build --no-cache api

# Reset volumes (WARNING: deletes data)
docker-compose down -v
```

### Database Connection Issues

```bash
# Check postgres health
docker-compose exec postgres pg_isready -U intel_user

# Test connection
docker-compose exec postgres psql -U intel_user -d corporate_intel -c "SELECT 1"

# Check network
docker network inspect corporate-intel-network
```

### Memory Issues

```bash
# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory (increase to 8GB)

# Check container memory usage
docker stats --no-stream

# Reduce Gunicorn workers in Dockerfile (change --workers from 4 to 2)
```

### Permission Issues

```bash
# Fix volume permissions
docker-compose exec api chown -R appuser:appuser /app/logs /app/cache /app/data
```

## Production Deployment

### Environment Variables

Ensure these are set in production `.env`:

```bash
# Security
SECRET_KEY=<generate-secure-random-key>
ENVIRONMENT=production
DEBUG=false

# Database
POSTGRES_PASSWORD=<secure-password>

# External services
ALPHA_VANTAGE_API_KEY=<your-key>
SENTRY_DSN=<your-sentry-dsn>

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector:4317
```

### SSL/TLS

Use a reverse proxy (Nginx, Traefik) for SSL termination:

```yaml
# Example nginx configuration
upstream api {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Backup Strategy

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U intel_user corporate_intel > backup.sql

# Backup volumes
docker run --rm \
  -v corporate-intel-postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz /data

# Restore from backup
docker run --rm \
  -v corporate-intel-postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

### Scaling

```bash
# Scale API service
docker-compose up -d --scale api=3

# With load balancer (nginx)
docker-compose --profile production up -d
```

## Cleanup

### Remove Containers

```bash
# Stop and remove containers
docker-compose down

# Remove with volumes (deletes data)
docker-compose down -v

# Remove images
docker rmi corporate-intel-api:latest
```

### Prune System

```bash
# Remove unused containers, networks, images
docker system prune -a

# Remove unused volumes
docker volume prune
```

## Best Practices

1. **Security**
   - Run security scans before deploying
   - Never commit `.env` files
   - Use secrets management (Docker secrets, Vault)
   - Keep base images updated

2. **Performance**
   - Use BuildKit for faster builds
   - Leverage layer caching
   - Adjust worker count based on CPU cores
   - Monitor resource usage

3. **Monitoring**
   - Enable observability profile in production
   - Set up alerts in Prometheus
   - Configure log aggregation
   - Monitor health check endpoints

4. **Maintenance**
   - Regular backups
   - Update dependencies monthly
   - Scan for vulnerabilities weekly
   - Review logs daily

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
