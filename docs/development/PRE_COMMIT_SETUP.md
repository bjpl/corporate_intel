# Pre-commit Hooks Setup Guide

## Overview

This guide covers the setup and usage of pre-commit hooks for the Corporate Intelligence Platform. Pre-commit hooks automatically check code quality before commits, ensuring consistent standards across the codebase.

## Installation

### 1. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Install Pre-commit Hooks

```bash
pre-commit install

# Optional: Install commit message hooks
pre-commit install --hook-type commit-msg
```

### 3. Verify Installation

```bash
pre-commit --version
pre-commit run --all-files --verbose
```

## Hook Categories

### Code Formatting
- **Black**: Python code formatter (line-length: 100)
- **isort**: Import statement organizer (profile: black)

### Linting
- **Flake8**: Style guide enforcement (max-complexity: 10)

### Type Checking
- **mypy**: Static type checker (strict mode)

### Security
- **Bandit**: Security vulnerability scanner

### File Utilities
- Trailing whitespace remover
- End-of-file fixer
- YAML/JSON/TOML validators
- Large file checker (500KB limit)

### Documentation
- **Interrogate**: Docstring coverage (75% minimum)

## Running Pre-commit Hooks

### Automatic (on commit)
```bash
git add .
git commit -m "Your commit message"
```

### Manual Execution
```bash
# All hooks on all files
pre-commit run --all-files

# Staged files only
pre-commit run

# Specific hook
pre-commit run black --all-files
```

## Individual Tool Usage

### Black (Code Formatter)
```bash
black .
black --check .
black --diff .
```

### isort (Import Sorter)
```bash
isort .
isort --check-only .
isort --diff .
```

### Flake8 (Linter)
```bash
flake8
flake8 src/
flake8 --statistics
```

### mypy (Type Checker)
```bash
mypy src/
mypy src/ --verbose
mypy --html-report mypy-report
```

## Bypassing Hooks

```bash
# Skip all hooks (emergency only)
git commit --no-verify -m "Emergency fix"

# Skip specific hook
SKIP=black git commit -m "Message"
```

## Troubleshooting

### Hook Failures
```bash
# Run Black manually
black --check --diff .
black .

# Check isort
isort --check-only --diff .
isort .

# Identify Flake8 issues
flake8 --show-source
```

### Performance Issues
```bash
# Update hooks
pre-commit autoupdate

# Clean cache
pre-commit clean
pre-commit install-hooks
```

## Configuration Files

- `.pre-commit-config.yaml` - Main configuration
- `.flake8` - Linter settings
- `pyproject.toml` - Tool configurations

## Best Practices

1. Run hooks before committing
2. Fix issues locally
3. Update hooks regularly
4. Document bypass reasons
5. Use IDE integration

## Related Documentation

- [Coverage Guide](COVERAGE_GUIDE.md)
- [Code Quality Quick Reference](CODE_QUALITY_QUICK_REFERENCE.md)
