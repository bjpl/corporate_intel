#!/bin/bash
# Corporate Intel SSL Certificate Automation Script
# Manages Let's Encrypt SSL certificates with Certbot
# Updated: 2025-10-17

set -euo pipefail

# Configuration
DOMAINS=("api.corporate-intel.com" "metrics.corporate-intel.com" "docs.corporate-intel.com")
EMAIL="admin@corporate-intel.com"
WEBROOT="/var/www/certbot"
CERTBOT_PATH="/usr/bin/certbot"
NGINX_PATH="/usr/sbin/nginx"
BACKUP_DIR="/var/backups/ssl-certs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Install Certbot if not present
install_certbot() {
    if ! command -v certbot &> /dev/null; then
        log "Installing Certbot..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    else
        log "Certbot is already installed ($(certbot --version))"
    fi
}

# Create webroot directory for ACME challenge
setup_webroot() {
    log "Setting up webroot directory..."
    mkdir -p "$WEBROOT"
    chown -R www-data:www-data "$WEBROOT"
    chmod -R 755 "$WEBROOT"
}

# Backup existing certificates
backup_certificates() {
    log "Backing up existing certificates..."
    mkdir -p "$BACKUP_DIR"

    if [[ -d /etc/letsencrypt ]]; then
        BACKUP_FILE="$BACKUP_DIR/letsencrypt-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        tar -czf "$BACKUP_FILE" /etc/letsencrypt
        log "Backup created: $BACKUP_FILE"
    else
        warning "No existing certificates to backup"
    fi
}

# Obtain SSL certificates
obtain_certificates() {
    log "Obtaining SSL certificates..."

    for domain in "${DOMAINS[@]}"; do
        log "Processing domain: $domain"

        # Check if certificate already exists
        if [[ -d "/etc/letsencrypt/live/$domain" ]]; then
            warning "Certificate already exists for $domain, skipping..."
            continue
        fi

        # Obtain certificate using webroot method
        $CERTBOT_PATH certonly \
            --webroot \
            --webroot-path="$WEBROOT" \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email \
            --domain "$domain" \
            --non-interactive \
            --quiet

        if [[ $? -eq 0 ]]; then
            log "Certificate obtained successfully for $domain"
        else
            error "Failed to obtain certificate for $domain"
            exit 1
        fi
    done
}

# Obtain wildcard certificate (requires DNS challenge)
obtain_wildcard_certificate() {
    log "Obtaining wildcard certificate..."

    # This requires DNS plugin (e.g., certbot-dns-cloudflare)
    # Uncomment and configure for your DNS provider

    # $CERTBOT_PATH certonly \
    #     --dns-cloudflare \
    #     --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
    #     --email "$EMAIL" \
    #     --agree-tos \
    #     --no-eff-email \
    #     --domain "*.corporate-intel.com" \
    #     --domain "corporate-intel.com" \
    #     --non-interactive

    warning "Wildcard certificate setup requires DNS plugin configuration"
}

# Test nginx configuration
test_nginx_config() {
    log "Testing nginx configuration..."

    if $NGINX_PATH -t; then
        log "Nginx configuration is valid"
        return 0
    else
        error "Nginx configuration test failed"
        return 1
    fi
}

# Reload nginx
reload_nginx() {
    log "Reloading nginx..."

    if test_nginx_config; then
        systemctl reload nginx
        log "Nginx reloaded successfully"
    else
        error "Nginx reload failed due to configuration errors"
        exit 1
    fi
}

# Setup automatic renewal
setup_renewal() {
    log "Setting up automatic certificate renewal..."

    # Create renewal hook script
    cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/bash
# Reload nginx after successful certificate renewal
systemctl reload nginx
logger "SSL certificates renewed and nginx reloaded"
EOF

    chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

    # Test renewal process (dry-run)
    log "Testing renewal process (dry-run)..."
    $CERTBOT_PATH renew --dry-run

    if [[ $? -eq 0 ]]; then
        log "Renewal test successful"
    else
        warning "Renewal test failed, but continuing..."
    fi

    # Setup systemd timer for automatic renewal
    setup_systemd_timer
}

# Setup systemd timer for certificate renewal
setup_systemd_timer() {
    log "Configuring systemd timer for certificate renewal..."

    # Create systemd service
    cat > /etc/systemd/system/certbot-renewal.service <<EOF
[Unit]
Description=Certbot SSL Certificate Renewal
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$CERTBOT_PATH renew --quiet --deploy-hook "systemctl reload nginx"
StandardOutput=journal
StandardError=journal
EOF

    # Create systemd timer (runs twice daily)
    cat > /etc/systemd/system/certbot-renewal.timer <<EOF
[Unit]
Description=Certbot SSL Certificate Renewal Timer
After=network-online.target

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable and start timer
    systemctl daemon-reload
    systemctl enable certbot-renewal.timer
    systemctl start certbot-renewal.timer

    log "Systemd timer configured and started"
    systemctl status certbot-renewal.timer --no-pager
}

# Verify SSL configuration
verify_ssl() {
    log "Verifying SSL configuration..."

    for domain in "${DOMAINS[@]}"; do
        log "Checking $domain..."

        # Test HTTPS connection
        if curl -sI "https://$domain" | grep -q "200 OK\|301 Moved Permanently\|302 Found"; then
            log "HTTPS working for $domain"
        else
            warning "HTTPS check failed for $domain"
        fi

        # Check SSL grade (requires ssllabs-scan or similar)
        # Uncomment if ssllabs-scan is installed
        # ssllabs-scan --quiet "$domain"
    done
}

# Generate DH parameters for enhanced security
generate_dhparams() {
    log "Generating DH parameters (this may take several minutes)..."

    if [[ ! -f /etc/ssl/certs/dhparam.pem ]]; then
        openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
        log "DH parameters generated"
    else
        log "DH parameters already exist"
    fi
}

# Setup monitoring and alerting
setup_monitoring() {
    log "Setting up certificate expiration monitoring..."

    # Create monitoring script
    cat > /usr/local/bin/check-cert-expiry.sh <<'EOF'
#!/bin/bash
# Check SSL certificate expiration

ALERT_DAYS=30
DOMAINS=("api.corporate-intel.com" "metrics.corporate-intel.com" "docs.corporate-intel.com")

for domain in "${DOMAINS[@]}"; do
    expiry_date=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    expiry_epoch=$(date -d "$expiry_date" +%s)
    current_epoch=$(date +%s)
    days_until_expiry=$(( ($expiry_epoch - $current_epoch) / 86400 ))

    if [[ $days_until_expiry -lt $ALERT_DAYS ]]; then
        echo "WARNING: Certificate for $domain expires in $days_until_expiry days" | logger -t cert-expiry
        # Send alert (configure your alerting mechanism)
        # Example: mail -s "SSL Cert Expiring" admin@corporate-intel.com
    fi
done
EOF

    chmod +x /usr/local/bin/check-cert-expiry.sh

    # Add to crontab (daily check)
    (crontab -l 2>/dev/null; echo "0 8 * * * /usr/local/bin/check-cert-expiry.sh") | crontab -

    log "Certificate monitoring configured"
}

# Display certificate information
show_cert_info() {
    log "Certificate Information:"

    for domain in "${DOMAINS[@]}"; do
        if [[ -d "/etc/letsencrypt/live/$domain" ]]; then
            echo -e "\n${GREEN}Domain: $domain${NC}"
            certbot certificates -d "$domain" 2>/dev/null | grep -A 5 "Certificate Name"
        fi
    done
}

# Main execution
main() {
    log "Starting SSL Certificate Setup for Corporate Intel"

    check_root
    install_certbot
    setup_webroot
    backup_certificates
    generate_dhparams
    obtain_certificates
    # obtain_wildcard_certificate  # Uncomment if using wildcard cert
    setup_renewal
    reload_nginx
    verify_ssl
    setup_monitoring
    show_cert_info

    log "SSL Certificate setup completed successfully!"
    log "Certificates will auto-renew twice daily via systemd timer"
    log "Next renewal check: $(systemctl show certbot-renewal.timer | grep NextElapseUSecRealtime)"
}

# Script entry point
case "${1:-}" in
    install)
        check_root
        install_certbot
        ;;
    obtain)
        check_root
        obtain_certificates
        ;;
    renew)
        check_root
        $CERTBOT_PATH renew
        reload_nginx
        ;;
    verify)
        verify_ssl
        ;;
    info)
        show_cert_info
        ;;
    *)
        main
        ;;
esac
