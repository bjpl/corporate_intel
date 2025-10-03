"""Integration test fixtures and database setup."""

import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.db.models import Base, Company, SECFiling, FinancialMetric

# Test database configuration
TEST_DB_NAME = "corporate_intel_test"
settings = get_settings()

# Build test database URLs
TEST_DB_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{TEST_DB_NAME}"
TEST_DB_SYNC_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{TEST_DB_NAME}"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_test_database():
    """Create test database and tables."""
    # Connect to default postgres database to create test database
    admin_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        # Drop existing test database if exists
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))

        # Create test database
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))

    engine.dispose()

    # Create test database engine
    test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)

    async with test_engine.begin() as conn:
        # Enable required extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Convert financial_metrics to hypertable
        await conn.execute(text("""
            SELECT create_hypertable(
                'financial_metrics',
                'metric_date',
                if_not_exists => TRUE
            )
        """))

    yield test_engine

    # Cleanup
    await test_engine.dispose()

    # Drop test database
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test."""
    async_session = async_sessionmaker(
        setup_test_database,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def db_session_factory(setup_test_database):
    """Provide session factory for pipeline functions."""
    async_session = async_sessionmaker(
        setup_test_database,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        "ticker": "DUOL",
        "name": "Duolingo Inc.",
        "cik": "1835631",
        "sector": "Technology",
        "subsector": "Educational Software",
        "category": "direct_to_consumer",
        "subcategory": ["language_learning", "mobile_first"],
        "delivery_model": "B2C",
        "monetization_strategy": ["freemium", "subscription"],
        "founded_year": 2011,
        "headquarters": "Pittsburgh, PA",
        "website": "https://www.duolingo.com",
        "employee_count": 800,
    }


@pytest.fixture
def sample_sec_filing_data():
    """Sample SEC filing data for testing."""
    return {
        "form": "10-K",
        "filingDate": "2024-03-15",
        "accessionNumber": "0001835631-24-000012",
        "primaryDocument": "duol-20231231.htm",
        "cik": "1835631",
        "content": """
        <SEC-DOCUMENT>
        ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934

        For the fiscal year ended December 31, 2023

        DUOLINGO, INC.

        Item 1. Business

        Duolingo is a leading technology platform for language learning. Founded in 2011,
        the Company has grown to over 80 million monthly active users across 40+ languages.

        Item 8. Financial Statements and Supplementary Data

        Revenue for fiscal year 2023 was $531.4 million, representing 44% growth year-over-year.
        Subscription revenue was $441.6 million, up 51% from prior year.
        Monthly Active Users (MAU) reached 83.1 million, up 47% year-over-year.
        Paid subscribers totaled 6.6 million, up 60% from prior year.

        </SEC-DOCUMENT>
        """ * 10,  # Make content long enough
        "content_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
        "downloaded_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_sec_api_responses():
    """Mock SEC EDGAR API responses."""

    company_info_response = {
        "cik": "1835631",
        "entityType": "operating",
        "sic": "7372",
        "sicDescription": "Services-Prepackaged Software",
        "name": "Duolingo, Inc.",
        "tickers": ["DUOL"],
        "exchanges": ["Nasdaq"],
        "ein": "455997061",
        "category": "Large accelerated filer",
        "fiscalYearEnd": "1231",
        "filings": {
            "recent": {
                "accessionNumber": ["0001835631-24-000012", "0001835631-23-000024", "0001835631-23-000018"],
                "filingDate": ["2024-03-15", "2023-11-03", "2023-08-09"],
                "reportDate": ["2023-12-31", "2023-09-30", "2023-06-30"],
                "acceptanceDateTime": ["2024-03-15T16:30:00.000Z", "2023-11-03T16:30:00.000Z", "2023-08-09T16:30:00.000Z"],
                "form": ["10-K", "10-Q", "10-Q"],
                "primaryDocument": ["duol-20231231.htm", "duol-20230930.htm", "duol-20230630.htm"],
                "items": ["1, 1A, 7, 8", "1, 2", "1, 2"],
                "size": [5234567, 3456789, 3123456],
                "isXBRL": [1, 1, 1],
                "isInlineXBRL": [1, 1, 1],
            }
        },
    }

    filing_content_10k = """
    <SEC-DOCUMENT>0001835631-24-000012.txt : 20240315
    <SEC-HEADER>0001835631-24-000012.hdr.sgml : 20240315
    <ACCEPTANCE-DATETIME>20240315163000
    ACCESSION NUMBER:		0001835631-24-000012
    CONFORMED SUBMISSION TYPE:	10-K
    PUBLIC DOCUMENT COUNT:		150
    CONFORMED PERIOD OF REPORT:	20231231
    FILED AS OF DATE:		20240315
    DATE AS OF CHANGE:		20240315

    FILER:
        COMPANY DATA:
            COMPANY CONFORMED NAME:			DUOLINGO, INC.
            CENTRAL INDEX KEY:			0001835631
            IRS NUMBER:				455997061
            FISCAL YEAR END:			1231

    10-K	1	duol-20231231.htm	FORM 10-K

    PART I

    Item 1. Business

    Overview

    Duolingo is a technology platform dedicated to language learning. Since our founding in 2011,
    we have grown to become the world's leading mobile learning platform with over 80 million monthly
    active users learning 40+ languages.

    Our Mission

    Our mission is to develop the best education in the world and make it universally available.
    We accomplish this through a gamified mobile application that makes learning languages fun,
    effective, and accessible to everyone.

    Key Metrics

    For the fiscal year ended December 31, 2023:
    - Monthly Active Users (MAU): 83.1 million (up 47% YoY)
    - Paid Subscribers: 6.6 million (up 60% YoY)
    - Daily Active Users (DAU): 24.2 million (up 62% YoY)
    - DAU/MAU Ratio: 29.1%

    Item 8. Financial Statements and Supplementary Data

    CONSOLIDATED STATEMENTS OF OPERATIONS
    (In thousands, except per share data)

    Year Ended December 31,
                                    2023        2022        2021
    Revenue                      $531,432    $369,454    $250,778
    Cost of revenue               58,234      42,156      31,445
    Gross profit                 473,198     327,298     219,333
    Operating expenses:
      Research and development   156,789     112,345      89,234
      Sales and marketing        234,567     178,234     145,678
      General and administrative  89,234      67,890      56,789
    Total operating expenses     480,590     358,469     291,701
    Loss from operations         (7,392)    (31,171)    (72,368)
    Interest income              15,234       3,456       1,234
    Net income (loss)           $  7,842   $(27,715)   $(71,134)

    </SEC-DOCUMENT>
    """

    filing_content_10q = """
    <SEC-DOCUMENT>0001835631-23-000024.txt : 20231103
    FORM 10-Q

    Item 1. Financial Statements

    DUOLINGO, INC.
    CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS
    (Unaudited)
    (In thousands, except per share data)

    Three Months Ended September 30,
                                    2023        2022
    Revenue                      $137,553    $ 96,743
    Cost of revenue               14,567      11,234
    Gross profit                 122,986      85,509
    Operating expenses           127,890      92,345
    Loss from operations          (4,904)     (6,836)
    Net loss                    $ (3,456)   $ (5,234)

    </SEC-DOCUMENT>
    """

    return {
        "company_info": company_info_response,
        "filing_10k": filing_content_10k,
        "filing_10q": filing_content_10q,
    }


@pytest_asyncio.fixture
async def test_company(db_session: AsyncSession, sample_company_data: Dict[str, Any]) -> Company:
    """Create test company in database."""
    company = Company(**sample_company_data)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


@pytest_asyncio.fixture
async def test_filing(
    db_session: AsyncSession,
    test_company: Company,
    sample_sec_filing_data: Dict[str, Any]
) -> SECFiling:
    """Create test SEC filing in database."""
    filing = SECFiling(
        company_id=test_company.id,
        filing_type=sample_sec_filing_data["form"],
        filing_date=datetime.strptime(sample_sec_filing_data["filingDate"], "%Y-%m-%d"),
        accession_number=sample_sec_filing_data["accessionNumber"],
        filing_url=f"https://www.sec.gov/Archives/edgar/data/{sample_sec_filing_data['cik']}/",
        raw_text=sample_sec_filing_data["content"],
        processing_status="pending",
    )
    db_session.add(filing)
    await db_session.commit()
    await db_session.refresh(filing)
    return filing


@pytest.fixture
def mock_http_client(mock_sec_api_responses):
    """Mock HTTP client for SEC API requests."""

    class MockResponse:
        def __init__(self, json_data=None, text_data=None, status_code=200):
            self._json_data = json_data
            self._text_data = text_data
            self.status_code = status_code

        def json(self):
            return self._json_data

        @property
        def text(self):
            return self._text_data

    class MockAsyncClient:
        def __init__(self):
            self.responses = mock_sec_api_responses

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            # Company info endpoint
            if "submissions/CIK" in url and url.endswith(".json"):
                return MockResponse(json_data=self.responses["company_info"])

            # Filing content endpoint (10-K)
            elif "10-K" in url or "duol-20231231.htm" in url:
                return MockResponse(text_data=self.responses["filing_10k"])

            # Filing content endpoint (10-Q)
            elif "10-Q" in url or "duol-20230930.htm" in url:
                return MockResponse(text_data=self.responses["filing_10q"])

            # Default
            return MockResponse(status_code=404)

    return MockAsyncClient


@pytest.fixture
def patch_httpx_client(mock_http_client):
    """Patch httpx.AsyncClient with mock."""
    import httpx
    from unittest.mock import patch

    with patch("httpx.AsyncClient", return_value=mock_http_client()):
        yield


@pytest.fixture
def patch_session_factory(db_session_factory):
    """Patch get_session_factory to use test database."""
    from unittest.mock import patch

    with patch("src.db.session.get_session_factory", return_value=db_session_factory):
        yield
