# Version Constraints Quick Reference Card

## 🎯 Constraint Format Rules

### Stable Packages (≥1.0)
```
package>=X.Y.Z,<(X+1).0.0
```
Example: `fastapi>=0.104.0,<1.0.0`

### Pre-1.0 Packages
```
package>=0.X.Y,<1.0.0
```
Example: `asyncpg>=0.29.0,<1.0.0`

### Beta/Special Cases
Review individually, typically:
```
package>=X.Yb0,<1.0.0
```

## 🚨 High Priority Monitoring (3 packages)

| Package | Constraint | Why Monitor |
|---------|------------|-------------|
| yfinance | >=0.2.33,<1.0.0 | External Yahoo Finance API changes |
| great-expectations | >=0.18.0,<1.0.0 | Pre-1.0, evolving data validation API |
| opentelemetry-instrumentation-fastapi | >=0.42b0,<1.0.0 | Beta package, tracing critical |

## ⚠️ Medium Priority (11 packages)

asyncpg, pgvector, pandera, prefect-dask, aiocache, prometheus-client, loguru, pdfplumber, alpha-vantage, pytest-asyncio, httpx, ruff

## ✅ Stable & Low Risk (47 packages)

All major frameworks and tools with mature APIs

## 📋 Update Strategy

| Type | Timeframe | Action |
|------|-----------|--------|
| Security | Immediate | Apply patch within constraints |
| Bug Fix | 48 hours | Test and deploy |
| Feature | Quarterly | Review and plan |
| Major | Planned | Migration with full testing |

## 🔍 File Status

- ✅ requirements.txt - Complete (42 packages)
- ⏳ requirements-dev.txt - Needs update (16 packages)  
- ⏳ pyproject.toml - Needs sync

## 📚 Full Documentation

1. **dependency-version-constraints-research.md** - Detailed analysis
2. **version-constraints-summary.md** - Quick reference
3. **version-constraints-table.md** - Complete table
4. **phase1-step7-completion-summary.md** - Completion report

## 🛠️ Next Steps

1. Apply constraints to requirements-dev.txt
2. Sync pyproject.toml dependencies
3. Generate requirements.lock
4. Configure Dependabot
5. Setup CI/CD version tests
