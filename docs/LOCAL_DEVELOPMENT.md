# Local Development Setup Guide

## Prerequisites

- **Docker Desktop**: 4.25.0+ (with Docker Compose V2)
- **Python**: 3.10 or 3.11
- **Git**: 2.40+
- **VS Code** (recommended) or PyCharm
- **Minimum Hardware**: 8GB RAM, 20GB free disk space

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/corporate-intel.git
cd corporate-intel
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your local settings
# Use default values for local development
```

### 3. Python Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, MinIO
docker-compose up -d postgres redis minio

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Verify all services show "healthy" status
```

### 5. Initialize Database

```bash
# Run database migrations
alembic upgrade head

# (Optional) Seed with sample data
python scripts/seed_data.py
```

### 6. Start Development Server

```bash
# Run with auto-reload enabled
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use the development script
python -m src.api.main
```

### 7. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (admin/minio_password)
- **PostgreSQL**: localhost:5432 (intel_user/intel_password)
- **Redis**: localhost:6379

## Development Workflow

### Code Quality Tools

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/ --fix

# Type checking with mypy
mypy src/

# Run all checks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_companies.py

# Run with verbosity
pytest -v -s

# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### Database Operations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Check current version
alembic current
```

### Docker Operations

```bash
# View logs
docker-compose logs -f api

# Restart specific service
docker-compose restart postgres

# Rebuild containers
docker-compose up -d --build

# Stop all services
docker-compose down

# Remove volumes (CAUTION: deletes all data)
docker-compose down -v

# Clean up Docker system
docker system prune -a
```

## Project Structure

```
corporate-intel/
├── src/                    # Application source code
│   ├── api/               # FastAPI application
│   │   ├── main.py       # Application entry point
│   │   └── v1/           # API version 1 endpoints
│   ├── core/             # Core functionality
│   ├── db/               # Database models and utilities
│   └── services/         # Business logic services
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Pytest fixtures
├── alembic/              # Database migrations
├── dbt/                  # Data transformation (DBT)
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── config/               # Configuration files
├── .github/              # GitHub Actions workflows
├── docker-compose.yml    # Local development services
├── Dockerfile            # Production container image
├── pyproject.toml        # Python project configuration
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (gitignored)
```

## Environment Variables

### Required Variables

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_PASSWORD=intel_password
POSTGRES_DB=corporate_intel

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_password
MINIO_USE_SSL=false

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-change-in-production
```

### Optional Variables

```bash
# External APIs
ALPHA_VANTAGE_API_KEY=your_api_key
NEWSAPI_KEY=your_api_key
SEC_USER_AGENT=Corporate Intel Dev/1.0 (your-email@example.com)

# Observability
SENTRY_DSN=your_sentry_dsn
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## IDE Setup

### VS Code

Install recommended extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- Docker (Microsoft)
- GitLens
- Better Comments
- autoDocstring

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.rulers": [100]
  }
}
```

### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter: venv/bin/python
3. Enable Django support (if needed)
4. Configure code style: Black (100 line length)
5. Enable type checking with mypy

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Test connection
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000
# Or on Windows:
netstat -ano | findstr :8000

# Kill the process
kill -9 <PID>
```

### Docker Issues

```bash
# Reset Docker environment
docker-compose down -v
docker system prune -a
docker-compose up -d

# Check Docker disk usage
docker system df
```

### Import Errors

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Migration Errors

```bash
# Reset database (CAUTION: deletes all data)
docker-compose down -v postgres
docker-compose up -d postgres
alembic upgrade head
```

## Common Tasks

### Adding a New Endpoint

1. Create endpoint in `src/api/v1/`
2. Add database models in `src/db/models.py`
3. Create Pydantic schemas in `src/api/schemas/`
4. Write tests in `tests/`
5. Update API documentation

### Adding Dependencies

```bash
# Add to pyproject.toml dependencies
# Then regenerate requirements.txt
pip install <package>
pip freeze > requirements.txt
```

### Running Background Tasks

```bash
# Start Prefect agent (for workflow orchestration)
prefect agent start -q default

# Run specific flow
python -m src.workflows.example_flow
```

## Performance Tips

1. **Use connection pooling** - Already configured in SQLAlchemy
2. **Enable Redis caching** - Cache frequently accessed data
3. **Use async/await** - FastAPI supports async operations
4. **Index database queries** - Add indexes for frequently queried columns
5. **Monitor query performance** - Use `EXPLAIN ANALYZE` in PostgreSQL

## Best Practices

1. **Always write tests** for new features
2. **Use type hints** for better IDE support and type checking
3. **Follow PEP 8** and project style guidelines
4. **Write docstrings** for all functions and classes
5. **Keep functions small** (< 50 lines)
6. **Use dependency injection** via FastAPI dependencies
7. **Commit often** with clear, descriptive messages
8. **Never commit secrets** to version control

## Getting Help

- **Documentation**: See `docs/` directory
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Slack**: #corporate-intel-dev (if applicable)

## Next Steps

After completing local setup:

1. Review the [API Documentation](API_DOCUMENTATION.md)
2. Read [Contributing Guidelines](CONTRIBUTING.md)
3. Check [Architecture Overview](ARCHITECTURE.md)
4. Join the development Slack channel
5. Pick up a "good first issue" from GitHub
