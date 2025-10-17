"""Pytest configuration and fixtures for testing."""

import os
import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, patch
from datetime import datetime
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--real-world",
        action="store_true",
        default=False,
        help="Enable real-world API tests (calls actual APIs, may be slow and incur costs)"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "real_world: mark test as requiring real API calls (slow, may incur costs)"
    )
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )


# Import after path configuration
from src.api.main import app
from src.db.base import Base, get_db
from src.core.config import get_settings

# Get settings instance
settings = get_settings()

# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a clean database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Create a test client with overridden database dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_company_data():
    """Sample company data for testing."""
    return {
        "ticker": "DUOL",
        "name": "Duolingo Inc.",
        "sector": "EdTech",
        "industry": "Language Learning",
        "description": "Language learning platform",
        "website": "https://www.duolingo.com",
        "employees": 800,
        "founded": 2011,
        "headquarters": "Pittsburgh, PA"
    }


@pytest.fixture(scope="function")
def sample_financial_metrics():
    """Sample financial metrics for testing."""
    return {
        "company_id": "test-company-id",
        "date": datetime.utcnow().isoformat(),
        "revenue": 500000000,
        "revenue_growth": 0.45,
        "gross_profit": 350000000,
        "gross_margin": 0.70,
        "operating_income": 50000000,
        "net_income": 40000000,
        "ebitda": 60000000,
        "cash_flow": 55000000,
        "total_assets": 800000000,
        "total_debt": 100000000,
        "market_cap": 5000000000,
        "pe_ratio": 125.0,
        "price_to_sales": 10.0,
        "debt_to_equity": 0.125
    }


# Test environment settings override
@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for testing."""
    settings.ENVIRONMENT = "testing"
    settings.DEBUG = True
    yield


# Async event loop fixture
@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
