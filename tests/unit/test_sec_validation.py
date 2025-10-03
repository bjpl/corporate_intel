"""Comprehensive tests for SEC filing validation functions."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.validation.data_quality import (
    DataQualityValidator,
    SECFilingSchema,
    FinancialMetricsSchema
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def validator():
    """Create a DataQualityValidator instance for testing."""
    return DataQualityValidator()


@pytest.fixture
def valid_sec_filing():
    """Sample valid SEC filing data."""
    return {
        "company_id": "test-company-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345",
        "content": "Annual Report\n\n" + "Financial Data: " * 500 +
                  "Revenue: $1,000,000\nNet Income: $200,000\n" +
                  "Assets: $5,000,000\nLiabilities: $2,000,000\n" +
                  "Cash Flow: $300,000\n" + "<table><tr><td>Q1</td></tr></table>"
    }


@pytest.fixture
def valid_sec_filing_dataframe():
    """Sample valid SEC filing dataframe."""
    return pd.DataFrame([
        {
            "company_id": "DUOL-001",
            "filing_type": "10-K",
            "filing_date": pd.Timestamp("2024-03-15"),
            "accession_number": "0001234567-89-012345",
            "content_length": 50000
        },
        {
            "company_id": "DUOL-001",
            "filing_type": "10-Q",
            "filing_date": pd.Timestamp("2024-06-15"),
            "accession_number": "0001234567-89-012346",
            "content_length": 25000
        },
        {
            "company_id": "DUOL-001",
            "filing_type": "8-K",
            "filing_date": pd.Timestamp("2024-08-20"),
            "accession_number": "0001234567-89-012347",
            "content_length": 5000
        }
    ])


@pytest.fixture
def valid_financial_metrics_dataframe():
    """Sample valid financial metrics dataframe."""
    return pd.DataFrame([
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-Q1"),
            "metric_type": "revenue",
            "value": 500000000.0,
            "unit": "USD",
            "confidence_score": 0.95
        },
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-Q1"),
            "metric_type": "monthly_active_users",
            "value": 100000000.0,
            "unit": "count",
            "confidence_score": 0.90
        },
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-Q1"),
            "metric_type": "gross_margin",
            "value": 70.5,
            "unit": "percent",
            "confidence_score": 0.88
        }
    ])


# ============================================================================
# VALID DATA TESTS
# ============================================================================

def test_valid_sec_filing_passes_validation(validator, valid_sec_filing):
    """Test that valid SEC filing data passes all validation checks."""
    result = validator.validate_sec_filing(valid_sec_filing)

    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["has_tables"] is True


def test_valid_sec_filing_dataframe_passes_pandera(valid_sec_filing_dataframe):
    """Test that valid SEC filing dataframe passes Pandera schema validation."""
    try:
        validated_df = SECFilingSchema.validate(valid_sec_filing_dataframe)
        assert len(validated_df) == 3
    except Exception as e:
        pytest.fail(f"Valid dataframe failed validation: {e}")


def test_valid_financial_metrics_passes_validation(validator, valid_financial_metrics_dataframe):
    """Test that valid financial metrics pass validation."""
    result = validator.validate_financial_metrics(valid_financial_metrics_dataframe)

    assert result["pandera_valid"] is True
    assert len(result["pandera_errors"]) == 0
    assert result["row_count"] == 3
    assert result["unique_companies"] == 1


# ============================================================================
# INVALID CIK/ACCESSION NUMBER FORMAT TESTS
# ============================================================================

def test_invalid_accession_number_format_fails(validator):
    """Test that invalid accession number format fails validation."""
    invalid_filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "invalid-format-123",  # Invalid format
        "content": "Test content " * 200
    }

    result = validator.validate_sec_filing(invalid_filing)

    assert result["valid"] is False
    assert any("accession number" in error.lower() for error in result["errors"])


def test_missing_accession_number_fails(validator):
    """Test that missing accession number fails validation."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "content": "Test content " * 200
        # Missing accession_number
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert any("accession_number" in error for error in result["errors"])


def test_dataframe_invalid_accession_format_fails():
    """Test that dataframe with invalid accession number format fails."""
    invalid_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "filing_type": "10-K",
        "filing_date": pd.Timestamp("2024-03-15"),
        "accession_number": "123-45-6789",  # Wrong format (should be 10-2-6)
        "content_length": 50000
    }])

    with pytest.raises(Exception):  # Pandera will raise SchemaErrors
        SECFilingSchema.validate(invalid_df)


# ============================================================================
# MISSING REQUIRED FIELDS TESTS
# ============================================================================

def test_missing_filing_type_fails(validator):
    """Test that missing filing_type field fails validation."""
    filing = {
        "company_id": "test-123",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345",
        "content": "Test content " * 200
        # Missing filing_type
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert any("filing_type" in error for error in result["errors"])


def test_missing_content_fails(validator):
    """Test that missing content field fails validation."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345"
        # Missing content
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert any("content" in error for error in result["errors"])


def test_missing_filing_date_fails(validator):
    """Test that missing filing_date field fails validation."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "accession_number": "0001234567-89-012345",
        "content": "Test content " * 200
        # Missing filing_date
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert any("filing_date" in error for error in result["errors"])


def test_multiple_missing_fields_reported(validator):
    """Test that multiple missing fields are all reported."""
    filing = {
        "company_id": "test-123"
        # Missing: filing_type, filing_date, accession_number, content
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert len(result["errors"]) >= 4  # Should report all missing fields


# ============================================================================
# INVALID FORM TYPES TESTS
# ============================================================================

def test_invalid_filing_type_fails():
    """Test that invalid filing type fails Pandera validation."""
    invalid_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "filing_type": "INVALID-FORM",  # Not in allowed set
        "filing_date": pd.Timestamp("2024-03-15"),
        "accession_number": "0001234567-89-012345",
        "content_length": 50000
    }])

    with pytest.raises(Exception):  # Pandera SchemaErrors
        SECFilingSchema.validate(invalid_df)


def test_only_valid_form_types_accepted():
    """Test that only specific form types are accepted."""
    valid_types = ["10-K", "10-Q", "8-K", "DEF 14A", "20-F", "S-1", "S-4"]

    for form_type in valid_types:
        df = pd.DataFrame([{
            "company_id": "DUOL-001",
            "filing_type": form_type,
            "filing_date": pd.Timestamp("2024-03-15"),
            "accession_number": "0001234567-89-012345",
            "content_length": 50000
        }])

        try:
            SECFilingSchema.validate(df)
        except Exception as e:
            pytest.fail(f"Valid form type {form_type} failed validation: {e}")


# ============================================================================
# INVALID DATE FORMAT TESTS
# ============================================================================

def test_future_filing_date_fails(validator):
    """Test that filing date in the future fails validation."""
    future_date = (datetime.now() + timedelta(days=365)).isoformat()
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": future_date,
        "accession_number": "0001234567-89-012345",
        "content": "Test content " * 200
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert any("future" in error.lower() for error in result["errors"])


def test_pre_edgar_filing_date_warning(validator):
    """Test that filing date before EDGAR (1994) generates warning."""
    old_date = "1990-01-01T00:00:00"
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": old_date,
        "accession_number": "0001234567-89-012345",
        "content": "Test content " * 200
    }

    result = validator.validate_sec_filing(filing)

    assert any("1994" in warning or "EDGAR" in warning for warning in result["warnings"])


def test_invalid_date_string_fails(validator):
    """Test that invalid date string format fails validation."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": "not-a-valid-date",
        "accession_number": "0001234567-89-012345",
        "content": "Test content " * 200
    }

    result = validator.validate_sec_filing(filing)

    assert result["valid"] is False
    assert any("date" in error.lower() for error in result["errors"])


def test_dataframe_filing_date_boundaries():
    """Test that dataframe enforces filing date boundaries."""
    # Test future date
    future_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "filing_type": "10-K",
        "filing_date": pd.Timestamp.now() + pd.Timedelta(days=30),
        "accession_number": "0001234567-89-012345",
        "content_length": 50000
    }])

    with pytest.raises(Exception):
        SECFilingSchema.validate(future_df)

    # Test pre-EDGAR date
    old_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "filing_type": "10-K",
        "filing_date": pd.Timestamp("1990-01-01"),
        "accession_number": "0001234567-89-012345",
        "content_length": 50000
    }])

    with pytest.raises(Exception):
        SECFilingSchema.validate(old_df)


# ============================================================================
# EDGE CASES - EMPTY DATA
# ============================================================================

def test_empty_filing_data_fails(validator):
    """Test that empty filing data dictionary fails validation."""
    result = validator.validate_sec_filing({})

    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_empty_dataframe_validation():
    """Test validation behavior with empty dataframe."""
    empty_df = pd.DataFrame()

    # Empty dataframe should fail schema validation
    with pytest.raises(Exception):
        SECFilingSchema.validate(empty_df)


def test_empty_content_string_generates_warning(validator):
    """Test that empty content string is flagged."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345",
        "content": ""
    }

    result = validator.validate_sec_filing(filing)

    # Should fail on missing content or generate warning
    assert result["valid"] is False or len(result["warnings"]) > 0


def test_null_values_in_dataframe_fail():
    """Test that null values in required fields fail validation."""
    null_df = pd.DataFrame([{
        "company_id": None,  # Required field
        "filing_type": "10-K",
        "filing_date": pd.Timestamp("2024-03-15"),
        "accession_number": "0001234567-89-012345",
        "content_length": 50000
    }])

    with pytest.raises(Exception):
        SECFilingSchema.validate(null_df)


# ============================================================================
# EDGE CASES - MALFORMED DATA
# ============================================================================

def test_malformed_content_minimal_length(validator):
    """Test that content with insufficient length generates warning."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345",
        "content": "Short"  # Very short content
    }

    result = validator.validate_sec_filing(filing)

    assert any("short" in warning.lower() for warning in result["warnings"])


def test_content_without_financial_keywords_warning(validator):
    """Test that content without financial keywords generates warning."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345",
        "content": "Lorem ipsum dolor sit amet " * 200  # No financial keywords
    }

    result = validator.validate_sec_filing(filing)

    assert any("financial" in warning.lower() or "keyword" in warning.lower()
               for warning in result["warnings"])


def test_content_without_tables_warning(validator):
    """Test that content without tables generates warning."""
    filing = {
        "company_id": "test-123",
        "filing_type": "10-K",
        "filing_date": datetime.now().isoformat(),
        "accession_number": "0001234567-89-012345",
        "content": "Revenue: $1M, Income: $200K " * 100  # No tables
    }

    result = validator.validate_sec_filing(filing)

    assert result["has_tables"] is False
    assert any("table" in warning.lower() for warning in result["warnings"])


def test_content_length_below_minimum():
    """Test that content length below minimum fails validation."""
    short_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "filing_type": "10-K",
        "filing_date": pd.Timestamp("2024-03-15"),
        "accession_number": "0001234567-89-012345",
        "content_length": 50  # Below minimum of 100
    }])

    with pytest.raises(Exception):
        SECFilingSchema.validate(short_df)


def test_mixed_valid_invalid_rows():
    """Test dataframe with mix of valid and invalid rows."""
    mixed_df = pd.DataFrame([
        {  # Valid row
            "company_id": "DUOL-001",
            "filing_type": "10-K",
            "filing_date": pd.Timestamp("2024-03-15"),
            "accession_number": "0001234567-89-012345",
            "content_length": 50000
        },
        {  # Invalid row - bad form type
            "company_id": "DUOL-002",
            "filing_type": "INVALID",
            "filing_date": pd.Timestamp("2024-03-15"),
            "accession_number": "0001234567-89-012346",
            "content_length": 50000
        }
    ])

    with pytest.raises(Exception):
        SECFilingSchema.validate(mixed_df)


# ============================================================================
# TICKER VALIDATION TESTS
# ============================================================================

def test_invalid_ticker_format_fails():
    """Test that invalid ticker format fails validation."""
    invalid_ticker_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "invalid_ticker_123",  # Should be 1-5 uppercase letters
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "revenue",
        "value": 500000000.0,
        "unit": "USD",
        "confidence_score": 0.95
    }])

    with pytest.raises(Exception):
        FinancialMetricsSchema.validate(invalid_ticker_df)


def test_ticker_length_validation():
    """Test ticker length constraints (1-5 characters)."""
    # Too long
    long_ticker_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "TOOLONG",  # 7 characters
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "revenue",
        "value": 500000000.0,
        "unit": "USD",
        "confidence_score": 0.95
    }])

    with pytest.raises(Exception):
        FinancialMetricsSchema.validate(long_ticker_df)

    # Valid single character
    single_char_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "X",
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "revenue",
        "value": 500000000.0,
        "unit": "USD",
        "confidence_score": 0.95
    }])

    try:
        FinancialMetricsSchema.validate(single_char_df)
    except Exception as e:
        pytest.fail(f"Valid single-character ticker failed: {e}")


# ============================================================================
# FINANCIAL METRICS BOUNDARY TESTS
# ============================================================================

def test_negative_values_fail_validation():
    """Test that negative values in metrics fail validation."""
    negative_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "DUOL",
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "revenue",
        "value": -100000.0,  # Negative value
        "unit": "USD",
        "confidence_score": 0.95
    }])

    with pytest.raises(Exception):
        FinancialMetricsSchema.validate(negative_df)


def test_unreasonable_nrr_values_fail():
    """Test that net revenue retention outside 50-200% fails."""
    invalid_nrr_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "DUOL",
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "net_revenue_retention",
        "value": 300.0,  # Above 200%
        "unit": "percent",
        "confidence_score": 0.95
    }])

    with pytest.raises(Exception):
        FinancialMetricsSchema.validate(invalid_nrr_df)


def test_unreasonable_churn_rate_fails():
    """Test that churn rate above 50% fails validation."""
    invalid_churn_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "DUOL",
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "churn_rate",
        "value": 75.0,  # Above 50%
        "unit": "percent",
        "confidence_score": 0.95
    }])

    with pytest.raises(Exception):
        FinancialMetricsSchema.validate(invalid_churn_df)


def test_gross_margin_percentage_bounds():
    """Test that gross margin is constrained to 0-100%."""
    # Over 100%
    invalid_margin_df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "ticker": "DUOL",
        "metric_date": pd.Timestamp("2024-Q1"),
        "metric_type": "gross_margin",
        "value": 150.0,  # Above 100%
        "unit": "percent",
        "confidence_score": 0.95
    }])

    with pytest.raises(Exception):
        FinancialMetricsSchema.validate(invalid_margin_df)


# ============================================================================
# ANOMALY DETECTION TESTS
# ============================================================================

def test_anomaly_detection_large_change(validator):
    """Test that large metric changes are detected as anomalies."""
    df_with_anomaly = pd.DataFrame([
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-01-01"),
            "metric_type": "revenue",
            "value": 100000000.0,
            "unit": "USD",
            "confidence_score": 0.95
        },
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-04-01"),
            "metric_type": "revenue",
            "value": 200000000.0,  # 100% increase
            "unit": "USD",
            "confidence_score": 0.95
        }
    ])

    result = validator.validate_financial_metrics(df_with_anomaly)

    assert "anomalies" in result
    assert len(result["anomalies"]) > 0
    assert result["anomalies"][0]["change_pct"] == 100.0


def test_no_anomaly_for_normal_growth(validator):
    """Test that normal growth doesn't trigger anomaly detection."""
    normal_df = pd.DataFrame([
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-01-01"),
            "metric_type": "revenue",
            "value": 100000000.0,
            "unit": "USD",
            "confidence_score": 0.95
        },
        {
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-04-01"),
            "metric_type": "revenue",
            "value": 120000000.0,  # 20% increase - normal
            "unit": "USD",
            "confidence_score": 0.95
        }
    ])

    result = validator.validate_financial_metrics(normal_df)

    if "anomalies" in result:
        assert len(result["anomalies"]) == 0


# ============================================================================
# VALIDATION REPORT TESTS
# ============================================================================

def test_validation_report_generation(validator):
    """Test that validation report is properly formatted."""
    validation_results = {
        "sec_filing": {
            "valid": False,
            "errors": ["Invalid accession number"],
            "warnings": ["Content too short"]
        },
        "financial_metrics": {
            "valid": True,
            "errors": [],
            "warnings": []
        }
    }

    report = validator.create_validation_report(validation_results)

    assert "DATA QUALITY VALIDATION REPORT" in report
    assert "SEC_FILING" in report
    assert "FINANCIAL_METRICS" in report
    assert "Invalid accession number" in report
    assert "Content too short" in report


def test_empty_validation_report(validator):
    """Test validation report with no issues."""
    validation_results = {
        "test": {
            "valid": True,
            "errors": [],
            "warnings": []
        }
    }

    report = validator.create_validation_report(validation_results)

    assert "Total Issues Found: 0" in report
    assert "✅ VALID" in report


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_validation_pipeline(validator, valid_sec_filing):
    """Test complete validation pipeline from filing to report."""
    # Validate filing
    filing_result = validator.validate_sec_filing(valid_sec_filing)

    # Create metrics from filing
    metrics_df = pd.DataFrame([{
        "company_id": valid_sec_filing["company_id"],
        "ticker": "DUOL",
        "metric_date": pd.Timestamp(valid_sec_filing["filing_date"]),
        "metric_type": "revenue",
        "value": 500000000.0,
        "unit": "USD",
        "confidence_score": 0.95
    }])

    # Validate metrics
    metrics_result = validator.validate_financial_metrics(metrics_df)

    # Generate report
    results = {
        "sec_filing": filing_result,
        "financial_metrics": metrics_result
    }
    report = validator.create_validation_report(results)

    assert filing_result["valid"] is True
    assert metrics_result["pandera_valid"] is True
    assert "DATA QUALITY VALIDATION REPORT" in report


def test_validator_initialization():
    """Test that validator initializes properly with all components."""
    validator = DataQualityValidator()

    assert validator.context is not None
    assert validator.expectations is not None
    assert "financial_metrics" in validator.expectations
    assert "sec_filings" in validator.expectations
    assert "documents" in validator.expectations


@pytest.mark.parametrize("filing_type", ["10-K", "10-Q", "8-K", "DEF 14A", "20-F", "S-1", "S-4"])
def test_all_valid_filing_types_accepted(filing_type):
    """Parametrized test for all valid filing types."""
    df = pd.DataFrame([{
        "company_id": "DUOL-001",
        "filing_type": filing_type,
        "filing_date": pd.Timestamp("2024-03-15"),
        "accession_number": "0001234567-89-012345",
        "content_length": 50000
    }])

    try:
        SECFilingSchema.validate(df)
    except Exception as e:
        pytest.fail(f"Valid filing type {filing_type} failed validation: {e}")


@pytest.mark.parametrize("metric_type,valid_range", [
    ("net_revenue_retention", (50, 200)),
    ("churn_rate", (0, 50)),
    ("gross_margin", (0, 100))
])
def test_metric_type_ranges(metric_type, valid_range):
    """Parametrized test for metric type value ranges."""
    min_val, max_val = valid_range

    # Test valid boundary values
    for value in [min_val, max_val]:
        df = pd.DataFrame([{
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-Q1"),
            "metric_type": metric_type,
            "value": float(value),
            "unit": "percent",
            "confidence_score": 0.95
        }])

        try:
            FinancialMetricsSchema.validate(df)
        except Exception as e:
            pytest.fail(f"Boundary value {value} for {metric_type} failed: {e}")

    # Test invalid values outside range
    invalid_values = [min_val - 10, max_val + 10]
    for value in invalid_values:
        df = pd.DataFrame([{
            "company_id": "DUOL-001",
            "ticker": "DUOL",
            "metric_date": pd.Timestamp("2024-Q1"),
            "metric_type": metric_type,
            "value": float(value),
            "unit": "percent",
            "confidence_score": 0.95
        }])

        with pytest.raises(Exception):
            FinancialMetricsSchema.validate(df)
