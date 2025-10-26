#!/bin/bash
#
# Backup Verification and Testing Script
# Tests backup integrity and performs automated restoration tests
#
# Usage: ./verify-backups.sh [--all|--latest|--backup-file <file>]
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/postgres}"
MINIO_BACKUP_ROOT="${MINIO_BACKUP_ROOT:-/var/backups/minio}"
LOG_DIR="${BACKUP_ROOT}/logs"
LOG_FILE="${LOG_DIR}/verify-$(date +%Y%m%d-%H%M%S).log"

# Test database
TEST_DB_HOST="${TEST_DB_HOST:-localhost}"
TEST_DB_PORT="${TEST_DB_PORT:-5432}"
TEST_DB_USER="${TEST_DB_USER:-postgres}"
TEST_DB_NAME="backup_verification_test"

# Alerting
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_ALERTS="${EMAIL_ALERTS:-ops@corporate-intel.local}"

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
            --data "{\"text\":\"[Backup Verification ${status}] ${message}\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
}

verify_backup_file_integrity() {
    local backup_file="$1"

    log "Verifying file integrity: $(basename $backup_file)..."

    # Check file exists and is readable
    if [[ ! -f "$backup_file" ]] || [[ ! -r "$backup_file" ]]; then
        error "Backup file not accessible: ${backup_file}"
        return 1
    fi

    # Check file is not empty
    if [[ ! -s "$backup_file" ]]; then
        error "Backup file is empty: ${backup_file}"
        return 1
    fi

    # Verify checksum if metadata exists
    if [[ -f "${backup_file}.metadata.json" ]]; then
        local stored_checksum=$(jq -r '.checksum_sha256' "${backup_file}.metadata.json" 2>/dev/null || echo "")

        if [[ -n "$stored_checksum" ]]; then
            local actual_checksum=$(sha256sum "$backup_file" | cut -d' ' -f1)

            if [[ "$stored_checksum" == "$actual_checksum" ]]; then
                log "✓ Checksum verification passed"
            else
                error "✗ Checksum mismatch"
                error "  Expected: ${stored_checksum}"
                error "  Actual:   ${actual_checksum}"
                return 1
            fi
        fi
    fi

    # Verify file format based on extension
    if [[ "$backup_file" == *.gz ]]; then
        if gzip -t "$backup_file" 2>/dev/null; then
            log "✓ Gzip format valid"
        else
            error "✗ Gzip format invalid"
            return 1
        fi
    fi

    if [[ "$backup_file" == *.gpg ]]; then
        if gpg --list-packets "$backup_file" &>/dev/null; then
            log "✓ GPG encryption valid"
        else
            error "✗ GPG encryption invalid"
            return 1
        fi
    fi

    log "✓ File integrity verification passed"
    return 0
}

test_backup_restoration() {
    local backup_file="$1"

    log "Testing backup restoration: $(basename $backup_file)..."

    # Use the restore script with --verify-only flag
    if bash "$(dirname $0)/restore-database.sh" "$backup_file" --verify-only; then
        log "✓ Restoration test passed"
        return 0
    else
        error "✗ Restoration test failed"
        return 1
    fi
}

verify_backup_metadata() {
    local backup_file="$1"
    local metadata_file="${backup_file}.metadata.json"

    log "Verifying backup metadata..."

    if [[ ! -f "$metadata_file" ]]; then
        log "⚠ No metadata file found"
        return 0
    fi

    # Validate JSON format
    if ! jq empty "$metadata_file" 2>/dev/null; then
        error "✗ Invalid JSON in metadata file"
        return 1
    fi

    # Check required fields
    local required_fields=("timestamp" "database" "backup_file" "file_size" "checksum_sha256")
    for field in "${required_fields[@]}"; do
        if ! jq -e ".${field}" "$metadata_file" &>/dev/null; then
            error "✗ Missing required field in metadata: ${field}"
            return 1
        fi
    done

    # Verify timestamp is recent (not older than 31 days for daily backups)
    local backup_timestamp=$(jq -r '.timestamp' "$metadata_file")
    local backup_age=$(( ($(date +%s) - $(date -d "$backup_timestamp" +%s)) / 86400 ))

    if [[ $(basename $(dirname $backup_file)) == "daily" ]] && [[ $backup_age -gt 31 ]]; then
        log "⚠ Backup is ${backup_age} days old"
    fi

    log "✓ Metadata verification passed"
    return 0
}

check_backup_age() {
    local backup_dir="$1"
    local max_age_hours="${2:-24}"

    log "Checking for recent backups in: ${backup_dir}..."

    local latest_backup=$(find "$backup_dir" -name "*.sql.*" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

    if [[ -z "$latest_backup" ]]; then
        error "✗ No backups found in ${backup_dir}"
        return 1
    fi

    local backup_timestamp=$(stat -c %Y "$latest_backup")
    local current_timestamp=$(date +%s)
    local age_hours=$(( (current_timestamp - backup_timestamp) / 3600 ))

    log "Latest backup: $(basename $latest_backup)"
    log "Age: ${age_hours} hours"

    if [[ $age_hours -gt $max_age_hours ]]; then
        error "✗ Latest backup is older than ${max_age_hours} hours"
        return 1
    fi

    log "✓ Backup age check passed"
    return 0
}

verify_remote_backups() {
    log "Verifying remote backup storage..."

    local s3_bucket="${S3_BUCKET:-corporate-intel-backups}"
    local s3_endpoint="${S3_ENDPOINT:-https://s3.amazonaws.com}"

    if ! command -v aws &>/dev/null; then
        log "⚠ AWS CLI not found, skipping remote verification"
        return 0
    fi

    # Check daily backups in S3
    local remote_count=$(aws s3 ls "s3://${s3_bucket}/daily/" --endpoint-url "$s3_endpoint" 2>/dev/null | wc -l || echo "0")

    if [[ $remote_count -gt 0 ]]; then
        log "✓ Found ${remote_count} remote backups"
        return 0
    else
        error "✗ No remote backups found"
        return 1
    fi
}

verify_minio_backups() {
    log "Verifying MinIO backups..."

    local minio_snapshots="${MINIO_BACKUP_ROOT}/snapshots"

    if [[ ! -d "$minio_snapshots" ]]; then
        log "⚠ MinIO backup directory not found"
        return 0
    fi

    local snapshot_count=$(find "$minio_snapshots" -name "*.tar.gz" -type f -mtime -7 | wc -l)

    if [[ $snapshot_count -gt 0 ]]; then
        log "✓ Found ${snapshot_count} recent MinIO snapshots"
        return 0
    else
        error "✗ No recent MinIO snapshots found"
        return 1
    fi
}

generate_verification_report() {
    local total_tests="$1"
    local passed_tests="$2"
    local failed_tests="$3"

    local report_file="${BACKUP_ROOT}/verification-report-$(date +%Y%m%d).txt"

    cat > "$report_file" <<EOF
Backup Verification Report - $(date)
================================================================

Test Summary:
  Total Tests:  ${total_tests}
  Passed:       ${passed_tests}
  Failed:       ${failed_tests}
  Success Rate: $(awk "BEGIN {printf \"%.1f\", ($passed_tests/$total_tests)*100}")%

Verification Details:
$(tail -100 "$LOG_FILE")

Backup Statistics:
  Daily Backups:   $(find "${BACKUP_ROOT}/daily" -name "*.sql.*" -type f | wc -l)
  Weekly Backups:  $(find "${BACKUP_ROOT}/weekly" -name "*.sql.*" -type f | wc -l)
  Monthly Backups: $(find "${BACKUP_ROOT}/monthly" -name "*.sql.*" -type f | wc -l)

Disk Usage:
  PostgreSQL Backups: $(du -sh "$BACKUP_ROOT" | cut -f1)
  MinIO Backups:      $(du -sh "$MINIO_BACKUP_ROOT" 2>/dev/null | cut -f1 || echo "N/A")

EOF

    log "Verification report generated: ${report_file}"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    local mode="${1:---latest}"

    log "==================================================================="
    log "Backup Verification Script Starting"
    log "Mode: ${mode}"
    log "==================================================================="

    mkdir -p "$LOG_DIR"

    local total_tests=0
    local passed_tests=0
    local failed_tests=0

    case "$mode" in
        --all)
            log "Verifying all backups..."

            # Find all backups from last 7 days
            local backup_files=$(find "${BACKUP_ROOT}/daily" "${BACKUP_ROOT}/weekly" "${BACKUP_ROOT}/monthly" \
                -name "*.sql.*" -type f -mtime -7 2>/dev/null || true)

            for backup_file in $backup_files; do
                ((total_tests++))
                if verify_backup_file_integrity "$backup_file" && \
                   verify_backup_metadata "$backup_file"; then
                    ((passed_tests++))
                else
                    ((failed_tests++))
                fi
            done
            ;;

        --latest)
            log "Verifying latest backups..."

            # Check backup age
            ((total_tests++))
            if check_backup_age "${BACKUP_ROOT}/daily" 24; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi

            # Verify latest daily backup
            local latest_backup=$(find "${BACKUP_ROOT}/daily" -name "*.sql.*" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)

            if [[ -n "$latest_backup" ]]; then
                ((total_tests++))
                if verify_backup_file_integrity "$latest_backup" && \
                   verify_backup_metadata "$latest_backup"; then
                    ((passed_tests++))
                else
                    ((failed_tests++))
                fi

                # Test restoration
                ((total_tests++))
                if test_backup_restoration "$latest_backup"; then
                    ((passed_tests++))
                else
                    ((failed_tests++))
                fi
            fi

            # Verify remote backups
            ((total_tests++))
            if verify_remote_backups; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi

            # Verify MinIO backups
            ((total_tests++))
            if verify_minio_backups; then
                ((passed_tests++))
            else
                ((failed_tests++))
            fi
            ;;

        --backup-file)
            local backup_file="$2"

            if [[ -z "$backup_file" ]]; then
                error "No backup file specified"
                exit 1
            fi

            ((total_tests += 3))

            verify_backup_file_integrity "$backup_file" && ((passed_tests++)) || ((failed_tests++))
            verify_backup_metadata "$backup_file" && ((passed_tests++)) || ((failed_tests++))
            test_backup_restoration "$backup_file" && ((passed_tests++)) || ((failed_tests++))
            ;;

        *)
            error "Unknown mode: ${mode}"
            echo "Usage: $0 [--all|--latest|--backup-file <file>]"
            exit 1
            ;;
    esac

    # Generate report
    generate_verification_report "$total_tests" "$passed_tests" "$failed_tests"

    # Summary
    log "==================================================================="
    log "Verification Summary:"
    log "  Total Tests:  ${total_tests}"
    log "  Passed:       ${passed_tests}"
    log "  Failed:       ${failed_tests}"
    log "==================================================================="

    if [[ $failed_tests -eq 0 ]]; then
        send_alert "SUCCESS" "All backup verifications passed (${total_tests}/${total_tests})"
        exit 0
    else
        send_alert "FAILED" "Backup verification failed (${passed_tests}/${total_tests} passed)"
        exit 1
    fi
}

main "$@"
