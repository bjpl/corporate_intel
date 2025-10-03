# Corporate Intelligence Platform - Complete Setup Guide

## 🎯 Overview

The Corporate Intelligence Platform is a comprehensive business intelligence and data analysis system built with Python, Docker, and modern data stack components. This guide will walk you through the complete setup process from scratch.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, macOS, or Linux
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: 20GB free space minimum
- **CPU**: Multi-core processor recommended

### Required Software
- **Docker Desktop**: Latest version
- **Docker Compose**: v3.9 or higher
- **Git**: Latest version
- **Python**: 3.11+ (for development)
- **Node.js**: 18+ (if working with frontend components)

## 🔑 Required API Keys & External Services

### 1. Financial Data APIs

**Alpha Vantage (Stock/Financial Data)**
- **Get from**: https://www.alphavantage.co/support/#api-key
- **Steps**: Register → Get free API key
- **Free tier**: 25 requests/day
- **Cost**: $49.99/month for 1,200 requests/day

**Crunchbase (Company Data)**
- **Get from**: https://data.crunchbase.com/docs/using-the-api
- **Steps**: Create account → Apply for API access
- **Note**: Requires business justification
- **Cost**: Contact for pricing

### 2. News & Media APIs

**NewsAPI (News Articles)**
- **Get from**: https://newsapi.org/
- **Steps**: Register → Get free API key
- **Free tier**: 100 requests/day
- **Cost**: $449/month for unlimited

### 3. Development APIs

**GitHub Token (Repository Analysis)**
- **Get from**: https://github.com/settings/tokens
- **Steps**: Settings → Developer settings → Personal access tokens → Generate new token
- **Scopes needed**: `repo`, `read:org`, `user:email`
- **Free**: Yes

### 4. Email Configuration (Optional)

**SMTP Settings**
- Gmail, Outlook, or custom SMTP server
- Required for alert notifications

## 🚀 Installation Steps

### Step 1: Clone and Setup Repository

```bash
# Clone the repository
git clone https://github.com/bjpl/corporate_intel.git
cd corporate_intel

# Create environment file
cp .env.example .env
```

### Step 2: Configure Environment Variables

Edit the `.env` file with your actual values:

```bash
# Required: Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Database (keep default for local development)
POSTGRES_PASSWORD=your_secure_postgres_password

# Redis (set a strong password)
REDIS_PASSWORD=your_secure_redis_password

# MinIO (for development, you can keep defaults)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_secure_minio_password

# External API Keys (get from providers above)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
NEWSAPI_KEY=your_newsapi_key
CRUNCHBASE_API_KEY=your_crunchbase_key
GITHUB_TOKEN=your_github_token

# Superset (generate secure key)
SUPERSET_SECRET_KEY=$(openssl rand -hex 32)

# Grafana
GRAFANA_PASSWORD=your_grafana_admin_password

# SEC EDGAR (required for SEC filings)
SEC_USER_AGENT=Corporate Intel Platform/1.0 (your-email@example.com)
```

### Step 3: Start Infrastructure Services

```bash
# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Check logs if any service fails
docker-compose logs [service-name]
```

### Step 4: Initialize Databases

```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U intel_user -d corporate_intel

# Create initial database schema (when backend is implemented)
# docker-compose exec api python manage.py migrate

# Create MinIO buckets
docker-compose exec minio mc mb /data/corporate-documents
docker-compose exec minio mc mb /data/analysis-reports
```

### Step 5: Configure Apache Superset

```bash
# Initialize Superset database
docker-compose exec superset superset db upgrade

# Create admin user
docker-compose exec superset superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@example.com \
  --password admin123

# Initialize Superset
docker-compose exec superset superset init
```

## 🔧 Service Configuration

### PostgreSQL with TimescaleDB
- **Port**: 5432
- **Database**: corporate_intel
- **User**: intel_user
- **Features**: Time-series data, hypertables for financial data

### Redis Cache
- **Port**: 6379
- **Usage**: Session storage, rate limiting, caching

### MinIO Object Storage
- **API Port**: 9000
- **Console Port**: 9001
- **Usage**: Document storage, report files, data backups

### Prefect Workflow Engine
- **Port**: 4200
- **Usage**: Data pipeline orchestration, ETL jobs

### Apache Superset
- **Port**: 8088
- **Usage**: Business intelligence dashboards, data visualization

### Ray Distributed Computing
- **Dashboard Port**: 8265
- **Ray Port**: 10001
- **Usage**: Parallel processing, ML model training

### Monitoring Stack
- **Prometheus**: Port 9090 (metrics collection)
- **Grafana**: Port 3000 (dashboards and alerting)
- **Loki**: Port 3100 (log aggregation)

## 🌐 Service URLs

After successful setup, access these services:

| Service | URL | Default Login |
|---------|-----|---------------|
| Grafana Dashboard | http://localhost:3000 | admin / [your_password] |
| Superset BI | http://localhost:8088 | admin / admin123 |
| MinIO Console | http://localhost:9001 | minioadmin / [your_password] |
| Prefect UI | http://localhost:4200 | No auth required |
| Ray Dashboard | http://localhost:8265 | No auth required |
| Prometheus | http://localhost:9090 | No auth required |

## 🧪 Verification & Testing

### Step 1: Health Checks

```bash
# Check all services are healthy
docker-compose ps

# Test database connection
docker-compose exec postgres psql -U intel_user -d corporate_intel -c "\dt"

# Test Redis connection
docker-compose exec redis redis-cli ping

# Test MinIO
curl http://localhost:9000/minio/health/live
```

### Step 2: API Key Validation

Create a test script to verify your API keys:

```python
# test_apis.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_alpha_vantage():
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey={api_key}"
    response = requests.get(url)
    return response.status_code == 200

def test_newsapi():
    api_key = os.getenv('NEWSAPI_KEY')
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
    response = requests.get(url)
    return response.status_code == 200

def test_github():
    token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': f'token {token}'}
    response = requests.get('https://api.github.com/user', headers=headers)
    return response.status_code == 200

# Run tests
print("Alpha Vantage:", "✓" if test_alpha_vantage() else "✗")
print("NewsAPI:", "✓" if test_newsapi() else "✗")
print("GitHub:", "✓" if test_github() else "✗")
```

### Step 3: Service Integration Tests

```bash
# Test MinIO bucket creation
docker-compose exec minio mc ls /data/

# Test PostgreSQL TimescaleDB extension
docker-compose exec postgres psql -U intel_user -d corporate_intel -c "SELECT * FROM pg_extension WHERE extname='timescaledb';"

# Test Superset connectivity
curl -f http://localhost:8088/health

# Test Prefect API
curl -f http://localhost:4200/api/health
```

## 🛠️ Development Setup

### Python Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install
```

### Environment Variables for Development

Add these to your development environment:

```bash
# Development settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Local service connections
DATABASE_URL=postgresql://intel_user:your_password@localhost:5432/corporate_intel
REDIS_URL=redis://:your_password@localhost:6379/0
MINIO_ENDPOINT=localhost:9000
```

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Change all default passwords
- [ ] Use strong, unique passwords for all services
- [ ] Enable SSL/TLS for all web interfaces
- [ ] Configure firewall rules
- [ ] Set up proper backup procedures
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerting

### API Key Security

- Store API keys in environment variables, never in code
- Use different API keys for development and production
- Regularly rotate API keys
- Monitor API usage and set up alerts for unusual activity
- Use API key restrictions where available (IP allowlists, etc.)

## 📊 Data Sources Overview

The platform integrates with multiple data sources:

### Financial Data
- **Alpha Vantage**: Stock prices, financial indicators
- **SEC EDGAR**: Company filings, 10-K/10-Q reports
- **Crunchbase**: Company information, funding data

### News & Media
- **NewsAPI**: News articles, press releases
- **RSS Feeds**: Industry publications, company blogs

### Internal Data
- **Uploaded Documents**: PDF reports, spreadsheets
- **Manual Data Entry**: Custom datasets
- **Database Imports**: External database connections

## 🚨 Troubleshooting

### Common Issues

**Container fails to start:**
```bash
# Check logs
docker-compose logs [service-name]

# Check resource usage
docker stats

# Restart specific service
docker-compose restart [service-name]
```

**Database connection errors:**
```bash
# Verify PostgreSQL is running
docker-compose exec postgres pg_isready

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection manually
docker-compose exec postgres psql -U intel_user -d corporate_intel
```

**API rate limit errors:**
- Check your API usage quotas
- Implement proper rate limiting in application code
- Consider upgrading to paid API tiers

**Memory issues:**
- Increase Docker Desktop memory allocation
- Reduce number of concurrent services
- Monitor memory usage with `docker stats`

### Getting Help

1. Check the logs: `docker-compose logs`
2. Verify environment variables are set correctly
3. Ensure all required ports are available
4. Check Docker Desktop resources allocation
5. Review API key permissions and quotas

## 📈 Next Steps

After successful setup:

1. **Data Pipeline Development**: Create ETL workflows using Prefect
2. **Dashboard Creation**: Build business intelligence dashboards in Superset
3. **Model Development**: Implement ML models using Ray for distributed computing
4. **Monitoring Setup**: Configure alerts and monitoring in Grafana
5. **API Development**: Build REST APIs for data access
6. **Security Hardening**: Implement production security measures

## 📚 Additional Resources

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Apache Superset Documentation](https://superset.apache.org/docs/intro)
- [Prefect Documentation](https://docs.prefect.io/)
- [Ray Documentation](https://docs.ray.io/)
- [MinIO Documentation](https://docs.min.io/)
- [Grafana Documentation](https://grafana.com/docs/)

---

**Note**: This platform is designed for legitimate business intelligence and research purposes. Ensure compliance with all applicable laws and regulations when collecting and analyzing corporate data.