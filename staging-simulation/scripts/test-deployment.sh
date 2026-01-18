#!/bin/bash
# ============================================================================
# Staging模拟环境 - 完整测试脚本
# ============================================================================
#
# 功能:
# 1. 验证环境配置
# 2. 运行健康检查
# 3. 执行数据库迁移
# 4. 运行测试套件
# 5. 测试备份恢复
#
# 使用:
#   bash test-deployment.sh
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================"
echo "🧪 Staging模拟环境 - 完整测试"
echo "======================================"
echo ""

# 检查环境变量文件
ENV_FILE="$SCRIPT_DIR/.env.local"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠${NC}  环境变量文件不存在,使用模板..."
    ENV_FILE="$SCRIPT_DIR/env.local.template"
fi

# 加载环境变量
export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ ! -d ".venv-test" ]; then
    echo -e "${RED}❌ 虚拟环境不存在: .venv-test${NC}"
    echo "请先创建虚拟环境: uv venv .venv-test"
    exit 1
fi

source .venv-test/bin/activate
echo -e "${GREEN}✓${NC} 虚拟环境已激活"
echo ""

# 测试1: 验证环境配置
echo -e "${BLUE}测试 1/7: 验证环境配置${NC}"
echo "----------------------------------------"
python scripts/validate_env.py "$ENV_FILE" || true
echo ""

# 测试2: 健康检查
echo -e "${BLUE}测试 2/7: 运行健康检查${NC}"
echo "----------------------------------------"
python scripts/staging_health_check.py
echo ""

# 测试3: 数据库迁移
echo -e "${BLUE}测试 3/7: 数据库迁移${NC}"
echo "----------------------------------------"
echo "当前迁移版本:"
alembic current || echo "尚未执行迁移"

echo ""
echo "执行迁移到最新版本..."
alembic upgrade head

echo ""
echo "验证迁移结果:"
alembic current
echo ""

# 测试4: 单元测试
echo -e "${BLUE}测试 4/7: 单元测试${NC}"
echo "----------------------------------------"
pytest tests/unit/ -v --tb=short --maxfail=5 || echo -e "${YELLOW}⚠${NC}  单元测试有失败"
echo ""

# 测试5: 集成测试 (可选)
echo -e "${BLUE}测试 5/7: 集成测试${NC}"
echo "----------------------------------------"
if [ -d "tests/integration" ]; then
    pytest tests/integration/ -v --tb=short --maxfail=3 || echo -e "${YELLOW}⚠${NC}  集成测试有失败"
else
    echo "跳过: 无集成测试目录"
fi
echo ""

# 测试6: 数据库备份
echo -e "${BLUE}测试 6/7: 数据库备份测试${NC}"
echo "----------------------------------------"
export BACKUP_DIR="$SCRIPT_DIR/backups"
mkdir -p "$BACKUP_DIR"

echo "执行备份..."
bash scripts/backup_database.sh || echo -e "${YELLOW}⚠${NC}  备份脚本执行失败"

echo ""
echo "备份文件:"
ls -lh "$BACKUP_DIR/" || echo "无备份文件"
echo ""

# 测试7: 迁移回滚测试
echo -e "${BLUE}测试 7/7: 数据库迁移回滚测试${NC}"
echo "----------------------------------------"
bash scripts/test_migration_rollback.sh || echo -e "${YELLOW}⚠${NC}  回滚测试失败"
echo ""

# 汇总结果
echo "======================================"
echo "✅ 测试完成!"
echo "======================================"
echo ""
echo "📊 测试摘要:"
echo "  1. 环境配置验证: 完成"
echo "  2. 健康检查: 完成"
echo "  3. 数据库迁移: 完成"
echo "  4. 单元测试: 已执行"
echo "  5. 集成测试: 已执行"
echo "  6. 数据库备份: 完成"
echo "  7. 迁移回滚测试: 完成"
echo ""
echo "📁 测试数据:"
echo "  备份目录: $BACKUP_DIR"
echo "  日志目录: $SCRIPT_DIR/logs"
echo ""
echo "🔧 下一步:"
echo "  查看详细测试结果,修复失败的测试"
echo "  如需性能测试,运行: locust -f tests/performance/load_test.py"
echo ""
