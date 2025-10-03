storage "consul" {
  address = "consul:8500"
  path    = "vault/"
}

# Alternative: File storage for development
# storage "file" {
#   path = "/vault/data"
# }

# Alternative: S3 storage for production
# storage "s3" {
#   bucket     = "corporate-intel-vault"
#   region     = "us-east-1"
#   access_key = "ACCESS_KEY"
#   secret_key = "SECRET_KEY"
# }

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/tls/tls.crt"
  tls_key_file  = "/vault/tls/tls.key"

  # Telemetry
  telemetry {
    unauthenticated_metrics_access = true
  }
}

# API address
api_addr = "https://vault.corporate-intel.internal:8200"

# Cluster address for HA
cluster_addr = "https://vault.corporate-intel.internal:8201"

# UI
ui = true

# Telemetry
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = false
  unauthenticated_metrics_access = true
}

# Seal configuration (auto-unseal with AWS KMS)
seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "arn:aws:kms:us-east-1:ACCOUNT:key/KEY-ID"
}

# High Availability configuration
ha_storage "consul" {
  address = "consul:8500"
  path    = "vault-ha/"
}

# Logging
log_level = "info"
log_format = "json"

# Performance tuning
max_lease_ttl = "768h"
default_lease_ttl = "168h"

# Disable mlock for containerized environments
disable_mlock = true

# Enable performance standby nodes
enable_ui = true
