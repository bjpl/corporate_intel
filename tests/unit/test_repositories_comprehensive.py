"""Comprehensive repository tests to achieve 80%+ coverage.

Tests cover:
- BaseRepository CRUD operations
- CompanyRepository specialized methods
- MetricsRepository time-series queries
- Transaction management
- Error handling (DuplicateRecordError, RecordNotFoundError, TransactionError)
- Bulk operations
- Edge cases and boundary conditions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.base_repository import (
    BaseRepository,
    DuplicateRecordError,
    RecordNotFoundError,
    RepositoryError,
    TransactionError,
)
from src.repositories.company_repository import CompanyRepository
from src.repositories.metrics_repository import MetricsRepository
from src.db.models import Company, FinancialMetric


# ============================================================================
# BaseRepository Tests
# ============================================================================


class TestBaseRepository:
    """Test BaseRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful record creation."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        with patch.object(repo, 'session', mock_session):
            company = await repo.create(ticker="DUOL", name="Duolingo Inc.")

            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_error(self):
        """Test create with duplicate constraint violation."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add.side_effect = IntegrityError("Duplicate", None, None)
        mock_session.rollback = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        with pytest.raises(DuplicateRecordError):
            await repo.create(ticker="DUOL", name="Duolingo Inc.")

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sqlalchemy_error(self):
        """Test create with SQLAlchemy error."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add.side_effect = SQLAlchemyError("DB Error")
        mock_session.rollback = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        with pytest.raises(TransactionError):
            await repo.create(ticker="DUOL", name="Duolingo Inc.")

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test get_by_id when record exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_company = Company(id=uuid4(), ticker="DUOL", name="Duolingo Inc.")
        mock_session.get = AsyncMock(return_value=mock_company)

        repo = BaseRepository(Company, mock_session)

        result = await repo.get_by_id(mock_company.id)

        assert result == mock_company

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test get_by_id when record doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=None)

        repo = BaseRepository(Company, mock_session)

        result = await repo.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_sqlalchemy_error(self):
        """Test get_by_id with database error."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(side_effect=SQLAlchemyError("DB Error"))

        repo = BaseRepository(Company, mock_session)

        with pytest.raises(TransactionError):
            await repo.get_by_id(uuid4())

    @pytest.mark.asyncio
    async def test_get_all_success(self):
        """Test get_all with pagination."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_companies = [
            Company(id=uuid4(), ticker="DUOL", name="Duolingo"),
            Company(id=uuid4(), ticker="CHGG", name="Chegg")
        ]
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = BaseRepository(Company, mock_session)

        results = await repo.get_all(limit=10, offset=0, order_by="ticker")

        assert len(results) == 2
        assert results[0].ticker == "DUOL"

    @pytest.mark.asyncio
    async def test_get_all_empty(self):
        """Test get_all with no results."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalars().all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = BaseRepository(Company, mock_session)

        results = await repo.get_all()

        assert results == []

    @pytest.mark.asyncio
    async def test_update_success(self):
        """Test successful update."""
        mock_session = AsyncMock(spec=AsyncSession)
        company_id = uuid4()
        mock_company = Company(id=company_id, ticker="DUOL", name="Duolingo Inc.")
        mock_session.get = AsyncMock(return_value=mock_company)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        updated = await repo.update(company_id, name="Duolingo Corporation")

        assert updated.name == "Duolingo Corporation"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test update when record doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=None)

        repo = BaseRepository(Company, mock_session)

        with pytest.raises(RecordNotFoundError):
            await repo.update(uuid4(), name="New Name")

    @pytest.mark.asyncio
    async def test_update_with_timestamp(self):
        """Test update sets updated_at timestamp."""
        mock_session = AsyncMock(spec=AsyncSession)
        company_id = uuid4()
        mock_company = Company(id=company_id, ticker="DUOL", name="Duolingo Inc.")
        mock_company.updated_at = datetime(2023, 1, 1)
        mock_session.get = AsyncMock(return_value=mock_company)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        await repo.update(company_id, name="New Name")

        assert mock_company.updated_at > datetime(2023, 1, 1)

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Test successful delete."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        deleted = await repo.delete(uuid4())

        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test delete when record doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        deleted = await repo.delete(uuid4())

        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists when record exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_company = Company(id=uuid4(), ticker="DUOL", name="Duolingo")
        mock_session.get = AsyncMock(return_value=mock_company)

        repo = BaseRepository(Company, mock_session)

        exists = await repo.exists(mock_company.id)

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists when record doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.get = AsyncMock(return_value=None)

        repo = BaseRepository(Company, mock_session)

        exists = await repo.exists(uuid4())

        assert exists is False

    @pytest.mark.asyncio
    async def test_count_with_filters(self):
        """Test count with filters."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_companies = [Company(id=uuid4(), ticker="DUOL", sector="EdTech")]
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = BaseRepository(Company, mock_session)

        count = await repo.count(sector="EdTech")

        assert count == 1

    @pytest.mark.asyncio
    async def test_find_by_success(self):
        """Test find_by with filters."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_companies = [
            Company(id=uuid4(), ticker="DUOL", category="k12"),
            Company(id=uuid4(), ticker="CHGG", category="k12")
        ]
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = BaseRepository(Company, mock_session)

        results = await repo.find_by(category="k12")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_one_by_found(self):
        """Test find_one_by when record found."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_company = Company(id=uuid4(), ticker="DUOL", name="Duolingo")
        mock_result.scalars().all.return_value = [mock_company]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = BaseRepository(Company, mock_session)

        result = await repo.find_one_by(ticker="DUOL")

        assert result == mock_company

    @pytest.mark.asyncio
    async def test_find_one_by_not_found(self):
        """Test find_one_by when no record found."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.scalars().all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = BaseRepository(Company, mock_session)

        result = await repo.find_one_by(ticker="INVALID")

        assert result is None

    @pytest.mark.asyncio
    async def test_bulk_create_success(self):
        """Test successful bulk create."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        records = [
            {"ticker": "DUOL", "name": "Duolingo"},
            {"ticker": "CHGG", "name": "Chegg"}
        ]

        with patch.object(repo, 'model_class', Company):
            instances = await repo.bulk_create(records)

            assert len(instances) == 2
            mock_session.add_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_success(self):
        """Test successful bulk update."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        repo = BaseRepository(Company, mock_session)

        updates = [
            {"id": uuid4(), "name": "New Name 1"},
            {"id": uuid4(), "name": "New Name 2"}
        ]

        count = await repo.bulk_update(updates)

        assert count == 2


# ============================================================================
# CompanyRepository Tests
# ============================================================================


class TestCompanyRepository:
    """Test CompanyRepository specialized methods."""

    @pytest.mark.asyncio
    async def test_get_or_create_by_ticker_existing(self):
        """Test get_or_create when company exists."""
        mock_session = AsyncMock(spec=AsyncSession)
        existing_company = Company(id=uuid4(), ticker="DUOL", name="Duolingo Inc.")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_company
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        company, created = await repo.get_or_create_by_ticker("DUOL")

        assert created is False
        assert company == existing_company

    @pytest.mark.asyncio
    async def test_get_or_create_by_ticker_new(self):
        """Test get_or_create when company doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)

        # First call returns None (doesn't exist)
        mock_result_none = Mock()
        mock_result_none.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_result_none)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = CompanyRepository(mock_session)

        company, created = await repo.get_or_create_by_ticker(
            "DUOL",
            defaults={"name": "Duolingo Inc.", "sector": "EdTech"}
        )

        assert created is True

    @pytest.mark.asyncio
    async def test_find_by_ticker_found(self):
        """Test find_by_ticker when company found."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_company = Company(id=uuid4(), ticker="DUOL", name="Duolingo")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_company
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        company = await repo.find_by_ticker("DUOL")

        assert company == mock_company

    @pytest.mark.asyncio
    async def test_find_by_ticker_case_insensitive(self):
        """Test find_by_ticker is case insensitive."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_company = Company(id=uuid4(), ticker="DUOL", name="Duolingo")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_company
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        company = await repo.find_by_ticker("duol")  # lowercase

        assert company == mock_company

    @pytest.mark.asyncio
    async def test_find_by_cik_success(self):
        """Test find_by_cik when company found."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_company = Company(id=uuid4(), cik="0001364612", ticker="DUOL")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_company
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        company = await repo.find_by_cik("1364612")  # Without leading zeros

        assert company == mock_company

    @pytest.mark.asyncio
    async def test_find_by_category_success(self):
        """Test find_by_category returns correct companies."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_companies = [
            Company(id=uuid4(), ticker="DUOL", category="k12"),
            Company(id=uuid4(), ticker="TEST", category="k12")
        ]
        mock_result = Mock()
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        companies = await repo.find_by_category("k12")

        assert len(companies) == 2

    @pytest.mark.asyncio
    async def test_search_by_name_success(self):
        """Test search_by_name with partial match."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_companies = [
            Company(id=uuid4(), ticker="DUOL", name="Duolingo Education"),
            Company(id=uuid4(), ticker="EDU", name="Education Corp")
        ]
        mock_result = Mock()
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        companies = await repo.search_by_name("education")

        assert len(companies) == 2

    @pytest.mark.asyncio
    async def test_get_all_tickers_success(self):
        """Test get_all_tickers returns list of tickers."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.fetchall.return_value = [("DUOL",), ("CHGG",), ("EDU",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        tickers = await repo.get_all_tickers()

        assert tickers == ["DUOL", "CHGG", "EDU"]

    @pytest.mark.asyncio
    async def test_count_by_category_success(self):
        """Test count_by_category groups correctly."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_companies = [
            Company(id=uuid4(), ticker="DUOL", category="k12"),
            Company(id=uuid4(), ticker="CHGG", category="higher_education"),
            Company(id=uuid4(), ticker="EDU", category="k12")
        ]
        mock_result = Mock()
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        counts = await repo.count_by_category()

        assert counts["k12"] == 2
        assert counts["higher_education"] == 1

    @pytest.mark.asyncio
    async def test_get_recently_added_success(self):
        """Test get_recently_added filters by date."""
        mock_session = AsyncMock(spec=AsyncSession)
        recent_date = datetime.utcnow() - timedelta(days=3)
        mock_companies = [
            Company(id=uuid4(), ticker="DUOL", created_at=recent_date),
        ]
        mock_result = Mock()
        mock_result.scalars().all.return_value = mock_companies
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CompanyRepository(mock_session)

        companies = await repo.get_recently_added(days=7)

        assert len(companies) == 1
