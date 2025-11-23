#!/bin/bash
# SSL Certificate Renewal Cron Script
# Alternative to systemd timer for systems using cron
# Updated: 2025-10-17

set -euo pipefail

# Configuration
LOGFILE="/var/log/certbot-renewal.log"
CERTBOT_PATH="/usr/bin/certbot"
NGINX_PATH="/usr/sbin/nginx"
EMAIL="admin@corporate-intel.com"

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

# Email notification function
send_notification() {
    local subject="$1"
    local message="$2"

    # Configure your mail command or API call here
    # Example using mail command:
    # echo "$message" | mail -s "$subject" "$EMAIL"

    # Example using sendmail or API
    log "Notification: $subject - $message"
}

# Renewal function
renew_certificates() {
    log "Starting certificate renewal process..."

    # Run renewal
    if $CERTBOT_PATH renew --quiet --deploy-hook "systemctl reload nginx" 2>&1 | tee -a "$LOGFILE"; then
        log "Certificate renewal completed successfully"
        send_notification "SSL Renewal Success" "SSL certificates renewed successfully"
        return 0
    else
        log "ERROR: Certificate renewal failed"
        send_notification "SSL Renewal Failed" "Certificate renewal process failed. Check logs at $LOGFILE"
        return 1
    fi
}

# Check certificate expiration
check_expiration() {
    log "Checking certificate expiration..."

    DOMAINS=("api.corporate-intel.com" "metrics.corporate-intel.com" "docs.corporate-intel.com")

    for domain in "${DOMAINS[@]}"; do
        if [[ -d "/etc/letsencrypt/live/$domain" ]]; then
            expiry_date=$(openssl x509 -in "/etc/letsencrypt/live/$domain/cert.pem" -noout -enddate | cut -d= -f2)
            expiry_epoch=$(date -d "$expiry_date" +%s)
            current_epoch=$(date +%s)
            days_until_expiry=$(( ($expiry_epoch - $current_epoch) / 86400 ))

            log "$domain expires in $days_until_expiry days"

            if [[ $days_until_expiry -lt 30 ]]; then
                send_notification "SSL Certificate Expiring Soon" "$domain expires in $days_until_expiry days"
            fi
        fi
    done
}

# Main execution
log "=== SSL Certificate Renewal Cron Job Started ==="
check_expiration
renew_certificates
log "=== SSL Certificate Renewal Cron Job Completed ==="

# Cleanup old logs (keep last 90 days)
find /var/log/certbot-renewal.log.* -mtime +90 -delete 2>/dev/null || true
