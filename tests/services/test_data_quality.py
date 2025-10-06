"""Comprehensive tests for DataQualityValidator - validation, anomalies, schemas."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.validation.data_quality import (
    DataQualityValidator,
    FinancialMetricsSchema,
    SECFilingSchema
)


@pytest.fixture
def validator():
    """Create DataQualityValidator instance."""
    return DataQualityValidator()


@pytest.fixture
def valid_financial_metrics():
    """Create valid financial metrics DataFrame."""
    return pd.DataFrame({
        'company_id': ['uuid-1', 'uuid-2', 'uuid-3'],
        'ticker': ['DUOL', 'CHGG', 'COUR'],
        'metric_date': [datetime(2025, 1, 1), datetime(2025, 1, 1), datetime(2025, 1, 1)],
        'metric_type': ['revenue', 'monthly_active_users', 'net_revenue_retention'],
        'value': [484.2e6, 83.1e6, 124.0],
        'unit': ['USD', 'count', 'percent'],
        'confidence_score': [0.95, 0.88, 0.92]
    })


@pytest.fixture
def valid_sec_filing():
    """Create valid SEC filing data."""
    return {
        'company_id': 'uuid-1',
        'filing_type': '10-K',
        'filing_date': datetime(2024, 12, 31),
        'accession_number': '0001234567-24-000001',
        'content': 'Revenue increased to $484.2 million. Income statement shows assets of $1.2 billion and liabilities of $500 million. Cash flow from operations was positive.'
    }


class TestFinancialMetricsValidation:
    """Tests for financial metrics validation."""

    def test_validate_valid_metrics(self, validator, valid_financial_metrics):
        """Test validation of valid financial metrics."""
        result = validator.validate_financial_metrics(valid_financial_metrics)

        assert result['pandera_valid'] is True
        assert len(result['pandera_errors']) == 0
        assert result['row_count'] == 3
        assert result['unique_companies'] == 3

    def test_validate_missing_required_field(self, validator, valid_financial_metrics):
        """Test validation fails with missing required field."""
        df = valid_financial_metrics.drop(columns=['company_id'])

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False
        assert len(result['pandera_errors']) > 0

    def test_validate_invalid_ticker_format(self, validator, valid_financial_metrics):
        """Test validation fails with invalid ticker format."""
        df = valid_financial_metrics.copy()
        df.loc[0, 'ticker'] = 'invalid_ticker'  # Should be uppercase, 1-5 chars

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False

    def test_validate_negative_value(self, validator, valid_financial_metrics):
        """Test validation fails with negative value."""
        df = valid_financial_metrics.copy()
        df.loc[0, 'value'] = -1000

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False

    def test_validate_invalid_metric_type(self, validator, valid_financial_metrics):
        """Test validation fails with invalid metric type."""
        df = valid_financial_metrics.copy()
        df.loc[0, 'metric_type'] = 'invalid_metric'

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False

    def test_validate_invalid_unit(self, validator, valid_financial_metrics):
        """Test validation fails with invalid unit."""
        df = valid_financial_metrics.copy()
        df.loc[0, 'unit'] = 'invalid_unit'

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False

    def test_validate_confidence_score_bounds(self, validator, valid_financial_metrics):
        """Test validation enforces confidence score bounds (0-1)."""
        df = valid_financial_metrics.copy()
        df.loc[0, 'confidence_score'] = 1.5  # Invalid, should be <= 1

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False

    def test_validate_reasonable_nrr(self, validator, valid_financial_metrics):
        """Test validation of reasonable NRR values (50-200%)."""
        df = pd.DataFrame({
            'company_id': ['uuid-1', 'uuid-2'],
            'ticker': ['DUOL', 'CHGG'],
            'metric_date': [datetime(2025, 1, 1), datetime(2025, 1, 1)],
            'metric_type': ['net_revenue_retention', 'net_revenue_retention'],
            'value': [124.0, 250.0],  # Second value unreasonable
            'unit': ['percent', 'percent'],
            'confidence_score': [0.9, 0.9]
        })

        result = validator.validate_financial_metrics(df)

        # Custom check should flag unreasonable NRR
        assert result['pandera_valid'] is False

    def test_validate_churn_rate_bounds(self, validator):
        """Test validation of churn rate bounds (0-50%)."""
        df = pd.DataFrame({
            'company_id': ['uuid-1'],
            'ticker': ['DUOL'],
            'metric_date': [datetime(2025, 1, 1)],
            'metric_type': ['churn_rate'],
            'value': [75.0],  # Unreasonable churn rate
            'unit': ['percent'],
            'confidence_score': [0.9]
        })

        result = validator.validate_financial_metrics(df)

        assert result['pandera_valid'] is False

    def test_validate_date_range(self, validator, valid_financial_metrics):
        """Test date range reporting."""
        df = valid_financial_metrics.copy()
        df.loc[1, 'metric_date'] = datetime(2024, 6, 30)
        df.loc[2, 'metric_date'] = datetime(2025, 3, 31)

        result = validator.validate_financial_metrics(df)

        assert 'date_range' in result
        assert result['date_range']['min'] == datetime(2024, 6, 30)
        assert result['date_range']['max'] == datetime(2025, 3, 31)


class TestAnomalyDetection:
    """Tests for anomaly detection in financial metrics."""

    def test_detect_sudden_increase_anomaly(self, validator):
        """Test detection of sudden metric increase (>50%)."""
        df = pd.DataFrame({
            'company_id': ['uuid-1', 'uuid-1', 'uuid-1'],
            'ticker': ['DUOL', 'DUOL', 'DUOL'],
            'metric_date': [
                datetime(2024, 9, 30),
                datetime(2024, 12, 31),
                datetime(2025, 3, 31)
            ],
            'metric_type': ['revenue', 'revenue', 'revenue'],
            'value': [100e6, 120e6, 250e6],  # >100% increase
            'unit': ['USD', 'USD', 'USD'],
            'confidence_score': [0.9, 0.9, 0.9]
        })

        result = validator.validate_financial_metrics(df)

        assert 'anomalies' in result
        assert len(result['anomalies']) > 0
        assert result['anomalies'][0]['severity'] == 'high'
        assert result['anomalies'][0]['metric_type'] == 'revenue'

    def test_detect_sudden_decrease_anomaly(self, validator):
        """Test detection of sudden metric decrease (>50%)."""
        df = pd.DataFrame({
            'company_id': ['uuid-1', 'uuid-1'],
            'ticker': ['DUOL', 'DUOL'],
            'metric_date': [datetime(2024, 12, 31), datetime(2025, 3, 31)],
            'metric_type': ['revenue', 'revenue'],
            'value': [200e6, 80e6],  # >50% decrease
            'unit': ['USD', 'USD'],
            'confidence_score': [0.9, 0.9]
        })

        result = validator.validate_financial_metrics(df)

        assert 'anomalies' in result
        assert abs(result['anomalies'][0]['change_pct']) > 50

    def test_no_anomalies_gradual_change(self, validator):
        """Test no anomalies detected for gradual changes."""
        df = pd.DataFrame({
            'company_id': ['uuid-1'] * 4,
            'ticker': ['DUOL'] * 4,
            'metric_date': [
                datetime(2024, 3, 31),
                datetime(2024, 6, 30),
                datetime(2024, 9, 30),
                datetime(2024, 12, 31)
            ],
            'metric_type': ['revenue'] * 4,
            'value': [100e6, 110e6, 120e6, 130e6],  # ~10% growth each quarter
            'unit': ['USD'] * 4,
            'confidence_score': [0.9] * 4
        })

        result = validator.validate_financial_metrics(df)

        assert 'anomalies' not in result or len(result['anomalies']) == 0

    def test_multiple_companies_anomaly_detection(self, validator):
        """Test anomaly detection across multiple companies."""
        df = pd.DataFrame({
            'company_id': ['uuid-1', 'uuid-1', 'uuid-2', 'uuid-2'],
            'ticker': ['DUOL', 'DUOL', 'CHGG', 'CHGG'],
            'metric_date': [
                datetime(2024, 12, 31),
                datetime(2025, 3, 31),
                datetime(2024, 12, 31),
                datetime(2025, 3, 31)
            ],
            'metric_type': ['revenue', 'revenue', 'revenue', 'revenue'],
            'value': [100e6, 180e6, 200e6, 210e6],  # DUOL has anomaly
            'unit': ['USD'] * 4,
            'confidence_score': [0.9] * 4
        })

        result = validator.validate_financial_metrics(df)

        assert 'anomalies' in result
        # Should only detect anomaly for DUOL
        duol_anomalies = [a for a in result['anomalies'] if a['company_id'] == 'uuid-1']
        assert len(duol_anomalies) > 0


class TestSECFilingValidation:
    """Tests for SEC filing validation."""

    def test_validate_valid_filing(self, validator, valid_sec_filing):
        """Test validation of valid SEC filing."""
        result = validator.validate_sec_filing(valid_sec_filing)

        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['has_tables'] is False  # Simple text content

    def test_validate_missing_required_field(self, validator, valid_sec_filing):
        """Test validation fails with missing required field."""
        filing = valid_sec_filing.copy()
        del filing['accession_number']

        result = validator.validate_sec_filing(filing)

        assert result['valid'] is False
        assert any('accession_number' in error for error in result['errors'])

    def test_validate_invalid_accession_format(self, validator, valid_sec_filing):
        """Test validation fails with invalid accession number format."""
        filing = valid_sec_filing.copy()
        filing['accession_number'] = 'invalid-format'

        result = validator.validate_sec_filing(filing)

        assert result['valid'] is False
        assert any('accession number format' in error for error in result['errors'])

    def test_validate_valid_accession_format(self, validator, valid_sec_filing):
        """Test validation passes with valid accession number format."""
        filing = valid_sec_filing.copy()
        filing['accession_number'] = '0001234567-24-123456'

        result = validator.validate_sec_filing(filing)

        assert result['valid'] is True

    def test_validate_content_too_short(self, validator, valid_sec_filing):
        """Test warning for suspiciously short content."""
        filing = valid_sec_filing.copy()
        filing['content'] = 'Too short'

        result = validator.validate_sec_filing(filing)

        assert any('suspiciously short' in warning for warning in result['warnings'])

    def test_validate_no_financial_keywords(self, validator, valid_sec_filing):
        """Test warning for missing financial keywords."""
        filing = valid_sec_filing.copy()
        filing['content'] = 'This is a long document but contains no financial information at all. ' * 50

        result = validator.validate_sec_filing(filing)

        assert any('financial keywords' in warning for warning in result['warnings'])

    def test_validate_future_filing_date(self, validator, valid_sec_filing):
        """Test validation fails with future filing date."""
        filing = valid_sec_filing.copy()
        filing['filing_date'] = datetime.utcnow() + timedelta(days=30)

        result = validator.validate_sec_filing(filing)

        assert result['valid'] is False
        assert any('future' in error for error in result['errors'])

    def test_validate_pre_edgar_date(self, validator, valid_sec_filing):
        """Test warning for filing date before EDGAR system (1994)."""
        filing = valid_sec_filing.copy()
        filing['filing_date'] = datetime(1990, 1, 1)

        result = validator.validate_sec_filing(filing)

        assert any('EDGAR' in warning for warning in result['warnings'])

    def test_validate_table_detection(self, validator, valid_sec_filing):
        """Test table detection in filing content."""
        filing = valid_sec_filing.copy()
        filing['content'] = '<table><tr><td>Revenue</td><td>$100M</td></tr></table>'

        result = validator.validate_sec_filing(filing)

        assert result['has_tables'] is True

    def test_validate_invalid_filing_date_format(self, validator, valid_sec_filing):
        """Test validation fails with invalid date format."""
        filing = valid_sec_filing.copy()
        filing['filing_date'] = 'not-a-date'

        result = validator.validate_sec_filing(filing)

        assert result['valid'] is False
        assert any('Invalid filing date' in error for error in result['errors'])


class TestEmbeddingValidation:
    """Tests for embedding quality validation."""

    def test_validate_valid_embeddings(self, validator):
        """Test validation of valid normalized embeddings."""
        # Create normalized embeddings
        embeddings = np.random.randn(10, 384)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        result = validator.validate_embeddings(embeddings)

        assert result['valid'] is True
        assert result['shape'] == (10, 384)
        assert len(result['issues']) == 0

    def test_validate_wrong_dimension(self, validator):
        """Test validation fails with wrong dimension."""
        embeddings = np.random.randn(10, 256)  # Wrong dimension

        result = validator.validate_embeddings(embeddings, expected_dim=384)

        assert result['valid'] is False
        assert any('Wrong dimension' in issue for issue in result['issues'])

    def test_validate_nan_values(self, validator):
        """Test validation fails with NaN values."""
        embeddings = np.random.randn(10, 384)
        embeddings[0, 0] = np.nan

        result = validator.validate_embeddings(embeddings)

        assert result['valid'] is False
        assert any('NaN' in issue for issue in result['issues'])

    def test_validate_inf_values(self, validator):
        """Test validation fails with infinite values."""
        embeddings = np.random.randn(10, 384)
        embeddings[0, 0] = np.inf

        result = validator.validate_embeddings(embeddings)

        assert result['valid'] is False
        assert any('infinite' in issue for issue in result['issues'])

    def test_validate_not_normalized(self, validator):
        """Test warning for non-normalized embeddings."""
        embeddings = np.random.randn(10, 384) * 10  # Not normalized

        result = validator.validate_embeddings(embeddings)

        assert any('not normalized' in issue for issue in result['issues'])
        assert 'mean_norm' in result

    def test_validate_diversity(self, validator):
        """Test diversity check for embeddings."""
        # Create normalized embeddings
        embeddings = np.random.randn(10, 384)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        result = validator.validate_embeddings(embeddings)

        assert 'embedding_diversity' in result
        assert 'mean_similarity' in result['embedding_diversity']

    def test_validate_too_similar_embeddings(self, validator):
        """Test detection of overly similar embeddings."""
        # Create very similar embeddings
        base = np.random.randn(1, 384)
        base = base / np.linalg.norm(base)
        embeddings = np.repeat(base, 10, axis=0)
        embeddings += np.random.randn(10, 384) * 0.01  # Add tiny noise
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        result = validator.validate_embeddings(embeddings)

        assert any('too similar' in issue for issue in result['issues'])

    def test_validate_single_embedding(self, validator):
        """Test validation of single embedding (no diversity check)."""
        embedding = np.random.randn(1, 384)
        embedding = embedding / np.linalg.norm(embedding)

        result = validator.validate_embeddings(embedding)

        # Should not have diversity metrics for single embedding
        assert 'embedding_diversity' not in result


class TestValidationReport:
    """Tests for validation report generation."""

    def test_create_validation_report(self, validator):
        """Test creation of formatted validation report."""
        validation_results = {
            'financial_metrics': {
                'valid': True,
                'errors': [],
                'warnings': ['Minor issue detected']
            },
            'sec_filings': {
                'valid': False,
                'errors': ['Missing required field'],
                'warnings': []
            },
            'embeddings': {
                'valid': True,
                'anomalies': [
                    {'metric_type': 'revenue', 'change_pct': 150.0, 'company_id': 'uuid-1'}
                ]
            }
        }

        report = validator.create_validation_report(validation_results)

        assert 'DATA QUALITY VALIDATION REPORT' in report
        assert 'FINANCIAL_METRICS' in report
        assert 'SEC_FILINGS' in report
        assert 'VALID' in report or 'INVALID' in report
        assert 'Minor issue detected' in report
        assert 'Missing required field' in report

    def test_report_total_issues_count(self, validator):
        """Test total issues count in report."""
        validation_results = {
            'test1': {'errors': ['e1', 'e2'], 'warnings': ['w1']},
            'test2': {'errors': ['e3'], 'warnings': ['w2', 'w3']}
        }

        report = validator.create_validation_report(validation_results)

        assert 'Total Issues Found: 6' in report

    def test_report_empty_results(self, validator):
        """Test report with no validation results."""
        report = validator.create_validation_report({})

        assert 'Total Issues Found: 0' in report


class TestPanderaSchemas:
    """Tests for Pandera schema definitions."""

    def test_financial_metrics_schema_valid_data(self):
        """Test FinancialMetricsSchema with valid data."""
        df = pd.DataFrame({
            'company_id': ['uuid-1'],
            'ticker': ['DUOL'],
            'metric_date': [pd.Timestamp('2025-01-01')],
            'metric_type': ['revenue'],
            'value': [100.0],
            'unit': ['USD'],
            'confidence_score': [0.95]
        })

        # Should not raise
        FinancialMetricsSchema.validate(df)

    def test_sec_filing_schema_valid_data(self):
        """Test SECFilingSchema with valid data."""
        df = pd.DataFrame({
            'company_id': ['uuid-1'],
            'filing_type': ['10-K'],
            'filing_date': [pd.Timestamp('2024-12-31')],
            'accession_number': ['0001234567-24-123456'],
            'content_length': [5000]
        })

        # Should not raise
        SECFilingSchema.validate(df)
