"""
Unit Tests for Data Quality Service

Tests validation rules, anomaly detection, data freshness checks,
and schema validation for data quality management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from app.services.data_quality import (
    DataQualityService,
    ValidationEngine,
    AnomalyDetector,
    FreshnessChecker,
    SchemaValidator
)
from app.core.exceptions import (
    ValidationError,
    DataQualityError,
    SchemaValidationError
)


class TestValidationEngine:
    """Test suite for validation rules"""

    @pytest.fixture
    def engine(self):
        """Create validation engine instance"""
        return ValidationEngine()

    def test_validate_required_fields_success(self, engine):
        """Test successful required fields validation"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': Decimal('1000000'),
            'industry': 'Technology'
        }
        required_fields = ['company_name', 'revenue', 'industry']

        # Act
        result = engine.validate_required_fields(data, required_fields)

        # Assert
        assert result['valid'] == True
        assert result['missing_fields'] == []

    def test_validate_required_fields_missing(self, engine):
        """Test required fields validation with missing fields"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': Decimal('1000000')
        }
        required_fields = ['company_name', 'revenue', 'industry', 'employees']

        # Act
        result = engine.validate_required_fields(data, required_fields)

        # Assert
        assert result['valid'] == False
        assert 'industry' in result['missing_fields']
        assert 'employees' in result['missing_fields']

    def test_validate_data_types_success(self, engine):
        """Test successful data type validation"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': Decimal('1000000'),
            'employees': 250,
            'founded_date': datetime(2020, 1, 1)
        }

        type_schema = {
            'company_name': str,
            'revenue': Decimal,
            'employees': int,
            'founded_date': datetime
        }

        # Act
        result = engine.validate_data_types(data, type_schema)

        # Assert
        assert result['valid'] == True
        assert result['type_errors'] == []

    def test_validate_data_types_invalid(self, engine):
        """Test data type validation with type mismatches"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': '1000000',  # Should be Decimal
            'employees': '250',     # Should be int
        }

        type_schema = {
            'company_name': str,
            'revenue': Decimal,
            'employees': int
        }

        # Act
        result = engine.validate_data_types(data, type_schema)

        # Assert
        assert result['valid'] == False
        assert len(result['type_errors']) == 2

    def test_validate_numeric_ranges(self, engine):
        """Test numeric range validation"""
        # Arrange
        data = {
            'revenue': Decimal('1000000'),
            'profit_margin': Decimal('15.5'),
            'employees': 250
        }

        range_constraints = {
            'revenue': {'min': Decimal('0'), 'max': Decimal('10000000')},
            'profit_margin': {'min': Decimal('0'), 'max': Decimal('100')},
            'employees': {'min': 1, 'max': 10000}
        }

        # Act
        result = engine.validate_ranges(data, range_constraints)

        # Assert
        assert result['valid'] == True
        assert result['range_violations'] == []

    def test_validate_numeric_ranges_violations(self, engine):
        """Test numeric range validation with violations"""
        # Arrange
        data = {
            'revenue': Decimal('-100000'),  # Negative
            'profit_margin': Decimal('150'),  # > 100%
            'employees': 0  # Below minimum
        }

        range_constraints = {
            'revenue': {'min': Decimal('0'), 'max': Decimal('10000000')},
            'profit_margin': {'min': Decimal('0'), 'max': Decimal('100')},
            'employees': {'min': 1, 'max': 10000}
        }

        # Act
        result = engine.validate_ranges(data, range_constraints)

        # Assert
        assert result['valid'] == False
        assert len(result['range_violations']) == 3

    def test_validate_string_patterns(self, engine):
        """Test string pattern validation with regex"""
        # Arrange
        data = {
            'email': 'contact@acmecorp.com',
            'phone': '+1-555-123-4567',
            'ticker': 'ACME'
        }

        patterns = {
            'email': r'^[\w\.-]+@[\w\.-]+\.\w+$',
            'phone': r'^\+\d{1,3}-\d{3}-\d{3}-\d{4}$',
            'ticker': r'^[A-Z]{2,5}$'
        }

        # Act
        result = engine.validate_patterns(data, patterns)

        # Assert
        assert result['valid'] == True
        assert result['pattern_violations'] == []

    def test_validate_business_rules(self, engine):
        """Test custom business rule validation"""
        # Arrange
        data = {
            'revenue': Decimal('1000000'),
            'expenses': Decimal('800000'),
            'profit': Decimal('200000')
        }

        def validate_profit_calculation(data):
            return data['revenue'] - data['expenses'] == data['profit']

        business_rules = [
            {
                'name': 'profit_calculation',
                'validator': validate_profit_calculation,
                'message': 'Profit must equal revenue minus expenses'
            }
        ]

        # Act
        result = engine.validate_business_rules(data, business_rules)

        # Assert
        assert result['valid'] == True

    def test_validate_referential_integrity(self, engine):
        """Test referential integrity validation"""
        # Arrange
        data = {
            'company_id': 123,
            'industry_id': 456,
            'location_id': 789
        }

        valid_references = {
            'company_id': [123, 124, 125],
            'industry_id': [456, 457],
            'location_id': [789, 790, 791]
        }

        # Act
        result = engine.validate_references(data, valid_references)

        # Assert
        assert result['valid'] == True
        assert result['invalid_references'] == []


class TestAnomalyDetector:
    """Test suite for anomaly detection"""

    @pytest.fixture
    def detector(self):
        """Create anomaly detector instance"""
        return AnomalyDetector(sensitivity=2.0)

    def test_detect_statistical_outliers_zscore(self, detector):
        """Test Z-score based outlier detection"""
        # Arrange
        data = [10, 12, 11, 13, 12, 11, 10, 100, 12, 11]  # 100 is outlier

        # Act
        outliers = detector.detect_outliers_zscore(data, threshold=2.0)

        # Assert
        assert len(outliers) > 0
        assert 100 in [data[i] for i in outliers['indices']]

    def test_detect_statistical_outliers_iqr(self, detector):
        """Test IQR based outlier detection"""
        # Arrange
        data = [10, 12, 11, 13, 12, 11, 10, 100, 12, 11]

        # Act
        outliers = detector.detect_outliers_iqr(data)

        # Assert
        assert len(outliers) > 0
        assert 100 in [data[i] for i in outliers['indices']]

    def test_detect_time_series_anomalies(self, detector):
        """Test time series anomaly detection"""
        # Arrange
        timestamps = [datetime(2024, 1, i) for i in range(1, 31)]
        values = [100] * 29 + [500]  # Spike on last day

        time_series_data = list(zip(timestamps, values))

        # Act
        anomalies = detector.detect_time_series_anomalies(time_series_data)

        # Assert
        assert len(anomalies) > 0
        assert anomalies[-1]['value'] == 500

    def test_detect_pattern_anomalies(self, detector):
        """Test pattern-based anomaly detection"""
        # Arrange
        # Revenue should follow seasonal pattern
        seasonal_data = [100, 110, 95, 105, 100, 115, 98, 107, 500, 105, 100]

        # Act
        anomalies = detector.detect_pattern_anomalies(
            seasonal_data,
            pattern_type='seasonal',
            period=4
        )

        # Assert
        assert len(anomalies) > 0
        assert 500 in [seasonal_data[i] for i in anomalies['indices']]

    def test_detect_multivariate_anomalies(self, detector):
        """Test multivariate anomaly detection"""
        # Arrange
        data = np.array([
            [100, 50, 25],   # Normal
            [105, 52, 26],   # Normal
            [98, 49, 24],    # Normal
            [102, 51, 25],   # Normal
            [500, 10, 5]     # Anomaly - inconsistent ratios
        ])

        # Act
        anomalies = detector.detect_multivariate_anomalies(data)

        # Assert
        assert len(anomalies) > 0
        assert 4 in anomalies['indices']  # Last row is anomaly

    def test_detect_sudden_changes(self, detector):
        """Test detection of sudden changes in data"""
        # Arrange
        data = [100, 102, 101, 103, 105, 150, 148, 152, 149]
        # Sudden jump from ~103 to ~150

        # Act
        changes = detector.detect_sudden_changes(data, threshold=20)

        # Assert
        assert len(changes) > 0
        assert changes[0]['index'] == 5  # Jump at index 5

    def test_detect_missing_patterns(self, detector):
        """Test detection of missing expected patterns"""
        # Arrange
        # Expected daily data, but some days missing
        dates = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 5),  # Missing 3rd and 4th
            datetime(2024, 1, 6)
        ]

        # Act
        missing = detector.detect_missing_patterns(dates, expected_frequency='daily')

        # Assert
        assert len(missing) == 2  # Two missing dates
        assert datetime(2024, 1, 3) in missing
        assert datetime(2024, 1, 4) in missing


class TestFreshnessChecker:
    """Test suite for data freshness checks"""

    @pytest.fixture
    def checker(self):
        """Create freshness checker instance"""
        return FreshnessChecker()

    def test_check_data_freshness_fresh(self, checker):
        """Test freshness check for recent data"""
        # Arrange
        data_timestamp = datetime.utcnow() - timedelta(hours=2)
        max_age_hours = 24

        # Act
        result = checker.check_freshness(data_timestamp, max_age_hours)

        # Assert
        assert result['is_fresh'] == True
        assert result['age_hours'] < max_age_hours

    def test_check_data_freshness_stale(self, checker):
        """Test freshness check for stale data"""
        # Arrange
        data_timestamp = datetime.utcnow() - timedelta(hours=48)
        max_age_hours = 24

        # Act
        result = checker.check_freshness(data_timestamp, max_age_hours)

        # Assert
        assert result['is_fresh'] == False
        assert result['age_hours'] > max_age_hours

    def test_check_update_frequency(self, checker):
        """Test data update frequency validation"""
        # Arrange
        update_timestamps = [
            datetime.utcnow() - timedelta(days=7),
            datetime.utcnow() - timedelta(days=6),
            datetime.utcnow() - timedelta(days=5),
            datetime.utcnow() - timedelta(days=4)
        ]
        expected_frequency = 'daily'

        # Act
        result = checker.check_update_frequency(
            update_timestamps,
            expected_frequency
        )

        # Assert
        assert result['meets_frequency'] == True
        assert result['average_gap_hours'] <= 24

    def test_check_completeness_over_time(self, checker):
        """Test data completeness check over time period"""
        # Arrange
        # Weekly data for 4 weeks, but one week missing
        data_points = [
            {'date': datetime(2024, 1, 7), 'value': 100},
            {'date': datetime(2024, 1, 14), 'value': 105},
            # Missing week of Jan 21
            {'date': datetime(2024, 1, 28), 'value': 110}
        ]

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        expected_frequency = 'weekly'

        # Act
        result = checker.check_completeness(
            data_points,
            start_date,
            end_date,
            expected_frequency
        )

        # Assert
        assert result['is_complete'] == False
        assert len(result['missing_periods']) > 0

    def test_detect_stale_dependencies(self, checker):
        """Test detection of stale data dependencies"""
        # Arrange
        dependencies = {
            'market_data': datetime.utcnow() - timedelta(hours=2),
            'company_financials': datetime.utcnow() - timedelta(hours=48),
            'industry_metrics': datetime.utcnow() - timedelta(hours=1)
        }

        max_ages = {
            'market_data': 24,
            'company_financials': 24,
            'industry_metrics': 24
        }

        # Act
        result = checker.detect_stale_dependencies(dependencies, max_ages)

        # Assert
        assert len(result['stale_dependencies']) == 1
        assert 'company_financials' in result['stale_dependencies']


class TestSchemaValidator:
    """Test suite for schema validation"""

    @pytest.fixture
    def validator(self):
        """Create schema validator instance"""
        return SchemaValidator()

    def test_validate_json_schema_success(self, validator):
        """Test successful JSON schema validation"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': 1000000,
            'employees': 250,
            'industry': 'Technology'
        }

        schema = {
            'type': 'object',
            'properties': {
                'company_name': {'type': 'string'},
                'revenue': {'type': 'number'},
                'employees': {'type': 'integer'},
                'industry': {'type': 'string'}
            },
            'required': ['company_name', 'revenue']
        }

        # Act
        result = validator.validate_json_schema(data, schema)

        # Assert
        assert result['valid'] == True
        assert result['errors'] == []

    def test_validate_json_schema_failure(self, validator):
        """Test JSON schema validation with errors"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': 'invalid',  # Should be number
            'employees': 250.5     # Should be integer
        }

        schema = {
            'type': 'object',
            'properties': {
                'company_name': {'type': 'string'},
                'revenue': {'type': 'number'},
                'employees': {'type': 'integer'}
            },
            'required': ['company_name', 'revenue', 'employees']
        }

        # Act
        result = validator.validate_json_schema(data, schema)

        # Assert
        assert result['valid'] == False
        assert len(result['errors']) > 0

    def test_validate_database_schema(self, validator):
        """Test database schema validation"""
        # Arrange
        table_schema = {
            'columns': [
                {'name': 'id', 'type': 'INTEGER', 'nullable': False},
                {'name': 'company_name', 'type': 'VARCHAR', 'nullable': False},
                {'name': 'revenue', 'type': 'DECIMAL', 'nullable': True}
            ],
            'primary_key': ['id'],
            'indexes': ['company_name']
        }

        data_row = {
            'id': 1,
            'company_name': 'ACME Corp',
            'revenue': Decimal('1000000')
        }

        # Act
        result = validator.validate_database_row(data_row, table_schema)

        # Assert
        assert result['valid'] == True

    def test_validate_schema_evolution(self, validator):
        """Test schema evolution compatibility"""
        # Arrange
        old_schema = {
            'version': '1.0',
            'fields': ['id', 'name', 'revenue']
        }

        new_schema = {
            'version': '2.0',
            'fields': ['id', 'name', 'revenue', 'employees']  # Added field
        }

        # Act
        result = validator.validate_schema_evolution(old_schema, new_schema)

        # Assert
        assert result['compatible'] == True
        assert 'employees' in result['added_fields']


class TestDataQualityService:
    """Integration tests for DataQualityService"""

    @pytest.fixture
    def service(self):
        """Create data quality service instance"""
        return DataQualityService()

    def test_comprehensive_quality_check(self, service):
        """Test comprehensive data quality validation"""
        # Arrange
        data = {
            'company_name': 'ACME Corp',
            'revenue': Decimal('1000000'),
            'employees': 250,
            'last_updated': datetime.utcnow() - timedelta(hours=12)
        }

        quality_rules = {
            'required_fields': ['company_name', 'revenue'],
            'type_validation': True,
            'range_checks': True,
            'freshness_check': {'max_age_hours': 24},
            'anomaly_detection': True
        }

        # Act
        result = service.validate_data_quality(data, quality_rules)

        # Assert
        assert 'validation_passed' in result
        assert 'quality_score' in result
        assert result['quality_score'] >= 0
        assert result['quality_score'] <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
