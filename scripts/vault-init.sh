#!/bin/bash
set -euo pipefail

# Vault Initialization and Configuration Script
# This script initializes Vault, creates policies, and configures secrets engines

VAULT_ADDR="${VAULT_ADDR:-https://vault.corporate-intel.internal:8200}"
export VAULT_ADDR

echo "🔐 Starting Vault initialization..."

# Check if Vault is already initialized
if vault status 2>/dev/null | grep -q "Initialized.*true"; then
    echo "✅ Vault is already initialized"
else
    echo "🚀 Initializing Vault..."
    vault operator init -key-shares=5 -key-threshold=3 > vault-keys.txt
    echo "⚠️  IMPORTANT: Save vault-keys.txt in a secure location and delete from server!"

    # Auto-unseal for first time (read keys from file)
    for i in {1..3}; do
        KEY=$(grep "Unseal Key $i:" vault-keys.txt | awk '{print $NF}')
        vault operator unseal "$KEY"
    done
fi

# Login with root token
ROOT_TOKEN=$(grep 'Initial Root Token:' vault-keys.txt | awk '{print $NF}')
vault login "$ROOT_TOKEN"

echo "📝 Creating policies..."

# Create corporate-intel policy
vault policy write corporate-intel /vault/policies/corporate-intel-policy.hcl

# Create read-only policy
vault policy write corporate-intel-readonly - <<EOF
path "secret/data/corporate-intel/*" {
  capabilities = ["read", "list"]
}
EOF

# Create admin policy
vault policy write corporate-intel-admin - <<EOF
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "database/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "pki/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

echo "🔧 Enabling secrets engines..."

# Enable KV v2 secrets engine
vault secrets enable -path=secret kv-v2

# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL database connection
vault write database/config/corporate-intel \
    plugin_name=postgresql-database-plugin \
    allowed_roles="corporate-intel-role" \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/corporate_intel?sslmode=require" \
    username="${POSTGRES_ADMIN_USER}" \
    password="${POSTGRES_ADMIN_PASSWORD}"

# Create database role for application
vault write database/roles/corporate-intel-role \
    db_name=corporate-intel \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; \
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# Enable PKI secrets engine for SSL certificates
vault secrets enable pki
vault secrets tune -max-lease-ttl=87600h pki

# Generate root CA
vault write -field=certificate pki/root/generate/internal \
    common_name="Corporate Intel Root CA" \
    ttl=87600h > CA_cert.crt

# Configure CA and CRL URLs
vault write pki/config/urls \
    issuing_certificates="$VAULT_ADDR/v1/pki/ca" \
    crl_distribution_points="$VAULT_ADDR/v1/pki/crl"

# Create PKI role for corporate-intel
vault write pki/roles/corporate-intel \
    allowed_domains="corporate-intel.internal,corporate-intel.com" \
    allow_subdomains=true \
    max_ttl="720h"

# Enable transit secrets engine for encryption
vault secrets enable transit
vault write -f transit/keys/corporate-intel

# Enable AWS secrets engine for dynamic credentials
vault secrets enable aws
vault write aws/config/root \
    access_key="${AWS_ACCESS_KEY}" \
    secret_key="${AWS_SECRET_KEY}" \
    region="us-east-1"

vault write aws/roles/corporate-intel-role \
    credential_type=iam_user \
    policy_document=-<<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::corporate-intel-*/*"]
    }
  ]
}
EOF

echo "🔑 Creating application secrets..."

# Database secrets
vault kv put secret/corporate-intel/db \
    username="${DB_USER}" \
    password="${DB_PASSWORD}" \
    url="postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/corporate_intel"

# Redis secrets
vault kv put secret/corporate-intel/redis \
    password="${REDIS_PASSWORD}"

# RabbitMQ secrets
vault kv put secret/corporate-intel/rabbitmq \
    username="${RABBITMQ_USER}" \
    password="${RABBITMQ_PASSWORD}"

# MinIO/S3 secrets
vault kv put secret/corporate-intel/minio \
    access_key="${MINIO_ACCESS_KEY}" \
    secret_key="${MINIO_SECRET_KEY}"

# JWT secrets
vault kv put secret/corporate-intel/jwt \
    secret_key="$(openssl rand -base64 32)" \
    auth_secret="$(openssl rand -base64 32)"

# API keys
vault kv put secret/corporate-intel/apis \
    openai="${OPENAI_API_KEY:-}" \
    anthropic="${ANTHROPIC_API_KEY:-}" \
    serp="${SERP_API_KEY:-}"

# Encryption keys
vault kv put secret/corporate-intel/encryption \
    key="$(openssl rand -base64 32)" \
    data_key="$(openssl rand -base64 32)"

echo "🔒 Enabling Kubernetes authentication..."

# Enable Kubernetes auth
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc:443" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
    token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Create Kubernetes auth role
vault write auth/kubernetes/role/corporate-intel \
    bound_service_account_names=corporate-intel-api \
    bound_service_account_namespaces=default,production,staging \
    policies=corporate-intel \
    ttl=1h

# Create production-specific role
vault write auth/kubernetes/role/corporate-intel-prod \
    bound_service_account_names=corporate-intel-api \
    bound_service_account_namespaces=production \
    policies=corporate-intel,corporate-intel-admin \
    ttl=1h

echo "✅ Vault initialization complete!"
echo ""
echo "📋 Summary:"
echo "  - Policies created: corporate-intel, corporate-intel-readonly, corporate-intel-admin"
echo "  - Secrets engines enabled: kv-v2, database, pki, transit, aws"
echo "  - Kubernetes authentication configured"
echo "  - Application secrets stored"
echo ""
echo "⚠️  SECURITY REMINDERS:"
echo "  1. Revoke the root token: vault token revoke $ROOT_TOKEN"
echo "  2. Securely store vault-keys.txt and delete from server"
echo "  3. Enable audit logging: vault audit enable file file_path=/vault/logs/audit.log"
echo "  4. Rotate secrets regularly using the rotation script"
