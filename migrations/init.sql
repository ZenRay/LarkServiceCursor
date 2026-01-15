-- Lark Service PostgreSQL 初始化脚本
-- 用途: 启用必要的扩展和创建初始结构

-- 启用 pgcrypto 扩展 (用于加密功能)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 启用 uuid-ossp 扩展 (用于 UUID 生成)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建 schema (可选,用于组织表)
-- CREATE SCHEMA IF NOT EXISTS lark_service;

-- 设置默认搜索路径
-- SET search_path TO lark_service, public;

-- 注释: 实际的表结构由 Alembic 迁移脚本创建
-- 这个脚本只负责启用必要的 PostgreSQL 扩展

-- 验证扩展已安装
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        RAISE EXCEPTION 'pgcrypto extension not installed';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN
        RAISE EXCEPTION 'uuid-ossp extension not installed';
    END IF;
    
    RAISE NOTICE 'PostgreSQL extensions initialized successfully';
END $$;
