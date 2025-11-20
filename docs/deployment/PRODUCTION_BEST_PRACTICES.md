# Corporate Intelligence Platform - Production Deployment Best Practices

**Version:** 1.0.0
**Last Updated:** 2025-10-25
**Status:** Production Reference Guide

---

## Table of Contents

1. [FastAPI Production Configuration](#1-fastapi-production-configuration)
2. [PostgreSQL Production Hardening](#2-postgresql-production-hardening)
3. [Redis Production Configuration](#3-redis-production-configuration)
4. [External API Resilience](#4-external-api-resilience)
5. [Security Hardening](#5-security-hardening)
6. [Disaster Recovery](#6-disaster-recovery)
7. [Performance Optimization](#7-performance-optimization)
8. [Monitoring & Observability](#8-monitoring--observability)

---

## 1. FastAPI Production Configuration

### 1.1 ASGI Server Configuration

#### Gunicorn + Uvicorn Workers (Recommended)

**Current Implementation** (Dockerfile, line 141-152):
```dockerfile
CMD ["gunicorn", "src.api.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50"]
```

**Best Practices:**

1. **Worker Count Calculation**
   ```bash
   # Formula: (2 x CPU cores) + 1
   # For 4 cores: (2 x 4) + 1 = 9 workers
   # Current setting: 4 (conservative for 8GB RAM constraint)
   ```

2. **Resource-Based Worker Tuning**
   ```yaml
   # For 8GB RAM server
   workers: 4                    # Conservative
   threads: 2                    # Threads per worker
   worker_class: uvicorn.workers.UvicornWorker

   # For 16GB RAM server
   workers: 9                    # Optimal
   threads: 1                    # Single-threaded async workers

   # For 32GB RAM server
   workers: 17                   # (2 x 8) + 1
   threads: 1
   ```

3. **Timeout Configuration**
   ```bash
   --timeout 120              # Request timeout (2 minutes)
   --graceful-timeout 30      # Graceful shutdown time
   --keep-alive 5             # Keep-alive connections (seconds)
   ```

4. **Worker Lifecycle Management**
   ```bash
   --max-requests 1000        # Restart after N requests (prevents memory leaks)
   --max-requests-jitter 50   # Randomize restart (prevents thundering herd)
   --worker-tmp-dir /dev/shm  # Use shared memory for better performance
   ```

#### Environment-Specific Configurations

**Development:**
```bash
uvicorn src.api.main:app --reload --workers 1 --log-level debug
```

**Staging:**
```bash
gunicorn src.api.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8000 \
  --timeout 90 \
  --log-level info
```

**Production:**
```bash
gunicorn src.api.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --worker-tmp-dir /dev/shm \
  --access-logfile - \
  --error-logfile - \
  --log-level warning \
  --preload                      # Preload app before forking workers
```

### 1.2 Request Limits & Timeouts

**Current Implementation** (docker-compose.production.yml):
```yaml
environment:
  API_WORKERS: 4
  API_TIMEOUT: 120
  RATE_LIMIT_ENABLED: true
```

**Recommendations:**

```python
# src/core/config.py
class Settings(BaseSettings):
    # Server Configuration
    API_WORKERS: int = 4
    API_TIMEOUT: int = 120
    API_GRACEFUL_TIMEOUT: int = 30
    API_KEEP_ALIVE: int = 5

    # Request Limits
    MAX_REQUEST_SIZE: int = 10_485_760  # 10MB
    MAX_UPLOAD_SIZE: int = 104_857_600  # 100MB
    REQUEST_TIMEOUT: int = 120

    # Connection Limits
    MAX_CONNECTIONS_PER_WORKER: int = 1000
    BACKLOG: int = 2048  # Socket backlog
```

**nginx Configuration** (config/nginx-ssl.conf):
```nginx
http {
    client_max_body_size 100M;
    client_body_timeout 120s;
    client_header_timeout 60s;
    keepalive_timeout 65s;
    send_timeout 120s;

    proxy_connect_timeout 60s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;

    # Buffer sizes
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
}
```

### 1.3 Worker Process Scaling

**Horizontal Pod Autoscaling** (k8s/base/hpa.yaml):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: corporate-intel-api
spec:
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 120
```

**Key Considerations:**
- **CPU-based scaling**: Scale at 70% CPU (allows headroom for traffic spikes)
- **Memory-based scaling**: Scale at 75% memory (prevent OOM kills)
- **Scale-up**: Aggressive (100% increase every 60s)
- **Scale-down**: Conservative (50% decrease every 120s with 5-min stabilization)

---

## 2. PostgreSQL Production Hardening

### 2.1 Connection Pooling

#### Current Configuration
**docker-compose.production.yml**:
```yaml
environment:
  POSTGRES_MAX_CONNECTIONS: 200
  DB_POOL_SIZE: 30
  DB_MAX_OVERFLOW: 20
```

#### Recommended PgBouncer Configuration

**Why PgBouncer?**
- Reduces connection overhead
- Enables connection reuse
- Supports 10,000+ client connections with only 100 database connections

**deployment/pgbouncer.ini**:
```ini
[databases]
corporate_intel = host=postgres port=5432 dbname=corporate_intel

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

# Connection Pooling
pool_mode = transaction            # Most efficient for web apps
max_client_conn = 10000           # Maximum client connections
default_pool_size = 25            # Connections per database
reserve_pool_size = 5             # Emergency connections
reserve_pool_timeout = 3          # Seconds before using reserve pool

# Timeouts
server_idle_timeout = 600         # Close idle server connections (10 min)
server_lifetime = 3600            # Force reconnect after 1 hour
query_timeout = 120               # Kill queries after 2 minutes
client_idle_timeout = 300         # Close idle clients (5 min)

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
```

**Docker Compose Integration**:
```yaml
services:
  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    container_name: corporate-intel-pgbouncer
    restart: always
    environment:
      DATABASE_URL: postgres://postgres:${POSTGRES_PASSWORD}@postgres:5432/corporate_intel
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 10000
      DEFAULT_POOL_SIZE: 25
    ports:
      - "127.0.0.1:6432:6432"
    depends_on:
      postgres:
        condition: service_healthy
```

**Application Configuration**:
```python
# Update connection string to use PgBouncer
SQLALCHEMY_DATABASE_URI = "postgresql+asyncpg://user:pass@pgbouncer:6432/corporate_intel"

# Reduce application pool size (PgBouncer handles pooling)
DB_POOL_SIZE: int = 10
DB_MAX_OVERFLOW: int = 5
```

### 2.2 Query Optimization

**Current Configuration**:
```yaml
POSTGRES_SHARED_BUFFERS: 2GB
POSTGRES_EFFECTIVE_CACHE_SIZE: 6GB
POSTGRES_MAINTENANCE_WORK_MEM: 512MB
POSTGRES_WORK_MEM: 10485kB
```

#### Performance Tuning Guidelines

**For 8GB RAM Server**:
```conf
# Memory Settings
shared_buffers = 2GB                    # 25% of RAM
effective_cache_size = 6GB              # 75% of RAM
maintenance_work_mem = 512MB            # For VACUUM, CREATE INDEX
work_mem = 10485kB                      # Per query operation

# Checkpoint Settings
checkpoint_completion_target = 0.9      # Spread checkpoint writes
wal_buffers = 16MB
min_wal_size = 2GB
max_wal_size = 8GB

# Query Planner
default_statistics_target = 100         # ANALYZE sample size
random_page_cost = 1.1                  # For SSD storage
effective_io_concurrency = 200          # For SSD storage

# Connections
max_connections = 200                   # Total connections allowed
```

**For 16GB RAM Server**:
```conf
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 20971kB
```

#### Query Performance Best Practices

1. **Add Indexes on Foreign Keys**
   ```sql
   -- Current implementation (alembic migrations)
   CREATE INDEX idx_companies_ticker ON companies(ticker);
   CREATE INDEX idx_filings_company_id ON filings(company_id);
   CREATE INDEX idx_filings_filing_date ON filings(filing_date);

   -- Additional recommended indexes
   CREATE INDEX idx_metrics_company_id_date ON metrics(company_id, date);
   CREATE INDEX idx_news_published_at ON news(published_at);
   ```

2. **Enable Query Logging**
   ```conf
   log_min_duration_statement = 1000     # Log queries > 1 second
   log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
   log_checkpoints = on
   log_connections = on
   log_disconnections = on
   log_lock_waits = on
   ```

3. **Monitor Slow Queries**
   ```sql
   -- Install pg_stat_statements extension
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

   -- Find top 10 slowest queries
   SELECT
       calls,
       total_time::numeric(10,2) as total_time_ms,
       mean_time::numeric(10,2) as mean_time_ms,
       query
   FROM pg_stat_statements
   ORDER BY total_time DESC
   LIMIT 10;
   ```

### 2.3 Backup Strategies

**Current Implementation**: `scripts/backup/backup-database.sh`

#### Three-Tier Backup Strategy

**Tier 1: Continuous WAL Archiving**
```conf
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://corporate-intel-backups/wal/%f'
archive_timeout = 300  # Archive every 5 minutes
```

**Tier 2: Daily Full Backups**
```bash
#!/bin/bash
# Automated daily backup with compression

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="corporate_intel_${TIMESTAMP}.sql.gz"

# Full backup with custom format (supports parallel restore)
pg_dump \
  -h postgres \
  -U postgres \
  -d corporate_intel \
  --format=custom \
  --compress=9 \
  --verbose \
  --file="/backups/${BACKUP_FILE}"

# Upload to S3 with encryption
aws s3 cp "/backups/${BACKUP_FILE}" \
  "s3://corporate-intel-backups/daily/" \
  --storage-class INTELLIGENT_TIERING \
  --server-side-encryption AES256

# Verify integrity
pg_restore --list "/backups/${BACKUP_FILE}" > /dev/null
if [ $? -eq 0 ]; then
    echo "Backup verified successfully"
else
    echo "ERROR: Backup verification failed"
    exit 1
fi
```

**Tier 3: Weekly Schema-Only Backups**
```bash
# Schema-only backup for quick recovery testing
pg_dump \
  -h postgres \
  -U postgres \
  -d corporate_intel \
  --schema-only \
  --file="/backups/schema_${TIMESTAMP}.sql"
```

#### Backup Retention Policy

```yaml
Retention Schedule:
  WAL Archives: 7 days (continuous)
  Daily Backups: 30 days
  Weekly Backups: 90 days
  Monthly Backups: 1 year
  Yearly Backups: 7 years (compliance)
```

**S3 Lifecycle Policy**:
```json
{
  "Rules": [
    {
      "Id": "BackupTransitionRule",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 2555
      }
    }
  ]
}
```

#### Backup Verification & Testing

**Automated Verification**:
```bash
#!/bin/bash
# Test restore to temporary database weekly

# Create test database
createdb corporate_intel_restore_test

# Restore from latest backup
pg_restore \
  --dbname=corporate_intel_restore_test \
  --jobs=4 \
  --verbose \
  /backups/latest.sql.gz

# Verify critical tables
psql -d corporate_intel_restore_test -c "
SELECT
    'companies' as table_name, COUNT(*) as row_count FROM companies
UNION ALL
SELECT 'filings', COUNT(*) FROM filings
UNION ALL
SELECT 'metrics', COUNT(*) FROM metrics;
"

# Cleanup
dropdb corporate_intel_restore_test
```

**Recovery Time Objectives (RTO)**:
```yaml
RTO Targets:
  Critical Failure: 4 hours
  Data Corruption: 2 hours
  Accidental Deletion: 30 minutes

RPO Targets:
  Database: 5 minutes (WAL archiving)
  Application State: 15 minutes
  User Data: 0 minutes (continuous)
```

---

## 3. Redis Production Configuration

### 3.1 Persistence Settings

**Current Implementation**:
```yaml
redis:
  command: >
    redis-server
    --appendonly yes
    --appendfsync everysec
    --maxmemory 4gb
    --maxmemory-policy allkeys-lru
```

#### Persistence Strategy Recommendations

**1. RDB + AOF Hybrid (Recommended)**
```conf
# RDB Snapshots (for fast restarts)
save 900 1          # Save if >=1 key changed in 15 minutes
save 300 10         # Save if >=10 keys changed in 5 minutes
save 60 10000       # Save if >=10,000 keys changed in 1 minute
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb

# AOF (for durability)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec              # Good balance: sync every second
no-appendfsync-on-rewrite no      # Don't fsync during BGSAVE/BGREWRITEAOF
auto-aof-rewrite-percentage 100   # Rewrite when AOF is 100% bigger
auto-aof-rewrite-min-size 64mb    # Minimum size to trigger rewrite
```

**Trade-offs**:
```
appendfsync options:
- always:   Maximum durability, slow writes (~500 ops/sec)
- everysec: Good balance, potential 1-second data loss (recommended)
- no:       Fast, relies on OS fsync, potential data loss
```

### 3.2 Eviction Policies

**Current**: `allkeys-lru` (good for cache)

#### Policy Selection Guide

```yaml
Eviction Policies:
  allkeys-lru:      # Remove least recently used keys (any key)
    Use Case: Pure cache, no persistence needed
    Current: YES

  volatile-lru:     # Remove LRU keys with TTL set
    Use Case: Mix of cache + persistent data

  allkeys-lfu:      # Remove least frequently used keys
    Use Case: Access patterns vary significantly

  volatile-ttl:     # Remove keys with shortest TTL
    Use Case: Time-sensitive data

  noeviction:       # Return errors when memory limit reached
    Use Case: Critical data, never evict (not recommended)
```

**Recommended Configuration**:
```conf
maxmemory 4gb
maxmemory-policy allkeys-lru
maxmemory-samples 5      # Number of keys to sample for LRU
```

### 3.3 High Availability (Redis Sentinel)

**Current**: Single instance
**Recommended**: Redis Sentinel for production

**docker-compose.production.yml enhancement**:
```yaml
services:
  redis-master:
    image: redis:7.2-alpine
    container_name: corporate-intel-redis-master
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./config/redis-master.conf:/usr/local/etc/redis/redis.conf
      - redis_master_data:/data
    networks:
      - backend

  redis-replica-1:
    image: redis:7.2-alpine
    container_name: corporate-intel-redis-replica-1
    command: redis-server /usr/local/etc/redis/redis.conf --replicaof redis-master 6379
    volumes:
      - ./config/redis-replica.conf:/usr/local/etc/redis/redis.conf
      - redis_replica1_data:/data
    depends_on:
      - redis-master
    networks:
      - backend

  redis-sentinel-1:
    image: redis:7.2-alpine
    container_name: corporate-intel-redis-sentinel-1
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./config/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - backend
```

**sentinel.conf**:
```conf
port 26379
sentinel monitor corporate-intel-master redis-master 6379 2
sentinel down-after-milliseconds corporate-intel-master 5000
sentinel parallel-syncs corporate-intel-master 1
sentinel failover-timeout corporate-intel-master 10000
```

**Application Configuration**:
```python
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [('sentinel-1', 26379), ('sentinel-2', 26379), ('sentinel-3', 26379)],
    socket_timeout=0.1
)

# Get master for writes
master = sentinel.master_for(
    'corporate-intel-master',
    socket_timeout=0.1,
    password='${REDIS_PASSWORD}'
)

# Get replica for reads
replica = sentinel.slave_for(
    'corporate-intel-master',
    socket_timeout=0.1,
    password='${REDIS_PASSWORD}'
)
```

---

## 4. External API Resilience

### 4.1 Circuit Breaker Pattern

**Current**: Basic retry logic in connectors
**Recommended**: Implement circuit breaker

**Implementation** (src/resilience/circuit_breaker.py):
```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)
        )

    def _on_success(self):
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

**Usage in Connectors**:
```python
from src.resilience.circuit_breaker import CircuitBreaker

class SECEdgarConnector:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60
        )

    async def get_company_filings(self, ticker: str):
        return await self.circuit_breaker.call(
            self._fetch_filings,
            ticker
        )
```

### 4.2 Retry Strategies

**Current Implementation**: Basic exponential backoff in `src/connectors/data_sources.py`

**Enhanced Retry Configuration**:
```python
import tenacity
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

class ExternalAPIConnector:
    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def fetch_data(self, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.json()
```

**Per-API Configuration**:
```yaml
API Retry Policies:
  SEC EDGAR:
    max_attempts: 3
    backoff: exponential
    initial_wait: 2s
    max_wait: 30s
    jitter: true

  Yahoo Finance:
    max_attempts: 5
    backoff: exponential
    initial_wait: 1s
    max_wait: 60s
    jitter: true

  Alpha Vantage:
    max_attempts: 3
    backoff: linear
    initial_wait: 5s
    max_wait: 30s
    respect_retry_after: true
```

### 4.3 Rate Limiting

**Current**: Token bucket implementation in `src/middleware/rate_limiting.py` (excellent!)

**Enhancements**:

1. **Distributed Rate Limiting with Redis**
   - Already implemented via Lua script
   - Add monitoring for rate limit violations

2. **Per-API Rate Limiters**
   ```python
   # src/connectors/rate_limiters.py

   API_RATE_LIMITS = {
       "sec_edgar": RateLimiter(calls_per_second=10),
       "yahoo_finance": RateLimiter(calls_per_second=2),
       "alpha_vantage": RateLimiter(calls_per_second=5),
       "newsapi": RateLimiter(calls_per_second=1),
   }
   ```

3. **Adaptive Rate Limiting**
   ```python
   class AdaptiveRateLimiter:
       def __init__(self, initial_rate: float):
           self.current_rate = initial_rate
           self.min_rate = initial_rate * 0.5
           self.max_rate = initial_rate * 2.0

       async def adjust_rate(self, success: bool):
           if success:
               # Increase rate on success
               self.current_rate = min(
                   self.current_rate * 1.1,
                   self.max_rate
               )
           else:
               # Decrease rate on failure
               self.current_rate = max(
                   self.current_rate * 0.5,
                   self.min_rate
               )
   ```

---

## 5. Security Hardening

### 5.1 SSL/TLS Configuration

**nginx SSL Configuration** (config/nginx-ssl.conf):
```nginx
server {
    listen 443 ssl http2;
    server_name api.corporate-intel.com;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/corporate-intel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/corporate-intel.com/privkey.pem;

    # SSL Configuration (Mozilla Modern)
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # SSL Session Cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/corporate-intel.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP to HTTPS Redirect
server {
    listen 80;
    server_name api.corporate-intel.com;
    return 301 https://$server_name$request_uri;
}
```

### 5.2 Secrets Management

**Current**: Environment variables
**Recommended**: HashiCorp Vault or AWS Secrets Manager

**AWS Secrets Manager Integration**:
```python
# src/core/secrets.py

import boto3
import json
from functools import lru_cache

class SecretsManager:
    def __init__(self):
        self.client = boto3.client('secretsmanager')

    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str) -> dict:
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

# Usage
secrets = SecretsManager()
db_creds = secrets.get_secret("corporate-intel/production/database")
redis_creds = secrets.get_secret("corporate-intel/production/redis")
```

**Environment Variable Rotation**:
```bash
# scripts/rotate-secrets.sh

#!/bin/bash
# Rotate database password

NEW_PASSWORD=$(openssl rand -base64 32)

# Update in Secrets Manager
aws secretsmanager update-secret \
    --secret-id corporate-intel/production/database \
    --secret-string "{\"password\": \"$NEW_PASSWORD\"}"

# Update database
psql -h postgres -U postgres -c "ALTER USER postgres PASSWORD '$NEW_PASSWORD';"

# Restart application (K8s will pull new secret)
kubectl rollout restart deployment/corporate-intel-api
```

### 5.3 API Authentication

**Current**: JWT-based authentication in `src/auth/`

**Best Practices**:

1. **JWT Configuration**
   ```python
   # src/auth/config.py

   JWT_ALGORITHM = "RS256"  # Use RSA instead of HS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
   JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
   JWT_ISSUER = "corporate-intel-api"
   JWT_AUDIENCE = "corporate-intel-app"
   ```

2. **API Key Management**
   ```python
   # src/auth/api_keys.py

   class APIKey(BaseModel):
       key: str
       tier: str  # free, basic, premium, enterprise
       rate_limit: int
       expires_at: datetime
       scopes: List[str]  # Limited permissions

   async def validate_api_key(key: str) -> APIKey:
       # Hash API key before storage
       key_hash = hashlib.sha256(key.encode()).hexdigest()

       # Check in database/cache
       api_key = await get_api_key_by_hash(key_hash)

       if not api_key or api_key.expires_at < datetime.utcnow():
           raise HTTPException(401, "Invalid or expired API key")

       return api_key
   ```

3. **IP Whitelisting (Enterprise)**
   ```python
   # src/middleware/ip_whitelist.py

   ENTERPRISE_IP_WHITELIST = {
       "enterprise-client-1": ["52.1.2.3", "52.1.2.4"],
       "enterprise-client-2": ["10.0.0.0/8"],
   }

   async def check_ip_whitelist(request: Request):
       client_ip = request.client.host
       api_key = request.headers.get("X-API-Key")

       if api_key in ENTERPRISE_IP_WHITELIST:
           allowed_ips = ENTERPRISE_IP_WHITELIST[api_key]
           if not is_ip_allowed(client_ip, allowed_ips):
               raise HTTPException(403, "IP not whitelisted")
   ```

---

## 6. Disaster Recovery

### 6.1 RTO/RPO Targets

**Defined Recovery Objectives**:

```yaml
Service Level Objectives:
  API Availability: 99.9%  # 43 minutes downtime/month
  Data Durability: 99.999999999%  # 11 nines

Recovery Time Objectives (RTO):
  Critical System Failure: 4 hours
  Database Corruption: 2 hours
  Accidental Data Deletion: 30 minutes
  Regional Outage: 1 hour (failover to backup region)

Recovery Point Objectives (RPO):
  Database: 5 minutes (continuous WAL archiving)
  Application State: 15 minutes
  User-Generated Content: 0 minutes (real-time replication)
```

### 6.2 Backup Verification

**Automated Backup Testing** (scripts/verify-backup.sh):
```bash
#!/bin/bash
# Weekly automated restore test

set -euo pipefail

BACKUP_FILE="$1"
TEST_DB="corporate_intel_restore_test_$(date +%Y%m%d)"

echo "Testing backup restore: $BACKUP_FILE"

# Create test database
createdb "$TEST_DB"

# Restore backup
pg_restore \
    --dbname="$TEST_DB" \
    --jobs=4 \
    --verbose \
    --no-owner \
    --no-acl \
    "$BACKUP_FILE" 2>&1 | tee restore_test.log

# Verify critical tables
psql -d "$TEST_DB" -c "
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
        n_live_tup as row_count
    FROM pg_stat_user_tables
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Run integrity checks
psql -d "$TEST_DB" -c "
    -- Check for null critical fields
    SELECT COUNT(*) as invalid_companies
    FROM companies
    WHERE ticker IS NULL OR name IS NULL;

    -- Verify foreign key integrity
    SELECT COUNT(*) as orphaned_filings
    FROM filings f
    LEFT JOIN companies c ON f.company_id = c.id
    WHERE c.id IS NULL;
"

# Cleanup
dropdb "$TEST_DB"

echo "Backup verification completed successfully"
```

### 6.3 Failover Procedures

**Multi-Region Failover**:

```yaml
Primary Region: us-east-1
Backup Region: us-west-2

Failover Triggers:
  - Region-wide outage
  - RTO exceeded (4 hours)
  - Data center failure
```

**Automated Failover** (scripts/failover.sh):
```bash
#!/bin/bash
# Automated failover to backup region

PRIMARY_ENDPOINT="https://api.corporate-intel.com"
BACKUP_ENDPOINT="https://api-backup.corporate-intel.com"

# Check primary health
if ! curl -f "$PRIMARY_ENDPOINT/health" --max-time 10; then
    echo "Primary region unhealthy, initiating failover"

    # Update Route53 to point to backup
    aws route53 change-resource-record-sets \
        --hosted-zone-id Z1234567890ABC \
        --change-batch '{
            "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "api.corporate-intel.com",
                    "Type": "A",
                    "AliasTarget": {
                        "HostedZoneId": "Z0987654321XYZ",
                        "DNSName": "backup-lb.us-west-2.elb.amazonaws.com",
                        "EvaluateTargetHealth": true
                    }
                }
            }]
        }'

    # Send alert
    aws sns publish \
        --topic-arn arn:aws:sns:us-east-1:123456789:critical-alerts \
        --message "FAILOVER: Primary region failed, now serving from us-west-2"
fi
```

**Manual Failover Checklist**:
```markdown
## Disaster Recovery Failover Procedure

### Pre-Failover (5 minutes)
- [ ] Confirm primary region is unrecoverable
- [ ] Alert team via PagerDuty
- [ ] Join incident war room (Slack #incidents)
- [ ] Assign Incident Commander

### Failover Execution (15 minutes)
- [ ] Stop writes to primary database
- [ ] Promote read replica to master in backup region
- [ ] Update DNS records (Route53)
- [ ] Verify backup region health
- [ ] Test critical API endpoints
- [ ] Monitor error rates and latency

### Post-Failover (30 minutes)
- [ ] Communicate status to customers
- [ ] Update status page
- [ ] Begin incident postmortem
- [ ] Schedule primary region recovery
- [ ] Document lessons learned
```

---

## 7. Performance Optimization

### 7.1 Database Query Optimization

**Query Performance Monitoring**:
```sql
-- Install pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Monitor top slow queries
SELECT
    calls,
    total_time::numeric(10,2) as total_ms,
    mean_time::numeric(10,2) as mean_ms,
    min_time::numeric(10,2) as min_ms,
    max_time::numeric(10,2) as max_ms,
    stddev_time::numeric(10,2) as stddev_ms,
    LEFT(query, 100) as query_sample
FROM pg_stat_statements
WHERE mean_time > 100  -- Queries averaging >100ms
ORDER BY total_time DESC
LIMIT 20;
```

**Index Optimization**:
```sql
-- Find missing indexes
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    CASE
        WHEN seq_scan > 0
        THEN seq_tup_read / seq_scan
        ELSE 0
    END as avg_seq_tup_read
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_tup_read DESC
LIMIT 20;

-- Create recommended indexes
CREATE INDEX CONCURRENTLY idx_metrics_company_date
ON metrics(company_id, date DESC);

CREATE INDEX CONCURRENTLY idx_filings_type_date
ON filings(filing_type, filing_date DESC);
```

### 7.2 Caching Strategy

**Multi-Layer Caching**:

```python
# src/core/caching.py

from typing import Optional
import hashlib
import json

class CacheManager:
    def __init__(self, redis_client, ttl_short=300, ttl_long=3600):
        self.redis = redis_client
        self.ttl_short = ttl_short  # 5 minutes
        self.ttl_long = ttl_long    # 1 hour

    async def get_or_fetch(
        self,
        cache_key: str,
        fetch_func,
        ttl: Optional[int] = None,
    ):
        # Try L1 cache (in-memory)
        if hasattr(self, '_memory_cache'):
            value = self._memory_cache.get(cache_key)
            if value:
                return value

        # Try L2 cache (Redis)
        value = await self.redis.get(cache_key)
        if value:
            return json.loads(value)

        # Cache miss - fetch from source
        value = await fetch_func()

        # Store in both cache layers
        ttl = ttl or self.ttl_short
        await self.redis.setex(cache_key, ttl, json.dumps(value))

        return value
```

**Cache Warming**:
```python
# scripts/warm_cache.py

async def warm_cache():
    """Preload frequently accessed data into cache"""

    # Top 100 companies
    companies = await db.get_top_companies(limit=100)
    for company in companies:
        cache_key = f"company:{company.id}"
        await cache.set(cache_key, company.dict(), ttl=3600)

    # Latest filings
    filings = await db.get_recent_filings(limit=1000)
    for filing in filings:
        cache_key = f"filing:{filing.id}"
        await cache.set(cache_key, filing.dict(), ttl=1800)
```

### 7.3 Connection Pooling

**Optimized Database Pool**:
```python
# src/db/session.py

from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=30,              # Base pool size
    max_overflow=20,           # Additional connections
    pool_pre_ping=True,        # Verify connections before use
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_timeout=30,           # Wait 30s for connection
)
```

---

## 8. Monitoring & Observability

### 8.1 Key Metrics to Track

**Application Metrics** (Prometheus):
```yaml
API Performance:
  - http_request_duration_seconds (p50, p95, p99)
  - http_requests_total (by endpoint, status_code)
  - http_requests_in_flight

Database:
  - db_connections_active
  - db_connections_idle
  - db_query_duration_seconds
  - db_transaction_duration_seconds

Cache:
  - cache_hit_ratio
  - cache_key_count
  - cache_memory_usage_bytes

External APIs:
  - api_call_duration_seconds (by provider)
  - api_call_errors_total (by provider, error_type)
  - api_rate_limit_remaining
```

**Business Metrics**:
```yaml
Usage:
  - daily_active_users
  - api_requests_per_user
  - data_ingestion_volume

Performance:
  - average_response_time
  - error_rate_percentage
  - uptime_percentage
```

### 8.2 Alerting Rules

**Prometheus Alerts** (config/production/prometheus/alerts/api-alerts.yml):
```yaml
groups:
- name: api_alerts
  interval: 30s
  rules:
  - alert: HighErrorRate
    expr: |
      (
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        /
        sum(rate(http_requests_total[5m]))
      ) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High API error rate detected"
      description: "Error rate is {{ $value }}% (threshold: 5%)"

  - alert: SlowAPIResponse
    expr: |
      histogram_quantile(0.95,
        rate(http_request_duration_seconds_bucket[5m])
      ) > 2.0
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Slow API responses detected"
      description: "P95 latency is {{ $value }}s (threshold: 2s)"

  - alert: DatabaseConnectionPoolExhausted
    expr: db_connections_active >= db_connections_max * 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Database connection pool nearly exhausted"
      description: "{{ $value }} connections active (90% of max)"
```

### 8.3 Log Aggregation

**Structured Logging** (already implemented with Loguru):
```python
# src/core/logging.py

from loguru import logger
import sys
import json

def setup_logging(environment: str):
    # Remove default handler
    logger.remove()

    # Add structured JSON logging for production
    if environment == "production":
        logger.add(
            sys.stdout,
            format="{message}",
            serialize=True,  # JSON output
            level="INFO",
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG",
        )

    # Add file handler with rotation
    logger.add(
        "/app/logs/app.log",
        rotation="100 MB",
        retention="30 days",
        compression="gz",
        level="INFO",
    )
```

**CloudWatch Integration**:
```python
# Send logs to CloudWatch
import watchtower

logger.add(
    watchtower.CloudWatchLogHandler(
        log_group="/aws/corporate-intel/production",
        stream_name="api-server",
    ),
    format="{message}",
    serialize=True,
)
```

---

## Summary Checklist

### Pre-Production Deployment

**Infrastructure:**
- [ ] Configure Gunicorn workers: 4-9 workers based on CPU
- [ ] Set up PgBouncer for connection pooling
- [ ] Configure PostgreSQL performance tuning
- [ ] Implement Redis Sentinel for HA
- [ ] Set up automated backups (daily + WAL archiving)

**Security:**
- [ ] Configure SSL/TLS with strong ciphers
- [ ] Implement secrets rotation
- [ ] Set up API authentication (JWT + API keys)
- [ ] Configure network policies and firewalls

**Resilience:**
- [ ] Implement circuit breakers for external APIs
- [ ] Configure retry strategies with exponential backoff
- [ ] Set up rate limiting (already done!)
- [ ] Create disaster recovery runbooks

**Monitoring:**
- [ ] Deploy Prometheus + Grafana dashboards
- [ ] Configure critical alerts
- [ ] Set up log aggregation
- [ ] Test backup restore procedures

**Testing:**
- [ ] Load test with expected traffic (2x capacity)
- [ ] Chaos engineering (kill pods, network failures)
- [ ] Backup restore verification
- [ ] Disaster recovery drill

---

**Document Version:** 1.0.0
**Last Review Date:** 2025-10-25
**Next Review:** 2025-11-25
