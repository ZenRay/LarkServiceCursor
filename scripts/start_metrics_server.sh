#!/bin/bash
# Metrics服务器启动脚本
# 用于在staging环境中独立运行metrics暴露服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "════════════════════════════════════════════════════════════"
echo "🚀 启动Lark Service Metrics服务器"
echo "════════════════════════════════════════════════════════════"
echo ""

# 检查Python环境
if [ -d "$PROJECT_ROOT/.venv-test" ]; then
    source "$PROJECT_ROOT/.venv-test/bin/activate"
    echo "✅ 使用虚拟环境: .venv-test"
else
    echo "⚠️  未找到虚拟环境，使用系统Python"
fi

# 加载环境变量（如果存在）
if [ -f "$PROJECT_ROOT/staging-simulation/.env.local" ]; then
    export $(cat "$PROJECT_ROOT/staging-simulation/.env.local" | grep -v '^#' | grep -v '^$' | xargs)
    echo "✅ 已加载环境变量"
fi

# 设置默认值
export METRICS_PORT=${METRICS_PORT:-9091}
export METRICS_HOST=${METRICS_HOST:-0.0.0.0}

echo ""
echo "配置信息:"
echo "  端口: $METRICS_PORT"
echo "  主机: $METRICS_HOST"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

# 运行metrics服务器
cd "$PROJECT_ROOT"
python -m lark_service.monitoring.server
