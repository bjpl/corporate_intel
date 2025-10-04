# Installation Guide - Corporate Intelligence Platform

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for infrastructure)
- Git
- 8GB RAM minimum (16GB recommended)
- 20GB disk space

## Quick Start (Development)

### 1. Clone Repository

```bash
git clone <repository-url>
cd corporate_intel
```

### 2. Python Environment Setup

#### Option A: Using venv (Recommended for Linux/Mac)

```bash
# Install python3-venv if needed (Ubuntu/Debian)
sudo apt install python3.12-venv

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

#### Option B: Using system Python (WSL/Windows)

```bash
# Install dependencies directly
pip install -r requirements.lock
pip install -r requirements-dev.txt
```

### 3. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.lock

# Development dependencies
pip install -r requirements-dev.txt

# Verify installation
python -c "import fastapi; import sqlalchemy; print('Dependencies OK')"
```

### 4. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# NEVER commit .env to version control
```

### 5. Pre-commit Hooks (Development)

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

## Docker Infrastructure Setup

### Development Environment

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f
```

### Production Environment

```bash
# Use production compose file
docker-compose -f docker-compose.yml up -d

# Verify deployment
make verify-production
```

## Database Setup

### Initialize Database

```bash
# Run migrations
alembic upgrade head

# Verify database
python -c "from src.db.base import get_db; next(get_db())"
```

### Seed Data (Development)

```bash
# Load test data
python scripts/seed_data.py
```

## Verification

### Run Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# All tests with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

### Start Development Server

```bash
# Run FastAPI development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# API available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## Troubleshooting

### Virtual Environment Issues (WSL/Ubuntu)

```bash
# Install required packages
sudo apt update
sudo apt install python3.12-venv python3-pip
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL
```

### Import Errors

```bash
# Install package in editable mode
pip install -e .
```

## Dependency Management

### Updating Dependencies

```bash
# Update requirements.lock after changes
pip freeze > requirements.lock

# For Poetry users
poetry lock
poetry export -f requirements.txt --output requirements.lock --without-hashes
```

### Security Updates

```bash
# Check for vulnerabilities
pip-audit

# Update specific package
pip install --upgrade <package-name>
pip freeze > requirements.lock
```

## Next Steps

1. Review [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
2. Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API usage
3. Check [SECURITY.md](SECURITY.md) for security best practices
4. See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines

## Support

- Issues: https://github.com/your-org/corporate-intel/issues
- Documentation: https://docs.corporate-intel.io
- Security: security@corporate-intel.io
