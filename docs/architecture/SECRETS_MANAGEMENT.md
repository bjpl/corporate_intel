# Secrets Management Architecture

## Overview

This document details the secrets management architecture for the Corporate Intelligence Platform, implementing HashiCorp Vault as the primary secrets manager with AWS Secrets Manager as a backup/failover solution.

---

## Architecture Decision

**Primary**: HashiCorp Vault (self-hosted)
**Backup**: AWS Secrets Manager
**Rationale**: See [ADR-001](/mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docs/architecture/adr/001-secrets-management.md)

---

## Vault Architecture

### Deployment Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│                    HashiCorp Vault Cluster                       │
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │ Vault Node 1 │────│ Vault Node 2 │────│ Vault Node 3 │   │
│  │  (Active)    │     │  (Standby)   │     │  (Standby)   │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                    │                    │             │
│         └────────────────────┼────────────────────┘             │
│                              │                                  │
│                              ▼                                  │
│                    ┌──────────────────┐                        │
│                    │  Consul Cluster  │                        │
│                    │  (HA Storage)    │                        │
│                    └──────────────────┘                        │
│                                                                  │
│  Auto-Unseal: AWS KMS (arn:aws:kms:us-east-1:...)              │
│  TLS: Let's Encrypt certificates (auto-renewed)                 │
│  Access: AppRole authentication for services                    │
└─────────────────────────────────────────────────────────────────┘
```

### Secrets Engines Configuration

#### 1. KV Secrets Engine v2 (Static Secrets)

```hcl
# Enable KV v2 secrets engine
vault secrets enable -version=2 -path=secret kv

# Create application secrets
vault kv put secret/corporate-intel/database \
  username="intel_prod_user" \
  password="<GENERATED_STRONG_PASSWORD>" \
  host="postgres" \
  port="5432" \
  database="corporate_intel_prod"

vault kv put secret/corporate-intel/redis \
  password="<GENERATED_STRONG_PASSWORD>" \
  host="redis" \
  port="6379"

vault kv put secret/corporate-intel/minio \
  access_key="<GENERATED_ACCESS_KEY>" \
  secret_key="<GENERATED_SECRET_KEY>" \
  endpoint="minio:9000"

vault kv put secret/corporate-intel/api \
  secret_key="<GENERATED_JWT_SECRET>" \
  alpha_vantage_api_key="<YOUR_KEY>" \
  newsapi_key="<YOUR_KEY>"

# Staging environment
vault kv put secret/corporate-intel/staging/database \
  username="intel_staging_user" \
  password="<STAGING_PASSWORD>"
```

#### 2. Database Secrets Engine (Dynamic Secrets)

```hcl
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL connection
vault write database/config/corporate-intel \
  plugin_name=postgresql-database-plugin \
  allowed_roles="corporate-intel-role,readonly-role" \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/corporate_intel_prod" \
  username="vault_admin" \
  password="<VAULT_DB_ADMIN_PASSWORD>"

# Create role for application
vault write database/roles/corporate-intel-role \
  db_name=corporate-intel \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; \
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="24h" \
  max_ttl="72h"

# Read-only role for analytics
vault write database/roles/readonly-role \
  db_name=corporate-intel \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="24h" \
  max_ttl="72h"
```

#### 3. PKI Secrets Engine (SSL Certificates)

```hcl
# Enable PKI secrets engine
vault secrets enable pki
vault secrets tune -max-lease-ttl=8760h pki

# Generate root CA
vault write -field=certificate pki/root/generate/internal \
  common_name="Corporate Intel Root CA" \
  ttl=87600h > CA_cert.crt

# Configure CA and CRL URLs
vault write pki/config/urls \
  issuing_certificates="https://vault.corporate-intel.internal:8200/v1/pki/ca" \
  crl_distribution_points="https://vault.corporate-intel.internal:8200/v1/pki/crl"

# Create role for API certificates
vault write pki/roles/corporate-intel \
  allowed_domains="corporate-intel.com,corporate-intel.internal" \
  allow_subdomains=true \
  max_ttl="2160h" \
  generate_lease=true

# Issue certificate
vault write pki/issue/corporate-intel \
  common_name="api.corporate-intel.com" \
  ttl="2160h" > api_cert.pem
```

#### 4. Transit Secrets Engine (Encryption as a Service)

```hcl
# Enable transit secrets engine
vault secrets enable transit

# Create encryption key for PII data
vault write -f transit/keys/corporate-intel

# Encryption policy
vault write transit/keys/corporate-intel/config \
  min_encryption_version=1 \
  deletion_allowed=false \
  exportable=false \
  allow_plaintext_backup=false

# Encrypt data
vault write transit/encrypt/corporate-intel \
  plaintext=$(echo "sensitive-data" | base64)

# Decrypt data
vault write transit/decrypt/corporate-intel \
  ciphertext="vault:v1:..."
```

#### 5. AWS Secrets Engine (Dynamic AWS Credentials)

```hcl
# Enable AWS secrets engine
vault secrets enable aws

# Configure AWS credentials
vault write aws/config/root \
  access_key=<AWS_ACCESS_KEY> \
  secret_key=<AWS_SECRET_KEY> \
  region=us-east-1

# Create role for S3 access
vault write aws/roles/s3-backup-role \
  credential_type=iam_user \
  policy_document=-<<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::corporate-intel-backups/*"
    }
  ]
}
EOF

# Generate credentials (24-hour TTL)
vault read aws/creds/s3-backup-role
```

---

## Authentication Methods

### 1. AppRole (Service Authentication)

```bash
# Enable AppRole authentication
vault auth enable approle

# Create policy for corporate-intel application
vault policy write corporate-intel - <<EOF
# Read application secrets
path "secret/data/corporate-intel/*" {
  capabilities = ["read", "list"]
}

# Generate dynamic database credentials
path "database/creds/corporate-intel-role" {
  capabilities = ["read"]
}

# Encrypt/decrypt with transit engine
path "transit/encrypt/corporate-intel" {
  capabilities = ["update"]
}

path "transit/decrypt/corporate-intel" {
  capabilities = ["update"]
}

# Issue SSL certificates
path "pki/issue/corporate-intel" {
  capabilities = ["create", "update"]
}
EOF

# Create AppRole
vault write auth/approle/role/corporate-intel \
  token_policies="corporate-intel" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=0

# Get RoleID (store in secure location)
vault read auth/approle/role/corporate-intel/role-id

# Generate SecretID (one-time use recommended)
vault write -f auth/approle/role/corporate-intel/secret-id
```

### 2. Kubernetes Authentication (Future)

```bash
# Enable Kubernetes authentication
vault auth enable kubernetes

# Configure Kubernetes connection
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Create role for corporate-intel service account
vault write auth/kubernetes/role/corporate-intel \
  bound_service_account_names=corporate-intel-api \
  bound_service_account_namespaces=production,staging \
  policies=corporate-intel \
  ttl=1h
```

---

## Application Integration

### Python Integration (FastAPI)

```python
# src/core/vault_client.py

import hvac
from typing import Dict, Any
from functools import lru_cache
import os

class VaultClient:
    """HashiCorp Vault client for secrets management."""

    def __init__(self):
        self.client = hvac.Client(
            url=os.getenv("VAULT_ADDR", "https://vault:8200"),
            verify=True  # Use CA cert in production
        )
        self._authenticate()

    def _authenticate(self):
        """Authenticate using AppRole method."""
        role_id = os.getenv("VAULT_ROLE_ID")
        secret_id = os.getenv("VAULT_SECRET_ID")

        if not role_id or not secret_id:
            raise ValueError("VAULT_ROLE_ID and VAULT_SECRET_ID must be set")

        self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id
        )

    def get_secret(self, path: str) -> Dict[str, Any]:
        """Read secret from KV v2 engine."""
        response = self.client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point="secret"
        )
        return response['data']['data']

    def get_database_credentials(self, role: str = "corporate-intel-role") -> Dict[str, str]:
        """Generate dynamic database credentials."""
        response = self.client.secrets.database.generate_credentials(
            name=role
        )
        return {
            'username': response['data']['username'],
            'password': response['data']['password'],
            'lease_id': response['lease_id'],
            'lease_duration': response['lease_duration']
        }

    def renew_lease(self, lease_id: str):
        """Renew a lease before it expires."""
        self.client.sys.renew_lease(lease_id=lease_id)

    def encrypt_data(self, plaintext: str) -> str:
        """Encrypt data using Transit engine."""
        import base64
        plaintext_b64 = base64.b64encode(plaintext.encode()).decode()

        response = self.client.secrets.transit.encrypt_data(
            name="corporate-intel",
            plaintext=plaintext_b64
        )
        return response['data']['ciphertext']

    def decrypt_data(self, ciphertext: str) -> str:
        """Decrypt data using Transit engine."""
        import base64
        response = self.client.secrets.transit.decrypt_data(
            name="corporate-intel",
            ciphertext=ciphertext
        )
        plaintext_b64 = response['data']['plaintext']
        return base64.b64decode(plaintext_b64).decode()

@lru_cache
def get_vault_client() -> VaultClient:
    """Get cached Vault client instance."""
    return VaultClient()
```

### Settings Integration

```python
# src/core/config.py (updated)

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .vault_client import get_vault_client

class Settings(BaseSettings):
    """Application settings with Vault integration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    # Vault configuration
    VAULT_ADDR: str = Field(default="https://vault:8200")
    VAULT_ROLE_ID: str = Field(description="AppRole Role ID")
    VAULT_SECRET_ID: str = Field(description="AppRole Secret ID")
    USE_VAULT: bool = Field(default=True)

    # Database (loaded from Vault or env)
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "corporate_intel"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load secrets from Vault if enabled
        if self.USE_VAULT:
            self._load_from_vault()

    def _load_from_vault(self):
        """Load secrets from Vault."""
        try:
            vault = get_vault_client()

            # Load static secrets
            db_secrets = vault.get_secret("corporate-intel/database")
            self.POSTGRES_USER = db_secrets['username']
            self.POSTGRES_PASSWORD = db_secrets['password']
            self.POSTGRES_HOST = db_secrets['host']
            self.POSTGRES_PORT = int(db_secrets['port'])
            self.POSTGRES_DB = db_secrets['database']

            # Load Redis secrets
            redis_secrets = vault.get_secret("corporate-intel/redis")
            self.REDIS_PASSWORD = redis_secrets['password']

            # Load MinIO secrets
            minio_secrets = vault.get_secret("corporate-intel/minio")
            self.MINIO_ACCESS_KEY = minio_secrets['access_key']
            self.MINIO_SECRET_KEY = minio_secrets['secret_key']

            # Load API secrets
            api_secrets = vault.get_secret("corporate-intel/api")
            self.SECRET_KEY = api_secrets['secret_key']
            self.ALPHA_VANTAGE_API_KEY = api_secrets.get('alpha_vantage_api_key')

        except Exception as e:
            # Fallback to environment variables
            print(f"Warning: Failed to load from Vault: {e}")
            print("Falling back to environment variables")

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Lease Renewal Background Task

```python
# src/core/vault_renewal.py

import asyncio
from loguru import logger
from .vault_client import get_vault_client

class LeaseRenewalService:
    """Background service for renewing Vault leases."""

    def __init__(self):
        self.vault = get_vault_client()
        self.leases = {}
        self.running = False

    async def start(self):
        """Start lease renewal background task."""
        self.running = True
        asyncio.create_task(self._renewal_loop())

    async def stop(self):
        """Stop lease renewal background task."""
        self.running = False

    def register_lease(self, lease_id: str, lease_duration: int):
        """Register a lease for automatic renewal."""
        self.leases[lease_id] = {
            'duration': lease_duration,
            'renew_at': asyncio.get_event_loop().time() + (lease_duration * 0.8)
        }

    async def _renewal_loop(self):
        """Background loop for renewing leases."""
        while self.running:
            current_time = asyncio.get_event_loop().time()

            for lease_id, lease_info in list(self.leases.items()):
                if current_time >= lease_info['renew_at']:
                    try:
                        self.vault.renew_lease(lease_id)
                        lease_info['renew_at'] = current_time + (lease_info['duration'] * 0.8)
                        logger.info(f"Renewed lease {lease_id}")
                    except Exception as e:
                        logger.error(f"Failed to renew lease {lease_id}: {e}")
                        del self.leases[lease_id]

            await asyncio.sleep(60)  # Check every minute
```

---

## Docker Compose Configuration

```yaml
# docker-compose.vault.yml

version: '3.8'

services:
  consul:
    image: consul:latest
    container_name: corporate-intel-consul
    command: agent -server -ui -bootstrap-expect=1 -client=0.0.0.0
    ports:
      - "8500:8500"
      - "8600:8600/udp"
    volumes:
      - consul_data:/consul/data
    networks:
      - vault-network
    healthcheck:
      test: ["CMD", "consul", "members"]
      interval: 10s
      timeout: 5s
      retries: 5

  vault:
    image: hashicorp/vault:latest
    container_name: corporate-intel-vault
    depends_on:
      consul:
        condition: service_healthy
    ports:
      - "8200:8200"
    environment:
      VAULT_ADDR: 'https://0.0.0.0:8200'
      VAULT_API_ADDR: 'https://vault:8200'
      VAULT_DEV_ROOT_TOKEN_ID: '${VAULT_DEV_ROOT_TOKEN:-dev-only-token}'
    volumes:
      - vault_data:/vault/data
      - ./secrets/vault-config.hcl:/vault/config/vault.hcl:ro
      - ./secrets/tls:/vault/tls:ro
    cap_add:
      - IPC_LOCK
    networks:
      - vault-network
      - corporate-intel-network
    command: server
    healthcheck:
      test: ["CMD", "vault", "status"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Vault UI (development only)
  vault-ui:
    image: djenriquez/vault-ui:latest
    container_name: vault-ui
    depends_on:
      - vault
    ports:
      - "8000:8000"
    environment:
      VAULT_URL_DEFAULT: https://vault:8200
      VAULT_AUTH_DEFAULT: TOKEN
    networks:
      - vault-network
    profiles:
      - development

networks:
  vault-network:
    driver: bridge
    name: vault-network
  corporate-intel-network:
    external: true

volumes:
  consul_data:
    name: corporate-intel-consul-data
  vault_data:
    name: corporate-intel-vault-data
```

---

## Backup and Disaster Recovery

### Vault Backup Strategy

```bash
#!/bin/bash
# scripts/vault-backup.sh

BACKUP_DIR="/backups/vault"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Take Consul snapshot (Vault HA storage)
docker exec corporate-intel-consul consul snapshot save \
  /consul/data/backup_${TIMESTAMP}.snap

# Copy snapshot to backup location
docker cp corporate-intel-consul:/consul/data/backup_${TIMESTAMP}.snap \
  ${BACKUP_DIR}/consul_snapshot_${TIMESTAMP}.snap

# Upload to S3
aws s3 cp ${BACKUP_DIR}/consul_snapshot_${TIMESTAMP}.snap \
  s3://corporate-intel-vault-backups/

# Retention: Keep 30 days
find ${BACKUP_DIR} -name "consul_snapshot_*.snap" -mtime +30 -delete

echo "Vault backup completed: ${TIMESTAMP}"
```

### Disaster Recovery Procedure

```bash
#!/bin/bash
# scripts/vault-restore.sh

BACKUP_ID=$1

# Stop Vault
docker-compose -f docker-compose.vault.yml down vault

# Restore Consul snapshot
docker cp ${BACKUP_DIR}/consul_snapshot_${BACKUP_ID}.snap \
  corporate-intel-consul:/tmp/restore.snap

docker exec corporate-intel-consul consul snapshot restore \
  /tmp/restore.snap

# Start Vault
docker-compose -f docker-compose.vault.yml up -d vault

# Unseal Vault (use unseal keys)
vault operator unseal <UNSEAL_KEY_1>
vault operator unseal <UNSEAL_KEY_2>
vault operator unseal <UNSEAL_KEY_3>

echo "Vault restored from backup: ${BACKUP_ID}"
```

---

## Security Best Practices

1. **Seal/Unseal Keys**
   - Use Shamir's Secret Sharing (5 keys, threshold 3)
   - Store unseal keys in separate secure locations
   - Use AWS KMS auto-unseal in production

2. **Root Token**
   - Generate root token only when needed
   - Revoke immediately after use
   - Never store root token

3. **Audit Logging**
   ```hcl
   vault audit enable file file_path=/vault/logs/audit.log
   ```

4. **Network Security**
   - TLS 1.3 only
   - Mutual TLS for service authentication
   - Firewall rules (allow only necessary IPs)

5. **Access Control**
   - Principle of least privilege
   - Time-bound tokens (short TTLs)
   - Regular access reviews

---

## Monitoring and Alerts

### Prometheus Metrics

```yaml
# prometheus.yml

scrape_configs:
  - job_name: 'vault'
    metrics_path: '/v1/sys/metrics'
    params:
      format: ['prometheus']
    bearer_token: '<VAULT_METRICS_TOKEN>'
    static_configs:
      - targets: ['vault:8200']
```

### Critical Alerts

```yaml
# alerts/vault.yml

groups:
  - name: vault_alerts
    rules:
      - alert: VaultSealed
        expr: vault_core_unsealed == 0
        for: 1m
        annotations:
          summary: "Vault is sealed"

      - alert: VaultLeaderLost
        expr: vault_core_leadership_lost_count > 0
        for: 5m
        annotations:
          summary: "Vault lost leadership"

      - alert: VaultHighRequestRate
        expr: rate(vault_core_handle_request_count[5m]) > 1000
        for: 10m
        annotations:
          summary: "Vault request rate > 1000/s"
```

---

## Migration from Environment Variables

### Phase 1: Dual Mode (Current + Vault)

```python
# Support both env vars and Vault
if USE_VAULT:
    settings = load_from_vault()
else:
    settings = load_from_env()
```

### Phase 2: Vault Primary, Env Fallback

```python
try:
    settings = load_from_vault()
except VaultError:
    logger.warning("Vault unavailable, using environment variables")
    settings = load_from_env()
```

### Phase 3: Vault Only

```python
settings = load_from_vault()
# No fallback to env vars
```

---

## Cost Analysis

### Solo Developer Deployment

| Component | Cost | Notes |
|-----------|------|-------|
| **Vault** | $0 | Self-hosted (open-source) |
| **Consul** | $0 | Self-hosted (open-source) |
| **AWS KMS** | ~$1/month | Auto-unseal key only |
| **S3 Backups** | ~$5/month | Snapshot storage |
| **Total** | **~$6/month** | Minimal operational cost |

### AWS Secrets Manager Comparison

| Component | Cost | Notes |
|-----------|------|-------|
| **Secrets** | $0.40/secret/month | 20 secrets = $8/month |
| **API Calls** | $0.05/10,000 calls | ~$10/month at scale |
| **Total** | **~$18/month** | 3x more expensive |

**Decision**: Vault is more cost-effective for solo deployment while providing more features.

---

## Next Steps

1. **Week 1**: Deploy Vault in development
   ```bash
   docker-compose -f docker-compose.vault.yml up -d
   vault operator init
   vault operator unseal (x3)
   ```

2. **Week 2**: Configure secrets engines and policies
   ```bash
   ./scripts/vault-setup.sh
   ```

3. **Week 3**: Integrate with application
   ```bash
   # Update config.py with Vault integration
   # Deploy to staging for testing
   ```

4. **Week 4**: Production deployment
   ```bash
   # Configure AWS KMS auto-unseal
   # Deploy to production
   # Migrate secrets from env vars
   ```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-03
**Author**: System Architect Agent
