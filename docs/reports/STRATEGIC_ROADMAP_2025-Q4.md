# Corporate Intelligence Platform - Strategic Roadmap

**Roadmap Period:** Q4 2025 - Q2 2026
**Last Updated:** October 3, 2025
**Status:** Production-Ready Path

---

## Executive Summary

This roadmap provides a strategic path to transform the Corporate Intelligence Platform from its current state (8.2/10 health score) to a production-hardened, enterprise-grade system with 99.9% uptime and comprehensive observability.

### Timeline Overview

```
Week 1-2      Sprint 1-2    Quarter 1     Quarter 2
   |             |             |             |
   ↓             ↓             ↓             ↓
Critical    Code Quality  Infrastructure  Advanced
Fixes       & Testing     & Security      Features
```

### Key Milestones

- **Week 1-2:** Critical git issues resolved, pipeline complete
- **Sprint 1-2:** Test coverage 80%, code quality improved
- **Quarter 1:** Full CI/CD, security hardened, documentation complete
- **Quarter 2:** Advanced features, multi-region, ML deployment

---

## Phase 1: Critical Stabilization (Week 1-2)

**Goal:** Resolve critical blockers and establish version control

**Total Effort:** 40 hours
**Team Size:** 2-3 developers
**Priority:** CRITICAL

### Week 1: Version Control & Git Repository

**Days 1-2: Initialize Git Repository**
```bash
# Priority 1: Initialize corporate_intel repo
cd /mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel

# Create .gitignore
cat > .gitignore <<EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# MinIO
minio-data/
EOF

# Initialize repository
git init
git add .
git commit -m "feat: initial commit - Corporate Intelligence Platform

- FastAPI-based EdTech analytics platform
- PostgreSQL + TimescaleDB for time-series
- Ray distributed processing
- Comprehensive observability stack
- Production-ready containerization"

# Create remote repository (GitHub/GitLab)
gh repo create corporate-intel --private --source=. --remote=origin --push
```

**Days 3-4: Resolve Branch Divergence**
```bash
# Navigate to parent workspace
cd ../..

# Backup current state
git stash save "Backup before merge"

# Fetch latest from origin
git fetch origin main

# Analyze differences
git log origin/main..HEAD --oneline > local_commits.txt
git log HEAD..origin/main --oneline > remote_commits.txt

# Create merge strategy
# Option A: Merge (preserves all history)
git merge origin/main -m "Merge origin/main - reconcile divergence"

# Option B: Rebase (linear history)
# git rebase origin/main

# Resolve conflicts if any
git status
# Fix conflicts, then:
git add .
git commit -m "Resolve merge conflicts"

# Push reconciled state
git push origin main
```

**Day 5: Documentation & Cleanup**
- Create CONTRIBUTING.md (4h)
- Add LICENSE file (1h)
- Update README with git workflow (2h)
- Clean up 162 untracked files (1h)

**Deliverables:**
- ✅ Git repository initialized
- ✅ Branch divergence resolved
- ✅ .gitignore configured
- ✅ CONTRIBUTING.md created
- ✅ LICENSE added (MIT recommended)

### Week 2: Complete Pipeline Implementation

**Days 1-3: SEC Pipeline Completion**

**Task 1: Implement Great Expectations Validation (8h)**
```python
# File: src/pipeline/sec_ingestion.py, line 208

import great_expectations as ge
from great_expectations.core.batch import RuntimeBatchRequest

def validate_filing_data(df: pd.DataFrame) -> bool:
    """Validate SEC filing data using Great Expectations."""

    # Create expectation suite
    suite = ge.core.ExpectationSuite(
        expectation_suite_name="sec_filing_validation"
    )

    # Add expectations
    suite.add_expectation(
        ge.core.ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={"column": "cik"}
        )
    )

    suite.add_expectation(
        ge.core.ExpectationConfiguration(
            expectation_type="expect_column_values_to_match_regex",
            kwargs={
                "column": "form_type",
                "regex": "^(10-K|10-Q|8-K)$"
            }
        )
    )

    suite.add_expectation(
        ge.core.ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_of_type",
            kwargs={
                "column": "filing_date",
                "type_": "datetime64"
            }
        )
    )

    # Create data context
    context = ge.data_context.DataContext()

    # Validate
    batch = ge.dataset.PandasDataset(df)
    results = batch.validate(expectation_suite=suite)

    if not results.success:
        logger.error(f"Validation failed: {results}")
        raise DataValidationError(results)

    return True
```

**Task 2: Implement Database Storage (4h)**
```python
# File: src/pipeline/sec_ingestion.py, line 228

async def store_filing_in_database(
    session: AsyncSession,
    filing_data: Dict[str, Any]
) -> int:
    """Store SEC filing in PostgreSQL with TimescaleDB."""

    from src.db.models import SECFiling, Company

    # Check if company exists
    company = await session.execute(
        select(Company).where(Company.cik == filing_data["cik"])
    )
    company = company.scalar_one_or_none()

    if not company:
        # Create company record
        company = Company(
            cik=filing_data["cik"],
            name=filing_data["company_name"],
            ticker=filing_data.get("ticker")
        )
        session.add(company)
        await session.flush()

    # Create filing record
    filing = SECFiling(
        company_id=company.id,
        form_type=filing_data["form_type"],
        filing_date=filing_data["filing_date"],
        accession_number=filing_data["accession_number"],
        document_url=filing_data["document_url"],
        raw_content=filing_data["content"],
        parsed_data=filing_data.get("parsed_data", {})
    )

    session.add(filing)
    await session.commit()

    logger.info(f"Stored filing {filing.accession_number} for {company.name}")

    return filing.id
```

**Days 4-5: Quick Wins**

**Task 3: Fix Wildcard Imports (4h)**
```python
# Before (alembic/env.py):
from src.db.models import *
from src.auth.models import *

# After:
from src.db.models import (
    Base,
    Company,
    SECFiling,
    FinancialMetric,
    MarketSegment
)
from src.auth.models import User, APIKey
```

**Task 4: Add SECRET_KEY Validation (2h)**
```python
# File: src/core/config.py

from pydantic import Field, validator

class Settings(BaseSettings):
    SECRET_KEY: str = Field(
        ...,  # Required
        min_length=32,
        description="JWT secret key - must be 32+ characters"
    )

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate with: openssl rand -hex 32"
            )
        if v == "your-secret-key-here":
            raise ValueError(
                "SECRET_KEY cannot be default value. "
                "Set a secure random key."
            )
        return v
```

**Task 5: Pin Dependency Versions (4h)**
```python
# requirements.txt - Update from:
fastapi>=0.104.0
pandas>=2.1.0
sqlalchemy>=2.0.0

# To:
fastapi>=0.104.0,<1.0.0
pandas>=2.1.0,<3.0.0
sqlalchemy>=2.0.0,<3.0.0
ray>=2.8.0,<3.0.0
prefect>=2.14.0,<3.0.0
```

**Deliverables:**
- ✅ Great Expectations validation implemented
- ✅ Database storage completed
- ✅ Wildcard imports fixed
- ✅ SECRET_KEY validation added
- ✅ Dependencies pinned with upper bounds
- ✅ All tests passing

---

## Phase 2: Code Quality & Testing (Sprint 1-2, 4 weeks)

**Goal:** Achieve 80% test coverage and resolve major technical debt

**Total Effort:** 72 hours
**Team Size:** 3-4 developers
**Priority:** HIGH

### Sprint 1 (Weeks 3-4): Exception Handling & File Refactoring

**Week 3: Exception Handling Improvements**

**Task 1: Specific Exception Types (12h)**
```python
# Create custom exception hierarchy
# File: src/core/exceptions.py

class CorporateIntelError(Exception):
    """Base exception for Corporate Intel platform."""
    pass

class DataValidationError(CorporateIntelError):
    """Data validation failed."""
    pass

class ExternalAPIError(CorporateIntelError):
    """External API request failed."""

    def __init__(self, service: str, message: str, status_code: int = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service} API error: {message}")

class DatabaseError(CorporateIntelError):
    """Database operation failed."""
    pass

class AuthenticationError(CorporateIntelError):
    """Authentication failed."""
    pass

# Update 39 exception handlers across codebase:
# Before:
try:
    result = await fetch_data()
except Exception as e:
    logger.error(f"Error: {e}")

# After:
try:
    result = await fetch_data()
except asyncio.TimeoutError:
    raise ExternalAPIError("SEC", "Request timeout", 408)
except aiohttp.ClientError as e:
    raise ExternalAPIError("SEC", str(e), e.status)
except ValidationError as e:
    raise DataValidationError(f"Invalid data: {e}")
```

**Task 2: Remove Console Logging (4h)**
```python
# Find and replace across 14 files:
# Before:
print(f"Processing {filename}")
console.log("Debug info")

# After:
logger.info(f"Processing {filename}")
logger.debug("Debug info")
```

**Week 4: File Refactoring**

**Task 3: Break Down Large Files (16h)**

**File 1: tests/unit/test_data_quality.py (596 lines)**
```
Split into:
├── tests/unit/data_quality/
│   ├── test_validation_rules.py (200 lines)
│   ├── test_quality_metrics.py (180 lines)
│   ├── test_data_profiling.py (150 lines)
│   └── test_anomaly_detection.py (100 lines)
```

**File 2: tests/unit/test_integrations.py (586 lines)**
```
Split into:
├── tests/unit/integrations/
│   ├── test_sec_api.py (150 lines)
│   ├── test_yahoo_finance.py (140 lines)
│   ├── test_alpha_vantage.py (130 lines)
│   ├── test_newsapi.py (120 lines)
│   └── test_crunchbase.py (80 lines)
```

**File 3: src/connectors/data_sources.py (553 lines)**
```
Split into:
├── src/connectors/
│   ├── base.py (100 lines) - Base connector class
│   ├── sec_edgar.py (120 lines)
│   ├── yahoo_finance.py (110 lines)
│   ├── alpha_vantage.py (100 lines)
│   ├── news_api.py (80 lines)
│   └── crunchbase.py (70 lines)
```

**Task 4: Extract Shared Utilities (2h)**
```python
# Create: src/core/rate_limiter.py
# Extract RateLimiter from:
# - src/pipeline/sec_ingestion.py (lines 122-138)
# - src/connectors/data_sources.py (lines 42-60)

class RateLimiter:
    """Thread-safe rate limiter with token bucket algorithm."""

    def __init__(self, requests_per_second: float):
        self.rate = requests_per_second
        self.tokens = requests_per_second
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire token, waiting if necessary."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.rate,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1
```

### Sprint 2 (Weeks 5-6): Test Coverage Expansion

**Week 5: Add Missing Unit Tests**

**Task 1: Identify Coverage Gaps (4h)**
```bash
# Run coverage analysis
pytest --cov=src --cov-report=html --cov-report=term-missing

# Generate report
python -m coverage report -m > coverage_gaps.txt

# Prioritize files with <70% coverage
grep -E "^src/" coverage_gaps.txt | awk '$NF < 70 {print $0}'
```

**Task 2: Write Unit Tests (24h)**

**Target modules (prioritized):**
1. `src/analysis/engine.py` - Analysis strategies (6h)
2. `src/pipeline/sec_ingestion.py` - SEC pipeline (6h)
3. `src/auth/service.py` - Authentication (4h)
4. `src/connectors/` - External APIs (8h)

**Example test structure:**
```python
# tests/unit/analysis/test_competitor_strategy.py

import pytest
from src.analysis.strategies import CompetitorAnalysisStrategy

class TestCompetitorAnalysisStrategy:
    @pytest.fixture
    def strategy(self):
        return CompetitorAnalysisStrategy()

    @pytest.fixture
    def sample_companies(self):
        return [
            {"id": 1, "name": "Coursera", "segment": "Higher Ed"},
            {"id": 2, "name": "Udemy", "segment": "D2C"},
        ]

    async def test_analyze_market_concentration(
        self, strategy, sample_companies
    ):
        """Test HHI calculation."""
        result = await strategy.analyze(sample_companies)

        assert "market_concentration" in result
        assert "herfindahl_index" in result["market_concentration"]
        assert 0 <= result["market_concentration"]["herfindahl_index"] <= 10000

    async def test_competitor_positioning(self, strategy, sample_companies):
        """Test competitive positioning analysis."""
        result = await strategy.analyze(sample_companies)

        assert "positioning" in result
        assert len(result["positioning"]) == len(sample_companies)

        for position in result["positioning"]:
            assert "company_id" in position
            assert "market_share" in position
            assert "growth_rate" in position
```

**Week 6: Integration Tests & Coverage Gates**

**Task 3: Add Integration Tests (12h)**
```python
# tests/integration/test_full_pipeline.py

import pytest
from datetime import datetime, timedelta

@pytest.mark.integration
async def test_sec_filing_pipeline_end_to_end(
    db_session, mock_sec_api
):
    """Test complete SEC filing ingestion pipeline."""

    # Setup
    cik = "0001326801"  # Facebook/Meta
    filing_date = datetime.now() - timedelta(days=30)

    # Execute pipeline
    from src.pipeline.sec_ingestion import SECIngestionPipeline
    pipeline = SECIngestionPipeline()

    filing_id = await pipeline.ingest_filing(
        cik=cik,
        form_type="10-Q",
        filing_date=filing_date
    )

    # Verify database storage
    from src.db.models import SECFiling
    filing = await db_session.get(SECFiling, filing_id)

    assert filing is not None
    assert filing.form_type == "10-Q"
    assert filing.company.cik == cik
    assert filing.parsed_data is not None

    # Verify data quality
    assert filing.parsed_data.get("revenue") is not None
    assert filing.parsed_data.get("net_income") is not None

    # Verify TimescaleDB hypertable
    result = await db_session.execute(
        "SELECT * FROM timescaledb_information.hypertables "
        "WHERE hypertable_name = 'sec_filings'"
    )
    assert result.rowcount > 0
```

**Task 4: Set Coverage Gates (4h)**
```yaml
# .github/workflows/test-coverage.yml

name: Test Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov

      - name: Run tests with coverage
        run: |
          pytest --cov=src \
                 --cov-report=xml \
                 --cov-report=term \
                 --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

**Deliverables:**
- ✅ Specific exception handling implemented
- ✅ Large files refactored into modules
- ✅ Shared utilities extracted
- ✅ Test coverage increased to 80%
- ✅ Coverage gates in CI/CD
- ✅ Integration tests added

---

## Phase 3: Infrastructure & Security (Quarter 1, 12 weeks)

**Goal:** Production-hardened infrastructure with comprehensive security

**Total Effort:** 120 hours
**Team Size:** 4-5 developers
**Priority:** HIGH

### Month 1: CI/CD Pipeline Implementation

**Week 7-8: Complete CI/CD Workflows**

**Task 1: Automated Testing Pipeline (16h)**
```yaml
# .github/workflows/ci.yml

name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install black flake8 mypy

      - name: Black formatting
        run: black --check src/ tests/

      - name: Flake8 linting
        run: flake8 src/ tests/

      - name: MyPy type checking
        run: mypy src/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov pytest-asyncio

      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: alembic upgrade head

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Bandit security scan
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: Run Safety dependency check
        run: |
          pip install safety
          safety check --file requirements.txt

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json
```

**Task 2: Docker Build & Registry (8h)**
```yaml
# .github/workflows/docker-build.yml

name: Docker Build

on:
  push:
    branches: [main]
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to DockerHub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: corporateintel/api
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=registry,ref=corporateintel/api:buildcache
          cache-to: type=registry,ref=corporateintel/api:buildcache,mode=max
```

**Week 9-10: Infrastructure as Code**

**Task 3: Terraform Configuration (16h)**
```hcl
# terraform/main.tf

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "corporate-intel-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
  }
}

# VPC and networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "corporate-intel-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Environment = "production"
    Project     = "corporate-intel"
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"

  cluster_name    = "corporate-intel-prod"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 2
      max_size     = 10

      instance_types = ["t3.large"]
      capacity_type  = "ON_DEMAND"
    }

    processing = {
      desired_size = 2
      min_size     = 1
      max_size     = 20

      instance_types = ["c6i.2xlarge"]
      capacity_type  = "SPOT"

      labels = {
        workload = "processing"
      }

      taints = [{
        key    = "processing"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
  }
}

# RDS PostgreSQL with TimescaleDB
module "db" {
  source = "terraform-aws-modules/rds/aws"

  identifier = "corporate-intel-db"

  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.r6g.xlarge"
  allocated_storage    = 100
  storage_encrypted    = true

  db_name  = "corporate_intel"
  username = "postgres"
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name

  backup_retention_period = 7
  backup_window          = "03:00-06:00"
  maintenance_window     = "Mon:00:00-Mon:03:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  parameters = [
    {
      name  = "shared_preload_libraries"
      value = "timescaledb,pg_stat_statements"
    }
  ]
}

# ElastiCache Redis
module "redis" {
  source = "terraform-aws-modules/elasticache/aws"

  cluster_id           = "corporate-intel-cache"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 3
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379

  subnet_group_name = module.vpc.elasticache_subnet_group_name
  security_group_ids = [aws_security_group.redis.id]

  automatic_failover_enabled = true
}

# S3 for object storage (MinIO alternative)
resource "aws_s3_bucket" "storage" {
  bucket = "corporate-intel-storage-prod"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}
```

### Month 2: Security Hardening

**Week 11-12: Security Implementations**

**Task 4: API Key Rotation System (8h)**
```python
# src/auth/key_rotation.py

from datetime import datetime, timedelta
from typing import Optional
import secrets

class APIKeyRotation:
    """Manages API key rotation and lifecycle."""

    def __init__(
        self,
        rotation_days: int = 90,
        grace_period_days: int = 7
    ):
        self.rotation_days = rotation_days
        self.grace_period_days = grace_period_days

    async def create_key(
        self,
        user_id: int,
        name: str,
        expires_in_days: Optional[int] = None
    ) -> APIKey:
        """Create new API key with automatic expiration."""

        key = f"ci_{secrets.token_urlsafe(32)}"

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=hash_key(key),
            expires_at=expires_at,
            last_used_at=None,
            rotation_required=False
        )

        await db.add(api_key)

        # Only return raw key once
        return key, api_key

    async def check_rotation_required(self, api_key: APIKey) -> bool:
        """Check if key needs rotation based on age."""

        if api_key.rotation_required:
            return True

        age = datetime.utcnow() - api_key.created_at
        if age.days >= self.rotation_days:
            api_key.rotation_required = True
            await db.commit()
            return True

        return False

    async def rotate_key(
        self,
        old_key_id: int,
        user_id: int
    ) -> tuple[str, APIKey]:
        """Rotate API key with grace period."""

        old_key = await db.get(APIKey, old_key_id)
        if old_key.user_id != user_id:
            raise PermissionError("Cannot rotate other user's keys")

        # Create new key
        new_key, new_api_key = await self.create_key(
            user_id=user_id,
            name=f"{old_key.name} (rotated)"
        )

        # Set grace period for old key
        old_key.expires_at = datetime.utcnow() + timedelta(
            days=self.grace_period_days
        )
        old_key.rotation_required = False

        await db.commit()

        # Notify user
        await send_key_rotation_notification(user_id, new_api_key.id)

        return new_key, new_api_key
```

**Task 5: Audit Logging System (8h)**
```python
# src/observability/audit.py

from enum import Enum
from typing import Optional, Dict, Any
import json

class AuditAction(Enum):
    """Audit action types."""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    API_KEY_CREATED = "api_key.created"
    API_KEY_ROTATED = "api_key.rotated"
    API_KEY_REVOKED = "api_key.revoked"
    DATA_ACCESSED = "data.accessed"
    DATA_MODIFIED = "data.modified"
    CONFIG_CHANGED = "config.changed"
    PERMISSION_CHANGED = "permission.changed"

class AuditLogger:
    """Structured audit logging with compliance requirements."""

    def __init__(self):
        self.logger = logging.getLogger("audit")

    async def log(
        self,
        action: AuditAction,
        user_id: Optional[int],
        resource_type: str,
        resource_id: Optional[str],
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log audit event with structured data."""

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action.value,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }

        # Store in database
        audit_log = AuditLog(**audit_entry)
        await db.add(audit_log)

        # Send to SIEM
        await self.send_to_siem(audit_entry)

        # Log for observability
        self.logger.info(
            "Audit event",
            extra=audit_entry
        )

    async def send_to_siem(self, audit_entry: Dict[str, Any]):
        """Send audit log to SIEM system."""
        # Integration with Splunk, ELK, or cloud SIEM
        pass

# Usage in endpoints:
from fastapi import Request

@router.post("/data/export")
async def export_data(
    request: Request,
    user: User = Depends(get_current_user),
    audit: AuditLogger = Depends()
):
    """Export sensitive data with audit trail."""

    await audit.log(
        action=AuditAction.DATA_ACCESSED,
        user_id=user.id,
        resource_type="data_export",
        resource_id=None,
        details={"format": "csv", "rows": 1000},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    # Perform export...
    return export_result
```

**Week 13-14: Disaster Recovery**

**Task 6: Backup & Recovery Plan (12h)**
```yaml
# k8s/cronjobs/backup.yaml

apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
  namespace: corporate-intel
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            env:
            - name: PGHOST
              valueFrom:
                secretKeyRef:
                  name: database-credentials
                  key: host
            - name: PGDATABASE
              value: corporate_intel
            - name: PGUSER
              valueFrom:
                secretKeyRef:
                  name: database-credentials
                  key: username
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: database-credentials
                  key: password
            command:
            - /bin/sh
            - -c
            - |
              BACKUP_FILE="/backups/corporate_intel_$(date +%Y%m%d_%H%M%S).sql.gz"
              pg_dump --format=custom | gzip > $BACKUP_FILE

              # Upload to S3
              aws s3 cp $BACKUP_FILE s3://corporate-intel-backups/

              # Keep last 30 days locally
              find /backups -name "*.sql.gz" -mtime +30 -delete
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

**Recovery Procedures:**
```bash
# scripts/disaster_recovery/restore_from_backup.sh

#!/bin/bash
set -euo pipefail

BACKUP_DATE=$1
BACKUP_FILE="corporate_intel_${BACKUP_DATE}.sql.gz"

echo "Starting disaster recovery process..."

# 1. Download backup from S3
aws s3 cp "s3://corporate-intel-backups/${BACKUP_FILE}" /tmp/

# 2. Stop application pods
kubectl scale deployment/api --replicas=0 -n corporate-intel

# 3. Create new database (if needed)
psql -h $DB_HOST -U postgres -c "DROP DATABASE IF EXISTS corporate_intel_recovery;"
psql -h $DB_HOST -U postgres -c "CREATE DATABASE corporate_intel_recovery;"

# 4. Restore backup
gunzip -c "/tmp/${BACKUP_FILE}" | pg_restore -h $DB_HOST -U postgres -d corporate_intel_recovery

# 5. Run integrity checks
psql -h $DB_HOST -U postgres -d corporate_intel_recovery -c "SELECT COUNT(*) FROM companies;"
psql -h $DB_HOST -U postgres -d corporate_intel_recovery -c "SELECT COUNT(*) FROM sec_filings;"

# 6. Swap databases
psql -h $DB_HOST -U postgres <<EOF
ALTER DATABASE corporate_intel RENAME TO corporate_intel_old;
ALTER DATABASE corporate_intel_recovery RENAME TO corporate_intel;
EOF

# 7. Restart application
kubectl scale deployment/api --replicas=3 -n corporate-intel

echo "Recovery complete! Verify application functionality."
```

### Month 3: Monitoring & Observability

**Week 15-16: Monitoring Dashboards**

**Task 7: Grafana Dashboards (8h)**
```yaml
# monitoring/dashboards/api_performance.json

{
  "dashboard": {
    "title": "Corporate Intel API Performance",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total{job=\"api\"}[5m])"
        }]
      },
      {
        "title": "Response Time (p50, p95, p99)",
        "targets": [
          {"expr": "histogram_quantile(0.50, http_request_duration_seconds)"},
          {"expr": "histogram_quantile(0.95, http_request_duration_seconds)"},
          {"expr": "histogram_quantile(0.99, http_request_duration_seconds)"}
        ]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }]
      },
      {
        "title": "Database Connection Pool",
        "targets": [
          {"expr": "db_connection_pool_size"},
          {"expr": "db_connection_pool_active"}
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [{
          "expr": "rate(redis_cache_hits[5m]) / (rate(redis_cache_hits[5m]) + rate(redis_cache_misses[5m]))"
        }]
      },
      {
        "title": "Ray Processing Throughput",
        "targets": [{
          "expr": "rate(ray_tasks_completed[5m])"
        }]
      }
    ]
  }
}
```

**Task 8: Alerting Rules (8h)**
```yaml
# monitoring/alerts/corporate_intel.rules.yml

groups:
- name: corporate_intel_api
  interval: 30s
  rules:

  # High error rate
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API error rate (> 5%)"
      description: "{{ $value | humanizePercentage }} of requests are failing"

  # Slow response time
  - alert: SlowResponseTime
    expr: histogram_quantile(0.99, http_request_duration_seconds) > 1.0
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "API response time degraded (p99 > 1s)"
      description: "99th percentile response time is {{ $value }}s"

  # Database connection pool exhausted
  - alert: DatabasePoolExhausted
    expr: db_connection_pool_active / db_connection_pool_size > 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Database connection pool nearly exhausted"
      description: "{{ $value | humanizePercentage }} of connections in use"

  # Cache unavailable
  - alert: CacheUnavailable
    expr: up{job="redis"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Redis cache is unavailable"
      description: "Application may experience degraded performance"

  # Disk space low
  - alert: DiskSpaceLow
    expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.15
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Disk space running low (< 15% free)"
      description: "Only {{ $value | humanizePercentage }} disk space remaining"

  # Pod restart loop
  - alert: PodRestartLoop
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.05
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Pod is restarting frequently"
      description: "{{ $labels.pod }} has restarted {{ $value }} times"
```

**Deliverables (Phase 3):**
- ✅ Complete CI/CD pipeline with automated testing
- ✅ Infrastructure as Code (Terraform)
- ✅ API key rotation system
- ✅ Comprehensive audit logging
- ✅ Disaster recovery plan with automated backups
- ✅ Production monitoring dashboards
- ✅ Alerting rules configured

---

## Phase 4: Advanced Features (Quarter 2, 12 weeks)

**Goal:** Implement advanced analytics and ML capabilities

**Total Effort:** 140 hours
**Team Size:** 5-6 developers
**Priority:** MEDIUM

### Month 4: Rate Limiting & Performance

**Week 17-18: Rate Limiting Implementation**

**Task 1: FastAPI Rate Limiting (4h)**
```python
# src/middleware/rate_limit.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://redis:6379/1"
)

# In main.py:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints:
@app.get("/api/v1/companies")
@limiter.limit("100/minute")
async def list_companies(request: Request):
    """List companies with rate limiting."""
    pass

@app.post("/api/v1/intelligence/analyze")
@limiter.limit("10/minute")
async def analyze_intelligence(request: Request):
    """Heavy analysis endpoint with stricter limits."""
    pass
```

**Week 19-20: Query Optimization**

**Task 2: Database Indexing Strategy (8h)**
```sql
-- Add strategic indexes for performance

-- Companies table
CREATE INDEX CONCURRENTLY idx_companies_ticker ON companies(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_companies_segment ON companies(market_segment);
CREATE INDEX CONCURRENTLY idx_companies_founded ON companies(founded_date) WHERE founded_date IS NOT NULL;

-- SEC filings table (TimescaleDB hypertable)
CREATE INDEX CONCURRENTLY idx_filings_company_date ON sec_filings(company_id, filing_date DESC);
CREATE INDEX CONCURRENTLY idx_filings_form_type ON sec_filings(form_type);
CREATE INDEX CONCURRENTLY idx_filings_accession ON sec_filings(accession_number);

-- Financial metrics
CREATE INDEX CONCURRENTLY idx_metrics_company_date ON financial_metrics(company_id, metric_date DESC);
CREATE INDEX CONCURRENTLY idx_metrics_type_value ON financial_metrics(metric_type, metric_value) WHERE metric_value IS NOT NULL;

-- Full-text search
CREATE INDEX CONCURRENTLY idx_filings_content_fts ON sec_filings USING GIN(to_tsvector('english', raw_content));

-- Vector similarity search (pgvector)
CREATE INDEX CONCURRENTLY idx_filings_embedding ON sec_filings USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
```

**Task 3: Query Result Caching (8h)**
```python
# src/core/cache.py

from functools import wraps
import hashlib
import json
from typing import Any, Callable, Optional

class QueryCache:
    """Intelligent query result caching with Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes

    def cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function and arguments."""
        key_data = {
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]
        return f"query_cache:{func_name}:{key_hash}"

    def cached(
        self,
        ttl: Optional[int] = None,
        invalidate_on: Optional[list] = None
    ):
        """Decorator to cache function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.cache_key(func.__name__, *args, **kwargs)

                # Try to get from cache
                cached_result = await self.redis.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit: {cache_key}")
                    return json.loads(cached_result)

                # Execute function
                result = await func(*args, **kwargs)

                # Store in cache
                cache_ttl = ttl or self.default_ttl
                await self.redis.setex(
                    cache_key,
                    cache_ttl,
                    json.dumps(result, default=str)
                )

                logger.debug(f"Cache miss: {cache_key}")
                return result

            return wrapper
        return decorator

# Usage:
from src.core.cache import QueryCache

cache = QueryCache(redis_client)

@cache.cached(ttl=600)
async def get_company_metrics(company_id: int) -> dict:
    """Get company metrics with caching."""
    query = select(FinancialMetric).where(
        FinancialMetric.company_id == company_id
    ).order_by(FinancialMetric.metric_date.desc()).limit(100)

    results = await session.execute(query)
    return [row.to_dict() for row in results.scalars()]
```

### Month 5: GraphQL API Layer

**Week 21-22: GraphQL Implementation**

**Task 4: Strawberry GraphQL Setup (20h)**
```python
# src/api/graphql/schema.py

import strawberry
from typing import List, Optional
from datetime import datetime

@strawberry.type
class Company:
    id: int
    name: str
    ticker: Optional[str]
    cik: str
    market_segment: str
    founded_date: Optional[datetime]

    @strawberry.field
    async def filings(
        self,
        limit: int = 10,
        form_type: Optional[str] = None
    ) -> List["SECFiling"]:
        """Get company's SEC filings."""
        query = select(SECFiling).where(
            SECFiling.company_id == self.id
        )

        if form_type:
            query = query.where(SECFiling.form_type == form_type)

        query = query.order_by(
            SECFiling.filing_date.desc()
        ).limit(limit)

        results = await session.execute(query)
        return results.scalars().all()

    @strawberry.field
    async def metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List["FinancialMetric"]:
        """Get company's financial metrics."""
        query = select(FinancialMetric).where(
            FinancialMetric.company_id == self.id
        )

        if start_date:
            query = query.where(FinancialMetric.metric_date >= start_date)
        if end_date:
            query = query.where(FinancialMetric.metric_date <= end_date)

        results = await session.execute(query)
        return results.scalars().all()

@strawberry.type
class Query:
    @strawberry.field
    async def companies(
        self,
        segment: Optional[str] = None,
        limit: int = 100
    ) -> List[Company]:
        """List companies with optional filtering."""
        query = select(CompanyModel)

        if segment:
            query = query.where(CompanyModel.market_segment == segment)

        query = query.limit(limit)

        results = await session.execute(query)
        return results.scalars().all()

    @strawberry.field
    async def company(self, id: int) -> Optional[Company]:
        """Get company by ID."""
        result = await session.get(CompanyModel, id)
        return result

    @strawberry.field
    async def search_companies(
        self,
        query: str,
        limit: int = 10
    ) -> List[Company]:
        """Full-text search for companies."""
        sql_query = select(CompanyModel).where(
            func.to_tsvector('english', CompanyModel.name).match(query)
        ).limit(limit)

        results = await session.execute(sql_query)
        return results.scalars().all()

schema = strawberry.Schema(query=Query)

# In main.py:
from strawberry.fastapi import GraphQLRouter

graphql_router = GraphQLRouter(schema)
app.include_router(graphql_router, prefix="/graphql")
```

### Month 6: ML Model Deployment

**Week 23-24: Sentiment Analysis Model**

**Task 5: Deploy BERT for Financial Sentiment (40h)**
```python
# src/ml/sentiment_analyzer.py

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Dict
import ray

@ray.remote
class SentimentAnalyzer:
    """Distributed sentiment analysis with FinBERT."""

    def __init__(self):
        self.model_name = "ProsusAI/finbert"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name
        ).to(self.device)

        self.labels = ["positive", "negative", "neutral"]

    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of financial text."""

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.nn.functional.softmax(
                outputs.logits,
                dim=-1
            ).cpu().numpy()[0]

        # Return scores
        return {
            label: float(prob)
            for label, prob in zip(self.labels, probabilities)
        }

    def batch_analyze(self, texts: List[str]) -> List[Dict[str, float]]:
        """Batch sentiment analysis for efficiency."""

        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.nn.functional.softmax(
                outputs.logits,
                dim=-1
            ).cpu().numpy()

        return [
            {label: float(prob) for label, prob in zip(self.labels, probs)}
            for probs in probabilities
        ]

# Deploy as Ray actors for distributed inference
ray.init()

sentiment_analyzers = [
    SentimentAnalyzer.remote()
    for _ in range(4)  # 4 parallel analyzers
]

async def analyze_filing_sentiment(filing_text: str) -> Dict[str, float]:
    """Analyze SEC filing sentiment using Ray."""

    # Split text into paragraphs
    paragraphs = [p.strip() for p in filing_text.split('\n\n') if len(p) > 50]

    # Distribute across analyzers
    batch_size = len(paragraphs) // len(sentiment_analyzers)

    futures = []
    for i, analyzer in enumerate(sentiment_analyzers):
        start = i * batch_size
        end = start + batch_size if i < len(sentiment_analyzers) - 1 else len(paragraphs)

        futures.append(
            analyzer.batch_analyze.remote(paragraphs[start:end])
        )

    # Collect results
    results = await asyncio.gather(*[ray.get(f) for f in futures])

    # Aggregate sentiment scores
    all_scores = [score for batch in results for score in batch]

    avg_sentiment = {
        label: sum(s[label] for s in all_scores) / len(all_scores)
        for label in ["positive", "negative", "neutral"]
    }

    return avg_sentiment
```

**Deliverables (Phase 4):**
- ✅ Rate limiting implemented
- ✅ Database query optimization complete
- ✅ Result caching system deployed
- ✅ GraphQL API layer operational
- ✅ ML sentiment analysis model deployed
- ✅ Distributed inference with Ray

---

## Success Metrics & KPIs

### Technical Metrics

| Metric | Baseline | Q1 Target | Q2 Target | Measurement |
|--------|----------|-----------|-----------|-------------|
| Test Coverage | 45% | 80% | 90% | Codecov |
| API Response (p99) | N/A | < 100ms | < 50ms | Prometheus |
| Uptime | N/A | 99.5% | 99.9% | Grafana |
| Error Rate | N/A | < 1% | < 0.1% | Sentry |
| Deployment Time | Manual | < 30min | < 15min | CI/CD |
| Technical Debt | 15% | 8% | 5% | SonarQube |

### Business Metrics

| Metric | Q1 Target | Q2 Target | Description |
|--------|-----------|-----------|-------------|
| Time to Deploy | 30 minutes | 15 minutes | From commit to production |
| Deployment Frequency | 2x/week | Daily | Automated deployments |
| Change Failure Rate | < 10% | < 5% | Failed deployments |
| MTTR | < 2 hours | < 1 hour | Mean time to recovery |
| Developer Onboarding | 4 hours | 2 hours | New dev setup time |

### Security Metrics

| Metric | Q1 Target | Q2 Target | Status |
|--------|-----------|-----------|--------|
| Critical Vulnerabilities | 0 | 0 | Ongoing |
| Secrets in Vault | 100% | 100% | Q1 |
| Audit Log Coverage | 90% | 100% | Q1 |
| Security Scan Frequency | Weekly | Daily | Q2 |

---

## Risk Management

### Critical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss (no git) | HIGH | CRITICAL | Initialize git immediately (Week 1) |
| Branch merge conflicts | MEDIUM | HIGH | Careful merge strategy with testing |
| Pipeline failures | MEDIUM | HIGH | Complete TODOs with comprehensive tests |
| Dependency breaking changes | LOW | MEDIUM | Pin versions with upper bounds |

### Mitigation Strategies

**Week 1 (CRITICAL):**
- Daily backups before git initialization
- Test merge strategy on separate branch
- Document rollback procedures

**Sprint 1:**
- Comprehensive test coverage before refactoring
- Feature flags for risky changes
- Staged rollout (dev → staging → production)

**Quarter 1:**
- Disaster recovery drills monthly
- Security audits quarterly
- Performance load testing before launch

---

## Budget & Resource Allocation

### Team Composition

**Phase 1 (Week 1-2):** 2-3 developers
- 1 Senior Backend Engineer (git, pipeline)
- 1 DevOps Engineer (infrastructure)
- 1 QA Engineer (testing)

**Phase 2 (Sprint 1-2):** 3-4 developers
- 2 Backend Engineers (refactoring, tests)
- 1 QA Engineer (coverage expansion)
- 1 DevOps Engineer (CI/CD)

**Phase 3 (Quarter 1):** 4-5 developers
- 2 Backend Engineers (features, optimization)
- 1 Security Engineer (hardening, audits)
- 1 DevOps Engineer (infrastructure, monitoring)
- 1 QA Engineer (integration testing)

**Phase 4 (Quarter 2):** 5-6 developers
- 3 Backend Engineers (GraphQL, ML)
- 1 ML Engineer (model deployment)
- 1 DevOps Engineer (scaling, multi-region)
- 1 QA Engineer (performance testing)

### Infrastructure Costs (Monthly)

**Development/Staging:**
- EKS cluster: $150
- RDS (db.t3.medium): $70
- ElastiCache (cache.t3.micro): $20
- S3 storage: $10
- **Total:** ~$250/month

**Production:**
- EKS cluster (3 nodes): $300
- RDS (db.r6g.xlarge): $400
- ElastiCache (cache.r6g.large): $200
- S3 storage: $50
- CloudWatch/monitoring: $100
- **Total:** ~$1,050/month

---

## Conclusion

This strategic roadmap provides a clear path from the current state (8.2/10 health score) to a production-hardened, enterprise-grade system. By following this phased approach:

**Week 1-2:** Critical stabilization (git, pipeline completion)
**Sprint 1-2:** Code quality & testing (80% coverage)
**Quarter 1:** Infrastructure & security hardening
**Quarter 2:** Advanced features & ML deployment

The platform will achieve:
- ✅ 99.9% uptime with comprehensive monitoring
- ✅ < 100ms API response time (p99)
- ✅ 90% test coverage with automated gates
- ✅ Complete security hardening with audit trails
- ✅ Production-grade infrastructure with disaster recovery
- ✅ Advanced ML-powered analytics capabilities

**Estimated Timeline:** 6 months
**Estimated Effort:** 372 developer-hours
**Estimated Infrastructure Cost:** $7,800 for 6 months

**Next Steps:**
1. Review and approve roadmap
2. Allocate team resources
3. Begin Phase 1 (Week 1) immediately
4. Schedule weekly progress reviews
5. Adjust timeline based on actual velocity

---

**Roadmap Version:** 1.0
**Last Updated:** October 3, 2025
**Next Review:** November 1, 2025
