# DNS and SSL Configuration Guide

## Table of Contents
- [Overview](#overview)
- [DNS Configuration](#dns-configuration)
- [SSL Certificate Setup](#ssl-certificate-setup)
- [Nginx Configuration](#nginx-configuration)
- [Traefik Configuration](#traefik-configuration)
- [Certificate Renewal](#certificate-renewal)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

## Overview

This guide covers the complete DNS and SSL/TLS setup for the Corporate Intel production environment. The configuration achieves **SSL Labs Grade A+** rating with modern security practices.

### Infrastructure Components
- **Reverse Proxy**: Nginx or Traefik
- **SSL Provider**: Let's Encrypt (free, automated)
- **Certificate Management**: Certbot with automatic renewal
- **DNS Requirements**: A records, CNAME records, optional wildcard

### Security Standards
- TLS 1.2+ only (TLS 1.3 preferred)
- HSTS with preload
- OCSP Stapling
- Modern cipher suites
- Security headers (CSP, X-Frame-Options, etc.)

---

## DNS Configuration

### Required DNS Records

Configure the following DNS records with your domain registrar or DNS provider:

#### A Records (IPv4)
```dns
api.corporate-intel.com.          IN  A     203.0.113.10
metrics.corporate-intel.com.      IN  A     203.0.113.10
docs.corporate-intel.com.         IN  A     203.0.113.10
```

#### AAAA Records (IPv6) - Optional but Recommended
```dns
api.corporate-intel.com.          IN  AAAA  2001:db8::1
metrics.corporate-intel.com.      IN  AAAA  2001:db8::1
docs.corporate-intel.com.         IN  AAAA  2001:db8::1
```

#### CNAME Records (if using load balancer)
```dns
api.corporate-intel.com.          IN  CNAME lb.corporate-intel.com.
metrics.corporate-intel.com.      IN  CNAME lb.corporate-intel.com.
```

#### Wildcard Certificate (Optional)
```dns
*.corporate-intel.com.            IN  A     203.0.113.10
```

### CAA Records (Certificate Authority Authorization)
Restrict which CAs can issue certificates for your domain:

```dns
corporate-intel.com.              IN  CAA   0 issue "letsencrypt.org"
corporate-intel.com.              IN  CAA   0 issuewild "letsencrypt.org"
corporate-intel.com.              IN  CAA   0 iodef "mailto:security@corporate-intel.com"
```

### DNS Provider Examples

#### Cloudflare DNS Setup
1. Log in to Cloudflare dashboard
2. Navigate to DNS management
3. Add A records with proxy status (orange cloud) disabled for initial SSL setup
4. Enable proxy (orange cloud) after SSL verification
5. Configure SSL/TLS mode to "Full (strict)"

#### Route 53 (AWS) Setup
```bash
# Create hosted zone
aws route53 create-hosted-zone \
    --name corporate-intel.com \
    --caller-reference $(date +%s)

# Add A record
aws route53 change-resource-record-sets \
    --hosted-zone-id Z1234567890ABC \
    --change-batch file://dns-records.json
```

#### Google Cloud DNS
```bash
# Create DNS zone
gcloud dns managed-zones create corporate-intel \
    --dns-name=corporate-intel.com \
    --description="Corporate Intel Production"

# Add A record
gcloud dns record-sets transaction start --zone=corporate-intel
gcloud dns record-sets transaction add 203.0.113.10 \
    --name=api.corporate-intel.com. \
    --ttl=300 \
    --type=A \
    --zone=corporate-intel
gcloud dns record-sets transaction execute --zone=corporate-intel
```

### DNS Verification

Verify DNS propagation before proceeding:

```bash
# Check A record
dig api.corporate-intel.com +short

# Check all records
dig api.corporate-intel.com ANY

# Check from multiple locations
nslookup api.corporate-intel.com 8.8.8.8
nslookup api.corporate-intel.com 1.1.1.1

# Use online tools
# - https://dnschecker.org
# - https://www.whatsmydns.net
```

---

## SSL Certificate Setup

### Prerequisites

1. **Domain ownership verified** (DNS records configured)
2. **Port 80 accessible** for ACME HTTP-01 challenge
3. **Port 443 accessible** for HTTPS traffic
4. **Certbot installed** (automated by script)

### Automatic Setup (Recommended)

Use the provided automation script:

```bash
# Make script executable
chmod +x scripts/ssl-setup.sh

# Run complete setup
sudo ./scripts/ssl-setup.sh

# Or run specific commands
sudo ./scripts/ssl-setup.sh install   # Install Certbot only
sudo ./scripts/ssl-setup.sh obtain    # Obtain certificates only
sudo ./scripts/ssl-setup.sh renew     # Manual renewal
sudo ./scripts/ssl-setup.sh verify    # Verify SSL configuration
sudo ./scripts/ssl-setup.sh info      # Show certificate info
```

### Manual Setup

#### 1. Install Certbot

**Ubuntu/Debian:**
```bash
apt-get update
apt-get install -y certbot python3-certbot-nginx
```

**CentOS/RHEL:**
```bash
yum install -y epel-release
yum install -y certbot python3-certbot-nginx
```

**Docker:**
```bash
docker pull certbot/certbot
```

#### 2. Obtain Certificates

**Webroot Method (Recommended for Nginx):**
```bash
# Create webroot directory
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot

# Obtain certificate
certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@corporate-intel.com \
    --agree-tos \
    --no-eff-email \
    --domain api.corporate-intel.com \
    --non-interactive
```

**Standalone Method (Temporary server):**
```bash
# Stop nginx temporarily
systemctl stop nginx

# Obtain certificate
certbot certonly \
    --standalone \
    --preferred-challenges http \
    --email admin@corporate-intel.com \
    --agree-tos \
    --domain api.corporate-intel.com

# Restart nginx
systemctl start nginx
```

**Nginx Plugin (Automatic configuration):**
```bash
certbot --nginx \
    --email admin@corporate-intel.com \
    --agree-tos \
    --domain api.corporate-intel.com \
    --redirect
```

#### 3. Wildcard Certificates (DNS Challenge)

Wildcard certificates require DNS validation:

**Install DNS plugin (Cloudflare example):**
```bash
apt-get install python3-certbot-dns-cloudflare
```

**Create Cloudflare credentials file:**
```bash
cat > /etc/letsencrypt/cloudflare.ini <<EOF
dns_cloudflare_api_token = your_cloudflare_api_token
EOF

chmod 600 /etc/letsencrypt/cloudflare.ini
```

**Obtain wildcard certificate:**
```bash
certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
    --email admin@corporate-intel.com \
    --agree-tos \
    --domain "*.corporate-intel.com" \
    --domain "corporate-intel.com"
```

**Other DNS providers:**
- `python3-certbot-dns-route53` (AWS Route 53)
- `python3-certbot-dns-google` (Google Cloud DNS)
- `python3-certbot-dns-digitalocean` (DigitalOcean)

### Certificate Locations

After successful issuance, certificates are stored at:

```
/etc/letsencrypt/live/api.corporate-intel.com/
├── fullchain.pem     -> Full certificate chain (use in nginx)
├── privkey.pem       -> Private key (keep secure!)
├── cert.pem          -> Certificate only
└── chain.pem         -> Intermediate certificates
```

### Verify Certificates

```bash
# Check certificate details
openssl x509 -in /etc/letsencrypt/live/api.corporate-intel.com/cert.pem -text -noout

# Verify certificate chain
openssl verify -CAfile /etc/letsencrypt/live/api.corporate-intel.com/chain.pem \
    /etc/letsencrypt/live/api.corporate-intel.com/cert.pem

# Check expiration date
openssl x509 -in /etc/letsencrypt/live/api.corporate-intel.com/cert.pem -noout -enddate
```

---

## Nginx Configuration

### Installation

```bash
# Ubuntu/Debian
apt-get update
apt-get install -y nginx

# CentOS/RHEL
yum install -y nginx

# Verify installation
nginx -v
```

### Configuration Files

The production nginx configuration is located at:
- **Main config**: `/config/production/nginx.conf`
- **Copy to**: `/etc/nginx/sites-available/corporate-intel.conf`

### Deployment Steps

```bash
# Copy configuration
cp config/production/nginx.conf /etc/nginx/sites-available/corporate-intel.conf

# Create symbolic link
ln -s /etc/nginx/sites-available/corporate-intel.conf /etc/nginx/sites-enabled/

# Remove default site
rm /etc/nginx/sites-enabled/default

# Test configuration
nginx -t

# Reload nginx
systemctl reload nginx
```

### Key Configuration Features

1. **HTTP to HTTPS Redirect**
   - All HTTP traffic automatically redirected to HTTPS
   - Preserves request URI and query parameters

2. **SSL/TLS Configuration**
   - TLS 1.2 and 1.3 only
   - Modern cipher suites
   - OCSP stapling enabled
   - DH parameters for forward secrecy

3. **Security Headers**
   - Strict-Transport-Security (HSTS)
   - X-Frame-Options: DENY
   - X-Content-Type-Options: nosniff
   - Content-Security-Policy
   - Referrer-Policy

4. **Rate Limiting**
   - API: 10 requests/second (burst 20)
   - Metrics: 5 requests/second (burst 10)
   - Connection limit: 10 concurrent per IP

5. **Load Balancing**
   - Least connections algorithm
   - Health checks every 10 seconds
   - Automatic failover to backup

### Generate DH Parameters

For enhanced security, generate Diffie-Hellman parameters:

```bash
# Generate 2048-bit DH parameters (faster)
openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048

# Or 4096-bit (more secure, takes longer)
openssl dhparam -out /etc/ssl/certs/dhparam.pem 4096

# Add to nginx SSL configuration
# ssl_dhparam /etc/ssl/certs/dhparam.pem;
```

### Testing and Verification

```bash
# Test configuration syntax
nginx -t

# Check nginx status
systemctl status nginx

# View error logs
tail -f /var/log/nginx/error.log

# View access logs
tail -f /var/log/nginx/access.log

# Test SSL configuration
curl -I https://api.corporate-intel.com

# Check SSL grade
# Use: https://www.ssllabs.com/ssltest/
```

---

## Traefik Configuration

### Installation

**Binary Installation:**
```bash
# Download latest Traefik
wget https://github.com/traefik/traefik/releases/download/v2.10.7/traefik_v2.10.7_linux_amd64.tar.gz
tar -xzf traefik_v2.10.7_linux_amd64.tar.gz
sudo mv traefik /usr/local/bin/
sudo chmod +x /usr/local/bin/traefik
```

**Docker Installation:**
```bash
docker run -d \
    --name traefik \
    --restart unless-stopped \
    -p 80:80 \
    -p 443:443 \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v /etc/traefik:/etc/traefik \
    traefik:v2.10
```

### Configuration Files

- **Static config**: `/config/production/traefik.yml`
- **Dynamic config**: `/config/production/traefik-dynamic.yml`

### Deployment Steps

```bash
# Create Traefik directories
mkdir -p /etc/traefik/dynamic
mkdir -p /var/log/traefik

# Copy configurations
cp config/production/traefik.yml /etc/traefik/
cp config/production/traefik-dynamic.yml /etc/traefik/dynamic/

# Create acme.json for Let's Encrypt
touch /etc/traefik/acme.json
chmod 600 /etc/traefik/acme.json

# Create systemd service
cat > /etc/systemd/system/traefik.service <<EOF
[Unit]
Description=Traefik Reverse Proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/traefik --configFile=/etc/traefik/traefik.yml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start Traefik
systemctl daemon-reload
systemctl enable traefik
systemctl start traefik
```

### Key Features

1. **Automatic SSL**
   - Automatic certificate issuance with Let's Encrypt
   - Automatic renewal
   - Support for wildcard certificates with DNS challenge

2. **Dynamic Configuration**
   - File-based or Docker label configuration
   - Hot reload without downtime
   - Middleware chaining

3. **Middlewares**
   - Security headers
   - Rate limiting
   - Basic authentication
   - Compression
   - Retry logic

4. **Observability**
   - Prometheus metrics
   - Access logs in JSON format
   - Dashboard with authentication

### Docker Compose Example

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/production/traefik.yml:/etc/traefik/traefik.yml
      - ./config/production/traefik-dynamic.yml:/etc/traefik/dynamic/config.yml
      - traefik-acme:/etc/traefik/acme
    networks:
      - corporate-intel-network

  api:
    image: corporate-intel/api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.corporate-intel.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
    networks:
      - corporate-intel-network

volumes:
  traefik-acme:

networks:
  corporate-intel-network:
    driver: bridge
```

---

## Certificate Renewal

### Automatic Renewal with Systemd Timer

The SSL setup script configures automatic renewal via systemd timer.

**View timer status:**
```bash
systemctl status certbot-renewal.timer

# Check next run time
systemctl list-timers certbot-renewal.timer
```

**Manual trigger:**
```bash
systemctl start certbot-renewal.service
```

### Automatic Renewal with Cron

Alternative method using cron (for systems without systemd):

```bash
# Install cron renewal script
cp scripts/ssl-renewal-cron.sh /usr/local/bin/
chmod +x /usr/local/bin/ssl-renewal-cron.sh

# Add to crontab (runs twice daily)
echo "0 0,12 * * * /usr/local/bin/ssl-renewal-cron.sh" | crontab -
```

### Manual Renewal

```bash
# Dry-run (test without making changes)
certbot renew --dry-run

# Force renewal (even if not expiring soon)
certbot renew --force-renewal

# Renew specific domain
certbot renew --cert-name api.corporate-intel.com
```

### Post-Renewal Hooks

Certbot executes hooks after successful renewal:

```bash
# Deploy hook (runs after any renewal)
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-services.sh <<'EOF'
#!/bin/bash
systemctl reload nginx
logger "SSL certificates renewed and nginx reloaded"
EOF

chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-services.sh
```

---

## Monitoring and Maintenance

### Certificate Expiration Monitoring

**Manual check:**
```bash
# Check all certificates
certbot certificates

# Check specific domain
openssl s_client -servername api.corporate-intel.com \
    -connect api.corporate-intel.com:443 2>/dev/null | \
    openssl x509 -noout -dates
```

**Automated monitoring script:**
```bash
# Install monitoring script
cp /usr/local/bin/check-cert-expiry.sh /usr/local/bin/
chmod +x /usr/local/bin/check-cert-expiry.sh

# Add to crontab (daily check at 8 AM)
echo "0 8 * * * /usr/local/bin/check-cert-expiry.sh" | crontab -
```

### SSL Grade Testing

**SSLLabs Test (Manual):**
1. Visit https://www.ssllabs.com/ssltest/
2. Enter domain: `api.corporate-intel.com`
3. Target grade: A or A+

**Automated SSL testing:**
```bash
# Install ssllabs-scan
go install github.com/ssllabs/ssllabs-scan@latest

# Run scan
ssllabs-scan --quiet api.corporate-intel.com
```

### Log Monitoring

**Nginx logs:**
```bash
# Real-time monitoring
tail -f /var/log/nginx/api.corporate-intel.com-access.log
tail -f /var/log/nginx/api.corporate-intel.com-error.log

# Check for SSL errors
grep -i ssl /var/log/nginx/error.log
```

**Certbot logs:**
```bash
# View renewal logs
cat /var/log/letsencrypt/letsencrypt.log

# Check for errors
grep -i error /var/log/letsencrypt/letsencrypt.log
```

### Prometheus Metrics

Monitor SSL certificate expiration with Prometheus:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://api.corporate-intel.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

**Alert rules:**
```yaml
groups:
  - name: ssl_expiry
    rules:
      - alert: SSLCertExpiringSoon
        expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL certificate expiring soon"
          description: "SSL certificate for {{ $labels.instance }} expires in {{ $value | humanizeDuration }}"
```

---

## Troubleshooting

### Common Issues

#### 1. Certificate Acquisition Fails

**Problem:** Certbot cannot obtain certificate

**Solutions:**
```bash
# Check DNS resolution
dig api.corporate-intel.com +short

# Verify port 80 is accessible
curl -I http://api.corporate-intel.com/.well-known/acme-challenge/test

# Check firewall
ufw status
iptables -L -n | grep 80

# Verify webroot permissions
ls -la /var/www/certbot

# Try standalone mode
systemctl stop nginx
certbot certonly --standalone -d api.corporate-intel.com
systemctl start nginx
```

#### 2. SSL Handshake Errors

**Problem:** Clients cannot establish SSL connection

**Solutions:**
```bash
# Test SSL connection
openssl s_client -connect api.corporate-intel.com:443 -servername api.corporate-intel.com

# Check certificate chain
curl -vI https://api.corporate-intel.com

# Verify nginx is using correct certificates
nginx -T | grep ssl_certificate

# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/api.corporate-intel.com/cert.pem -noout -dates
```

#### 3. Rate Limit Exceeded

**Problem:** Let's Encrypt rate limit hit

**Solutions:**
- Wait 7 days for limit reset (50 certs per domain per week)
- Use staging environment for testing:
  ```bash
  certbot certonly --staging -d api.corporate-intel.com
  ```
- Delete failed attempts don't count toward limit
- Consider wildcard certificate

#### 4. Renewal Fails

**Problem:** Automatic renewal not working

**Solutions:**
```bash
# Test renewal
certbot renew --dry-run

# Check systemd timer
systemctl status certbot-renewal.timer
journalctl -u certbot-renewal.service

# Verify webroot is accessible
ls -la /var/www/certbot/.well-known/acme-challenge/

# Manual renewal
certbot renew --force-renewal
```

#### 5. Mixed Content Warnings

**Problem:** HTTPS page loads HTTP resources

**Solutions:**
- Update all resource URLs to use HTTPS
- Add Content-Security-Policy header:
  ```nginx
  add_header Content-Security-Policy "upgrade-insecure-requests";
  ```
- Check browser console for mixed content errors

### Debug Mode

Enable verbose output for troubleshooting:

```bash
# Certbot verbose mode
certbot renew --dry-run --verbose

# Nginx debug mode
nginx -T  # Test and dump configuration
nginx -t -v  # Test with verbose output

# Enable nginx debug log
error_log /var/log/nginx/debug.log debug;
```

---

## Security Best Practices

### 1. Private Key Security

**Protect private keys:**
```bash
# Set restrictive permissions
chmod 600 /etc/letsencrypt/archive/*/privkey*.pem
chown root:root /etc/letsencrypt/archive/*/privkey*.pem

# Regular backups (encrypted)
tar -czf - /etc/letsencrypt | \
    openssl enc -aes-256-cbc -salt -out letsencrypt-backup.tar.gz.enc
```

### 2. HSTS Preload

Submit your domain to HSTS preload list:

1. Ensure HSTS header is configured with `preload` directive
2. Visit https://hstspreload.org
3. Enter domain and submit
4. Wait for inclusion in browser preload lists

### 3. Certificate Transparency Monitoring

Monitor Certificate Transparency logs:

- Use https://crt.sh to search for your domain
- Set up alerts for unexpected certificate issuance
- Consider using Facebook's CT Monitor

### 4. OCSP Must-Staple

Add must-staple flag to certificate requests:

```bash
certbot certonly \
    --must-staple \
    -d api.corporate-intel.com
```

### 5. Key Rotation

Regularly rotate certificates and keys:

```bash
# Force renewal with new key
certbot renew --force-renewal --reuse-key false

# Or for new issuance
certbot certonly --force-renewal -d api.corporate-intel.com
```

### 6. Security Headers

Implement comprehensive security headers (configured in nginx/traefik):

- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### 7. Firewall Configuration

**UFW (Ubuntu):**
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

**iptables:**
```bash
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables-save > /etc/iptables/rules.v4
```

### 8. Fail2ban Integration

Protect against brute force attacks:

```bash
# Install fail2ban
apt-get install fail2ban

# Configure jail for nginx
cat > /etc/fail2ban/jail.d/nginx.conf <<EOF
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
EOF

systemctl restart fail2ban
```

---

## Appendix

### Quick Reference Commands

```bash
# DNS verification
dig api.corporate-intel.com +short

# Obtain SSL certificate
sudo certbot certonly --webroot -w /var/www/certbot -d api.corporate-intel.com

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check certificate expiry
sudo certbot certificates

# Renew certificates
sudo certbot renew

# Test SSL grade
curl -I https://api.corporate-intel.com

# View renewal timer
systemctl status certbot-renewal.timer
```

### Configuration Templates

See `/config/production/` for complete templates:
- `nginx.conf` - Production nginx configuration
- `traefik.yml` - Traefik static configuration
- `traefik-dynamic.yml` - Traefik dynamic configuration

### Additional Resources

- **Let's Encrypt**: https://letsencrypt.org/docs/
- **Certbot**: https://certbot.eff.org/
- **Mozilla SSL Config**: https://ssl-config.mozilla.org/
- **SSL Labs**: https://www.ssllabs.com/
- **Nginx Docs**: https://nginx.org/en/docs/
- **Traefik Docs**: https://doc.traefik.io/traefik/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-17
**Maintained By**: DevOps Team
**Review Cycle**: Quarterly
