# SEC Filing Validation - Quick Reference

## Overview
Comprehensive Great Expectations validation suite for SEC filing data with 45+ expectations across 3 suites.

## Validation Suites

### 1. Core Suite (`sec_filings_core`)
**Critical validations for data integrity**

| Field | Validation | Severity |
|-------|------------|----------|
| `accession_number` | Not null, Unique, Format: `NNNNNNNNNN-NN-NNNNNN` | Critical |
| `company_id` | Not null, Valid UUID, FK to companies | Critical |
| `filing_type` | Not null, In set: 10-K, 10-Q, 8-K, etc. | Critical |
| `filing_date` | Not null, Range: 1994-01-01 to today | High |
| `cik` | Format: 10 digits or CIK + 10 digits | High |

### 2. Content Suite (`sec_filings_content`)
**Content quality validations**

| Check | Rule | Threshold |
|-------|------|-----------|
| Raw text length | Min 1000 chars | 95% compliance |
| Financial keywords | Contains 2+ keywords | 90% compliance |
| Parsed sections | Valid JSON structure | 90% compliance |
| Filing URL | Matches sec.gov pattern | 98% compliance |

### 3. Pipeline Suite (`sec_filings_pipeline`)
**Processing workflow validations**

| Status | Requirements |
|--------|--------------|
| `completed` | Must have `processed_at` timestamp |
| `failed` | Must have `error_message` and `processed_at` |
| `pending` | `processed_at` should be null |

## Common Validation Rules

### Accession Number
```regex
^[0-9]{10}-[0-9]{2}-[0-9]{6}$
```
**Example**: `0001234567-24-000001`

### CIK Format
```regex
^[0-9]{10}$|^CIK[0-9]{10}$
```
**Examples**: `0001318605` or `CIK0001318605`

### Valid Filing Types
```
10-K, 10-Q, 8-K, DEF 14A, 20-F, S-1, S-4,
10-K/A, 10-Q/A, SC 13D, SC 13G
```

### Date Ranges
- **Min**: 1994-01-01 (EDGAR launch)
- **Max**: Current date
- **No future dates allowed**

## Test Coverage

### Test Case Summary
- **Positive Cases**: 5 (TC-001 to TC-005)
- **Negative Cases**: 10 (TC-101 to TC-110)
- **Edge Cases**: 5 (TC-201 to TC-205)
- **Quality Scenarios**: 5 (TC-301 to TC-305)

### Key Test Scenarios

#### Positive
- ✅ Valid 10-K, 10-Q, 8-K filings
- ✅ Historical filings (1994+)
- ✅ Multiple filings per company
- ✅ All valid filing types
- ✅ Amended filings (10-K/A)

#### Negative
- ❌ Missing required fields
- ❌ Invalid formats
- ❌ Future dates
- ❌ Duplicate accessions
- ❌ Pre-EDGAR dates
- ❌ Invalid statuses

## Data Quality Metrics

### Target Scores
```
Data Quality Score = 95%+

Components:
- Required Fields: 30% weight (100% complete)
- Format Validity: 25% weight (98%+ valid)
- Content Quality: 20% weight (95%+ substantial)
- Uniqueness: 15% weight (100% unique)
- Temporal Validity: 10% weight (100% valid)
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Failed validations | >5% | >10% |
| Missing required | >1% | >5% |
| Invalid formats | >2% | >10% |
| Duplicate records | >0 | >10 |
| Poor content | >10% | >25% |

## Quick Commands

### Run Validation
```bash
# Full suite validation
python -m pytest tests/validation/test_sec_filing_expectations.py -v

# Specific test class
pytest tests/validation/test_sec_filing_expectations.py::TestSECFilingCoreExpectations -v

# Run with coverage
pytest tests/validation/ --cov=src/validation --cov-report=html
```

### Great Expectations Checkpoints
```bash
# Daily validation checkpoint
great_expectations checkpoint run sec_filings_daily

# Content quality checkpoint
great_expectations checkpoint run sec_filings_content

# View data docs
great_expectations docs build
```

## Common Issues & Solutions

### Issue: Accession Format Failures
**Symptom**: Regex validation fails
**Solution**: Check format is `0001234567-24-000001` (10 digits - 2 digits - 6 digits)

### Issue: Date Range Violations
**Symptom**: Filing date out of range
**Solution**: Ensure 1994-01-01 ≤ date ≤ today

### Issue: Missing Content
**Symptom**: Raw text too short or null
**Solution**: Verify SEC download completed, min 1000 chars required

### Issue: Duplicate Accessions
**Symptom**: Uniqueness constraint fails
**Solution**: Check for duplicate downloads, verify accession_number generation

### Issue: Invalid Filing Types
**Symptom**: Filing type not in approved list
**Solution**: Map to standard SEC form types (10-K, 10-Q, 8-K, etc.)

## Implementation Checklist

- [ ] Install Great Expectations (`pip install great_expectations`)
- [ ] Initialize GE context
- [ ] Create expectation suites (core, content, pipeline)
- [ ] Configure data sources (PostgreSQL)
- [ ] Set up validation checkpoints
- [ ] Configure notifications (Slack, email)
- [ ] Create data docs
- [ ] Run test suite
- [ ] Integrate with pipeline
- [ ] Set up monitoring dashboard

## File Locations

```
docs/validation/
├── great_expectations_validation_design.md  # Full specification
└── VALIDATION_QUICK_REFERENCE.md            # This file

tests/validation/
└── test_sec_filing_expectations.py          # Test suite

src/validation/
└── data_quality.py                          # Validation logic

great_expectations/
├── expectations/
│   ├── sec_filings_core.json
│   ├── sec_filings_content.json
│   └── sec_filings_pipeline.json
├── checkpoints/
│   ├── sec_filings_daily.yml
│   └── sec_filings_content.yml
└── uncommitted/
    └── data_docs/                           # Generated docs
```

## Key Expectations Reference

### Critical (12 expectations)
1. `expect_column_values_to_not_be_null` (accession_number)
2. `expect_column_values_to_be_unique` (accession_number)
3. `expect_column_values_to_match_regex` (accession_number format)
4. `expect_column_values_to_not_be_null` (company_id)
5. `expect_column_values_to_not_be_null` (filing_type)
6. `expect_column_values_to_not_be_null` (filing_date)
7. `expect_column_values_to_be_in_set` (filing_type)
8. `expect_compound_columns_to_be_unique` (company_id + accession)
9. `expect_column_values_to_be_in_set` (company_id FK)
10. `expect_column_values_to_be_dateutil_parseable` (filing_date)
11. `expect_table_row_count_to_be_between` (sanity check)
12. `expect_column_to_exist` (all critical columns)

### High Priority (15 expectations)
- Date range validations
- CIK format validation
- URL format validation
- Content length validation
- Processing status validation
- Timestamp consistency checks

### Medium Priority (12 expectations)
- JSON structure validation
- Financial keywords presence
- Error message requirements
- Status-timestamp alignment
- Distribution checks

### Low Priority (6 expectations)
- Table size checks
- Optional field completeness
- Distribution metrics
- Diversity checks

## Performance Targets

- **Validation Runtime**: <5 min per 10K records
- **Memory Usage**: <2GB per run
- **API Response**: <500ms for checks
- **Coverage**: 95%+ of all data

## Next Steps

1. **Week 1**: Implement core expectations
2. **Week 2**: Add content quality rules
3. **Week 3**: Integrate with pipeline
4. **Week 4**: Test and refine thresholds

---

**Version**: 1.0
**Last Updated**: 2025-10-03
**Owner**: Data Quality Team
**Related**: [Full Design Doc](./great_expectations_validation_design.md)
