# Production Security Hardening Guide

## Security Layers Overview

This guide implements defense-in-depth security for the Corporate Intelligence Platform production deployment.

## 1. SSL/TLS Configuration

### NGINX SSL Configuration

Create production-ready NGINX SSL configuration:

**File: config/nginx-ssl.conf**

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name corporate-intel.yourdomain.com api.corporate-intel.yourdomain.com;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name corporate-intel.yourdomain.com;

    # SSL Certificate Configuration
    ssl_certificate /etc/letsencrypt/live/corporate-intel.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/corporate-intel.yourdomain.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/corporate-intel.yourdomain.com/chain.pem;

    # SSL Protocol Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # SSL Session Configuration
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req zone=api_limit burst=20 nodelay;
    limit_req_status 429;

    # Connection Limiting
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    limit_conn addr 10;

    # Hide NGINX Version
    server_tokens off;

    # API Proxy Configuration
    location /api/ {
        # Rate limiting for API
        limit_req zone=api_limit burst=20 nodelay;

        # Proxy settings
        proxy_pass http://api:8000/api/;
        proxy_http_version 1.1;

        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }

    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://api:8000/health;
        access_log off;
    }

    # Static assets caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Logging
    access_log /var/log/nginx/access.log combined;
    error_log /var/log/nginx/error.log warn;
}

# API subdomain
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.corporate-intel.yourdomain.com;

    # SSL configuration (same as main server)
    ssl_certificate /etc/letsencrypt/live/corporate-intel.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/corporate-intel.yourdomain.com/privkey.pem;

    # Same SSL settings as main server
    include /etc/nginx/conf.d/ssl-common.conf;

    # CORS configuration for API
    add_header 'Access-Control-Allow-Origin' 'https://corporate-intel.yourdomain.com' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
    add_header 'Access-Control-Max-Age' '3600' always;

    # Handle preflight
    if ($request_method = 'OPTIONS') {
        return 204;
    }

    location / {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL Certificate Automation

**File: scripts/ssl/renew-certificates.sh**

```bash
#!/bin/bash
# Automatic SSL certificate renewal

set -e

DOMAIN="corporate-intel.yourdomain.com"
EMAIL="ssl-admin@yourdomain.com"

# Renew certificates
certbot renew --quiet --deploy-hook "docker-compose -f /opt/corporate-intel/docker-compose.production.yml restart nginx"

# Check expiration (alert if < 30 days)
EXPIRY_DATE=$(openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "WARNING: SSL certificate expires in $DAYS_LEFT days"
    # Send alert
    curl -X POST "https://api.yourdomain.com/alerts" \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"SSL certificate expires in $DAYS_LEFT days\", \"severity\": \"warning\"}"
fi
```

## 2. Firewall Configuration

### UFW Firewall Rules

```bash
#!/bin/bash
# Configure UFW firewall for production

# Reset UFW
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# SSH (change port if using non-standard)
ufw allow 22/tcp comment 'SSH'

# HTTP/HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Docker network (internal only)
ufw allow from 172.20.0.0/16 to any comment 'Docker internal'

# Limit SSH connections (prevent brute force)
ufw limit 22/tcp

# Enable firewall
ufw --force enable

# Show status
ufw status verbose
```

### iptables Rules (Alternative)

```bash
#!/bin/bash
# iptables firewall rules

# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (with rate limiting)
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 -j DROP
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow Docker internal network
iptables -A INPUT -s 172.20.0.0/16 -j ACCEPT

# Allow ICMP (ping) with rate limiting
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "iptables-dropped: " --log-level 4

# Save rules
iptables-save > /etc/iptables/rules.v4
```

## 3. Application Security

### Environment Variable Encryption

**File: scripts/security/encrypt-env.sh**

```bash
#!/bin/bash
# Encrypt production environment variables

set -e

ENV_FILE="config/production/.env.production"
ENCRYPTED_FILE="config/production/.env.production.enc"
KEY_FILE="config/production/.env.key"

# Generate encryption key (do this once and store securely)
if [ ! -f "$KEY_FILE" ]; then
    openssl rand -base64 32 > "$KEY_FILE"
    chmod 600 "$KEY_FILE"
fi

# Encrypt environment file
openssl enc -aes-256-cbc -salt -pbkdf2 \
    -in "$ENV_FILE" \
    -out "$ENCRYPTED_FILE" \
    -pass file:"$KEY_FILE"

echo "Environment file encrypted successfully"
```

### Secrets Rotation Script

**File: scripts/security/rotate-secrets.sh**

```bash
#!/bin/bash
# Rotate production secrets

set -e

# Generate new secrets
NEW_DB_PASSWORD=$(openssl rand -base64 32)
NEW_REDIS_PASSWORD=$(openssl rand -base64 32)
NEW_API_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# Update in AWS Secrets Manager
aws secretsmanager update-secret \
    --secret-id prod/db/password \
    --secret-string "$NEW_DB_PASSWORD"

aws secretsmanager update-secret \
    --secret-id prod/redis/password \
    --secret-string "$NEW_REDIS_PASSWORD"

aws secretsmanager update-secret \
    --secret-id prod/api/secret-key \
    --secret-string "$NEW_API_SECRET"

# Trigger graceful service restart
docker-compose -f /opt/corporate-intel/docker-compose.production.yml restart api
docker-compose -f /opt/corporate-intel/docker-compose.production.yml restart redis

echo "Secrets rotated successfully"
```

## 4. Database Security

### PostgreSQL Security Configuration

```sql
-- Create production database user with limited privileges
CREATE USER intel_prod_user WITH PASSWORD 'REPLACE_WITH_SECURE_PASSWORD';

-- Grant only necessary privileges
GRANT CONNECT ON DATABASE corporate_intel_prod TO intel_prod_user;
GRANT USAGE ON SCHEMA public TO intel_prod_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO intel_prod_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO intel_prod_user;

-- Deny superuser privileges
ALTER USER intel_prod_user NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Enable connection encryption
ALTER SYSTEM SET ssl = 'on';
ALTER SYSTEM SET ssl_cert_file = '/etc/ssl/certs/server.crt';
ALTER SYSTEM SET ssl_key_file = '/etc/ssl/private/server.key';

-- Configure password encryption
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Limit connections per user
ALTER USER intel_prod_user CONNECTION LIMIT 50;

-- Enable logging
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_duration = 'on';
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Reload configuration
SELECT pg_reload_conf();
```

### Database Connection Encryption

**File: config/production/pg_hba.conf**

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
# Require SSL for all connections
hostssl all             all             0.0.0.0/0               scram-sha-256
hostssl all             all             ::/0                    scram-sha-256

# Reject non-SSL connections
hostnossl all           all             all                     reject
```

## 5. Container Security

### Docker Security Best Practices

**File: docker-compose.production.yml (security settings)**

```yaml
services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    user: "1000:1000"  # Non-root user
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed

  postgres:
    security_opt:
      - no-new-privileges:true
    user: "postgres"

  redis:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    user: "redis"
```

### Image Scanning

```bash
#!/bin/bash
# Scan Docker images for vulnerabilities

# Install Trivy
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# Scan production image
trivy image --severity HIGH,CRITICAL ghcr.io/yourorg/corporate-intel:latest

# Fail build if critical vulnerabilities found
trivy image --exit-code 1 --severity CRITICAL ghcr.io/yourorg/corporate-intel:latest
```

## 6. Monitoring & Intrusion Detection

### Fail2Ban Configuration

**File: /etc/fail2ban/jail.local**

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = security@yourdomain.com
sendername = Fail2Ban
action = %(action_mwl)s

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/access.log
maxretry = 6
```

### AIDE (Intrusion Detection)

```bash
#!/bin/bash
# Setup AIDE for file integrity monitoring

# Install AIDE
apt-get install aide aide-common

# Initialize database
aideinit

# Move database
mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Create daily check cron
cat > /etc/cron.daily/aide-check << 'EOF'
#!/bin/bash
/usr/bin/aide --check | mail -s "AIDE Report $(date)" security@yourdomain.com
EOF

chmod +x /etc/cron.daily/aide-check
```

## 7. Compliance & Audit

### Audit Logging

```bash
#!/bin/bash
# Setup audit logging with auditd

# Install auditd
apt-get install auditd audispd-plugins

# Configure rules
cat > /etc/audit/rules.d/corporate-intel.rules << 'EOF'
# Monitor authentication
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity

# Monitor SSH configuration
-w /etc/ssh/sshd_config -p wa -k sshd_config

# Monitor Docker
-w /var/lib/docker -p wa -k docker

# Monitor application configuration
-w /opt/corporate-intel/config -p wa -k app_config

# Monitor sudo usage
-w /etc/sudoers -p wa -k sudoers
-w /etc/sudoers.d -p wa -k sudoers

# Monitor network configuration
-w /etc/network -p wa -k network
EOF

# Load rules
augenrules --load

# Enable auditd
systemctl enable auditd
systemctl start auditd
```

## 8. Security Checklist

### Pre-Deployment Security Verification

```bash
#!/bin/bash
# Security validation script

echo "Running security validation..."

FAILED=0

# Check 1: SSL certificate
if ! openssl x509 -checkend 2592000 -noout -in /etc/letsencrypt/live/corporate-intel.yourdomain.com/fullchain.pem; then
    echo "FAIL: SSL certificate expires within 30 days"
    FAILED=1
fi

# Check 2: Firewall enabled
if ! ufw status | grep -q "Status: active"; then
    echo "FAIL: Firewall is not enabled"
    FAILED=1
fi

# Check 3: No default passwords
if docker-compose -f docker-compose.production.yml config | grep -q "REPLACE_WITH"; then
    echo "FAIL: Default passwords detected"
    FAILED=1
fi

# Check 4: Secrets in secure storage
if [ ! -f "/etc/secrets/db-password" ]; then
    echo "FAIL: Database password not in secure storage"
    FAILED=1
fi

# Check 5: Non-root containers
if docker-compose -f docker-compose.production.yml config | grep -q "user: root"; then
    echo "FAIL: Containers running as root"
    FAILED=1
fi

# Check 6: Security headers present
if ! curl -s -I https://corporate-intel.yourdomain.com | grep -q "Strict-Transport-Security"; then
    echo "FAIL: Security headers missing"
    FAILED=1
fi

if [ $FAILED -eq 0 ]; then
    echo "Security validation passed!"
    exit 0
else
    echo "Security validation failed!"
    exit 1
fi
```

## Summary

This security hardening guide implements multiple layers of defense:

1. **Edge Security**: SSL/TLS, NGINX hardening, rate limiting
2. **Network Security**: Firewalls, network segmentation
3. **Application Security**: Secrets management, environment encryption
4. **Data Security**: Database encryption, access controls
5. **Container Security**: Non-root users, capability dropping
6. **Monitoring**: Intrusion detection, audit logging

Follow all sections for comprehensive production security.
