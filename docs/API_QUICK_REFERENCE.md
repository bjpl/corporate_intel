# API Configuration Quick Reference

## Minimum Required Configuration

```bash
# Copy and customize this in your .env file

# ===========================
# SECURITY (REQUIRED)
# ===========================
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(32))">

# ===========================
# DATABASE (REQUIRED)
# ===========================
POSTGRES_PASSWORD=<secure_password_here>

# ===========================
# SEC EDGAR (REQUIRED)
# ===========================
SEC_USER_AGENT=Corporate Intel Platform/1.0 (YOUR-EMAIL@example.com)
SEC_RATE_LIMIT=10

# ===========================
# YAHOO FINANCE (FREE - ENABLED)
# ===========================
YAHOO_FINANCE_ENABLED=true
```

## Recommended Free APIs

```bash
# ===========================
# ALPHA VANTAGE (FREE TIER)
# ===========================
# Get key: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=

# Limits: 5 calls/min, 500 calls/day
# Use for: Fundamental data, financial statements

# ===========================
# NEWSAPI (FREE TIER)
# ===========================
# Get key: https://newsapi.org/register
NEWSAPI_KEY=

# Limits: 100 requests/day
# Use for: Market sentiment, company news

# ===========================
# GITHUB (FREE WITH TOKEN)
# ===========================
# Get token: https://github.com/settings/tokens
GITHUB_TOKEN=

# Limits: 5000 requests/hour with token
# Use for: Open source metrics, developer activity
```

## Optional Premium APIs

```bash
# ===========================
# CRUNCHBASE (PAID)
# ===========================
# Get key: https://data.crunchbase.com/docs
CRUNCHBASE_API_KEY=

# Cost: $29+/month
# Use for: Funding rounds, investor data
```

## Setup Commands

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Validate configuration
python scripts/env_manager.py validate

# 4. Test API connectivity
python -c "from src.connectors.data_sources import DataAggregator; import asyncio; asyncio.run(DataAggregator().get_comprehensive_company_data('DUOL', 'Duolingo'))"
```

## API Rate Limits Summary

| API              | Free Tier Limit       | With Key Limit    |
|------------------|-----------------------|-------------------|
| SEC EDGAR        | 10/second             | 10/second         |
| Yahoo Finance    | Unlimited*            | Unlimited*        |
| Alpha Vantage    | 5/min, 500/day        | 5/min, 500/day    |
| NewsAPI          | 100/day               | 100+/day (paid)   |
| GitHub           | 60/hour               | 5000/hour         |
| Crunchbase       | N/A                   | Varies (paid)     |

*Soft limits apply

## Configuration File Locations

- **Main config**: `/src/core/config.py`
- **Connectors**: `/src/connectors/data_sources.py`
- **Environment**: `/.env` (never commit!)
- **Template**: `/.env.example` (commit safe)
- **Validation**: `/scripts/env_manager.py`

## Testing Individual APIs

```python
# SEC EDGAR
from src.connectors.data_sources import SECEdgarConnector
import asyncio
sec = SECEdgarConnector()
filings = asyncio.run(sec.get_company_filings('DUOL'))
print(f"Found {len(filings)} filings")

# Yahoo Finance
from src.connectors.data_sources import YahooFinanceConnector
yf = YahooFinanceConnector()
info = asyncio.run(yf.get_stock_info('DUOL'))
print(f"Market Cap: ${info.get('market_cap', 0):,}")

# Alpha Vantage
from src.connectors.data_sources import AlphaVantageConnector
av = AlphaVantageConnector()
overview = asyncio.run(av.get_company_overview('DUOL'))
print(f"P/E Ratio: {overview.get('pe_ratio', 'N/A')}")
```

## Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| SEC rate limit error | Reduce `SEC_RATE_LIMIT` to 5-8 |
| Yahoo Finance timeout | Verify internet connection, ticker symbol |
| Alpha Vantage "Invalid API key" | Check key has no spaces, verify at alphavantage.co |
| NewsAPI quota exceeded | Free tier = 100/day, cache results or upgrade |
| GitHub 403 error | Add `GITHUB_TOKEN` for higher rate limit |

## EdTech Companies Tracked

Default watchlist in `.env`:

```bash
EDTECH_COMPANIES_WATCHLIST=["CHGG","COUR","DUOL","TWOU","ARCE","LAUR","INST","POWL"]
```

- **CHGG**: Chegg
- **COUR**: Coursera
- **DUOL**: Duolingo
- **TWOU**: 2U Inc.
- **ARCE**: Arco Platform
- **LAUR**: Laureate Education
- **INST**: Instructure (Canvas LMS)
- **POWL**: Powell Industries (Powerschool)

## Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] `SECRET_KEY` is 32+ characters
- [ ] All passwords are strong and unique
- [ ] API keys stored in `.env`, not code
- [ ] File permissions: `chmod 600 .env`
- [ ] Different keys for dev/staging/prod
- [ ] Regular credential rotation enabled

## Resources

- **Full Setup Guide**: [API_SETUP_GUIDE.md](./API_SETUP_GUIDE.md)
- **SEC EDGAR API**: https://www.sec.gov/edgar/sec-api-documentation
- **Alpha Vantage**: https://www.alphavantage.co/documentation/
- **NewsAPI**: https://newsapi.org/docs
- **yfinance**: https://github.com/ranaroussi/yfinance
- **GitHub API**: https://docs.github.com/en/rest
