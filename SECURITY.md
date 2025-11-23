# Security Policy

## 🔒 Reporting Security Vulnerabilities

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, please report security issues responsibly:

1. **Email**: Send details to [your-security-email@example.com]
2. **GitHub Security Advisories**: Use GitHub's private vulnerability reporting at:
   https://github.com/[your-org]/corporate_intel/security/advisories/new

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

We will acknowledge your email within 48 hours and provide a detailed response within 7 days.

## 🛡️ Security Measures

This project implements the following security controls:

### 1. Authentication & Authorization
- JWT-based authentication with HS256 algorithm
- Token expiration after 30 minutes (configurable)
- Password hashing with bcrypt
- Role-based access control (RBAC)

### 2. API Security
- Rate limiting: 60 requests/minute per IP (configurable)
- CORS protection with whitelist
- Input validation using Pydantic
- SQL injection prevention via parameterized queries
- XSS protection via content security policy

### 3. Data Protection
- Secrets stored as environment variables (never in code)
- Database passwords encrypted at rest
- TLS/SSL for all external connections
- PII data encryption in database

### 4. Infrastructure Security
- Docker container isolation
- Non-root container users
- Resource limits on containers
- Regular security updates
- Automated vulnerability scanning

### 5. Dependency Management
- Regular dependency updates
- Automated security scanning (Dependabot/Snyk)
- Minimal container base images
- No unnecessary packages

## 🔑 Credential Management

### Never Commit
- `.env` files with real credentials
- API keys or tokens
- Private keys (`.pem`, `.key` files)
- Database passwords
- OAuth secrets

### Best Practices
1. Use `.env.example` for templates
2. Generate strong secrets: `openssl rand -hex 32`
3. Rotate credentials regularly
4. Use secrets managers in production (Vault, AWS Secrets Manager)
5. Enable pre-commit hooks to prevent accidents

## 🚨 Known Exposed Credentials

⚠️ **IMPORTANT**: If you cloned this repository before [DATE], credentials were accidentally exposed in git history.

### Exposed Secrets (Must Rotate)
1. GitHub Personal Access Token
2. Alpha Vantage API Key
3. NewsAPI Key
4. Sentry DSN
5. Application SECRET_KEY
6. MinIO Access/Secret Keys
7. Database passwords

### Immediate Actions Required
1. **Rotate ALL credentials** listed above
2. **Generate new secrets**: See `docs/security/SECURITY_GUIDELINES.md`
3. **Update your local `.env`** file
4. **Never commit the new credentials**

### Remediation Status
- [x] Secrets removed from repository code
- [x] `.gitignore` updated
- [x] Pre-commit hooks installed
- [ ] Git history cleaned (requires: `./scripts/security/remove-secrets-from-history.sh`)
- [ ] All exposed credentials rotated

## 📋 Security Checklist

Before deploying to production:

- [ ] All `.env` files are in `.gitignore`
- [ ] No hardcoded credentials in source code
- [ ] Strong, unique passwords for all services
- [ ] TLS/SSL enabled for all external connections
- [ ] Rate limiting configured appropriately
- [ ] CORS origins limited to known domains
- [ ] Database backups configured
- [ ] Monitoring and alerting enabled
- [ ] Security headers configured
- [ ] Dependencies scanned for vulnerabilities
- [ ] Pre-commit hooks installed
- [ ] Secrets rotated after any exposure

## 🔍 Security Testing

Run security scans before commits:

```bash
# Scan for exposed secrets
./scripts/security/scan-secrets.sh

# Run security linter
bandit -r src/

# Check dependencies
pip-audit

# Run security tests
pytest tests/security/ -v
```

## 📚 Additional Resources

- [Security Guidelines](docs/security/SECURITY_GUIDELINES.md) - Detailed security practices
- [Secrets Management](docs/architecture/SECRETS_MANAGEMENT.md) - How to handle secrets
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Common vulnerabilities

## 🔄 Update Policy

- **Critical vulnerabilities**: Patched within 24 hours
- **High severity**: Patched within 7 days
- **Medium severity**: Patched within 30 days
- **Low severity**: Patched in next release

## 📜 Disclosure Policy

We follow a 90-day coordinated disclosure policy:

1. Issue reported to security team
2. We acknowledge within 48 hours
3. Fix developed and tested
4. Security advisory published
5. Public disclosure after 90 days or when fix is released

## 🏆 Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities:

<!-- List will be maintained here -->

---

**Last Updated**: [DATE]
**Security Contact**: [your-security-email@example.com]
