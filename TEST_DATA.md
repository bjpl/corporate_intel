# Test Data Documentation

This document describes the test data available for user testing the Corporate Intelligence Platform.

---

## Overview

The platform comes with seed data and sample data loaders to help you test all features with realistic EdTech company information.

---

## 🌱 Seed Data (dbt Seeds)

### Loading Seed Data

```bash
cd dbt
dbt seed
cd ..
```

### Available Seed Files

#### 1. Companies (`dbt/seeds/companies.csv`)

Sample EdTech companies for testing:

| Field | Description | Example |
|-------|-------------|---------|
| id | Company ID | 1, 2, 3 |
| name | Company name | "Coursera", "Duolingo" |
| ticker | Stock ticker | "COUR", "DUOL" |
| sector | Industry sector | "EdTech", "Online Learning" |
| description | Company description | "Leading online learning platform" |
| founded_year | Year founded | 2012 |
| headquarters | Location | "Mountain View, CA" |
| website | Company website | "https://coursera.com" |

**Sample Companies:**
- Coursera (COUR)
- Duolingo (DUOL)
- Chegg (CHGG)
- 2U Inc (TWOU)
- Udemy (Private)
- Khan Academy (Non-profit)

#### 2. Financial Metrics (`dbt/seeds/metrics.csv`)

Historical financial data for companies:

| Field | Description | Example |
|-------|-------------|---------|
| company_id | Foreign key to companies | 1 |
| metric_date | Date of metric | 2024-12-31 |
| revenue | Quarterly revenue | 150000000 |
| profit | Net profit | 25000000 |
| growth_rate | YoY growth % | 15.5 |
| market_cap | Market capitalization | 5000000000 |

**Time Periods Covered:**
- Q1 2023 - Q4 2024
- Quarterly intervals
- Multiple years for trend analysis

#### 3. User Accounts (`dbt/seeds/users.csv`)

Test user accounts:

| Username | Email | Role | Password (hashed) |
|----------|-------|------|-------------------|
| test_user | test@example.com | user | [hashed] |
| test_admin | admin@example.com | admin | [hashed] |
| test_analyst | analyst@example.com | analyst | [hashed] |

**Default Test Password**: `TestPassword123!`

---

## 🔄 Loading Sample Data via API

### Sample Company Data

Create a test company via API:

```bash
# 1. Login first
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"TestPassword123!"}' \
  | jq -r '.access_token')

# 2. Create company
curl -X POST http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test EdTech Startup",
    "ticker": "TEST",
    "sector": "EdTech",
    "description": "A test company for development",
    "founded_year": 2020,
    "headquarters": "San Francisco, CA",
    "website": "https://testedtech.example.com"
  }'
```

### Sample Financial Metrics

Add financial data for a company:

```bash
curl -X POST http://localhost:8000/api/v1/companies/1/metrics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_date": "2024-12-31",
    "revenue": 50000000,
    "profit": 5000000,
    "growth_rate": 25.0,
    "market_cap": 500000000,
    "stock_price": 45.50,
    "pe_ratio": 35.2
  }'
```

---

## 📊 Realistic Test Scenarios

### Scenario 1: High-Growth Startup

**Profile:**
- Name: "Rocket EdTech"
- Founded: 2021
- Growth Rate: 100%+ YoY
- Status: Pre-IPO

**Test Data:**
```json
{
  "name": "Rocket EdTech",
  "ticker": null,
  "sector": "K-12 Online Learning",
  "founded_year": 2021,
  "metrics": [
    {"metric_date": "2023-Q1", "revenue": 1000000, "growth_rate": 50},
    {"metric_date": "2023-Q2", "revenue": 2000000, "growth_rate": 100},
    {"metric_date": "2023-Q3", "revenue": 4000000, "growth_rate": 100},
    {"metric_date": "2023-Q4", "revenue": 8000000, "growth_rate": 100}
  ]
}
```

### Scenario 2: Mature Public Company

**Profile:**
- Name: "EduCorp Global"
- Founded: 2005
- Growth Rate: 5-10% YoY
- Status: Public (NYSE)

**Test Data:**
```json
{
  "name": "EduCorp Global",
  "ticker": "EDUC",
  "sector": "Higher Education",
  "founded_year": 2005,
  "metrics": [
    {"metric_date": "2024-Q1", "revenue": 500000000, "growth_rate": 7.5, "profit": 75000000},
    {"metric_date": "2024-Q2", "revenue": 510000000, "growth_rate": 8.0, "profit": 77000000},
    {"metric_date": "2024-Q3", "revenue": 520000000, "growth_rate": 6.5, "profit": 78000000}
  ]
}
```

### Scenario 3: Struggling Company

**Profile:**
- Name: "TechLearn Inc"
- Founded: 2015
- Growth Rate: Negative
- Status: Declining revenue

**Test Data:**
```json
{
  "name": "TechLearn Inc",
  "ticker": "TCHL",
  "sector": "Corporate Training",
  "founded_year": 2015,
  "metrics": [
    {"metric_date": "2024-Q1", "revenue": 100000000, "growth_rate": -5, "profit": -10000000},
    {"metric_date": "2024-Q2", "revenue": 95000000, "growth_rate": -10, "profit": -15000000},
    {"metric_date": "2024-Q3", "revenue": 85000000, "growth_rate": -15, "profit": -20000000}
  ]
}
```

---

## 🔌 External API Test Data

### SEC EDGAR Data

For testing SEC filing ingestion, use these real companies:

- **Coursera (COUR)**: CIK 0001651562
- **Duolingo (DUOL)**: CIK 0001788882
- **Chegg (CHGG)**: CIK 0001364954

**Test Filing Fetch:**
```python
from src.connectors.sec_edgar import SECEdgarConnector

connector = SECEdgarConnector()
filings = connector.get_company_filings(cik="0001651562", filing_type="10-K")
```

### Yahoo Finance Data

**Test Stock Data Fetch:**
```python
from src.connectors.yahoo_finance import YahooFinanceConnector

connector = YahooFinanceConnector()
stock_data = connector.get_stock_data(ticker="COUR", period="1y")
```

### Alpha Vantage Data

**Note:** Requires API key in `.env`

```python
from src.connectors.alpha_vantage import AlphaVantageConnector

connector = AlphaVantageConnector()
fundamentals = connector.get_company_overview(symbol="COUR")
```

---

## 🧪 Data Generation Scripts

### Generate Random Test Data

Create a script to generate bulk test data:

```python
# scripts/generate_test_data.py
import random
from datetime import datetime, timedelta
from src.db.models import Company, Metric
from src.db.session import SessionLocal

def generate_test_companies(count=50):
    """Generate random test companies."""
    db = SessionLocal()

    sectors = ["K-12", "Higher Ed", "Corporate Training", "Language Learning", "Test Prep"]

    for i in range(count):
        company = Company(
            name=f"EdTech Company {i+1}",
            ticker=f"EDU{i:02d}" if i % 2 == 0 else None,
            sector=random.choice(sectors),
            founded_year=random.randint(2010, 2023),
            headquarters=f"City {i+1}, State"
        )
        db.add(company)

    db.commit()
    db.close()

def generate_test_metrics(company_id, quarters=8):
    """Generate quarterly metrics for a company."""
    db = SessionLocal()

    base_revenue = random.randint(1000000, 100000000)
    growth_rate = random.uniform(-10, 50)

    for i in range(quarters):
        metric_date = datetime.now() - timedelta(days=90 * i)
        revenue = base_revenue * (1 + growth_rate/100) ** i

        metric = Metric(
            company_id=company_id,
            metric_date=metric_date,
            revenue=revenue,
            profit=revenue * random.uniform(-0.1, 0.2),
            growth_rate=growth_rate + random.uniform(-5, 5)
        )
        db.add(metric)

    db.commit()
    db.close()

if __name__ == "__main__":
    generate_test_companies(50)
    for company_id in range(1, 51):
        generate_test_metrics(company_id)
```

**Run:**
```bash
python scripts/generate_test_data.py
```

---

## 📥 Loading Production-Like Data

### Import from CSV

Prepare CSV files with production-like data:

```bash
# Import companies
python scripts/import_csv.py --file data/companies.csv --model Company

# Import metrics
python scripts/import_csv.py --file data/metrics.csv --model Metric
```

### Import from JSON

```bash
# Import bulk data
python scripts/import_json.py --file data/edtech_companies.json
```

---

## 🧹 Data Cleanup

### Reset Test Data

```bash
# Drop all tables and recreate
alembic downgrade base
alembic upgrade head

# Reload seed data
cd dbt && dbt seed --full-refresh && cd ..
```

### Delete Test Companies

```python
from src.db.session import SessionLocal
from src.db.models import Company

db = SessionLocal()

# Delete test companies (those with "Test" in name)
db.query(Company).filter(Company.name.like("%Test%")).delete()
db.commit()
```

---

## 🔍 Verifying Test Data

### Check Database Contents

```bash
# Connect to database
psql $DATABASE_URL

# Count companies
SELECT COUNT(*) FROM companies;

# View sample companies
SELECT id, name, ticker, sector FROM companies LIMIT 10;

# Check metrics
SELECT
    c.name,
    COUNT(m.id) as metric_count,
    MAX(m.metric_date) as latest_metric
FROM companies c
LEFT JOIN metrics m ON c.id = m.company_id
GROUP BY c.name;
```

### API Data Verification

```bash
# Get company count
curl http://localhost:8000/api/v1/companies?limit=1 \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.total'

# Get sample company
curl http://localhost:8000/api/v1/companies/1 \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

---

## 📋 Test Data Checklist

Before starting testing, verify:

- [ ] Seed data loaded successfully
- [ ] At least 5 companies in database
- [ ] At least 20 metrics records
- [ ] Test user accounts exist
- [ ] Sample companies span different sectors
- [ ] Metrics cover multiple time periods
- [ ] Both public and private companies included
- [ ] Mix of growing and declining companies
- [ ] Realistic revenue ranges
- [ ] External API keys configured (if testing integrations)

---

## 🎯 Recommended Test Data Sets

### Minimal Test Set (Quick Testing)
- 5 companies
- 2 quarters of metrics per company
- 1 test user
- **Setup time**: 2 minutes

### Standard Test Set (Full Testing)
- 20 companies
- 8 quarters of metrics per company
- 3 test users (user, analyst, admin)
- **Setup time**: 5 minutes

### Large Test Set (Performance Testing)
- 100+ companies
- 16+ quarters of metrics per company
- 10+ test users
- **Setup time**: 15 minutes
- **Use**: `python scripts/generate_test_data.py --large`

---

## 📊 Example Query Results

After loading seed data, you should see:

```sql
-- Company count by sector
SELECT sector, COUNT(*)
FROM companies
GROUP BY sector;

-- Output:
--  sector              | count
-- ---------------------+-------
--  EdTech             |    15
--  Online Learning    |    10
--  K-12               |     8
--  Higher Education   |     7
--  Corporate Training |     5
```

```sql
-- Revenue trends
SELECT
    c.name,
    m.metric_date,
    m.revenue,
    m.growth_rate
FROM companies c
JOIN metrics m ON c.id = m.company_id
WHERE c.ticker = 'COUR'
ORDER BY m.metric_date DESC
LIMIT 5;
```

---

## 🚀 Quick Start Commands

```bash
# Full test data setup
cd dbt
dbt deps
dbt seed --full-refresh
dbt run
cd ..

# Verify data loaded
psql $DATABASE_URL -c "SELECT COUNT(*) FROM companies;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM metrics;"

# Generate additional test data (optional)
python scripts/generate_test_data.py

# Ready to test!
```

---

## 📝 Notes

- **Data Privacy**: All test data is synthetic. Do not use real user data.
- **API Keys**: External API calls will fail without valid keys, but core functionality can still be tested.
- **Performance**: Large datasets (100+ companies) may slow down some queries. This is useful for performance testing.
- **Cleanup**: Always clean up test data before production deployment.

---

## Need Help?

- **Seed data not loading?** Check `dbt/seeds/` directory exists and files are valid CSV
- **Database connection issues?** Verify PostgreSQL is running: `docker-compose ps postgres`
- **Foreign key errors?** Ensure parent records (companies) exist before creating child records (metrics)
- **Data validation errors?** Check Pydantic models in `src/db/models.py` for constraints

Happy Testing! 🎉
