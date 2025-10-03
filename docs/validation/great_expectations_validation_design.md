# Great Expectations Validation Suite Design for SEC Filing Data

## Executive Summary

This document defines comprehensive data validation expectations for SEC filing data using Great Expectations framework. The validation suite ensures data quality, consistency, and reliability across the corporate intelligence pipeline.

## 1. Data Model Overview

### Core Entities
- **SECFiling**: Primary SEC filing documents
- **Company**: EdTech company metadata
- **FinancialMetric**: Time-series financial data
- **Document**: Generic document storage with embeddings

### Critical Fields Analysis

#### SECFiling Table
```python
{
    "id": "UUID (primary key)",
    "company_id": "UUID (foreign key to companies)",
    "filing_type": "String(20) - required",
    "filing_date": "DateTime(TZ) - required, indexed",
    "accession_number": "String(25) - unique, required",
    "filing_url": "Text",
    "raw_text": "Text",
    "parsed_sections": "JSON",
    "processing_status": "String(20) - default 'pending'",
    "processed_at": "DateTime(TZ)",
    "error_message": "Text",
    "created_at": "DateTime(TZ) - server_default",
    "updated_at": "DateTime(TZ) - auto-update"
}
```

## 2. Validation Expectations Suite

### 2.1 SEC Filing Core Expectations

#### 2.1.1 Required Fields Validation

**Expectation: expect_column_values_to_not_be_null**
```python
expectations = [
    {
        "expectation_type": "expect_column_values_to_not_be_null",
        "kwargs": {
            "column": "company_id",
            "meta": {
                "severity": "critical",
                "business_rule": "Every filing must be associated with a company"
            }
        }
    },
    {
        "expectation_type": "expect_column_values_to_not_be_null",
        "kwargs": {
            "column": "filing_type",
            "meta": {
                "severity": "critical",
                "business_rule": "Filing type is mandatory for categorization"
            }
        }
    },
    {
        "expectation_type": "expect_column_values_to_not_be_null",
        "kwargs": {
            "column": "filing_date",
            "meta": {
                "severity": "critical",
                "business_rule": "Filing date required for temporal analysis"
            }
        }
    },
    {
        "expectation_type": "expect_column_values_to_not_be_null",
        "kwargs": {
            "column": "accession_number",
            "meta": {
                "severity": "critical",
                "business_rule": "Accession number is unique SEC identifier"
            }
        }
    }
]
```

#### 2.1.2 Data Type Validation

**Expectation: expect_column_values_to_be_of_type**
```python
type_expectations = [
    {
        "expectation_type": "expect_column_values_to_be_of_type",
        "kwargs": {
            "column": "company_id",
            "type_": "str",  # UUID represented as string
            "meta": {"severity": "high"}
        }
    },
    {
        "expectation_type": "expect_column_values_to_be_of_type",
        "kwargs": {
            "column": "filing_date",
            "type_": "datetime64",
            "meta": {"severity": "critical"}
        }
    },
    {
        "expectation_type": "expect_column_values_to_be_of_type",
        "kwargs": {
            "column": "filing_type",
            "type_": "str",
            "meta": {"severity": "high"}
        }
    }
]
```

#### 2.1.3 Format Constraints

**Accession Number Format (SEC Standard)**
```python
{
    "expectation_type": "expect_column_values_to_match_regex",
    "kwargs": {
        "column": "accession_number",
        "regex": "^[0-9]{10}-[0-9]{2}-[0-9]{6}$",
        "meta": {
            "severity": "critical",
            "description": "SEC accession format: 10 digits, dash, 2 digits, dash, 6 digits",
            "example": "0001234567-23-000001"
        }
    }
}
```

**Filing Type Validation**
```python
{
    "expectation_type": "expect_column_values_to_be_in_set",
    "kwargs": {
        "column": "filing_type",
        "value_set": [
            "10-K",      # Annual report
            "10-Q",      # Quarterly report
            "8-K",       # Current report
            "DEF 14A",   # Proxy statement
            "20-F",      # Foreign annual report
            "S-1",       # IPO registration
            "S-4",       # Merger registration
            "10-K/A",    # Amended annual
            "10-Q/A",    # Amended quarterly
            "SC 13D",    # Beneficial ownership
            "SC 13G"     # Passive ownership
        ],
        "meta": {
            "severity": "high",
            "business_rule": "Only accept valid SEC form types"
        }
    }
}
```

**CIK Format Validation**
```python
{
    "expectation_type": "expect_column_values_to_match_regex",
    "kwargs": {
        "column": "cik",
        "regex": "^[0-9]{10}$|^CIK[0-9]{10}$",
        "meta": {
            "severity": "high",
            "description": "CIK must be 10-digit number, optionally prefixed with 'CIK'",
            "example": "0001318605 or CIK0001318605"
        }
    }
}
```

#### 2.1.4 Date Range Constraints

**Filing Date Validation**
```python
{
    "expectation_type": "expect_column_values_to_be_between",
    "kwargs": {
        "column": "filing_date",
        "min_value": "1994-01-01",  # EDGAR system start date
        "max_value": "{{ current_date }}",
        "parse_strings_as_datetimes": True,
        "meta": {
            "severity": "high",
            "business_rule": "EDGAR filings available from 1994 onwards, cannot be future-dated"
        }
    }
}
```

**Processing Timestamp Validation**
```python
{
    "expectation_type": "expect_column_pair_values_A_to_be_greater_than_B",
    "kwargs": {
        "column_A": "processed_at",
        "column_B": "filing_date",
        "or_equal": True,
        "meta": {
            "severity": "medium",
            "business_rule": "Processing must occur on or after filing date"
        }
    }
}
```

#### 2.1.5 Uniqueness Constraints

**Accession Number Uniqueness**
```python
{
    "expectation_type": "expect_column_values_to_be_unique",
    "kwargs": {
        "column": "accession_number",
        "meta": {
            "severity": "critical",
            "business_rule": "Each SEC filing has unique accession number"
        }
    }
}
```

**Compound Uniqueness: Company + Accession**
```python
{
    "expectation_type": "expect_compound_columns_to_be_unique",
    "kwargs": {
        "column_list": ["company_id", "accession_number"],
        "meta": {
            "severity": "critical",
            "business_rule": "Prevent duplicate filings for same company"
        }
    }
}
```

### 2.2 Content Quality Expectations

#### 2.2.1 Raw Text Validation

**Minimum Content Length**
```python
{
    "expectation_type": "expect_column_value_lengths_to_be_between",
    "kwargs": {
        "column": "raw_text",
        "min_value": 1000,
        "max_value": 50000000,  # 50MB text limit
        "meta": {
            "severity": "high",
            "business_rule": "Filings should have substantial content (min 1000 chars)"
        }
    }
}
```

**Content Presence Check**
```python
{
    "expectation_type": "expect_column_values_to_not_be_null",
    "kwargs": {
        "column": "raw_text",
        "mostly": 0.95,  # Allow 5% missing for edge cases
        "meta": {
            "severity": "high",
            "business_rule": "95% of filings must have raw text content"
        }
    }
}
```

#### 2.2.2 Parsed Sections Validation

**JSON Structure Validation**
```python
{
    "expectation_type": "expect_column_values_to_match_json_schema",
    "kwargs": {
        "column": "parsed_sections",
        "json_schema": {
            "type": "object",
            "properties": {
                "business_description": {"type": "string"},
                "risk_factors": {"type": "string"},
                "financial_statements": {"type": "object"},
                "management_discussion": {"type": "string"},
                "section_1a": {"type": "string"},
                "section_7": {"type": "string"}
            },
            "required": ["business_description"]
        },
        "meta": {
            "severity": "medium",
            "business_rule": "Parsed sections must contain valid JSON structure"
        }
    }
}
```

#### 2.2.3 URL Validation

**Filing URL Format**
```python
{
    "expectation_type": "expect_column_values_to_match_regex",
    "kwargs": {
        "column": "filing_url",
        "regex": "^https?://www\\.sec\\.gov/.*",
        "mostly": 0.98,
        "meta": {
            "severity": "medium",
            "business_rule": "Filing URLs should point to SEC.gov"
        }
    }
}
```

### 2.3 Processing Status Validation

**Valid Status Values**
```python
{
    "expectation_type": "expect_column_values_to_be_in_set",
    "kwargs": {
        "column": "processing_status",
        "value_set": [
            "pending",
            "processing",
            "completed",
            "failed",
            "retry",
            "archived"
        ],
        "meta": {
            "severity": "medium",
            "business_rule": "Processing status must match pipeline states"
        }
    }
}
```

**Status-Timestamp Consistency**
```python
{
    "expectation_type": "expect_column_pair_values_to_be_in_set",
    "kwargs": {
        "column_A": "processing_status",
        "column_B": "processed_at",
        "value_pairs_set": [
            ("completed", "not_null"),
            ("failed", "not_null")
        ],
        "meta": {
            "severity": "medium",
            "business_rule": "Completed/failed filings must have processed_at timestamp"
        }
    }
}
```

### 2.4 Company Reference Validation

**Valid Company ID Reference**
```python
{
    "expectation_type": "expect_column_values_to_be_in_set",
    "kwargs": {
        "column": "company_id",
        "value_set": "{{ valid_company_ids }}",  # Dynamic from companies table
        "meta": {
            "severity": "critical",
            "business_rule": "Filing must reference existing company"
        }
    }
}
```

### 2.5 Data Quality Metrics

#### 2.5.1 Completeness Metrics

**Overall Completeness**
```python
{
    "expectation_type": "expect_table_row_count_to_be_between",
    "kwargs": {
        "min_value": 100,
        "max_value": 10000000,
        "meta": {
            "severity": "low",
            "business_rule": "Sanity check on dataset size"
        }
    }
}
```

**Field Completeness Rate**
```python
completeness_expectations = [
    {
        "column": "filing_url",
        "expected_null_rate": 0.05,  # 95% completeness
        "severity": "medium"
    },
    {
        "column": "raw_text",
        "expected_null_rate": 0.02,  # 98% completeness
        "severity": "high"
    },
    {
        "column": "parsed_sections",
        "expected_null_rate": 0.10,  # 90% completeness
        "severity": "medium"
    }
]
```

#### 2.5.2 Consistency Metrics

**Filing Type Distribution**
```python
{
    "expectation_type": "expect_column_proportion_of_unique_values_to_be_between",
    "kwargs": {
        "column": "filing_type",
        "min_value": 0.01,
        "max_value": 0.50,
        "meta": {
            "severity": "low",
            "business_rule": "Filing type distribution should be reasonable"
        }
    }
}
```

**Temporal Distribution**
```python
{
    "expectation_type": "expect_column_values_to_be_dateutil_parseable",
    "kwargs": {
        "column": "filing_date",
        "meta": {
            "severity": "critical",
            "business_rule": "All dates must be parseable"
        }
    }
}
```

## 3. Expectation Suite Structure

### 3.1 Primary Suite: `sec_filings_core`

```python
{
    "expectation_suite_name": "sec_filings_core",
    "data_asset_type": "Dataset",
    "meta": {
        "great_expectations_version": "0.18.0",
        "description": "Core validation suite for SEC filing data",
        "created_by": "Data Quality Team",
        "tags": ["sec", "filings", "critical"]
    },
    "expectations": [
        # Required fields (critical)
        # Data types (high)
        # Format constraints (high)
        # Uniqueness (critical)
    ]
}
```

### 3.2 Content Quality Suite: `sec_filings_content`

```python
{
    "expectation_suite_name": "sec_filings_content",
    "data_asset_type": "Dataset",
    "meta": {
        "description": "Content quality validation for SEC filings",
        "severity_distribution": {
            "critical": 5,
            "high": 8,
            "medium": 12,
            "low": 3
        }
    },
    "expectations": [
        # Content length
        # JSON structure
        # URL validation
        # Financial keywords presence
    ]
}
```

### 3.3 Processing Pipeline Suite: `sec_filings_pipeline`

```python
{
    "expectation_suite_name": "sec_filings_pipeline",
    "data_asset_type": "Dataset",
    "meta": {
        "description": "Processing status and workflow validation"
    },
    "expectations": [
        # Status values
        # Timestamp consistency
        # Error handling
    ]
}
```

## 4. Test Case Planning

### 4.1 Positive Test Cases

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| TC-001 | Valid 10-K filing | Complete 10-K data with all required fields | All expectations pass |
| TC-002 | Valid 10-Q filing | Complete 10-Q data | All expectations pass |
| TC-003 | Historical filing (1994) | Filing from EDGAR launch | Date validation passes |
| TC-004 | Recent filing | Current year filing | All validations pass |
| TC-005 | Multiple filings per company | 5+ filings for one company | Uniqueness maintained |

### 4.2 Negative Test Cases

| Test ID | Description | Input | Expected Failure |
|---------|-------------|-------|-----------------|
| TC-101 | Missing accession number | Filing without accession_number | NOT NULL expectation fails |
| TC-102 | Invalid accession format | Accession: "12345" | Regex expectation fails |
| TC-103 | Future filing date | Filing date: 2030-01-01 | Date range expectation fails |
| TC-104 | Duplicate accession | Two filings with same accession | Uniqueness expectation fails |
| TC-105 | Invalid filing type | Filing type: "INVALID" | Value set expectation fails |
| TC-106 | Short content | Raw text < 1000 chars | Length expectation fails |
| TC-107 | Pre-EDGAR date | Filing date: 1990-01-01 | Date range expectation fails |
| TC-108 | Invalid company reference | Non-existent company_id | Foreign key expectation fails |
| TC-109 | Invalid processing status | Status: "random_status" | Value set expectation fails |
| TC-110 | Inconsistent timestamps | processed_at < filing_date | Timestamp comparison fails |

### 4.3 Edge Cases

| Test ID | Description | Input | Expected Behavior |
|---------|-------------|-------|-------------------|
| TC-201 | Minimum content length | Exactly 1000 characters | Pass with warning |
| TC-202 | Maximum filing type variation | All valid filing types | Distribution check passes |
| TC-203 | Null optional fields | Only required fields populated | Pass completely |
| TC-204 | Amended filing | 10-K/A format | Filing type validation passes |
| TC-205 | Foreign issuer | 20-F filing | Recognized in value set |

### 4.4 Data Quality Scenarios

| Test ID | Description | Scenario | Validation |
|---------|-------------|----------|------------|
| TC-301 | Batch completeness | 95% of batch has all required fields | Meets threshold |
| TC-302 | Temporal coverage | Filings span multiple years | Distribution validation |
| TC-303 | Company coverage | Multiple companies represented | Diversity check |
| TC-304 | Processing efficiency | 90%+ completion rate | Status distribution check |
| TC-305 | Content quality | 98% have substantial content | Length validation passes |

## 5. Validation Rules Documentation

### 5.1 Critical Rules (Severity: Critical)

1. **RULE-001: Accession Number Uniqueness**
   - Every filing must have unique accession number
   - Format: `^[0-9]{10}-[0-9]{2}-[0-9]{6}$`
   - Business Impact: Prevents duplicate processing

2. **RULE-002: Required Field Completeness**
   - Fields: company_id, filing_type, filing_date, accession_number
   - 100% completeness required
   - Business Impact: Enables core functionality

3. **RULE-003: Valid Company Reference**
   - company_id must exist in companies table
   - Business Impact: Data integrity

### 5.2 High Priority Rules (Severity: High)

4. **RULE-004: Filing Date Range**
   - Min: 1994-01-01 (EDGAR launch)
   - Max: Current date
   - Business Impact: Historical accuracy

5. **RULE-005: Filing Type Validity**
   - Must be in approved SEC form types list
   - Business Impact: Proper categorization

6. **RULE-006: Content Presence**
   - 95%+ of filings must have raw_text
   - Min length: 1000 characters
   - Business Impact: Analysis capability

### 5.3 Medium Priority Rules (Severity: Medium)

7. **RULE-007: Processing Status Consistency**
   - Valid statuses only
   - Timestamp alignment with status
   - Business Impact: Pipeline monitoring

8. **RULE-008: URL Validity**
   - 98%+ URLs should point to sec.gov
   - Business Impact: Source traceability

9. **RULE-009: Parsed Sections Structure**
   - Valid JSON format
   - Contains expected sections
   - Business Impact: Structured analysis

## 6. Implementation Plan

### 6.1 Phase 1: Core Expectations (Week 1)
- Implement critical field validations
- Set up Great Expectations context
- Create base expectation suites
- Configure data sources

### 6.2 Phase 2: Content Quality (Week 2)
- Add content validation rules
- Implement JSON schema validation
- Create custom expectations for financial keywords
- Set up anomaly detection

### 6.3 Phase 3: Pipeline Integration (Week 3)
- Integrate with data pipeline
- Add checkpoint automation
- Configure Slack/email notifications
- Set up validation dashboards

### 6.4 Phase 4: Testing & Refinement (Week 4)
- Execute all test cases
- Tune thresholds based on results
- Document exceptions and edge cases
- Create validation playbooks

## 7. Monitoring & Alerting

### 7.1 Validation Checkpoints

**Daily Checkpoint**
```python
checkpoint_config = {
    "name": "sec_filings_daily",
    "config_version": 1.0,
    "class_name": "SimpleCheckpoint",
    "run_name_template": "%Y%m%d-%H%M%S-sec-filings",
    "validations": [
        {
            "batch_request": {
                "datasource_name": "postgres_datasource",
                "data_asset_name": "sec_filings",
                "options": {
                    "date_filter": "last_24_hours"
                }
            },
            "expectation_suite_name": "sec_filings_core"
        }
    ],
    "action_list": [
        {
            "name": "store_validation_result",
            "action": {"class_name": "StoreValidationResultAction"}
        },
        {
            "name": "update_data_docs",
            "action": {"class_name": "UpdateDataDocsAction"}
        },
        {
            "name": "send_slack_notification_on_validation_result",
            "action": {
                "class_name": "SlackNotificationAction",
                "slack_webhook": "${SLACK_WEBHOOK}",
                "notify_on": "failure"
            }
        }
    ]
}
```

### 7.2 Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Failed validations | > 5% | > 10% |
| Missing required fields | > 1% | > 5% |
| Invalid formats | > 2% | > 10% |
| Duplicate records | > 0 | > 10 |
| Content quality issues | > 10% | > 25% |

## 8. Metrics & KPIs

### 8.1 Data Quality Score

```
DQ Score = (
    (Required Fields Complete * 0.30) +
    (Format Validity * 0.25) +
    (Content Quality * 0.20) +
    (Uniqueness * 0.15) +
    (Temporal Validity * 0.10)
) * 100
```

Target: DQ Score ≥ 95%

### 8.2 Validation Coverage

- Total expectations: 45+
- Critical expectations: 12
- High priority: 15
- Medium priority: 12
- Low priority: 6

### 8.3 Performance Targets

- Validation runtime: < 5 minutes per 10K records
- Memory usage: < 2GB per validation run
- API response time: < 500ms for validation checks

## 9. Documentation & Handoff

### 9.1 Deliverables

1. **Expectation Suite JSON Files**
   - `sec_filings_core.json`
   - `sec_filings_content.json`
   - `sec_filings_pipeline.json`

2. **Test Case Suite**
   - Positive, negative, and edge case tests
   - Automated test runner scripts

3. **Validation Playbook**
   - Troubleshooting guide
   - Common issues and resolutions
   - Escalation procedures

4. **Dashboard & Reports**
   - Data Docs configuration
   - Validation metrics dashboard
   - Automated reporting setup

### 9.2 Training Materials

- Great Expectations best practices guide
- Custom expectation development guide
- Checkpoint configuration tutorial
- Alert response procedures

## 10. Future Enhancements

### 10.1 Advanced Validations

- **Machine Learning-Based Anomaly Detection**
  - Outlier detection for financial metrics
  - Content similarity analysis
  - Temporal pattern recognition

- **Cross-Table Validation**
  - Company-filing consistency checks
  - Financial metrics extraction validation
  - Document embedding quality checks

### 10.2 Automation Improvements

- Auto-tuning of validation thresholds
- Dynamic expectation generation
- Intelligent alert routing
- Self-healing data pipelines

## Appendix A: Example Expectation Suite

```json
{
    "expectation_suite_name": "sec_filings_core",
    "data_asset_type": "Dataset",
    "expectations": [
        {
            "expectation_type": "expect_table_row_count_to_be_between",
            "kwargs": {
                "min_value": 0,
                "max_value": 10000000
            },
            "meta": {
                "severity": "low"
            }
        },
        {
            "expectation_type": "expect_column_to_exist",
            "kwargs": {
                "column": "accession_number"
            },
            "meta": {
                "severity": "critical"
            }
        },
        {
            "expectation_type": "expect_column_values_to_not_be_null",
            "kwargs": {
                "column": "accession_number"
            },
            "meta": {
                "severity": "critical"
            }
        },
        {
            "expectation_type": "expect_column_values_to_be_unique",
            "kwargs": {
                "column": "accession_number"
            },
            "meta": {
                "severity": "critical"
            }
        },
        {
            "expectation_type": "expect_column_values_to_match_regex",
            "kwargs": {
                "column": "accession_number",
                "regex": "^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
            },
            "meta": {
                "severity": "critical"
            }
        }
    ],
    "meta": {
        "great_expectations_version": "0.18.0"
    }
}
```

## Appendix B: Custom Expectation Examples

```python
# Custom expectation for financial keyword presence
class ExpectColumnValuesToContainFinancialKeywords(ColumnMapExpectation):
    """Expect column values to contain financial keywords."""

    map_metric = "column_values.contain_financial_keywords"

    FINANCIAL_KEYWORDS = [
        "revenue", "income", "assets", "liabilities",
        "cash flow", "earnings", "profit", "loss"
    ]

    @classmethod
    def _validate_value(cls, value):
        if not isinstance(value, str):
            return False

        value_lower = value.lower()
        return any(keyword in value_lower for keyword in cls.FINANCIAL_KEYWORDS)
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-03
**Owner**: Data Quality Team
**Review Cycle**: Quarterly
