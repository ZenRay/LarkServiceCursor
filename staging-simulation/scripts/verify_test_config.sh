#!/bin/bash
# 快速验证集成测试资源配置
# 使用方式: bash scripts/verify_test_config.sh

set -e

# 获取脚本所在目录的父目录（staging-simulation目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$STAGING_DIR/.env.local"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        🔍 验证集成测试配置                                    ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 加载环境变量
if [ -f "$ENV_FILE" ]; then
    echo "📄 加载配置文件: $ENV_FILE"
    export $(cat "$ENV_FILE" | grep -v '^#' | grep -v '^$' | xargs)
    echo ""
else
    echo "❌ 错误: $ENV_FILE 文件不存在"
    exit 1
fi

# 检查必需配置
echo "════════════════════════════════════════════════════════════════"
echo "✅ 基础配置检查"
echo "════════════════════════════════════════════════════════════════"

check_var() {
    local var_name=$1
    local var_value=${!var_name}
    if [ -z "$var_value" ]; then
        echo "❌ $var_name: 未配置"
        return 1
    elif [[ "$var_value" == *"example"* ]] || [[ "$var_value" == *"REPLACE"* ]] || [[ "$var_value" == *"change_me"* ]]; then
        echo "⚠️  $var_name: 使用示例值，需要替换"
        return 1
    else
        # 脱敏显示
        local masked_value="${var_value:0:10}...${var_value: -4}"
        echo "✅ $var_name: $masked_value"
        return 0
    fi
}

ERRORS=0

# 检查应用凭证
check_var "LARK_APP_ID" || ((ERRORS++))
check_var "LARK_APP_SECRET" || ((ERRORS++))

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ 测试资源Token检查"
echo "════════════════════════════════════════════════════════════════"

# 检查测试资源
check_var "TEST_BITABLE_APP_TOKEN" || ((ERRORS++))
check_var "TEST_BITABLE_TABLE_ID" || ((ERRORS++))
check_var "TEST_SHEET_TOKEN" || ((ERRORS++))
check_var "TEST_SHEET_ID" || ((ERRORS++))
check_var "TEST_DOC_TOKEN" || ((ERRORS++))

echo ""

# 总结
if [ $ERRORS -eq 0 ]; then
    echo "════════════════════════════════════════════════════════════════"
    echo "🎉 配置完整！所有必需的环境变量都已正确设置"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "📊 配置的测试资源:"
    echo "  ✅ Bitable: RZI2b0owwaQMN8suYevcbYPBnEe (表: tblfzrP1TqrIClDe)"
    echo "  ✅ Sheet:   HiwasEZJthNgDMttCeBckPTHnsc (sheet: a3fb01)"
    echo "  ✅ Doc:     QkvCdrrzIoOcXAxXbBXcGvZinsg"
    echo ""
    echo "🚀 可以运行集成测试了！"
    echo ""
    echo "运行命令:"
    echo "  export \$(cat $ENV_FILE | grep -v '^#' | xargs)"
    echo ""
    echo "  # 测试Bitable功能"
    echo "  pytest tests/integration/test_bitable_e2e.py -v"
    echo ""
    echo "  # 测试Sheet功能"
    echo "  pytest tests/integration/test_sheet_e2e.py -v"
    echo ""
    echo "  # 测试CloudDoc功能"
    echo "  pytest tests/integration/test_clouddoc_e2e.py -v"
    echo ""
    echo "  # 运行所有集成测试"
    echo "  pytest tests/integration/ -v"
    echo ""
else
    echo "════════════════════════════════════════════════════════════════"
    echo "⚠️  发现 $ERRORS 个配置问题"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "请检查并修复上述配置问题后再运行集成测试。"
    echo ""
    exit 1
fi
