#!/bin/bash
#
# Backup Monitoring and Alerting Script
# Monitors backup health, tracks metrics, and sends alerts
#
# Usage: ./monitor-backups.sh
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/postgres}"
MINIO_BACKUP_ROOT="${MINIO_BACKUP_ROOT:-/var/backups/minio}"
METRICS_DIR="${BACKUP_ROOT}/metrics"
LOG_DIR="${BACKUP_ROOT}/logs"

# Alert thresholds
MAX_BACKUP_AGE_HOURS=24
MIN_BACKUP_SIZE_MB=10
MAX_BACKUP_SIZE_GB=100
DISK_USAGE_WARNING_PERCENT=80
DISK_USAGE_CRITICAL_PERCENT=90

# Alerting
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_ALERTS="${EMAIL_ALERTS:-ops@corporate-intel.local}"
PAGERDUTY_KEY="${PAGERDUTY_KEY:-}"

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

send_alert() {
    local severity="$1"  # INFO, WARNING, CRITICAL
    local title="$2"
    local message="$3"

    local color="good"
    case "$severity" in
        WARNING) color="warning" ;;
        CRITICAL) color="danger" ;;
    esac

    # Slack notification
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"${color}\",
                    \"title\": \"[${severity}] ${title}\",
                    \"text\": \"${message}\",
                    \"footer\": \"Backup Monitoring\",
                    \"ts\": $(date +%s)
                }]
            }" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi

    # Email notification
    if [[ -n "$EMAIL_ALERTS" ]]; then
        echo -e "Subject: [${severity}] Backup Alert: ${title}\n\n${message}" | \
            sendmail "$EMAIL_ALERTS" 2>/dev/null || true
    fi

    # PagerDuty for critical alerts
    if [[ "$severity" == "CRITICAL" ]] && [[ -n "$PAGERDUTY_KEY" ]]; then
        curl -X POST https://events.pagerduty.com/v2/enqueue \
            -H 'Content-Type: application/json' \
            -d "{
                \"routing_key\": \"${PAGERDUTY_KEY}\",
                \"event_action\": \"trigger\",
                \"payload\": {
                    \"summary\": \"${title}\",
                    \"severity\": \"critical\",
                    \"source\": \"backup-monitor\",
                    \"custom_details\": {
                        \"message\": \"${message}\"
                    }
                }
            }" 2>/dev/null || true
    fi
}

check_backup_age() {
    log "Checking backup age..."

    local latest_backup=$(find "${BACKUP_ROOT}/daily" -name "*.sql.*" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)

    if [[ -z "$latest_backup" ]]; then
        send_alert "CRITICAL" "No Backups Found" "No database backups found in ${BACKUP_ROOT}/daily"
        return 1
    fi

    local backup_timestamp=$(echo "$latest_backup" | cut -d' ' -f1 | cut -d'.' -f1)
    local current_timestamp=$(date +%s)
    local age_hours=$(( (current_timestamp - backup_timestamp) / 3600 ))

    local backup_file=$(echo "$latest_backup" | cut -d' ' -f2-)

    if [[ $age_hours -gt $MAX_BACKUP_AGE_HOURS ]]; then
        send_alert "CRITICAL" "Backup Too Old" \
            "Latest backup is ${age_hours} hours old (threshold: ${MAX_BACKUP_AGE_HOURS}h)\nFile: $(basename $backup_file)"
        return 1
    elif [[ $age_hours -gt $((MAX_BACKUP_AGE_HOURS / 2)) ]]; then
        send_alert "WARNING" "Backup Age Warning" \
            "Latest backup is ${age_hours} hours old\nFile: $(basename $backup_file)"
    fi

    log "✓ Latest backup age: ${age_hours} hours"
    echo "$age_hours" > "${METRICS_DIR}/last_backup_age_hours.txt"
    return 0
}

check_backup_size() {
    log "Checking backup size..."

    local latest_backup=$(find "${BACKUP_ROOT}/daily" -name "*.sql.*" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

    if [[ -z "$latest_backup" ]]; then
        return 1
    fi

    local size_bytes=$(stat -c%s "$latest_backup")
    local size_mb=$((size_bytes / 1024 / 1024))
    local size_gb=$((size_bytes / 1024 / 1024 / 1024))

    if [[ $size_mb -lt $MIN_BACKUP_SIZE_MB ]]; then
        send_alert "CRITICAL" "Backup Too Small" \
            "Backup size (${size_mb}MB) is below minimum threshold (${MIN_BACKUP_SIZE_MB}MB)\nFile: $(basename $latest_backup)"
        return 1
    fi

    if [[ $size_gb -gt $MAX_BACKUP_SIZE_GB ]]; then
        send_alert "WARNING" "Backup Size Large" \
            "Backup size (${size_gb}GB) exceeds ${MAX_BACKUP_SIZE_GB}GB\nFile: $(basename $latest_backup)"
    fi

    log "✓ Latest backup size: ${size_mb}MB"
    echo "$size_mb" > "${METRICS_DIR}/last_backup_size_mb.txt"
    return 0
}

check_disk_usage() {
    log "Checking disk usage..."

    local backup_disk_usage=$(df "${BACKUP_ROOT}" | awk 'NR==2 {print $5}' | sed 's/%//')

    if [[ $backup_disk_usage -ge $DISK_USAGE_CRITICAL_PERCENT ]]; then
        send_alert "CRITICAL" "Backup Disk Full" \
            "Backup disk usage is at ${backup_disk_usage}% (critical: ${DISK_USAGE_CRITICAL_PERCENT}%)"
        return 1
    elif [[ $backup_disk_usage -ge $DISK_USAGE_WARNING_PERCENT ]]; then
        send_alert "WARNING" "Backup Disk Usage High" \
            "Backup disk usage is at ${backup_disk_usage}% (warning: ${DISK_USAGE_WARNING_PERCENT}%)"
    fi

    log "✓ Backup disk usage: ${backup_disk_usage}%"
    echo "$backup_disk_usage" > "${METRICS_DIR}/disk_usage_percent.txt"
    return 0
}

check_backup_success_rate() {
    log "Checking backup success rate..."

    local log_file=$(find "${LOG_DIR}" -name "backup-*.log" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)

    if [[ -z "$log_file" ]]; then
        send_alert "WARNING" "No Backup Logs" "No backup log files found"
        return 1
    fi

    # Check last 10 backup attempts
    local total_attempts=0
    local successful=0

    for log in $(find "${LOG_DIR}" -name "backup-*.log" -type f -mtime -7 | sort -rn | head -10); do
        ((total_attempts++))
        if grep -q "Backup completed successfully" "$log"; then
            ((successful++))
        fi
    done

    if [[ $total_attempts -gt 0 ]]; then
        local success_rate=$(awk "BEGIN {printf \"%.1f\", ($successful/$total_attempts)*100}")

        if (( $(echo "$success_rate < 80" | bc -l) )); then
            send_alert "CRITICAL" "Low Backup Success Rate" \
                "Backup success rate is ${success_rate}% (${successful}/${total_attempts} successful)"
            return 1
        elif (( $(echo "$success_rate < 95" | bc -l) )); then
            send_alert "WARNING" "Backup Success Rate Warning" \
                "Backup success rate is ${success_rate}% (${successful}/${total_attempts} successful)"
        fi

        log "✓ Backup success rate: ${success_rate}% (${successful}/${total_attempts})"
        echo "$success_rate" > "${METRICS_DIR}/success_rate_percent.txt"
    fi

    return 0
}

check_backup_count() {
    log "Checking backup counts..."

    local daily_count=$(find "${BACKUP_ROOT}/daily" -name "*.sql.*" -type f | wc -l)
    local weekly_count=$(find "${BACKUP_ROOT}/weekly" -name "*.sql.*" -type f | wc -l)
    local monthly_count=$(find "${BACKUP_ROOT}/monthly" -name "*.sql.*" -type f | wc -l)

    # Expected: 7 daily, 4 weekly, 12 monthly
    if [[ $daily_count -lt 5 ]]; then
        send_alert "WARNING" "Low Daily Backup Count" \
            "Only ${daily_count} daily backups found (expected: ~7)"
    fi

    log "✓ Backup counts - Daily: ${daily_count}, Weekly: ${weekly_count}, Monthly: ${monthly_count}"
    echo "$daily_count" > "${METRICS_DIR}/daily_backup_count.txt"
    echo "$weekly_count" > "${METRICS_DIR}/weekly_backup_count.txt"
    echo "$monthly_count" > "${METRICS_DIR}/monthly_backup_count.txt"

    return 0
}

check_minio_backups() {
    log "Checking MinIO backups..."

    if [[ ! -d "$MINIO_BACKUP_ROOT" ]]; then
        log "⚠ MinIO backup directory not found, skipping"
        return 0
    fi

    local snapshot_count=$(find "${MINIO_BACKUP_ROOT}/snapshots" -name "*.tar.gz" -type f -mtime -7 | wc -l)

    if [[ $snapshot_count -eq 0 ]]; then
        send_alert "WARNING" "No Recent MinIO Backups" \
            "No MinIO snapshots found from the last 7 days"
        return 1
    fi

    log "✓ MinIO snapshots (last 7 days): ${snapshot_count}"
    echo "$snapshot_count" > "${METRICS_DIR}/minio_snapshot_count.txt"
    return 0
}

check_remote_storage() {
    log "Checking remote storage sync..."

    if ! command -v aws &>/dev/null; then
        log "⚠ AWS CLI not found, skipping remote storage check"
        return 0
    fi

    local s3_bucket="${S3_BUCKET:-corporate-intel-backups}"
    local s3_endpoint="${S3_ENDPOINT:-https://s3.amazonaws.com}"

    local remote_daily_count=$(aws s3 ls "s3://${s3_bucket}/daily/" --endpoint-url "$s3_endpoint" 2>/dev/null | wc -l || echo "0")

    if [[ $remote_daily_count -eq 0 ]]; then
        send_alert "CRITICAL" "No Remote Backups" \
            "No backups found in remote storage: s3://${s3_bucket}/daily/"
        return 1
    fi

    log "✓ Remote backup count: ${remote_daily_count}"
    echo "$remote_daily_count" > "${METRICS_DIR}/remote_backup_count.txt"
    return 0
}

generate_metrics_json() {
    local metrics_file="${METRICS_DIR}/backup_metrics_$(date +%Y%m%d-%H%M%S).json"

    cat > "$metrics_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "metrics": {
    "last_backup_age_hours": $(cat "${METRICS_DIR}/last_backup_age_hours.txt" 2>/dev/null || echo "null"),
    "last_backup_size_mb": $(cat "${METRICS_DIR}/last_backup_size_mb.txt" 2>/dev/null || echo "null"),
    "disk_usage_percent": $(cat "${METRICS_DIR}/disk_usage_percent.txt" 2>/dev/null || echo "null"),
    "success_rate_percent": $(cat "${METRICS_DIR}/success_rate_percent.txt" 2>/dev/null || echo "null"),
    "daily_backup_count": $(cat "${METRICS_DIR}/daily_backup_count.txt" 2>/dev/null || echo "null"),
    "weekly_backup_count": $(cat "${METRICS_DIR}/weekly_backup_count.txt" 2>/dev/null || echo "null"),
    "monthly_backup_count": $(cat "${METRICS_DIR}/monthly_backup_count.txt" 2>/dev/null || echo "null"),
    "minio_snapshot_count": $(cat "${METRICS_DIR}/minio_snapshot_count.txt" 2>/dev/null || echo "null"),
    "remote_backup_count": $(cat "${METRICS_DIR}/remote_backup_count.txt" 2>/dev/null || echo "null")
  },
  "thresholds": {
    "max_backup_age_hours": $MAX_BACKUP_AGE_HOURS,
    "min_backup_size_mb": $MIN_BACKUP_SIZE_MB,
    "disk_usage_warning_percent": $DISK_USAGE_WARNING_PERCENT,
    "disk_usage_critical_percent": $DISK_USAGE_CRITICAL_PERCENT
  }
}
EOF

    log "Metrics saved to: ${metrics_file}"

    # Keep only last 30 days of metrics
    find "$METRICS_DIR" -name "backup_metrics_*.json" -type f -mtime +30 -delete 2>/dev/null || true
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log "==================================================================="
    log "Backup Monitoring Script Starting"
    log "==================================================================="

    mkdir -p "$METRICS_DIR" "$LOG_DIR"

    local failed_checks=0

    # Run all checks
    check_backup_age || ((failed_checks++))
    check_backup_size || ((failed_checks++))
    check_disk_usage || ((failed_checks++))
    check_backup_success_rate || ((failed_checks++))
    check_backup_count || ((failed_checks++))
    check_minio_backups || ((failed_checks++))
    check_remote_storage || ((failed_checks++))

    # Generate metrics
    generate_metrics_json

    log "==================================================================="
    log "Monitoring Summary:"
    log "  Failed Checks: ${failed_checks}"
    log "==================================================================="

    if [[ $failed_checks -eq 0 ]]; then
        log "✓ All backup health checks passed"
        exit 0
    else
        error "✗ ${failed_checks} backup health check(s) failed"
        exit 1
    fi
}

main "$@"
