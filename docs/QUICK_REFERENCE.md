# Quick Reference Guide
**Corporate Intelligence Platform - Essential Commands & Configuration**

**Version:** 0.1.0 | **Last Updated:** October 2, 2025

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Essential Commands](#essential-commands)
3. [API Endpoints](#api-endpoints)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)
6. [Common Tasks](#common-tasks)

---

## Quick Start

### First-Time Setup (5 minutes)

```bash
# 1. Clone and navigate
git clone <repository-url>
cd corporate_intel

# 2. Set up environment
cp .env.example .env
# Edit .env with your credentials

# 3. Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output to .env SECRET_KEY

# 4. Start infrastructure
docker-compose up -d postgres redis minio

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run migrations
alembic upgrade head

# 7. Start API server
uvicorn src.api.main:app --reload

# 8. Verify
curl http://localhost:8000/health
```

**Expected Result:** `{"status": "healthy", "version": "0.1.0"}`

---

## Essential Commands

### Development

```bash
# Start API server (development mode)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Start API server (production mode)
gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Start Dash dashboard
python -m src.visualization.dash_app
# Access at http://localhost:8050
```

### Docker

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis minio

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Remove volumes (⚠️ deletes data!)
docker-compose down -v

# Rebuild API image
docker-compose build api
```

### Database

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration
alembic current

# Show migration history
alembic history
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run tests matching pattern
pytest -k "test_authentication"

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Run all quality checks
black src/ tests/ && ruff check src/ tests/ && mypy src/
```

---

## API Endpoints

### Base URL
- **Development:** `http://localhost:8000`
- **Production:** Configure in deployment

### Health & Monitoring

```bash
# Basic health check
GET /health
# Response: {"status": "healthy", "version": "0.1.0"}

# Database health check
GET /health/database
# Response: {"status": "healthy", "database": "connected", "migrations": "up-to-date"}

# Prometheus metrics
GET /metrics
# Response: Prometheus-formatted metrics

# API documentation (Swagger UI)
GET /api/v1/docs

# API documentation (ReDoc)
GET /api/v1/redoc
```

### Authentication

```bash
# Register new user
POST /auth/register
Content-Type: application/json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}

# Login
POST /auth/login
Content-Type: application/json
{
  "username": "user@example.com",
  "password": "secure_password"
}
# Response: {"access_token": "...", "token_type": "bearer"}

# Get current user
GET /auth/me
Authorization: Bearer <token>

# Create API key
POST /auth/api-keys
Authorization: Bearer <token>
Content-Type: application/json
{
  "name": "My API Key",
  "scopes": ["read:companies", "write:analysis"]
}
```

### Companies API

```bash
# List companies
GET /api/v1/companies?limit=10&offset=0

# Get company by ID
GET /api/v1/companies/{company_id}

# Get company by ticker
GET /api/v1/companies/ticker/{ticker}

# Search companies
GET /api/v1/companies/search?query=edtech&segment=K12

# Create company
POST /api/v1/companies
Authorization: Bearer <token>
Content-Type: application/json
{
  "name": "Example EdTech Corp",
  "ticker": "EDUX",
  "cik": "0001234567",
  "edtech_segment": "K12"
}
```

### Financial Metrics API

```bash
# List metrics for company
GET /api/v1/metrics/company/{company_id}?start_date=2024-01-01&end_date=2024-12-31

# Get specific metric
GET /api/v1/metrics/{metric_id}

# Create metric
POST /api/v1/metrics
Authorization: Bearer <token>
Content-Type: application/json
{
  "company_id": 1,
  "metric_type": "revenue",
  "value": 1500000.00,
  "reporting_date": "2024-09-30",
  "fiscal_quarter": "Q3",
  "fiscal_year": 2024
}
```

### Filings API

```bash
# List filings
GET /api/v1/filings?company_id=1&filing_type=10-K

# Get filing by ID
GET /api/v1/filings/{filing_id}

# Download filing document
GET /api/v1/filings/{filing_id}/download

# Upload filing
POST /api/v1/filings
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

### Intelligence API

```bash
# Run competitive analysis
POST /api/v1/intelligence/competitive
Authorization: Bearer <token>
Content-Type: application/json
{
  "company_ids": [1, 2, 3],
  "analysis_type": "market_position"
}

# Get analysis results
GET /api/v1/intelligence/analysis/{analysis_id}

# Search documents
POST /api/v1/intelligence/search
Content-Type: application/json
{
  "query": "artificial intelligence in education",
  "top_k": 10
}
```

### Reports API

```bash
# Generate performance report
POST /api/v1/reports/performance
Authorization: Bearer <token>
Content-Type: application/json
{
  "company_id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}

# Download report
GET /api/v1/reports/{report_id}/download
```

---

## Configuration

### Environment Variables

**Critical (Required):**
```bash
# Security
SECRET_KEY=<generate_with_secrets.token_urlsafe(32)>

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=corporate_intel

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=<access_key>
MINIO_SECRET_KEY=<secret_key>
```

**Optional (Enhanced Features):**
```bash
# External APIs
ALPHA_VANTAGE_API_KEY=<your_key>
NEWSAPI_KEY=<your_key>
SEC_USER_AGENT=YourCompany/1.0 (your@email.com)

# Observability
SENTRY_DSN=<your_sentry_dsn>
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Application
ENVIRONMENT=development
DEBUG=false
```

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000 |
| Dashboard | 8050 | http://localhost:8050 |
| PostgreSQL | 5432 | postgresql://localhost:5432 |
| Redis | 6379 | redis://localhost:6379 |
| MinIO | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | http://localhost:9001 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |
| Jaeger | 16686 | http://localhost:16686 |

### Default Credentials (Development Only)

**PostgreSQL:**
- User: `intel_user`
- Password: Set in `.env`
- Database: `corporate_intel`

**Redis:**
- No authentication (development)
- Password: Set in `.env` (production)

**MinIO:**
- Access Key: Set in `.env`
- Secret Key: Set in `.env`

**Grafana:**
- User: `admin`
- Password: Set in `.env` (default: `admin`)

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms:** `ModuleNotFoundError`, `ImportError`

**Solutions:**
```bash
# Verify Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/corporate_intel"
```

#### 2. Database Connection Errors

**Symptoms:** `Connection refused`, `FATAL: password authentication failed`

**Solutions:**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database credentials in .env
grep POSTGRES_ .env

# Test connection manually
psql -h localhost -U intel_user -d corporate_intel

# Restart PostgreSQL
docker-compose restart postgres
```

#### 3. Migration Errors

**Symptoms:** `Target database is not up to date`, `revision not found`

**Solutions:**
```bash
# Check current migration
alembic current

# View migration history
alembic history

# Force migration to specific version
alembic upgrade <revision_id>

# Reset migrations (⚠️ development only)
alembic downgrade base
alembic upgrade head
```

#### 4. Redis Connection Errors

**Symptoms:** `ConnectionError`, `Redis is not available`

**Solutions:**
```bash
# Verify Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli ping  # Should return PONG

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

#### 5. Docker Build Failures

**Symptoms:** `ERROR [build X/Y]`, `dependency conflicts`

**Solutions:**
```bash
# Clear Docker cache
docker builder prune -a

# Rebuild without cache
docker-compose build --no-cache api

# Check Docker disk space
docker system df

# Clean up unused images
docker image prune -a
```

#### 6. Authentication Issues

**Symptoms:** `401 Unauthorized`, `Invalid token`

**Solutions:**
```bash
# Verify SECRET_KEY is set
grep SECRET_KEY .env

# Generate new token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}'

# Check token expiration
# Tokens expire after 30 minutes by default
```

### Health Check Commands

```bash
# Check all services
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Check database health
curl http://localhost:8000/health/database

# Check PostgreSQL
docker-compose exec postgres pg_isready

# Check Redis
docker-compose exec redis redis-cli ping

# Check MinIO
curl http://localhost:9000/minio/health/live

# View API logs
docker-compose logs -f api

# View all logs
docker-compose logs --tail=100
```

### Performance Debugging

```bash
# Check resource usage
docker stats

# Check database connections
docker-compose exec postgres psql -U intel_user -d corporate_intel \
  -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory
docker-compose exec redis redis-cli info memory

# Monitor API requests
# View logs with timestamps
docker-compose logs -f --timestamps api

# Profile slow queries
# Enable in PostgreSQL: log_min_duration_statement = 1000
```

---

## Common Tasks

### Adding a New Company

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Corp",
    "ticker": "EXAM",
    "cik": "0001234567",
    "edtech_segment": "Higher Ed"
  }'

# Via Python
python -c "
from src.db.session import get_sync_session
from src.db.models import Company

session = get_sync_session()
company = Company(
    name='Example Corp',
    ticker='EXAM',
    cik='0001234567',
    edtech_segment='Higher Ed'
)
session.add(company)
session.commit()
"
```

### Running Data Ingestion

```bash
# Ingest SEC filings for specific companies
python scripts/ingest_historical_data.py --tickers CHGG,COUR,DUOL

# Run scheduled ingestion workflow
prefect deployment run sec-ingestion-flow/production
```

### Generating Reports

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/reports/performance \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'

# Via Dashboard
# Navigate to http://localhost:8050
# Select company and date range
# Click "Generate Report"
```

### Backing Up Data

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U intel_user corporate_intel > backup.sql

# Backup MinIO buckets
docker-compose exec minio mc mirror minio/corporate-documents ./backups/documents

# Backup Redis
docker-compose exec redis redis-cli --rdb /data/backup.rdb
```

### Restoring Data

```bash
# Restore PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U intel_user corporate_intel

# Restore MinIO
docker-compose exec minio mc mirror ./backups/documents minio/corporate-documents

# Restore Redis
docker-compose exec redis redis-cli --rdb /data/backup.rdb
```

### Monitoring Performance

```bash
# View Prometheus metrics
curl http://localhost:8000/metrics

# Access Grafana dashboards
# http://localhost:3000
# Login: admin / <GRAFANA_PASSWORD>

# View Jaeger traces
# http://localhost:16686

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# curl-format.txt:
# time_total: %{time_total}s
```

---

## Additional Resources

### Documentation
- **Detailed Setup:** See `docs/SETUP_GUIDE.md`
- **Security:** See `docs/SECURITY_SETUP.md`
- **Docker:** See `docs/DOCKER_GUIDE.md`
- **Testing:** See `docs/TEST_ARCHITECTURE.md`

### API Documentation
- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc

### Support
- **GitHub Issues:** <repository-url>/issues
- **Email:** brandon.lambert87@gmail.com

---

## Quick Reference Card

### Most Used Commands

```bash
# Start everything
docker-compose up -d && alembic upgrade head && uvicorn src.api.main:app --reload

# Run tests
pytest --cov=src

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f api

# Format & lint
black src/ tests/ && ruff check src/ tests/

# Stop everything
docker-compose down
```

### Emergency Troubleshooting

```bash
# 1. Nuclear option (⚠️ deletes all data!)
docker-compose down -v
docker-compose up -d
alembic upgrade head

# 2. Check everything
docker-compose ps && curl http://localhost:8000/health

# 3. View logs
docker-compose logs --tail=100
```

---

**Last Updated:** October 2, 2025
**Version:** 0.1.0
**Maintained By:** Code Review Agent
