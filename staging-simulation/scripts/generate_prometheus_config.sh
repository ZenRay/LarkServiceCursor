#!/bin/bash
# Prometheus配置生成脚本
# 从模板生成实际配置文件，支持环境变量替换

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/prometheus.yml.template"
OUTPUT_FILE="$SCRIPT_DIR/prometheus.yml"

echo "════════════════════════════════════════════════════════════"
echo "🔧 生成Prometheus配置"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "模板文件: $TEMPLATE_FILE"
echo "输出文件: $OUTPUT_FILE"
echo ""

# 检查模板文件
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ 模板文件不存在: $TEMPLATE_FILE"
    exit 1
fi

# 检查envsubst命令
if ! command -v envsubst &> /dev/null; then
    echo "❌ envsubst命令未找到，请安装: sudo apt-get install gettext-base"
    exit 1
fi

# 设置默认值（如果环境变量未设置）
export PROMETHEUS_SCRAPE_INTERVAL=${PROMETHEUS_SCRAPE_INTERVAL:-15s}
export PROMETHEUS_EVALUATION_INTERVAL=${PROMETHEUS_EVALUATION_INTERVAL:-15s}
export ENVIRONMENT=${ENVIRONMENT:-staging-local}
export LARK_SERVICE_METRICS_HOST=${LARK_SERVICE_METRICS_HOST:-172.17.0.1}
export LARK_SERVICE_METRICS_PORT=${LARK_SERVICE_METRICS_PORT:-9091}
export LARK_SERVICE_SCRAPE_INTERVAL=${LARK_SERVICE_SCRAPE_INTERVAL:-10s}
export RABBITMQ_HOST=${RABBITMQ_HOST:-rabbitmq}
export RABBITMQ_METRICS_PORT=${RABBITMQ_METRICS_PORT:-15692}

echo "当前配置:"
echo "  PROMETHEUS_SCRAPE_INTERVAL=$PROMETHEUS_SCRAPE_INTERVAL"
echo "  LARK_SERVICE_METRICS_HOST=$LARK_SERVICE_METRICS_HOST"
echo "  LARK_SERVICE_METRICS_PORT=$LARK_SERVICE_METRICS_PORT"
echo "  ENVIRONMENT=$ENVIRONMENT"
echo ""

# 生成配置文件
envsubst < "$TEMPLATE_FILE" > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 配置文件生成成功: $OUTPUT_FILE"
    echo ""
    echo "预览前10行:"
    head -n 10 "$OUTPUT_FILE"
    echo "..."
else
    echo "❌ 配置文件生成失败"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "下一步: docker compose restart prometheus"
echo "════════════════════════════════════════════════════════════"
