# API Configuration Setup Guide

## Overview

The Corporate Intelligence Platform integrates with multiple external APIs to provide comprehensive EdTech industry analysis. This guide covers all required API configurations.

## Required API Keys

### 1. SEC EDGAR API (FREE - REQUIRED)

**Purpose:** Access to financial filings (10-K, 10-Q, 8-K)

**Cost:** Free

**Configuration:**
```bash
SEC_USER_AGENT=Corporate Intel Platform/1.0 (your-email@example.com)
SEC_RATE_LIMIT=10
```

**Setup Instructions:**
- No API key required
- MUST include a valid email address in the User-Agent per SEC guidelines
- Rate limit: 10 requests/second
- Documentation: https://www.sec.gov/edgar/sec-api-documentation

**Required Libraries:**
- `sec-edgar-api>=1.0.0` (already in requirements.txt)

---

### 2. Yahoo Finance (FREE - NO KEY REQUIRED)

**Purpose:** Real-time stock data, financial metrics, quarterly statements

**Cost:** Free (no API key needed)

**Configuration:**
```bash
YAHOO_FINANCE_ENABLED=true
```

**Features:**
- Market cap, P/E ratios, revenue metrics
- Quarterly financial statements
- 52-week highs/lows
- Company profiles

**Required Libraries:**
- `yfinance>=0.2.33` (already in requirements.txt)

**Usage:** No authentication required - works out of the box

---

### 3. Alpha Vantage API (FREE TIER AVAILABLE - OPTIONAL)

**Purpose:** Fundamental data, financial statements, technical indicators

**Cost:** Free tier: 5 API calls/minute, 500 calls/day

**Configuration:**
```bash
ALPHA_VANTAGE_API_KEY=your_api_key_here
```

**Setup Instructions:**
1. Visit https://www.alphavantage.co/support/#api-key
2. Fill out the form (name, email, organization optional)
3. Receive API key immediately via email
4. Copy key to `.env` file

**Free Tier Limits:**
- 5 API calls per minute
- 500 calls per day
- No credit card required

**Required Libraries:**
- `alpha-vantage>=2.3.1` (already in requirements.txt)

---

### 4. NewsAPI (FREE TIER AVAILABLE - OPTIONAL)

**Purpose:** Market news, sentiment analysis, company coverage

**Cost:** Free tier: 100 requests/day

**Configuration:**
```bash
NEWSAPI_KEY=your_api_key_here
```

**Setup Instructions:**
1. Visit https://newsapi.org/register
2. Create free account with email
3. Verify email address
4. Copy API key from dashboard
5. Add to `.env` file

**Free Tier Limits:**
- 100 requests per day
- Developer plan (free)
- No credit card required
- 1-month historical data access

**Premium Features (Paid):**
- 250-100,000 requests/day
- Full historical data access
- Advanced filtering

---

### 5. Crunchbase API (PAID - OPTIONAL)

**Purpose:** Funding rounds, investor data, company acquisitions

**Cost:** Starting at $29/month (Basic API)

**Configuration:**
```bash
CRUNCHBASE_API_KEY=your_api_key_here
```

**Setup Instructions:**
1. Visit https://data.crunchbase.com/docs
2. Sign up for API access (requires payment)
3. Choose plan based on usage needs
4. Retrieve API key from dashboard
5. Add to `.env` file

**Note:** This API is optional but provides valuable funding insights for EdTech companies

---

### 6. GitHub API (FREE - OPTIONAL)

**Purpose:** Open source project metrics, developer activity tracking

**Cost:** Free (with authentication)

**Configuration:**
```bash
GITHUB_TOKEN=your_personal_access_token
```

**Setup Instructions:**
1. Visit https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `public_repo` (for public repositories)
   - `read:org` (if tracking organization metrics)
4. Generate token and copy immediately
5. Add to `.env` file

**Rate Limits:**
- Without token: 60 requests/hour
- With token: 5,000 requests/hour

**Required for:**
- Tracking EdTech open source projects
- Developer community engagement metrics

---

## Environment Setup

### Step 1: Copy Environment Template

```bash
cp .env.example .env
```

### Step 2: Generate Secure Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or use the env_manager tool
python scripts/env_manager.py generate --length 32
```

### Step 3: Configure Required APIs

**Minimum configuration for basic functionality:**

```bash
# Security (REQUIRED)
SECRET_KEY=<generated_from_step_2>

# Database (REQUIRED)
POSTGRES_PASSWORD=<secure_password>

# SEC EDGAR (REQUIRED)
SEC_USER_AGENT=Corporate Intel Platform/1.0 (your-email@example.com)

# Yahoo Finance (ENABLED BY DEFAULT)
YAHOO_FINANCE_ENABLED=true
```

### Step 4: Configure Optional APIs

Add API keys for enhanced features:

```bash
# Alpha Vantage (recommended for fundamental data)
ALPHA_VANTAGE_API_KEY=<your_key>

# NewsAPI (recommended for sentiment analysis)
NEWSAPI_KEY=<your_key>

# GitHub (recommended for open source tracking)
GITHUB_TOKEN=<your_token>

# Crunchbase (optional - paid)
CRUNCHBASE_API_KEY=<your_key>
```

### Step 5: Validate Configuration

```bash
# Validate environment variables
python scripts/env_manager.py validate

# Check Python and dependencies
./scripts/check-python-version.sh
```

---

## API Usage Summary

| API | Cost | Rate Limit | Required | Purpose |
|-----|------|-----------|----------|---------|
| SEC EDGAR | Free | 10/sec | ✅ Yes | Financial filings |
| Yahoo Finance | Free | Unlimited* | ✅ Yes | Stock data |
| Alpha Vantage | Free tier | 5/min | ⚠️ Recommended | Fundamental data |
| NewsAPI | Free tier | 100/day | ⚠️ Recommended | News & sentiment |
| GitHub | Free | 5000/hour** | ⚪ Optional | Open source metrics |
| Crunchbase | Paid | Varies | ⚪ Optional | Funding data |

\* Yahoo Finance has soft limits but generally unlimited for reasonable use
\** With authentication; 60/hour without

---

## EdTech Company Watchlist

The platform tracks these EdTech companies by default:

```bash
EDTECH_COMPANIES_WATCHLIST=["CHGG","COUR","DUOL","TWOU","ARCE","LAUR","INST","POWL"]
```

Companies tracked:
- **CHGG** - Chegg
- **COUR** - Coursera
- **DUOL** - Duolingo
- **TWOU** - 2U Inc.
- **ARCE** - Arco Platform
- **LAUR** - Laureate Education
- **INST** - Instructure
- **POWL** - Powell Industries (Powerschool)

---

## Data Sources Architecture

### Connector Classes

The platform uses dedicated connector classes in `/src/connectors/data_sources.py`:

1. **SECEdgarConnector** - SEC financial filings
2. **YahooFinanceConnector** - Real-time market data
3. **AlphaVantageConnector** - Fundamental analysis
4. **NewsAPIConnector** - Market sentiment
5. **CrunchbaseConnector** - Funding intelligence
6. **GitHubConnector** - Developer metrics
7. **DataAggregator** - Combines all sources

### Rate Limiting

Each connector implements automatic rate limiting:
- Prevents API quota exhaustion
- Respects provider guidelines
- Exponential backoff on errors

### Caching Strategy

- Response caching via Redis
- TTL varies by data type:
  - Stock prices: 5 minutes
  - Fundamental data: 1 hour
  - Historical filings: 24 hours

---

## Security Best Practices

### Environment Variables

1. **NEVER commit `.env` to version control**
   - Already in `.gitignore`
   - Use `.env.example` as template

2. **Use strong, unique passwords**
   ```bash
   python scripts/env_manager.py generate --length 32 --count 5
   ```

3. **Rotate credentials regularly**
   ```bash
   ./scripts/rotate-credentials.sh
   ```

4. **Set restrictive file permissions**
   ```bash
   chmod 600 .env
   ```

### API Key Security

- Store keys in environment variables, not code
- Use separate keys for dev/staging/production
- Monitor API usage for anomalies
- Revoke compromised keys immediately

---

## Testing API Configuration

### Quick Test Script

```python
import asyncio
from src.connectors.data_sources import DataAggregator

async def test_apis():
    aggregator = DataAggregator()

    # Test with a sample EdTech company
    result = await aggregator.get_comprehensive_company_data(
        ticker="DUOL",
        company_name="Duolingo"
    )

    print(f"SEC Filings: {len(result.get('sec_filings', []))}")
    print(f"Yahoo Finance: {bool(result.get('yahoo_finance'))}")
    print(f"Alpha Vantage: {bool(result.get('alpha_vantage'))}")
    print(f"News Articles: {len(result.get('news_sentiment', []))}")

asyncio.run(test_apis())
```

### Verify Individual APIs

```bash
# Test SEC EDGAR
python -c "from src.connectors.data_sources import SECEdgarConnector; import asyncio; c = SECEdgarConnector(); print(asyncio.run(c.get_company_filings('DUOL')))"

# Test Yahoo Finance
python -c "from src.connectors.data_sources import YahooFinanceConnector; import asyncio; c = YahooFinanceConnector(); print(asyncio.run(c.get_stock_info('DUOL')))"
```

---

## Troubleshooting

### Common Issues

**1. "SEC API rate limit exceeded"**
- Solution: Reduce `SEC_RATE_LIMIT` in `.env`
- Default: 10 requests/second (within limits)

**2. "Alpha Vantage API key invalid"**
- Solution: Verify key from https://www.alphavantage.co/
- Check for extra spaces in `.env` file

**3. "NewsAPI quota exceeded"**
- Solution: Free tier limited to 100 requests/day
- Consider caching results or upgrading plan

**4. "Yahoo Finance data not loading"**
- Solution: Check ticker symbol is correct
- Yahoo Finance has no rate limits but may block excessive requests

**5. "GitHub API rate limit"**
- Solution: Add `GITHUB_TOKEN` for 5000/hour limit
- Without token: only 60/hour

### Debug Mode

Enable detailed API logging:

```bash
LOG_LEVEL=DEBUG
```

Check logs in:
- Console output
- `logs/api-calls.log`
- Sentry (if configured)

---

## Cost Optimization

### Free Tier Strategy

**Recommended for development:**
- SEC EDGAR: Free (always)
- Yahoo Finance: Free (always)
- Alpha Vantage: Free tier (500 calls/day)
- NewsAPI: Free tier (100 calls/day)
- GitHub: Free with token (5000/hour)

**Total monthly cost: $0**

### Production Recommendations

**For production deployment:**
- Keep free tiers for SEC and Yahoo
- Upgrade Alpha Vantage if >500 calls/day needed
- Consider NewsAPI paid plan for real-time news
- Crunchbase API for comprehensive funding data

**Estimated production cost: $29-99/month** (depending on scale)

---

## Next Steps

1. ✅ Copy `.env.example` to `.env`
2. ✅ Configure required APIs (SEC, Yahoo)
3. ⚪ Sign up for recommended free APIs (Alpha Vantage, NewsAPI)
4. ⚪ Test API connectivity
5. ⚪ Review rate limits and caching
6. ⚪ Set up monitoring for API usage

For deployment, see:
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Infrastructure Setup](./INFRASTRUCTURE_SETUP.md)
- [Security Hardening](./SECURITY_GUIDE.md)

---

## Support

For API-related issues:
- Check provider documentation links above
- Review `/src/connectors/data_sources.py` implementation
- Enable debug logging for detailed error messages
- Contact API provider support for key/quota issues
