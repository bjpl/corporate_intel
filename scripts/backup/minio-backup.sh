#!/bin/bash
#
# MinIO Object Storage Backup Script
# Supports: Bucket replication, incremental backups, versioning, lifecycle policies
#
# Usage: ./minio-backup.sh [backup|replicate|verify]
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# MinIO source configuration
MINIO_SOURCE_ENDPOINT="${MINIO_SOURCE_ENDPOINT:-http://localhost:9000}"
MINIO_SOURCE_ACCESS_KEY="${MINIO_SOURCE_ACCESS_KEY:-minioadmin}"
MINIO_SOURCE_SECRET_KEY="${MINIO_SOURCE_SECRET_KEY:-minioadmin}"
MINIO_SOURCE_ALIAS="source-minio"

# MinIO destination/backup configuration
MINIO_BACKUP_ENDPOINT="${MINIO_BACKUP_ENDPOINT:-http://backup-minio:9000}"
MINIO_BACKUP_ACCESS_KEY="${MINIO_BACKUP_ACCESS_KEY:-minioadmin}"
MINIO_BACKUP_SECRET_KEY="${MINIO_BACKUP_SECRET_KEY:-minioadmin}"
MINIO_BACKUP_ALIAS="backup-minio"

# Buckets to backup
BUCKETS_TO_BACKUP="${BUCKETS_TO_BACKUP:-company-data,embeddings,user-uploads}"

# Backup directories
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/minio}"
BACKUP_DIR="${BACKUP_ROOT}/snapshots"
LOG_DIR="${BACKUP_ROOT}/logs"

# Remote storage (S3-compatible for off-site backups)
REMOTE_STORAGE="${REMOTE_STORAGE:-true}"
S3_BUCKET="${S3_BUCKET:-corporate-intel-minio-backups}"
S3_ENDPOINT="${S3_ENDPOINT:-https://s3.amazonaws.com}"
S3_ALIAS="s3-backup"

# Retention
SNAPSHOT_RETENTION=7  # days
INCREMENTAL_RETENTION=30  # days

# Monitoring
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_ALERTS="${EMAIL_ALERTS:-ops@corporate-intel.local}"

# Logging
LOG_FILE="${LOG_DIR}/minio-backup-$(date +%Y%m%d-%H%M%S).log"

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

    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[MinIO Backup ${status}] ${message}\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi

    if [[ -n "$EMAIL_ALERTS" ]]; then
        echo "$message" | mail -s "MinIO Backup ${status}" "$EMAIL_ALERTS" 2>/dev/null || true
    fi
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check mc (MinIO Client)
    if ! command -v mc &> /dev/null; then
        error "MinIO Client (mc) not found. Install from: https://min.io/docs/minio/linux/reference/minio-mc.html"
        return 1
    fi

    # Create directories
    mkdir -p "$BACKUP_DIR" "$LOG_DIR"

    log "Prerequisites check passed"
    return 0
}

configure_mc_aliases() {
    log "Configuring MinIO Client aliases..."

    # Configure source MinIO
    mc alias set "$MINIO_SOURCE_ALIAS" \
        "$MINIO_SOURCE_ENDPOINT" \
        "$MINIO_SOURCE_ACCESS_KEY" \
        "$MINIO_SOURCE_SECRET_KEY" \
        --api S3v4

    # Configure backup MinIO
    mc alias set "$MINIO_BACKUP_ALIAS" \
        "$MINIO_BACKUP_ENDPOINT" \
        "$MINIO_BACKUP_ACCESS_KEY" \
        "$MINIO_BACKUP_SECRET_KEY" \
        --api S3v4

    # Configure remote S3 if enabled
    if [[ "$REMOTE_STORAGE" == "true" ]]; then
        mc alias set "$S3_ALIAS" \
            "$S3_ENDPOINT" \
            "$AWS_ACCESS_KEY_ID" \
            "$AWS_SECRET_ACCESS_KEY" \
            --api S3v4
    fi

    log "MC aliases configured successfully"
    return 0
}

enable_versioning() {
    local alias="$1"
    local bucket="$2"

    log "Enabling versioning for ${alias}/${bucket}..."

    if mc version enable "${alias}/${bucket}"; then
        log "Versioning enabled for ${bucket}"
        return 0
    else
        error "Failed to enable versioning for ${bucket}"
        return 1
    fi
}

setup_bucket_replication() {
    local source_bucket="$1"
    local dest_bucket="$2"

    log "Setting up replication: ${source_bucket} -> ${dest_bucket}..."

    # Create destination bucket if it doesn't exist
    mc mb "${MINIO_BACKUP_ALIAS}/${dest_bucket}" --ignore-existing

    # Enable versioning on both buckets (required for replication)
    enable_versioning "$MINIO_SOURCE_ALIAS" "$source_bucket"
    enable_versioning "$MINIO_BACKUP_ALIAS" "$dest_bucket"

    # Create replication configuration
    local replication_id="backup-replication-${source_bucket}"

    mc replicate add "${MINIO_SOURCE_ALIAS}/${source_bucket}" \
        --remote-bucket "${dest_bucket}" \
        --arn "arn:minio:replication::${replication_id}:${MINIO_BACKUP_ENDPOINT}" \
        --path "/" \
        --priority 1 \
        --replicate "delete,delete-marker,existing-objects" \
        --storage-class "STANDARD" || {
        log "Replication rule already exists or setup failed, continuing..."
    }

    log "Replication configured for ${source_bucket}"
    return 0
}

perform_snapshot_backup() {
    local bucket="$1"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local snapshot_dir="${BACKUP_DIR}/${bucket}_${timestamp}"

    log "Creating snapshot backup for bucket: ${bucket}..."

    mkdir -p "$snapshot_dir"

    # Mirror bucket to local snapshot
    if mc mirror "${MINIO_SOURCE_ALIAS}/${bucket}" "$snapshot_dir" \
        --preserve \
        --overwrite; then

        local backup_size=$(du -sh "$snapshot_dir" | cut -f1)
        log "Snapshot created successfully. Size: ${backup_size}"

        # Create tar archive
        local archive_file="${BACKUP_DIR}/${bucket}_${timestamp}.tar.gz"
        tar -czf "$archive_file" -C "$BACKUP_DIR" "$(basename $snapshot_dir)"

        # Remove uncompressed snapshot
        rm -rf "$snapshot_dir"

        local archive_size=$(du -sh "$archive_file" | cut -f1)
        log "Archive created: ${archive_file} (${archive_size})"

        # Create metadata
        create_snapshot_metadata "$archive_file" "$bucket"

        # Upload to remote storage
        if [[ "$REMOTE_STORAGE" == "true" ]]; then
            upload_snapshot_to_remote "$archive_file" "$bucket"
        fi

        return 0
    else
        error "Snapshot backup failed for ${bucket}"
        return 1
    fi
}

perform_incremental_backup() {
    local bucket="$1"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local incremental_dir="${BACKUP_DIR}/incremental/${bucket}_${timestamp}"

    log "Performing incremental backup for bucket: ${bucket}..."

    mkdir -p "$incremental_dir"

    # Find last snapshot
    local last_snapshot=$(find "${BACKUP_DIR}/incremental" -name "${bucket}_*.tar.gz" -type f 2>/dev/null | sort | tail -1)

    if [[ -z "$last_snapshot" ]]; then
        log "No previous snapshot found, performing full snapshot..."
        perform_snapshot_backup "$bucket"
        return $?
    fi

    # Mirror only changes since last backup
    mc mirror "${MINIO_SOURCE_ALIAS}/${bucket}" "$incremental_dir" \
        --preserve \
        --newer-than "24h"

    # Create incremental archive
    local archive_file="${BACKUP_DIR}/incremental/${bucket}_${timestamp}.tar.gz"
    tar -czf "$archive_file" -C "${BACKUP_DIR}/incremental" "$(basename $incremental_dir)"
    rm -rf "$incremental_dir"

    log "Incremental backup completed: ${archive_file}"
    return 0
}

upload_snapshot_to_remote() {
    local archive_file="$1"
    local bucket="$2"

    log "Uploading snapshot to remote storage..."

    if mc cp "$archive_file" "${S3_ALIAS}/${S3_BUCKET}/snapshots/$(basename $archive_file)"; then
        log "Upload successful"

        # Also upload metadata
        if [[ -f "${archive_file}.metadata.json" ]]; then
            mc cp "${archive_file}.metadata.json" \
                "${S3_ALIAS}/${S3_BUCKET}/snapshots/$(basename ${archive_file}).metadata.json"
        fi

        return 0
    else
        error "Upload failed"
        return 1
    fi
}

create_snapshot_metadata() {
    local archive_file="$1"
    local bucket="$2"
    local metadata_file="${archive_file}.metadata.json"

    # Get bucket statistics
    local object_count=$(mc ls "${MINIO_SOURCE_ALIAS}/${bucket}" --recursive | wc -l)
    local bucket_size=$(mc du "${MINIO_SOURCE_ALIAS}/${bucket}" | awk '{print $1}')

    cat > "$metadata_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "bucket": "${bucket}",
  "source_endpoint": "${MINIO_SOURCE_ENDPOINT}",
  "archive_file": "$(basename $archive_file)",
  "archive_size": $(stat -c%s "$archive_file"),
  "archive_size_human": "$(du -h $archive_file | cut -f1)",
  "object_count": ${object_count},
  "bucket_size": ${bucket_size},
  "checksum_sha256": "$(sha256sum $archive_file | cut -d' ' -f1)",
  "backup_type": "snapshot"
}
EOF

    log "Metadata created: ${metadata_file}"
}

verify_bucket_sync() {
    local source_bucket="$1"
    local dest_bucket="$2"

    log "Verifying bucket synchronization..."

    # Compare object counts
    local source_count=$(mc ls "${MINIO_SOURCE_ALIAS}/${source_bucket}" --recursive | wc -l)
    local dest_count=$(mc ls "${MINIO_BACKUP_ALIAS}/${dest_bucket}" --recursive | wc -l)

    log "Source bucket object count: ${source_count}"
    log "Destination bucket object count: ${dest_count}"

    if [[ "$source_count" -eq "$dest_count" ]]; then
        log "Object counts match - verification passed"
        return 0
    else
        error "Object counts do not match - verification failed"
        return 1
    fi
}

configure_lifecycle_policy() {
    local bucket="$1"
    local retention_days="${2:-90}"

    log "Configuring lifecycle policy for ${bucket}..."

    # Create lifecycle configuration
    cat > /tmp/lifecycle-${bucket}.json <<EOF
{
  "Rules": [
    {
      "ID": "expire-old-versions",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": ${retention_days}
      }
    },
    {
      "ID": "cleanup-incomplete-uploads",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "AbortIncompleteMultipartUpload": {
        "DaysAfterInitiation": 7
      }
    }
  ]
}
EOF

    mc ilm import "${MINIO_SOURCE_ALIAS}/${bucket}" < /tmp/lifecycle-${bucket}.json
    rm /tmp/lifecycle-${bucket}.json

    log "Lifecycle policy configured"
    return 0
}

cleanup_old_backups() {
    log "Cleaning up old backups..."

    # Cleanup local snapshots
    find "$BACKUP_DIR" -name "*.tar.gz" -type f -mtime +${SNAPSHOT_RETENTION} -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*.metadata.json" -type f -mtime +${SNAPSHOT_RETENTION} -delete 2>/dev/null || true

    # Cleanup incremental backups
    find "${BACKUP_DIR}/incremental" -name "*.tar.gz" -type f -mtime +${INCREMENTAL_RETENTION} -delete 2>/dev/null || true

    # Cleanup logs
    find "$LOG_DIR" -name "minio-backup-*.log" -type f -mtime +30 -delete 2>/dev/null || true

    log "Cleanup completed"
}

generate_backup_report() {
    log "Generating backup report..."

    local report_file="${BACKUP_ROOT}/minio-backup-report-$(date +%Y%m%d).txt"

    cat > "$report_file" <<EOF
MinIO Backup Report - $(date)
================================================================

Source MinIO: ${MINIO_SOURCE_ENDPOINT}
Backup MinIO: ${MINIO_BACKUP_ENDPOINT}

Buckets Backed Up:
$(echo "$BUCKETS_TO_BACKUP" | tr ',' '\n')

Recent Snapshots:
$(ls -lht "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -10 || echo "No snapshots found")

Disk Usage:
Snapshots:    $(du -sh "$BACKUP_DIR" | cut -f1)
Incremental:  $(du -sh "${BACKUP_DIR}/incremental" 2>/dev/null | cut -f1 || echo "N/A")
Total:        $(du -sh "$BACKUP_ROOT" | cut -f1)

Bucket Statistics:
EOF

    IFS=',' read -ra BUCKET_ARRAY <<< "$BUCKETS_TO_BACKUP"
    for bucket in "${BUCKET_ARRAY[@]}"; do
        echo "" >> "$report_file"
        echo "Bucket: ${bucket}" >> "$report_file"
        mc du "${MINIO_SOURCE_ALIAS}/${bucket}" >> "$report_file" 2>/dev/null || echo "  Error reading bucket" >> "$report_file"
    done

    log "Report generated: ${report_file}"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    local operation="${1:-backup}"
    local start_time=$(date +%s)

    log "==================================================================="
    log "MinIO Backup Script Starting"
    log "Operation: ${operation}"
    log "==================================================================="

    # Check prerequisites
    if ! check_prerequisites; then
        error "Prerequisites check failed"
        send_alert "FAILED" "MinIO backup prerequisites check failed"
        exit 1
    fi

    # Configure MC aliases
    if ! configure_mc_aliases; then
        error "Failed to configure MC aliases"
        send_alert "FAILED" "MinIO client configuration failed"
        exit 1
    fi

    # Parse buckets
    IFS=',' read -ra BUCKET_ARRAY <<< "$BUCKETS_TO_BACKUP"

    case "$operation" in
        backup)
            log "Performing backup operation..."
            local failed=0

            for bucket in "${BUCKET_ARRAY[@]}"; do
                if perform_snapshot_backup "$bucket"; then
                    log "Backup successful for bucket: ${bucket}"
                else
                    error "Backup failed for bucket: ${bucket}"
                    ((failed++))
                fi
            done

            cleanup_old_backups
            generate_backup_report

            if [[ $failed -eq 0 ]]; then
                local end_time=$(date +%s)
                local duration=$((end_time - start_time))
                send_alert "SUCCESS" "All bucket backups completed (${duration}s)"
                exit 0
            else
                send_alert "PARTIAL" "${failed} bucket backup(s) failed"
                exit 1
            fi
            ;;

        replicate)
            log "Setting up replication..."

            for bucket in "${BUCKET_ARRAY[@]}"; do
                setup_bucket_replication "$bucket" "$bucket"
                configure_lifecycle_policy "$bucket" 90
            done

            send_alert "SUCCESS" "Replication configured for all buckets"
            ;;

        verify)
            log "Verifying backups..."
            local failed=0

            for bucket in "${BUCKET_ARRAY[@]}"; do
                if ! verify_bucket_sync "$bucket" "$bucket"; then
                    ((failed++))
                fi
            done

            if [[ $failed -eq 0 ]]; then
                send_alert "SUCCESS" "All bucket verifications passed"
                exit 0
            else
                send_alert "FAILED" "${failed} bucket verification(s) failed"
                exit 1
            fi
            ;;

        *)
            error "Unknown operation: ${operation}"
            echo "Usage: $0 [backup|replicate|verify]"
            exit 1
            ;;
    esac
}

main "$@"
