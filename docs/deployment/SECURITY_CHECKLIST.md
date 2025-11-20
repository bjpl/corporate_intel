# Production Security Checklist

**Version:** 1.0.0
**Last Updated:** 2025-10-25

---

## Pre-Deployment Security Review

### 1. Authentication & Authorization

#### API Authentication
- [ ] JWT tokens use RS256 (RSA) instead of HS256
- [ ] Access tokens expire within 15 minutes
- [ ] Refresh tokens expire within 7 days
- [ ] Token rotation implemented
- [ ] API keys hashed before storage (SHA-256)
- [ ] API key rotation policy defined (90 days)

#### User Authentication
- [ ] Password hashing uses bcrypt (cost factor >= 12)
- [ ] Password minimum length: 12 characters
- [ ] Account lockout after 5 failed attempts
- [ ] Password reset tokens expire within 1 hour
- [ ] Multi-factor authentication (MFA) supported
- [ ] Session timeout: 30 minutes inactive, 8 hours max

---

### 2. Network Security

#### SSL/TLS Configuration
- [ ] TLS 1.3 enabled (TLS 1.2 minimum)
- [ ] Strong cipher suites only (ECDHE-ECDSA, ECDHE-RSA)
- [ ] Certificate pinning for mobile clients
- [ ] HSTS header configured (max-age >= 31536000)
- [ ] OCSP stapling enabled
- [ ] Certificate auto-renewal configured (Let's Encrypt)

#### Network Policies
- [ ] Database port (5432) not exposed externally
- [ ] Redis port (6379) not exposed externally
- [ ] Admin interfaces behind VPN only
- [ ] Kubernetes network policies configured
- [ ] Firewall rules restrict traffic to known IPs
- [ ] DDoS protection enabled (Cloudflare/AWS Shield)

---

### 3. Secrets Management

#### Credential Storage
- [ ] No secrets in source code
- [ ] No secrets in container images
- [ ] Secrets stored in AWS Secrets Manager/Vault
- [ ] Environment variables encrypted at rest
- [ ] Secrets rotation automated
- [ ] Kubernetes secrets encrypted (at-rest encryption)

#### Secret Rotation Schedule
```yaml
Database Passwords:      90 days
API Keys:                60 days
JWT Signing Keys:        180 days
SSL Certificates:        Auto-renewal (Let's Encrypt)
Service Account Keys:    90 days
```

---

### 4. Data Protection

#### Encryption at Rest
- [ ] Database encryption enabled (PostgreSQL SSL)
- [ ] MinIO buckets encrypted (AES-256)
- [ ] Backup files encrypted before S3 upload
- [ ] Redis data persistence encrypted
- [ ] Logs encrypted in CloudWatch

#### Encryption in Transit
- [ ] All API endpoints use HTTPS
- [ ] Database connections use SSL/TLS
- [ ] Redis connections use TLS
- [ ] Internal service mesh uses mTLS
- [ ] External API calls use HTTPS

#### Data Retention
- [ ] PII data retention policy: 2 years
- [ ] Audit logs retention: 7 years
- [ ] Automated data deletion after retention period
- [ ] GDPR compliance: Right to be forgotten implemented
- [ ] Data anonymization for analytics

---

### 5. Container Security

#### Image Security
- [ ] Base images from trusted sources (python:3.11-slim)
- [ ] Multi-stage builds to minimize attack surface
- [ ] No secrets baked into images
- [ ] Regular vulnerability scanning (Trivy, Snyk)
- [ ] Image signing and verification
- [ ] Minimal user privileges (non-root user)

#### Runtime Security
```yaml
Security Context:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
```

- [ ] Containers run as non-root
- [ ] Read-only root filesystem
- [ ] No privileged containers
- [ ] Resource limits configured
- [ ] Security profiles (AppArmor/SELinux)

---

### 6. Dependency Security

#### Package Management
- [ ] All dependencies pinned to specific versions
- [ ] Automated dependency updates (Dependabot)
- [ ] Regular security audits (pip-audit, safety)
- [ ] CVE monitoring for dependencies
- [ ] Private PyPI mirror for internal packages

#### Vulnerability Scanning
```bash
# Run before each deployment
pip-audit --strict
safety check --json
trivy image corporate-intel:latest --severity HIGH,CRITICAL
```

- [ ] No HIGH/CRITICAL vulnerabilities in production
- [ ] Automated vulnerability scans in CI/CD
- [ ] Security patches applied within 7 days
- [ ] Emergency patches within 24 hours

---

### 7. Input Validation

#### API Request Validation
- [ ] All inputs validated with Pydantic models
- [ ] Request size limits enforced (10MB default)
- [ ] File upload restrictions (type, size)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (input sanitization)
- [ ] CSRF protection for state-changing operations

#### Rate Limiting
- [ ] API rate limiting enabled (100 req/min default)
- [ ] DDoS protection configured
- [ ] IP-based throttling
- [ ] Tiered rate limits (free, premium, enterprise)
- [ ] Rate limit headers in responses

---

### 8. Logging & Monitoring

#### Audit Logging
- [ ] All authentication attempts logged
- [ ] All authorization failures logged
- [ ] All data access logged (who, what, when)
- [ ] Admin actions logged
- [ ] Failed login attempts trigger alerts
- [ ] Logs immutable and tamper-proof

#### Security Monitoring
```yaml
Critical Alerts:
  - Multiple failed login attempts (>5 in 5 minutes)
  - Privilege escalation attempts
  - Unusual data access patterns
  - Suspicious API usage
  - Certificate expiration (<30 days)
  - Vulnerability scan failures
```

- [ ] Real-time security monitoring
- [ ] Anomaly detection configured
- [ ] SIEM integration (Splunk, DataDog)
- [ ] Security incident response plan
- [ ] Regular security reviews (quarterly)

---

### 9. Access Control

#### Principle of Least Privilege
- [ ] Service accounts have minimal permissions
- [ ] Database users have role-based access
- [ ] API endpoints require authentication
- [ ] Admin endpoints require additional authorization
- [ ] Temporary elevated access with expiration
- [ ] Regular access audits

#### Kubernetes RBAC
```yaml
ServiceAccount: corporate-intel-api
Permissions:
  - Read: ConfigMaps, Secrets
  - Write: Logs (stdout only)
  - No cluster-wide permissions
  - No access to other namespaces
```

---

### 10. Compliance

#### GDPR
- [ ] Privacy policy published
- [ ] Data processing agreements signed
- [ ] User consent mechanisms
- [ ] Right to access implemented
- [ ] Right to deletion implemented
- [ ] Data portability supported
- [ ] Data breach notification process

#### SOC 2
- [ ] Access controls documented
- [ ] Change management process
- [ ] Incident response plan
- [ ] Regular security audits
- [ ] Employee security training
- [ ] Vendor security assessments

#### PCI DSS (if handling payments)
- [ ] Cardholder data encrypted
- [ ] Network segmentation
- [ ] Regular penetration testing
- [ ] Secure coding practices
- [ ] Security awareness training

---

## Security Testing

### Automated Security Tests

**Pre-Deployment:**
```bash
# Static analysis
bandit -r src/ -ll
semgrep --config=auto src/

# Dependency scanning
pip-audit --strict
safety check --full-report

# Container scanning
trivy image corporate-intel:latest --severity CRITICAL
docker scout cves corporate-intel:latest

# Secret scanning
gitleaks detect --source . --verbose
```

### Manual Security Testing

**Quarterly:**
- [ ] Penetration testing by external firm
- [ ] Security code review
- [ ] Threat modeling workshop
- [ ] Social engineering tests
- [ ] Physical security audit

**Annual:**
- [ ] Full security audit (SOC 2)
- [ ] Compliance certification renewal
- [ ] Disaster recovery drill
- [ ] Incident response simulation

---

## Incident Response

### Security Incident Levels

**P0 - Critical (Response: Immediate)**
- Active data breach
- Ransomware attack
- Complete service outage
- Root compromise

**P1 - High (Response: 1 hour)**
- Suspicious data access
- Failed security controls
- Vulnerability exploitation attempt
- DDoS attack

**P2 - Medium (Response: 4 hours)**
- Multiple failed login attempts
- Anomalous API usage
- Security configuration drift
- Non-critical vulnerability

**P3 - Low (Response: 24 hours)**
- Security policy violation
- Minor configuration issue
- Informational security finding

### Incident Response Checklist

**Detection Phase:**
- [ ] Alert triggered via monitoring
- [ ] Incident severity assessed
- [ ] Incident commander assigned
- [ ] War room established (Slack #security-incidents)

**Containment Phase:**
- [ ] Affected systems isolated
- [ ] Attack vector identified
- [ ] Additional compromises checked
- [ ] Forensic evidence preserved

**Eradication Phase:**
- [ ] Vulnerabilities patched
- [ ] Malicious code removed
- [ ] Compromised credentials rotated
- [ ] Systems hardened

**Recovery Phase:**
- [ ] Services restored from clean backups
- [ ] Monitoring intensified
- [ ] User communications sent
- [ ] Regulatory notifications filed (if required)

**Post-Incident Phase:**
- [ ] Incident report written
- [ ] Root cause analysis completed
- [ ] Preventive measures implemented
- [ ] Team debriefing conducted
- [ ] Lessons learned documented

---

## Security Contacts

```yaml
Security Team:
  Email: security@corporate-intel.com
  Phone: +1-XXX-XXX-XXXX (24/7)
  PagerDuty: security-oncall

Vulnerability Reporting:
  Email: security-reports@corporate-intel.com
  GPG Key: https://corporate-intel.com/.well-known/security.txt
  Bug Bounty: https://hackerone.com/corporate-intel

Compliance:
  Email: compliance@corporate-intel.com
  DPO: dpo@corporate-intel.com
```

---

## Security Review Sign-Off

**Pre-Production Deployment:**

| Review Area | Status | Reviewer | Date |
|-------------|--------|----------|------|
| Authentication | ☐ Pass / ☐ Fail | ___________ | _____ |
| Network Security | ☐ Pass / ☐ Fail | ___________ | _____ |
| Secrets Management | ☐ Pass / ☐ Fail | ___________ | _____ |
| Data Protection | ☐ Pass / ☐ Fail | ___________ | _____ |
| Container Security | ☐ Pass / ☐ Fail | ___________ | _____ |
| Dependency Security | ☐ Pass / ☐ Fail | ___________ | _____ |
| Input Validation | ☐ Pass / ☐ Fail | ___________ | _____ |
| Logging & Monitoring | ☐ Pass / ☐ Fail | ___________ | _____ |
| Access Control | ☐ Pass / ☐ Fail | ___________ | _____ |
| Compliance | ☐ Pass / ☐ Fail | ___________ | _____ |

**Final Approval:**

Security Lead: ___________________________ Date: __________

CTO/Engineering Lead: ____________________ Date: __________

---

**Document Version:** 1.0.0
**Next Review:** 2025-11-25
