# Code Quality Quick Reference

## One-Page Cheat Sheet for Development Workflow

### Pre-commit Hooks

**Installation**
```bash
pip install -r requirements-dev.txt
pre-commit install
```

**Usage**
```bash
pre-commit run --all-files          # Run all hooks on all files
pre-commit run black                # Run specific hook
git commit --no-verify              # Bypass (emergency only)
SKIP=black,flake8 git commit        # Skip specific hooks
pre-commit autoupdate               # Update hook versions
```

### Code Formatting

**Black** (Auto-formatter)
```bash
black .                             # Format all files
black --check .                     # Check without changes
black --diff .                      # Show what would change
black src/api/                      # Format specific directory
```

**isort** (Import Sorter)
```bash
isort .                             # Sort all imports
isort --check-only .                # Check without changes
isort --diff .                      # Show what would change
isort src/                          # Sort specific directory
```

### Linting

**Flake8** (Style Checker)
```bash
flake8                              # Lint all code
flake8 src/                         # Lint specific directory
flake8 --statistics                 # Show error statistics
flake8 --show-source                # Show error source code
```

**Config**: `.flake8`
- Max line length: 100
- Max complexity: 10

### Type Checking

**mypy** (Static Type Checker)
```bash
mypy src/                           # Type check source
mypy src/ --verbose                 # Verbose output
mypy --html-report mypy-report      # Generate HTML report
mypy src/api/routes.py              # Check specific file
```

**Config**: `pyproject.toml` → `[tool.mypy]`
- Python version: 3.11
- Strict mode: Enabled

### Testing

**pytest** (Test Runner)
```bash
pytest                              # Run all tests
pytest tests/unit/                  # Run specific directory
pytest tests/unit/test_api.py       # Run specific file
pytest -k "test_user"               # Run tests matching pattern
pytest -m "not slow"                # Run by marker
pytest -n auto                      # Parallel execution
pytest -vv                          # Very verbose
pytest -x                           # Stop on first failure
pytest --lf                         # Run last failed
pytest --pdb                        # Drop to debugger on failure
```

### Coverage

**Quick Commands**
```bash
./scripts/run_coverage.sh           # Full coverage report
./scripts/coverage_check.sh         # Quick threshold check
open htmlcov/index.html             # View HTML report (macOS)
xdg-open htmlcov/index.html         # View HTML report (Linux)
```

**Manual Coverage**
```bash
pytest --cov=src                    # Basic coverage
pytest --cov=src --cov-report=html  # With HTML report
pytest --cov=src --cov-branch       # Branch coverage
pytest --cov=src --cov-fail-under=80 # Enforce threshold
coverage report --show-missing      # Show uncovered lines
coverage report --skip-covered      # Hide 100% covered
```

**Thresholds**
- Minimum: 80%
- Target: 90%+
- Branch coverage: Required

### Security

**Bandit** (Security Scanner)
```bash
bandit -r src/                      # Scan source code
bandit -r src/ -c pyproject.toml    # With config
bandit -r src/ -f json              # JSON output
```

**Safety** (Dependency Checker)
```bash
safety check                        # Check dependencies
safety check --json                 # JSON output
```

### CI/CD

**GitHub Actions Status**
- ✅ Pre-commit checks pass
- ✅ Type checking passes
- ✅ Tests pass with 80%+ coverage
- ✅ Security scan passes

**Local CI Simulation**
```bash
# Run all quality checks
pre-commit run --all-files && \
mypy src/ && \
./scripts/run_coverage.sh && \
bandit -r src/
```

### Common Workflows

#### Before Committing
```bash
# 1. Format code
black .
isort .

# 2. Check types
mypy src/

# 3. Run tests with coverage
./scripts/run_coverage.sh

# 4. Commit (hooks run automatically)
git add .
git commit -m "Your message"
```

#### Fixing Pre-commit Issues
```bash
# Let hooks auto-fix
git add .
git commit -m "Message"  # Hooks run and fix

# Review changes
git diff

# Commit fixes
git add .
git commit -m "Message"
```

#### Adding New Code
```bash
# 1. Write test first (TDD)
touch tests/unit/test_feature.py

# 2. Implement feature
vim src/feature.py

# 3. Run tests with coverage
pytest tests/unit/test_feature.py --cov=src.feature

# 4. Check coverage
coverage report --show-missing

# 5. Add missing tests if needed

# 6. Format and commit
black . && isort .
git add .
git commit -m "Add new feature"
```

#### Code Review Checklist
- [ ] Pre-commit checks pass
- [ ] Tests added/updated
- [ ] Coverage ≥ 80%
- [ ] Type hints present
- [ ] No security issues
- [ ] Documentation updated

### Configuration Files

**`.pre-commit-config.yaml`**
- Pre-commit hook configuration
- Hook versions and settings

**`.flake8`**
- Flake8 linting rules
- Line length, complexity limits

**`pyproject.toml`**
- Tool configurations:
  - `[tool.black]` - Formatting
  - `[tool.isort]` - Import sorting
  - `[tool.mypy]` - Type checking
  - `[tool.pytest.ini_options]` - Testing
  - `[tool.coverage.*]` - Coverage
  - `[tool.bandit]` - Security

**`requirements-dev.txt`**
- Development dependencies
- Tool versions

### Troubleshooting

**Pre-commit fails**
```bash
pre-commit clean                    # Clear cache
pre-commit install --install-hooks  # Reinstall
pre-commit run --all-files          # Run manually
```

**Coverage incorrect**
```bash
rm -rf .coverage .coverage.*        # Clear data
pytest --cov=src --cov-report=html  # Fresh run
```

**mypy errors**
```bash
mypy src/ --verbose                 # Verbose output
mypy --show-error-codes             # Show codes
mypy --ignore-missing-imports       # Ignore imports
```

**Tests fail in CI but pass locally**
```bash
# Check environment
pytest --verbose
pytest -vv --tb=long

# Check dependencies
pip list | grep -i package-name

# Simulate CI environment
docker run -it python:3.11 bash
```

### Quick Fixes

**Format all code**
```bash
black . && isort . && flake8
```

**Fix import order**
```bash
isort --force-single-line-imports .
isort .
```

**Update dependencies**
```bash
pip install -U -r requirements-dev.txt
pre-commit autoupdate
```

**Clean all caches**
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf .pytest_cache .mypy_cache .coverage htmlcov
```

### IDE Integration

**VS Code**
- Install: Python, Black Formatter, isort extensions
- Enable: Format on Save
- Configure: `.vscode/settings.json`

**PyCharm**
- External Tools: Black, isort, flake8, mypy
- File Watchers: Auto-format on save
- Enable: "Reformat code" on commit

### Performance Tips

**Speed up pre-commit**
```bash
pre-commit run --all-files --parallel
```

**Speed up tests**
```bash
pytest -n auto                      # Parallel execution
pytest -n 4                         # 4 workers
pytest --lf                         # Last failed only
pytest -k "TestClass"               # Specific tests
```

**Speed up coverage**
```bash
pytest --cov=src -n auto            # Parallel with coverage
./scripts/coverage_check.sh         # Quick check
```

### Resources

- [Pre-commit Setup Guide](PRE_COMMIT_SETUP.md)
- [Coverage Guide](COVERAGE_GUIDE.md)
- [Testing Strategy](../testing/TESTING_STRATEGY.md)
- [GitHub Actions](.github/workflows/tests.yml)

### Support

**Local Issues**: Check configuration files
**CI Issues**: Review GitHub Actions logs
**Tool Issues**: Consult tool documentation
**Project Issues**: Contact development team

---

**Remember**: Code quality is continuous, not a one-time check. Run tools frequently during development, not just before commits.
