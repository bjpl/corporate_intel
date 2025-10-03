"""Pytest fixtures for API endpoint testing."""

import pytest
from typing import Dict, Generator
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, AsyncMock

from src.api.main import app
from src.db.models import Company, SECFiling, FinancialMetric
from src.auth.models import User, UserRole


@pytest.fixture
def api_client(client: TestClient) -> TestClient:
    """FastAPI test client for API endpoints."""
    return client


@pytest.fixture
def sample_company(db_session: Session) -> Company:
    """Create a sample company for testing."""
    company = Company(
        id=uuid4(),
        ticker="DUOL",
        name="Duolingo Inc.",
        cik="0001485945",
        sector="Technology",
        subsector="EdTech",
        category="direct_to_consumer",
        delivery_model="b2c",
        subcategory=["language_learning", "gamification"],
        monetization_strategy=["subscription", "freemium"],
        founded_year=2011,
        headquarters="Pittsburgh, PA",
        website="https://www.duolingo.com",
        employee_count=800,
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_companies(db_session: Session) -> list[Company]:
    """Create multiple sample companies for testing pagination/filtering."""
    companies = [
        Company(
            id=uuid4(),
            ticker="CHGG",
            name="Chegg Inc.",
            cik="0001364954",
            sector="Technology",
            subsector="EdTech",
            category="higher_education",
            delivery_model="b2c",
            founded_year=2005,
        ),
        Company(
            id=uuid4(),
            ticker="2U",
            name="2U Inc.",
            cik="0001459417",
            sector="Technology",
            subsector="EdTech",
            category="higher_education",
            delivery_model="b2b2c",
            founded_year=2008,
        ),
        Company(
            id=uuid4(),
            ticker="STRA",
            name="Strategic Education Inc.",
            cik="0001013934",
            sector="Education",
            subsector="Higher Education",
            category="higher_education",
            delivery_model="hybrid",
            founded_year=1892,
        ),
    ]

    for company in companies:
        db_session.add(company)

    db_session.commit()
    for company in companies:
        db_session.refresh(company)

    return companies


@pytest.fixture
def sample_filing(db_session: Session, sample_company: Company) -> SECFiling:
    """Create a sample SEC filing for testing."""
    filing = SECFiling(
        id=uuid4(),
        company_id=sample_company.id,
        filing_type="10-K",
        filing_date=datetime.utcnow() - timedelta(days=30),
        accession_number="0001485945-23-000001",
        filing_url="https://www.sec.gov/Archives/edgar/data/1485945/000148594523000001/duol-20221231.htm",
        processing_status="pending",
    )
    db_session.add(filing)
    db_session.commit()
    db_session.refresh(filing)
    return filing


@pytest.fixture
def sample_filings(db_session: Session, sample_company: Company) -> list[SECFiling]:
    """Create multiple sample filings for testing."""
    filings = [
        SECFiling(
            id=uuid4(),
            company_id=sample_company.id,
            filing_type="10-K",
            filing_date=datetime.utcnow() - timedelta(days=365),
            accession_number="0001485945-22-000001",
            processing_status="completed",
        ),
        SECFiling(
            id=uuid4(),
            company_id=sample_company.id,
            filing_type="10-Q",
            filing_date=datetime.utcnow() - timedelta(days=90),
            accession_number="0001485945-23-000002",
            processing_status="completed",
        ),
        SECFiling(
            id=uuid4(),
            company_id=sample_company.id,
            filing_type="8-K",
            filing_date=datetime.utcnow() - timedelta(days=15),
            accession_number="0001485945-23-000003",
            processing_status="pending",
        ),
    ]

    for filing in filings:
        db_session.add(filing)

    db_session.commit()
    for filing in filings:
        db_session.refresh(filing)

    return filings


@pytest.fixture
def sample_metrics(db_session: Session, sample_company: Company) -> list[FinancialMetric]:
    """Create sample financial metrics for testing."""
    metrics = [
        FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow() - timedelta(days=90),
            period_type="quarterly",
            metric_type="revenue",
            metric_category="financial",
            value=150000000.0,
            unit="USD",
        ),
        FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow() - timedelta(days=90),
            period_type="quarterly",
            metric_type="revenue_growth_yoy",
            metric_category="growth",
            value=0.45,
            unit="percentage",
        ),
        FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow() - timedelta(days=90),
            period_type="quarterly",
            metric_type="monthly_active_users",
            metric_category="engagement",
            value=50000000.0,
            unit="users",
        ),
    ]

    for metric in metrics:
        db_session.add(metric)

    db_session.commit()
    for metric in metrics:
        db_session.refresh(metric)

    return metrics


@pytest.fixture
def mock_cache():
    """Mock Redis cache for API tests."""
    with patch('src.core.cache.get_cache') as mock:
        cache_mock = AsyncMock()
        cache_mock.get.return_value = None
        cache_mock.set.return_value = True
        cache_mock.delete.return_value = 1
        mock.return_value = cache_mock
        yield cache_mock


@pytest.fixture
def unauthorized_headers() -> Dict[str, str]:
    """Headers without authentication."""
    return {}


@pytest.fixture
def invalid_token_headers() -> Dict[str, str]:
    """Headers with invalid token."""
    return {"Authorization": "Bearer invalid.token.here"}


@pytest.fixture
def expired_token_headers(auth_service) -> Dict[str, str]:
    """Headers with expired token."""
    from src.auth.models import UserCreate

    user_data = UserCreate(
        email="expired@example.com",
        username="expireduser",
        password="Test123!@#",
    )

    # Create token with -1 hour expiry (expired)
    expired_token = auth_service.create_access_token_custom(
        user_data.dict(),
        expires_delta=timedelta(hours=-1)
    )

    return {"Authorization": f"Bearer {expired_token}"}
