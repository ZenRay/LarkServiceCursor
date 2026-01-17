#!/bin/bash
# ============================================================================
# Docker环境数据库恢复脚本
# ============================================================================
#
# 功能: 从备份文件恢复PostgreSQL数据库
# 用法: bash restore_docker.sh <backup_file>
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker容器名称
CONTAINER_NAME="lark-staging-postgres"

# 数据库配置
DB_NAME="lark_service_staging"
DB_USER="lark_staging"

# 检查参数
if [ $# -eq 0 ]; then
    echo "================================================================"
    echo -e "${RED}❌ 错误: 未提供备份文件${NC}"
    echo "================================================================"
    echo "用法: bash $0 <backup_file>"
    echo ""
    echo "可用的备份文件:"
    ls -lh "$SCRIPT_DIR/backups/" 2>/dev/null || echo "  (暂无备份文件)"
    exit 1
fi

BACKUP_FILE="$1"

echo "================================================================"
echo "🔄 Docker环境PostgreSQL数据库恢复"
echo "================================================================"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "容器: $CONTAINER_NAME"
echo "数据库: $DB_NAME"
echo "备份文件: $BACKUP_FILE"
echo ""

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ 备份文件不存在: $BACKUP_FILE${NC}"
    exit 1
fi

# 检查Docker容器是否运行
echo "[1/5] 检查Docker容器状态..."
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ Docker容器 $CONTAINER_NAME 未运行${NC}"
    echo "请先启动Docker容器: cd $SCRIPT_DIR && docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✓${NC} 容器运行正常"
echo ""

# 确认恢复操作
echo -e "${YELLOW}⚠️  警告: 此操作将删除当前数据库的所有数据!${NC}"
echo -en "确认继续? (yes/no): "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "取消恢复操作"
    exit 0
fi
echo ""

# 创建当前数据库的备份
echo "[2/5] 创建当前数据库的安全备份..."
SAFETY_BACKUP="$SCRIPT_DIR/backups/safety_backup_$(date +%Y%m%d_%H%M%S).sql"
if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" > "$SAFETY_BACKUP"; then
    echo -e "${GREEN}✓${NC} 安全备份已创建: $SAFETY_BACKUP"
    gzip "$SAFETY_BACKUP" && echo "  已压缩"
else
    echo -e "${YELLOW}⚠${NC}  安全备份失败,但继续恢复"
fi
echo ""

# 删除并重建数据库
echo "[3/5] 重建数据库..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;" postgres
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" postgres
echo -e "${GREEN}✓${NC} 数据库已重建"
echo ""

# 恢复数据
echo "[4/5] 恢复数据..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "  解压并恢复压缩备份..."
    if gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME" > /dev/null; then
        echo -e "${GREEN}✓${NC} 数据恢复成功"
    else
        echo -e "${RED}❌ 数据恢复失败${NC}"
        exit 1
    fi
else
    echo "  恢复SQL备份..."
    if cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME" > /dev/null; then
        echo -e "${GREEN}✓${NC} 数据恢复成功"
    else
        echo -e "${RED}❌ 数据恢复失败${NC}"
        exit 1
    fi
fi
echo ""

# 验证恢复
echo "[5/5] 验证恢复结果..."

# 检查表是否存在
TABLE_COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "  表数量: $TABLE_COUNT"

# 检查pgcrypto扩展
PGCRYPTO=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME" -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname='pgcrypto';")
if [ "$PGCRYPTO" -gt 0 ]; then
    echo -e "  pgcrypto扩展: ${GREEN}✓${NC} 已启用"
else
    echo -e "  pgcrypto扩展: ${YELLOW}⚠${NC}  未启用,正在启用..."
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
fi

echo ""
echo "================================================================"
echo -e "${GREEN}✅ 数据库恢复成功完成!${NC}"
echo "================================================================"
echo "数据库: $DB_NAME"
echo "表数量: $TABLE_COUNT"
echo ""
echo "验证命令:"
echo "  docker exec $CONTAINER_NAME psql -U $DB_USER $DB_NAME -c '\\dt'"
echo ""
