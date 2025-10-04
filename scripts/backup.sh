#!/bin/bash
# Corporate Intelligence Platform - Automated Backup Script
# Backs up PostgreSQL database and Docker volumes
# Usage: ./scripts/backup.sh [daily|weekly|monthly]

set -euo pipefail

# Configuration
BACKUP_TYPE="${1:-daily}"
BACKUP_ROOT="/var/backups/corporate-intel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${BACKUP_TYPE}/${TIMESTAMP}"
RETENTION_DAYS_DAILY=7
RETENTION_DAYS_WEEKLY=30
RETENTION_DAYS_MONTHLY=365

# Docker container and volume names
POSTGRES_CONTAINER="corporate-intel-postgres"
DB_NAME="${POSTGRES_DB:-corporate_intel}"
DB_USER="${POSTGRES_USER:-intel_user}"

# Volume names
POSTGRES_VOLUME="corporate-intel-postgres-data"
REDIS_VOLUME="corporate-intel-redis-data"
MINIO_VOLUME="corporate-intel-minio-data"

# Notification settings
ALERT_EMAIL="${BACKUP_ALERT_EMAIL:-admin@example.com}"
SLACK_WEBHOOK="${SLACK_BACKUP_WEBHOOK:-}"

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
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Send notification
notify() {
    local status=$1
    local message=$2

    # Email notification
    if command -v mail &> /dev/null && [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Corporate Intel Backup ${status}" "$ALERT_EMAIL"
    fi

    # Slack notification
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Corporate Intel Backup ${status}: ${message}\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
}

# Create backup directory
create_backup_dir() {
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
}

# Backup PostgreSQL database
backup_postgres() {
    log "Backing up PostgreSQL database..."

    local dump_file="${BACKUP_DIR}/postgres_${DB_NAME}_${TIMESTAMP}.sql.gz"

    if docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$dump_file"; then
        log "PostgreSQL backup completed: $dump_file"

        # Verify backup integrity
        if gzip -t "$dump_file" 2>/dev/null; then
            log "PostgreSQL backup integrity verified"
            echo "$dump_file" >> "${BACKUP_DIR}/backup_manifest.txt"
        else
            error "PostgreSQL backup integrity check failed"
            return 1
        fi
    else
        error "PostgreSQL backup failed"
        return 1
    fi
}

# Backup Docker volumes
backup_volume() {
    local volume_name=$1
    local backup_name=$2

    log "Backing up Docker volume: $volume_name"

    local tar_file="${BACKUP_DIR}/${backup_name}_${TIMESTAMP}.tar.gz"

    if docker run --rm \
        -v "$volume_name:/volume" \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/$(basename $tar_file)" -C /volume .; then
        log "Volume backup completed: $tar_file"
        echo "$tar_file" >> "${BACKUP_DIR}/backup_manifest.txt"
    else
        error "Volume backup failed: $volume_name"
        return 1
    fi
}

# Create backup metadata
create_metadata() {
    log "Creating backup metadata..."

    cat > "${BACKUP_DIR}/metadata.json" <<EOF
{
  "backup_type": "${BACKUP_TYPE}",
  "timestamp": "${TIMESTAMP}",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "database": "${DB_NAME}",
  "hostname": "$(hostname)",
  "docker_version": "$(docker --version)",
  "postgres_version": "$(docker exec $POSTGRES_CONTAINER psql -V)",
  "backup_size": "$(du -sh $BACKUP_DIR | cut -f1)"
}
EOF

    log "Metadata created"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."

    local retention_days
    case "$BACKUP_TYPE" in
        daily)
            retention_days=$RETENTION_DAYS_DAILY
            ;;
        weekly)
            retention_days=$RETENTION_DAYS_WEEKLY
            ;;
        monthly)
            retention_days=$RETENTION_DAYS_MONTHLY
            ;;
        *)
            retention_days=$RETENTION_DAYS_DAILY
            ;;
    esac

    log "Retention policy: ${retention_days} days for ${BACKUP_TYPE} backups"

    find "${BACKUP_ROOT}/${BACKUP_TYPE}" -type d -mtime +${retention_days} -exec rm -rf {} + 2>/dev/null || true

    log "Old backups cleaned up"
}

# Verify backup success
verify_backup() {
    log "Verifying backup completeness..."

    local required_files=(
        "postgres_${DB_NAME}_${TIMESTAMP}.sql.gz"
        "postgres-data_${TIMESTAMP}.tar.gz"
        "redis-data_${TIMESTAMP}.tar.gz"
        "minio-data_${TIMESTAMP}.tar.gz"
        "metadata.json"
        "backup_manifest.txt"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "${BACKUP_DIR}/${file}" ]; then
            error "Missing backup file: $file"
            return 1
        fi
    done

    log "All backup files verified"
    return 0
}

# Main backup process
main() {
    log "=== Starting Corporate Intelligence Platform Backup ==="
    log "Backup type: $BACKUP_TYPE"

    local start_time=$(date +%s)

    # Check if Docker is running
    if ! docker ps >/dev/null 2>&1; then
        error "Docker is not running"
        notify "FAILED" "Docker is not running"
        exit 1
    fi

    # Check if containers are running
    if ! docker ps --format '{{.Names}}' | grep -q "$POSTGRES_CONTAINER"; then
        error "PostgreSQL container is not running"
        notify "FAILED" "PostgreSQL container is not running"
        exit 1
    fi

    # Create backup directory
    create_backup_dir

    # Perform backups
    if backup_postgres && \
       backup_volume "$POSTGRES_VOLUME" "postgres-data" && \
       backup_volume "$REDIS_VOLUME" "redis-data" && \
       backup_volume "$MINIO_VOLUME" "minio-data"; then

        # Create metadata
        create_metadata

        # Verify backup
        if verify_backup; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))

            log "=== Backup completed successfully in ${duration}s ==="
            log "Backup location: $BACKUP_DIR"
            log "Backup size: $(du -sh $BACKUP_DIR | cut -f1)"

            # Cleanup old backups
            cleanup_old_backups

            notify "SUCCESS" "Backup completed in ${duration}s. Location: $BACKUP_DIR"
            exit 0
        else
            error "Backup verification failed"
            notify "FAILED" "Backup verification failed"
            exit 1
        fi
    else
        error "Backup failed"
        notify "FAILED" "Backup process failed"
        exit 1
    fi
}

# Run main function
main
