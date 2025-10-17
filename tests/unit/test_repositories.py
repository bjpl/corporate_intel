"""Comprehensive unit tests for repository pattern implementation.

Tests cover:
- BaseRepository CRUD operations
- CompanyRepository specialized methods
- MetricsRepository time-series operations
- Transaction management
- Error handling
- Edge cases
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company, FinancialMetric
from src.repositories import (
    BaseRepository,
    CompanyRepository,
    DuplicateRecordError,
    MetricsRepository,
    RecordNotFoundError,
    RepositoryError,
    TransactionError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.get = AsyncMock()
    session.add = MagicMock()  # Regular mock (not async)
    session.add_all = MagicMock()  # Regular mock (not async)
    return session


@pytest.fixture
def sample_company():
    """Create a sample company instance."""
    return Company(
        id=uuid4(),
        ticker="DUOL",
        name="Duolingo Inc.",
        cik="0001364612",
        sector="Education Technology",
        category="k12",
        founded_year=2011,
        headquarters="Pittsburgh, PA",
        website="https://duolingo.com",
        employee_count=700,
    )


@pytest.fixture
def sample_metric():
    """Create a sample financial metric instance."""
    company_id = uuid4()
    return FinancialMetric(
        id=1,
        company_id=company_id,
        metric_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
        period_type="quarterly",
        metric_type="revenue",
        metric_category="financial",
        value=50000000.0,
        unit="USD",
        source="alpha_vantage",
        confidence_score=0.95,
    )


# ============================================================================
# BaseRepository Tests
# ============================================================================

class TestBaseRepository:
    """Test suite for BaseRepository abstract class."""

    @pytest.mark.asyncio
    async def test_create_success(self, mock_session, sample_company):
        """Test successful record creation."""
        # Setup
        repo = CompanyRepository(mock_session)  # Use concrete implementation
        mock_session.flush.return_value = None
        mock_session.refresh.return_value = None

        # Execute
        result = await repo.create(
            ticker="TEST",
            name="Test Company",
            sector="Technology"
        )

        # Verify
        assert mock_session.add.called
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_error(self, mock_session):
        """Test creation with duplicate constraint violation."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.flush.side_effect = IntegrityError("duplicate", {}, None)

        # Execute & Verify
        with pytest.raises(DuplicateRecordError):
            await repo.create(ticker="DUOL", name="Duplicate")

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_transaction_error(self, mock_session):
        """Test creation with general database error."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.flush.side_effect = SQLAlchemyError("Database error")

        # Execute & Verify
        with pytest.raises(TransactionError):
            await repo.create(ticker="TEST", name="Test")

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session, sample_company):
        """Test getting record by ID when found."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.get.return_value = sample_company

        # Execute
        result = await repo.get_by_id(sample_company.id)

        # Verify
        assert result == sample_company
        mock_session.get.assert_called_once_with(Company, sample_company.id)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        """Test getting record by ID when not found."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.get.return_value = None

        # Execute
        result = await repo.get_by_id(uuid4())

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, mock_session, sample_company):
        """Test getting all records with pagination."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.get_all(limit=10, offset=5, order_by="name")

        # Verify
        assert len(results) == 1
        assert results[0] == sample_company
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(self, mock_session, sample_company):
        """Test successful record update."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.get.return_value = sample_company

        # Execute
        updated = await repo.update(
            sample_company.id,
            name="Updated Name",
            employee_count=1000
        )

        # Verify
        assert updated.name == "Updated Name"
        assert updated.employee_count == 1000
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, mock_session):
        """Test update when record doesn't exist."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.get.return_value = None

        # Execute & Verify
        with pytest.raises(RecordNotFoundError):
            await repo.update(uuid4(), name="New Name")

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_session):
        """Test successful record deletion."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        deleted = await repo.delete(uuid4())

        # Verify
        assert deleted is True
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_session):
        """Test deletion when record doesn't exist."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Execute
        deleted = await repo.delete(uuid4())

        # Verify
        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists_true(self, mock_session, sample_company):
        """Test exists check when record exists."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.get.return_value = sample_company

        # Execute
        exists = await repo.exists(sample_company.id)

        # Verify
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_false(self, mock_session):
        """Test exists check when record doesn't exist."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_session.get.return_value = None

        # Execute
        exists = await repo.exists(uuid4())

        # Verify
        assert exists is False

    @pytest.mark.asyncio
    async def test_count(self, mock_session, sample_company):
        """Test counting records with filters."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repo.count(sector="Education Technology")

        # Verify
        assert count == 1

    @pytest.mark.asyncio
    async def test_find_by(self, mock_session, sample_company):
        """Test finding records by filters."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.find_by(ticker="DUOL")

        # Verify
        assert len(results) == 1
        assert results[0] == sample_company

    @pytest.mark.asyncio
    async def test_find_one_by(self, mock_session, sample_company):
        """Test finding single record by filters."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repo.find_one_by(ticker="DUOL")

        # Verify
        assert result == sample_company

    @pytest.mark.asyncio
    async def test_find_one_by_not_found(self, mock_session):
        """Test finding single record when not found."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repo.find_one_by(ticker="NONEXISTENT")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_transaction_success(self, mock_session):
        """Test successful transaction context manager."""
        # Setup
        repo = CompanyRepository(mock_session)

        # Execute
        async with repo.transaction():
            pass  # Simulate operations

        # Verify
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, mock_session):
        """Test transaction rollback on error."""
        # Setup
        repo = CompanyRepository(mock_session)

        # Execute & Verify
        with pytest.raises(TransactionError):
            async with repo.transaction():
                raise ValueError("Simulated error")

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(self, mock_session):
        """Test bulk creation of records."""
        # Setup
        repo = CompanyRepository(mock_session)
        records = [
            {"ticker": "TEST1", "name": "Test 1"},
            {"ticker": "TEST2", "name": "Test 2"},
        ]

        # Execute
        results = await repo.bulk_create(records)

        # Verify
        assert mock_session.add_all.called
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update(self, mock_session):
        """Test bulk update of records."""
        # Setup
        repo = CompanyRepository(mock_session)
        updates = [
            {"id": uuid4(), "employee_count": 500},
            {"id": uuid4(), "employee_count": 1000},
        ]
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repo.bulk_update(updates)

        # Verify
        assert count == 2


# ============================================================================
# CompanyRepository Tests
# ============================================================================

class TestCompanyRepository:
    """Test suite for CompanyRepository."""

    @pytest.mark.asyncio
    async def test_get_or_create_by_ticker_existing(self, mock_session, sample_company):
        """Test get_or_create with existing company."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_session.execute.return_value = mock_result

        # Execute
        company, created = await repo.get_or_create_by_ticker("DUOL")

        # Verify
        assert company == sample_company
        assert created is False

    @pytest.mark.asyncio
    async def test_get_or_create_by_ticker_new(self, mock_session):
        """Test get_or_create with new company."""
        # Setup
        repo = CompanyRepository(mock_session)
        # First call returns None (not found)
        mock_result_none = AsyncMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result_none

        # Execute
        company, created = await repo.get_or_create_by_ticker(
            "NEW",
            defaults={"name": "New Company"}
        )

        # Verify
        assert created is True
        assert mock_session.add.called

    @pytest.mark.asyncio
    async def test_find_by_ticker(self, mock_session, sample_company):
        """Test finding company by ticker."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repo.find_by_ticker("DUOL")

        # Verify
        assert result == sample_company

    @pytest.mark.asyncio
    async def test_find_by_ticker_case_insensitive(self, mock_session, sample_company):
        """Test ticker search is case-insensitive."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_session.execute.return_value = mock_result

        # Execute - lowercase ticker
        result = await repo.find_by_ticker("duol")

        # Verify
        assert result == sample_company

    @pytest.mark.asyncio
    async def test_find_by_cik(self, mock_session, sample_company):
        """Test finding company by CIK."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repo.find_by_cik("0001364612")

        # Verify
        assert result == sample_company

    @pytest.mark.asyncio
    async def test_find_by_category(self, mock_session, sample_company):
        """Test finding companies by category."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.find_by_category("k12")

        # Verify
        assert len(results) == 1
        assert results[0] == sample_company

    @pytest.mark.asyncio
    async def test_find_by_sector(self, mock_session, sample_company):
        """Test finding companies by sector."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.find_by_sector("Education Technology")

        # Verify
        assert len(results) == 1
        assert results[0] == sample_company

    @pytest.mark.asyncio
    async def test_search_by_name(self, mock_session, sample_company):
        """Test searching companies by name."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_company]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.search_by_name("duolingo")

        # Verify
        assert len(results) == 1
        assert results[0] == sample_company

    @pytest.mark.asyncio
    async def test_get_all_tickers(self, mock_session):
        """Test getting all company tickers."""
        # Setup
        repo = CompanyRepository(mock_session)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("DUOL",), ("CHGG",), ("COUR",)]
        mock_session.execute.return_value = mock_result

        # Execute
        tickers = await repo.get_all_tickers()

        # Verify
        assert tickers == ["DUOL", "CHGG", "COUR"]

    @pytest.mark.asyncio
    async def test_count_by_category(self, mock_session, sample_company):
        """Test counting companies by category."""
        # Setup
        repo = CompanyRepository(mock_session)
        companies = [
            sample_company,
            Company(id=uuid4(), ticker="TEST", name="Test", category="k12"),
            Company(id=uuid4(), ticker="HED", name="Higher Ed", category="higher_education"),
        ]
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = companies
        mock_session.execute.return_value = mock_result

        # Execute
        counts = await repo.count_by_category()

        # Verify
        assert counts["k12"] == 2
        assert counts["higher_education"] == 1


# ============================================================================
# MetricsRepository Tests
# ============================================================================

class TestMetricsRepository:
    """Test suite for MetricsRepository."""

    @pytest.mark.asyncio
    async def test_upsert_metric_insert(self, mock_session):
        """Test upserting a new metric (insert)."""
        # Setup
        repo = MetricsRepository(mock_session)
        company_id = uuid4()
        metric_date = datetime(2024, 3, 31, tzinfo=timezone.utc)

        # Mock find_one_by to return a metric after upsert
        mock_metric = FinancialMetric(
            id=1,
            company_id=company_id,
            metric_date=metric_date,
            period_type="quarterly",
            metric_type="revenue",
            value=50000000.0,
        )
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_metric]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repo.upsert_metric(
            company_id=company_id,
            metric_type="revenue",
            metric_date=metric_date,
            period_type="quarterly",
            value=50000000.0,
            unit="USD"
        )

        # Verify
        assert mock_session.execute.called
        assert mock_session.flush.called

    @pytest.mark.asyncio
    async def test_get_metrics_by_period_with_quarters(self, mock_session, sample_metric):
        """Test getting metrics by period with quarters filter."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_metric]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.get_metrics_by_period(
            sample_metric.company_id,
            "revenue",
            quarters=8
        )

        # Verify
        assert len(results) == 1
        assert results[0] == sample_metric

    @pytest.mark.asyncio
    async def test_get_metrics_by_period_with_date_range(self, mock_session, sample_metric):
        """Test getting metrics by date range."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_metric]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.get_metrics_by_period(
            sample_metric.company_id,
            "revenue",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )

        # Verify
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_latest_metric(self, mock_session, sample_metric):
        """Test getting the latest metric value."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_metric
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repo.get_latest_metric(
            sample_metric.company_id,
            "revenue"
        )

        # Verify
        assert result == sample_metric

    @pytest.mark.asyncio
    async def test_get_all_metrics_for_company(self, mock_session, sample_metric):
        """Test getting all metrics for a company."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_metric]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.get_all_metrics_for_company(sample_metric.company_id)

        # Verify
        assert len(results) == 1
        assert results[0] == sample_metric

    @pytest.mark.asyncio
    async def test_get_metrics_by_category(self, mock_session, sample_metric):
        """Test getting metrics by category."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_metric]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repo.get_metrics_by_category(
            sample_metric.company_id,
            "financial"
        )

        # Verify
        assert len(results) == 1
        assert results[0].metric_category == "financial"

    @pytest.mark.asyncio
    async def test_delete_metrics_for_company(self, mock_session):
        """Test deleting metrics for a company."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repo.delete_metrics_for_company(uuid4())

        # Verify
        assert count == 5
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_metrics_by_type(self, mock_session):
        """Test deleting specific metric type."""
        # Setup
        repo = MetricsRepository(mock_session)
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repo.delete_metrics_for_company(
            uuid4(),
            metric_type="revenue"
        )

        # Verify
        assert count == 2

    @pytest.mark.asyncio
    async def test_bulk_upsert_metrics(self, mock_session):
        """Test bulk upserting metrics."""
        # Setup
        repo = MetricsRepository(mock_session)
        company_id = uuid4()
        metrics_data = [
            {
                "company_id": company_id,
                "metric_type": "revenue",
                "metric_date": datetime(2024, 3, 31, tzinfo=timezone.utc),
                "period_type": "quarterly",
                "value": 50000000.0,
                "unit": "USD"
            },
            {
                "company_id": company_id,
                "metric_type": "mau",
                "metric_date": datetime(2024, 3, 31, tzinfo=timezone.utc),
                "period_type": "quarterly",
                "value": 1000000.0,
                "unit": "count"
            }
        ]

        # Execute
        count = await repo.bulk_upsert_metrics(metrics_data)

        # Verify
        assert count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_growth_rate(self, mock_session):
        """Test calculating growth rate."""
        # Setup
        repo = MetricsRepository(mock_session)
        company_id = uuid4()

        # Create metrics with growth
        metrics = [
            FinancialMetric(
                id=1,
                company_id=company_id,
                metric_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
                period_type="quarterly",
                metric_type="revenue",
                value=60000000.0,  # Latest
            ),
            FinancialMetric(
                id=2,
                company_id=company_id,
                metric_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
                period_type="quarterly",
                metric_type="revenue",
                value=55000000.0,
            ),
            FinancialMetric(
                id=3,
                company_id=company_id,
                metric_date=datetime(2023, 9, 30, tzinfo=timezone.utc),
                period_type="quarterly",
                metric_type="revenue",
                value=52000000.0,
            ),
            FinancialMetric(
                id=4,
                company_id=company_id,
                metric_date=datetime(2023, 6, 30, tzinfo=timezone.utc),
                period_type="quarterly",
                metric_type="revenue",
                value=48000000.0,
            ),
            FinancialMetric(
                id=5,
                company_id=company_id,
                metric_date=datetime(2023, 3, 31, tzinfo=timezone.utc),
                period_type="quarterly",
                metric_type="revenue",
                value=50000000.0,  # YoY base
            ),
        ]

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = metrics
        mock_session.execute.return_value = mock_result

        # Execute - calculate YoY growth (4 quarters)
        growth_rate = await repo.calculate_growth_rate(
            company_id,
            "revenue",
            periods=4
        )

        # Verify - (60M - 50M) / 50M * 100 = 20%
        assert growth_rate == pytest.approx(20.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_metric_statistics(self, mock_session):
        """Test getting metric statistics."""
        # Setup
        repo = MetricsRepository(mock_session)
        company_id = uuid4()

        metrics = [
            FinancialMetric(
                id=i,
                company_id=company_id,
                metric_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
                period_type="quarterly",
                metric_type="revenue",
                value=float(40000000 + i * 10000000),
            )
            for i in range(5)
        ]

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = metrics
        mock_session.execute.return_value = mock_result

        # Execute
        stats = await repo.get_metric_statistics(company_id, "revenue")

        # Verify
        assert stats['count'] == 5
        assert stats['min'] == 40000000.0
        assert stats['max'] == 80000000.0
        assert stats['avg'] == 60000000.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestRepositoryIntegration:
    """Integration tests for repository pattern."""

    @pytest.mark.asyncio
    async def test_company_and_metrics_workflow(self, mock_session):
        """Test complete workflow: create company and add metrics."""
        # Setup
        company_repo = CompanyRepository(mock_session)
        metrics_repo = MetricsRepository(mock_session)

        # Mock for company creation
        mock_result_none = AsyncMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result_none

        # Create company
        company, created = await company_repo.get_or_create_by_ticker(
            "TEST",
            defaults={"name": "Test Company"}
        )

        assert created is True

        # Mock for metric upsert
        mock_metric = FinancialMetric(
            id=1,
            company_id=company.id,
            metric_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
            period_type="quarterly",
            metric_type="revenue",
            value=50000000.0,
        )
        mock_result_metric = AsyncMock()
        mock_result_metric.scalars.return_value.all.return_value = [mock_metric]
        mock_session.execute.return_value = mock_result_metric

        # Add metric
        metric = await metrics_repo.upsert_metric(
            company_id=company.id,
            metric_type="revenue",
            metric_date=datetime(2024, 3, 31, tzinfo=timezone.utc),
            period_type="quarterly",
            value=50000000.0,
            unit="USD"
        )

        # Verify workflow completed
        assert mock_session.execute.called
        assert mock_session.flush.called
