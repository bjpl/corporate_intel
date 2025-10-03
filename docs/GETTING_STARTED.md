# Getting Started with Corporate Intel

This guide will help you set up and run the Corporate Intel application for development and production environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Running the Application](#running-the-application)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

## Quick Start

For the impatient developer:

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd corporate_intel

# Run the automated setup
bash scripts/setup-dev.sh

# Configure your environment
cp .env.example .env
# Edit .env with your configuration

# Start the application
bash scripts/start-app.sh
```

Visit http://localhost:8000/docs for the API documentation.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required

- **Python 3.11+**: The application is built with Python
  - Check version: `python3 --version`
  - Download: https://www.python.org/downloads/

- **PostgreSQL 14+**: Primary database
  - Check version: `psql --version`
  - Download: https://www.postgresql.org/download/

### Recommended

- **Redis 7+**: For caching (optional but recommended)
  - Check version: `redis-cli --version`
  - Download: https://redis.io/download

- **Git**: For version control
  - Check version: `git --version`
  - Download: https://git-scm.com/downloads

### Optional

- **Docker & Docker Compose**: For containerized deployment
- **pgAdmin**: For database management
- **Postman**: For API testing

## Development Setup

### Automated Setup (Recommended)

The easiest way to set up your development environment:

```bash
bash scripts/setup-dev.sh
```

This script will:
- Create a Python virtual environment
- Install all dependencies
- Set up pre-commit hooks
- Create necessary directories
- Initialize the database
- Create a default `.env` file

### Manual Setup

If you prefer manual setup or need more control:

#### 1. Create Virtual Environment

```bash
python3 -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

#### 2. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install application dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

#### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

#### 4. Set Up Database

```bash
# Create database
createdb corporate_intel

# Run migrations
alembic upgrade head
```

#### 5. Create Directories

```bash
mkdir -p logs data tmp
```

## Running the Application

### Using the Start Script (Recommended)

```bash
bash scripts/start-app.sh
```

This script will:
- Check all dependencies
- Verify database connection
- Run migrations
- Start the API server
- Perform health checks

### Manual Start

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Docker

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop containers
docker-compose down
```

### Verify Installation

Run the health check script:

```bash
bash scripts/health-check.sh
```

Expected output:
```
[SUCCESS] API is healthy (HTTP 200)
[SUCCESS] Database is accessible and ready
[SUCCESS] Redis is accessible and responding
Status: HEALTHY
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Application
ENVIRONMENT=development        # development, staging, production
DEBUG=true                    # Enable debug mode
SECRET_KEY=your-secret-key    # Change in production!
API_HOST=0.0.0.0
API_PORT=8000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=corporate_intel
DB_USER=postgres
DB_PASSWORD=your-password

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI API
OPENAI_API_KEY=your-api-key

# Logging
LOG_LEVEL=debug              # debug, info, warning, error

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Database Configuration

The application uses PostgreSQL with SQLAlchemy ORM. Database settings:

- **Connection pooling**: Automatically managed
- **Migrations**: Handled by Alembic
- **Schema**: Automatically created on first run

### Redis Configuration

Redis is used for:
- Session management
- Rate limiting
- API response caching

Redis is optional; the application will run without it but with reduced performance.

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Specific Tests

```bash
# Test a specific file
pytest tests/test_api.py

# Test a specific function
pytest tests/test_api.py::test_create_company

# Run with verbose output
pytest -v
```

### Run Tests in Watch Mode

```bash
pytest-watch
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Error**: `could not connect to server: Connection refused`

**Solutions**:
- Ensure PostgreSQL is running: `pg_isready`
- Check database credentials in `.env`
- Verify database exists: `psql -l | grep corporate_intel`
- Check PostgreSQL logs for errors

```bash
# Start PostgreSQL (Linux)
sudo systemctl start postgresql

# Start PostgreSQL (Mac)
brew services start postgresql

# Start PostgreSQL (Docker)
docker-compose up -d postgres
```

#### 2. Port Already in Use

**Error**: `Address already in use`

**Solutions**:
- Find process using port: `lsof -i :8000`
- Kill the process: `kill -9 <PID>`
- Or use a different port: `API_PORT=8001 bash scripts/start-app.sh`

#### 3. Dependencies Not Installed

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solutions**:
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.11+)

#### 4. Migration Errors

**Error**: `alembic.util.exc.CommandError`

**Solutions**:
- Check database connection
- Reset migrations: `alembic downgrade base && alembic upgrade head`
- Check migration files in `alembic/versions/`

#### 5. Redis Not Available

**Error**: `Redis connection failed`

**Solutions**:
- Redis is optional; application will run without it
- Install Redis: `brew install redis` (Mac) or `apt install redis` (Linux)
- Start Redis: `redis-server`

### Getting Help

1. **Check logs**: `tail -f logs/app.log`
2. **Run health check**: `bash scripts/health-check.sh`
3. **Enable debug mode**: Set `DEBUG=true` in `.env`
4. **Check documentation**: Visit `/docs` endpoint
5. **Review issues**: Check GitHub issues for similar problems

## Production Deployment

### Pre-Deployment Checklist

- [ ] Update `SECRET_KEY` to a secure random value
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure production database credentials
- [ ] Set up proper logging
- [ ] Configure CORS for production domains
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Review security settings

### Deployment Options

#### Option 1: Traditional Server

```bash
# Set environment
export ENVIRONMENT=production

# Run with production settings
bash scripts/start-app.sh
```

Use a process manager like systemd or supervisor to keep the application running.

#### Option 2: Docker

```bash
# Build production image
docker build -t corporate-intel:latest .

# Run container
docker run -d \
  --name corporate-intel \
  -p 8000:8000 \
  --env-file .env.production \
  corporate-intel:latest
```

#### Option 3: Docker Compose

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

### Performance Tuning

- **Workers**: Set `WORKERS=4` (adjust based on CPU cores)
- **Connection Pool**: Configure in `app/core/database.py`
- **Redis**: Enable for caching and session management
- **Logging**: Set `LOG_LEVEL=info` or `warning`
- **CORS**: Restrict to specific origins

### Monitoring

- **Health endpoint**: `GET /health`
- **Metrics endpoint**: `GET /metrics`
- **Logs**: Centralize with ELK stack or CloudWatch
- **APM**: Integrate with DataDog, New Relic, or similar

## Next Steps

- Review [API documentation](http://localhost:8000/docs)
- Read [Architecture Overview](ARCHITECTURE.md)
- Check [Contributing Guidelines](CONTRIBUTING.md)
- Explore [Example Use Cases](EXAMPLES.md)

## Resources

- **API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **GitHub Repository**: <repository-url>
- **Issue Tracker**: <repository-url>/issues

---

**Need help?** Open an issue or contact the development team.
