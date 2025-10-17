#!/bin/bash
set -euo pipefail

# SSL/TLS Setup with Let's Encrypt - Production Deployment
# This script automates SSL certificate generation and renewal setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
DOMAIN="${DOMAIN:-corporate-intel.example.com}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@example.com}"
WEBROOT="${WEBROOT:-/var/www/certbot}"
CERT_DIR="${CERT_DIR:-/etc/letsencrypt}"
STAGING="${STAGING:-false}"
DRY_RUN="${DRY_RUN:-false}"

usage() {
    cat << EOF
SSL/TLS Setup with Let's Encrypt

Usage: $0 [OPTIONS]

Options:
    -d, --domain DOMAIN         Domain name (required)
    -e, --email EMAIL           Email for Let's Encrypt (required)
    -s, --staging               Use Let's Encrypt staging environment
    --dry-run                   Dry run mode (no actual changes)
    -h, --help                  Show this help message

Environment Variables:
    DOMAIN                      Domain name
    LETSENCRYPT_EMAIL           Contact email
    WEBROOT                     Webroot directory (default: /var/www/certbot)
    STAGING                     Use staging environment (default: false)

Examples:
    # Production certificate
    $0 -d corporate-intel.com -e admin@corporate-intel.com

    # Staging certificate (testing)
    $0 -d corporate-intel.com -e admin@corporate-intel.com --staging

    # Dry run
    $0 -d corporate-intel.com -e admin@corporate-intel.com --dry-run

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain) DOMAIN="$2"; shift 2 ;;
        -e|--email) EMAIL="$2"; shift 2 ;;
        -s|--staging) STAGING="true"; shift ;;
        --dry-run) DRY_RUN="true"; shift ;;
        -h|--help) usage ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

# Validation
if [[ "$DOMAIN" == "corporate-intel.example.com" ]] || [[ -z "$DOMAIN" ]]; then
    print_error "Valid domain name required"
    usage
fi

if [[ "$EMAIL" == "admin@example.com" ]] || [[ -z "$EMAIL" ]]; then
    print_error "Valid email address required"
    usage
fi

print_info "SSL/TLS Setup for $DOMAIN"
print_info "Contact Email: $EMAIL"
[[ "$STAGING" == "true" ]] && print_warning "Using Let's Encrypt STAGING environment"
[[ "$DRY_RUN" == "true" ]] && print_warning "DRY RUN MODE - No changes will be made"

# Step 1: Check prerequisites
print_step "Checking prerequisites..."

if ! command -v certbot &> /dev/null; then
    print_error "certbot is not installed"
    print_info "Install certbot:"
    print_info "  Ubuntu/Debian: sudo apt-get install certbot python3-certbot-nginx"
    print_info "  CentOS/RHEL: sudo yum install certbot python3-certbot-nginx"
    exit 1
fi

if ! command -v nginx &> /dev/null; then
    print_warning "nginx not found in PATH - ensure nginx is installed and running"
fi

print_info "Prerequisites check passed"

# Step 2: Create webroot directory for ACME challenge
print_step "Setting up webroot for ACME challenge..."
if [[ "$DRY_RUN" == "false" ]]; then
    sudo mkdir -p "$WEBROOT"
    sudo chown -R www-data:www-data "$WEBROOT" 2>/dev/null || sudo chown -R nginx:nginx "$WEBROOT" 2>/dev/null || true
fi
print_info "Webroot created: $WEBROOT"

# Step 3: Test DNS resolution
print_step "Verifying DNS resolution..."
if ! host "$DOMAIN" &> /dev/null; then
    print_error "Domain $DOMAIN does not resolve"
    print_error "Please configure DNS A/AAAA record before proceeding"
    exit 1
fi

DOMAIN_IP=$(host "$DOMAIN" | grep "has address" | head -1 | awk '{print $4}')
print_info "Domain resolves to: $DOMAIN_IP"

# Step 4: Check if nginx is configured
print_step "Checking nginx configuration..."
if systemctl is-active --quiet nginx 2>/dev/null; then
    print_info "nginx is running"

    # Test nginx configuration
    if sudo nginx -t &> /dev/null; then
        print_info "nginx configuration is valid"
    else
        print_error "nginx configuration has errors"
        sudo nginx -t
        exit 1
    fi
else
    print_warning "nginx is not running - certificate will be obtained in standalone mode"
fi

# Step 5: Generate SSL certificate
print_step "Generating SSL certificate..."

CERTBOT_OPTS=(
    "--non-interactive"
    "--agree-tos"
    "--email" "$EMAIL"
    "-d" "$DOMAIN"
)

# Add staging flag if requested
if [[ "$STAGING" == "true" ]]; then
    CERTBOT_OPTS+=("--staging")
fi

# Choose certbot mode
if systemctl is-active --quiet nginx 2>/dev/null; then
    print_info "Using webroot authentication method"
    CERTBOT_OPTS+=("--webroot" "-w" "$WEBROOT")
else
    print_info "Using standalone authentication method"
    CERTBOT_OPTS+=("--standalone" "--preferred-challenges" "http")
fi

if [[ "$DRY_RUN" == "false" ]]; then
    if sudo certbot certonly "${CERTBOT_OPTS[@]}"; then
        print_info "SSL certificate generated successfully!"
    else
        print_error "Failed to generate SSL certificate"
        exit 1
    fi
else
    print_info "DRY RUN: Would execute: certbot certonly ${CERTBOT_OPTS[*]}"
fi

# Step 6: Verify certificate files
print_step "Verifying certificate files..."
CERT_PATH="${CERT_DIR}/live/${DOMAIN}"

if [[ "$DRY_RUN" == "false" ]]; then
    if [[ -f "${CERT_PATH}/fullchain.pem" ]] && [[ -f "${CERT_PATH}/privkey.pem" ]]; then
        print_info "Certificate files verified"
        print_info "  Certificate: ${CERT_PATH}/fullchain.pem"
        print_info "  Private Key: ${CERT_PATH}/privkey.pem"
        print_info "  Chain: ${CERT_PATH}/chain.pem"

        # Display certificate info
        print_info "Certificate Details:"
        sudo openssl x509 -in "${CERT_PATH}/fullchain.pem" -noout -dates
    else
        print_error "Certificate files not found"
        exit 1
    fi
fi

# Step 7: Configure automatic renewal
print_step "Setting up automatic certificate renewal..."

if [[ "$DRY_RUN" == "false" ]]; then
    # Create renewal hook script
    RENEWAL_HOOK="/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"
    sudo mkdir -p "$(dirname "$RENEWAL_HOOK")"

    cat << 'HOOK_SCRIPT' | sudo tee "$RENEWAL_HOOK" > /dev/null
#!/bin/bash
# Reload nginx after certificate renewal
systemctl reload nginx || docker-compose restart nginx 2>/dev/null || true
echo "SSL certificate renewed and nginx reloaded"
HOOK_SCRIPT

    sudo chmod +x "$RENEWAL_HOOK"
    print_info "Renewal hook created: $RENEWAL_HOOK"

    # Test renewal
    print_info "Testing certificate renewal..."
    if sudo certbot renew --dry-run; then
        print_info "Certificate renewal test successful"
    else
        print_warning "Certificate renewal test failed - check certbot configuration"
    fi

    # Set up cron job for renewal check
    CRON_CMD="0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx' >> /var/log/letsencrypt-renewal.log 2>&1"

    if ! sudo crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (sudo crontab -l 2>/dev/null; echo "$CRON_CMD") | sudo crontab -
        print_info "Cron job created for automatic renewal"
    else
        print_info "Cron job for renewal already exists"
    fi
fi

# Step 8: Generate DH parameters
print_step "Generating Diffie-Hellman parameters..."
DH_PARAM="${CERT_DIR}/ssl-dhparams.pem"

if [[ "$DRY_RUN" == "false" ]]; then
    if [[ ! -f "$DH_PARAM" ]]; then
        print_info "Generating 2048-bit DH parameters (this may take several minutes)..."
        sudo openssl dhparam -out "$DH_PARAM" 2048
        print_info "DH parameters generated: $DH_PARAM"
    else
        print_info "DH parameters already exist: $DH_PARAM"
    fi
fi

# Step 9: Update nginx configuration
print_step "Updating nginx configuration..."

NGINX_SSL_CONF="/etc/nginx/conf.d/${DOMAIN}-ssl.conf"

if [[ "$DRY_RUN" == "false" ]]; then
    cat << EOF | sudo tee "$NGINX_SSL_CONF" > /dev/null
# SSL Configuration for ${DOMAIN}
# Generated by setup-ssl-letsencrypt.sh

ssl_certificate ${CERT_PATH}/fullchain.pem;
ssl_certificate_key ${CERT_PATH}/privkey.pem;
ssl_trusted_certificate ${CERT_PATH}/chain.pem;

# SSL Session Configuration
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# Modern TLS Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;

# DH Parameters
ssl_dhparam ${DH_PARAM};

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security Headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
EOF

    print_info "Nginx SSL configuration created: $NGINX_SSL_CONF"
fi

# Step 10: Test and reload nginx
if [[ "$DRY_RUN" == "false" ]]; then
    print_step "Testing and reloading nginx..."

    if sudo nginx -t; then
        print_info "Nginx configuration test passed"
        if systemctl is-active --quiet nginx; then
            sudo systemctl reload nginx
            print_info "Nginx reloaded successfully"
        fi
    else
        print_error "Nginx configuration test failed"
        exit 1
    fi
fi

# Step 11: Create monitoring metrics
print_step "Setting up certificate expiry monitoring..."

if [[ "$DRY_RUN" == "false" ]]; then
    CERT_MONITOR_SCRIPT="/usr/local/bin/check-ssl-expiry.sh"

    cat << 'MONITOR_SCRIPT' | sudo tee "$CERT_MONITOR_SCRIPT" > /dev/null
#!/bin/bash
# Certificate expiry monitoring for Prometheus
DOMAIN="$1"
CERT_FILE="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"

if [[ -f "$CERT_FILE" ]]; then
    EXPIRY_DATE=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_REMAINING=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

    mkdir -p /var/lib/node_exporter/textfile_collector
    cat > /var/lib/node_exporter/textfile_collector/ssl_cert_expiry.prom << EOF
# HELP ssl_cert_expiry_days Days until SSL certificate expires
# TYPE ssl_cert_expiry_days gauge
ssl_cert_expiry_days{domain="${DOMAIN}"} ${DAYS_REMAINING}
EOF

    echo "SSL certificate for ${DOMAIN} expires in ${DAYS_REMAINING} days"
else
    echo "Certificate file not found: $CERT_FILE"
    exit 1
fi
MONITOR_SCRIPT

    sudo chmod +x "$CERT_MONITOR_SCRIPT"
    print_info "Certificate monitoring script created: $CERT_MONITOR_SCRIPT"

    # Add to cron
    MONITOR_CRON="0 */6 * * * $CERT_MONITOR_SCRIPT $DOMAIN >> /var/log/ssl-cert-monitor.log 2>&1"
    if ! sudo crontab -l 2>/dev/null | grep -q "check-ssl-expiry"; then
        (sudo crontab -l 2>/dev/null; echo "$MONITOR_CRON") | sudo crontab -
        print_info "Certificate monitoring cron job created"
    fi
fi

# Summary
print_info ""
print_info "================================================"
print_info "SSL/TLS Setup Complete!"
print_info "================================================"
print_info "Domain: $DOMAIN"
print_info "Certificate Path: ${CERT_PATH}"
print_info "Nginx Config: $NGINX_SSL_CONF"
print_info ""
print_info "Next Steps:"
print_info "1. Update your main nginx configuration to include:"
print_info "   include ${NGINX_SSL_CONF};"
print_info "2. Test your site: https://${DOMAIN}"
print_info "3. Check SSL rating: https://www.ssllabs.com/ssltest/"
print_info "4. Monitor certificate expiry with Prometheus"
print_info ""
print_info "Automatic Renewal:"
print_info "- Certificates renew automatically 30 days before expiry"
print_info "- Test renewal: sudo certbot renew --dry-run"
print_info "- Check renewal log: /var/log/letsencrypt/letsencrypt.log"
print_info ""
print_info "Monitoring:"
print_info "- Certificate expiry metrics: /var/lib/node_exporter/textfile_collector/ssl_cert_expiry.prom"
print_info "- Check expiry: $CERT_MONITOR_SCRIPT $DOMAIN"
print_info "================================================"
