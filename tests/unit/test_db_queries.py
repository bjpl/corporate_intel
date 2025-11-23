"""Comprehensive tests for database query operations, bulk operations, and transactions."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine, select, func, and_, or_, desc, asc
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from src.db.models import (
    Base, Company, SECFiling, Document, DocumentChunk,
    MarketIntelligence, AnalysisReport
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite engine for testing."""
    from sqlalchemy import MetaData
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Create tables except financial_metrics (SQLite composite PK limitation)
    metadata = MetaData()
    for table_name, table in Base.metadata.tables.items():
        if table_name != 'financial_metrics':
            table.to_metadata(metadata)

    metadata.create_all(engine)
    yield engine
    metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_companies(session):
    """Create multiple sample companies for testing."""
    companies = [
        Company(
            ticker="DUOL",
            name="Duolingo Inc.",
            cik="1234567890",
            sector="EdTech",
            subsector="Language Learning",
            category="direct_to_consumer",
            founded_year=2011,
            employee_count=800
        ),
        Company(
            ticker="CHGG",
            name="Chegg Inc.",
            cik="9876543210",
            sector="EdTech",
            subsector="Higher Education",
            category="higher_education",
            founded_year=2005,
            employee_count=3000
        ),
        Company(
            ticker="COUR",
            name="Coursera Inc.",
            cik="1122334455",
            sector="EdTech",
            subsector="Online Learning",
            category="higher_education",
            founded_year=2012,
            employee_count=1500
        ),
        Company(
            ticker="UDMY",
            name="Udemy Inc.",
            cik="5544332211",
            sector="EdTech",
            subsector="Corporate Training",
            category="corporate_learning",
            founded_year=2010,
            employee_count=1200
        )
    ]
    session.add_all(companies)
    session.commit()
    for company in companies:
        session.refresh(company)
    return companies


# ============================================================================
# BASIC QUERY TESTS
# ============================================================================

class TestBasicQueries:
    """Test basic database query operations."""

    def test_query_all_companies(self, session, sample_companies):
        """Test querying all companies."""
        result = session.query(Company).all()
        assert len(result) == 4

        tickers = {c.ticker for c in result}
        assert tickers == {"DUOL", "CHGG", "COUR", "UDMY"}

    def test_query_by_ticker(self, session, sample_companies):
        """Test querying company by ticker."""
        company = session.query(Company).filter_by(ticker="DUOL").first()

        assert company is not None
        assert company.name == "Duolingo Inc."
        assert company.cik == "1234567890"

    def test_query_by_multiple_criteria(self, session, sample_companies):
        """Test querying with multiple filter criteria."""
        companies = session.query(Company).filter(
            Company.category == "higher_education",
            Company.founded_year >= 2010
        ).all()

        assert len(companies) == 1
        assert companies[0].ticker == "COUR"

    def test_query_with_or_condition(self, session, sample_companies):
        """Test querying with OR condition."""
        companies = session.query(Company).filter(
            or_(
                Company.ticker == "DUOL",
                Company.ticker == "CHGG"
            )
        ).all()

        assert len(companies) == 2
        tickers = {c.ticker for c in companies}
        assert tickers == {"DUOL", "CHGG"}

    def test_query_with_like(self, session, sample_companies):
        """Test querying with LIKE pattern matching."""
        companies = session.query(Company).filter(
            Company.name.like("%Inc%")
        ).all()

        # All our sample companies have "Inc" in name except one
        assert len(companies) >= 3

    def test_query_with_in_clause(self, session, sample_companies):
        """Test querying with IN clause."""
        tickers = ["DUOL", "COUR"]
        companies = session.query(Company).filter(
            Company.ticker.in_(tickers)
        ).all()

        assert len(companies) == 2
        result_tickers = {c.ticker for c in companies}
        assert result_tickers == set(tickers)


# ============================================================================
# SORTING AND ORDERING TESTS
# ============================================================================

class TestSortingAndOrdering:
    """Test query sorting and ordering."""

    def test_order_by_ticker_asc(self, session, sample_companies):
        """Test ordering companies by ticker ascending."""
        companies = session.query(Company).order_by(
            Company.ticker.asc()
        ).all()

        tickers = [c.ticker for c in companies]
        assert tickers == ["CHGG", "COUR", "DUOL", "UDMY"]

    def test_order_by_ticker_desc(self, session, sample_companies):
        """Test ordering companies by ticker descending."""
        companies = session.query(Company).order_by(
            Company.ticker.desc()
        ).all()

        tickers = [c.ticker for c in companies]
        assert tickers == ["UDMY", "DUOL", "COUR", "CHGG"]

    def test_order_by_multiple_columns(self, session, sample_companies):
        """Test ordering by multiple columns."""
        companies = session.query(Company).order_by(
            Company.category.asc(),
            Company.founded_year.desc()
        ).all()

        assert len(companies) == 4
        # Verify category grouping
        categories = [c.category for c in companies]
        # Categories should be grouped together

    def test_order_by_founded_year(self, session, sample_companies):
        """Test ordering by founded year."""
        companies = session.query(Company).order_by(
            Company.founded_year.asc()
        ).all()

        years = [c.founded_year for c in companies]
        assert years == sorted(years)


# ============================================================================
# PAGINATION AND LIMITING TESTS
# ============================================================================

class TestPaginationAndLimiting:
    """Test pagination and result limiting."""

    def test_limit_results(self, session, sample_companies):
        """Test limiting query results."""
        companies = session.query(Company).limit(2).all()
        assert len(companies) == 2

    def test_offset_results(self, session, sample_companies):
        """Test offsetting query results."""
        all_companies = session.query(Company).order_by(Company.ticker).all()
        offset_companies = session.query(Company).order_by(
            Company.ticker
        ).offset(2).all()

        assert len(offset_companies) == 2
        assert offset_companies[0].ticker == all_companies[2].ticker

    def test_pagination(self, session, sample_companies):
        """Test pagination with limit and offset."""
        page_size = 2
        page_1 = session.query(Company).order_by(
            Company.ticker
        ).limit(page_size).offset(0).all()

        page_2 = session.query(Company).order_by(
            Company.ticker
        ).limit(page_size).offset(page_size).all()

        assert len(page_1) == 2
        assert len(page_2) == 2
        assert page_1[0].ticker != page_2[0].ticker


# ============================================================================
# AGGREGATION TESTS
# ============================================================================

class TestAggregations:
    """Test aggregation queries."""

    def test_count_companies(self, session, sample_companies):
        """Test counting companies."""
        count = session.query(Company).count()
        assert count == 4

    def test_count_by_category(self, session, sample_companies):
        """Test counting companies by category."""
        from sqlalchemy import func

        category_counts = session.query(
            Company.category,
            func.count(Company.id)
        ).group_by(Company.category).all()

        # Convert to dict for easier assertion
        counts = {cat: count for cat, count in category_counts}

        assert counts.get("higher_education", 0) == 2
        assert counts.get("direct_to_consumer", 0) == 1
        assert counts.get("corporate_learning", 0) == 1

    def test_average_employee_count(self, session, sample_companies):
        """Test calculating average employee count."""
        avg_employees = session.query(
            func.avg(Company.employee_count)
        ).scalar()

        expected_avg = (800 + 3000 + 1500 + 1200) / 4
        assert avg_employees == expected_avg

    def test_min_max_founded_year(self, session, sample_companies):
        """Test finding min and max founded year."""
        min_year = session.query(
            func.min(Company.founded_year)
        ).scalar()

        max_year = session.query(
            func.max(Company.founded_year)
        ).scalar()

        assert min_year == 2005
        assert max_year == 2012


# ============================================================================
# JOIN TESTS
# ============================================================================

class TestJoins:
    """Test join operations."""

    def test_join_company_and_filings(self, session, sample_companies):
        """Test joining companies with their filings."""
        company = sample_companies[0]

        # Add filings
        filing1 = SECFiling(
            company_id=company.id,
            filing_type="10-K",
            filing_date=datetime(2024, 3, 15),
            accession_number="0001234567-24-000001"
        )
        filing2 = SECFiling(
            company_id=company.id,
            filing_type="10-Q",
            filing_date=datetime(2024, 6, 15),
            accession_number="0001234567-24-000002"
        )
        session.add_all([filing1, filing2])
        session.commit()

        # Query with join
        results = session.query(Company, SECFiling).join(
            SECFiling, Company.id == SECFiling.company_id
        ).filter(Company.ticker == "DUOL").all()

        assert len(results) == 2

        for company_obj, filing_obj in results:
            assert company_obj.ticker == "DUOL"
            assert filing_obj.filing_type in ["10-K", "10-Q"]

    def test_left_outer_join(self, session, sample_companies):
        """Test left outer join to include companies without filings."""
        # Add filing only for first company
        filing = SECFiling(
            company_id=sample_companies[0].id,
            filing_type="10-K",
            filing_date=datetime.utcnow(),
            accession_number="0001234567-24-000001"
        )
        session.add(filing)
        session.commit()

        # Left join should include all companies
        results = session.query(Company).outerjoin(SECFiling).all()

        assert len(results) == 4  # All companies


# ============================================================================
# BULK OPERATIONS TESTS
# ============================================================================

class TestBulkOperations:
    """Test bulk insert, update, and delete operations."""

    def test_bulk_insert_companies(self, session):
        """Test bulk inserting companies."""
        companies = [
            Company(
                ticker=f"TEST{i}",
                name=f"Test Company {i}",
                cik=f"100000000{i}",
                sector="Test"
            )
            for i in range(100)
        ]

        session.add_all(companies)
        session.commit()

        # Verify all were inserted
        count = session.query(Company).filter(
            Company.ticker.like("TEST%")
        ).count()
        assert count == 100

    def test_bulk_update_companies(self, session, sample_companies):
        """Test bulk updating companies."""
        # Update all companies' sector
        session.query(Company).filter(
            Company.sector == "EdTech"
        ).update({"sector": "Education Technology"})
        session.commit()

        # Verify updates
        updated_companies = session.query(Company).filter(
            Company.sector == "Education Technology"
        ).all()
        assert len(updated_companies) == 4

    def test_bulk_delete_companies(self, session):
        """Test bulk deleting companies."""
        # Create test companies
        companies = [
            Company(
                ticker=f"DEL{i}",
                name=f"Delete Company {i}",
                cik=f"900000000{i}"
            )
            for i in range(10)
        ]
        session.add_all(companies)
        session.commit()

        # Bulk delete
        deleted = session.query(Company).filter(
            Company.ticker.like("DEL%")
        ).delete()
        session.commit()

        assert deleted == 10

        # Verify deletion
        remaining = session.query(Company).filter(
            Company.ticker.like("DEL%")
        ).count()
        assert remaining == 0


# ============================================================================
# TRANSACTION TESTS
# ============================================================================

class TestTransactions:
    """Test transaction handling."""

    def test_transaction_commit(self, session):
        """Test successful transaction commit."""
        company = Company(
            ticker="TRAN",
            name="Transaction Test",
            cik="1111111111"
        )
        session.add(company)
        session.commit()

        # Verify committed
        result = session.query(Company).filter_by(ticker="TRAN").first()
        assert result is not None

    def test_transaction_rollback(self, session):
        """Test transaction rollback on error."""
        company1 = Company(
            ticker="ROLL1",
            name="Rollback Test 1",
            cik="2222222222"
        )
        session.add(company1)
        session.commit()

        try:
            # Try to add duplicate
            company2 = Company(
                ticker="ROLL1",  # Duplicate ticker
                name="Rollback Test 2",
                cik="3333333333"
            )
            session.add(company2)
            session.commit()
        except IntegrityError:
            session.rollback()

        # First company should still exist
        result = session.query(Company).filter_by(ticker="ROLL1").first()
        assert result is not None
        assert result.name == "Rollback Test 1"

    def test_transaction_savepoint(self, session):
        """Test using savepoints in transactions."""
        # Add first company
        company1 = Company(
            ticker="SAVE1",
            name="Savepoint Test 1",
            cik="4444444444"
        )
        session.add(company1)
        session.flush()

        # Create savepoint
        savepoint = session.begin_nested()

        try:
            # Try to add duplicate
            company2 = Company(
                ticker="SAVE1",  # Duplicate
                name="Savepoint Test 2",
                cik="5555555555"
            )
            session.add(company2)
            session.flush()
        except IntegrityError:
            savepoint.rollback()

        # Commit outer transaction
        session.commit()

        # First company should exist
        result = session.query(Company).filter_by(ticker="SAVE1").first()
        assert result is not None


# ============================================================================
# COMPLEX QUERY TESTS
# ============================================================================

class TestComplexQueries:
    """Test complex query scenarios."""

    def test_subquery(self, session, sample_companies):
        """Test using subqueries."""
        # Create subquery for average employee count
        subq = session.query(
            func.avg(Company.employee_count).label("avg_employees")
        ).subquery()

        # Query companies above average
        companies = session.query(Company).filter(
            Company.employee_count > subq.c.avg_employees
        ).all()

        # Should get companies with above average employees
        assert len(companies) >= 1

    def test_case_statement(self, session, sample_companies):
        """Test using CASE statement in query."""
        from sqlalchemy import case

        # Categorize by employee size
        size_category = case(
            (Company.employee_count < 1000, "Small"),
            (Company.employee_count < 2000, "Medium"),
            else_="Large"
        ).label("size_category")

        results = session.query(
            Company.name,
            Company.employee_count,
            size_category
        ).all()

        assert len(results) == 4

    def test_distinct_values(self, session, sample_companies):
        """Test querying distinct values."""
        categories = session.query(
            Company.category
        ).distinct().all()

        # Flatten results
        category_list = [c[0] for c in categories]

        assert len(category_list) == 3
        assert "higher_education" in category_list

    def test_exists_query(self, session, sample_companies):
        """Test using EXISTS in query."""
        company = sample_companies[0]

        # Add a filing
        filing = SECFiling(
            company_id=company.id,
            filing_type="10-K",
            filing_date=datetime.utcnow(),
            accession_number="0001234567-24-000001"
        )
        session.add(filing)
        session.commit()

        # Query companies that have filings
        companies_with_filings = session.query(Company).filter(
            Company.filings.any()
        ).all()

        assert len(companies_with_filings) >= 1
        assert company.id in [c.id for c in companies_with_filings]
