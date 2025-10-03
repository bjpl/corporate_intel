"""Integration tests for SEC ingestion pipeline.

Tests complete workflow from SEC API fetch to database storage,
including error handling, rollback scenarios, and concurrent execution.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company, SECFiling, FinancialMetric
from src.pipeline.sec_ingestion import (
    FilingRequest,
    fetch_company_data,
    fetch_filings,
    download_filing,
    validate_filing_data,
    store_filing,
    sec_ingestion_flow,
    batch_sec_ingestion_flow,
)


# ============================================================================
# END-TO-END WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
class TestEndToEndWorkflow:
    """Test complete SEC filing ingestion workflow."""

    async def test_complete_ingestion_flow_new_company(
        self,
        db_session: AsyncSession,
        patch_httpx_client,
        patch_session_factory
    ):
        """Test complete ingestion flow for a new company."""
        # Create filing request
        request = FilingRequest(
            company_ticker="DUOL",
            filing_types=["10-K"],
            start_date=datetime(2024, 1, 1)
        )

        # Execute flow
        result = await sec_ingestion_flow(request)

        # Verify result
        assert result is not None
        assert result["ticker"] == "DUOL"
        assert result["cik"] == "1835631"
        assert result["filings_found"] >= 1
        assert result["filings_stored"] >= 1

        # Verify company was created
        company_result = await db_session.execute(
            select(Company).where(Company.ticker == "DUOL")
        )
        company = company_result.scalar_one()
        assert company.name == "Duolingo, Inc."
        assert company.cik == "1835631"

        # Verify filing was stored
        filing_result = await db_session.execute(
            select(SECFiling).where(SECFiling.company_id == company.id)
        )
        filing = filing_result.scalar_one()
        assert filing.filing_type == "10-K"
        assert filing.processing_status == "pending"
        assert len(filing.raw_text) > 100


    async def test_complete_ingestion_flow_existing_company(
        self,
        db_session: AsyncSession,
        test_company: Company,
        patch_httpx_client,
        patch_session_factory
    ):
        """Test ingestion flow for existing company."""
        request = FilingRequest(
            company_ticker="DUOL",
            filing_types=["10-K"],
            start_date=datetime(2024, 1, 1)
        )

        result = await sec_ingestion_flow(request)

        # Verify company was not duplicated
        count_result = await db_session.execute(
            select(func.count()).select_from(Company).where(Company.ticker == "DUOL")
        )
        company_count = count_result.scalar()
        assert company_count == 1

        # Verify filing was added to existing company
        filing_result = await db_session.execute(
            select(SECFiling).where(SECFiling.company_id == test_company.id)
        )
        filings = filing_result.scalars().all()
        assert len(filings) >= 1


    async def test_batch_ingestion_multiple_companies(
        self,
        db_session: AsyncSession,
        patch_httpx_client,
        patch_session_factory
    ):
        """Test batch ingestion for multiple companies."""
        tickers = ["DUOL", "CHGG", "COUR"]

        with patch("src.pipeline.sec_ingestion.sec_ingestion_flow") as mock_flow:
            # Mock individual flow results
            mock_flow.side_effect = [
                {
                    "ticker": ticker,
                    "cik": f"123456{i}",
                    "filings_found": 3,
                    "filings_stored": 3
                }
                for i, ticker in enumerate(tickers)
            ]

            results = await batch_sec_ingestion_flow(tickers)

            # Verify all companies processed
            assert len(results) == 3
            assert mock_flow.call_count == 3

            # Verify results
            for i, result in enumerate(results):
                assert result["ticker"] == tickers[i]
                assert result["filings_stored"] == 3


# ============================================================================
# DUPLICATE FILING HANDLING
# ============================================================================

@pytest.mark.asyncio
class TestDuplicateFilingHandling:
    """Test duplicate filing detection and handling."""

    async def test_duplicate_filing_skipped(
        self,
        db_session: AsyncSession,
        test_company: Company,
        test_filing: SECFiling,
        sample_sec_filing_data
    ):
        """Test that duplicate filings are detected and skipped."""
        # Try to store the same filing again
        filing_id = await store_filing(sample_sec_filing_data, test_company.cik)

        # Should return existing filing ID
        assert str(filing_id) == str(test_filing.id)

        # Verify only one filing exists
        result = await db_session.execute(
            select(func.count()).select_from(SECFiling).where(
                SECFiling.accession_number == sample_sec_filing_data["accessionNumber"]
            )
        )
        count = result.scalar()
        assert count == 1


    async def test_duplicate_detection_across_sessions(
        self,
        db_session: AsyncSession,
        test_company: Company,
        sample_sec_filing_data,
        patch_session_factory
    ):
        """Test duplicate detection works across different sessions."""
        # Store filing in first session
        filing_id_1 = await store_filing(sample_sec_filing_data, test_company.cik)
        await db_session.commit()

        # Try to store again (simulating different session)
        filing_id_2 = await store_filing(sample_sec_filing_data, test_company.cik)

        # Should be same filing
        assert filing_id_1 == filing_id_2

        # Verify database integrity
        result = await db_session.execute(
            select(SECFiling).where(SECFiling.accession_number == sample_sec_filing_data["accessionNumber"])
        )
        filings = result.scalars().all()
        assert len(filings) == 1


# ============================================================================
# ERROR RECOVERY AND ROLLBACK
# ============================================================================

@pytest.mark.asyncio
class TestErrorRecoveryRollback:
    """Test error recovery and transaction rollback scenarios."""

    async def test_validation_failure_rollback(
        self,
        db_session: AsyncSession,
        test_company: Company
    ):
        """Test that validation failures trigger rollback."""
        invalid_filing = {
            "form": "INVALID-TYPE",  # Invalid form type
            "filingDate": "2024-03-15",
            "accessionNumber": "0001835631-24-999999",
            "cik": test_company.cik,
            "content": "x" * 50,  # Too short
            "content_hash": "invalid-hash",  # Invalid hash format
            "downloaded_at": datetime.utcnow().isoformat()
        }

        # Validation should fail
        is_valid = validate_filing_data(invalid_filing)
        assert is_valid is False

        # If we try to store invalid data, it should raise error
        with pytest.raises(Exception):
            await store_filing(invalid_filing, test_company.cik)

        # Verify no filing was stored
        result = await db_session.execute(
            select(SECFiling).where(
                SECFiling.accession_number == invalid_filing["accessionNumber"]
            )
        )
        filing = result.scalar_one_or_none()
        assert filing is None


    async def test_database_error_rollback(
        self,
        db_session: AsyncSession,
        test_company: Company,
        sample_sec_filing_data
    ):
        """Test rollback on database errors."""
        # Patch db session to raise error on commit
        with patch.object(db_session, 'commit', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await store_filing(sample_sec_filing_data, test_company.cik)

        # Verify rollback occurred - no filing stored
        result = await db_session.execute(
            select(SECFiling).where(
                SECFiling.accession_number == sample_sec_filing_data["accessionNumber"]
            )
        )
        filing = result.scalar_one_or_none()
        assert filing is None


    async def test_partial_batch_failure_isolation(
        self,
        db_session: AsyncSession,
        patch_httpx_client,
        patch_session_factory
    ):
        """Test that one filing failure doesn't affect others."""
        # Create multiple filing data with one invalid
        filings = [
            {
                "form": "10-K",
                "filingDate": "2024-03-15",
                "accessionNumber": f"0001835631-24-00001{i}",
                "cik": "1835631",
                "content": "Valid content " * 100 if i != 2 else "x",  # Third one is invalid
                "content_hash": "a" * 64,
                "downloaded_at": datetime.utcnow().isoformat(),
            }
            for i in range(5)
        ]

        # Process filings
        stored_count = 0
        for filing in filings:
            try:
                if validate_filing_data(filing):
                    await store_filing(filing, "1835631")
                    stored_count += 1
            except Exception:
                pass

        # Should have stored all valid filings
        assert stored_count == 4

        # Verify in database
        result = await db_session.execute(
            select(func.count()).select_from(SECFiling)
        )
        count = result.scalar()
        assert count == 4


# ============================================================================
# CONCURRENT EXECUTION
# ============================================================================

@pytest.mark.asyncio
class TestConcurrentExecution:
    """Test concurrent filing processing."""

    async def test_concurrent_filing_downloads(
        self,
        db_session: AsyncSession,
        patch_httpx_client,
        patch_session_factory
    ):
        """Test concurrent download of multiple filings."""
        # Mock filings list
        filings = [
            {
                "form": "10-K",
                "filingDate": "2024-03-15",
                "accessionNumber": f"0001835631-24-00001{i}",
                "primaryDocument": f"filing{i}.htm",
                "cik": "1835631",
            }
            for i in range(10)
        ]

        # Download concurrently
        download_tasks = [download_filing(filing) for filing in filings]
        results = await asyncio.gather(*download_tasks)

        # Verify all downloads completed
        assert len(results) == 10
        for result in results:
            assert "content" in result
            assert "content_hash" in result


    async def test_concurrent_company_ingestion(
        self,
        db_session: AsyncSession,
        patch_httpx_client,
        patch_session_factory
    ):
        """Test concurrent ingestion for multiple companies."""
        tickers = ["DUOL", "CHGG", "COUR", "2U", "ARCE"]

        # Create concurrent requests
        requests = [
            FilingRequest(
                company_ticker=ticker,
                filing_types=["10-K"],
                start_date=datetime.now() - timedelta(days=365)
            )
            for ticker in tickers
        ]

        # Execute flows concurrently
        with patch("src.pipeline.sec_ingestion.sec_ingestion_flow") as mock_flow:
            mock_flow.side_effect = [
                {
                    "ticker": ticker,
                    "cik": f"123456{i}",
                    "filings_found": 2,
                    "filings_stored": 2
                }
                for i, ticker in enumerate(tickers)
            ]

            tasks = [sec_ingestion_flow(req) for req in requests]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(r["filings_stored"] > 0 for r in results)


    async def test_rate_limiting_concurrent_requests(
        self,
        db_session: AsyncSession,
        patch_httpx_client
    ):
        """Test rate limiting works with concurrent requests."""
        from src.pipeline.sec_ingestion import RateLimiter

        rate_limiter = RateLimiter(calls_per_second=10)

        async def rate_limited_task(task_id: int):
            await rate_limiter.acquire()
            return task_id

        # Execute 50 concurrent tasks
        start_time = datetime.now()
        tasks = [rate_limited_task(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        elapsed = (datetime.now() - start_time).total_seconds()

        # Should take at least 5 seconds (50 calls / 10 per second)
        assert len(results) == 50
        assert elapsed >= 4.0  # Allow some margin


# ============================================================================
# TIMESCALEDB FEATURES
# ============================================================================

@pytest.mark.asyncio
class TestTimescaleDBFeatures:
    """Test TimescaleDB time-series features."""

    async def test_financial_metrics_hypertable(
        self,
        db_session: AsyncSession,
        test_company: Company
    ):
        """Test financial metrics stored in TimescaleDB hypertable."""
        # Insert time-series financial metrics
        metrics = []
        base_date = datetime(2024, 1, 1)

        for i in range(12):  # 12 months of data
            metric_date = base_date + timedelta(days=30 * i)
            metric = FinancialMetric(
                company_id=test_company.id,
                metric_date=metric_date,
                period_type="monthly",
                metric_type="revenue",
                metric_category="financial",
                value=1000000 + (i * 100000),
                unit="USD",
                source="sec_filing",
                confidence_score=0.95
            )
            metrics.append(metric)
            db_session.add(metric)

        await db_session.commit()

        # Query time-series data
        result = await db_session.execute(
            select(FinancialMetric)
            .where(FinancialMetric.company_id == test_company.id)
            .where(FinancialMetric.metric_type == "revenue")
            .order_by(FinancialMetric.metric_date)
        )
        stored_metrics = result.scalars().all()

        assert len(stored_metrics) == 12
        assert stored_metrics[0].value == 1000000
        assert stored_metrics[-1].value == 2100000


    async def test_time_bucket_aggregation(
        self,
        db_session: AsyncSession,
        test_company: Company
    ):
        """Test TimescaleDB time_bucket aggregation."""
        # Insert daily metrics
        base_date = datetime(2024, 1, 1)
        for i in range(90):  # 90 days of data
            metric = FinancialMetric(
                company_id=test_company.id,
                metric_date=base_date + timedelta(days=i),
                period_type="daily",
                metric_type="mau",
                metric_category="operational",
                value=1000000 + (i * 1000),
                unit="count",
                source="api",
                confidence_score=0.99
            )
            db_session.add(metric)

        await db_session.commit()

        # Use time_bucket to aggregate by week
        from sqlalchemy import text
        result = await db_session.execute(
            text("""
                SELECT
                    time_bucket('7 days', metric_date) as week,
                    AVG(value) as avg_value,
                    MAX(value) as max_value,
                    MIN(value) as min_value
                FROM financial_metrics
                WHERE company_id = :company_id
                AND metric_type = 'mau'
                GROUP BY week
                ORDER BY week
            """),
            {"company_id": test_company.id}
        )

        weekly_data = result.fetchall()

        # Should have approximately 13 weeks of data
        assert len(weekly_data) >= 12
        assert len(weekly_data) <= 14


    async def test_continuous_aggregate_materialized_view(
        self,
        setup_test_database,
        test_company: Company
    ):
        """Test creating continuous aggregates for metrics."""
        async with setup_test_database.begin() as conn:
            # Create continuous aggregate view
            await conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_revenue_summary
                WITH (timescaledb.continuous) AS
                SELECT
                    company_id,
                    time_bucket('1 month', metric_date) as month,
                    AVG(value) as avg_revenue,
                    SUM(value) as total_revenue,
                    COUNT(*) as data_points
                FROM financial_metrics
                WHERE metric_type = 'revenue'
                GROUP BY company_id, month
            """))

            # Insert some revenue data
            await conn.execute(text("""
                INSERT INTO financial_metrics
                (company_id, metric_date, period_type, metric_type, metric_category, value, unit, source, confidence_score)
                VALUES
                (:company_id, :date1, 'daily', 'revenue', 'financial', 100000, 'USD', 'api', 0.95),
                (:company_id, :date2, 'daily', 'revenue', 'financial', 105000, 'USD', 'api', 0.95),
                (:company_id, :date3, 'daily', 'revenue', 'financial', 110000, 'USD', 'api', 0.95)
            """), {
                "company_id": test_company.id,
                "date1": datetime(2024, 1, 1),
                "date2": datetime(2024, 1, 15),
                "date3": datetime(2024, 1, 30)
            })

            # Refresh the continuous aggregate
            await conn.execute(text("CALL refresh_continuous_aggregate('monthly_revenue_summary', NULL, NULL)"))

            # Query the aggregate view
            result = await conn.execute(
                text("SELECT * FROM monthly_revenue_summary WHERE company_id = :company_id"),
                {"company_id": test_company.id}
            )

            summary = result.fetchone()
            assert summary is not None
            assert summary.data_points == 3
            assert summary.total_revenue == 315000


# ============================================================================
# DATA VALIDATION
# ============================================================================

@pytest.mark.asyncio
class TestDataValidation:
    """Test Great Expectations data validation."""

    async def test_valid_filing_passes_validation(self, sample_sec_filing_data):
        """Test that valid filing data passes validation."""
        is_valid = validate_filing_data(sample_sec_filing_data)
        assert is_valid is True


    async def test_missing_required_field_fails(self):
        """Test validation fails for missing required fields."""
        invalid_filing = {
            "form": "10-K",
            # Missing other required fields
        }

        is_valid = validate_filing_data(invalid_filing)
        assert is_valid is False


    async def test_invalid_accession_number_format(self):
        """Test validation fails for invalid accession number format."""
        invalid_filing = {
            "form": "10-K",
            "filingDate": "2024-03-15",
            "accessionNumber": "invalid-format",  # Wrong format
            "cik": "1835631",
            "content": "x" * 1000,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        is_valid = validate_filing_data(invalid_filing)
        assert is_valid is False


    async def test_invalid_form_type_fails(self):
        """Test validation fails for invalid form types."""
        invalid_filing = {
            "form": "INVALID-FORM",  # Not a valid SEC form type
            "filingDate": "2024-03-15",
            "accessionNumber": "0001835631-24-000012",
            "cik": "1835631",
            "content": "x" * 1000,
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        is_valid = validate_filing_data(invalid_filing)
        assert is_valid is False


    async def test_content_too_short_fails(self):
        """Test validation fails for content that's too short."""
        invalid_filing = {
            "form": "10-K",
            "filingDate": "2024-03-15",
            "accessionNumber": "0001835631-24-000012",
            "cik": "1835631",
            "content": "x" * 50,  # Less than minimum 100 characters
            "content_hash": "a" * 64,
            "downloaded_at": datetime.utcnow().isoformat()
        }

        is_valid = validate_filing_data(invalid_filing)
        assert is_valid is False


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestPerformance:
    """Test pipeline performance and optimization."""

    async def test_bulk_filing_storage_performance(
        self,
        db_session: AsyncSession,
        test_company: Company
    ):
        """Test performance of bulk filing storage."""
        # Generate 100 filings
        filings = [
            {
                "form": "10-K" if i % 4 == 0 else "10-Q",
                "filingDate": (datetime(2024, 1, 1) + timedelta(days=i * 10)).strftime("%Y-%m-%d"),
                "accessionNumber": f"0001835631-24-{i:06d}",
                "cik": test_company.cik,
                "content": f"Filing content {i} " * 100,
                "content_hash": f"{i:064d}",
                "downloaded_at": datetime.utcnow().isoformat()
            }
            for i in range(100)
        ]

        start_time = datetime.now()

        for filing in filings:
            if validate_filing_data(filing):
                await store_filing(filing, test_company.cik)

        elapsed = (datetime.now() - start_time).total_seconds()

        # Should complete in reasonable time (< 10 seconds for 100 filings)
        assert elapsed < 10.0

        # Verify all stored
        result = await db_session.execute(
            select(func.count()).select_from(SECFiling).where(
                SECFiling.company_id == test_company.id
            )
        )
        count = result.scalar()
        assert count == 100


    async def test_concurrent_validation_performance(self, sample_sec_filing_data):
        """Test concurrent validation performance."""
        # Create 50 filing variants
        filings = [
            {**sample_sec_filing_data, "accessionNumber": f"0001835631-24-{i:06d}"}
            for i in range(50)
        ]

        start_time = datetime.now()

        # Validate concurrently
        tasks = [asyncio.to_thread(validate_filing_data, filing) for filing in filings]
        results = await asyncio.gather(*tasks)

        elapsed = (datetime.now() - start_time).total_seconds()

        # Should complete quickly
        assert elapsed < 5.0
        assert all(results)  # All should be valid
