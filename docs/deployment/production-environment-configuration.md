# Production Environment Configuration Guide

## Environment Variables Template

### Production Environment File Structure

```
config/production/
├── .env.production          # Main environment configuration
├── .env.production.local    # Local overrides (git-ignored)
├── secrets/                 # External secrets management
│   ├── database.key
│   ├── redis.key
│   └── api-keys.json
└── ssl/                     # SSL certificates
    ├── fullchain.pem
    └── privkey.pem
```

## Complete Production Environment Variables

### 1. Core Application Settings

```bash
# Environment Identification
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Application Security
# CRITICAL: Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=${AWS_SECRET_MANAGER:prod/api/secret-key}
SESSION_SECRET_KEY=${AWS_SECRET_MANAGER:prod/api/session-secret}

# Application Settings
API_WORKERS=4
API_TIMEOUT=120
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["https://corporate-intel.yourdomain.com"]
SECURE_COOKIES=true
```

### 2. Database Configuration

```bash
# PostgreSQL Connection
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=${AWS_SECRET_MANAGER:prod/db/user}
POSTGRES_PASSWORD=${AWS_SECRET_MANAGER:prod/db/password}
POSTGRES_DB=corporate_intel_prod

# Connection Pool Settings
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Performance Tuning (Applied via Docker environment)
POSTGRES_MAX_CONNECTIONS=200
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=6GB
POSTGRES_MAINTENANCE_WORK_MEM=512MB
POSTGRES_CHECKPOINT_COMPLETION_TARGET=0.9
POSTGRES_WAL_BUFFERS=16MB
POSTGRES_DEFAULT_STATISTICS_TARGET=100
POSTGRES_RANDOM_PAGE_COST=1.1
POSTGRES_EFFECTIVE_IO_CONCURRENCY=200
POSTGRES_WORK_MEM=10485kB
POSTGRES_MIN_WAL_SIZE=2GB
POSTGRES_MAX_WAL_SIZE=8GB

# TimescaleDB Configuration
TIMESCALE_COMPRESSION_AFTER_DAYS=30
TIMESCALE_RETENTION_YEARS=2
TIMESCALEDB_TELEMETRY=off

# Backup Configuration
POSTGRES_BACKUP_ENABLED=true
POSTGRES_BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
POSTGRES_BACKUP_RETENTION_DAYS=30
POSTGRES_BACKUP_DESTINATION=s3://corporate-intel-backups/postgres/
```

### 3. Redis Cache Configuration

```bash
# Redis Connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${AWS_SECRET_MANAGER:prod/redis/password}
REDIS_DB=0
REDIS_MAX_CONNECTIONS=100

# Redis Performance
REDIS_MAX_MEMORY=4gb
REDIS_EVICTION_POLICY=allkeys-lru
REDIS_APPENDONLY=yes
REDIS_APPENDFSYNC=everysec

# Cache Settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
```

### 4. Object Storage (MinIO)

```bash
# MinIO Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ROOT_USER=${AWS_SECRET_MANAGER:prod/minio/root-user}
MINIO_ROOT_PASSWORD=${AWS_SECRET_MANAGER:prod/minio/root-password}
MINIO_SECURE=false  # Internal network only
MINIO_BROWSER_REDIRECT_URL=https://minio.corporate-intel.yourdomain.com

# Bucket Configuration
MINIO_BUCKET_DOCUMENTS=corporate-documents-prod
MINIO_BUCKET_REPORTS=analysis-reports-prod
MINIO_BUCKET_BACKUPS=database-backups-prod
MINIO_BUCKET_MODELS=model-artifacts-prod

# Versioning & Retention
MINIO_VERSIONING_ENABLED=true
MINIO_RETENTION_DAYS=90
```

### 5. External API Keys

```bash
# Alpha Vantage (Financial Data)
ALPHA_VANTAGE_API_KEY=${AWS_SECRET_MANAGER:prod/external/alpha-vantage}
ALPHA_VANTAGE_RATE_LIMIT=5
ALPHA_VANTAGE_TIMEOUT=30

# NewsAPI (News Aggregation)
NEWSAPI_KEY=${AWS_SECRET_MANAGER:prod/external/newsapi}
NEWSAPI_RATE_LIMIT=100
NEWSAPI_TIMEOUT=30

# SEC EDGAR (Required)
SEC_USER_AGENT=Corporate Intel Platform/1.0 (compliance@yourdomain.com)
SEC_RATE_LIMIT=10
SEC_TIMEOUT=30
```

### 6. Observability & Monitoring

```bash
# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=corporate-intel-api-prod
OTEL_TRACES_ENABLED=true
OTEL_METRICS_ENABLED=true
OTEL_LOGS_ENABLED=true

# Sentry Error Tracking
SENTRY_DSN=${AWS_SECRET_MANAGER:prod/observability/sentry-dsn}
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.05
SENTRY_SEND_DEFAULT_PII=false

# Prometheus Metrics
PROMETHEUS_METRICS_ENABLED=true
PROMETHEUS_METRICS_PORT=9090

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${AWS_SECRET_MANAGER:prod/grafana/admin-password}
GRAFANA_SERVER_ROOT_URL=https://grafana.corporate-intel.yourdomain.com
```

### 7. SSL/TLS Configuration

```bash
# Domain Configuration
DOMAIN_NAME=corporate-intel.yourdomain.com
API_DOMAIN=api.corporate-intel.yourdomain.com

# SSL Certificates
SSL_CERTIFICATE_PATH=/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem
SSL_CERTIFICATE_KEY_PATH=/etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem

# Let's Encrypt Configuration
LETSENCRYPT_EMAIL=ssl-admin@yourdomain.com
LETSENCRYPT_STAGING=false  # Set to true for testing
```

### 8. AWS Integration

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=${AWS_SECRET_MANAGER:prod/aws/access-key-id}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_MANAGER:prod/aws/secret-access-key}

# AWS Services
AWS_SECRETS_MANAGER_ENABLED=true
AWS_CLOUDWATCH_ENABLED=true
AWS_S3_BACKUP_ENABLED=true
AWS_S3_BACKUP_BUCKET=corporate-intel-backups
```

### 9. Feature Flags

```bash
# Application Features
DATA_QUALITY_ENABLED=true
ANOMALY_DETECTION_ENABLED=true
YAHOO_FINANCE_ENABLED=true

# AI/ML Features
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=32

# Vector Database
VECTOR_DIMENSION=1536
VECTOR_INDEX_TYPE=ivfflat
VECTOR_LISTS=100
```

### 10. Logging Configuration

```bash
# Application Logging
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_OUTPUT=stdout

# Log Retention
LOG_MAX_SIZE=20m
LOG_MAX_FILES=10
LOG_ROTATION_ENABLED=true

# Structured Logging
STRUCTURED_LOGGING_ENABLED=true
LOG_REQUEST_BODY=false  # Security: Don't log sensitive data
LOG_RESPONSE_BODY=false
```

## Docker Compose Environment Variables

### Production-Specific Overrides

```bash
# Docker Registry
DOCKER_REGISTRY=ghcr.io
DOCKER_IMAGE_NAME=yourorg/corporate-intel
DEPLOYMENT_VERSION=1.0.0

# Container Resources
API_CPU_LIMIT=2.0
API_MEMORY_LIMIT=4G
DB_CPU_LIMIT=2.0
DB_MEMORY_LIMIT=4G
REDIS_CPU_LIMIT=1.0
REDIS_MEMORY_LIMIT=4G

# Scaling
API_REPLICAS=3
AUTO_SCALING_ENABLED=true
AUTO_SCALING_MIN_REPLICAS=2
AUTO_SCALING_MAX_REPLICAS=10
AUTO_SCALING_CPU_THRESHOLD=70
```

## Secrets Management Strategy

### Option 1: AWS Secrets Manager (Recommended)

```bash
# Install AWS CLI
aws configure

# Create secrets
aws secretsmanager create-secret \
  --name prod/db/password \
  --secret-string "$(openssl rand -base64 32)"

aws secretsmanager create-secret \
  --name prod/redis/password \
  --secret-string "$(openssl rand -base64 32)"

aws secretsmanager create-secret \
  --name prod/api/secret-key \
  --secret-string "$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"

# Reference in docker-compose
environment:
  POSTGRES_PASSWORD: ${AWS_SECRET_MANAGER:prod/db/password}
```

### Option 2: HashiCorp Vault

```bash
# Initialize Vault
vault kv put secret/prod/database \
  username=intel_prod_user \
  password="$(openssl rand -base64 32)"

vault kv put secret/prod/redis \
  password="$(openssl rand -base64 32)"

vault kv put secret/prod/api \
  secret_key="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"

# Use Vault agent for injection
```

### Option 3: Environment File (Less Secure, Development Only)

```bash
# .env.production (Never commit to git!)
POSTGRES_PASSWORD=<generated-password>
REDIS_PASSWORD=<generated-password>
SECRET_KEY=<generated-secret>
```

## Configuration Validation

### Pre-deployment Checklist

```bash
#!/bin/bash
# scripts/validate-production-config.sh

echo "Validating production configuration..."

# Check required environment variables
REQUIRED_VARS=(
  "ENVIRONMENT"
  "SECRET_KEY"
  "POSTGRES_PASSWORD"
  "REDIS_PASSWORD"
  "MINIO_ROOT_PASSWORD"
  "DOMAIN_NAME"
)

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var is not set"
    exit 1
  fi
done

# Validate SECRET_KEY length
if [ ${#SECRET_KEY} -lt 32 ]; then
  echo "ERROR: SECRET_KEY must be at least 32 characters"
  exit 1
fi

# Check SSL certificates exist
if [ ! -f "$SSL_CERTIFICATE_PATH" ]; then
  echo "ERROR: SSL certificate not found at $SSL_CERTIFICATE_PATH"
  exit 1
fi

# Validate database connection
docker-compose -f docker-compose.prod.yml run --rm api \
  python -c "from src.core.database import test_connection; test_connection()"

echo "Configuration validation passed!"
```

## Security Hardening

### Required Security Settings

```bash
# Password Requirements
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Session Security
SESSION_TIMEOUT_MINUTES=30
SESSION_ABSOLUTE_TIMEOUT_MINUTES=480
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=strict

# Rate Limiting
RATE_LIMIT_GLOBAL=1000/hour
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_API=100/minute

# CORS Configuration
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=3600
CORS_METHODS=["GET","POST","PUT","DELETE","OPTIONS"]
```

## Environment-Specific Overrides

### Production vs Staging Differences

| Setting | Staging | Production |
|---------|---------|------------|
| DEBUG | true | false |
| LOG_LEVEL | DEBUG | WARNING |
| RATE_LIMIT | 1000/min | 100/min |
| AUTO_SCALING | disabled | enabled |
| BACKUP_RETENTION | 7 days | 30 days |
| SSL_CERT | self-signed | Let's Encrypt |
| MONITORING_RETENTION | 7 days | 30 days |
| SENTRY_SAMPLE_RATE | 1.0 | 0.1 |

## Configuration Management

### Version Control

```bash
# Directory structure
config/
├── production/
│   ├── .env.production.template    # Template (committed)
│   ├── .env.production            # Actual values (git-ignored)
│   └── README.md                  # Setup instructions
├── staging/
│   ├── .env.staging.template
│   └── .env.staging
└── development/
    └── .env.development
```

### Git Configuration

```bash
# .gitignore
.env.production
.env.production.local
.env.staging
*.key
*.pem
secrets/
```

## Deployment Commands

### Initial Setup

```bash
# 1. Copy template
cp config/production/.env.production.template config/production/.env.production

# 2. Generate secrets
./scripts/generate-production-secrets.sh

# 3. Validate configuration
./scripts/validate-production-config.sh

# 4. Deploy
docker-compose -f docker-compose.production.yml \
  --env-file config/production/.env.production \
  up -d
```

### Update Configuration

```bash
# 1. Update environment file
vim config/production/.env.production

# 2. Validate changes
./scripts/validate-production-config.sh

# 3. Reload services (zero-downtime)
docker-compose -f docker-compose.production.yml \
  --env-file config/production/.env.production \
  up -d --no-deps --build api
```
