#!/bin/bash
set -euo pipefail

# PostgreSQL Backup Script with Retention Policy
# Performs full database backup and uploads to S3

BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-s3://corporate-intel-backups/postgres}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-corporate_intel}"
DB_USER="${DB_USER:-postgres}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="corporate_intel_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

echo "🗄️  Starting database backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform backup with pg_dump
echo "📦 Creating backup: $BACKUP_FILE"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --verbose \
    --file="${BACKUP_PATH%.gz}" 2>&1 | tee "${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Compress backup
gzip -9 "${BACKUP_PATH%.gz}"

# Calculate checksum
echo "🔐 Calculating checksum..."
sha256sum "$BACKUP_PATH" > "${BACKUP_PATH}.sha256"

# Get backup size
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | awk '{print $1}')
echo "📊 Backup size: $BACKUP_SIZE"

# Upload to S3
echo "☁️  Uploading to S3..."
aws s3 cp "$BACKUP_PATH" "$S3_BUCKET/" --storage-class INTELLIGENT_TIERING
aws s3 cp "${BACKUP_PATH}.sha256" "$S3_BUCKET/"
aws s3 cp "${BACKUP_DIR}/backup_${TIMESTAMP}.log" "$S3_BUCKET/logs/"

# Verify upload
echo "✅ Verifying S3 upload..."
aws s3 ls "${S3_BUCKET}/${BACKUP_FILE}"

# Apply retention policy
echo "🗑️  Applying retention policy (${RETENTION_DAYS} days)..."
find "$BACKUP_DIR" -name "corporate_intel_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "backup_*.log" -mtime +$RETENTION_DAYS -delete

# S3 lifecycle policy (delete after retention period)
CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)
aws s3 ls "$S3_BUCKET/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
        echo "Deleting old backup: $FILE_NAME"
        aws s3 rm "${S3_BUCKET}/${FILE_NAME}"
    fi
done

# Send notification
echo "📧 Sending backup notification..."
cat <<EOF | mail -s "Database Backup Complete - ${BACKUP_FILE}" backup-notifications@corporate-intel.com
Database backup completed successfully:

Backup File: ${BACKUP_FILE}
Backup Size: ${BACKUP_SIZE}
Timestamp: ${TIMESTAMP}
S3 Location: ${S3_BUCKET}/${BACKUP_FILE}
Retention: ${RETENTION_DAYS} days

Checksum: $(cat "${BACKUP_PATH}.sha256")

Logs: ${BACKUP_DIR}/backup_${TIMESTAMP}.log
EOF

# Prometheus metrics
cat <<EOF > /var/lib/node_exporter/textfile_collector/postgres_backup.prom
# HELP postgres_backup_size_bytes Size of the last PostgreSQL backup
# TYPE postgres_backup_size_bytes gauge
postgres_backup_size_bytes $(stat -c%s "$BACKUP_PATH")

# HELP postgres_backup_timestamp_seconds Timestamp of the last PostgreSQL backup
# TYPE postgres_backup_timestamp_seconds gauge
postgres_backup_timestamp_seconds $(date +%s)

# HELP postgres_backup_success Success status of the last backup (1=success, 0=failure)
# TYPE postgres_backup_success gauge
postgres_backup_success 1
EOF

echo "✅ Database backup complete!"
echo "📁 Local: $BACKUP_PATH"
echo "☁️  S3: ${S3_BUCKET}/${BACKUP_FILE}"
