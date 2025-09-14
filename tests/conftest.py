"""Pytest configuration and fixtures for testing."""

import os
import sys
from pathlib import Path
from typing import Generator, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import redis
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import jwt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app
from src.db.base import Base, get_db
from src.auth.models import User, UserRole, APIKey
from src.auth.service import AuthService
from src.config import settings
from src.cache.redis_cache import CacheManager

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
def auth_service(db_session: Session) -> AuthService:
    """Create an auth service instance for testing."""
    return AuthService(db_session)


@pytest.fixture(scope="function")
def test_user(db_session: Session, auth_service: AuthService) -> User:
    """Create a test user."""
    from src.auth.models import UserCreate
    
    user_data = UserCreate(
        email="test@example.com",
        username="testuser",
        password="Test123!@#",
        full_name="Test User",
        organization="Test Corp"
    )
    
    user = auth_service.create_user(user_data, role=UserRole.VIEWER)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session: Session, auth_service: AuthService) -> User:
    """Create a test admin user."""
    from src.auth.models import UserCreate
    
    user_data = UserCreate(
        email="admin@example.com",
        username="adminuser",
        password="Admin123!@#",
        full_name="Admin User",
        organization="Test Corp"
    )
    
    user = auth_service.create_user(user_data, role=UserRole.ADMIN)
    return user


@pytest.fixture(scope="function")
def analyst_user(db_session: Session, auth_service: AuthService) -> User:
    """Create a test analyst user."""
    from src.auth.models import UserCreate
    
    user_data = UserCreate(
        email="analyst@example.com",
        username="analystuser",
        password="Analyst123!@#",
        full_name="Analyst User",
        organization="Test Corp"
    )
    
    user = auth_service.create_user(user_data, role=UserRole.ANALYST)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User, auth_service: AuthService) -> dict:
    """Create authentication headers for test user."""
    token = auth_service.create_access_token(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_user: User, auth_service: AuthService) -> dict:
    """Create authentication headers for admin user."""
    token = auth_service.create_access_token(admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def api_key(test_user: User, auth_service: AuthService) -> tuple[str, APIKey]:
    """Create a test API key."""
    from src.auth.models import APIKeyCreate, PermissionScope
    
    key_data = APIKeyCreate(
        name="Test API Key",
        scopes=[PermissionScope.READ_COMPANIES, PermissionScope.READ_METRICS],
        expires_in_days=30
    )
    
    response = auth_service.create_api_key(test_user, key_data)
    
    # Get the actual APIKey object
    api_key_obj = auth_service.db.query(APIKey).filter(
        APIKey.id == response.id
    ).first()
    
    return response.key, api_key_obj


@pytest.fixture(scope="function")
def api_key_headers(api_key: tuple[str, APIKey]) -> dict:
    """Create API key headers."""
    key, _ = api_key
    return {"X-API-Key": key}


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client for testing."""
    with patch('redis.Redis') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        
        # Mock common Redis operations
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = 1
        mock_instance.exists.return_value = False
        mock_instance.expire.return_value = True
        mock_instance.ttl.return_value = 3600
        
        yield mock_instance


@pytest.fixture(scope="function")
def mock_cache_manager(mock_redis):
    """Mock cache manager for testing."""
    cache = CacheManager()
    cache.redis_client = mock_redis
    return cache


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


@pytest.fixture(scope="function")
def sample_sec_filing():
    """Sample SEC filing data for testing."""
    return {
        "company_id": "test-company-id",
        "filing_type": "10-K",
        "filing_date": datetime.utcnow().isoformat(),
        "period_end": datetime.utcnow().isoformat(),
        "accession_number": "0001234567890123456",
        "file_number": "001-12345",
        "form_type": "10-K",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/test",
        "content": "Annual report content...",
        "processed": False
    }


@pytest.fixture(scope="function")
def mock_external_apis():
    """Mock external API calls."""
    with patch('src.connectors.data_sources.SECConnector.get_filings') as mock_sec, \
         patch('src.connectors.data_sources.YahooFinanceConnector.get_stock_data') as mock_yahoo, \
         patch('src.connectors.data_sources.AlphaVantageConnector.get_company_overview') as mock_alpha, \
         patch('src.connectors.data_sources.NewsAPIConnector.get_company_news') as mock_news:
        
        # Mock SEC responses
        mock_sec.return_value = [
            {
                "filing_type": "10-K",
                "filing_date": datetime.utcnow().isoformat(),
                "url": "https://sec.gov/test"
            }
        ]
        
        # Mock Yahoo Finance responses
        mock_yahoo.return_value = {
            "price": 150.00,
            "volume": 1000000,
            "market_cap": 5000000000
        }
        
        # Mock Alpha Vantage responses
        mock_alpha.return_value = {
            "revenue": 500000000,
            "net_income": 40000000,
            "pe_ratio": 125.0
        }
        
        # Mock News API responses
        mock_news.return_value = [
            {
                "title": "Test news article",
                "url": "https://news.com/test",
                "published_at": datetime.utcnow().isoformat()
            }
        ]
        
        yield {
            "sec": mock_sec,
            "yahoo": mock_yahoo,
            "alpha": mock_alpha,
            "news": mock_news
        }


@pytest.fixture(scope="function")
def mock_ray():
    """Mock Ray for testing."""
    with patch('ray.init') as mock_init, \
         patch('ray.remote') as mock_remote:
        
        # Mock Ray initialization
        mock_init.return_value = None
        
        # Mock Ray remote decorator
        def remote_decorator(cls):
            return cls
        mock_remote.side_effect = remote_decorator
        
        yield {
            "init": mock_init,
            "remote": mock_remote
        }


@pytest.fixture(scope="function")
def mock_prefect():
    """Mock Prefect for testing."""
    with patch('prefect.flow') as mock_flow, \
         patch('prefect.task') as mock_task:
        
        # Mock Prefect decorators
        def flow_decorator(fn):
            return fn
        def task_decorator(fn):
            return fn
        
        mock_flow.side_effect = flow_decorator
        mock_task.side_effect = task_decorator
        
        yield {
            "flow": mock_flow,
            "task": mock_task
        }


# Test environment settings override
@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for testing."""
    settings.ENVIRONMENT = "testing"
    settings.DEBUG = True
    settings.DATABASE_URL = TEST_DATABASE_URL
    settings.REDIS_URL = "redis://localhost:6379/15"  # Use test database
    settings.CACHE_ENABLED = False  # Disable caching in tests
    settings.RATE_LIMIT_ENABLED = False  # Disable rate limiting in tests
    settings.DATA_QUALITY_ENABLED = False  # Disable data quality checks in tests
    yield
    # Reset after tests if needed