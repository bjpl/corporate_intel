# Version Constraints Summary

## Quick Reference Guide

### Constraint Format
- **Stable (>=1.0)**: `package>=X.Y.Z,<(X+1).0.0`
- **Pre-1.0 (0.x)**: `package>=0.X.Y,<0.(X+1).0` or `<1.0.0`
- **Beta/Special**: Case-by-case analysis

### Complete Constraints List

#### Core Framework
```
fastapi>=0.104.0,<1.0.0
uvicorn[standard]>=0.24.0,<1.0.0
pydantic>=2.5.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0
```

#### Database
```
sqlalchemy>=2.0.0,<3.0.0
asyncpg>=0.29.0,<1.0.0
psycopg2-binary>=2.9.0,<3.0.0
alembic>=1.12.0,<2.0.0
pgvector>=0.2.4,<1.0.0
```

#### Data Processing
```
pandas>=2.1.0,<3.0.0
numpy>=1.24.0,<2.0.0
pandera>=0.17.0,<1.0.0
great-expectations>=0.18.0,<1.0.0
dbt-core>=1.7.0,<2.0.0
dbt-postgres>=1.7.0,<2.0.0
```

#### Orchestration
```
prefect>=2.14.0,<3.0.0
prefect-dask>=0.2.5,<1.0.0
ray[default]>=2.8.0,<3.0.0
```

#### Caching & Storage
```
redis>=5.0.0,<6.0.0
aiocache[redis]>=0.12.0,<1.0.0
minio>=7.2.0,<8.0.0
```

#### Observability
```
opentelemetry-api>=1.21.0,<2.0.0
opentelemetry-sdk>=1.21.0,<2.0.0
opentelemetry-instrumentation-fastapi>=0.42b0,<1.0.0
prometheus-client>=0.19.0,<1.0.0
loguru>=0.7.0,<1.0.0
sentry-sdk[fastapi]>=1.39.0,<2.0.0
```

#### Document Processing
```
pypdf>=3.17.0,<4.0.0
pdfplumber>=0.10.0,<1.0.0
python-docx>=1.1.0,<2.0.0
beautifulsoup4>=4.12.0,<5.0.0
```

#### Financial Data
```
yfinance>=0.2.33,<1.0.0
alpha-vantage>=2.3.1,<3.0.0
sec-edgar-api>=1.0.0,<2.0.0
```

#### Visualization
```
plotly>=5.18.0,<6.0.0
dash>=2.14.0,<3.0.0
```

#### Testing
```
pytest>=7.4.0,<8.0.0
pytest-asyncio>=0.21.0,<1.0.0
pytest-cov>=4.1.0,<5.0.0
httpx>=0.25.0,<1.0.0
```

#### Development Tools
```
black>=23.12.0,<25.0.0
ruff>=0.1.0,<1.0.0
mypy>=1.7.0,<2.0.0
pre-commit>=3.5.0,<4.0.0
ipython>=8.18.0,<9.0.0
isort>=5.12.0,<6.0.0
flake8>=6.1.0,<7.0.0
bandit>=1.7.5,<2.0.0
safety>=2.3.5,<3.0.0
```

#### Documentation
```
sphinx>=7.0.0,<8.0.0
sphinx-rtd-theme>=1.3.0,<2.0.0
myst-parser>=2.0.0,<3.0.0
```

#### Type Stubs
```
types-redis>=4.6.0,<5.0.0
types-requests>=2.31.0,<3.0.0
pandas-stubs>=2.1.0,<3.0.0
```

## Special Cases & Notes

### yfinance (>=0.2.33,<1.0.0)
- **Note**: Changed from `<0.3.0` to `<1.0.0` after review
- Pre-1.0 but relatively stable API
- Yahoo Finance API wrapper with frequent updates
- Monitor for API changes

### High Priority Monitoring
1. **yfinance**: External API dependency
2. **great-expectations**: Pre-1.0, evolving API
3. **opentelemetry-instrumentation-fastapi**: Beta package
4. **pgvector**: New technology, API evolving

### Upgrade Priority Order
1. Security patches (immediate)
2. Bug fixes (within sprint)
3. Feature updates (quarterly review)
4. Major versions (planned migration)

## Implementation Status

✅ All dependencies researched
✅ Version constraints determined
✅ Rationale documented
✅ Risk assessment completed
✅ requirements.txt updated (complete)
⏳ requirements-dev.txt needs update
⏳ pyproject.toml needs update

## Next Steps

1. Apply constraints to requirements-dev.txt
2. Update pyproject.toml dependencies section
3. Generate requirements.lock file
4. Configure Dependabot
5. Set up CI/CD version boundary tests
