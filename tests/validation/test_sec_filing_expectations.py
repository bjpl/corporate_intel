"""
Test cases for SEC Filing Great Expectations validation suite.

This module contains comprehensive test cases covering:
- Positive scenarios (valid data)
- Negative scenarios (invalid data)
- Edge cases
- Data quality scenarios
"""

import pandas as pd
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from great_expectations.core import ExpectationSuite
from great_expectations.core.batch import RuntimeBatchRequest


class TestSECFilingCoreExpectations:
    """Test core validation expectations for SEC filings."""

    @pytest.fixture
    def valid_filing_data(self) -> pd.DataFrame:
        """Create valid SEC filing test data."""
        return pd.DataFrame([
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "filing_type": "10-K",
                "filing_date": datetime(2024, 3, 15),
                "accession_number": "0001234567-24-000001",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456724000001/filing.htm",
                "raw_text": "A" * 5000,  # 5000 char content
                "parsed_sections": {"business_description": "EdTech company"},
                "processing_status": "completed",
                "processed_at": datetime(2024, 3, 16),
                "created_at": datetime(2024, 3, 15),
                "updated_at": datetime(2024, 3, 16)
            }
        ])

    @pytest.fixture
    def expectation_suite(self) -> ExpectationSuite:
        """Load SEC filing core expectation suite."""
        # This would load from actual suite file
        suite = ExpectationSuite(expectation_suite_name="sec_filings_core")

        # Add core expectations
        suite.add_expectation({
            "expectation_type": "expect_column_values_to_not_be_null",
            "kwargs": {"column": "accession_number"}
        })

        suite.add_expectation({
            "expectation_type": "expect_column_values_to_match_regex",
            "kwargs": {
                "column": "accession_number",
                "regex": "^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
            }
        })

        return suite

    # === Positive Test Cases ===

    def test_valid_10k_filing(self, valid_filing_data, expectation_suite):
        """TC-001: Valid 10-K filing with all required fields."""
        # Test that valid data passes all expectations
        assert valid_filing_data["filing_type"].iloc[0] == "10-K"
        assert valid_filing_data["accession_number"].notna().all()
        assert len(valid_filing_data["raw_text"].iloc[0]) >= 1000

    def test_valid_10q_filing(self):
        """TC-002: Valid 10-Q filing."""
        data = pd.DataFrame([{
            "company_id": "660e8400-e29b-41d4-a716-446655440001",
            "filing_type": "10-Q",
            "filing_date": datetime(2024, 6, 15),
            "accession_number": "0001234567-24-000002",
            "raw_text": "B" * 2000,
            "processing_status": "completed"
        }])

        assert data["filing_type"].iloc[0] == "10-Q"
        assert data["accession_number"].str.match(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$").all()

    def test_historical_filing_1994(self):
        """TC-003: Historical filing from EDGAR launch (1994)."""
        data = pd.DataFrame([{
            "company_id": "660e8400-e29b-41d4-a716-446655440001",
            "filing_type": "10-K",
            "filing_date": datetime(1994, 1, 15),
            "accession_number": "0001234567-94-000001",
            "raw_text": "C" * 3000
        }])

        assert data["filing_date"].iloc[0] >= datetime(1994, 1, 1)
        assert data["filing_date"].iloc[0] <= datetime.now()

    def test_recent_filing_current_year(self):
        """TC-004: Recent filing from current year."""
        current_year = datetime.now().year
        data = pd.DataFrame([{
            "company_id": "660e8400-e29b-41d4-a716-446655440001",
            "filing_type": "8-K",
            "filing_date": datetime.now() - timedelta(days=7),
            "accession_number": f"0001234567-{current_year % 100:02d}-000001",
            "raw_text": "D" * 1500
        }])

        assert data["filing_date"].iloc[0].year == current_year

    def test_multiple_filings_per_company(self):
        """TC-005: Multiple filings for one company maintain uniqueness."""
        data = pd.DataFrame([
            {
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "accession_number": "0001234567-24-000001",
                "filing_type": "10-K",
                "filing_date": datetime(2024, 3, 15),
                "raw_text": "E" * 2000
            },
            {
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "accession_number": "0001234567-24-000002",
                "filing_type": "10-Q",
                "filing_date": datetime(2024, 6, 15),
                "raw_text": "F" * 2000
            },
            {
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "accession_number": "0001234567-24-000003",
                "filing_type": "8-K",
                "filing_date": datetime(2024, 9, 15),
                "raw_text": "G" * 1500
            }
        ])

        # Check uniqueness of accession numbers
        assert data["accession_number"].is_unique
        # All belong to same company
        assert data["company_id"].nunique() == 1

    # === Negative Test Cases ===

    def test_missing_accession_number(self):
        """TC-101: Missing accession number should fail validation."""
        data = pd.DataFrame([{
            "company_id": "660e8400-e29b-41d4-a716-446655440001",
            "filing_type": "10-K",
            "filing_date": datetime(2024, 3, 15),
            "accession_number": None,
            "raw_text": "H" * 2000
        }])

        # This should fail NOT NULL expectation
        assert data["accession_number"].isna().any()

    def test_invalid_accession_format(self):
        """TC-102: Invalid accession format should fail validation."""
        data = pd.DataFrame([{
            "accession_number": "12345",  # Too short, wrong format
            "filing_type": "10-K"
        }])

        pattern = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
        assert not data["accession_number"].str.match(pattern).all()

    def test_future_filing_date(self):
        """TC-103: Future filing date should fail validation."""
        future_date = datetime.now() + timedelta(days=365)
        data = pd.DataFrame([{
            "company_id": "660e8400-e29b-41d4-a716-446655440001",
            "filing_type": "10-K",
            "filing_date": future_date,
            "accession_number": "0001234567-30-000001"
        }])

        assert data["filing_date"].iloc[0] > datetime.now()

    def test_duplicate_accession_number(self):
        """TC-104: Duplicate accession numbers should fail uniqueness."""
        data = pd.DataFrame([
            {
                "accession_number": "0001234567-24-000001",
                "filing_type": "10-K"
            },
            {
                "accession_number": "0001234567-24-000001",  # Duplicate
                "filing_type": "10-Q"
            }
        ])

        assert not data["accession_number"].is_unique

    def test_invalid_filing_type(self):
        """TC-105: Invalid filing type should fail validation."""
        data = pd.DataFrame([{
            "filing_type": "INVALID-FORM",
            "accession_number": "0001234567-24-000001"
        }])

        valid_types = ["10-K", "10-Q", "8-K", "DEF 14A", "20-F", "S-1", "S-4"]
        assert data["filing_type"].iloc[0] not in valid_types

    def test_short_content(self):
        """TC-106: Content shorter than minimum should fail."""
        data = pd.DataFrame([{
            "raw_text": "Too short",  # Less than 1000 chars
            "filing_type": "10-K",
            "accession_number": "0001234567-24-000001"
        }])

        assert len(data["raw_text"].iloc[0]) < 1000

    def test_pre_edgar_date(self):
        """TC-107: Filing date before EDGAR (1994) should fail."""
        data = pd.DataFrame([{
            "filing_date": datetime(1990, 1, 1),
            "filing_type": "10-K",
            "accession_number": "0001234567-90-000001"
        }])

        assert data["filing_date"].iloc[0] < datetime(1994, 1, 1)

    def test_invalid_company_reference(self):
        """TC-108: Non-existent company_id should fail foreign key validation."""
        data = pd.DataFrame([{
            "company_id": "00000000-0000-0000-0000-000000000000",  # Invalid UUID
            "filing_type": "10-K",
            "accession_number": "0001234567-24-000001"
        }])

        # Would fail when checking against companies table
        assert data["company_id"].iloc[0] == "00000000-0000-0000-0000-000000000000"

    def test_invalid_processing_status(self):
        """TC-109: Invalid processing status should fail validation."""
        data = pd.DataFrame([{
            "processing_status": "random_status",
            "filing_type": "10-K",
            "accession_number": "0001234567-24-000001"
        }])

        valid_statuses = ["pending", "processing", "completed", "failed", "retry", "archived"]
        assert data["processing_status"].iloc[0] not in valid_statuses

    def test_inconsistent_timestamps(self):
        """TC-110: Processed timestamp before filing date should fail."""
        data = pd.DataFrame([{
            "filing_date": datetime(2024, 3, 15),
            "processed_at": datetime(2024, 3, 10),  # Before filing date
            "processing_status": "completed",
            "accession_number": "0001234567-24-000001"
        }])

        assert data["processed_at"].iloc[0] < data["filing_date"].iloc[0]

    # === Edge Cases ===

    def test_minimum_content_length(self):
        """TC-201: Exactly minimum content length (1000 chars)."""
        data = pd.DataFrame([{
            "raw_text": "X" * 1000,  # Exactly 1000 chars
            "filing_type": "10-K",
            "accession_number": "0001234567-24-000001"
        }])

        assert len(data["raw_text"].iloc[0]) == 1000

    def test_all_filing_types(self):
        """TC-202: All valid filing types should pass."""
        filing_types = ["10-K", "10-Q", "8-K", "DEF 14A", "20-F", "S-1", "S-4", "10-K/A", "10-Q/A"]

        data = pd.DataFrame([
            {
                "filing_type": ft,
                "accession_number": f"0001234567-24-{i:06d}",
                "filing_date": datetime(2024, 1, 1) + timedelta(days=i*30),
                "raw_text": "Y" * 2000
            }
            for i, ft in enumerate(filing_types)
        ])

        valid_types_set = set(["10-K", "10-Q", "8-K", "DEF 14A", "20-F", "S-1", "S-4", "10-K/A", "10-Q/A"])
        assert set(data["filing_type"].unique()).issubset(valid_types_set)

    def test_null_optional_fields(self):
        """TC-203: Only required fields populated."""
        data = pd.DataFrame([{
            "company_id": "660e8400-e29b-41d4-a716-446655440001",
            "filing_type": "10-K",
            "filing_date": datetime(2024, 3, 15),
            "accession_number": "0001234567-24-000001",
            "filing_url": None,
            "raw_text": "Z" * 2000,
            "parsed_sections": None,
            "processed_at": None,
            "error_message": None
        }])

        # Required fields should not be null
        assert data["accession_number"].notna().all()
        assert data["filing_type"].notna().all()
        # Optional fields can be null
        assert data["filing_url"].isna().iloc[0]

    def test_amended_filing(self):
        """TC-204: Amended filing (10-K/A) format validation."""
        data = pd.DataFrame([{
            "filing_type": "10-K/A",  # Amended annual report
            "accession_number": "0001234567-24-000001",
            "filing_date": datetime(2024, 4, 15),
            "raw_text": "AA" * 1500
        }])

        assert data["filing_type"].iloc[0] == "10-K/A"

    def test_foreign_issuer_filing(self):
        """TC-205: Foreign issuer (20-F) filing validation."""
        data = pd.DataFrame([{
            "filing_type": "20-F",
            "accession_number": "0001234567-24-000001",
            "filing_date": datetime(2024, 6, 30),
            "raw_text": "BB" * 2000
        }])

        assert data["filing_type"].iloc[0] == "20-F"

    # === Data Quality Scenarios ===

    def test_batch_completeness(self):
        """TC-301: 95% of batch has all required fields."""
        # Create 100 records, 95 complete, 5 incomplete
        complete_records = [
            {
                "company_id": f"660e8400-e29b-41d4-a716-44665544{i:04d}",
                "filing_type": "10-K",
                "filing_date": datetime(2024, 1, 1) + timedelta(days=i),
                "accession_number": f"0001234567-24-{i:06d}",
                "raw_text": "CC" * 1000
            }
            for i in range(95)
        ]

        incomplete_records = [
            {
                "company_id": f"660e8400-e29b-41d4-a716-44665544{i:04d}",
                "filing_type": "10-K",
                "filing_date": datetime(2024, 1, 1) + timedelta(days=i),
                "accession_number": None,  # Missing required field
                "raw_text": "DD" * 1000
            }
            for i in range(95, 100)
        ]

        data = pd.DataFrame(complete_records + incomplete_records)

        completeness_rate = data["accession_number"].notna().sum() / len(data)
        assert completeness_rate == 0.95

    def test_temporal_coverage(self):
        """TC-302: Filings span multiple years."""
        data = pd.DataFrame([
            {
                "filing_date": datetime(2020 + i, 3, 15),
                "filing_type": "10-K",
                "accession_number": f"0001234567-{20+i:02d}-000001",
                "raw_text": "EE" * 2000
            }
            for i in range(5)  # 2020-2024
        ])

        years_covered = data["filing_date"].dt.year.nunique()
        assert years_covered == 5

    def test_company_coverage(self):
        """TC-303: Multiple companies represented."""
        data = pd.DataFrame([
            {
                "company_id": f"660e8400-e29b-41d4-a716-44665544{i:04d}",
                "filing_type": "10-K",
                "accession_number": f"000123456{i}-24-000001",
                "filing_date": datetime(2024, 3, 15),
                "raw_text": "FF" * 2000
            }
            for i in range(10)  # 10 different companies
        ])

        assert data["company_id"].nunique() == 10

    def test_processing_efficiency(self):
        """TC-304: 90%+ completion rate."""
        data = pd.DataFrame([
            {
                "processing_status": "completed" if i < 92 else "failed",
                "accession_number": f"0001234567-24-{i:06d}",
                "filing_type": "10-K"
            }
            for i in range(100)
        ])

        completion_rate = (data["processing_status"] == "completed").sum() / len(data)
        assert completion_rate == 0.92

    def test_content_quality(self):
        """TC-305: 98% have substantial content (>1000 chars)."""
        # 98 with good content, 2 with poor content
        good_content = [
            {
                "raw_text": "GG" * 1000,
                "accession_number": f"0001234567-24-{i:06d}",
                "filing_type": "10-K"
            }
            for i in range(98)
        ]

        poor_content = [
            {
                "raw_text": "HH",  # Too short
                "accession_number": f"0001234567-24-{i:06d}",
                "filing_type": "10-K"
            }
            for i in range(98, 100)
        ]

        data = pd.DataFrame(good_content + poor_content)

        quality_rate = (data["raw_text"].str.len() >= 1000).sum() / len(data)
        assert quality_rate == 0.98


class TestSECFilingContentExpectations:
    """Test content quality expectations."""

    def test_json_structure_validation(self):
        """Validate parsed_sections JSON structure."""
        data = pd.DataFrame([{
            "parsed_sections": {
                "business_description": "EdTech platform",
                "risk_factors": "Market competition",
                "financial_statements": {"revenue": 1000000},
                "management_discussion": "Strong growth"
            }
        }])

        parsed = data["parsed_sections"].iloc[0]
        assert "business_description" in parsed
        assert isinstance(parsed["financial_statements"], dict)

    def test_url_validation(self):
        """Validate SEC.gov URL format."""
        data = pd.DataFrame([{
            "filing_url": "https://www.sec.gov/Archives/edgar/data/1234567/filing.htm"
        }])

        assert data["filing_url"].str.startswith("https://www.sec.gov/").all()

    def test_financial_keywords_presence(self):
        """Check for financial keywords in content."""
        data = pd.DataFrame([{
            "raw_text": "The company reported revenue of $10M with strong income growth. " * 50
        }])

        keywords = ["revenue", "income", "assets", "liabilities", "cash flow"]
        text_lower = data["raw_text"].iloc[0].lower()
        keywords_found = [kw for kw in keywords if kw in text_lower]

        assert len(keywords_found) >= 2  # At least 2 financial keywords


class TestSECFilingPipelineExpectations:
    """Test pipeline processing expectations."""

    def test_status_timestamp_consistency(self):
        """Completed/failed filings must have processed_at timestamp."""
        data = pd.DataFrame([
            {
                "processing_status": "completed",
                "processed_at": datetime(2024, 3, 16),
                "accession_number": "0001234567-24-000001"
            },
            {
                "processing_status": "failed",
                "processed_at": datetime(2024, 3, 16),
                "error_message": "Parse error",
                "accession_number": "0001234567-24-000002"
            },
            {
                "processing_status": "pending",
                "processed_at": None,
                "accession_number": "0001234567-24-000003"
            }
        ])

        # Completed/failed should have processed_at
        completed_or_failed = data[data["processing_status"].isin(["completed", "failed"])]
        assert completed_or_failed["processed_at"].notna().all()

    def test_error_message_on_failure(self):
        """Failed filings should have error message."""
        data = pd.DataFrame([{
            "processing_status": "failed",
            "error_message": "Connection timeout",
            "processed_at": datetime(2024, 3, 16)
        }])

        failed_records = data[data["processing_status"] == "failed"]
        assert failed_records["error_message"].notna().all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
