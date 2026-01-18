#!/bin/bash
# 更新 .env.local 文件添加集成测试资源token
# 使用方式: bash scripts/update_test_tokens.sh

set -e

# 获取脚本所在目录的父目录（staging-simulation目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$STAGING_DIR/.env.local"

echo "🔧 更新集成测试资源token到 $ENV_FILE"

# 检查文件是否存在
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 错误: $ENV_FILE 文件不存在"
    echo "请先创建 .env.local 文件（可以从 env.local.template 复制）"
    exit 1
fi

# 备份原文件
cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ 已备份原文件"

# 定义要添加的配置
TEST_CONFIGS="
# ============================================================================
# 集成测试资源Token (已配置)
# 更新时间: $(date +"%Y-%m-%d %H:%M:%S")
# ============================================================================

# Bitable多维表格测试
TEST_BITABLE_APP_TOKEN=RZI2b0owwaQMN8suYevcbYPBnEe
TEST_BITABLE_TABLE_ID=tblfzrP1TqrIClDe
# TEST_WRITABLE_BITABLE_TOKEN=  # 可选，如果需要测试写操作

# Sheet电子表格测试
TEST_SHEET_TOKEN=HiwasEZJthNgDMttCeBckPTHnsc
TEST_SHEET_ID=a3fb01
# TEST_WRITABLE_SHEET_TOKEN=  # 可选，如果需要测试写操作

# 文档测试
TEST_DOC_TOKEN=QkvCdrrzIoOcXAxXbBXcGvZinsg
"

# 检查是否已经存在这些配置
if grep -q "TEST_BITABLE_APP_TOKEN=RZI2b0owwaQMN8suYevcbYPBnEe" "$ENV_FILE"; then
    echo "⚠️  检测到配置已存在，跳过添加"
    echo "如需更新，请手动编辑 $ENV_FILE"
else
    # 添加到文件末尾
    echo "$TEST_CONFIGS" >> "$ENV_FILE"
    echo "✅ 已添加集成测试资源token到 $ENV_FILE"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📋 已配置的测试资源:"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "✅ Bitable (多维表格):"
echo "   TEST_BITABLE_APP_TOKEN=RZI2b0owwaQMN8suYevcbYPBnEe"
echo "   TEST_BITABLE_TABLE_ID=tblfzrP1TqrIClDe"
echo ""
echo "✅ Sheet (电子表格):"
echo "   TEST_SHEET_TOKEN=HiwasEZJthNgDMttCeBckPTHnsc"
echo "   TEST_SHEET_ID=a3fb01"
echo ""
echo "✅ Doc (文档):"
echo "   TEST_DOC_TOKEN=QkvCdrrzIoOcXAxXbBXcGvZinsg"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 下一步:"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "1. 确保 LARK_APP_ID 和 LARK_APP_SECRET 已正确配置"
echo ""
echo "2. 设置环境变量:"
echo "   export \$(cat $ENV_FILE | grep -v '^#' | xargs)"
echo ""
echo "3. 运行集成测试:"
echo "   pytest tests/integration/test_bitable_e2e.py -v"
echo "   pytest tests/integration/test_sheet_e2e.py -v"
echo "   pytest tests/integration/test_clouddoc_e2e.py -v"
echo ""
echo "4. 或运行所有集成测试:"
echo "   pytest tests/integration/ -v"
echo ""
echo "════════════════════════════════════════════════════════════"
