# Code Coverage Guide

## Overview

Comprehensive code coverage testing for the Corporate Intelligence Platform.

## Quick Start

```bash
./scripts/run_coverage.sh           # Full coverage report
./scripts/coverage_check.sh         # Quick threshold check
open htmlcov/index.html             # View HTML report
```

## Coverage Configuration

### Thresholds
- Minimum: 80%
- Target: 90%+
- Branch coverage: Required

### Tool Configuration (pyproject.toml)
```toml
[tool.coverage.run]
source = ["src"]
branch = true
fail_under = 80.0
```

## Running Coverage

### Basic Commands
```bash
pytest --cov=src                    # Basic coverage
pytest --cov=src --cov-report=html  # HTML report
pytest --cov=src --cov-branch       # Branch coverage
coverage report --show-missing      # Show uncovered lines
```

### Coverage Scripts

**run_coverage.sh** - Full report with HTML, XML, terminal
**coverage_check.sh** - Quick threshold validation

## Report Types

### Terminal Report
```bash
coverage report
coverage report --show-missing
coverage report --skip-covered
```

### HTML Report
```bash
coverage html
open htmlcov/index.html
```

### XML Report
```bash
coverage xml
```

## Interpreting Results

**Statement Coverage**: Code lines executed (80%+ target)
**Branch Coverage**: Decision branches taken (75%+ target)
**Function Coverage**: Functions called (90%+ target)

**Report Colors**:
- Green: Executed code
- Red: Not executed
- Yellow: Partial branch coverage

## Improving Coverage

### Identify Gaps
```bash
coverage report --skip-covered
coverage report --show-missing
coverage html
```

### Target Low Coverage
```bash
coverage report --sort=cover
coverage report | awk '$6 < 80'
```

### Write Targeted Tests
```python
def test_all_branches():
    # Test true branch
    assert func(True) == expected_true
    # Test false branch
    assert func(False) == expected_false
    # Test edge case
    assert func(None) == expected_edge
```

## Excluding Code

### Inline Exclusions
```python
if DEBUG:  # pragma: no cover
    print("Debug mode")
```

### Configuration (pyproject.toml)
```toml
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

## CI/CD Integration

```yaml
- name: Run coverage
  run: pytest --cov=src --cov-fail-under=80

- name: Upload coverage
  uses: codecov/codecov-action@v4
```

## Troubleshooting

```bash
# Clear coverage data
rm -rf .coverage .coverage.*

# Fresh coverage run
pytest --cov=src --cov-report=html

# Check configuration
cat pyproject.toml | grep -A 20 "coverage"
```

## Best Practices

1. Maintain 80%+ coverage
2. Test edge cases
3. Use branch coverage
4. Review reports regularly
5. Write meaningful tests
6. Don't game metrics

## Related Documentation

- [Pre-commit Setup](PRE_COMMIT_SETUP.md)
- [Code Quality Quick Reference](CODE_QUALITY_QUICK_REFERENCE.md)
