#!/bin/bash
# ==============================================================================
# PostgreSQL Database Restore Script
# ==============================================================================
# Purpose: Restore Lark Service PostgreSQL database from backup
# Usage: ./restore_database.sh <backup_file>
# Example: ./restore_database.sh /backups/postgres/lark_service_full_20260118_020000.sql.gz
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-lark_service}"
DB_USER="${POSTGRES_USER:-lark_user}"
LOG_FILE="/tmp/restore_$(date +%Y%m%d_%H%M%S).log"

# Functions
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# ==============================================================================
# Validate Input
# ==============================================================================
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Examples:"
    echo "  $0 /backups/postgres/lark_service_full_20260118_020000.sql.gz"
    echo "  $0 /backups/postgres/lark_service_custom_20260118_020000.dump"
    echo "  $0 /backups/postgres/lark_service_latest.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

log "=================================================================="
log "PostgreSQL Database Restore"
log "=================================================================="
log "Backup file: $BACKUP_FILE"
log "Database: $DB_NAME@$DB_HOST:$DB_PORT"
log "Log file: $LOG_FILE"
log ""

# ==============================================================================
# Safety Confirmation
# ==============================================================================
echo -e "${YELLOW}WARNING: This will DROP and recreate the database!${NC}"
echo "Database: $DB_NAME"
echo "Backup: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log "Restore cancelled by user"
    exit 0
fi

log "User confirmed restore operation"

# ==============================================================================
# Pre-Restore Backup (Safety)
# ==============================================================================
log "[1/6] Creating pre-restore backup..."

PRE_RESTORE_BACKUP="/tmp/pre_restore_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null | gzip > "$PRE_RESTORE_BACKUP"; then
    PRE_SIZE=$(du -h "$PRE_RESTORE_BACKUP" | cut -f1)
    log "✓ Pre-restore backup created: $PRE_RESTORE_BACKUP"
    log "  Size: $PRE_SIZE"
else
    log "⚠ Pre-restore backup failed (database may not exist)"
fi

# ==============================================================================
# Stop Application (if running)
# ==============================================================================
log "[2/6] Checking application status..."

if docker compose ps app 2>/dev/null | grep -q "Up"; then
    log "⚠ Application is running"
    read -p "Stop application before restore? (yes/no): " STOP_APP

    if [ "$STOP_APP" == "yes" ]; then
        docker compose stop app
        log "✓ Application stopped"
        APP_WAS_RUNNING=true
    else
        log "⚠ Continuing with application running (not recommended)"
        APP_WAS_RUNNING=false
    fi
else
    log "✓ Application is not running"
    APP_WAS_RUNNING=false
fi

# ==============================================================================
# Terminate Active Connections
# ==============================================================================
log "[3/6] Terminating active database connections..."

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
" > /dev/null 2>&1 || true

log "✓ Active connections terminated"

# ==============================================================================
# Drop and Recreate Database
# ==============================================================================
log "[4/6] Recreating database..."

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" <<EOF 2>&1 | tee -a "$LOG_FILE"
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

log "✓ Database recreated"

# ==============================================================================
# Restore from Backup
# ==============================================================================
log "[5/6] Restoring from backup..."

# Detect backup format
if [[ "$BACKUP_FILE" == *.sql.gz ]]; then
    log "Detected format: Compressed SQL dump"

    if gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>&1 | tee -a "$LOG_FILE"; then
        log "✓ SQL dump restored successfully"
    else
        error "SQL dump restore failed"
    fi

elif [[ "$BACKUP_FILE" == *.sql ]]; then
    log "Detected format: SQL dump"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        log "✓ SQL dump restored successfully"
    else
        error "SQL dump restore failed"
    fi

elif [[ "$BACKUP_FILE" == *.dump ]]; then
    log "Detected format: Custom format dump"

    if pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-owner --no-acl \
        "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        log "✓ Custom dump restored successfully"
    else
        error "Custom dump restore failed"
    fi

else
    error "Unknown backup format: $BACKUP_FILE"
fi

# ==============================================================================
# Verify Restore
# ==============================================================================
log "[6/6] Verifying restore..."

# Check Alembic version
ALEMBIC_VERSION=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "N/A")
log "  Alembic version: $ALEMBIC_VERSION"

# Check table counts
TOKENS_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM tokens;" 2>/dev/null || echo "0")
log "  Tokens: $TOKENS_COUNT"

USERS_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM user_cache;" 2>/dev/null || echo "0")
log "  User cache: $USERS_COUNT"

# List all tables
log "  Tables:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" 2>&1 | tee -a "$LOG_FILE"

log "✓ Restore verification completed"

# ==============================================================================
# Restart Application (if needed)
# ==============================================================================
if [ "$APP_WAS_RUNNING" = true ]; then
    log "Restarting application..."

    if docker compose start app; then
        log "✓ Application restarted"

        # Wait for health check
        log "Waiting for health check..."
        sleep 5

        if curl -f http://localhost:8000/health/ready 2>/dev/null; then
            log "${GREEN}✓ Health check passed${NC}"
        else
            log "${YELLOW}⚠ Health check failed - please verify manually${NC}"
        fi
    else
        log "${YELLOW}⚠ Application restart failed - please start manually${NC}"
    fi
fi

# ==============================================================================
# Summary
# ==============================================================================
log ""
log "=================================================================="
log "${GREEN}Database restore completed successfully${NC}"
log "=================================================================="
log "Restore summary:"
log "  - Backup file: $BACKUP_FILE"
log "  - Database: $DB_NAME"
log "  - Alembic version: $ALEMBIC_VERSION"
log "  - Records restored: $TOKENS_COUNT tokens, $USERS_COUNT users"
log "  - Pre-restore backup: $PRE_RESTORE_BACKUP"
log "  - Log file: $LOG_FILE"
log ""
log "Next steps:"
log "  1. Verify application functionality"
log "  2. Check logs: docker compose logs -f app"
log "  3. Test critical workflows"
log "=================================================================="

exit 0
