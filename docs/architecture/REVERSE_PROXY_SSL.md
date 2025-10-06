# Reverse Proxy and SSL/TLS Architecture

## Overview

This document details the reverse proxy and SSL/TLS configuration for the Corporate Intelligence Platform, implementing Nginx for Docker Compose deployments with a migration path to Traefik for Kubernetes.

---

## Architecture Decision

**Current**: Nginx (Docker Compose)
**Future**: Traefik (Kubernetes)
**Rationale**: See [ADR-002](/mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/docs/architecture/adr/002-reverse-proxy-ssl.md)

---

## Nginx Configuration (Docker Compose)

### Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Nginx Reverse Proxy                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Port 443 (HTTPS)                                    │   │
│  │  - SSL/TLS Termination (TLS 1.2/1.3)                │   │
│  │  - Certificate: Let's Encrypt (auto-renewed)        │   │
│  │  - Security Headers (HSTS, CSP, etc.)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Rate Limiting & DDoS Protection                     │   │
│  │  - 100 req/sec per IP (burst 200)                   │   │
│  │  - Connection limit: 10 per IP                      │   │
│  │  - Request size limit: 10MB                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Caching Layer                                       │   │
│  │  - Static assets: 1 year                            │   │
│  │  - API responses: 5 minutes (selective)             │   │
│  │  - Proxy cache: 100MB                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Load Balancing (future multi-instance)             │   │
│  │  - Round robin / Least connections                  │   │
│  │  - Health checks (interval: 10s)                    │   │
│  │  - Automatic failover                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  FastAPI Application   │
            │  (Gunicorn + Uvicorn)  │
            │  Internal Port: 8000   │
            └────────────────────────┘
```

### Configuration Files

#### 1. Main Nginx Configuration

```nginx
# nginx/nginx.conf

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

# Performance optimizations
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct=$upstream_connect_time '
                    'uht=$upstream_header_time urt=$upstream_response_time';

    access_log /var/log/nginx/access.log main;

    # Performance settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10m;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;
    gzip_disable "msie6";

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # Proxy cache
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:100m
                     max_size=1g inactive=60m use_temp_path=off;

    # Upstream backend
    upstream api_backend {
        least_conn;
        server api:8000 max_fails=3 fail_timeout=30s;
        # Add more servers for load balancing:
        # server api2:8000 max_fails=3 fail_timeout=30s;
        # server api3:8000 max_fails=3 fail_timeout=30s;

        keepalive 32;
    }

    # Include site configurations
    include /etc/nginx/conf.d/*.conf;
}
```

#### 2. SSL/TLS Configuration

```nginx
# nginx/conf.d/ssl.conf

# SSL session cache
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# SSL protocols and ciphers
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self'" always;
```

#### 3. Main Site Configuration

```nginx
# nginx/conf.d/corporate-intel.conf

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name api.corporate-intel.com corporate-intel.com;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.corporate-intel.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.corporate-intel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.corporate-intel.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/api.corporate-intel.com/chain.pem;

    # Security headers (inherited from ssl.conf)

    # Rate limiting
    limit_req zone=api_limit burst=200 nodelay;
    limit_conn conn_limit 10;

    # Logging
    access_log /var/log/nginx/corporate-intel-access.log main;
    error_log /var/log/nginx/corporate-intel-error.log warn;

    # Root location
    location / {
        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # Proxy settings
        proxy_pass http://api_backend;
        proxy_redirect off;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check endpoint (no rate limiting)
    location /health {
        access_log off;
        proxy_pass http://api_backend/health;
        proxy_set_header Host $host;
    }

    # API endpoints with stricter rate limiting
    location /api/v1/auth {
        limit_req zone=auth_limit burst=20 nodelay;
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (if serving any)
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Monitoring metrics endpoint (restrict access)
    location /metrics {
        allow 10.0.0.0/8;  # Internal network
        deny all;
        proxy_pass http://api_backend/metrics;
    }
}
```

#### 4. Monitoring Dashboard Configuration (Optional)

```nginx
# nginx/conf.d/monitoring.conf

# Grafana
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name monitoring.corporate-intel.com;

    ssl_certificate /etc/letsencrypt/live/monitoring.corporate-intel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoring.corporate-intel.com/privkey.pem;

    location / {
        proxy_pass http://grafana:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Prometheus (restrict access)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name prometheus.corporate-intel.com;

    ssl_certificate /etc/letsencrypt/live/prometheus.corporate-intel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prometheus.corporate-intel.com/privkey.pem;

    # Basic authentication
    auth_basic "Prometheus Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://prometheus:9090;
        proxy_set_header Host $host;
    }
}
```

---

## Docker Compose Integration

```yaml
# docker-compose.nginx.yml

version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: corporate-intel-nginx
    restart: unless-stopped
    depends_on:
      - api
    ports:
      - "80:80"
      - "443:443"
    volumes:
      # Configuration
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro

      # SSL certificates
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro

      # Logs
      - nginx_logs:/var/log/nginx

      # Cache
      - nginx_cache:/var/cache/nginx

      # Static files (if any)
      - ./static:/var/www/static:ro

    networks:
      - corporate-intel-network
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  certbot:
    image: certbot/certbot:latest
    container_name: corporate-intel-certbot
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    networks:
      - corporate-intel-network

volumes:
  certbot_conf:
    name: corporate-intel-certbot-conf
  certbot_www:
    name: corporate-intel-certbot-www
  nginx_logs:
    name: corporate-intel-nginx-logs
  nginx_cache:
    name: corporate-intel-nginx-cache

networks:
  corporate-intel-network:
    external: true
```

---

## SSL Certificate Management

### Let's Encrypt Setup

```bash
#!/bin/bash
# scripts/ssl-setup.sh

DOMAIN="api.corporate-intel.com"
EMAIL="admin@corporate-intel.com"

# Initial certificate request
docker-compose -f docker-compose.nginx.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email ${EMAIL} \
  --agree-tos \
  --no-eff-email \
  -d ${DOMAIN}

# Reload Nginx to use new certificate
docker-compose -f docker-compose.nginx.yml exec nginx nginx -s reload

echo "SSL certificate installed for ${DOMAIN}"
```

### Automatic Renewal

```bash
#!/bin/bash
# scripts/ssl-renew.sh (runs via cron)

# Renew certificates
docker-compose -f docker-compose.nginx.yml run --rm certbot renew

# Reload Nginx if certificates were renewed
if [ $? -eq 0 ]; then
    docker-compose -f docker-compose.nginx.yml exec nginx nginx -s reload
    echo "SSL certificates renewed and Nginx reloaded"
fi
```

### Cron Job

```bash
# /etc/cron.d/certbot-renewal

# Run renewal twice daily
0 0,12 * * * /path/to/scripts/ssl-renew.sh >> /var/log/certbot-renewal.log 2>&1
```

---

## Vault PKI Integration (Alternative)

### Setup Vault PKI for Internal Certificates

```bash
# Enable PKI secrets engine
vault secrets enable pki
vault secrets tune -max-lease-ttl=8760h pki

# Generate root CA
vault write -field=certificate pki/root/generate/internal \
  common_name="Corporate Intel Internal CA" \
  ttl=87600h > /etc/ssl/certs/corporate-intel-ca.crt

# Configure PKI role
vault write pki/roles/corporate-intel \
  allowed_domains="corporate-intel.internal,corporate-intel.com" \
  allow_subdomains=true \
  max_ttl="2160h"

# Issue certificate
vault write pki/issue/corporate-intel \
  common_name="api.corporate-intel.com" \
  ttl="2160h" \
  format=pem > /tmp/api-cert.json

# Extract certificate and key
cat /tmp/api-cert.json | jq -r '.data.certificate' > /etc/nginx/ssl/api.crt
cat /tmp/api-cert.json | jq -r '.data.private_key' > /etc/nginx/ssl/api.key
cat /tmp/api-cert.json | jq -r '.data.ca_chain[]' > /etc/nginx/ssl/ca-chain.crt

# Reload Nginx
docker-compose exec nginx nginx -s reload
```

### Auto-Renewal Script

```bash
#!/bin/bash
# scripts/vault-cert-renew.sh

DOMAIN="api.corporate-intel.com"

# Generate new certificate from Vault
vault write -format=json pki/issue/corporate-intel \
  common_name="${DOMAIN}" \
  ttl="2160h" > /tmp/new-cert.json

# Extract and install
cat /tmp/new-cert.json | jq -r '.data.certificate' > /etc/nginx/ssl/${DOMAIN}.crt
cat /tmp/new-cert.json | jq -r '.data.private_key' > /etc/nginx/ssl/${DOMAIN}.key

# Reload Nginx
docker-compose exec nginx nginx -s reload

echo "Certificate renewed for ${DOMAIN}"
```

---

## Security Hardening

### 1. DDoS Protection

```nginx
# Rate limiting for different endpoints
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=search_limit:10m rate=20r/s;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# Apply limits
location /api/ {
    limit_req zone=api_limit burst=200 nodelay;
    limit_conn conn_limit 10;
}
```

### 2. Request Size Limits

```nginx
# Global limit
client_max_body_size 10m;

# Specific endpoint limits
location /api/v1/upload {
    client_max_body_size 50m;
}
```

### 3. IP Whitelisting (for admin endpoints)

```nginx
location /admin/ {
    allow 10.0.0.0/8;     # Internal network
    allow 203.0.113.0/24; # Office IP range
    deny all;

    proxy_pass http://api_backend;
}
```

### 4. Bot Protection

```nginx
# Block common bad bots
map $http_user_agent $blocked_agent {
    default 0;
    ~*malicious 1;
    ~*bot 1;
    ~*crawler 1;
    ~*spider 1;
}

server {
    if ($blocked_agent) {
        return 403;
    }
}
```

### 5. SSL Security Test

```bash
# Test SSL configuration
docker run --rm -it nmap/nmap-online --script ssl-enum-ciphers -p 443 api.corporate-intel.com

# Expected: A+ rating on SSL Labs
# https://www.ssllabs.com/ssltest/analyze.html?d=api.corporate-intel.com
```

---

## Monitoring and Logging

### 1. Access Logs

```nginx
# Extended log format
log_format extended '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    'rt=$request_time uct=$upstream_connect_time '
                    'uht=$upstream_header_time urt=$upstream_response_time '
                    'cache=$upstream_cache_status';

access_log /var/log/nginx/access.log extended;
```

### 2. Prometheus Metrics

```nginx
# Install nginx-prometheus-exporter
# docker-compose.nginx.yml

services:
  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:latest
    container_name: nginx-exporter
    command:
      - '-nginx.scrape-uri=http://nginx:8080/stub_status'
    ports:
      - "9113:9113"
    networks:
      - corporate-intel-network
```

```nginx
# nginx/conf.d/stub-status.conf

server {
    listen 8080;
    server_name localhost;

    location /stub_status {
        stub_status on;
        access_log off;
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

### 3. Log Aggregation (Loki)

```yaml
# promtail-config.yml

server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          job: nginx
          __path__: /var/log/nginx/*.log
```

---

## Performance Optimization

### 1. Caching Strategy

```nginx
# Proxy cache for API responses
proxy_cache_path /var/cache/nginx/api levels=1:2 keys_zone=api_cache:100m
                 max_size=1g inactive=60m use_temp_path=off;

location /api/v1/companies {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_valid 404 1m;
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    proxy_cache_background_update on;
    proxy_cache_lock on;

    add_header X-Cache-Status $upstream_cache_status;
    proxy_pass http://api_backend;
}
```

### 2. Connection Pooling

```nginx
upstream api_backend {
    least_conn;
    server api:8000;
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;
}
```

### 3. HTTP/2 Optimization

```nginx
# Enable HTTP/2
listen 443 ssl http2;

# HTTP/2 push (for critical resources)
location / {
    http2_push /static/css/main.css;
    http2_push /static/js/main.js;
}
```

---

## Kubernetes Migration (Traefik)

### Future Architecture

```yaml
# kubernetes/ingress.yaml

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: corporate-intel-ingress
  annotations:
    kubernetes.io/ingress.class: traefik
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.tls: "true"
    traefik.ingress.kubernetes.io/router.middlewares: default-rate-limit@kubernetescrd

spec:
  tls:
    - hosts:
        - api.corporate-intel.com
      secretName: corporate-intel-tls

  rules:
    - host: api.corporate-intel.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: corporate-intel-api
                port:
                  number: 8000
```

### Rate Limiting Middleware

```yaml
# kubernetes/middleware-ratelimit.yaml

apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: rate-limit

spec:
  rateLimit:
    average: 100
    burst: 200
    period: 1s
```

---

## Testing and Validation

### 1. SSL Certificate Validation

```bash
# Check certificate expiry
echo | openssl s_client -servername api.corporate-intel.com \
  -connect api.corporate-intel.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Verify certificate chain
openssl s_client -connect api.corporate-intel.com:443 -showcerts
```

### 2. Load Testing

```bash
# Apache Bench
ab -n 10000 -c 100 https://api.corporate-intel.com/health

# wrk
wrk -t12 -c400 -d30s https://api.corporate-intel.com/api/v1/companies
```

### 3. Security Scan

```bash
# Nmap SSL scan
nmap --script ssl-enum-ciphers -p 443 api.corporate-intel.com

# testssl.sh
docker run --rm -ti drwetter/testssl.sh https://api.corporate-intel.com
```

---

## Troubleshooting

### Common Issues

1. **Certificate Not Found**
   ```bash
   # Check certbot logs
   docker-compose logs certbot

   # Manually request certificate
   docker-compose run --rm certbot certonly --webroot \
     -w /var/www/certbot -d api.corporate-intel.com
   ```

2. **502 Bad Gateway**
   ```bash
   # Check backend health
   curl http://localhost:8000/health

   # Check Nginx upstream
   docker-compose exec nginx cat /etc/nginx/conf.d/corporate-intel.conf
   ```

3. **Rate Limit Errors**
   ```bash
   # Check rate limit zones
   docker-compose exec nginx nginx -T | grep limit_req_zone

   # Clear rate limit memory
   docker-compose restart nginx
   ```

---

## Maintenance

### Certificate Renewal Monitoring

```bash
#!/bin/bash
# scripts/check-cert-expiry.sh

DOMAIN="api.corporate-intel.com"
EXPIRY_DAYS=30

# Get certificate expiry date
EXPIRY_DATE=$(echo | openssl s_client -servername ${DOMAIN} \
  -connect ${DOMAIN}:443 2>/dev/null | \
  openssl x509 -noout -enddate | cut -d= -f2)

# Calculate days until expiry
EXPIRY_EPOCH=$(date -d "${EXPIRY_DATE}" +%s)
TODAY_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - TODAY_EPOCH) / 86400 ))

if [ ${DAYS_LEFT} -lt ${EXPIRY_DAYS} ]; then
    echo "WARNING: SSL certificate expires in ${DAYS_LEFT} days"
    # Send alert
fi
```

---

## Cost Analysis

### Nginx (Current)

| Component | Cost | Notes |
|-----------|------|-------|
| **Nginx** | $0 | Open-source |
| **Let's Encrypt** | $0 | Free SSL certificates |
| **Total** | **$0/month** | No cost |

### Traefik (Kubernetes)

| Component | Cost | Notes |
|-----------|------|-------|
| **Traefik** | $0 | Open-source |
| **cert-manager** | $0 | Free SSL automation |
| **Total** | **$0/month** | No cost |

---

## Next Steps

1. **Week 1**: Deploy Nginx with Let's Encrypt
   ```bash
   ./scripts/ssl-setup.sh
   docker-compose -f docker-compose.nginx.yml up -d
   ```

2. **Week 2**: Configure rate limiting and caching
   ```bash
   # Update nginx.conf with optimizations
   docker-compose exec nginx nginx -s reload
   ```

3. **Week 3**: Set up monitoring and alerts
   ```bash
   # Deploy nginx-exporter
   # Configure Prometheus scraping
   ```

4. **Future**: Kubernetes migration with Traefik
   ```bash
   # Apply Kubernetes manifests
   kubectl apply -f kubernetes/
   ```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-03
**Author**: System Architect Agent
