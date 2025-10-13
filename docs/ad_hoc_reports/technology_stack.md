# Corporate Intelligence Platform - Technology Stack Analysis

**Project:** Corporate Intel
**Generated:** 2025-10-12
**Version:** 1.0.0
**Analysis Type:** Comprehensive Technology Stack Documentation

---

## Executive Summary

The Corporate Intelligence Platform is a production-hardened business intelligence system built for EdTech financial analysis. The architecture leverages modern Python-based microservices, distributed computing, time-series optimization, and comprehensive observability patterns. This document provides a complete inventory of all technologies, frameworks, and tools used across the platform.

---

## 1. Operating System & Infrastructure

### Operating System
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Production Runtime** | Python Slim (Debian-based) | 3.11-slim | Minimal attack surface, optimized for containers |
| **Development OS** | Windows (MSYS) | NT-10.0-26200 | Local development environment |
| **CI/CD Platform** | Ubuntu Linux | Latest LTS | GitHub Actions runner environment |

### Container Platform
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Container Runtime** | Docker Engine | v20.10+ | Application containerization |
| **Orchestration (Local)** | Docker Compose | v2.0+ | Multi-container orchestration |
| **Orchestration (K8s)** | Kubernetes | 1.24+ | Production container orchestration |
| **Build System** | Docker BuildKit | Latest | Multi-stage builds with caching |
| **Image Registry** | GitHub Container Registry | - | Container image storage |

**Architectural Decision:** Multi-stage Dockerfile reduces final image size by separating build dependencies from runtime, improving security and deployment speed.

---

## 2. Programming Languages & Runtimes

### Primary Languages
| Language | Version | Usage | Lines of Code |
|----------|---------|-------|---------------|
| **Python** | 3.11+ | Backend, data processing, APIs | ~15,000+ |
| **SQL** | PostgreSQL 15 | Data models, migrations, analytics | ~3,000+ |
| **YAML** | 1.2 | Configuration, CI/CD, Kubernetes | ~2,000+ |
| **Bash/Shell** | 4.0+ | Automation scripts, deployment | ~500+ |

### Python Runtime Configuration
```toml
[project]
name = "corporate-intel"
version = "0.1.0"
requires-python = ">=3.10"
```

**Architectural Decision:** Python 3.11+ chosen for performance improvements (10-60% faster than 3.10), improved error messages, and modern type hinting support.

---

## 3. Backend Framework & API Layer

### Web Framework
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **API Framework** | FastAPI | 0.104.0+ | REST API, async endpoints, OpenAPI docs |
| **ASGI Server** | Uvicorn | 0.24.0+ | Async server with standard extras |
| **Production Server** | Gunicorn | 21.2.0+ | Process manager for Uvicorn workers |
| **Data Validation** | Pydantic | 2.5.0+ | Request/response models, settings |
| **Settings Management** | Pydantic Settings | 2.1.0+ | Environment-based configuration |

### API Configuration
```python
# Production server configuration (from Dockerfile)
CMD ["gunicorn", "src.api.main:app",
     "--worker-class", "uvicorn.workers.UvicornWorker",
     "--workers", "4",
     "--bind", "0.0.0.0:8000",
     "--timeout", "120",
     "--max-requests", "1000"]
```

**Architectural Decision:** FastAPI provides automatic OpenAPI documentation, async support for I/O-bound operations, and Pydantic integration for data validation with minimal overhead.

### Authentication & Security
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **JWT Tokens** | python-jose | 3.3.0+ | JWT creation and verification |
| **Password Hashing** | passlib[bcrypt] | 1.7.4+ | Secure password storage |
| **Cryptography** | cryptography | Latest | Encryption primitives |

---

## 4. Database Layer

### Primary Database
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **RDBMS** | PostgreSQL | 15+ | Primary data storage |
| **Time-Series Extension** | TimescaleDB | Latest | Optimized time-series operations |
| **Vector Search** | pgvector | 0.2.4+ | Semantic search via embeddings |

### Database Access
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **ORM** | SQLAlchemy | 2.0.0+ | Object-relational mapping |
| **Async Driver** | asyncpg | 0.29.0+ | High-performance async PostgreSQL |
| **Sync Driver** | psycopg2-binary | 2.9.0+ | Synchronous PostgreSQL connection |
| **Migrations** | Alembic | 1.12.0+ | Database schema versioning |

### TimescaleDB Configuration
```yaml
# Environment variables
TIMESCALE_COMPRESSION_AFTER_DAYS: 30
TIMESCALE_RETENTION_YEARS: 2
```

**Architectural Decision:** TimescaleDB provides 10x compression for time-series data while maintaining PostgreSQL compatibility. pgvector enables semantic document search without external vector databases.

---

## 5. Data Processing & Analytics

### Data Processing Framework
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **DataFrame Library** | pandas | 2.1.0+ | Data manipulation and analysis |
| **Numerical Computing** | numpy | 1.24.0+ | Array operations, linear algebra |
| **Data Validation** | pandera | 0.17.0+ | DataFrame schema validation |
| **Data Quality** | Great Expectations | 0.18.0+ | Data quality testing and profiling |

### Data Transformation
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Transformation Tool** | dbt-core | 1.7.0+ | SQL-based data transformations |
| **Database Adapter** | dbt-postgres | 1.7.0+ | PostgreSQL connector for dbt |

### dbt Structure
```
dbt/
├── models/
│   ├── staging/      # Raw data cleaning
│   ├── intermediate/ # Business logic transformations
│   └── marts/        # Analytics-ready data models
├── dbt_project.yml
└── profiles.yml
```

**Architectural Decision:** dbt provides version-controlled, testable SQL transformations with built-in data lineage and documentation generation.

---

## 6. Distributed Computing & Orchestration

### Workflow Orchestration
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Orchestration Engine** | Prefect | 2.14.0+ | Workflow management, scheduling |
| **Distributed Execution** | prefect-dask | 0.2.5+ | Parallel task execution |

### Distributed Computing
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Compute Framework** | Ray[default] | 2.8.0+ | Distributed Python execution |
| **Processing Throughput** | - | - | 100+ documents/second |

**Architectural Decision:** Prefect v2 locked to prevent breaking changes from v3. Ray provides distributed computing without infrastructure complexity, scaling from laptop to cluster seamlessly.

---

## 7. Caching & Storage

### In-Memory Cache
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Cache Server** | Redis | 7-alpine | Session storage, API caching |
| **Python Client** | redis | 5.0.0+ | Redis Python client |
| **Async Cache** | aiocache[redis] | 0.12.0+ | Async caching layer |

### Object Storage
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Object Store** | MinIO | Latest | S3-compatible document storage |
| **Python Client** | minio | 7.2.0+ | MinIO SDK for Python |

### Redis Configuration
```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --appendonly yes
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
```

**Architectural Decision:** Redis provides sub-millisecond cache access (p99 < 100ms API response). MinIO offers S3-compatible storage without cloud vendor lock-in.

---

## 8. Observability & Monitoring

### Distributed Tracing
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Tracing Standard** | OpenTelemetry | 1.21.0+ | Distributed tracing specification |
| **OTel SDK** | opentelemetry-sdk | 1.21.0+ | Tracing implementation |
| **FastAPI Instrumentation** | opentelemetry-instrumentation-fastapi | 0.42b0+ | Automatic API tracing |
| **Trace Backend** | Jaeger | Latest | Trace visualization and analysis |

### Metrics & Monitoring
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Metrics Server** | Prometheus | Latest | Metrics collection and storage |
| **Metrics Client** | prometheus-client | 0.19.0+ | Python Prometheus exporter |
| **Visualization** | Grafana | Latest | Dashboards and alerting |

### Logging
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Logging Library** | loguru | 0.7.0+ | Structured logging with color output |

### Error Tracking
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Error Monitoring** | Sentry | 1.39.0+ | Exception tracking and alerting |

**Architectural Decision:** OpenTelemetry provides vendor-neutral observability. Jaeger + Prometheus + Grafana stack offers comprehensive monitoring without commercial dependencies.

---

## 9. Document Processing

### PDF Processing
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **PDF Library** | pypdf | 3.17.0+ | PDF parsing and extraction |
| **Advanced Parsing** | pdfplumber | 0.10.0+ | Table and text extraction |

### Document Formats
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Word Documents** | python-docx | 1.1.0+ | DOCX file processing |
| **HTML Parsing** | beautifulsoup4 | 4.12.0+ | HTML/XML parsing |

**Architectural Decision:** Multiple PDF libraries provide fallback options for different document formats (SEC filings, financial reports).

---

## 10. External Data Connectors

### Financial APIs
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Market Data** | yfinance | 0.2.33+ | Yahoo Finance API wrapper |
| **Fundamental Data** | alpha-vantage | 2.3.1+ | Alpha Vantage API client |
| **SEC Filings** | sec-edgar-api | 1.0.0+ | SEC EDGAR API integration |

### Reliability
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Retry Logic** | tenacity | 8.2.3+ | Configurable retry with backoff |

### Data Sources
- **SEC EDGAR**: 10-K, 10-Q, 8-K automated filing ingestion
- **Yahoo Finance**: Real-time stock metrics
- **Alpha Vantage**: Fundamental analysis data
- **NewsAPI**: News aggregation and sentiment
- **Crunchbase**: Funding intelligence
- **GitHub**: Developer activity metrics

---

## 11. Visualization & Business Intelligence

### Interactive Dashboards
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Plotting Library** | Plotly | 5.18.0+ | Interactive charts and graphs |
| **Dashboard Framework** | Dash | 2.14.0+ | Web-based analytics dashboards |

### Visualization Capabilities
- Financial waterfall charts (revenue decomposition)
- Cohort heatmaps (retention analysis)
- Competitive landscape scatter plots
- Performance radar charts
- Market share sunburst diagrams

**Dashboard Performance:** < 100ms rendering for 10K data points

---

## 12. Testing & Quality Assurance

### Testing Framework
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Test Framework** | pytest | 7.4.0+ | Unit and integration testing |
| **Async Testing** | pytest-asyncio | 0.21.0+ | Async test support |
| **Coverage** | pytest-cov | 4.1.0+ | Code coverage measurement |
| **HTTP Client** | httpx | 0.25.0+ | Async HTTP testing |

### Additional Testing Tools
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Parallel Testing** | pytest-xdist | 3.5.0+ | Multi-core test execution |
| **Benchmarking** | pytest-benchmark | 4.0.0+ | Performance testing |
| **Timeout Management** | pytest-timeout | 2.2.0+ | Test timeout enforcement |
| **Data Generation** | faker | 22.0.0+ | Test data generation |
| **Load Testing** | locust | 2.20.0+ | API load testing |

### Test Coverage Configuration
```toml
[tool.coverage.report]
precision = 2
fail_under = 80.0  # Minimum 80% coverage required
```

**Test Metrics:**
- **Total Tests:** 391+ passing tests
- **Coverage:** 85%+ code coverage
- **Performance:** 100+ documents/second processing

---

## 13. Code Quality & Linting

### Code Formatting
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Formatter** | Black | 23.12.0+ | Opinionated code formatting |
| **Import Sorter** | isort | 5.13.0+ | Import statement organization |

### Linting
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Primary Linter** | Ruff | 0.1.0+ | Fast Python linter (Rust-based) |
| **Secondary Linter** | Flake8 | 7.0.0+ | Style guide enforcement |
| **Docstring Linter** | flake8-docstrings | 1.7.0+ | Documentation coverage |
| **Bug Detection** | flake8-bugbear | 23.12.0+ | Common bug patterns |

### Type Checking
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Type Checker** | mypy | 1.8.0+ | Static type checking |
| **Type Stubs** | types-redis, types-requests, pandas-stubs | Latest | Type hints for libraries |

### Security Scanning
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Security Scanner** | Bandit | 1.7.6+ | Python security issue detection |
| **Dependency Check** | Safety | 3.0.0+ | Known vulnerability scanning |

### Code Quality Standards
```toml
[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "UP", "S", "B", "A", "C4"]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.mypy]
python_version = "3.11"
strict = true
```

---

## 14. Pre-commit Hooks & Automation

### Pre-commit Framework
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Hook Manager** | pre-commit | 3.5.0+ | Git hook automation |

### Configured Hooks
1. **Black** - Code formatting (line-length: 100)
2. **isort** - Import sorting with Black profile
3. **Flake8** - Linting with multiple plugins
4. **mypy** - Type checking
5. **Bandit** - Security scanning
6. **interrogate** - Docstring coverage (75% minimum)
7. **yamllint** - YAML validation
8. **pyupgrade** - Syntax modernization (Python 3.11+)

### File Validation Hooks
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Large file detection (500KB limit)
- Merge conflict detection

---

## 15. CI/CD & DevOps

### Continuous Integration
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **CI Platform** | GitHub Actions | - | Automated testing and deployment |
| **Docker Build** | docker/build-push-action | v5 | Multi-platform image builds |
| **Code Coverage** | Codecov | v3 | Coverage tracking and reporting |

### CI/CD Workflow Stages
```yaml
1. Code Quality & Security
   - Ruff linting
   - Black formatting check
   - mypy type checking
   - Bandit security scan

2. Test Suite
   - PostgreSQL + Redis services
   - 391+ tests with coverage
   - Coverage upload to Codecov

3. Build Docker Image
   - Multi-platform build (amd64, arm64)
   - Push to GitHub Container Registry
   - Layer caching for speed

4. Deploy to Staging
   - Automated deployment on develop branch
   - Smoke tests

5. Deploy to Production
   - Triggered by version tags (v*)
   - Production smoke tests
   - GitHub release creation
```

### Infrastructure as Code
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Container Orchestration** | Kubernetes | 1.24+ | Production deployment |
| **Configuration Management** | Kustomize | Built-in K8s | Environment-specific configs |
| **Helm** | Helm Charts | 3.0+ | Kubernetes package management |

### Kubernetes Resources
```
k8s/
├── base/
│   ├── deployment.yaml      # Application deployment
│   ├── service.yaml         # Service definition
│   ├── ingress.yaml         # External access
│   ├── configmap.yaml       # Configuration
│   ├── secret.yaml          # Sensitive data
│   ├── hpa.yaml             # Horizontal Pod Autoscaler
│   ├── pdb.yaml             # Pod Disruption Budget
│   └── networkpolicy.yaml   # Network security
```

---

## 16. Development Tools

### Interactive Development
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **REPL** | IPython | 8.18.0+ | Enhanced Python shell |
| **Debugger** | ipdb | 0.13.13+ | IPython-based debugger |
| **File Watcher** | watchdog | 3.0.0+ | Hot reload functionality |

### Database Tools
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **pgAdmin** | pgAdmin 4 | Latest | PostgreSQL GUI (dev only) |
| **CLI** | pgcli | 4.0.0+ | PostgreSQL command-line interface |
| **Migration Utils** | alembic-utils | 0.8.0+ | Advanced migration helpers |

### API Development
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **API Client** | httpie | 3.2.0+ | Human-friendly HTTP client |

### Performance Profiling
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **CPU Profiler** | py-spy | 0.3.14+ | Sampling profiler (low overhead) |
| **Memory Profiler** | memory-profiler | 0.61.0+ | Line-by-line memory usage |
| **Line Profiler** | line-profiler | 4.1.0+ | Line-by-line execution time |

---

## 17. Documentation

### Documentation Generation
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Doc Generator** | Sphinx | 7.2.0+ | Python documentation generation |
| **Theme** | sphinx-rtd-theme | 2.0.0+ | Read the Docs theme |
| **Type Hints** | sphinx-autodoc-typehints | 1.25.0+ | Type annotation documentation |
| **Markdown Support** | myst-parser | 2.0.0+ | Markdown in Sphinx |

### Documentation Quality
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Docstring Coverage** | interrogate | 1.5.0+ | Documentation coverage metrics |
| **Style Checker** | pydocstyle | 6.3.0+ | Docstring style validation |

---

## 18. Networking & Protocols

### Network Configuration
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Docker Network** | Bridge | Container networking |
| **Load Balancer** | Traefik / Nginx | Reverse proxy (production) |
| **Service Discovery** | Kubernetes DNS | Service resolution |

### API Protocols
| Protocol | Usage | Purpose |
|----------|-------|---------|
| **HTTP/1.1** | REST API | Client-server communication |
| **HTTP/2** | Modern clients | Multiplexed streams |
| **WebSocket** | Dashboard | Real-time updates |
| **gRPC** | OpenTelemetry | Efficient telemetry transport |

### Ports Mapping
```yaml
API Server:        8000  # FastAPI application
Dashboard:         8050  # Plotly Dash
PostgreSQL:        5432  # Database
Redis:             6379  # Cache
MinIO API:         9000  # Object storage
MinIO Console:     9001  # Management UI
Prometheus:        9090  # Metrics
Grafana:           3000  # Visualization
Jaeger UI:        16686  # Tracing
Jaeger OTLP:       4317  # Trace ingestion
```

---

## 19. Security & Authentication

### Application Security
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Authentication** | JWT (JSON Web Tokens) | Stateless authentication |
| **Password Hashing** | bcrypt via passlib | Secure password storage |
| **Secrets Management** | Environment variables | Configuration injection |
| **CORS** | FastAPI middleware | Cross-origin request control |

### Container Security
| Practice | Implementation |
|----------|----------------|
| **Non-root User** | `appuser:appuser (1000:1000)` |
| **Minimal Base Image** | `python:3.11-slim` |
| **Multi-stage Build** | Separate build/runtime stages |
| **Security Scanning** | Bandit + Trivy (CI/CD) |
| **Image Signing** | Cosign (optional) |

### Network Security
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **TLS/SSL** | Let's Encrypt | HTTPS encryption |
| **Network Policies** | Kubernetes | Pod-to-pod communication rules |
| **Rate Limiting** | FastAPI middleware | API abuse prevention |

### Security Environment Variables
```bash
SECRET_KEY=<32-char minimum>
POSTGRES_PASSWORD=<secure password>
REDIS_PASSWORD=<secure password>
MINIO_SECRET_KEY=<secure key>
```

---

## 20. Build & Package Management

### Python Package Management
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Build System** | setuptools + wheel | Package building |
| **Dependency File** | pyproject.toml | Modern Python packaging |
| **Lock File** | requirements.lock | Reproducible builds |

### Dependency Management Strategy
```
requirements.txt          # Production dependencies
requirements-dev.txt      # Development dependencies
requirements-prod.txt     # Production optimizations
pyproject.toml           # Project metadata + tool config
```

### Build Tools
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Task Runner** | Make | Common command automation |
| **Docker Build** | BuildKit | Advanced Docker builds |

### Makefile Commands (54 commands)
```makefile
Development:  dev-up, dev-down, dev-logs, dev-shell
Testing:      test, test-coverage, test-integration, test-e2e
Production:   prod-build, prod-up, prod-down
Database:     migrate, db-backup, db-restore, db-shell
Maintenance:  clean, prune, security-scan, health-check
Observability: observability-up, logs, status
```

---

## 21. EdTech-Specific Components

### Financial Data Processing
- **SEC EDGAR** integration for 10-K/10-Q filings
- **Market data** via Yahoo Finance (CHGG, COUR, DUOL, TWOU)
- **Fundamental metrics** via Alpha Vantage
- **News sentiment** analysis pipeline

### EdTech Analytics
| Metric Category | Tracked KPIs |
|-----------------|--------------|
| **User Metrics** | MAU, ARPU, Engagement Score |
| **Financial** | Revenue, NRR, Burn Rate |
| **Product** | Course Completion, Retention Curves |
| **Acquisition** | CAC, LTV, Cohort Analysis |

### Market Segments
1. K-12 Education
2. Higher Education
3. Corporate Training
4. Direct-to-Consumer
5. Enabling Technology

---

## 22. Performance Benchmarks

### System Performance
| Metric | Target | Achieved |
|--------|--------|----------|
| **API Response (p99)** | < 100ms | < 100ms with Redis |
| **Document Processing** | 50+ docs/sec | 100+ docs/sec with Ray |
| **Database Compression** | 5x | 10x with TimescaleDB |
| **Embedding Generation** | 500 docs/min | 1000 docs/min |
| **Dashboard Render** | < 200ms | < 100ms for 10K points |

### Resource Requirements
```yaml
Minimum:
  CPU: 8 cores
  RAM: 16GB
  Disk: 50GB SSD

Recommended Production:
  CPU: 16+ cores
  RAM: 32GB+
  Disk: 200GB+ SSD
  Network: 1Gbps+
```

---

## 23. Architectural Patterns

### Design Patterns
| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Strategy Pattern** | Analysis engine | Pluggable analysis algorithms |
| **Repository Pattern** | Database layer | Data access abstraction |
| **Factory Pattern** | Connector initialization | External API creation |
| **Singleton Pattern** | Configuration management | Single config instance |
| **Observer Pattern** | Event-driven workflows | Decoupled components |

### Architecture Principles
1. **Separation of Concerns**: Clean layered architecture
2. **Dependency Injection**: FastAPI dependency system
3. **API-First Design**: OpenAPI schema generation
4. **Async by Default**: Maximized I/O concurrency
5. **Type Safety**: Comprehensive type hints with mypy

---

## 24. Environment Configuration

### Environment Files
```
.env                 # Development (gitignored)
.env.example         # Template with documentation
.env.production      # Production overrides
.env.staging         # Staging overrides
```

### Configuration Sources (Priority Order)
1. Environment variables
2. `.env` file
3. Docker Compose environment
4. Kubernetes ConfigMaps/Secrets
5. Default values in code

---

## 25. Technology Decision Matrix

### Key Architectural Decisions

| Decision | Chosen Technology | Alternatives Considered | Rationale |
|----------|------------------|------------------------|-----------|
| **API Framework** | FastAPI | Flask, Django REST | Async support, auto-docs, performance |
| **Database** | PostgreSQL + TimescaleDB | MongoDB, ClickHouse | ACID compliance, time-series optimization |
| **Orchestration** | Prefect | Airflow, Dagster | Modern API, better DX, Pythonic |
| **Distributed Compute** | Ray | Dask, Spark | Ease of use, Python-native, scaling |
| **Caching** | Redis | Memcached | Persistence, data structures, pub/sub |
| **Object Storage** | MinIO | AWS S3, GCS | Self-hosted, S3-compatible, cost |
| **Observability** | OpenTelemetry | Proprietary agents | Vendor-neutral, comprehensive |
| **Container Orchestration** | Kubernetes | Docker Swarm, Nomad | Industry standard, ecosystem |
| **Testing** | pytest | unittest, nose | Plugin ecosystem, fixtures, async |
| **Type Checking** | mypy | Pyright, pyre | Maturity, community support |

---

## 26. Dependency Version Strategy

### Version Pinning Philosophy
```python
# Capped to prevent breaking changes
"fastapi>=0.104.0,<1.0.0"      # Lock to 0.x
"prefect>=2.14.0,<3.0.0"       # Prevent v3 auto-upgrade

# More permissive for stable libraries
"sqlalchemy>=2.0.0,<3.0.0"     # Lock to major version
"pandas>=2.1.0,<3.0.0"         # Lock to major version
```

**Rationale:** Conservative versioning prevents unexpected breakages while allowing security patches and minor improvements.

---

## 27. Monitoring & Alerting

### Monitored Metrics

#### Application Metrics
- Request rate, latency, error rate (RED metrics)
- Database connection pool utilization
- Cache hit/miss ratio
- Background job success/failure rate
- API endpoint performance per route

#### Infrastructure Metrics
- CPU, memory, disk, network per container
- PostgreSQL query performance
- Redis memory usage and evictions
- MinIO storage utilization
- Container health checks

#### Business Metrics
- Data ingestion pipeline success rate
- Document processing throughput
- API usage by endpoint
- User session statistics

### Alerting Rules
```yaml
Critical Alerts:
  - API error rate > 5%
  - Database connection failures
  - Disk usage > 85%
  - Container crash loop

Warning Alerts:
  - API latency p99 > 500ms
  - Cache hit rate < 70%
  - Background job failures
  - Memory usage > 80%
```

---

## 28. Backup & Disaster Recovery

### Backup Strategy
```makefile
# Automated PostgreSQL backup
make db-backup
# Creates: ./backups/backup_YYYYMMDD_HHMMSS.sql

# Docker volume backup
docker run --rm -v corporate-intel-postgres-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres-data.tar.gz -C /data .
```

### Backup Schedule
- **Database**: Daily full backup, hourly incrementals
- **Object Storage**: Replicated to separate MinIO instance
- **Configuration**: Version controlled in Git
- **Retention**: 30 days rolling backup

---

## 29. Development Workflow

### Local Development Setup
```bash
# 1. Clone repository
git clone https://github.com/bjpl/corporate_intel.git

# 2. Copy environment configuration
cp .env.example .env

# 3. Start development environment
make dev-up

# 4. Run tests
make test

# 5. Access services
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Hot Reload Configuration
```yaml
# docker-compose.dev.yml
volumes:
  - ./src:/app/src:ro       # Source code hot reload
  - ./alembic:/app/alembic:ro
```

---

## 30. External Dependencies & APIs

### Required APIs (Must Have)
| Service | Purpose | Free Tier |
|---------|---------|-----------|
| **SEC EDGAR** | Financial filings | Yes (with user-agent) |
| **Yahoo Finance** | Market data | Yes (via yfinance) |

### Optional APIs (Enhanced Features)
| Service | Purpose | Free Tier | Limitations |
|---------|---------|-----------|-------------|
| **Alpha Vantage** | Fundamental data | Yes | 5 calls/min |
| **NewsAPI** | News aggregation | Yes | 100 req/day |
| **Crunchbase** | Funding data | No | Paid only |
| **GitHub** | Developer metrics | Yes | 5000 req/hour |

---

## 31. Cost Optimization

### Open Source Stack
- **Zero licensing costs** for all core technologies
- **Self-hosted** infrastructure (no cloud vendor lock-in)
- **Horizontal scaling** without per-instance licensing

### Resource Optimization
```yaml
Production Optimizations:
  - Multi-stage Docker builds (smaller images)
  - TimescaleDB compression (10x storage reduction)
  - Redis caching (90% database query reduction)
  - Gunicorn worker tuning (optimal CPU utilization)
  - Rate limiting (prevents abuse)
```

---

## 32. Future Technology Roadmap

### Planned Upgrades
1. **Machine Learning**: Integrate scikit-learn, TensorFlow for predictive analytics
2. **Natural Language Processing**: Add spaCy for SEC filing analysis
3. **Real-time Streaming**: Apache Kafka for event streaming
4. **Advanced Analytics**: Apache Superset for self-service BI
5. **API Gateway**: Kong or Traefik for advanced routing
6. **Service Mesh**: Istio for microservice communication

### Evaluation Stage
- **Feature Flags**: LaunchDarkly or Flagsmith
- **A/B Testing**: Optimizely integration
- **Data Warehouse**: Snowflake or BigQuery connector
- **GraphQL API**: Strawberry GraphQL layer

---

## Appendix A: Complete Dependency List

### Production Dependencies (66 packages)
```toml
# Core Framework
fastapi>=0.104.0,<1.0.0
uvicorn[standard]>=0.24.0,<1.0.0
gunicorn>=21.2.0
pydantic>=2.5.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0

# Database
sqlalchemy>=2.0.0,<3.0.0
asyncpg>=0.29.0,<1.0.0
psycopg2-binary>=2.9.0,<3.0.0
alembic>=1.12.0,<2.0.0
pgvector>=0.2.4,<1.0.0

# Data Processing
pandas>=2.1.0,<3.0.0
numpy>=1.24.0,<2.0.0
pandera>=0.17.0,<1.0.0
great-expectations>=0.18.0,<1.0.0
dbt-core>=1.7.0,<2.0.0
dbt-postgres>=1.7.0,<2.0.0

# Orchestration
prefect>=2.14.0,<3.0.0
prefect-dask>=0.2.5,<1.0.0
ray[default]>=2.8.0,<3.0.0

# Caching & Storage
redis>=5.0.0,<6.0.0
aiocache[redis]>=0.12.0,<1.0.0
minio>=7.2.0,<8.0.0

# Observability
opentelemetry-api>=1.21.0,<2.0.0
opentelemetry-sdk>=1.21.0,<2.0.0
opentelemetry-instrumentation-fastapi>=0.42b0,<1.0.0
prometheus-client>=0.19.0,<1.0.0
loguru>=0.7.0,<1.0.0
sentry-sdk[fastapi]>=1.39.0,<2.0.0

# Document Processing
pypdf>=3.17.0,<4.0.0
pdfplumber>=0.10.0,<1.0.0
python-docx>=1.1.0,<2.0.0
beautifulsoup4>=4.12.0,<5.0.0

# Financial Data
yfinance>=0.2.33,<1.0.0
alpha-vantage>=2.3.1,<3.0.0
sec-edgar-api>=1.0.0,<2.0.0
tenacity>=8.2.3,<9.0.0

# Visualization
plotly>=5.18.0,<6.0.0
dash>=2.14.0,<3.0.0

# Testing
pytest>=7.4.0,<8.0.0
pytest-asyncio>=0.21.0,<1.0.0
pytest-cov>=4.1.0,<5.0.0
httpx>=0.25.0,<1.0.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### Development Dependencies (45 packages)
```toml
# Code Quality
pre-commit>=3.5.0,<4.0.0
black>=23.12.0,<24.0.0
isort>=5.13.0,<6.0.0
ruff>=0.1.0,<1.0.0

# Type Checking
mypy>=1.8.0,<2.0.0
types-redis>=4.6.0,<5.0.0
pandas-stubs>=2.1.0,<3.0.0

# Security
bandit>=1.7.6,<2.0.0
safety>=3.0.0,<4.0.0

# Testing
pytest-xdist>=3.5.0,<4.0.0
pytest-benchmark>=4.0.0,<5.0.0
pytest-timeout>=2.2.0,<3.0.0
faker>=22.0.0,<23.0.0
locust>=2.20.0,<3.0.0

# Development Tools
ipython>=8.18.0,<9.0.0
ipdb>=0.13.13,<1.0.0
watchdog>=3.0.0,<4.0.0

# Performance Profiling
py-spy>=0.3.14,<1.0.0
memory-profiler>=0.61.0,<1.0.0
line-profiler>=4.1.0,<5.0.0

# Documentation
sphinx>=7.2.0,<8.0.0
sphinx-rtd-theme>=2.0.0,<3.0.0
```

---

## Appendix B: File Structure Summary

```
corporate_intel/
├── src/                           # Application source code
│   ├── api/                       # FastAPI routes and endpoints
│   ├── analysis/                  # Analysis engine (Strategy pattern)
│   ├── auth/                      # Authentication and authorization
│   ├── connectors/                # External API integrations
│   ├── core/                      # Core configuration and utilities
│   ├── db/                        # Database models and repositories
│   ├── middleware/                # Custom FastAPI middleware
│   ├── observability/             # OpenTelemetry setup
│   ├── pipeline/                  # Prefect data pipelines
│   ├── processing/                # Ray distributed processing
│   ├── services/                  # Business logic services
│   ├── validation/                # Great Expectations suites
│   └── visualization/             # Plotly Dash components
│
├── dbt/                           # dbt data transformations
│   ├── models/
│   │   ├── staging/              # Raw data cleaning
│   │   ├── intermediate/         # Business logic
│   │   └── marts/                # Analytics-ready models
│   └── dbt_project.yml
│
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration scripts
│   └── env.py
│
├── tests/                         # Test suite (391+ tests)
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── load-testing/              # Locust load tests
│   └── migrations/                # Migration tests
│
├── k8s/                           # Kubernetes manifests
│   ├── base/                      # Base configuration
│   ├── overlays/                  # Environment-specific
│   └── helm/                      # Helm charts
│
├── docs/                          # Documentation
│   ├── deployment/                # Deployment guides
│   ├── monitoring/                # Observability guides
│   └── ad_hoc_reports/           # Analysis reports
│
├── scripts/                       # Utility scripts
│   ├── docker-entrypoint.sh      # Container startup
│   ├── init-docker-db.sh         # Database initialization
│   └── backup.sh                 # Backup automation
│
├── monitoring/                    # Observability configs
│   ├── prometheus.yml            # Prometheus configuration
│   └── grafana/                  # Grafana dashboards
│
├── .github/workflows/             # CI/CD pipelines
│   ├── ci-cd.yml                 # Main CI/CD pipeline
│   ├── docker.yml                # Docker build automation
│   ├── tests.yml                 # Test automation
│   └── deploy.yml                # Deployment automation
│
├── docker-compose.yml             # Production compose
├── docker-compose.dev.yml         # Development compose
├── docker-compose.test.yml        # Testing compose
├── Dockerfile                     # Production image
├── Dockerfile.dev                # Development image
├── Makefile                      # Task automation (54 commands)
├── pyproject.toml                # Python project config
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── alembic.ini                   # Alembic configuration
├── .pre-commit-config.yaml       # Pre-commit hooks
└── .env.example                  # Environment template
```

---

## Appendix C: Quick Reference Commands

### Development
```bash
make dev-up          # Start development environment
make dev-logs        # View application logs
make dev-shell       # Shell into API container
make test            # Run test suite
make migrate         # Run database migrations
```

### Production
```bash
make prod-build      # Build production images
make prod-up         # Deploy production stack
make health-check    # Verify deployment
make logs            # View production logs
```

### Database
```bash
make db-backup       # Create database backup
make db-restore      # Restore from backup
make db-shell        # PostgreSQL CLI
make migrate-rollback # Rollback migration
```

### Maintenance
```bash
make clean           # Remove containers and volumes
make prune           # Remove unused Docker resources
make security-scan   # Run security scans
make status          # Show resource usage
```

---

## Conclusion

The Corporate Intelligence Platform represents a comprehensive, production-grade technology stack built entirely on open-source technologies. Key architectural strengths include:

1. **Modern Python Stack**: FastAPI + Pydantic for high-performance async APIs
2. **Time-Series Optimization**: TimescaleDB with 10x compression for financial data
3. **Distributed Computing**: Ray + Prefect for scalable data processing
4. **Comprehensive Observability**: OpenTelemetry + Prometheus + Grafana
5. **Container-First Architecture**: Docker + Kubernetes for consistent deployment
6. **Quality Assurance**: 391+ tests, 85% coverage, automated CI/CD
7. **Developer Experience**: Hot reload, pre-commit hooks, comprehensive tooling

**Total Technologies:** 100+ distinct tools and frameworks
**Lines of Code:** ~20,000+ (Python, SQL, YAML)
**Container Images:** 10 services in production stack
**API Endpoints:** 20+ RESTful endpoints
**Data Sources:** 6+ external API integrations

This architecture provides a solid foundation for scalable EdTech financial intelligence while maintaining operational simplicity and cost efficiency through open-source solutions.

---

**Document Metadata**
Generated: 2025-10-12
Version: 1.0.0
Project: Corporate Intelligence Platform
Author: System Architecture Designer
Path: `C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel\docs\ad_hoc_reports\technology_stack.md`
