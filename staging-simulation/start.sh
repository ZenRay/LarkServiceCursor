#!/bin/bash
# ============================================================================
# Staging模拟环境 - 快速启动脚本
# ============================================================================
#
# 功能:
# 1. 启动Docker服务
# 2. 等待服务就绪
# 3. 初始化数据库
# 4. 运行健康检查
#
# 使用:
#   bash start.sh
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "🚀 Staging模拟环境启动"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 步骤1: 检查Docker
echo "步骤 1/6: 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装${NC}"
    exit 1
fi

# 检查 docker compose 命令 (优先使用新版本)
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    echo -e "${GREEN}✓${NC} 使用 Docker Compose v2 (docker compose)"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo -e "${GREEN}✓${NC} 使用 Docker Compose v1 (docker-compose)"
else
    echo -e "${RED}❌ Docker Compose未安装${NC}"
    echo "请安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker环境正常"
echo ""

# 步骤2: 启动Docker服务
echo "步骤 2/6: 启动Docker服务..."
cd "$SCRIPT_DIR"

$DOCKER_COMPOSE up -d
echo -e "${GREEN}✓${NC} Docker服务已启动"
echo ""

# 步骤3: 等待服务就绪
echo "步骤 3/6: 等待服务就绪..."
echo "  等待PostgreSQL..."
for i in {1..30}; do
    if $DOCKER_COMPOSE exec -T postgres pg_isready -U lark_staging -d lark_service_staging &> /dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ PostgreSQL启动超时${NC}"
        $DOCKER_COMPOSE logs postgres
        exit 1
    fi
    sleep 2
done

echo "  等待RabbitMQ..."
for i in {1..30}; do
    if curl -s http://localhost:15672 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} RabbitMQ已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ RabbitMQ启动超时${NC}"
        $DOCKER_COMPOSE logs rabbitmq
        exit 1
    fi
    sleep 2
done

echo ""

# 步骤4: 验证pgcrypto扩展
echo "步骤 4/6: 验证数据库配置..."
PGCRYPTO_CHECK=$($DOCKER_COMPOSE exec -T postgres psql -U lark_staging -d lark_service_staging -tAc "SELECT COUNT(*) FROM pg_extension WHERE extname='pgcrypto';")
if [ "$PGCRYPTO_CHECK" -eq "1" ]; then
    echo -e "${GREEN}✓${NC} pgcrypto扩展已启用"
else
    echo -e "${YELLOW}⚠${NC}  pgcrypto扩展未启用,正在安装..."
    $DOCKER_COMPOSE exec -T postgres psql -U lark_staging -d lark_service_staging -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
    echo -e "${GREEN}✓${NC} pgcrypto扩展已安装"
fi
echo ""

# 步骤5: 创建备份目录
echo "步骤 5/6: 创建备份目录..."
mkdir -p "$SCRIPT_DIR/backups"
echo -e "${GREEN}✓${NC} 备份目录已创建: $SCRIPT_DIR/backups"
echo ""

# 步骤6: 显示服务信息
echo "步骤 6/6: 服务信息"
echo "======================================"
$DOCKER_COMPOSE ps
echo "======================================"
echo ""

# 显示连接信息
echo "📊 服务连接信息:"
echo ""
echo "PostgreSQL:"
echo "  Host: localhost:5432"
echo "  Database: lark_service_staging"
echo "  User: lark_staging"
echo "  Password: staging_password_local_only"
echo ""
echo "RabbitMQ:"
echo "  AMQP: localhost:5672"
echo "  Management: http://localhost:15672"
echo "  User: lark_staging"
echo "  Password: staging_rabbitmq_local_only"
echo ""
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000 (admin/admin_local_only)"
echo ""
echo "======================================"
echo "✅ Staging模拟环境启动完成!"
echo "======================================"
echo ""
echo "🔧 下一步操作:"
echo ""
echo "1. 配置环境变量:"
echo "   cp env.local.template .env.local"
echo "   vim .env.local  # 根据需要修改"
echo ""
echo "2. 运行数据库迁移:"
echo "   cd $PROJECT_ROOT"
echo "   source .venv-test/bin/activate"
echo "   export \$(cat staging-simulation/.env.local | grep -v '^#' | xargs)"
echo "   alembic upgrade head"
echo ""
echo "3. 运行健康检查:"
echo "   python scripts/staging_health_check.py"
echo ""
echo "4. 运行测试:"
echo "   pytest tests/unit/ -v"
echo ""
echo "5. 停止环境:"
echo "   cd $SCRIPT_DIR"
echo "   $DOCKER_COMPOSE down"
echo ""
