#!/bin/bash
# Corporate Intelligence Platform - Restore Script
# Restores database and volumes from backup
# Usage: ./scripts/restore.sh <backup_directory>

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-}"
POSTGRES_CONTAINER="corporate-intel-postgres"
DB_NAME="${POSTGRES_DB:-corporate_intel}"
DB_USER="${POSTGRES_USER:-intel_user}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Validate backup directory
if [ -z "$BACKUP_DIR" ]; then
    error "Usage: $0 <backup_directory>"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Confirmation prompt
warn "This will REPLACE all current data with backup from: $BACKUP_DIR"
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Restore cancelled"
    exit 0
fi

log "=== Starting restore from: $BACKUP_DIR ==="

# Stop application containers
log "Stopping application containers..."
docker-compose stop api

# Restore PostgreSQL
log "Restoring PostgreSQL database..."
POSTGRES_BACKUP=$(find "$BACKUP_DIR" -name "postgres_*.sql.gz" | head -1)
if [ -n "$POSTGRES_BACKUP" ]; then
    gunzip -c "$POSTGRES_BACKUP" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$DB_USER" "$DB_NAME"
    log "PostgreSQL restored"
else
    error "PostgreSQL backup file not found"
    exit 1
fi

# Restore volumes
log "Restoring Docker volumes..."
for volume_backup in "$BACKUP_DIR"/*-data_*.tar.gz; do
    volume_name=$(basename "$volume_backup" | sed 's/_[0-9]*.tar.gz//' | sed 's/^/corporate-intel-/')
    log "Restoring volume: $volume_name"

    docker run --rm \
        -v "$volume_name:/volume" \
        -v "$BACKUP_DIR:/backup" \
        alpine sh -c "cd /volume && tar xzf /backup/$(basename $volume_backup)"
done

log "=== Restore completed successfully ==="
log "Restarting services..."
docker-compose up -d

log "Services restarted. Please verify application functionality."
