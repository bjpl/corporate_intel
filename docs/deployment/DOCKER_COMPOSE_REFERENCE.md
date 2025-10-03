# Docker Compose Reference - Corporate Intelligence Platform

## Table of Contents
- [Service Descriptions](#service-descriptions)
- [Port Mappings](#port-mappings)
- [Volume Mounts](#volume-mounts)
- [Network Configuration](#network-configuration)
- [Environment Variables](#environment-variables)
- [Scaling Strategies](#scaling-strategies)
- [Health Checks](#health-checks)
- [Profiles](#profiles)

## Service Descriptions

### Core Services

#### PostgreSQL with TimescaleDB
```yaml
postgres:
  image: timescale/timescaledb:latest-pg15
  container_name: corporate-intel-postgres
```

**Purpose:** Primary database with time-series optimization

**Features:**
- TimescaleDB extension for time-series data
- pgvector for embeddings
- Automated backups
- Health checks

**Configuration:**
- User: `intel_user` (configurable)
- Database: `corporate_intel`
- Port: 5432 (internal), 5432 (external)

#### Redis Cache
```yaml
redis:
  image: redis:7-alpine
  container_name: corporate-intel-redis
```

**Purpose:** In-memory cache and session storage

**Features:**
- AOF persistence enabled
- LRU eviction policy
- 512MB memory limit (configurable)

**Configuration:**
- Port: 6379 (internal), 6379 (external)
- Persistence: AOF enabled

#### MinIO Object Storage
```yaml
minio:
  image: minio/minio:latest
  container_name: corporate-intel-minio
```

**Purpose:** S3-compatible object storage for documents and reports

**Features:**
- Multi-bucket support
- Web console
- S3 API compatibility

**Configuration:**
- API Port: 9000
- Console Port: 9001
- Root User: `minio_admin` (change in production)

#### Corporate Intelligence API
```yaml
api:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: corporate-intel-api
```

**Purpose:** FastAPI application server

**Features:**
- Gunicorn with Uvicorn workers
- Auto-reload in dev mode
- Health checks
- Observability integration

**Configuration:**
- Port: 8000
- Workers: 4 (configurable)
- Timeout: 120s

### Observability Services (Optional)

#### Jaeger Tracing
```yaml
jaeger:
  image: jaegertracing/all-in-one:latest
  profiles: [observability]
```

**Purpose:** Distributed tracing

**Ports:**
- UI: 16686
- OTLP gRPC: 4317
- OTLP HTTP: 4318

#### Prometheus Metrics
```yaml
prometheus:
  image: prom/prometheus:latest
  profiles: [observability]
```

**Purpose:** Metrics collection and storage

**Configuration:**
- Port: 9090
- Scrape interval: 15s (configurable)
- Retention: 15d (configurable)

#### Grafana Dashboards
```yaml
grafana:
  image: grafana/grafana:latest
  profiles: [observability]
```

**Purpose:** Metrics visualization

**Configuration:**
- Port: 3000
- Admin password: Set in `.env`
- Auto-provisioned dashboards

## Port Mappings

### Production Environment

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| API | 8000 | 8000 | HTTP API |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 6379 | Cache |
| MinIO API | 9000 | 9000 | Object Storage |
| MinIO Console | 9001 | 9001 | MinIO UI |
| Jaeger UI | 16686 | 16686 | Tracing UI |
| Prometheus | 9090 | 9090 | Metrics |
| Grafana | 3000 | 3000 | Dashboards |

### Development Environment

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| API | 8000 | 8000 | HTTP API |
| API Debug | 5678 | 5678 | Remote Debugging |
| PostgreSQL | 5432 | 5433 | Database |
| Redis | 6379 | 6380 | Cache |
| MinIO API | 9000 | 9001 | Object Storage |
| MinIO Console | 9001 | 9002 | MinIO UI |
| pgAdmin | 80 | 5050 | DB Management |
| Mailhog SMTP | 1025 | 1025 | Email Testing |
| Mailhog UI | 8025 | 8025 | Email UI |

### Test Environment

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| PostgreSQL Test | 5432 | 5434 | Test Database |
| Redis Test | 6379 | 6381 | Test Cache |
| MinIO Test | 9000 | 9003 | Test Storage |

## Volume Mounts

### Named Volumes (Data Persistence)

```yaml
volumes:
  # Production
  postgres_data:              # PostgreSQL data
  redis_data:                 # Redis persistence
  minio_data:                 # MinIO buckets
  api_logs:                   # Application logs
  api_cache:                  # Application cache
  api_data:                   # Application data
  prometheus_data:            # Metrics data
  grafana_data:               # Dashboard configs

  # Development
  postgres_dev_data:          # Dev database
  redis_dev_data:             # Dev cache
  minio_dev_data:             # Dev storage
  grafana_dev_data:           # Dev dashboards
  pgadmin_dev_data:           # pgAdmin config
```

### Bind Mounts (Code and Configuration)

#### Production
```yaml
api:
  volumes:
    - ./src:/app/src:ro                    # Read-only source
    - ./alembic:/app/alembic:ro            # Read-only migrations
    - api_logs:/app/logs                   # Writable logs
    - api_cache:/app/cache                 # Writable cache
```

#### Development
```yaml
api:
  volumes:
    - ./src:/app/src                       # Read-write source (hot reload)
    - ./alembic:/app/alembic              # Read-write migrations
    - ./tests:/app/tests                   # Test files
    - ./logs:/app/logs                     # Local logs
    - ./cache:/app/cache                   # Local cache
```

### Database Initialization
```yaml
postgres:
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
```

## Network Configuration

### Default Network
```yaml
networks:
  corporate-intel-network:
    driver: bridge
    name: corporate-intel-network
```

**All services connect to this network for inter-container communication.**

### Service Discovery

Services can communicate using service names:
```python
# In application code
POSTGRES_HOST = "postgres"  # Not localhost!
REDIS_HOST = "redis"
MINIO_ENDPOINT = "minio:9000"
```

### External Access

```yaml
services:
  api:
    ports:
      - "8000:8000"  # Host:Container
    networks:
      - corporate-intel-network
```

### Network Isolation (Testing)

```yaml
# Test network is isolated
networks:
  test-network:
    driver: bridge
    name: corporate-intel-test-network
```

## Environment Variables

### Core Configuration

```bash
# Application
ENVIRONMENT=development|staging|production
DEBUG=true|false
SECRET_KEY=<secure-random-key>

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=corporate_intel

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<secure-password>

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
MINIO_USE_SSL=false
```

### External Services

```bash
# External APIs
ALPHA_VANTAGE_API_KEY=<key>
NEWSAPI_KEY=<key>
SEC_USER_AGENT=<user-agent>

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=corporate-intel-api
SENTRY_DSN=<sentry-dsn>
```

### Per-Environment Overrides

Development:
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

Production:
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

Testing:
```bash
ENVIRONMENT=testing
DEBUG=false
LOG_LEVEL=WARNING
```

## Scaling Strategies

### Horizontal Scaling (API Workers)

```bash
# Scale API service to 3 instances
docker-compose up -d --scale api=3

# With load balancer
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api
```

### Vertical Scaling (Resource Limits)

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Database Read Replicas

```yaml
postgres_replica:
  image: timescale/timescaledb:latest-pg15
  environment:
    POSTGRES_MASTER_HOST: postgres
    POSTGRES_REPLICATION_MODE: slave
  depends_on:
    - postgres
```

### Redis Cluster

```yaml
redis_1:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf

redis_2:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf
```

## Health Checks

### API Health Check
```yaml
api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

### PostgreSQL Health Check
```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Redis Health Check
```yaml
redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Dependency Management
```yaml
api:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
    minio:
      condition: service_healthy
```

## Profiles

### Observability Profile

```bash
# Start with observability services
docker-compose --profile observability up -d

# Services included:
# - Jaeger
# - Prometheus
# - Grafana
```

### Development Profile

```bash
# Start development-only services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Additional services:
# - pgAdmin
# - Mailhog
```

### Testing Profile

```bash
# Start test services
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Test-specific:
# - Isolated network
# - Test database
# - Test runner
```

## Advanced Configurations

### Custom Compose Files

```bash
# Multiple compose files
docker-compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.local.yml \
  up -d
```

### Environment-Specific Overrides

```yaml
# docker-compose.override.yml (auto-loaded)
services:
  api:
    environment:
      MY_LOCAL_VAR: value
```

### Secrets Management (Swarm)

```yaml
secrets:
  postgres_password:
    external: true

services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
```

### Custom Networks with IPAM

```yaml
networks:
  corporate-intel-network:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.28.0.0/16
          ip_range: 172.28.5.0/24
          gateway: 172.28.5.254
```

## Best Practices

1. **Use Named Volumes:** Easier to manage and backup
2. **Health Checks:** Ensure proper startup order
3. **Resource Limits:** Prevent resource exhaustion
4. **Environment Files:** Separate configs per environment
5. **Profiles:** Group optional services
6. **Networks:** Isolate services when needed
7. **Restart Policies:** `unless-stopped` for resilience
8. **Logging:** Configure log drivers for production

## Next Steps

- [Docker Setup Guide](./DOCKER_SETUP_GUIDE.md) - Setup and workflow
- [Production Deployment](./PRODUCTION_DEPLOYMENT.md) - Production checklist
