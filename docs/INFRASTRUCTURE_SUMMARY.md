# Infrastructure Summary

## Overview

This document provides a comprehensive summary of the Corporate Intelligence Platform infrastructure, including all configuration files, deployment procedures, and operational runbooks.

## Infrastructure Components

### 1. Core Services

| Service | Technology | Purpose | Port(s) |
|---------|-----------|---------|---------|
| API | FastAPI + Gunicorn | REST API application | 8000 |
| Database | PostgreSQL 15 + TimescaleDB | Primary data store | 5432 |
| Cache | Redis 7 | Caching and sessions | 6379 |
| Object Storage | MinIO | Document storage | 9000, 9001 |
| Reverse Proxy | Nginx | SSL/TLS termination | 80, 443 |

### 2. Observability Stack

| Service | Purpose | Port |
|---------|---------|------|
| Prometheus | Metrics collection | 9090 |
| Grafana | Metrics visualization | 3000 |
| Jaeger | Distributed tracing | 16686, 4317, 4318 |
| Node Exporter | System metrics | 9100 |
| Postgres Exporter | Database metrics | 9187 |
| Redis Exporter | Cache metrics | 9121 |
| cAdvisor | Container metrics | 8080 |

## Configuration Files

### Production Configuration

```
corporate-intel/
├── docker-compose.yml              # Development services
├── docker-compose.prod.yml         # Production services + monitoring
├── Dockerfile                      # Production container image
├── Dockerfile.dev                  # Development container image
├── requirements-prod.txt           # Pinned production dependencies
├── .env.production                 # Production environment variables
├── .env.staging                    # Staging environment variables
│
├── config/
│   ├── nginx.conf                 # Nginx reverse proxy config
│   └── prometheus.yml             # Prometheus scrape config
│
├── scripts/
│   ├── backup.sh                  # Automated backup script
│   ├── restore.sh                 # Database restore script
│   └── validate-deployment.sh     # Pre/post deployment checks
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml              # GitHub Actions CI/CD pipeline
│
└── docs/
    ├── DEPLOYMENT_CHECKLIST.md    # Production deployment steps
    ├── LOCAL_DEVELOPMENT.md       # Local development setup
    └── INFRASTRUCTURE_SUMMARY.md  # This file
```

## Deployment Modes

### 1. Local Development

**Purpose**: Developer workstations
**Command**: `docker-compose up -d`
**Features**:
- Hot reload enabled
- Debug mode on
- Minimal monitoring
- Sample data seeding

**Services**: PostgreSQL, Redis, MinIO, API (development mode)

### 2. Staging Environment

**Purpose**: Pre-production testing
**Command**: `docker-compose -f docker-compose.prod.yml --env-file .env.staging up -d`
**Features**:
- Production-like configuration
- Full monitoring stack
- SSL with self-signed certificates
- Automated backups

**Services**: All production services + observability stack

### 3. Production Environment

**Purpose**: Live production deployment
**Command**: `docker-compose -f docker-compose.prod.yml --env-file .env.production up -d`
**Features**:
- Production-hardened configuration
- Let's Encrypt SSL certificates
- Full monitoring and alerting
- Automated backups and retention
- Log aggregation

**Services**: All services with production tuning

## Security Configuration

### 1. Network Security

```yaml
Firewall Rules:
  - Allow: 80/tcp (HTTP - redirects to HTTPS)
  - Allow: 443/tcp (HTTPS)
  - Allow: 22/tcp (SSH - key-based only)
  - Block: All other ports
  - Internal: Services communicate via Docker network
```

### 2. SSL/TLS Configuration

- **Protocol**: TLS 1.2, TLS 1.3 only
- **Cipher Suites**: Modern, secure ciphers only
- **HSTS**: Enabled with 2-year max-age
- **OCSP Stapling**: Enabled
- **Certificate**: Let's Encrypt (auto-renewal)

### 3. Application Security

- **Authentication**: JWT-based with secure secret rotation
- **Authorization**: Role-based access control (RBAC)
- **Rate Limiting**: 10 req/s per IP (configurable)
- **CORS**: Restricted to allowed origins
- **Input Validation**: Pydantic schema validation
- **SQL Injection**: Protected via SQLAlchemy ORM
- **XSS Protection**: Content Security Policy headers

### 4. Secrets Management

**Development**: `.env` file (gitignored)
**Production**: Environment variables from:
- AWS Secrets Manager
- HashiCorp Vault
- Docker secrets
- Kubernetes secrets

**Never commit**:
- `.env.production`
- SSL certificates
- API keys
- Database passwords

## Backup Strategy

### Automated Backups

| Type | Frequency | Retention | Script |
|------|-----------|-----------|--------|
| Daily | 2 AM UTC | 7 days | `backup.sh daily` |
| Weekly | Sunday 3 AM | 30 days | `backup.sh weekly` |
| Monthly | 1st of month | 365 days | `backup.sh monthly` |

### Backup Contents

1. **PostgreSQL Database** - Full SQL dump (gzipped)
2. **Docker Volumes**:
   - `postgres_data` - Database files
   - `redis_data` - Cache data
   - `minio_data` - Object storage
3. **Metadata** - Backup manifest and metadata JSON

### Backup Location

```
/var/backups/corporate-intel/
├── daily/
│   ├── 20251003_020000/
│   ├── 20251004_020000/
│   └── ...
├── weekly/
│   └── 20251001_030000/
└── monthly/
    └── 20251001_030000/
```

### Restore Procedure

```bash
# List available backups
ls -lh /var/backups/corporate-intel/daily/

# Restore from specific backup
./scripts/restore.sh /var/backups/corporate-intel/daily/20251003_020000

# Verify restoration
docker-compose logs -f api
curl http://localhost:8000/health
```

## Monitoring & Alerting

### Key Metrics

**System Metrics**:
- CPU usage (target: <70%)
- Memory usage (target: <80%)
- Disk usage (alert: >85%)
- Network I/O

**Application Metrics**:
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (target: <0.1%)
- Active connections

**Database Metrics**:
- Query performance
- Connection pool usage
- Lock wait time
- Replication lag

**Cache Metrics**:
- Hit rate (target: >80%)
- Memory usage
- Eviction rate

### Alert Rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| API Down | Health check fails 3x | Critical | Page on-call |
| High Error Rate | >1% errors for 5min | Critical | Page on-call |
| Disk Space Low | >85% used | Warning | Email team |
| Database Slow | p95 >1s for 10min | Warning | Email team |
| Memory High | >90% for 5min | Warning | Email team |
| Backup Failed | No backup in 25h | Critical | Page on-call |

### Notification Channels

- **Critical**: PagerDuty + Email
- **Warning**: Email + Slack
- **Info**: Slack only

## Scaling Strategy

### Vertical Scaling (Single Server)

Current configuration supports:
- **Traffic**: ~1000 req/s
- **Data**: Up to 500GB
- **Users**: ~10,000 concurrent

**Upgrade path**:
1. Increase Gunicorn workers (currently 4)
2. Tune PostgreSQL parameters
3. Add Redis cluster for caching
4. Scale server resources (CPU/RAM)

### Horizontal Scaling (Multi-Server)

For traffic >1000 req/s:

1. **API Tier**:
   - Deploy multiple API containers
   - Add load balancer (HAProxy/Nginx)
   - Share session state via Redis

2. **Database Tier**:
   - PostgreSQL read replicas
   - Connection pooling (PgBouncer)
   - Consider Aurora/RDS for managed scaling

3. **Cache Tier**:
   - Redis Sentinel or Cluster mode
   - Separate cache instances by use case

4. **Storage Tier**:
   - MinIO distributed mode
   - S3-compatible storage (AWS S3, R2)

## CI/CD Pipeline

### GitHub Actions Workflow

```
┌─────────────┐
│ Code Push   │
└──────┬──────┘
       │
       ├──────────────────┐
       │                  │
┌──────▼──────┐    ┌──────▼──────┐
│ Code Quality│    │    Tests    │
│  & Security │    │  (Unit/Int) │
└──────┬──────┘    └──────┬──────┘
       │                  │
       └─────────┬────────┘
                 │
          ┌──────▼──────┐
          │ Build Docker│
          │    Image    │
          └──────┬──────┘
                 │
          ┌──────▼──────┐
          │   Deploy    │
          │   Staging   │
          └──────┬──────┘
                 │
          ┌──────▼──────┐
          │ Smoke Tests │
          └──────┬──────┘
                 │
          ┌──────▼──────┐
          │   Deploy    │
          │ Production  │
          └─────────────┘
```

### Pipeline Stages

1. **Code Quality**: Ruff, Black, mypy, Bandit
2. **Tests**: Unit tests with 80% coverage requirement
3. **Build**: Docker image with layer caching
4. **Deploy Staging**: Auto-deploy on merge to develop
5. **Deploy Production**: Manual approval on tag push

## Performance Tuning

### PostgreSQL

```sql
-- Connection pooling
max_connections = 200
shared_buffers = 2GB
effective_cache_size = 6GB

-- Query performance
work_mem = 16MB
maintenance_work_mem = 512MB
random_page_cost = 1.1

-- Write-ahead log
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### Redis

```conf
maxmemory 2gb
maxmemory-policy allkeys-lru
appendonly yes
```

### Gunicorn

```bash
--workers 4                    # (2 x CPU cores) + 1
--worker-class uvicorn.workers.UvicornWorker
--max-requests 1000           # Restart workers after N requests
--max-requests-jitter 50      # Add jitter to prevent thundering herd
--timeout 120                 # Request timeout
```

## Disaster Recovery

### Recovery Time Objective (RTO)

- **Database**: 15 minutes (restore from latest backup)
- **Full System**: 30 minutes (redeploy all services)

### Recovery Point Objective (RPO)

- **Database**: 24 hours (daily backups)
- **Critical Data**: 1 hour (with WAL archiving)

### DR Procedures

1. **Database Corruption**:
   ```bash
   ./scripts/restore.sh /var/backups/corporate-intel/daily/latest
   ```

2. **Complete System Failure**:
   ```bash
   # On new server
   git clone <repo>
   cp .env.production.backup .env.production
   docker-compose -f docker-compose.prod.yml up -d
   ./scripts/restore.sh /path/to/backup
   ```

3. **Security Breach**:
   - Rotate all secrets immediately
   - Review audit logs
   - Restore from known-good backup
   - Apply security patches

## Operational Runbook

### Common Operations

**View Logs**:
```bash
docker-compose logs -f api
docker-compose logs --tail=100 postgres
```

**Restart Service**:
```bash
docker-compose restart api
```

**Scale API Workers**:
```bash
docker-compose up -d --scale api=3
```

**Database Maintenance**:
```bash
docker exec -it corporate-intel-postgres psql -U intel_prod_user -d corporate_intel_prod
```

**Manual Backup**:
```bash
./scripts/backup.sh daily
```

**Check Service Health**:
```bash
curl http://localhost:8000/health
docker-compose ps
docker stats
```

### Troubleshooting

**API Not Responding**:
1. Check health: `curl localhost:8000/health`
2. View logs: `docker-compose logs api`
3. Check database: `docker-compose ps postgres`
4. Restart: `docker-compose restart api`

**Database Connection Errors**:
1. Check PostgreSQL: `docker-compose logs postgres`
2. Test connection: `docker exec corporate-intel-postgres pg_isready`
3. Check credentials in `.env.production`

**High Memory Usage**:
1. Check stats: `docker stats`
2. Review logs for memory leaks
3. Restart affected service
4. Scale horizontally if persistent

## Maintenance Windows

**Regular Maintenance**:
- **When**: Sunday 2-4 AM UTC
- **Frequency**: Monthly
- **Activities**:
  - System updates
  - Dependency updates
  - Database optimization
  - Log cleanup

**Emergency Maintenance**:
- Coordinate via Slack #incidents
- Page on-call engineer
- Post mortem within 48 hours

## Cost Optimization

### Resource Allocation

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| API | 2 cores | 4GB | 10GB |
| PostgreSQL | 2 cores | 4GB | 100GB |
| Redis | 1 core | 2GB | 10GB |
| MinIO | 1 core | 2GB | 200GB |
| Monitoring | 2 cores | 4GB | 50GB |

**Total**: 8 CPU cores, 16GB RAM, 370GB disk

### Optimization Tips

1. Use spot instances for development
2. Enable log rotation to save disk
3. Archive old data to object storage
4. Use read replicas only when needed
5. Monitor actual usage and right-size

## Compliance & Auditing

**Audit Logs**:
- Application logs: 90 days retention
- Database logs: 30 days retention
- Access logs: 1 year retention
- Security logs: Indefinite (archived)

**Compliance**:
- GDPR: Data anonymization available
- SOC 2: Audit trail enabled
- HIPAA: Encryption at rest and in transit

## Support & Escalation

**Level 1 - General Issues**:
- Slack: #corporate-intel-support
- Email: support@example.com
- Response: 4 hours

**Level 2 - Production Issues**:
- Slack: #corporate-intel-incidents
- Email: incidents@example.com
- Response: 1 hour

**Level 3 - Critical Outages**:
- PagerDuty: On-call engineer
- Phone: Emergency hotline
- Response: 15 minutes

## References

- [Deployment Checklist](/mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docs/DEPLOYMENT_CHECKLIST.md)
- [Local Development Guide](/mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docs/LOCAL_DEVELOPMENT.md)
- [API Documentation](http://localhost:8000/docs)
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
