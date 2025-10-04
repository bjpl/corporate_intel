# Secrets Management Guide

## Overview

This guide documents the security practices for managing sensitive credentials in the Corporate Intelligence Platform. All production secrets MUST be managed through a dedicated secrets management service.

## Critical Security Issues Remediated

### Audit Findings (2025-10-03)
1. **CRITICAL**: Hardcoded staging credentials removed from `.env.staging`
2. **CRITICAL**: JWT token removed from `.env` file
3. **HIGH**: Database passwords replaced with placeholders
4. **HIGH**: `.env.staging` and `.env.production` added to `.gitignore`
5. **MEDIUM**: Standardized credential placeholder format

## Secrets Management Options

### Option 1: HashiCorp Vault (Recommended for Enterprise)

**Advantages:**
- Open source with enterprise support
- Dynamic secrets generation
- Detailed audit logging
- Multi-cloud support
- Secret rotation automation

**Setup:**
```bash
# Install Vault
brew install vault  # macOS
# or
apt-get install vault  # Ubuntu

# Start Vault dev server (development only)
vault server -dev

# Set environment variables
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='your-vault-token'

# Store secrets
vault kv put secret/corporate-intel/production \
  postgres_password="$(openssl rand -base64 32)" \
  redis_password="$(openssl rand -base64 32)" \
  minio_secret_key="$(openssl rand -base64 32)" \
  secret_key="$(openssl rand -hex 32)"
```

**Python Integration:**
See `/config/vault_integration.py` for implementation details.

### Option 2: AWS Secrets Manager (Recommended for AWS Deployments)

**Advantages:**
- Native AWS integration
- Automatic secret rotation
- Fine-grained IAM permissions
- Pay-per-secret pricing
- Encrypted at rest with KMS

**Setup:**
```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Create secrets
aws secretsmanager create-secret \
  --name corporate-intel/production/postgres-password \
  --secret-string "$(openssl rand -base64 32)"

aws secretsmanager create-secret \
  --name corporate-intel/production/redis-password \
  --secret-string "$(openssl rand -base64 32)"
```

**Python Integration:**
See `/config/aws_secrets_integration.py` for implementation details.

### Option 3: Docker Secrets (For Docker Swarm/Compose)

**Advantages:**
- Built into Docker ecosystem
- No external dependencies
- Simple for containerized deployments

**Setup:**
```bash
# Create secrets
echo "$(openssl rand -base64 32)" | docker secret create postgres_password -
echo "$(openssl rand -base64 32)" | docker secret create redis_password -

# Use in docker-compose.yml
secrets:
  postgres_password:
    external: true
  redis_password:
    external: true
```

### Option 4: Kubernetes Secrets (For K8s Deployments)

**Setup:**
```bash
# Create namespace
kubectl create namespace corporate-intel

# Create secrets
kubectl create secret generic db-credentials \
  --from-literal=postgres-password="$(openssl rand -base64 32)" \
  --namespace=corporate-intel

# Use in deployment
env:
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: postgres-password
```

## Environment-Specific Configuration

### Development Environment
- Use `.env` file with placeholder values
- Generate local secrets: `python scripts/env_manager.py generate`
- Never commit `.env` to version control

### Staging Environment
- Use `.env.staging` with Vault/AWS Secrets Manager references
- Mirror production security practices
- Use separate secrets from production

### Production Environment
- **NEVER** use `.env.production` file in production
- Load all secrets from secrets management service
- Enable audit logging for all secret access
- Implement secret rotation policies

## Secret Generation

### Generate Secure Passwords
```bash
# PostgreSQL password (32 characters)
openssl rand -base64 32

# Secret key (64 hex characters)
openssl rand -hex 32

# API key (URL-safe)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Superset secret key (42 characters)
openssl rand -base64 42
```

### Automated Generation
```bash
# Use the provided script
python scripts/env_manager.py generate

# Or generate specific secrets
python scripts/env_manager.py generate --service postgres
python scripts/env_manager.py generate --service redis
```

## Security Best Practices

### 1. Secret Rotation
- Rotate production secrets every 90 days minimum
- Rotate immediately if compromise suspected
- Use automated rotation where possible
- Test rotation procedures regularly

### 2. Access Control
- Implement least privilege access
- Use service accounts for application access
- Enable MFA for human access to secrets
- Audit all secret access regularly

### 3. Secret Storage
- **NEVER** commit secrets to version control
- **NEVER** store secrets in container images
- **NEVER** log secret values
- **NEVER** expose secrets in error messages

### 4. Encryption
- Encrypt secrets at rest
- Use TLS for secrets in transit
- Implement envelope encryption for sensitive data
- Use separate encryption keys per environment

### 5. Monitoring & Auditing
- Enable access logging for all secrets
- Alert on unauthorized access attempts
- Monitor for secret exposure in logs
- Regular security audits

## Environment Variable Validation

The application validates all secrets on startup:

```python
# In src/core/config.py
@field_validator("SECRET_KEY")
@classmethod
def validate_secret_key(cls, v: SecretStr) -> SecretStr:
    """Validate SECRET_KEY for security requirements."""
    if len(v.get_secret_value()) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters")
    # Additional validation...
```

## Integration with Application

### Loading Secrets at Runtime

```python
from src.config.vault_integration import VaultSecretsManager

# Initialize secrets manager
secrets_manager = VaultSecretsManager()

# Load secrets into environment
secrets_manager.load_secrets_to_env(
    secret_path="secret/corporate-intel/production"
)

# Or retrieve specific secret
postgres_password = secrets_manager.get_secret(
    "secret/corporate-intel/production",
    "postgres_password"
)
```

### Docker Compose Integration

```yaml
version: '3.8'

services:
  api:
    image: corporate-intel:latest
    environment:
      - VAULT_ADDR=${VAULT_ADDR}
      - VAULT_TOKEN=${VAULT_TOKEN}
      - SECRET_PATH=secret/corporate-intel/production
    command: >
      sh -c "
        python config/vault_integration.py load &&
        python -m uvicorn src.main:app --host 0.0.0.0
      "
```

## Emergency Procedures

### Secret Compromise Response
1. **Immediate Actions:**
   - Revoke compromised secret
   - Generate new secret
   - Update all services
   - Review access logs

2. **Investigation:**
   - Determine scope of exposure
   - Identify affected systems
   - Document timeline
   - Notify stakeholders

3. **Remediation:**
   - Rotate all related secrets
   - Update access controls
   - Implement additional monitoring
   - Conduct security review

### Secret Recovery
- Maintain encrypted backups of Vault/secrets
- Document recovery procedures
- Test recovery process quarterly
- Keep recovery keys in secure offline storage

## Compliance & Audit

### Audit Trail Requirements
- All secret access must be logged
- Logs retained for minimum 1 year
- Logs must be immutable
- Regular compliance reviews

### Secret Inventory
Maintain inventory of all secrets:
- Secret name and purpose
- Rotation schedule
- Access permissions
- Last rotation date
- Responsible team/individual

## Migration Guide

### Moving from .env to Vault

1. **Preparation:**
   ```bash
   # Backup current secrets
   cp .env .env.backup.$(date +%Y%m%d)

   # Install Vault integration
   pip install hvac boto3
   ```

2. **Migration:**
   ```bash
   # Upload secrets to Vault
   python scripts/migrate_to_vault.py --env production
   ```

3. **Validation:**
   ```bash
   # Test secret retrieval
   python scripts/test_vault_connection.py
   ```

4. **Cleanup:**
   ```bash
   # Remove .env files from production
   rm .env.production
   ```

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [AWS Secrets Manager User Guide](https://docs.aws.amazon.com/secretsmanager/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_CheatSheet.html)
- [NIST SP 800-57: Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

## Support

For security concerns or questions about secrets management:
- Internal: Contact DevOps team
- Security incidents: security@corporate-intel.example.com
- Emergency: Use incident response procedures
