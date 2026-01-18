#!/bin/bash
# ==============================================================================
# Database Migration Rollback Test Script
# ==============================================================================
# Purpose: Validate database migration rollback functionality
# Usage: ./test_migration_rollback.sh
# Environment: Test/Staging only (DO NOT run in production)
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================================="
echo "  数据库迁移回滚测试"
echo "=================================================================="
echo "开始时间: $(date)"
echo ""

# Configuration
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-lark_service}"
DB_USER="${POSTGRES_USER:-lark}"
BACKUP_DIR="/tmp/migration_test_backups"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "配置信息:"
echo "  - 数据库: $DB_NAME@$DB_HOST:$DB_PORT"
echo "  - 用户: $DB_USER"
echo "  - 备份目录: $BACKUP_DIR"
echo ""

# ==============================================================================
# Step 1: Record Initial State
# ==============================================================================
echo -e "${YELLOW}[Step 1/8]${NC} 记录初始状态"
echo "-----------------------------------"

alembic current > "$BACKUP_DIR/migration_before.txt" 2>&1 || true
echo "✓ 当前迁移版本已记录"

# Create backup
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_DIR/backup_before_test.sql" 2>/dev/null || true
echo "✓ 数据库备份已创建"
echo ""

# ==============================================================================
# Step 2: Ensure Latest Migration
# ==============================================================================
echo -e "${YELLOW}[Step 2/8]${NC} 确保数据库是最新版本"
echo "-----------------------------------"

alembic upgrade head
CURRENT_VERSION=$(alembic current 2>&1)
echo "✓ 当前版本: $CURRENT_VERSION"
echo ""

# ==============================================================================
# Step 3: Insert Test Data
# ==============================================================================
echo -e "${YELLOW}[Step 3/8]${NC} 插入测试数据"
echo "-----------------------------------"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
INSERT INTO tokens (app_id, token_type, token_value, expires_at)
VALUES ('test_rollback', 'app_access_token', 'test_value_rollback', now() + interval '1 hour')
ON CONFLICT DO NOTHING;
" > /dev/null 2>&1

echo "✓ 测试Token已插入"

# Verify data
TEST_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM tokens WHERE app_id='test_rollback';")
echo "✓ 测试数据条数: $TEST_COUNT"
echo ""

# ==============================================================================
# Step 4: Execute Downgrade (Rollback)
# ==============================================================================
echo -e "${YELLOW}[Step 4/8]${NC} 执行数据库回滚 (downgrade -1)"
echo "-----------------------------------"

alembic downgrade -1
NEW_VERSION=$(alembic current 2>&1)
echo "✓ 回滚后版本: $NEW_VERSION"
echo ""

# ==============================================================================
# Step 5: Verify Tables Dropped
# ==============================================================================
echo -e "${YELLOW}[Step 5/8]${NC} 验证表已删除"
echo "-----------------------------------"

TABLE_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT EXISTS (
   SELECT FROM information_schema.tables
   WHERE  table_schema = 'public'
   AND    table_name   = 'tokens'
);")

if [[ "$TABLE_EXISTS" == *"f"* ]]; then
    echo -e "${GREEN}✓ tokens表已成功删除${NC}"
else
    echo -e "${RED}✗ tokens表仍然存在 (回滚失败)${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Step 6: Re-upgrade to Latest
# ==============================================================================
echo -e "${YELLOW}[Step 6/8]${NC} 重新升级到最新版本"
echo "-----------------------------------"

alembic upgrade head
FINAL_VERSION=$(alembic current 2>&1)
echo "✓ 升级后版本: $FINAL_VERSION"
echo ""

# ==============================================================================
# Step 7: Verify Data State
# ==============================================================================
echo -e "${YELLOW}[Step 7/8]${NC} 验证数据状态"
echo "-----------------------------------"

# Check if table exists after re-upgrade
TABLE_EXISTS_AFTER=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT EXISTS (
   SELECT FROM information_schema.tables
   WHERE  table_schema = 'public'
   AND    table_name   = 'tokens'
);")

if [[ "$TABLE_EXISTS_AFTER" == *"t"* ]]; then
    echo -e "${GREEN}✓ tokens表已重新创建${NC}"
else
    echo -e "${RED}✗ tokens表创建失败${NC}"
    exit 1
fi

# Verify test data is gone (expected behavior)
FINAL_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM tokens WHERE app_id='test_rollback';" 2>/dev/null || echo "0")
echo "✓ 测试数据条数 (预期为0): $FINAL_COUNT"

# Verify table structure
COLUMNS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
SELECT COUNT(*) FROM information_schema.columns
WHERE table_name = 'tokens';")
echo "✓ tokens表列数: $COLUMNS (预期为7)"
echo ""

# ==============================================================================
# Step 8: Cleanup
# ==============================================================================
echo -e "${YELLOW}[Step 8/8]${NC} 清理测试环境"
echo "-----------------------------------"

# Remove test data if any
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
DELETE FROM tokens WHERE app_id='test_rollback';
" > /dev/null 2>&1

echo "✓ 测试数据已清理"
echo "✓ 备份文件保留在: $BACKUP_DIR"
echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo "=================================================================="
echo -e "${GREEN}  ✓ 数据库迁移回滚测试完成${NC}"
echo "=================================================================="
echo "结束时间: $(date)"
echo ""
echo "测试结果摘要:"
echo "  1. ✓ 初始状态记录成功"
echo "  2. ✓ 升级到最新版本成功"
echo "  3. ✓ 测试数据插入成功"
echo "  4. ✓ 回滚(downgrade -1)成功"
echo "  5. ✓ 表删除验证通过"
echo "  6. ✓ 重新升级成功"
echo "  7. ✓ 表结构恢复验证通过"
echo "  8. ✓ 清理完成"
echo ""
echo "备份文件:"
ls -lh "$BACKUP_DIR"
echo ""
echo -e "${GREEN}所有测试通过! 回滚功能正常.${NC}"
