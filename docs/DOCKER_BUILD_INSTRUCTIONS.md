# Docker Build and Deployment Instructions

## Quick Start

### Prerequisites
1. Docker Desktop installed and **running**
2. Environment file configured (`.env.production` or `.env.example`)

### Build and Run

```bash
# 1. Start Docker Desktop
# Verify Docker is running:
docker --version

# 2. Build the image
docker build -t corporate-intel:latest .

# 3. Run the container
docker run -d \
  --name corporate-intel \
  -p 8000:8000 \
  --env-file .env.production \
  corporate-intel:latest

# 4. Check health
curl http://localhost:8000/health

# 5. View logs
docker logs -f corporate-intel
```

### Build Validation Commands

```bash
# Test builder stage only
docker build --target python-builder -t corporate-intel:builder .

# Build with no cache (clean build)
docker build --no-cache -t corporate-intel:clean .

# Inspect image layers
docker history corporate-intel:latest --no-trunc

# Check image size
docker images corporate-intel:latest

# Verify non-root user
docker run --rm corporate-intel:latest id
# Expected: uid=1000(appuser) gid=1000(appuser)

# Security scan
docker scout cves corporate-intel:latest
```

### Troubleshooting

**Error: Docker daemon not running**
```bash
# Start Docker Desktop application
# Wait for Docker to fully start, then retry
```

**Error: poetry.lock not found**
```bash
# The current Dockerfile uses pip install instead of Poetry
# This has already been resolved in the latest version
```

### Production Deployment

See `docker-compose.yml` for full orchestration setup including:
- PostgreSQL database with pgvector
- Redis cache
- Health checks
- Network isolation
- Volume management

### Security Notes

- `.dockerignore` file prevents secrets from being copied
- Container runs as non-root user (uid=1000)
- No hardcoded credentials
- All sensitive data via environment variables
