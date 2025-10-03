# Docker Guide - Corporate Intelligence Platform

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Building Images](#building-images)
- [Running Containers](#running-containers)
- [Security](#security)
- [Optimization](#optimization)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

## Overview

This guide covers Docker containerization for the Corporate Intelligence Platform. The Dockerfile implements multi-stage builds with security best practices, resulting in a production-ready container under 500MB.

### Key Features
- Multi-stage build for minimal image size (<500MB)
- Non-root user execution for enhanced security
- Health check configuration for container orchestration
- Optimized layer caching for faster builds
- Security scanning integration (Trivy, Hadolint)
- Production-ready gunicorn + uvicorn configuration

### Architecture
```
┌─────────────────────────────────────────────────────────┐
│ Stage 1: python-builder                                 │
│ - Compile Python dependencies                           │
│ - Create virtual environment                            │
│ - Base: python:3.11-slim                                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: production                                     │
│ - Minimal runtime environment                           │
│ - Copy compiled dependencies                            │
│ - Non-root user (appuser:1000)                          │
│ - Health checks enabled                                 │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: development (optional)                         │
│ - Additional dev tools                                  │
│ - Hot-reload enabled                                    │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required
- Docker 24.0+ or higher
- Docker Compose 2.0+ (for multi-container setup)
- 4GB+ available disk space
- 2GB+ available RAM

### Optional (for security scanning)
- Trivy (vulnerability scanner)
- Hadolint (Dockerfile linter)
- Docker Bench Security

### Installation

**Docker Desktop (Windows/Mac)**
```bash
# Download from https://www.docker.com/products/docker-desktop
# Includes Docker Engine, Docker Compose, and Docker CLI
```

**Docker Engine (Linux)**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify installation
docker --version
docker compose version
```

**Security Tools**
```bash
# Install Trivy
# macOS
brew install aquasecurity/trivy/trivy

# Linux
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

# Install Hadolint
# macOS
brew install hadolint

# Linux
wget -O /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64
chmod +x /usr/local/bin/hadolint
```

## Quick Start

### 1. Build Production Image
```bash
# Navigate to project root
cd /path/to/corporate_intel

# Build production image
docker build -t corporate-intel:latest .

# Build with build arguments
docker build \
  --build-arg ENVIRONMENT=production \
  -t corporate-intel:v0.1.0 \
  .
```

### 2. Run Container
```bash
# Run with environment variables
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  --env-file .env \
  --health-cmd "curl -f http://localhost:8000/health || exit 1" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 3 \
  corporate-intel:latest

# Check container status
docker ps

# View logs
docker logs -f corporate-intel-api

# Access API
curl http://localhost:8000/health
```

### 3. Use Docker Compose (Recommended)
```bash
# Start all services (API, PostgreSQL, Redis)
docker compose up -d

# View logs
docker compose logs -f api

# Stop all services
docker compose down

# Clean up volumes
docker compose down -v
```

## Building Images

### Production Build
```bash
# Standard production build
docker build \
  --target production \
  -t corporate-intel:latest \
  .

# With version tag
docker build \
  --target production \
  -t corporate-intel:v0.1.0 \
  -t corporate-intel:latest \
  .

# With build cache optimization
docker build \
  --target production \
  --cache-from corporate-intel:latest \
  -t corporate-intel:v0.1.0 \
  .
```

### Development Build
```bash
# Build development image with hot-reload
docker build \
  --target development \
  -t corporate-intel:dev \
  .

# Run development container
docker run -d \
  --name corporate-intel-dev \
  -p 8000:8000 \
  -v $(pwd)/src:/app/src \
  --env-file .env \
  corporate-intel:dev
```

### Build Arguments
```bash
# Custom Python version
docker build \
  --build-arg PYTHON_VERSION=3.11-slim \
  -t corporate-intel:latest \
  .

# Custom environment
docker build \
  --build-arg ENVIRONMENT=staging \
  -t corporate-intel:staging \
  .
```

## Running Containers

### Basic Run
```bash
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  corporate-intel:latest
```

### With Environment Variables
```bash
# Using .env file (recommended)
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  --env-file .env \
  corporate-intel:latest

# Inline environment variables
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/corporate_intel" \
  -e REDIS_URL="redis://redis:6379/0" \
  -e ENVIRONMENT=production \
  corporate-intel:latest
```

### With Volumes
```bash
# Mount data directory
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  corporate-intel:latest
```

### With Resource Limits
```bash
# Set CPU and memory limits
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  --env-file .env \
  --cpus="2.0" \
  --memory="2g" \
  --memory-swap="2g" \
  corporate-intel:latest
```

### Interactive Shell Access
```bash
# Access running container
docker exec -it corporate-intel-api /bin/bash

# Run one-off commands
docker exec corporate-intel-api python -c "print('Hello')"

# Run database migrations
docker exec corporate-intel-api alembic upgrade head
```

## Security

### Security Scanning

**Run Complete Security Scan**
```bash
# Make script executable
chmod +x scripts/docker-security-scan.sh

# Run security scan
./scripts/docker-security-scan.sh

# Specify custom image
IMAGE_NAME=corporate-intel:v0.1.0 ./scripts/docker-security-scan.sh

# Custom report directory
REPORT_DIR=./reports IMAGE_NAME=corporate-intel:latest ./scripts/docker-security-scan.sh
```

**Manual Scans**

```bash
# Hadolint - Dockerfile linting
hadolint Dockerfile

# Trivy - Vulnerability scanning
trivy image corporate-intel:latest

# Trivy with severity filtering
trivy image --severity CRITICAL,HIGH corporate-intel:latest

# Generate JSON report
trivy image --format json --output trivy-report.json corporate-intel:latest
```

### Security Best Practices

1. **Non-Root User**
   - Container runs as `appuser` (UID 1000)
   - Never run as root in production

2. **Minimal Base Image**
   - Uses `python:3.11-slim` (not alpine for compatibility)
   - Removes build dependencies from final image

3. **No Secrets in Image**
   - All secrets via environment variables
   - Never commit `.env` files
   - Use Docker secrets or vault in production

4. **Regular Updates**
   ```bash
   # Rebuild with latest security patches
   docker build --no-cache -t corporate-intel:latest .

   # Scan for vulnerabilities
   trivy image corporate-intel:latest
   ```

5. **Read-Only Root Filesystem**
   ```bash
   docker run -d \
     --name corporate-intel-api \
     --read-only \
     --tmpfs /tmp \
     --tmpfs /app/logs \
     -p 8000:8000 \
     corporate-intel:latest
   ```

## Optimization

### Image Size Reduction

**Current Optimization**
- Multi-stage build: Separates build and runtime dependencies
- Minimal base image: `python:3.11-slim` instead of full Python
- Layer caching: Dependencies installed before code copy
- Cleanup: Remove apt cache and pip cache

**Measure Image Size**
```bash
# Check image size
docker images corporate-intel:latest

# Analyze image layers
docker history corporate-intel:latest

# Detailed analysis with dive
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest corporate-intel:latest
```

### Build Performance

**Enable BuildKit**
```bash
# Set environment variable
export DOCKER_BUILDKIT=1

# Build with BuildKit
docker build -t corporate-intel:latest .
```

**Use Build Cache**
```bash
# Save cache
docker build \
  --cache-from corporate-intel:latest \
  -t corporate-intel:v0.1.0 \
  .

# Registry cache (for CI/CD)
docker build \
  --cache-from registry.example.com/corporate-intel:latest \
  --cache-from registry.example.com/corporate-intel:builder \
  -t corporate-intel:v0.1.0 \
  .
```

### Runtime Optimization

**Gunicorn Workers**
```bash
# Default: 4 workers (in Dockerfile)
# Optimal formula: (2 x CPU cores) + 1

# Override workers
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  corporate-intel:latest \
  gunicorn src.api.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 8 \
    --bind 0.0.0.0:8000
```

## Troubleshooting

### Common Issues

**1. Container Exits Immediately**
```bash
# Check logs
docker logs corporate-intel-api

# Run interactively to debug
docker run -it --rm \
  --entrypoint /bin/bash \
  corporate-intel:latest

# Check health
docker inspect corporate-intel-api --format='{{json .State.Health}}'
```

**2. Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Use different port
docker run -d -p 8080:8000 corporate-intel:latest
```

**3. Environment Variables Not Loading**
```bash
# Verify .env file exists
ls -la .env

# Check loaded environment
docker exec corporate-intel-api env | grep DATABASE_URL

# Debug environment loading
docker run -it --rm --env-file .env corporate-intel:latest env
```

**4. Database Connection Issues**
```bash
# Test database connectivity
docker exec corporate-intel-api \
  psql "postgresql://user:pass@db:5432/corporate_intel" -c "SELECT 1"

# Check network
docker network ls
docker network inspect bridge
```

**5. Health Check Failing**
```bash
# Manual health check
docker exec corporate-intel-api curl http://localhost:8000/health

# Check health status
docker inspect corporate-intel-api --format='{{.State.Health.Status}}'

# Disable health check temporarily
docker run -d \
  --name corporate-intel-api \
  --no-healthcheck \
  -p 8000:8000 \
  corporate-intel:latest
```

### Debug Mode

**Enable Debug Logging**
```bash
docker run -d \
  --name corporate-intel-api \
  -p 8000:8000 \
  -e DEBUG=true \
  -e LOG_LEVEL=debug \
  corporate-intel:latest

# View debug logs
docker logs -f corporate-intel-api
```

**Interactive Debugging**
```bash
# Start container with shell
docker run -it --rm \
  -p 8000:8000 \
  --env-file .env \
  --entrypoint /bin/bash \
  corporate-intel:latest

# Inside container:
# Test imports
python -c "from src.api.main import app; print('OK')"

# Run with uvicorn directly
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

## Production Deployment

### Docker Compose Production Setup

**docker-compose.prod.yml**
```yaml
version: '3.8'

services:
  api:
    image: corporate-intel:v0.1.0
    restart: always
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  db:
    image: postgres:15-alpine
    restart: always
    environment:
      - POSTGRES_DB=corporate_intel
    env_file:
      - .env.production
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

**Deploy**
```bash
# Start production stack
docker compose -f docker-compose.prod.yml up -d

# Scale API instances
docker compose -f docker-compose.prod.yml up -d --scale api=5

# Rolling update
docker compose -f docker-compose.prod.yml up -d --no-deps --build api
```

### Kubernetes Deployment

**deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: corporate-intel-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: corporate-intel-api
  template:
    metadata:
      labels:
        app: corporate-intel-api
    spec:
      containers:
      - name: api
        image: corporate-intel:v0.1.0
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - secretRef:
            name: corporate-intel-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### CI/CD Integration

**GitHub Actions Example**
```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ghcr.io/yourorg/corporate-intel:latest
            ghcr.io/yourorg/corporate-intel:${{ github.sha }}
          cache-from: type=registry,ref=ghcr.io/yourorg/corporate-intel:buildcache
          cache-to: type=registry,ref=ghcr.io/yourorg/corporate-intel:buildcache,mode=max

      - name: Run Trivy security scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/yourorg/corporate-intel:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### Monitoring and Logging

**Prometheus Metrics**
```bash
# Metrics endpoint exposed at /metrics
curl http://localhost:8000/metrics
```

**Centralized Logging**
```bash
# Docker logging driver
docker run -d \
  --name corporate-intel-api \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  -p 8000:8000 \
  corporate-intel:latest

# Forward to logging service
docker run -d \
  --name corporate-intel-api \
  --log-driver syslog \
  --log-opt syslog-address=tcp://logserver:514 \
  -p 8000:8000 \
  corporate-intel:latest
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Hadolint Documentation](https://github.com/hadolint/hadolint)
- [FastAPI Docker Deployment](https://fastapi.tiangolo.com/deployment/docker/)

## Support

For issues or questions:
- Check existing issues: GitHub Issues
- Security concerns: Email brandon.lambert87@gmail.com
- Documentation updates: Submit PR to docs/
