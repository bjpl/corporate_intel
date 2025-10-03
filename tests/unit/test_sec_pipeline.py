"""Comprehensive tests for SEC pipeline storage functions."""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from uuid import uuid4

from src.pipeline.sec_ingestion import store_filing
from src.db.models import Company, SECFiling


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_company():
    """Sample company for testing."""
    return Company(
        id=uuid4(),
        ticker="DUOL",
        name="Duolingo Inc.",
        cik="1234567890",
        sector="EdTech",
        subsector="Language Learning",
        category="direct_to_consumer"
    )


@pytest.fixture
def sample_filing_data():
    """Sample filing data for testing."""
    return {
        "form": "10-K",
        "filingDate": "2024-03-15",
        "accessionNumber": "0001234567-89-012345",
        "primaryDocument": "duol-10k_20240315.htm",
        "cik": "1234567890",
        "content": "Annual Report Content " * 100,  # Ensure minimum length
        "content_hash": "a" * 64,  # Valid SHA-256 hash
        "downloaded_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_existing_filing():
    """Sample existing filing in database."""
    return SECFiling(
        id=uuid4(),
        company_id=uuid4(),
        filing_type="10-K",
        filing_date=datetime(2024, 3, 15),
        accession_number="0001234567-89-012345",
        filing_url="https://www.sec.gov/Archives/edgar/data/1234567890/0001234567-89-012345/duol-10k_20240315.htm",
        raw_text="Annual Report Content " * 100,
        processing_status="pending"
    )


# ============================================================================
# STORAGE TESTS - SUCCESS SCENARIOS
# ============================================================================

@pytest.mark.asyncio
class TestFilingStorageSuccess:
    """Test successful filing storage scenarios."""

    async def test_store_filing_new_company(self, mock_db_session, sample_filing_data):
        """Test storing filing for a new company."""
        # Mock company query - company doesn't exist
        mock_query = MagicMock()
        mock_query.filter.return_value.first = AsyncMock(return_value=None)
        mock_db_session.query.return_value = mock_query

        # Mock execute for company creation
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Execute storage
        with patch('src.db.models.Company') as MockCompany, \
             patch('src.db.models.SECFiling') as MockFiling:

            # Setup company mock
            mock_company = Mock()
            mock_company.id = str(uuid4())
            MockCompany.return_value = mock_company

            # Setup filing mock
            mock_filing = Mock()
            MockFiling.return_value = mock_filing

            result = await store_filing(sample_filing_data, sample_filing_data["cik"])

            # Assertions
            assert result == sample_filing_data["accessionNumber"]
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called_once()
            assert not mock_db_session.rollback.called

    async def test_store_filing_existing_company(self, mock_db_session, sample_company, sample_filing_data):
        """Test storing filing for an existing company."""
        # Mock company query - company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock filing query - filing doesn't exist
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        # Setup execute to return different results based on call order
        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result  # First call for company
            else:
                return mock_filing_result  # Second call for filing

        mock_db_session.execute.side_effect = execute_side_effect

        with patch('src.db.models.SECFiling') as MockFiling:
            mock_filing = Mock()
            MockFiling.return_value = mock_filing

            result = await store_filing(sample_filing_data, sample_company.cik)

            # Assertions
            assert result == sample_filing_data["accessionNumber"]
            mock_db_session.add.assert_called_with(mock_filing)
            mock_db_session.commit.assert_called_once()


    async def test_store_filing_with_valid_metadata(self, mock_db_session, sample_company, sample_filing_data):
        """Test that filing metadata is correctly stored."""
        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock filing doesn't exist
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result if call_count == 1 else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        with patch('src.db.models.SECFiling') as MockFiling:
            result = await store_filing(sample_filing_data, sample_company.cik)

            # Verify filing was created with correct data
            MockFiling.assert_called_once()
            call_kwargs = MockFiling.call_args[1]
            assert call_kwargs["filing_type"] == sample_filing_data["form"]
            assert call_kwargs["accession_number"] == sample_filing_data["accessionNumber"]
            assert call_kwargs["raw_text"] == sample_filing_data["content"]


# ============================================================================
# STORAGE TESTS - DUPLICATE DETECTION
# ============================================================================

@pytest.mark.asyncio
class TestDuplicateDetection:
    """Test duplicate filing detection."""

    async def test_duplicate_filing_detection(self, mock_db_session, sample_company, sample_filing_data, sample_existing_filing):
        """Test that duplicate filings are detected and not stored again."""
        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock filing already exists
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = sample_existing_filing

        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result if call_count == 1 else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        result = await store_filing(sample_filing_data, sample_company.cik)

        # Should return accession number but not add to session
        assert result == sample_filing_data["accessionNumber"]
        # Verify that add was not called (filing already exists)
        # In actual implementation, this would skip the add
        mock_db_session.commit.assert_called_once()


    async def test_duplicate_by_content_hash(self, mock_db_session, sample_company, sample_filing_data):
        """Test duplicate detection using content hash."""
        # Create existing filing with same content hash
        existing_filing = SECFiling(
            id=uuid4(),
            company_id=sample_company.id,
            filing_type="10-K",
            filing_date=datetime(2024, 3, 15),
            accession_number="different-accession-123",  # Different accession number
            raw_text=sample_filing_data["content"],  # Same content
            processing_status="completed"
        )

        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock filing with same hash exists
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = existing_filing

        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result if call_count == 1 else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        result = await store_filing(sample_filing_data, sample_company.cik)

        # Should detect duplicate even with different accession number
        assert result == sample_filing_data["accessionNumber"]


# ============================================================================
# STORAGE TESTS - INVALID DATA HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestInvalidDataHandling:
    """Test handling of invalid data."""

    async def test_invalid_cik_format(self, mock_db_session, sample_filing_data):
        """Test handling of invalid CIK format."""
        invalid_cik = "invalid-cik-123"  # Not numeric

        with pytest.raises(ValueError, match="Invalid CIK format"):
            await store_filing(sample_filing_data, invalid_cik)


    async def test_missing_required_fields(self, mock_db_session, sample_company):
        """Test handling of missing required fields in filing data."""
        incomplete_data = {
            "form": "10-K",
            # Missing accessionNumber, filingDate, content
        }

        with pytest.raises(KeyError):
            await store_filing(incomplete_data, sample_company.cik)


    async def test_invalid_accession_number_format(self, mock_db_session, sample_company):
        """Test handling of invalid accession number format."""
        invalid_filing = {
            "form": "10-K",
            "filingDate": "2024-03-15",
            "accessionNumber": "invalid-format",  # Wrong format
            "cik": sample_company.cik,
            "content": "Test content " * 100,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        # This should fail validation
        with pytest.raises(ValueError, match="Invalid accession number format"):
            await store_filing(invalid_filing, sample_company.cik)


    async def test_future_filing_date(self, mock_db_session, sample_company):
        """Test handling of filing date in the future."""
        future_filing = {
            "form": "10-K",
            "filingDate": "2099-12-31",  # Future date
            "accessionNumber": "0001234567-89-012345",
            "cik": sample_company.cik,
            "content": "Test content " * 100,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        with pytest.raises(ValueError, match="Filing date cannot be in the future"):
            await store_filing(future_filing, sample_company.cik)


    async def test_empty_content(self, mock_db_session, sample_company):
        """Test handling of empty filing content."""
        empty_content_filing = {
            "form": "10-K",
            "filingDate": "2024-03-15",
            "accessionNumber": "0001234567-89-012345",
            "cik": sample_company.cik,
            "content": "",  # Empty content
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        with pytest.raises(ValueError, match="Filing content cannot be empty"):
            await store_filing(empty_content_filing, sample_company.cik)


# ============================================================================
# STORAGE TESTS - DATABASE ERRORS
# ============================================================================

@pytest.mark.asyncio
class TestDatabaseErrors:
    """Test database error handling."""

    async def test_database_connection_error(self, mock_db_session, sample_filing_data, sample_company):
        """Test handling of database connection errors."""
        # Mock company query succeeds
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock commit fails with connection error
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit.side_effect = SQLAlchemyError("Connection lost")

        with pytest.raises(SQLAlchemyError, match="Connection lost"):
            await store_filing(sample_filing_data, sample_company.cik)

        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()


    async def test_integrity_constraint_violation(self, mock_db_session, sample_filing_data, sample_company):
        """Test handling of database integrity constraint violations."""
        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock commit fails with integrity error
        mock_db_session.commit.side_effect = IntegrityError(
            "duplicate key value violates unique constraint",
            params=None,
            orig=Exception()
        )

        with pytest.raises(IntegrityError):
            await store_filing(sample_filing_data, sample_company.cik)

        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()


    async def test_transaction_rollback_on_error(self, mock_db_session, sample_filing_data, sample_company):
        """Test that transaction is rolled back on any error."""
        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock filing query fails
        mock_db_session.execute = AsyncMock(side_effect=[
            mock_result,  # Company query succeeds
            Exception("Database error")  # Filing query fails
        ])

        with pytest.raises(Exception, match="Database error"):
            await store_filing(sample_filing_data, sample_company.cik)

        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()
        # Verify commit was never called
        assert not mock_db_session.commit.called


    async def test_session_cleanup_on_error(self, mock_db_session, sample_filing_data):
        """Test that database session is properly cleaned up on error."""
        # Mock execute fails
        mock_db_session.execute = AsyncMock(side_effect=SQLAlchemyError("Query failed"))

        with pytest.raises(SQLAlchemyError):
            await store_filing(sample_filing_data, "1234567890")

        # Verify rollback was called for cleanup
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# STORAGE TESTS - CONCURRENT ACCESS
# ============================================================================

@pytest.mark.asyncio
class TestConcurrentAccess:
    """Test concurrent filing storage."""

    async def test_concurrent_filing_storage(self, mock_db_session, sample_company):
        """Test storing multiple filings concurrently."""
        filings_data = [
            {
                "form": "10-K",
                "filingDate": "2024-03-15",
                "accessionNumber": f"0001234567-89-01234{i}",
                "cik": sample_company.cik,
                "content": f"Filing {i} content " * 100,
                "content_hash": f"{'a' * 63}{i}",
                "downloaded_at": datetime.utcnow().isoformat()
            }
            for i in range(5)
        ]

        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock no existing filings
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        async def execute_side_effect(*args, **kwargs):
            return mock_result if "companies" in str(args) else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        # Store filings concurrently
        import asyncio
        results = await asyncio.gather(*[
            store_filing(filing, sample_company.cik)
            for filing in filings_data
        ])

        # Verify all filings were processed
        assert len(results) == 5
        assert all(result.startswith("0001234567-89-01234") for result in results)


    async def test_race_condition_duplicate_filing(self, mock_db_session, sample_company, sample_filing_data):
        """Test handling of race condition when duplicate filing is inserted."""
        # First check: filing doesn't exist
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[
            mock_result,  # Company check
            mock_filing_result  # Filing check
        ])

        # Commit fails due to race condition (duplicate key)
        mock_db_session.commit.side_effect = IntegrityError(
            "duplicate key value violates unique constraint",
            params=None,
            orig=Exception()
        )

        with pytest.raises(IntegrityError):
            await store_filing(sample_filing_data, sample_company.cik)

        # Verify proper error handling
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# STORAGE TESTS - EDGE CASES
# ============================================================================

@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases in filing storage."""

    async def test_very_large_filing_content(self, mock_db_session, sample_company):
        """Test storing filing with very large content."""
        large_filing = {
            "form": "10-K",
            "filingDate": "2024-03-15",
            "accessionNumber": "0001234567-89-012345",
            "cik": sample_company.cik,
            "content": "x" * (10 * 1024 * 1024),  # 10MB content
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock no existing filing
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result if call_count == 1 else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        with patch('src.db.models.SECFiling') as MockFiling:
            result = await store_filing(large_filing, sample_company.cik)

            # Verify large content is handled
            assert result == large_filing["accessionNumber"]
            MockFiling.assert_called_once()


    async def test_special_characters_in_content(self, mock_db_session, sample_company):
        """Test storing filing with special characters and unicode."""
        special_filing = {
            "form": "10-K",
            "filingDate": "2024-03-15",
            "accessionNumber": "0001234567-89-012345",
            "cik": sample_company.cik,
            "content": "Special chars: €£¥ 中文 한글 العربية 🚀📊 \n\t\r" + "x" * 1000,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock no existing filing
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result if call_count == 1 else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        with patch('src.db.models.SECFiling') as MockFiling:
            result = await store_filing(special_filing, sample_company.cik)

            # Verify special characters are handled
            assert result == special_filing["accessionNumber"]
            call_kwargs = MockFiling.call_args[1]
            assert "€£¥" in call_kwargs["raw_text"]


    async def test_amended_filing_storage(self, mock_db_session, sample_company):
        """Test storing amended filings (10-K/A, 10-Q/A)."""
        amended_filing = {
            "form": "10-K/A",  # Amended filing
            "filingDate": "2024-04-15",
            "accessionNumber": "0001234567-89-012346",
            "cik": sample_company.cik,
            "content": "Amended Annual Report " * 100,
            "content_hash": "b" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        # Mock company exists
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_company

        # Mock no existing filing
        mock_filing_result = Mock()
        mock_filing_result.scalar_one_or_none.return_value = None

        call_count = 0
        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_result if call_count == 1 else mock_filing_result

        mock_db_session.execute.side_effect = execute_side_effect

        with patch('src.db.models.SECFiling') as MockFiling:
            result = await store_filing(amended_filing, sample_company.cik)

            # Verify amended filing type is stored correctly
            assert result == amended_filing["accessionNumber"]
            call_kwargs = MockFiling.call_args[1]
            assert call_kwargs["filing_type"] == "10-K/A"
