#!/bin/bash
# PostgreSQL 初始化脚本
# 自动启用 pgcrypto 扩展

set -e

echo "======================================"
echo "Initializing Lark Service Database"
echo "======================================"

# 切换到目标数据库
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 启用 pgcrypto 扩展 (用于加密)
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    -- 验证扩展
    SELECT extname, extversion FROM pg_extension WHERE extname = 'pgcrypto';

    -- 显示数据库信息
    SELECT current_database(), version();
EOSQL

echo "======================================"
echo "Database initialization completed!"
echo "======================================"
