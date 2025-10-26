#!/bin/bash
#
# PostgreSQL Automated Backup Script
# Supports: Full backups, WAL archiving, compression, encryption, retention policies
#
# Usage: ./postgres-backup.sh [full|incremental]
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-postgres}"
PGPASSWORD="${PGPASSWORD:-}"

# Backup directories
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/postgres}"
BACKUP_DIR="${BACKUP_ROOT}/daily"
WEEKLY_DIR="${BACKUP_ROOT}/weekly"
MONTHLY_DIR="${BACKUP_ROOT}/monthly"
WAL_ARCHIVE_DIR="${BACKUP_ROOT}/wal-archive"

# Retention policies (days)
DAILY_RETENTION=7
WEEKLY_RETENTION=28
MONTHLY_RETENTION=365

# Compression and encryption
COMPRESSION="gzip"
COMPRESSION_LEVEL=6
GPG_RECIPIENT="${GPG_RECIPIENT:-backup@corporate-intel.local}"
ENCRYPT_BACKUPS="${ENCRYPT_BACKUPS:-true}"

# Remote storage (S3-compatible)
REMOTE_STORAGE="${REMOTE_STORAGE:-true}"
S3_BUCKET="${S3_BUCKET:-corporate-intel-backups}"
S3_ENDPOINT="${S3_ENDPOINT:-https://s3.amazonaws.com}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

# Monitoring and alerting
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_ALERTS="${EMAIL_ALERTS:-ops@corporate-intel.local}"

# Logging
LOG_DIR="${BACKUP_ROOT}/logs"
LOG_FILE="${LOG_DIR}/backup-$(date +%Y%m%d-%H%M%S).log"

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

send_alert() {
    local status="$1"
    local message="$2"

    # Slack notification
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[Backup ${status}] ${message}\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi

    # Email notification
    if [[ -n "$EMAIL_ALERTS" ]]; then
        echo "$message" | mail -s "Database Backup ${status}" "$EMAIL_ALERTS" 2>/dev/null || true
    fi
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check required commands
    local required_commands=("pg_dump" "pg_dumpall" "gzip" "aws")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "Required command not found: $cmd"
            return 1
        fi
    done

    # Check encryption key if enabled
    if [[ "$ENCRYPT_BACKUPS" == "true" ]]; then
        if ! command -v gpg &> /dev/null; then
            error "GPG not found but encryption is enabled"
            return 1
        fi
        if ! gpg --list-keys "$GPG_RECIPIENT" &> /dev/null; then
            error "GPG recipient key not found: $GPG_RECIPIENT"
            return 1
        fi
    fi

    # Create directories
    mkdir -p "$BACKUP_DIR" "$WEEKLY_DIR" "$MONTHLY_DIR" "$WAL_ARCHIVE_DIR" "$LOG_DIR"

    log "Prerequisites check passed"
    return 0
}

test_database_connection() {
    log "Testing database connection..."

    if ! PGPASSWORD="$PGPASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" &> /dev/null; then
        error "Failed to connect to database"
        return 1
    fi

    log "Database connection successful"
    return 0
}

perform_full_backup() {
    local backup_type="$1"  # daily, weekly, or monthly
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local day_of_week=$(date +%u)
    local day_of_month=$(date +%d)

    log "Starting full backup (type: ${backup_type})..."

    # Determine backup directory based on type
    local target_dir="$BACKUP_DIR"
    if [[ "$backup_type" == "weekly" ]]; then
        target_dir="$WEEKLY_DIR"
    elif [[ "$backup_type" == "monthly" ]]; then
        target_dir="$MONTHLY_DIR"
    fi

    # Backup filename
    local backup_file="${target_dir}/${DB_NAME}_${backup_type}_${timestamp}.sql"

    # Perform dump
    log "Dumping database to: ${backup_file}"
    if ! PGPASSWORD="$PGPASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -F c \
        -f "${backup_file}.dump"; then
        error "Database dump failed"
        return 1
    fi

    # Get backup size
    local backup_size=$(du -h "${backup_file}.dump" | cut -f1)
    log "Dump completed. Size: ${backup_size}"

    # Compress backup
    log "Compressing backup..."
    if ! gzip -${COMPRESSION_LEVEL} "${backup_file}.dump"; then
        error "Compression failed"
        return 1
    fi
    mv "${backup_file}.dump.gz" "${backup_file}.gz"

    local compressed_size=$(du -h "${backup_file}.gz" | cut -f1)
    log "Compression completed. Size: ${compressed_size}"

    # Encrypt backup if enabled
    if [[ "$ENCRYPT_BACKUPS" == "true" ]]; then
        log "Encrypting backup..."
        if ! gpg --encrypt --recipient "$GPG_RECIPIENT" "${backup_file}.gz"; then
            error "Encryption failed"
            return 1
        fi
        mv "${backup_file}.gz.gpg" "${backup_file}.gz.gpg"
        rm -f "${backup_file}.gz"

        local encrypted_size=$(du -h "${backup_file}.gz.gpg" | cut -f1)
        log "Encryption completed. Size: ${encrypted_size}"

        backup_file="${backup_file}.gz.gpg"
    else
        backup_file="${backup_file}.gz"
    fi

    # Also backup global objects (roles, tablespaces)
    if [[ "$backup_type" == "daily" ]] || [[ "$day_of_week" == "7" ]]; then
        log "Backing up global objects..."
        local globals_file="${target_dir}/globals_${timestamp}.sql"

        if PGPASSWORD="$PGPASSWORD" pg_dumpall \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            --globals-only \
            -f "$globals_file"; then
            gzip -${COMPRESSION_LEVEL} "$globals_file"

            if [[ "$ENCRYPT_BACKUPS" == "true" ]]; then
                gpg --encrypt --recipient "$GPG_RECIPIENT" "${globals_file}.gz"
                rm -f "${globals_file}.gz"
            fi
        fi
    fi

    # Upload to remote storage
    if [[ "$REMOTE_STORAGE" == "true" ]]; then
        upload_to_remote "$backup_file" "$backup_type"
    fi

    # Create backup metadata
    create_backup_metadata "$backup_file" "$backup_type"

    log "Full backup completed successfully: $(basename $backup_file)"
    return 0
}

upload_to_remote() {
    local backup_file="$1"
    local backup_type="$2"

    log "Uploading backup to remote storage..."

    local s3_path="s3://${S3_BUCKET}/${backup_type}/$(basename $backup_file)"

    if aws s3 cp "$backup_file" "$s3_path" \
        --endpoint-url "$S3_ENDPOINT" \
        --storage-class STANDARD_IA \
        --metadata "backup-date=$(date -Iseconds),db-name=${DB_NAME},backup-type=${backup_type}"; then
        log "Upload successful: ${s3_path}"
        return 0
    else
        error "Upload failed: ${s3_path}"
        return 1
    fi
}

create_backup_metadata() {
    local backup_file="$1"
    local backup_type="$2"
    local metadata_file="${backup_file}.metadata.json"

    cat > "$metadata_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "database": "${DB_NAME}",
  "host": "${DB_HOST}",
  "backup_type": "${backup_type}",
  "backup_file": "$(basename $backup_file)",
  "file_size": $(stat -c%s "$backup_file"),
  "file_size_human": "$(du -h $backup_file | cut -f1)",
  "compressed": true,
  "encrypted": ${ENCRYPT_BACKUPS},
  "postgresql_version": "$(PGPASSWORD=$PGPASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -t -c 'SELECT version()' | tr -d '\n' | xargs)",
  "checksum_sha256": "$(sha256sum $backup_file | cut -d' ' -f1)"
}
EOF

    log "Backup metadata created: ${metadata_file}"
}

cleanup_old_backups() {
    log "Cleaning up old backups..."

    # Daily backups cleanup
    find "$BACKUP_DIR" -name "${DB_NAME}_daily_*.sql.*" -type f -mtime +${DAILY_RETENTION} -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "globals_*.sql.*" -type f -mtime +${DAILY_RETENTION} -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*.metadata.json" -type f -mtime +${DAILY_RETENTION} -delete 2>/dev/null || true

    # Weekly backups cleanup
    find "$WEEKLY_DIR" -name "${DB_NAME}_weekly_*.sql.*" -type f -mtime +${WEEKLY_RETENTION} -delete 2>/dev/null || true

    # Monthly backups cleanup
    find "$MONTHLY_DIR" -name "${DB_NAME}_monthly_*.sql.*" -type f -mtime +${MONTHLY_RETENTION} -delete 2>/dev/null || true

    # Log files cleanup
    find "$LOG_DIR" -name "backup-*.log" -type f -mtime +30 -delete 2>/dev/null || true

    log "Cleanup completed"
}

archive_wal_files() {
    log "Archiving WAL files..."

    # This function is called by PostgreSQL archive_command
    # Example archive_command in postgresql.conf:
    # archive_command = '/path/to/postgres-backup.sh archive-wal %p %f'

    if [[ "$1" == "archive-wal" ]]; then
        local wal_path="$2"
        local wal_file="$3"

        cp "$wal_path" "${WAL_ARCHIVE_DIR}/${wal_file}"

        if [[ "$REMOTE_STORAGE" == "true" ]]; then
            aws s3 cp "${WAL_ARCHIVE_DIR}/${wal_file}" \
                "s3://${S3_BUCKET}/wal-archive/${wal_file}" \
                --endpoint-url "$S3_ENDPOINT"
        fi

        # Keep only last 7 days of WAL files locally
        find "$WAL_ARCHIVE_DIR" -type f -mtime +7 -delete 2>/dev/null || true
    fi
}

verify_backup() {
    local backup_file="$1"

    log "Verifying backup integrity..."

    # Check file exists and is not empty
    if [[ ! -f "$backup_file" ]] || [[ ! -s "$backup_file" ]]; then
        error "Backup file is missing or empty"
        return 1
    fi

    # Verify checksum if metadata exists
    if [[ -f "${backup_file}.metadata.json" ]]; then
        local stored_checksum=$(jq -r '.checksum_sha256' "${backup_file}.metadata.json")
        local actual_checksum=$(sha256sum "$backup_file" | cut -d' ' -f1)

        if [[ "$stored_checksum" != "$actual_checksum" ]]; then
            error "Checksum verification failed"
            return 1
        fi
    fi

    log "Backup verification passed"
    return 0
}

generate_backup_report() {
    log "Generating backup report..."

    local report_file="${BACKUP_ROOT}/backup-report-$(date +%Y%m%d).txt"

    cat > "$report_file" <<EOF
Database Backup Report - $(date)
================================================================

Database: ${DB_NAME}
Host: ${DB_HOST}:${DB_PORT}

Daily Backups:
$(ls -lh "$BACKUP_DIR" | grep "${DB_NAME}_daily" || echo "No daily backups found")

Weekly Backups:
$(ls -lh "$WEEKLY_DIR" | grep "${DB_NAME}_weekly" || echo "No weekly backups found")

Monthly Backups:
$(ls -lh "$MONTHLY_DIR" | grep "${DB_NAME}_monthly" || echo "No monthly backups found")

Disk Usage:
Daily:   $(du -sh "$BACKUP_DIR" | cut -f1)
Weekly:  $(du -sh "$WEEKLY_DIR" | cut -f1)
Monthly: $(du -sh "$MONTHLY_DIR" | cut -f1)
Total:   $(du -sh "$BACKUP_ROOT" | cut -f1)

Recent Log Entries:
$(tail -n 20 "$LOG_FILE")
EOF

    log "Report generated: ${report_file}"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    local backup_type="${1:-daily}"
    local start_time=$(date +%s)

    log "==================================================================="
    log "PostgreSQL Backup Script Starting"
    log "Backup Type: ${backup_type}"
    log "==================================================================="

    # Check prerequisites
    if ! check_prerequisites; then
        error "Prerequisites check failed"
        send_alert "FAILED" "Backup prerequisites check failed for ${DB_NAME}"
        exit 1
    fi

    # Test database connection
    if ! test_database_connection; then
        error "Database connection test failed"
        send_alert "FAILED" "Cannot connect to database ${DB_NAME}"
        exit 1
    fi

    # Determine backup type based on day
    local day_of_week=$(date +%u)
    local day_of_month=$(date +%d)

    if [[ "$day_of_month" == "01" ]]; then
        backup_type="monthly"
    elif [[ "$day_of_week" == "7" ]]; then
        backup_type="weekly"
    else
        backup_type="daily"
    fi

    # Perform backup
    if perform_full_backup "$backup_type"; then
        log "Backup successful"

        # Cleanup old backups
        cleanup_old_backups

        # Generate report
        generate_backup_report

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log "Backup completed in ${duration} seconds"
        send_alert "SUCCESS" "Backup completed successfully for ${DB_NAME} (${backup_type}, ${duration}s)"

        exit 0
    else
        error "Backup failed"
        send_alert "FAILED" "Backup failed for ${DB_NAME}"
        exit 1
    fi
}

# Handle WAL archiving if called with archive-wal argument
if [[ "${1:-}" == "archive-wal" ]]; then
    archive_wal_files "$@"
    exit 0
fi

# Run main backup
main "$@"
