#!/bin/bash
# ============================================================================
# Docker环境数据库备份脚本
# ============================================================================
#
# 功能: 使用Docker容器内的pg_dump进行PostgreSQL备份
# 用法: bash backup_docker.sh
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Docker容器名称
CONTAINER_NAME="lark-staging-postgres"

# 数据库配置
DB_NAME="lark_service_staging"
DB_USER="lark_staging"

# 备份文件名
BACKUP_FILE="$BACKUP_DIR/lark_service_full_${TIMESTAMP}.sql"

echo "================================================================"
echo "🔄 Docker环境PostgreSQL备份"
echo "================================================================"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "容器: $CONTAINER_NAME"
echo "数据库: $DB_NAME"
echo "备份目录: $BACKUP_DIR"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 检查Docker容器是否运行
echo "[1/4] 检查Docker容器状态..."
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ Docker容器 $CONTAINER_NAME 未运行${NC}"
    echo "请先启动Docker容器: cd $SCRIPT_DIR && docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✓${NC} 容器运行正常"
echo ""

# 执行全量备份
echo "[2/4] 执行全量SQL备份..."
if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"; then
    echo -e "${GREEN}✓${NC} 备份完成: $BACKUP_FILE"

    # 显示备份文件大小
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "  文件大小: $BACKUP_SIZE"
else
    echo -e "${RED}❌ 备份失败${NC}"
    exit 1
fi
echo ""

# 压缩备份文件
echo "[3/4] 压缩备份文件..."
if gzip "$BACKUP_FILE"; then
    COMPRESSED_FILE="${BACKUP_FILE}.gz"
    echo -e "${GREEN}✓${NC} 压缩完成: $COMPRESSED_FILE"

    COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    echo "  压缩后大小: $COMPRESSED_SIZE"
else
    echo -e "${YELLOW}⚠${NC}  压缩失败,保留原文件"
    COMPRESSED_FILE="$BACKUP_FILE"
fi
echo ""

# 验证备份
echo "[4/4] 验证备份文件..."
if [ -f "$COMPRESSED_FILE" ]; then
    echo -e "${GREEN}✓${NC} 备份文件存在"

    # 检查文件大小
    FILE_SIZE=$(stat -f%z "$COMPRESSED_FILE" 2>/dev/null || stat -c%s "$COMPRESSED_FILE" 2>/dev/null)
    if [ "$FILE_SIZE" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} 备份文件非空 ($FILE_SIZE bytes)"
    else
        echo -e "${RED}❌ 备份文件为空${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ 备份文件不存在${NC}"
    exit 1
fi
echo ""

# 清理旧备份 (保留最近7天)
echo "清理旧备份文件 (保留7天)..."
find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "*.sql" -type f -mtime +7 -delete 2>/dev/null || true

OLD_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" -o -name "*.sql" | wc -l)
echo "当前备份文件数: $OLD_COUNT"
echo ""

echo "================================================================"
echo -e "${GREEN}✅ 备份成功完成!${NC}"
echo "================================================================"
echo "备份文件: $COMPRESSED_FILE"
echo ""
echo "恢复命令:"
echo "  gunzip -c $COMPRESSED_FILE | docker exec -i $CONTAINER_NAME psql -U $DB_USER $DB_NAME"
echo ""
