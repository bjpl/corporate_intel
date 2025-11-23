# Pre-Commit Hook Recommendations

**Status**: Recommendations for Implementation
**Last Updated**: 2025-10-25
**Priority**: Medium

## Overview

This document provides recommendations for implementing pre-commit hooks in the corporate_intel project to automate code quality checks and prevent common issues before they reach version control.

## Benefits

- **Automated Quality Control**: Catch issues before commit
- **Consistent Code Style**: Enforce project standards automatically
- **Reduced Review Time**: Fewer trivial issues in code review
- **Security**: Prevent accidental secret commits
- **Documentation**: Keep docs synchronized with code

## Recommended Pre-Commit Hooks

### 1. Python Code Quality

```yaml
# .pre-commit-config.yaml

repos:
  # Python formatting
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
        args: [--line-length=100]

  # Import sorting
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black]

  # Linting
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203]

  # Type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

### 2. Security Checks

```yaml
  # Detect secrets
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package.lock.json

  # Security vulnerabilities
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: [-c, .bandit.yml]
```

### 3. File Quality

```yaml
  # Generic file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: check-merge-conflict
      - id: mixed-line-ending
        args: [--fix=lf]
      - id: no-commit-to-branch
        args: [--branch=master, --branch=main]
```

### 4. SQL & DBT

```yaml
  # SQL formatting
  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.0.0
    hooks:
      - id: sqlfluff-lint
        files: \.(sql)$
      - id: sqlfluff-fix
        files: \.(sql)$

  # DBT validation
  - repo: local
    hooks:
      - id: dbt-compile
        name: DBT Compile Check
        entry: bash -c 'cd dbt && dbt compile'
        language: system
        files: \.(sql|yml)$
        pass_filenames: false
```

### 5. Documentation

```yaml
  # Markdown linting
  - repo: https://github.com/markdownlint/markdownlint
    rev: v0.12.0
    hooks:
      - id: markdownlint
        args: [--rules, ~MD013,~MD033]

  # Update daily reports template check
  - repo: local
    hooks:
      - id: daily-report-check
        name: Daily Report Template Validation
        entry: python scripts/validate_daily_report.py
        language: python
        files: daily_reports/.*\.md$
        pass_filenames: true
```

### 6. Git Commit Messages

```yaml
  # Commit message format
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen
      - id: commitizen-branch
        stages: [push]
```

## Implementation Steps

### Step 1: Install Pre-Commit

```bash
# Install pre-commit
pip install pre-commit

# Or add to requirements-dev.txt
echo "pre-commit>=3.6.0" >> requirements-dev.txt
pip install -r requirements-dev.txt
```

### Step 2: Create Configuration

```bash
# Create .pre-commit-config.yaml in project root
# Copy recommended hooks from above
```

### Step 3: Install Hooks

```bash
# Install git hooks
pre-commit install

# Install for commit messages
pre-commit install --hook-type commit-msg

# Install for pre-push
pre-commit install --hook-type pre-push
```

### Step 4: Initial Run

```bash
# Run against all files (first time only)
pre-commit run --all-files

# Fix any issues found
# Stage and commit fixes
```

### Step 5: Update Configuration

```bash
# Auto-update hook versions
pre-commit autoupdate
```

## Custom Hook Examples

### Daily Report Validator

Create `scripts/validate_daily_report.py`:

```python
#!/usr/bin/env python3
"""Validate daily report completeness."""
import sys
import re

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Session Objectives",
    "Work Completed",
    "Technical Decisions",
    "Metrics & Performance",
    "Next Session Planning"
]

def validate_report(filepath):
    """Check if daily report has all required sections."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    missing = []
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in content:
            missing.append(section)

    # Check for placeholder text
    placeholders = re.findall(r'\[.*?\]', content)

    if missing or placeholders:
        print(f"❌ {filepath} is incomplete:")
        if missing:
            print(f"  Missing sections: {', '.join(missing)}")
        if placeholders:
            print(f"  Contains {len(placeholders)} placeholders")
        return False

    return True

if __name__ == "__main__":
    files = sys.argv[1:]
    failed = [f for f in files if not validate_report(f)]

    if failed:
        sys.exit(1)
    sys.exit(0)
```

### Claude Flow Metrics Validator

Create `scripts/validate_claude_flow_metrics.py`:

```python
#!/usr/bin/env python3
"""Validate Claude Flow metrics before commit."""
import sys
import json

def validate_metrics(filepath):
    """Ensure metrics file is valid JSON with required fields."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Check for required top-level fields
        required = ['timestamp', 'session_id']
        missing = [f for f in required if f not in data]

        if missing:
            print(f"❌ {filepath} missing fields: {', '.join(missing)}")
            return False

        return True
    except json.JSONDecodeError as e:
        print(f"❌ {filepath} is not valid JSON: {e}")
        return False

if __name__ == "__main__":
    files = sys.argv[1:]
    failed = [f for f in files if not validate_metrics(f)]

    if failed:
        sys.exit(1)
    sys.exit(0)
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/pre-commit.yml
name: Pre-commit Checks

on:
  pull_request:
  push:
    branches: [master, develop]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: pre-commit/action@v3.0.0
```

## Performance Optimization

### Skip Hooks When Needed

```bash
# Skip all hooks for urgent fix
git commit --no-verify -m "hotfix: critical issue"

# Skip specific hook
SKIP=flake8 git commit -m "feat: work in progress"

# Skip multiple hooks
SKIP=flake8,mypy git commit -m "wip: experiment"
```

### Cache Dependencies

Pre-commit automatically caches hook environments. To clear cache:

```bash
# Clear all cache
pre-commit clean

# Update cache
pre-commit gc
```

## Project-Specific Recommendations

### High Priority

1. **Security Hooks** (detect-secrets, bandit)
   - Prevent credential leaks
   - Critical for corporate data

2. **Python Quality** (black, isort, flake8)
   - Enforce consistent style
   - Catch common errors

3. **File Quality** (trailing-whitespace, check-yaml, check-json)
   - Prevent formatting issues
   - Validate configuration files

### Medium Priority

4. **SQL Validation** (sqlfluff)
   - DBT model quality
   - Query optimization

5. **Documentation** (markdownlint)
   - Consistent docs format
   - Improve readability

### Low Priority

6. **Commit Message Format** (commitizen)
   - Nice to have
   - Can enforce later

## Maintenance

### Weekly

- Review hook execution times
- Update hook versions: `pre-commit autoupdate`

### Monthly

- Review .pre-commit-config.yaml
- Add/remove hooks based on needs
- Update documentation

### Per Release

- Ensure all hooks pass
- Document any exceptions
- Update CI/CD integration

## Team Adoption

### Phase 1: Awareness (Week 1)

- Share this document
- Demo pre-commit in team meeting
- Install on dev machines

### Phase 2: Soft Enforcement (Weeks 2-4)

- Hooks installed but bypassable
- Encourage but don't require
- Gather feedback

### Phase 3: Full Enforcement (Week 5+)

- CI/CD enforcement
- Required for all PRs
- Update contributing guide

## Troubleshooting

### Hook Failures

```bash
# Run specific hook manually
pre-commit run <hook-id> --all-files

# Debug hook
pre-commit run <hook-id> --verbose

# Show hook info
pre-commit run --show-diff-on-failure
```

### Performance Issues

```bash
# Profile hook execution
time pre-commit run --all-files

# Disable slow hooks temporarily
# Edit .pre-commit-config.yaml, set stages: [push]
```

### Version Conflicts

```bash
# Pin specific versions in .pre-commit-config.yaml
rev: v1.2.3  # Instead of 'main' or 'latest'
```

## Related Documents

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [CODE_STYLE.md](./CODE_STYLE.md) - Code style guide
- [CI_CD.md](./CI_CD.md) - CI/CD documentation

## References

- [Pre-commit Official Docs](https://pre-commit.com/)
- [Supported Hooks](https://pre-commit.com/hooks.html)
- [Creating Custom Hooks](https://pre-commit.com/#creating-new-hooks)

---

**Next Steps**:
1. Review recommendations with team
2. Create .pre-commit-config.yaml
3. Test on subset of developers
4. Roll out team-wide
5. Integrate with CI/CD
