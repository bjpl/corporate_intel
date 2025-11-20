# Security Guidelines for Contributors

## 🔒 Critical Security Rules

### 1. **NEVER Commit Secrets to Git**

**Prohibited items:**
- `.env` files with real credentials
- API keys, tokens, passwords
- Private keys (`.pem`, `.key` files)
- Database connection strings with passwords
- OAuth client secrets
- Encryption keys

### 2. **Exposed Credentials Found**

⚠️ **If you're reading this, credentials have been exposed in git history.**

**The following secrets were exposed and MUST be rotated:**
1. **GitHub Personal Access Token** - Rotate immediately at https://github.com/settings/tokens
2. **Alpha Vantage API Key** - Rotate at https://www.alphavantage.co/
3. **NewsAPI Key** - Rotate at https://newsapi.org/account
4. **Sentry DSN** - Rotate at https://sentry.io/settings/
5. **SECRET_KEY** - Generate new: `openssl rand -hex 32`
6. **MinIO Access/Secret Keys** - Generate new credentials
7. **Redis Password** - Change in docker-compose.yml and .env
8. **Grafana Password** - Reset admin password
9. **Superset Secret Key** - Generate new key

### 3. **Setting Up Your Environment**

```bash
# 1. Copy the example file
cp .env.example .env

# 2. Generate secure random keys
openssl rand -hex 32  # For SECRET_KEY
openssl rand -base64 32  # For other secrets

# 3. Edit .env and replace ALL placeholder values
nano .env  # or your preferred editor

# 4. Verify .env is in .gitignore
git check-ignore .env  # Should output: .env
```

### 4. **Pre-Commit Hooks**

Install pre-commit hooks to prevent accidental commits:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# This will scan for secrets before each commit
```

### 5. **API Security Best Practices**

#### Rate Limiting
- Enabled by default in production
- Configure `RATE_LIMIT_PER_MINUTE` in .env
- Per-endpoint limits defined in API code

#### CORS Configuration
- Production: Set specific allowed origins
- Never use `["*"]` in production
- Example: `CORS_ORIGINS=["https://yourdomain.com"]`

#### Authentication
- JWT tokens expire after 30 minutes (configurable)
- Tokens use HS256 algorithm with SECRET_KEY
- All protected endpoints require valid token

### 6. **Database Security**

#### Connection Security
- Use strong passwords (min 20 chars, mixed case, numbers, symbols)
- Never expose database ports publicly
- Use SSL/TLS in production: `?sslmode=require`

#### SQL Injection Prevention
- All queries use parameterized statements
- Input validation with Pydantic models
- Whitelist validation for dynamic SQL (see `companies.py:328`)

### 7. **External API Keys**

#### Minimum Required
- **SEC EDGAR**: No key needed, just valid User-Agent
- **Yahoo Finance**: No key needed (rate limited)

#### Optional APIs
- Alpha Vantage: Free tier sufficient for development
- NewsAPI: Free tier sufficient for testing
- GitHub: Only needed for repository analysis features
- Crunchbase: Optional, paid API

### 8. **Production Deployment**

#### Secrets Management
Use environment-specific secrets:

```bash
# Development
.env

# Staging
.env.staging  (not committed)

# Production
.env.production  (not committed, or use secrets manager)
```

#### Recommended: Use Secrets Manager
- **AWS Secrets Manager**: For AWS deployments
- **HashiCorp Vault**: Self-hosted option
- **Azure Key Vault**: For Azure deployments
- **GCP Secret Manager**: For GCP deployments

Example with Vault:
```bash
# Store secret
vault kv put secret/corporate-intel/db password=xxx

# Retrieve in code
from config.vault_integration import get_secret
password = get_secret("db/password")
```

### 9. **Security Headers**

The following headers are automatically added in production:

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### 10. **Dependency Security**

```bash
# Regularly check for vulnerabilities
pip install safety
safety check

# Or use
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt
```

### 11. **Monitoring & Alerting**

#### Log Security Events
- Failed authentication attempts
- Rate limit violations
- Invalid API keys
- SQL injection attempts

#### Set Up Alerts
- Sentry for error tracking
- Prometheus + AlertManager for metrics
- CloudWatch/DataDog for infrastructure

### 12. **Code Review Checklist**

Before submitting PRs, verify:
- [ ] No hardcoded credentials
- [ ] No `.env` files in commits
- [ ] Input validation on all user inputs
- [ ] SQL injection protection
- [ ] XSS protection for any rendered content
- [ ] CSRF protection for state-changing operations
- [ ] Rate limiting on public endpoints
- [ ] Authentication on protected endpoints
- [ ] Proper error messages (no sensitive info leaked)
- [ ] Dependencies updated and scanned

### 13. **Incident Response**

If credentials are exposed:

1. **Immediately rotate ALL exposed credentials**
2. **Remove from git history** (see below)
3. **Scan logs for unauthorized access**
4. **Notify affected parties if data breach occurred**
5. **Document incident and lessons learned**

#### Removing Secrets from Git History

```bash
# Option 1: Using git-filter-repo (recommended)
pip install git-filter-repo
git filter-repo --path .env --invert-paths
git push --force --all

# Option 2: Using BFG Repo Cleaner
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force --all

# Option 3: GitHub-specific
# Go to Settings > Security > Secret scanning
# GitHub will alert you to exposed secrets
```

### 14. **Security Testing**

```bash
# Run security tests
pytest tests/security/

# Check for common vulnerabilities
bandit -r src/

# Test authentication
pytest tests/api/v1/test_auth.py -v

# Test rate limiting
pytest tests/api/v1/test_rate_limiting.py -v
```

### 15. **Compliance**

- **GDPR**: If handling EU user data
- **SOC 2**: For enterprise customers
- **HIPAA**: If handling health data
- **PCI DSS**: If handling payment data

### 16. **Contact**

For security issues:
- **Do NOT** open public GitHub issues
- Email: [Your security contact email]
- Use GitHub Security Advisories for vulnerability disclosure

---

## Quick Reference

### Generate Secure Secrets

```bash
# SECRET_KEY (64 chars hex)
openssl rand -hex 32

# Generic secret (44 chars base64)
openssl rand -base64 32

# Strong password (24 chars alphanumeric)
openssl rand -base64 18

# UUID
python -c "import uuid; print(uuid.uuid4())"
```

### Check for Exposed Secrets

```bash
# Search for potential secrets
git grep -i "password\|secret\|api_key\|token" | grep -v ".md"

# Check if .env is tracked
git ls-files | grep .env

# Verify .gitignore is working
git check-ignore .env .env.local .env.production
```

### Emergency Credential Rotation

```bash
# Run the rotation script
./scripts/rotate-credentials.sh

# Or manually:
# 1. Update .env with new values
# 2. Restart all services
# 3. Update CI/CD secrets
# 4. Update production secrets manager
```

---

**Remember: Security is everyone's responsibility. When in doubt, ask!**
