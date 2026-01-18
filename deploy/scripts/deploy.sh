#!/bin/bash
# ============================================================================
# Lark Service - 生产环境自动化部署脚本
# ============================================================================

set -e

PROD_CONF="/etc/lark-service/production.env"
PROJECT_ROOT="/opt/lark-service"
PYTHON_VERSION="3.12"

# 颜色输出
GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }

if [ ! -f "$PROD_CONF" ]; then
    echo "错误: 配置文件不存在: $PROD_CONF"
    exit 1
fi

cd "$PROJECT_ROOT"

# Ensure .env exists for docker-compose env_file while keeping production config in /etc
ln -sfn "$PROD_CONF" "$PROJECT_ROOT/.env"
# Fallback for filesystems that don't support symlinks
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROD_CONF" "$PROJECT_ROOT/.env"
fi

# 1. 启动 Docker 服务 (生产核心)
log_info "正在通过 Docker Compose 部署服务..."
docker compose --env-file "$PROD_CONF" up -d --build --remove-orphans

# 2. 执行数据库迁移
log_info "正在执行数据库迁移..."
docker compose --env-file "$PROD_CONF" run --rm lark-service \
  alembic -c /app/alembic.ini upgrade head

# 3. 同步宿主机虚拟环境 (用于直接调用 CLI，不干扰系统)
log_info "正在更新宿主机隔离虚拟环境 (uv)..."
# 使用 uv 在宿主机创建/更新虚拟环境
uv venv .venv --python $PYTHON_VERSION --quiet
# 在虚拟环境中安装当前项目
uv pip install -e . --index-url https://pypi.tuna.tsinghua.edu.cn/simple

log_info "✓ 部署完成！"
log_info "提示: 如需在宿主机调用 CLI，请执行: source .venv/bin/activate"
