# Security Setup Guide

## Overview

This guide covers the secure configuration of the Corporate Intelligence Platform, focusing on credential management and security best practices.

## Critical Security Requirements

### 1. Environment Variables

**NEVER commit actual credentials to version control!**

All sensitive credentials MUST be stored in environment variables and loaded from a `.env` file that is excluded from version control.

### 2. Initial Setup

```bash
# 1. Copy the example environment file
cp .env.example .env

# 2. Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Update .env with your actual credentials
# Edit .env and replace all REPLACE_WITH_* placeholders
```

### 3. Required Credentials

The following credentials MUST be set before running the application:

#### Database
- `POSTGRES_PASSWORD` - PostgreSQL database password
- `REDIS_PASSWORD` - Redis cache password (optional but recommended)

#### Object Storage
- `MINIO_ACCESS_KEY` - MinIO access key
- `MINIO_SECRET_KEY` - MinIO secret key

#### Application Security
- `SECRET_KEY` - JWT signing key (generate with secrets.token_urlsafe(32))

#### Monitoring (Production)
- `GRAFANA_PASSWORD` - Grafana admin password
- `SUPERSET_SECRET_KEY` - Apache Superset secret key

### 4. Optional API Keys

These API keys enhance functionality but are optional:

- `ALPHA_VANTAGE_API_KEY` - Financial data (free tier available)
- `NEWSAPI_KEY` - News sentiment analysis (free tier available)
- `CRUNCHBASE_API_KEY` - Funding data (paid API)
- `GITHUB_TOKEN` - GitHub metrics (free with personal access token)

## Security Validation

The application includes automatic security validation on startup:

```python
# Validates that:
# 1. All required secrets are set
# 2. No default/placeholder values in production
# 3. Secret values meet minimum security requirements
```

## Fixed Security Issues

### 1. Hardcoded API Keys (FIXED)

**Before:**
```python
class NewsAPIConnector:
    def __init__(self):
        self.api_key = "YOUR_NEWSAPI_KEY"  # SECURITY ISSUE!
```

**After:**
```python
class NewsAPIConnector:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.NEWSAPI_KEY if hasattr(self.settings, 'NEWSAPI_KEY') else None
        if not self.api_key:
            logger.warning("NewsAPI key not configured")
```

### 2. Default SECRET_KEY (FIXED)

**Before:**
```python
SECRET_KEY: SecretStr = Field(
    default=SecretStr("change-me-in-production")  # SECURITY ISSUE!
)
```

**After:**
```python
SECRET_KEY: SecretStr = Field(
    description="Secret key for JWT and sessions - MUST be set via environment variable"
)
# No default value - application will fail to start if not set
```

### 3. Weak Secret Validation (FIXED)

Enhanced validation now rejects:
- Empty secrets
- Placeholder values ("your-secret-key-here", "change-me-in-production")
- Missing required credentials

## Credential Management Best Practices

### Development

```bash
# Use separate .env file for development
cp .env.example .env.development

# Never commit .env files
git status  # Should NOT show .env files
```

### Production

```bash
# Use environment variables directly (no .env file)
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export POSTGRES_PASSWORD="$(openssl rand -base64 32)"

# Or use a secrets manager:
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
```

### CI/CD

```bash
# Store secrets in CI/CD platform:
# - GitHub Secrets
# - GitLab CI/CD Variables
# - CircleCI Environment Variables

# Reference in pipeline:
docker run -e SECRET_KEY="${SECRET_KEY}" ...
```

## Verification Checklist

- [ ] `.env` file exists and is properly configured
- [ ] `.env` is listed in `.gitignore`
- [ ] `SECRET_KEY` is at least 32 characters
- [ ] All database passwords are strong (12+ characters)
- [ ] No hardcoded credentials in source code
- [ ] API keys are stored as environment variables
- [ ] `.env.example` has no actual secrets
- [ ] Production uses secrets manager or env vars

## Testing Credentials

For testing purposes ONLY, test fixtures use hardcoded test credentials that are safe:

```python
# tests/conftest.py - Safe for testing
password="Test123!@#"  # Only used in test database
```

These are:
- Only used in isolated test environments
- Never used in production
- Part of test fixtures that create temporary users

## Emergency Response

If credentials are accidentally committed:

1. **Immediately rotate all exposed credentials**
2. **Revoke the compromised keys/passwords**
3. **Remove from git history:**
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```
4. **Force push (coordinate with team)**
5. **Audit access logs for unauthorized usage**

## Monitoring

Set up alerts for:
- Failed authentication attempts
- API key usage anomalies
- Unusual database access patterns
- Environment variable changes

## Resources

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Python Secrets Module](https://docs.python.org/3/library/secrets.html)
- [Pydantic SecretStr](https://docs.pydantic.dev/latest/concepts/types/#secret-types)
