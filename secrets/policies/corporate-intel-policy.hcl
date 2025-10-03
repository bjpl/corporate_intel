# Policy for Corporate Intel application
path "secret/data/corporate-intel/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/corporate-intel/*" {
  capabilities = ["list", "read"]
}

# Database credentials
path "database/creds/corporate-intel-role" {
  capabilities = ["read"]
}

# PKI for SSL certificates
path "pki/issue/corporate-intel" {
  capabilities = ["create", "update"]
}

# Transit encryption
path "transit/encrypt/corporate-intel" {
  capabilities = ["update"]
}

path "transit/decrypt/corporate-intel" {
  capabilities = ["update"]
}

# AWS dynamic credentials
path "aws/creds/corporate-intel-role" {
  capabilities = ["read"]
}

# Read-only access to common secrets
path "secret/data/common/*" {
  capabilities = ["read", "list"]
}
