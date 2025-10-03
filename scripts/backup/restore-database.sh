#!/bin/bash
set -euo pipefail

# PostgreSQL Restore Script
# Restores database from backup with verification

BACKUP_FILE="${1:-}"
RESTORE_DIR="${RESTORE_DIR:-/restore/postgres}"
S3_BUCKET="${S3_BUCKET:-s3://corporate-intel-backups/postgres}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-postgres}"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Usage: $0 <backup-file-name>"
    echo ""
    echo "Available backups:"
    aws s3 ls "$S3_BUCKET/" | grep "\.sql\.gz$"
    exit 1
fi

RESTORE_PATH="${RESTORE_DIR}/${BACKUP_FILE}"

echo "🔄 Starting database restore..."

# Create restore directory
mkdir -p "$RESTORE_DIR"

# Download backup from S3
echo "☁️  Downloading backup from S3..."
aws s3 cp "${S3_BUCKET}/${BACKUP_FILE}" "$RESTORE_PATH"
aws s3 cp "${S3_BUCKET}/${BACKUP_FILE}.sha256" "${RESTORE_PATH}.sha256"

# Verify checksum
echo "🔐 Verifying checksum..."
if sha256sum -c "${RESTORE_PATH}.sha256"; then
    echo "✅ Checksum verified"
else
    echo "❌ Checksum verification failed!"
    exit 1
fi

# Decompress backup
echo "📦 Decompressing backup..."
gunzip -k "$RESTORE_PATH"
UNCOMPRESSED_FILE="${RESTORE_PATH%.gz}"

# Create database backup before restore (safety measure)
echo "💾 Creating safety backup of current database..."
SAFETY_BACKUP="/tmp/safety_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=custom --compress=9 --file="${SAFETY_BACKUP%.gz}"
gzip -9 "${SAFETY_BACKUP%.gz}"
echo "✅ Safety backup created: $SAFETY_BACKUP"

# Terminate active connections
echo "🔌 Terminating active connections..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '${DB_NAME}'
  AND pid <> pg_backend_pid();
EOF

# Drop and recreate database
echo "🗑️  Dropping database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"

echo "🔨 Creating database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Restore database
echo "📥 Restoring database..."
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose \
    --no-owner \
    --no-acl \
    "$UNCOMPRESSED_FILE" 2>&1 | tee "${RESTORE_DIR}/restore_$(date +%Y%m%d_%H%M%S).log"

# Verify restore
echo "✅ Verifying restore..."
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "📊 Tables restored: $TABLE_COUNT"

# Run ANALYZE to update statistics
echo "📈 Updating database statistics..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ANALYZE;"

# Send notification
echo "📧 Sending restore notification..."
cat <<EOF | mail -s "Database Restore Complete - ${BACKUP_FILE}" restore-notifications@corporate-intel.com
Database restore completed successfully:

Backup File: ${BACKUP_FILE}
Restore Time: $(date)
Tables Restored: ${TABLE_COUNT}
Safety Backup: ${SAFETY_BACKUP}

Logs: ${RESTORE_DIR}/restore_$(date +%Y%m%d_%H%M%S).log

Next Steps:
1. Verify application functionality
2. Check data integrity
3. Monitor database performance
EOF

# Cleanup
echo "🧹 Cleaning up..."
rm -f "$UNCOMPRESSED_FILE"

echo "✅ Database restore complete!"
echo "⚠️  Safety backup available at: $SAFETY_BACKUP"
echo "📋 Please verify application functionality"
