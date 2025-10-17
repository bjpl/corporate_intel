"""Unit tests for pipeline common utilities module.

Tests cover:
- get_or_create_company: Company record management
- upsert_financial_metric: Metric upsert with conflict resolution
- retry_with_backoff: Retry decorator with exponential backoff
- run_coordination_hook: Hook execution with error handling
- notify_progress: Progress notification wrapper

Target: 100% test coverage for src/pipeline/common/utilities.py
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Company, FinancialMetric
from src.pipeline.common import (
    get_or_create_company,
    upsert_financial_metric,
    retry_with_backoff,
    run_coordination_hook,
    notify_progress,
)


class TestGetOrCreateCompany:
    """Tests for get_or_create_company utility function."""

    @pytest.mark.asyncio
    async def test_get_existing_company(self, async_session: AsyncSession):
        """Test retrieving an existing company."""
        # Create existing company
        company = Company(
            ticker="CHGG",
            name="Chegg Inc.",
            sector="Education Technology",
            category="EdTech",
        )
        async_session.add(company)
        await async_session.commit()

        # Get existing company
        result = await get_or_create_company(async_session, "CHGG")

        assert result is not None
        assert result.ticker == "CHGG"
        assert result.name == "Chegg Inc."
        assert result.id == company.id

    @pytest.mark.asyncio
    async def test_get_existing_company_case_insensitive(self, async_session: AsyncSession):
        """Test ticker lookup is case-insensitive."""
        # Create company with uppercase ticker
        company = Company(
            ticker="DUOL",
            name="Duolingo Inc.",
            sector="Education Technology",
            category="EdTech",
        )
        async_session.add(company)
        await async_session.commit()

        # Search with lowercase ticker
        result = await get_or_create_company(async_session, "duol")

        assert result is not None
        assert result.ticker == "DUOL"
        assert result.id == company.id

    @pytest.mark.asyncio
    async def test_create_new_company_minimal(self, async_session: AsyncSession):
        """Test creating a new company with minimal fields."""
        result = await get_or_create_company(async_session, "NEWCO")

        assert result is not None
        assert result.ticker == "NEWCO"
        assert result.name == "NEWCO (Auto-created)"
        assert result.sector == "Education Technology"
        assert result.category == "EdTech"
        assert result.id is not None

        # Verify it was saved
        stmt = select(Company).where(Company.ticker == "NEWCO")
        query_result = await async_session.execute(stmt)
        saved_company = query_result.scalar_one_or_none()

        assert saved_company is not None
        assert saved_company.id == result.id

    @pytest.mark.asyncio
    async def test_create_new_company_with_extra_fields(self, async_session: AsyncSession):
        """Test creating a company with all optional fields."""
        result = await get_or_create_company(
            async_session,
            ticker="COUR",
            name="Coursera Inc.",
            sector="Online Education",
            category="Higher Ed",
            website="https://www.coursera.org",
            employee_count=1500,
            headquarters="Mountain View, CA",
            subcategory=["Online Learning", "MOOCs"],
        )

        assert result is not None
        assert result.ticker == "COUR"
        assert result.name == "Coursera Inc."
        assert result.sector == "Online Education"
        assert result.category == "Higher Ed"
        assert result.website == "https://www.coursera.org"
        assert result.employee_count == 1500
        assert result.headquarters == "Mountain View, CA"
        assert result.subcategory == ["Online Learning", "MOOCs"]


class TestUpsertFinancialMetric:
    """Tests for upsert_financial_metric utility function."""

    @pytest.mark.asyncio
    async def test_insert_new_metric(self, async_session: AsyncSession):
        """Test inserting a new financial metric."""
        # Create company first
        company = Company(
            ticker="TEST",
            name="Test Company",
            sector="Education Technology",
            category="EdTech",
        )
        async_session.add(company)
        await async_session.flush()

        # Insert metric
        metric_date = datetime(2024, 3, 31, tzinfo=timezone.utc)
        await upsert_financial_metric(
            async_session,
            company_id=company.id,
            metric_date=metric_date,
            period_type="quarterly",
            metric_type="revenue",
            value=150000000.0,
            unit="USD",
            metric_category="financial",
            source="test_source",
            confidence_score=0.95,
        )

        # Verify insert
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id,
            FinancialMetric.metric_type == "revenue",
        )
        result = await async_session.execute(stmt)
        metric = result.scalar_one_or_none()

        assert metric is not None
        assert metric.value == 150000000.0
        assert metric.unit == "USD"
        assert metric.metric_category == "financial"
        assert metric.source == "test_source"
        assert metric.confidence_score == 0.95

    @pytest.mark.asyncio
    async def test_update_existing_metric(self, async_session: AsyncSession):
        """Test updating an existing metric with conflict resolution."""
        # Create company and initial metric
        company = Company(
            ticker="TEST2",
            name="Test Company 2",
            sector="Education Technology",
            category="EdTech",
        )
        async_session.add(company)
        await async_session.flush()

        metric_date = datetime(2024, 6, 30, tzinfo=timezone.utc)

        # Insert initial metric
        await upsert_financial_metric(
            async_session,
            company_id=company.id,
            metric_date=metric_date,
            period_type="quarterly",
            metric_type="revenue",
            value=100000000.0,
            unit="USD",
            metric_category="financial",
            source="yahoo_finance",
            confidence_score=0.90,
        )
        await async_session.commit()

        # Update with new value
        await upsert_financial_metric(
            async_session,
            company_id=company.id,
            metric_date=metric_date,
            period_type="quarterly",
            metric_type="revenue",
            value=110000000.0,
            unit="USD",
            metric_category="financial",
            source="alpha_vantage",
            confidence_score=0.95,
        )
        await async_session.commit()

        # Verify update (should only have one record)
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id,
            FinancialMetric.metric_type == "revenue",
        )
        result = await async_session.execute(stmt)
        metrics = result.scalars().all()

        assert len(metrics) == 1
        assert metrics[0].value == 110000000.0
        assert metrics[0].source == "alpha_vantage"
        assert metrics[0].confidence_score == 0.95

    @pytest.mark.asyncio
    async def test_upsert_with_pandas_timestamp(self, async_session: AsyncSession):
        """Test upsert handles pandas Timestamp conversion."""
        company = Company(
            ticker="TEST3",
            name="Test Company 3",
            sector="Education Technology",
            category="EdTech",
        )
        async_session.add(company)
        await async_session.flush()

        # Use pandas Timestamp (naive)
        metric_date = pd.Timestamp("2024-09-30")

        await upsert_financial_metric(
            async_session,
            company_id=company.id,
            metric_date=metric_date,
            period_type="quarterly",
            metric_type="gross_margin",
            value=65.5,
            unit="percent",
            metric_category="financial",
        )

        # Verify insert
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id
        )
        result = await async_session.execute(stmt)
        metric = result.scalar_one_or_none()

        assert metric is not None
        assert metric.metric_date.tzinfo is not None  # Should be timezone-aware

    @pytest.mark.asyncio
    async def test_upsert_with_string_company_id(self, async_session: AsyncSession):
        """Test upsert handles string UUID conversion."""
        company = Company(
            ticker="TEST4",
            name="Test Company 4",
            sector="Education Technology",
            category="EdTech",
        )
        async_session.add(company)
        await async_session.flush()

        # Pass company_id as string
        company_id_str = str(company.id)
        metric_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        await upsert_financial_metric(
            async_session,
            company_id=company_id_str,
            metric_date=metric_date,
            period_type="annual",
            metric_type="eps",
            value=3.45,
            unit="USD",
            metric_category="profitability",
        )

        # Verify insert
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id
        )
        result = await async_session.execute(stmt)
        metric = result.scalar_one_or_none()

        assert metric is not None
        assert metric.value == 3.45


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test function succeeds on first attempt (no retry needed)."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """Test function retries on transient failure."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient error")
            return "success"

        result = await flaky_function()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test function fails after max retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent error")

        with pytest.raises(ConnectionError):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_value_error(self):
        """Test no retry on ValueError (non-retryable exception)."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1, no_retry_on=(ValueError,))
        async def validation_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid data")

        with pytest.raises(ValueError):
            await validation_error()

        assert call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_selective_retry_on_specific_exceptions(self):
        """Test retry only on specific exception types."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.1,
            retry_on=(ConnectionError, TimeoutError),
            no_retry_on=(ValueError,)
        )
        async def selective_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")
            elif call_count == 2:
                raise TimeoutError("Request timeout")
            return "success"

        result = await selective_function()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delay calculation."""
        call_times = []

        @retry_with_backoff(max_retries=4, base_delay=0.1, exponential=True)
        async def timed_function():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 4:
                raise ConnectionError("Retry")
            return "success"

        await timed_function()

        # Verify delays: 0.1s, 0.2s, 0.4s (exponential)
        assert len(call_times) == 4
        # Allow 50ms tolerance for timing
        assert 0.08 < (call_times[1] - call_times[0]) < 0.15
        assert 0.15 < (call_times[2] - call_times[1]) < 0.25
        assert 0.35 < (call_times[3] - call_times[2]) < 0.45

    @pytest.mark.asyncio
    async def test_linear_backoff_timing(self):
        """Test linear backoff delay calculation."""
        call_times = []

        @retry_with_backoff(max_retries=4, base_delay=0.1, exponential=False)
        async def timed_function():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 4:
                raise ConnectionError("Retry")
            return "success"

        await timed_function()

        # Verify delays: 0.1s, 0.2s, 0.3s (linear)
        assert len(call_times) == 4
        assert 0.08 < (call_times[1] - call_times[0]) < 0.15
        assert 0.18 < (call_times[2] - call_times[1]) < 0.25
        assert 0.28 < (call_times[3] - call_times[2]) < 0.35


class TestRunCoordinationHook:
    """Tests for run_coordination_hook utility function."""

    @pytest.mark.asyncio
    async def test_successful_hook_execution(self):
        """Test successful hook execution returns True."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"success", b""))
            mock_subprocess.return_value = mock_process

            result = await run_coordination_hook(
                "pre-task",
                description="Test task"
            )

            assert result is True
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_hook_execution(self):
        """Test failed hook execution returns False."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock failed process
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_subprocess.return_value = mock_process

            result = await run_coordination_hook(
                "post-task",
                task_id="test-task"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_hook_timeout(self):
        """Test hook execution timeout returns False."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock process that times out
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_process.kill = MagicMock()
            mock_subprocess.return_value = mock_process

            result = await run_coordination_hook(
                "notify",
                timeout=0.1,
                message="Test message"
            )

            assert result is False
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_hook_command_construction(self):
        """Test correct command construction with parameters."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_process

            await run_coordination_hook(
                "post-edit",
                file="test.py",
                memory_key="swarm/coder/test"
            )

            # Verify command was constructed correctly
            call_args = mock_subprocess.call_args
            cmd = call_args[0]

            assert "npx" in cmd
            assert "claude-flow@alpha" in cmd
            assert "hooks" in cmd
            assert "post-edit" in cmd
            assert "--file" in cmd
            assert "test.py" in cmd
            assert "--memory-key" in cmd
            assert "swarm/coder/test" in cmd

    @pytest.mark.asyncio
    async def test_hook_exception_handling(self):
        """Test exception during hook execution returns False."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock exception
            mock_subprocess.side_effect = Exception("Command not found")

            result = await run_coordination_hook(
                "pre-task",
                description="Test"
            )

            assert result is False


class TestNotifyProgress:
    """Tests for notify_progress utility function."""

    @pytest.mark.asyncio
    async def test_notify_progress_calls_hook(self):
        """Test notify_progress calls run_coordination_hook correctly."""
        with patch("src.pipeline.common.utilities.run_coordination_hook") as mock_hook:
            mock_hook.return_value = True

            await notify_progress("Test progress message")

            mock_hook.assert_called_once_with("notify", message="Test progress message")

    @pytest.mark.asyncio
    async def test_notify_progress_with_special_characters(self):
        """Test notify_progress handles special characters in message."""
        with patch("src.pipeline.common.utilities.run_coordination_hook") as mock_hook:
            mock_hook.return_value = True

            message = "Processed 15/27 companies - 55% complete"
            await notify_progress(message)

            mock_hook.assert_called_once_with("notify", message=message)


# Integration-style tests

class TestCommonUtilitiesIntegration:
    """Integration tests combining multiple utilities."""

    @pytest.mark.asyncio
    async def test_full_ingestion_workflow(self, async_session: AsyncSession):
        """Test realistic ingestion workflow using multiple utilities."""
        # 1. Get or create company
        company = await get_or_create_company(
            async_session,
            ticker="INTEG",
            name="Integration Test Company",
            website="https://example.com",
        )

        assert company is not None

        # 2. Insert multiple metrics
        metrics = [
            ("revenue", 100000000.0, "USD", "financial"),
            ("gross_margin", 65.5, "percent", "financial"),
            ("operating_margin", 25.3, "percent", "financial"),
        ]

        metric_date = datetime(2024, 9, 30, tzinfo=timezone.utc)

        for metric_type, value, unit, category in metrics:
            await upsert_financial_metric(
                async_session,
                company_id=company.id,
                metric_date=metric_date,
                period_type="quarterly",
                metric_type=metric_type,
                value=value,
                unit=unit,
                metric_category=category,
                source="test",
            )

        await async_session.commit()

        # 3. Verify all metrics were inserted
        stmt = select(FinancialMetric).where(
            FinancialMetric.company_id == company.id
        )
        result = await async_session.execute(stmt)
        saved_metrics = result.scalars().all()

        assert len(saved_metrics) == 3
        metric_types = {m.metric_type for m in saved_metrics}
        assert metric_types == {"revenue", "gross_margin", "operating_margin"}

    @pytest.mark.asyncio
    async def test_retry_with_coordination_hooks(self):
        """Test retry decorator with coordination hook notifications."""
        attempt_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.05)
        async def flaky_operation_with_hooks():
            nonlocal attempt_count
            attempt_count += 1

            # Simulate coordination hook
            await notify_progress(f"Attempt {attempt_count}")

            if attempt_count < 2:
                raise ConnectionError("Network error")

            return "success"

        with patch("src.pipeline.common.utilities.run_coordination_hook") as mock_hook:
            mock_hook.return_value = True

            result = await flaky_operation_with_hooks()

            assert result == "success"
            assert attempt_count == 2
            assert mock_hook.call_count == 2  # Called twice (once per attempt)
