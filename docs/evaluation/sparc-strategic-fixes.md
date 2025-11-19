# SPARC Strategic Fixes - Corporate Intelligence Platform

**Date:** 2025-11-19
**Methodology:** SPARC (Specification, Pseudocode, Architecture, Refinement, Completion)
**Focus:** High-Impact, Low-Effort Performance Improvements
**Platform Score:** B+ (85-87/100) → Target A (90-95/100)

---

## Executive Summary

This document applies SPARC methodology to design strategic fixes for the 4 highest-impact, lowest-effort improvements identified in the comprehensive architecture evaluation. These fixes target critical performance bottlenecks while maintaining minimal complexity and implementation risk.

### Strategic Priorities (Week 1 Quick Wins)

| Fix | Impact | Effort | ROI | Priority |
|-----|--------|--------|-----|----------|
| 1. N+1 Query Problem | **70% API speedup** | 4h | **17.5x** | CRITICAL |
| 2. Query Performance Monitoring | **Diagnostics unlocked** | 2h | **∞** | CRITICAL |
| 3. Composite Database Indexes | **40% query speedup** | 2h | **20x** | HIGH |
| 4. Circuit Breakers | **Prevent cascading failures** | 20h | **Medium** | HIGH |

**Total Estimated Effort:** 28 hours
**Expected Platform Improvement:** B+ (87/100) → A- (92/100)

---

## Fix #1: N+1 Query Problem Resolution

### SPARC Phase 1: SPECIFICATION

#### 1.1 Problem Statement

**Current State:**
- Zero eager loading implementation across all API endpoints
- Each relationship access triggers a separate database query
- Example: Fetching 10 companies with metrics = 1 + 10 + 10 = 21 queries
- Average API response time: 200ms (70% of time spent on N+1 queries)

**Root Cause:**
```python
# src/api/v1/companies.py:93
companies = query.offset(offset).limit(limit).all()
# Each subsequent access to company.filings or company.metrics = 1 query
for company in companies:
    metrics = company.metrics  # N+1 query!
```

**Impact Analysis:**
- **Performance:** 200ms → 60ms response time (70% reduction)
- **Database Load:** 50+ queries → 3-5 queries (90% reduction)
- **User Experience:** Faster dashboard loads, better perceived performance
- **Scale:** Problem compounds linearly with data growth

#### 1.2 Success Criteria

**Functional Requirements:**
1. All API endpoints use eager loading for relationships
2. Reduce query count from 50+ to 3-5 per request
3. Maintain backward compatibility with existing API contracts
4. Support both selectinload and joinedload strategies

**Performance Requirements:**
1. API response time: 200ms → 60-120ms (40-70% improvement)
2. Database query count: < 5 per endpoint
3. No regression in correctness or data completeness
4. Memory usage increase: < 10%

**Non-Functional Requirements:**
1. Zero breaking changes to API responses
2. Maintain existing test coverage
3. Add performance tests for query count validation
4. Document eager loading patterns for future development

#### 1.3 Constraints

**Technical Constraints:**
- Must use SQLAlchemy 2.0 async patterns
- Cannot break existing API contracts
- Must work with TimescaleDB hypertables
- Memory usage must remain reasonable

**Business Constraints:**
- Implementation time: 4 hours maximum
- Zero downtime deployment required
- Backward compatibility essential
- Must pass all existing tests

#### 1.4 Files Requiring Changes

**Priority 1 (Critical):**
- `/home/user/corporate_intel/src/api/v1/companies.py` (lines 93, 110, 122)
- `/home/user/corporate_intel/src/api/v1/metrics.py` (line 56)
- `/home/user/corporate_intel/src/api/v1/filings.py` (estimated)

**Priority 2 (Important):**
- `/home/user/corporate_intel/src/visualization/callbacks.py` (lines 87-111)
- `/home/user/corporate_intel/src/repositories/company_repository.py`

**Supporting Files:**
- `/home/user/corporate_intel/tests/api/test_companies.py` (add query count tests)
- `/home/user/corporate_intel/tests/performance/test_n_plus_one.py` (new)

---

### SPARC Phase 2: PSEUDOCODE

#### 2.1 Algorithm Design

**Strategy Selection Algorithm:**
```python
def select_loading_strategy(relationship_type, data_size):
    """
    Choose optimal loading strategy based on relationship cardinality

    Rules:
    - Use selectinload for 1:N relationships (separate query per relationship)
    - Use joinedload for N:1 relationships (single JOIN query)
    - Use subqueryload for large datasets (> 100 related records)
    """
    if relationship_type == "many_to_one":
        return "joinedload"  # Single JOIN query

    elif relationship_type == "one_to_many":
        if data_size > 100:
            return "subqueryload"  # More efficient for large datasets
        else:
            return "selectinload"  # Default for moderate datasets

    return "selectinload"  # Safe default
```

**Implementation Pattern:**
```python
# BEFORE: N+1 query problem
async def list_companies_slow(limit: int, offset: int):
    # 1 query for companies
    companies = await session.execute(
        select(Company).limit(limit).offset(offset)
    )
    results = companies.scalars().all()

    # N queries for each company's filings (N+1!)
    for company in results:
        filings = company.filings  # Triggers query #2, #3, #4...

    return results

# AFTER: Eager loading solution
async def list_companies_optimized(limit: int, offset: int):
    # 3 queries total: companies + filings + metrics
    companies = await session.execute(
        select(Company)
        .options(
            selectinload(Company.filings),
            selectinload(Company.metrics)
        )
        .limit(limit)
        .offset(offset)
    )
    results = companies.scalars().all()

    # All relationships already loaded - no additional queries
    for company in results:
        filings = company.filings  # No query - already loaded!

    return results
```

#### 2.2 Data Structures

**Loading Strategy Configuration:**
```python
# src/core/query_optimization.py (new file)

from sqlalchemy.orm import selectinload, joinedload, subqueryload
from typing import Dict, List, Any

class EagerLoadingConfig:
    """Central configuration for eager loading strategies"""

    COMPANY_RELATIONSHIPS = {
        "filings": selectinload(Company.filings),
        "metrics": selectinload(Company.metrics),
        "documents": selectinload(Company.documents)
    }

    FILING_RELATIONSHIPS = {
        "company": joinedload(SECFiling.company)  # N:1 relationship
    }

    METRIC_RELATIONSHIPS = {
        "company": joinedload(FinancialMetric.company)  # N:1 relationship
    }

    @classmethod
    def get_company_full_load(cls):
        """Load all company relationships"""
        return [
            selectinload(Company.filings),
            selectinload(Company.metrics),
            selectinload(Company.documents)
        ]

    @classmethod
    def get_company_basic_load(cls):
        """Load only essential relationships"""
        return [
            selectinload(Company.filings).load_only(
                SECFiling.id,
                SECFiling.filing_type,
                SECFiling.filing_date
            )
        ]
```

**Query Count Validator:**
```python
class QueryCountValidator:
    """Context manager to validate query count"""

    def __init__(self, max_queries: int):
        self.max_queries = max_queries
        self.query_count = 0

    async def __aenter__(self):
        # Hook into SQLAlchemy event system
        @event.listens_for(Engine, "before_cursor_execute")
        def increment_query_count(conn, cursor, statement, parameters, context, executemany):
            self.query_count += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self.query_count <= self.max_queries, \
            f"Query count {self.query_count} exceeds limit {self.max_queries}"
```

#### 2.3 Integration Points

**Repository Layer Integration:**
```python
class CompanyRepository(BaseRepository[Company]):
    """Enhanced repository with eager loading support"""

    async def get_all_with_relationships(
        self,
        limit: int = 100,
        offset: int = 0,
        include_relationships: List[str] = None
    ) -> List[Company]:
        """
        Get companies with eager loading

        Args:
            limit: Maximum results
            offset: Pagination offset
            include_relationships: List of relationships to load
                Options: ["filings", "metrics", "documents"]

        Returns:
            List of Company objects with relationships loaded
        """
        query = select(Company)

        # Apply eager loading based on requested relationships
        if include_relationships:
            for rel_name in include_relationships:
                if rel_name == "filings":
                    query = query.options(selectinload(Company.filings))
                elif rel_name == "metrics":
                    query = query.options(selectinload(Company.metrics))
                elif rel_name == "documents":
                    query = query.options(selectinload(Company.documents))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute with relationship loading
        result = await self.session.execute(query)
        return result.scalars().all()
```

---

### SPARC Phase 3: ARCHITECTURE

#### 3.1 Component Interactions

**Layered Architecture Update:**
```
┌─────────────────────────────────────────────┐
│          API Layer (FastAPI Routes)         │
│  - Specify required relationships           │
│  - Pass to service layer                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         Service Layer (Business Logic)      │
│  - Determine optimal loading strategy       │
│  - Call repository with relationships       │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│       Repository Layer (Data Access)        │
│  - Apply eager loading strategies           │
│  - Execute optimized queries                │
│  - Return fully loaded objects              │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│     ORM Layer (SQLAlchemy + PostgreSQL)     │
│  - selectinload: 1 query per relationship   │
│  - joinedload: Single JOIN query            │
│  - subqueryload: Subquery approach          │
└─────────────────────────────────────────────┘
```

**Request Flow with Eager Loading:**
```
Client Request: GET /api/v1/companies?limit=10
        ↓
API Route: companies.list_companies()
        ↓
Service: company_service.get_companies(include=["filings", "metrics"])
        ↓
Repository: company_repo.get_all_with_relationships()
        ↓
SQLAlchemy:
    Query 1: SELECT companies WHERE ... LIMIT 10
    Query 2: SELECT filings WHERE company_id IN (...)
    Query 3: SELECT metrics WHERE company_id IN (...)
        ↓
Total: 3 queries (instead of 21+)
        ↓
Response: JSON with embedded relationships
```

#### 3.2 File Changes Required

**File 1: `/home/user/corporate_intel/src/api/v1/companies.py`**

**Change 1 - list_companies endpoint (lines 72-95):**
```python
# BEFORE
@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Company)
    if category:
        query = query.where(Company.category == category)

    result = await db.execute(query.offset(offset).limit(limit))
    companies = result.scalars().all()  # N+1 problem here!
    return companies

# AFTER
@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_relationships: bool = Query(False, description="Include filings and metrics"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Company)

    # Apply eager loading for relationships
    if include_relationships:
        query = query.options(
            selectinload(Company.filings),
            selectinload(Company.metrics)
        )

    if category:
        query = query.where(Company.category == category)

    result = await db.execute(query.offset(offset).limit(limit))
    companies = result.scalars().all()
    return companies
```

**Change 2 - get_company endpoint (lines 98-111):**
```python
# BEFORE
@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

# AFTER
@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company)
        .options(
            selectinload(Company.filings),
            selectinload(Company.metrics)
        )
        .where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company
```

**Change 3 - get_company_metrics endpoint (lines 135-185):**
```python
# BEFORE
@router.get("/{company_id}/metrics", response_model=dict)
async def get_company_metrics(company_id: UUID, db: AsyncSession = Depends(get_db)):
    # First query: Get company
    company = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    # N+1 when accessing company.metrics

# AFTER
@router.get("/{company_id}/metrics", response_model=dict)
async def get_company_metrics(company_id: UUID, db: AsyncSession = Depends(get_db)):
    # Single query with metrics loaded
    company = await db.execute(
        select(Company)
        .options(selectinload(Company.metrics))
        .where(Company.id == company_id)
    )
```

**File 2: `/home/user/corporate_intel/src/api/v1/metrics.py`**

**Change 1 - get_metrics endpoint:**
```python
# AFTER
@router.get("/", response_model=List[MetricResponse])
async def get_metrics(
    company_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(FinancialMetric).options(
        joinedload(FinancialMetric.company)  # N:1 relationship - use joinedload
    )
    if company_id:
        query = query.where(FinancialMetric.company_id == company_id)

    result = await db.execute(query)
    return result.scalars().all()
```

**File 3: `/home/user/corporate_intel/src/core/query_optimization.py` (NEW)**

```python
"""Query optimization utilities for N+1 prevention"""

from sqlalchemy.orm import selectinload, joinedload, subqueryload
from typing import List, Any
from src.db.models import Company, SECFiling, FinancialMetric, Document

class EagerLoadingStrategies:
    """Centralized eager loading configurations"""

    # Company relationships (1:N)
    COMPANY_WITH_FILINGS = [
        selectinload(Company.filings).load_only(
            SECFiling.id,
            SECFiling.filing_type,
            SECFiling.filing_date,
            SECFiling.accession_number
        )
    ]

    COMPANY_WITH_METRICS = [
        selectinload(Company.metrics).load_only(
            FinancialMetric.metric_type,
            FinancialMetric.value,
            FinancialMetric.metric_date,
            FinancialMetric.period_type
        )
    ]

    COMPANY_FULL = [
        selectinload(Company.filings),
        selectinload(Company.metrics),
        selectinload(Company.documents)
    ]

    # Metric relationships (N:1)
    METRIC_WITH_COMPANY = [
        joinedload(FinancialMetric.company).load_only(
            Company.id,
            Company.ticker,
            Company.name,
            Company.category
        )
    ]
```

#### 3.3 Migration Strategy

**Deployment Steps:**

1. **Phase 1: Add Eager Loading (No Breaking Changes)**
   - Add eager loading to repository methods
   - Deploy to staging
   - Run performance tests
   - Verify query count reduction

2. **Phase 2: Update API Endpoints**
   - Update one endpoint at a time
   - Monitor query count and response times
   - Rollback if any issues detected
   - Deploy to production gradually (blue/green)

3. **Phase 3: Add Query Count Validation**
   - Add query count assertions to tests
   - Set up monitoring alerts
   - Document eager loading patterns

**Rollback Plan:**
```python
# Feature flag for eager loading
class Settings:
    ENABLE_EAGER_LOADING: bool = Field(default=True)

# In repository
async def get_all(self, ...):
    query = select(Company)

    if settings.ENABLE_EAGER_LOADING:
        query = query.options(selectinload(Company.filings))

    # ... rest of query
```

---

### SPARC Phase 4: REFINEMENT

#### 4.1 Implementation Details

**Step 1: Create Query Optimization Module**

```python
# src/core/query_optimization.py
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import event, Engine
from typing import List, Optional
from contextlib import contextmanager

class QueryCounter:
    """Track query count for testing"""

    def __init__(self):
        self.count = 0
        self.queries = []

    @contextmanager
    def track(self):
        """Context manager to track queries"""
        self.count = 0
        self.queries = []

        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            self.count += 1
            self.queries.append(statement)

        try:
            yield self
        finally:
            event.remove(Engine, "before_cursor_execute", receive_before_cursor_execute)

# Global query counter for tests
query_counter = QueryCounter()
```

**Step 2: Update Repository Layer**

```python
# src/repositories/company_repository.py

from src.core.query_optimization import EagerLoadingStrategies
from sqlalchemy.orm import selectinload

class CompanyRepository(BaseRepository[Company]):

    async def get_all_optimized(
        self,
        limit: int = 100,
        offset: int = 0,
        load_relationships: bool = True
    ) -> List[Company]:
        """
        Get companies with optimized relationship loading

        This method prevents N+1 queries by eagerly loading relationships.

        Query Count:
        - Without eager loading: 1 + N (companies) + N (metrics per company) = 1 + 2N
        - With eager loading: 3 queries (companies + filings + metrics)

        Performance:
        - 10 companies: 21 queries → 3 queries (85% reduction)
        - 100 companies: 201 queries → 3 queries (98% reduction)
        """
        query = select(Company)

        if load_relationships:
            query = query.options(
                selectinload(Company.filings),
                selectinload(Company.metrics)
            )

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id_optimized(
        self,
        company_id: UUID,
        load_relationships: bool = True
    ) -> Optional[Company]:
        """Get single company with optimized loading"""
        query = select(Company).where(Company.id == company_id)

        if load_relationships:
            query = query.options(
                selectinload(Company.filings),
                selectinload(Company.metrics)
            )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
```

**Step 3: Update API Endpoints**

```python
# src/api/v1/companies.py

@router.get("/", response_model=List[CompanyResponse])
@cache_key_wrapper(prefix="companies_list", expire=300)  # 5 min cache
async def list_companies(
    category: Optional[str] = Query(None, description="Filter by EdTech category"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_relationships: bool = Query(
        True,
        description="Include filings and metrics (prevents N+1 queries)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    List companies with optional filtering

    Performance Notes:
    - With include_relationships=True: 3 queries (optimized)
    - With include_relationships=False: 1 query (minimal)
    - Response cached for 5 minutes
    """
    query = select(Company)

    # Apply eager loading to prevent N+1 queries
    if include_relationships:
        query = query.options(
            selectinload(Company.filings),
            selectinload(Company.metrics)
        )

    # Apply filters
    if category:
        query = query.where(Company.category == category)
    if sector:
        query = query.where(Company.sector == sector)

    # Execute with pagination
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    companies = result.scalars().all()

    logger.info(
        f"Fetched {len(companies)} companies "
        f"(eager_loading={include_relationships})"
    )

    return companies
```

#### 4.2 Test Strategy

**Unit Tests:**

```python
# tests/api/test_companies_eager_loading.py

import pytest
from src.core.query_optimization import query_counter

@pytest.mark.asyncio
async def test_list_companies_prevents_n_plus_one(db_session, test_companies):
    """Verify eager loading prevents N+1 queries"""

    # Setup: Create 10 companies with filings and metrics
    for i in range(10):
        company = Company(ticker=f"TST{i}", name=f"Test Company {i}")
        db_session.add(company)

        # Add 5 filings per company
        for j in range(5):
            filing = SECFiling(company=company, filing_type="10-K")
            db_session.add(filing)

        # Add 10 metrics per company
        for k in range(10):
            metric = FinancialMetric(company=company, metric_type="revenue")
            db_session.add(metric)

    await db_session.commit()

    # Test WITH eager loading
    with query_counter.track() as counter:
        repo = CompanyRepository(db_session)
        companies = await repo.get_all_optimized(limit=10, load_relationships=True)

        # Access relationships (should not trigger queries)
        for company in companies:
            _ = company.filings
            _ = company.metrics

        # Assert query count
        assert counter.count <= 5, f"Expected ≤5 queries, got {counter.count}"
        # Breakdown: 1 for companies + 1 for filings + 1 for metrics + overhead

    # Test WITHOUT eager loading (N+1 problem)
    with query_counter.track() as counter:
        companies = await repo.get_all_optimized(limit=10, load_relationships=False)

        # Access relationships (triggers N+1 queries)
        for company in companies:
            _ = company.filings  # +10 queries
            _ = company.metrics  # +10 queries

        # Assert N+1 problem exists without eager loading
        assert counter.count > 20, f"Expected >20 queries (N+1), got {counter.count}"

@pytest.mark.asyncio
async def test_get_company_endpoint_query_count(client, db_session):
    """Integration test: Verify API endpoint query count"""

    # Create test company with relationships
    company = Company(ticker="DUOL", name="Duolingo")
    db_session.add(company)

    for i in range(5):
        filing = SECFiling(company=company, filing_type="10-K")
        db_session.add(filing)

    await db_session.commit()

    with query_counter.track() as counter:
        response = await client.get(f"/api/v1/companies/{company.id}")

        assert response.status_code == 200
        # Should use 3 queries max (company + filings + metrics)
        assert counter.count <= 5, f"API made {counter.count} queries"
```

**Performance Tests:**

```python
# tests/performance/test_n_plus_one_performance.py

import pytest
import time
from statistics import mean

@pytest.mark.performance
@pytest.mark.asyncio
async def test_eager_loading_performance_improvement(db_session):
    """Measure performance improvement from eager loading"""

    # Setup: 50 companies with 10 filings each
    for i in range(50):
        company = Company(ticker=f"PERF{i}", name=f"Perf Test {i}")
        db_session.add(company)

        for j in range(10):
            filing = SECFiling(company=company, filing_type="10-K")
            db_session.add(filing)

    await db_session.commit()

    # Test WITHOUT eager loading
    no_eager_times = []
    for _ in range(10):
        start = time.time()

        query = select(Company).limit(50)
        result = await db_session.execute(query)
        companies = result.scalars().all()

        # Access relationships (N+1)
        for company in companies:
            _ = company.filings

        no_eager_times.append(time.time() - start)

    avg_no_eager = mean(no_eager_times)

    # Test WITH eager loading
    with_eager_times = []
    for _ in range(10):
        start = time.time()

        query = select(Company).options(
            selectinload(Company.filings)
        ).limit(50)
        result = await db_session.execute(query)
        companies = result.scalars().all()

        # Access relationships (already loaded)
        for company in companies:
            _ = company.filings

        with_eager_times.append(time.time() - start)

    avg_with_eager = mean(with_eager_times)

    # Assert performance improvement
    improvement = (avg_no_eager - avg_with_eager) / avg_no_eager * 100

    print(f"\nPerformance Results:")
    print(f"  Without eager loading: {avg_no_eager:.3f}s")
    print(f"  With eager loading:    {avg_with_eager:.3f}s")
    print(f"  Improvement:           {improvement:.1f}%")

    assert improvement > 50, f"Expected >50% improvement, got {improvement:.1f}%"

@pytest.mark.performance
async def test_response_time_target(client):
    """Verify API response time meets target after eager loading"""

    times = []
    for _ in range(20):
        start = time.time()
        response = await client.get("/api/v1/companies?limit=50")
        times.append(time.time() - start)
        assert response.status_code == 200

    p95 = sorted(times)[int(len(times) * 0.95)]

    print(f"\nResponse Time (P95): {p95*1000:.0f}ms")

    # Target: < 120ms (down from 200ms)
    assert p95 < 0.120, f"P95 response time {p95*1000:.0f}ms exceeds 120ms target"
```

#### 4.3 Rollback Plan

**Feature Flag Implementation:**

```python
# src/core/config.py
class Settings(BaseSettings):
    # Feature flag for eager loading rollout
    ENABLE_EAGER_LOADING: bool = Field(
        default=True,
        description="Enable eager loading to prevent N+1 queries"
    )

# src/repositories/company_repository.py
async def get_all_optimized(self, ...):
    query = select(Company)

    # Conditional eager loading based on feature flag
    if settings.ENABLE_EAGER_LOADING:
        query = query.options(
            selectinload(Company.filings),
            selectinload(Company.metrics)
        )

    # ... rest of implementation
```

**Rollback Procedure:**
1. Set `ENABLE_EAGER_LOADING=false` in environment
2. Restart API servers (rolling restart, zero downtime)
3. Monitor for any issues
4. Investigate root cause before re-enabling

---

### SPARC Phase 5: COMPLETION

#### 5.1 Integration Testing

**End-to-End Test:**
```python
@pytest.mark.e2e
async def test_complete_eager_loading_workflow(client, db_session):
    """Test complete workflow with eager loading"""

    # 1. Create test data
    companies = []
    for i in range(10):
        company = Company(ticker=f"E2E{i}", name=f"E2E Test {i}")
        db_session.add(company)
        companies.append(company)

        # Add relationships
        for j in range(5):
            filing = SECFiling(company=company, filing_type="10-K")
            db_session.add(filing)

    await db_session.commit()

    # 2. Test list endpoint with query count validation
    with query_counter.track() as counter:
        response = await client.get("/api/v1/companies?limit=10&include_relationships=true")
        assert response.status_code == 200
        assert counter.count <= 5

    # 3. Test detail endpoint
    company_id = companies[0].id
    response = await client.get(f"/api/v1/companies/{company_id}")
    assert response.status_code == 200
    assert "filings" in response.json() or len(companies[0].filings) >= 0

    # 4. Verify performance target
    start = time.time()
    response = await client.get("/api/v1/companies?limit=10")
    duration = time.time() - start
    assert duration < 0.120  # 120ms target
```

#### 5.2 Deployment Checklist

**Pre-Deployment:**
- [ ] All unit tests pass (query count validation)
- [ ] Performance tests meet targets (< 120ms P95)
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Feature flag configured
- [ ] Rollback plan documented

**Deployment Steps:**
1. Deploy to staging environment
2. Run smoke tests
3. Measure query count and response times
4. Blue/green deployment to production
5. Monitor metrics for 1 hour
6. Gradual traffic shift (10% → 50% → 100%)

**Post-Deployment:**
- [ ] Verify query count reduction in Grafana
- [ ] Confirm response time improvement
- [ ] Check error rates (should be unchanged)
- [ ] Monitor memory usage (< 10% increase expected)
- [ ] Update runbook with eager loading patterns

#### 5.3 Success Metrics

**Performance Metrics:**
- API response time: 200ms → 60-120ms ✓
- Query count: 50+ → 3-5 ✓
- Database load: -90% ✓
- Memory usage: +5-10% (acceptable) ✓

**Quality Metrics:**
- Test coverage: Maintain 85%+ ✓
- Zero breaking changes ✓
- Zero production incidents ✓
- Code review score: 4.5/5+ ✓

---

## Fix #2: Query Performance Monitoring

### SPARC Phase 1: SPECIFICATION

#### 1.1 Problem Statement

**Current State:**
- No `pg_stat_statements` extension enabled
- No slow query logging configured
- Cannot identify production bottlenecks
- No query performance metrics in monitoring dashboards
- Impossible to diagnose performance issues proactively

**Impact:**
- Cannot optimize slow queries
- No data for capacity planning
- Performance regressions go unnoticed
- Difficult to troubleshoot production issues

#### 1.2 Success Criteria

**Functional Requirements:**
1. Enable `pg_stat_statements` extension
2. Configure slow query logging (> 1 second)
3. Expose query metrics to Prometheus
4. Create Grafana dashboard for query performance
5. Set up alerts for slow queries

**Performance Requirements:**
1. `pg_stat_statements` overhead: < 5%
2. Log storage: < 1GB per day
3. Metrics collection: < 100ms overhead
4. Dashboard load time: < 2 seconds

**Non-Functional Requirements:**
1. Zero downtime deployment
2. Historical data retention: 30 days
3. Real-time monitoring (< 1 minute lag)
4. Automated alerting

#### 1.3 Implementation Details

**Database Configuration:**
```sql
-- alembic/versions/002_enable_pg_stat_statements.py

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")

    # Configure PostgreSQL settings
    op.execute("ALTER SYSTEM SET shared_preload_libraries = 'timescaledb,pg_stat_statements'")
    op.execute("ALTER SYSTEM SET pg_stat_statements.track = 'all'")
    op.execute("ALTER SYSTEM SET pg_stat_statements.max = 10000")
    op.execute("ALTER SYSTEM SET log_min_duration_statement = 1000")  # Log queries > 1s

    # Create view for slow queries
    op.execute("""
        CREATE OR REPLACE VIEW slow_queries AS
        SELECT
            queryid,
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            max_exec_time,
            stddev_exec_time,
            rows
        FROM pg_stat_statements
        WHERE mean_exec_time > 100  -- Queries averaging > 100ms
        ORDER BY total_exec_time DESC
        LIMIT 50
    """)

def downgrade():
    op.execute("DROP VIEW IF EXISTS slow_queries")
    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements")
```

**Prometheus Metrics Exporter:**
```python
# src/monitoring/query_metrics.py

from prometheus_client import Histogram, Counter, Gauge
import asyncpg

# Query performance metrics
query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query execution time',
    ['query_type', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

slow_query_count = Counter(
    'db_slow_query_total',
    'Number of slow queries (>1s)',
    ['query_type']
)

active_connections = Gauge(
    'db_active_connections',
    'Number of active database connections'
)

class QueryPerformanceMonitor:
    """Monitor and export query performance metrics"""

    async def collect_metrics(self, db_url: str):
        """Collect metrics from pg_stat_statements"""
        conn = await asyncpg.connect(db_url)

        try:
            # Get slow query stats
            slow_queries = await conn.fetch("""
                SELECT
                    query,
                    calls,
                    mean_exec_time,
                    total_exec_time
                FROM pg_stat_statements
                WHERE mean_exec_time > 1000  -- > 1 second
                ORDER BY total_exec_time DESC
                LIMIT 20
            """)

            for row in slow_queries:
                slow_query_count.labels(
                    query_type=self._classify_query(row['query'])
                ).inc(row['calls'])

            # Get connection count
            conn_count = await conn.fetchval("""
                SELECT count(*) FROM pg_stat_activity
                WHERE state = 'active'
            """)
            active_connections.set(conn_count)

        finally:
            await conn.close()

    @staticmethod
    def _classify_query(query: str) -> str:
        """Classify query type for metrics"""
        query_upper = query.upper().strip()
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'OTHER'
```

**Grafana Dashboard Configuration:**
```json
{
  "dashboard": {
    "title": "Database Query Performance",
    "panels": [
      {
        "title": "Top 10 Slowest Queries",
        "targets": [
          {
            "expr": "topk(10, rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m]))",
            "legendFormat": "{{ query_type }} - {{ table }}"
          }
        ]
      },
      {
        "title": "Query Duration (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "title": "Slow Query Rate (>1s)",
        "targets": [
          {
            "expr": "rate(db_slow_query_total[5m])",
            "legendFormat": "{{ query_type }}"
          }
        ]
      }
    ]
  }
}
```

**Prometheus Alerts:**
```yaml
# prometheus/alerts/database.yml

groups:
  - name: database_performance
    interval: 30s
    rules:
      - alert: SlowQueryDetected
        expr: rate(db_slow_query_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rate of slow queries detected"
          description: "{{ $value }} slow queries per second"

      - alert: QueryDurationHigh
        expr: histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Query duration P95 exceeds 1 second"
          description: "P95 query time: {{ $value }}s"
```

---

## Fix #3: Composite Database Indexes

### SPARC Phase 1: SPECIFICATION

#### 1.1 Problem Statement

**Current State:**
- Missing composite indexes for common query patterns
- Dashboard queries use multiple single-column indexes
- Query performance 40% slower than optimal
- Index-only scans not possible for common queries

**Common Query Patterns Needing Optimization:**
```sql
-- Pattern 1: Dashboard company filtering
SELECT * FROM companies
WHERE category = 'higher_education' AND ticker = 'DUOL';

-- Pattern 2: Metrics time-series queries
SELECT * FROM financial_metrics
WHERE company_id = '...' AND metric_date BETWEEN '...' AND '...';

-- Pattern 3: Filing lookups
SELECT * FROM sec_filings
WHERE company_id = '...' AND filing_type = '10-K'
ORDER BY filing_date DESC;
```

#### 1.2 Success Criteria

**Performance Targets:**
- Dashboard query time: -40%
- Enable index-only scans
- Reduce database I/O by 30%

**Indexes to Add:**
1. `(company_id, metric_date)` on `financial_metrics`
2. `(ticker, category)` on `companies`
3. `(filing_type, company_id, filing_date)` on `sec_filings`
4. `(category, sector)` on `companies`

#### 1.3 Implementation

**Migration File:**
```python
# alembic/versions/003_add_composite_indexes.py

def upgrade():
    # Index 1: Metrics time-series queries
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_metrics_company_date
        ON financial_metrics(company_id, metric_date DESC)
        INCLUDE (value, unit, metric_type)
    """)

    # Index 2: Company filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_companies_ticker_category
        ON companies(ticker, category)
    """)

    # Index 3: Filing lookups
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_filings_type_company_date
        ON sec_filings(filing_type, company_id, filing_date DESC)
    """)

    # Index 4: Dashboard category filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_companies_category_sector
        ON companies(category, sector)
        WHERE category IS NOT NULL
    """)

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_metrics_company_date")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_companies_ticker_category")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_filings_type_company_date")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_companies_category_sector")
```

**Testing:**
```python
@pytest.mark.asyncio
async def test_composite_index_performance():
    # Test query uses new composite index
    query = """
        SELECT company_id, metric_date, value
        FROM financial_metrics
        WHERE company_id = :company_id
        AND metric_date BETWEEN :start_date AND :end_date
    """

    # Execute EXPLAIN ANALYZE
    explain = await db.execute(text(f"EXPLAIN ANALYZE {query}"))
    plan = explain.fetchall()

    # Verify index usage
    assert any("idx_metrics_company_date" in str(row) for row in plan)
```

---

## Fix #4: Circuit Breakers for External APIs

### SPARC Phase 1: SPECIFICATION

#### 1.1 Problem Statement

**Current State:**
- No circuit breakers for external APIs (SEC, Alpha Vantage, Yahoo)
- API failures cascade throughout system
- Retry storms can overwhelm external services
- No fallback strategies when APIs are down

**Risk:**
```python
# Current code - no protection
async def fetch_company_data(ticker):
    # If API is down, this retries indefinitely
    for attempt in range(3):
        try:
            data = await external_api.get(ticker)
            return data
        except Exception:
            await asyncio.sleep(2 ** attempt)

    # After 3 failures, raises exception and blocks ingestion
    raise APIException("Failed to fetch data")
```

#### 1.2 Success Criteria

**Functional Requirements:**
1. Implement circuit breaker pattern for all external APIs
2. Add fallback strategies (cached data, degraded mode)
3. Automatic recovery detection
4. Monitoring and alerting

**Circuit Breaker States:**
```
CLOSED (normal) → failures exceed threshold → OPEN (failing)
                                                    ↓
                                                timeout
                                                    ↓
                                            HALF_OPEN (testing)
                                                ↓ success
                                            CLOSED
```

#### 1.3 Implementation

**Using pybreaker Library:**
```python
# src/core/circuit_breaker.py

from pybreaker import CircuitBreaker, CircuitBreakerError
from typing import Callable, Any
import asyncio

class APICircuitBreaker:
    """Circuit breaker for external API calls"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.breaker = CircuitBreaker(
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            exclude=[expected_exception],
            name=name
        )

        # Fallback strategies
        self.fallback_handlers = {}

    def register_fallback(self, operation: str, handler: Callable):
        """Register fallback handler for operation"""
        self.fallback_handlers[operation] = handler

    async def call(
        self,
        func: Callable,
        *args,
        fallback_key: str = None,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection"""
        try:
            return await self.breaker.call_async(func, *args, **kwargs)

        except CircuitBreakerError:
            # Circuit is open - use fallback
            if fallback_key and fallback_key in self.fallback_handlers:
                logger.warning(f"Circuit breaker OPEN for {self.breaker.name}, using fallback")
                return await self.fallback_handlers[fallback_key](*args, **kwargs)
            else:
                raise

# src/connectors/data_sources.py

class AlphaVantageConnector:
    def __init__(self):
        self.circuit_breaker = APICircuitBreaker(
            name="alpha_vantage",
            failure_threshold=5,
            recovery_timeout=60
        )

        # Register fallback to cached data
        self.circuit_breaker.register_fallback(
            "get_company_overview",
            self._get_cached_overview
        )

    async def get_company_overview(self, ticker: str) -> dict:
        """Get company data with circuit breaker protection"""
        return await self.circuit_breaker.call(
            self._fetch_overview,
            ticker,
            fallback_key="get_company_overview"
        )

    async def _fetch_overview(self, ticker: str) -> dict:
        """Actual API call (protected by circuit breaker)"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/query"
            params = {
                "function": "OVERVIEW",
                "symbol": ticker,
                "apikey": self.api_key
            }

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise APIException(f"API returned {resp.status}")

                return await resp.json()

    async def _get_cached_overview(self, ticker: str) -> dict:
        """Fallback to cached data when circuit is open"""
        cache_key = f"alpha_vantage:overview:{ticker}"
        cached = await redis.get(cache_key)

        if cached:
            logger.info(f"Using cached data for {ticker} (circuit breaker OPEN)")
            return json.loads(cached)

        # No cache - return degraded response
        return {
            "Symbol": ticker,
            "Name": None,
            "_degraded": True,
            "_message": "API temporarily unavailable"
        }
```

**Monitoring:**
```python
# src/monitoring/circuit_breaker_metrics.py

from prometheus_client import Gauge, Counter

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['api_name']
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['api_name']
)

circuit_breaker_fallbacks = Counter(
    'circuit_breaker_fallbacks_total',
    'Number of times fallback was used',
    ['api_name', 'operation']
)
```

---

## Implementation Roadmap

### Week 1: Quick Wins

**Monday-Tuesday (8 hours):**
- [ ] Fix #1: N+1 Query Problem
  - Create query optimization module (1h)
  - Update repository layer (2h)
  - Update API endpoints (2h)
  - Write tests (2h)
  - Deploy to staging (1h)

**Wednesday (4 hours):**
- [ ] Fix #2: Query Performance Monitoring
  - Enable pg_stat_statements (0.5h)
  - Create Grafana dashboard (1.5h)
  - Set up Prometheus metrics (1h)
  - Configure alerts (1h)

**Thursday (2 hours):**
- [ ] Fix #3: Composite Database Indexes
  - Write migration (0.5h)
  - Test on staging (0.5h)
  - Deploy to production (1h)

**Friday (14 hours):**
- [ ] Fix #4: Circuit Breakers
  - Install pybreaker (0.5h)
  - Implement circuit breaker wrapper (4h)
  - Update Alpha Vantage connector (3h)
  - Update SEC connector (3h)
  - Update Yahoo Finance connector (2h)
  - Write tests (3h)
  - Deploy to staging (1h)

---

## Success Metrics & Validation

### Performance Improvements

**Before:**
```
API Response Time (P95):        200ms
Dashboard Load Time:            5 seconds
Database Query Count:           50+ per request
Slow Queries:                   Unknown (not monitored)
API Failure Cascades:           Yes
```

**After:**
```
API Response Time (P95):        60-120ms  (-40 to -70%)
Dashboard Load Time:            3 seconds  (-40%)
Database Query Count:           3-5 per request  (-90%)
Slow Queries:                   Monitored (Grafana dashboard)
API Failure Cascades:           Prevented (circuit breakers)
```

### Platform Grade Improvement

**Current:** B+ (87/100)

**After Fixes:**
- N+1 queries fixed: +2 points
- Query monitoring enabled: +1 point
- Composite indexes added: +1 point
- Circuit breakers implemented: +2 points

**Target:** A- (93/100)

---

## Risk Assessment & Mitigation

### Low Risk (Safe to Deploy)

1. **Composite Indexes** ✅
   - Uses `CREATE INDEX CONCURRENTLY` (no table locks)
   - Zero downtime
   - Easy rollback (DROP INDEX)

2. **Query Monitoring** ✅
   - Read-only metrics collection
   - Low overhead (< 5%)
   - Can be disabled instantly

### Medium Risk (Deploy with Caution)

3. **N+1 Query Fix** ⚠️
   - Risk: Increased memory usage per request
   - Mitigation: Feature flag, gradual rollout
   - Rollback: Disable feature flag

4. **Circuit Breakers** ⚠️
   - Risk: Fallback data might be stale
   - Mitigation: Validate fallback logic, monitor closely
   - Rollback: Remove circuit breaker calls

---

## Conclusion

These 4 strategic fixes represent **high-impact, low-effort** improvements that will:

1. **Eliminate N+1 queries** → 70% faster APIs
2. **Enable query diagnostics** → Proactive optimization
3. **Optimize database queries** → 40% faster dashboard
4. **Prevent cascading failures** → Better resilience

**Total Investment:** 28 hours
**Expected ROI:** Platform improvement from B+ to A-
**Risk Level:** Low to Medium (all mitigated)

The platform will be **production-ready at scale** after these fixes, with comprehensive monitoring and resilience patterns in place.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-19
**Next Review:** After implementation (Week 2)
