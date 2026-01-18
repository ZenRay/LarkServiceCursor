#!/bin/bash
# ==============================================================================
# PostgreSQL Database Backup Script
# ==============================================================================
# Purpose: Automated backup of Lark Service PostgreSQL database
# Schedule: Daily at 2:00 AM (configured via cron)
# Retention: 30 days
# ==============================================================================

set -e  # Exit on error

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-lark_service}"
DB_USER="${POSTGRES_USER:-lark_user}"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_READABLE=$(date "+%Y-%m-%d %H:%M:%S")

# Backup filenames
FULL_BACKUP="$BACKUP_DIR/lark_service_full_$TIMESTAMP.sql"
CUSTOM_BACKUP="$BACKUP_DIR/lark_service_custom_$TIMESTAMP.dump"
LOG_FILE="$BACKUP_DIR/backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=================================================================="
log "Starting PostgreSQL backup"
log "=================================================================="
log "Database: $DB_NAME@$DB_HOST:$DB_PORT"
log "Backup directory: $BACKUP_DIR"
log ""

# ==============================================================================
# 1. Full SQL Dump (Plain text, human-readable)
# ==============================================================================
log "[1/5] Creating full SQL dump..."

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl \
    -f "$FULL_BACKUP" 2>&1 | tee -a "$LOG_FILE"; then

    # Compress the dump
    gzip "$FULL_BACKUP"
    FULL_BACKUP_GZ="$FULL_BACKUP.gz"

    FULL_SIZE=$(du -h "$FULL_BACKUP_GZ" | cut -f1)
    log "✓ Full SQL dump completed: $FULL_BACKUP_GZ"
    log "  Size: $FULL_SIZE"
else
    log "✗ Full SQL dump failed"
    exit 1
fi

# ==============================================================================
# 2. Custom Format Dump (Binary, faster restore)
# ==============================================================================
log "[2/5] Creating custom format dump..."

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=custom \
    --no-owner --no-acl \
    -f "$CUSTOM_BACKUP" 2>&1 | tee -a "$LOG_FILE"; then

    CUSTOM_SIZE=$(du -h "$CUSTOM_BACKUP" | cut -f1)
    log "✓ Custom format dump completed: $CUSTOM_BACKUP"
    log "  Size: $CUSTOM_SIZE"
else
    log "✗ Custom format dump failed"
    exit 1
fi

# ==============================================================================
# 3. Verify Backup Integrity
# ==============================================================================
log "[3/5] Verifying backup integrity..."

# Verify SQL dump
if gunzip -t "$FULL_BACKUP_GZ" 2>&1 | tee -a "$LOG_FILE"; then
    log "✓ SQL dump compression integrity verified"
else
    log "✗ SQL dump compression corrupted"
    exit 1
fi

# Verify custom dump
if pg_restore --list "$CUSTOM_BACKUP" > /dev/null 2>&1; then
    TABLE_COUNT=$(pg_restore --list "$CUSTOM_BACKUP" 2>/dev/null | grep -c "TABLE DATA" || echo "0")
    log "✓ Custom dump integrity verified"
    log "  Tables: $TABLE_COUNT"
else
    log "✗ Custom dump corrupted"
    exit 1
fi

# ==============================================================================
# 4. Generate Backup Metadata
# ==============================================================================
log "[4/5] Generating backup metadata..."

METADATA_FILE="$BACKUP_DIR/lark_service_metadata_$TIMESTAMP.txt"
cat > "$METADATA_FILE" << EOF
================================================================
Lark Service PostgreSQL Backup Metadata
================================================================
Backup Date: $DATE_READABLE
Database: $DB_NAME
Host: $DB_HOST:$DB_PORT
User: $DB_USER

Files:
  - Full SQL: $FULL_BACKUP_GZ ($FULL_SIZE)
  - Custom Format: $CUSTOM_BACKUP ($CUSTOM_SIZE)

Database Statistics:
$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
" 2>/dev/null)

Alembic Version:
$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "N/A")

Backup Script: $0
Exit Code: 0
================================================================
EOF

log "✓ Metadata generated: $METADATA_FILE"

# ==============================================================================
# 5. Cleanup Old Backups
# ==============================================================================
log "[5/5] Cleaning up old backups (retention: $RETENTION_DAYS days)..."

# Count backups before cleanup
BEFORE_COUNT=$(find "$BACKUP_DIR" -name "lark_service_*" -type f | wc -l)

# Remove backups older than retention period
find "$BACKUP_DIR" -name "lark_service_full_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "lark_service_custom_*.dump" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "lark_service_metadata_*.txt" -type f -mtime +$RETENTION_DAYS -delete

# Count backups after cleanup
AFTER_COUNT=$(find "$BACKUP_DIR" -name "lark_service_*" -type f | wc -l)
REMOVED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

log "✓ Cleanup completed"
log "  Removed: $REMOVED_COUNT old backup files"
log "  Remaining: $AFTER_COUNT backup files"

# ==============================================================================
# 6. Summary
# ==============================================================================
log ""
log "=================================================================="
log "Backup completed successfully"
log "=================================================================="
log "Backup files:"
log "  - SQL: $FULL_BACKUP_GZ"
log "  - Custom: $CUSTOM_BACKUP"
log "  - Metadata: $METADATA_FILE"
log ""
log "Next backup: $(date -d 'tomorrow 02:00' '+%Y-%m-%d %H:%M:%S')"
log "=================================================================="

# Create latest symlink for easy access
ln -sf "$FULL_BACKUP_GZ" "$BACKUP_DIR/lark_service_latest.sql.gz"
ln -sf "$CUSTOM_BACKUP" "$BACKUP_DIR/lark_service_latest.dump"

log "✓ Latest backup symlinks updated"

# Send notification (optional - implement based on your notification system)
# Example: curl -X POST https://your-webhook.com/notify -d "Lark Service backup completed: $FULL_SIZE"

exit 0
