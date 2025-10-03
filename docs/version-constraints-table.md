# Version Constraints - Quick Reference Table

| Category | Package | Lower Bound | Upper Bound | Stability | Risk Level |
|----------|---------|-------------|-------------|-----------|------------|
| **Core Framework** |
| | fastapi | >=0.104.0 | <1.0.0 | Pre-1.0 Stable | Low |
| | uvicorn[standard] | >=0.24.0 | <1.0.0 | Pre-1.0 Stable | Low |
| | pydantic | >=2.5.0 | <3.0.0 | Major v2 | Low |
| | pydantic-settings | >=2.1.0 | <3.0.0 | Aligned w/ pydantic | Low |
| **Database** |
| | sqlalchemy | >=2.0.0 | <3.0.0 | Major v2 | Low |
| | asyncpg | >=0.29.0 | <1.0.0 | Pre-1.0 Mature | Medium |
| | psycopg2-binary | >=2.9.0 | <3.0.0 | Stable v2 | Low |
| | alembic | >=1.12.0 | <2.0.0 | Stable v1 | Low |
| | pgvector | >=0.2.4 | <1.0.0 | Pre-1.0 Evolving | Medium |
| **Data Processing** |
| | pandas | >=2.1.0 | <3.0.0 | Major v2 | Low |
| | numpy | >=1.24.0 | <2.0.0 | Pre-v2 | Low |
| | pandera | >=0.17.0 | <1.0.0 | Pre-1.0 | Medium |
| | great-expectations | >=0.18.0 | <1.0.0 | Pre-1.0 Active | High |
| | dbt-core | >=1.7.0 | <2.0.0 | Stable v1 | Low |
| | dbt-postgres | >=1.7.0 | <2.0.0 | Aligned w/ core | Low |
| **Orchestration** |
| | prefect | >=2.14.0 | <3.0.0 | Major v2 | Low |
| | prefect-dask | >=0.2.5 | <1.0.0 | Pre-1.0 | Medium |
| | ray[default] | >=2.8.0 | <3.0.0 | Major v2 | Low |
| **Caching & Storage** |
| | redis | >=5.0.0 | <6.0.0 | Stable v5 | Low |
| | aiocache[redis] | >=0.12.0 | <1.0.0 | Pre-1.0 | Medium |
| | minio | >=7.2.0 | <8.0.0 | Stable v7 | Low |
| **Observability** |
| | opentelemetry-api | >=1.21.0 | <2.0.0 | Stable v1 | Low |
| | opentelemetry-sdk | >=1.21.0 | <2.0.0 | Stable v1 | Low |
| | opentelemetry-instrumentation-fastapi | >=0.42b0 | <1.0.0 | Beta | High |
| | prometheus-client | >=0.19.0 | <1.0.0 | Pre-1.0 Mature | Medium |
| | loguru | >=0.7.0 | <1.0.0 | Pre-1.0 Stable | Medium |
| | sentry-sdk[fastapi] | >=1.39.0 | <2.0.0 | Stable v1 | Low |
| **Document Processing** |
| | pypdf | >=3.17.0 | <4.0.0 | Major v3 | Low |
| | pdfplumber | >=0.10.0 | <1.0.0 | Pre-1.0 | Medium |
| | python-docx | >=1.1.0 | <2.0.0 | Stable v1 | Low |
| | beautifulsoup4 | >=4.12.0 | <5.0.0 | Stable v4 | Low |
| **Financial Data** |
| | yfinance | >=0.2.33 | <1.0.0 | Pre-1.0 | High |
| | alpha-vantage | >=2.3.1 | <3.0.0 | Major v2 | Medium |
| | sec-edgar-api | >=1.0.0 | <2.0.0 | Stable v1 | Low |
| **Visualization** |
| | plotly | >=5.18.0 | <6.0.0 | Stable v5 | Low |
| | dash | >=2.14.0 | <3.0.0 | Major v2 | Low |
| **Testing** |
| | pytest | >=7.4.0 | <8.0.0 | Stable v7 | Low |
| | pytest-asyncio | >=0.21.0 | <1.0.0 | Pre-1.0 | Medium |
| | pytest-cov | >=4.1.0 | <5.0.0 | Stable v4 | Low |
| | httpx | >=0.25.0 | <1.0.0 | Pre-1.0 Mature | Medium |
| **Development Tools** |
| | black | >=23.12.0 | <25.0.0 | Year-based | Low |
| | ruff | >=0.1.0 | <1.0.0 | Pre-1.0 Active | Medium |
| | mypy | >=1.7.0 | <2.0.0 | Stable v1 | Low |
| | pre-commit | >=3.5.0 | <4.0.0 | Stable v3 | Low |
| | ipython | >=8.18.0 | <9.0.0 | Stable v8 | Low |
| | isort | >=5.12.0 | <6.0.0 | Stable v5 | Low |
| | flake8 | >=6.1.0 | <7.0.0 | Stable v6 | Low |
| | bandit | >=1.7.5 | <2.0.0 | Stable v1 | Low |
| | safety | >=2.3.5 | <3.0.0 | Major v2 | Low |
| **Documentation** |
| | sphinx | >=7.0.0 | <8.0.0 | Stable v7 | Low |
| | sphinx-rtd-theme | >=1.3.0 | <2.0.0 | Stable v1 | Low |
| | myst-parser | >=2.0.0 | <3.0.0 | Major v2 | Low |
| **Type Stubs** |
| | types-redis | >=4.6.0 | <5.0.0 | Aligned v4 | Low |
| | types-requests | >=2.31.0 | <3.0.0 | Aligned v2 | Low |
| | pandas-stubs | >=2.1.0 | <3.0.0 | Aligned v2 | Low |

## Risk Level Legend

- **Low**: Stable API, well-maintained, production-ready
- **Medium**: Pre-1.0 but mature, or active development
- **High**: External API dependency, beta status, or frequent breaking changes

## Monitoring Priority

### Immediate Monitoring (High Risk)
1. yfinance - External API changes
2. great-expectations - Pre-1.0 with evolving API
3. opentelemetry-instrumentation-fastapi - Beta package

### Regular Monitoring (Medium Risk)
- asyncpg, pgvector, pandera, prefect-dask, aiocache
- prometheus-client, loguru, pdfplumber, alpha-vantage
- pytest-asyncio, httpx, ruff

### Stable (Low Risk)
- Core framework (fastapi, pydantic, sqlalchemy)
- Data processing (pandas, numpy, dbt)
- Orchestration (prefect, ray)
- Most development tools

## Update Strategy

| Frequency | Action | Scope |
|-----------|--------|-------|
| Daily | Security alerts | All packages |
| Weekly | Patch updates | High-risk packages |
| Monthly | Minor updates | Medium-risk packages |
| Quarterly | Review all | Complete dependency audit |
| As-needed | Major versions | Planned migration with testing |

## File Status

- ✅ requirements.txt - **COMPLETE** with all constraints
- ⏳ requirements-dev.txt - Needs constraint update
- ⏳ pyproject.toml - Needs constraint update

## Total Dependencies

- Core dependencies: 42 packages
- Development dependencies: 16 packages
- Type stubs: 3 packages
- **Total**: 61 packages with version constraints
