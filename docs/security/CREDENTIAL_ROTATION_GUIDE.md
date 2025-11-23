# Credential Rotation Guide

## 🔄 Immediate Action Required

Credentials were exposed in git history. ALL must be rotated immediately.

## 🚨 Exposed Credentials Checklist

### 1. GitHub Personal Access Token
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Full access to your GitHub repositories

**Steps to Rotate**:
```bash
# 1. Go to https://github.com/settings/tokens
# 2. Find the exposed token and click "Delete"
# 3. Generate new token with same scopes:
#    - repo (if using private repos)
#    - read:org (for organization access)
# 4. Update .env file:
GITHUB_TOKEN=your_new_token_here
# 5. Update any CI/CD secrets
```

### 2. Alpha Vantage API Key
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Unauthorized stock market data access

**Steps to Rotate**:
```bash
# 1. Go to https://www.alphavantage.co/support/#support
# 2. Request a new API key
# 3. Update .env:
ALPHA_VANTAGE_API_KEY=your_new_key_here
```

### 3. NewsAPI Key
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Unauthorized news API access

**Steps to Rotate**:
```bash
# 1. Log in to https://newsapi.org/account
# 2. Generate new API key
# 3. Update .env:
NEWSAPI_KEY=your_new_key_here
```

### 4. Application SECRET_KEY
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Session hijacking, JWT forgery

**Steps to Rotate**:
```bash
# Generate new secret (64 hex characters)
openssl rand -hex 32

# Update .env:
SECRET_KEY=your_new_64_char_hex_key_here

# IMPORTANT: This will invalidate all existing user sessions
# Users will need to log in again
```

### 5. MinIO Access/Secret Keys
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Unauthorized object storage access

**Steps to Rotate**:
```bash
# For Docker setup:
# 1. Generate new keys:
MINIO_ACCESS_KEY=$(openssl rand -hex 16)
MINIO_SECRET_KEY=$(openssl rand -hex 32)

# 2. Update docker-compose.yml:
environment:
  MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
  MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}

# 3. Update .env:
MINIO_ACCESS_KEY=your_new_access_key
MINIO_SECRET_KEY=your_new_secret_key

# 4. Restart MinIO:
docker-compose restart minio
```

### 6. Database Passwords
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Unauthorized database access

**Steps to Rotate**:
```bash
# For PostgreSQL:
# 1. Connect to database:
psql -U postgres -d corporate_intel

# 2. Change password:
ALTER USER postgres WITH PASSWORD 'your_new_secure_password';

# 3. Update .env:
POSTGRES_PASSWORD=your_new_secure_password

# 4. Restart application
```

### 7. Redis Password
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Unauthorized cache access

**Steps to Rotate**:
```bash
# 1. Update docker-compose.yml:
services:
  redis:
    command: redis-server --requirepass your_new_redis_password

# 2. Update .env:
REDIS_PASSWORD=your_new_redis_password

# 3. Restart Redis:
docker-compose restart redis
```

### 8. Grafana Password
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Unauthorized monitoring access

**Steps to Rotate**:
```bash
# 1. Generate new password:
openssl rand -base64 24

# 2. Update .env:
GRAFANA_PASSWORD=your_new_password

# 3. Reset admin password in Grafana:
docker exec -it grafana grafana-cli admin reset-admin-password your_new_password
```

### 9. Superset Secret Key
**Current Status**: EXPOSED - ROTATE IMMEDIATELY
**Impact**: Session hijacking in Superset

**Steps to Rotate**:
```bash
# Generate new key:
openssl rand -base64 32

# Update .env:
SUPERSET_SECRET_KEY=your_new_key

# Restart Superset:
docker-compose restart superset
```

### 10. Sentry DSN
**Current Status**: EXPOSED - ROTATE (Lower Priority)
**Impact**: Error tracking data visibility

**Steps to Rotate**:
```bash
# 1. Go to Sentry.io
# 2. Project Settings > Client Keys (DSN)
# 3. Revoke old key and generate new one
# 4. Update .env:
SENTRY_DSN=https://new_key@ingest.sentry.io/project_id
```

## 🔧 Automated Rotation Script

Run this script to help automate rotation:

```bash
#!/bin/bash
# scripts/rotate-all-credentials.sh

echo "🔄 Credential Rotation Helper"
echo "============================="
echo ""
echo "This script will help you rotate all credentials."
echo "You will need to manually update external services (GitHub, Alpha Vantage, etc.)"
echo ""

# Generate new secrets
NEW_SECRET_KEY=$(openssl rand -hex 32)
NEW_MINIO_ACCESS=$(openssl rand -hex 16)
NEW_MINIO_SECRET=$(openssl rand -hex 32)
NEW_POSTGRES_PASSWORD=$(openssl rand -base64 24)
NEW_REDIS_PASSWORD=$(openssl rand -base64 16)
NEW_GRAFANA_PASSWORD=$(openssl rand -base64 24)
NEW_SUPERSET_SECRET=$(openssl rand -base64 32)

echo "✅ Generated new local secrets"
echo ""
echo "Add these to your .env file:"
echo "SECRET_KEY=$NEW_SECRET_KEY"
echo "MINIO_ACCESS_KEY=$NEW_MINIO_ACCESS"
echo "MINIO_SECRET_KEY=$NEW_MINIO_SECRET"
echo "POSTGRES_PASSWORD=$NEW_POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$NEW_REDIS_PASSWORD"
echo "GRAFANA_PASSWORD=$NEW_GRAFANA_PASSWORD"
echo "SUPERSET_SECRET_KEY=$NEW_SUPERSET_SECRET"
echo ""
echo "⚠️  MANUAL STEPS REQUIRED:"
echo "1. Rotate GitHub token: https://github.com/settings/tokens"
echo "2. Rotate Alpha Vantage key: https://www.alphavantage.co/"
echo "3. Rotate NewsAPI key: https://newsapi.org/account"
echo "4. Update database password: psql -U postgres"
echo "5. Restart all services: docker-compose restart"
```

## ✅ Verification Checklist

After rotation, verify:

- [ ] All services start successfully
- [ ] Database connections work
- [ ] API endpoints respond correctly
- [ ] External APIs (Alpha Vantage, NewsAPI) work
- [ ] Authentication still works (users need to re-login)
- [ ] MinIO object storage accessible
- [ ] Redis cache working
- [ ] Grafana dashboards accessible
- [ ] No old credentials remain in .env
- [ ] CI/CD pipeline secrets updated
- [ ] Production secrets manager updated (if applicable)

## 🔒 Post-Rotation Security

After rotating credentials:

1. **Remove from git history**:
   ```bash
   ./scripts/security/remove-secrets-from-history.sh
   ```

2. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

3. **Run security scan**:
   ```bash
   ./scripts/security/scan-secrets.sh
   ```

4. **Verify .gitignore**:
   ```bash
   git check-ignore .env .env.local .env.production
   # Should output all three files
   ```

5. **Test with dummy credentials**:
   ```bash
   # Try to commit a test .env file
   cp .env.example .env.test
   git add .env.test
   git commit -m "test"
   # Should be blocked by pre-commit hook
   ```

## 📅 Rotation Schedule

Establish a regular rotation schedule:

| Credential | Rotation Frequency | Next Due |
|------------|-------------------|----------|
| SECRET_KEY | Every 90 days | [DATE] |
| Database passwords | Every 90 days | [DATE] |
| API keys | Every 180 days | [DATE] |
| Service tokens | Every 90 days | [DATE] |

Set calendar reminders for each rotation date.

## 📞 Support

If you encounter issues during rotation:
1. Check service logs: `docker-compose logs [service]`
2. Verify .env file syntax
3. Ensure no trailing spaces/newlines
4. Restart services: `docker-compose restart`
5. Contact team lead if issues persist

---

**Last Updated**: [DATE]
**Next Review**: [DATE + 90 days]
