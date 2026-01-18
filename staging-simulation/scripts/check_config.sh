#!/bin/bash
# 检查 .env.local 配置完整性

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           📋 检查 .env.local 配置完整性                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -f ".env.local" ]; then
    echo "❌ 错误: .env.local 文件不存在"
    echo ""
    echo "请先创建配置文件:"
    echo "  cp env.local.template .env.local"
    echo "  vim .env.local"
    exit 1
fi

echo "✅ .env.local 文件存在"
echo ""

# 加载环境变量（不导出，仅用于检查）
source .env.local 2>/dev/null || {
    echo "⚠️  警告: 加载配置文件时出错，可能有语法问题"
    echo ""
}

# 关键配置项检查
echo "════════════════════════════════════════════════════════════════════════"
echo "🔍 关键配置项检查"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

check_config() {
    local var_name=$1
    local var_value="${!var_name}"
    local is_required=$2
    local example_values=$3

    if [ -z "$var_value" ]; then
        if [ "$is_required" = "required" ]; then
            echo "❌ $var_name: 未设置 (必填项)"
            return 1
        else
            echo "⚠️  $var_name: 未设置 (可选项)"
            return 0
        fi
    fi

    # 检查是否还是示例值
    if echo "$example_values" | grep -qw "$var_value" 2>/dev/null; then
        echo "⚠️  $var_name: 仍使用示例值，需要替换"
        return 1
    fi

    # 脱敏显示
    if [[ "$var_name" =~ (SECRET|PASSWORD|KEY|TOKEN) ]]; then
        local masked="${var_value:0:8}...${var_value: -4}"
        echo "✅ $var_name: $masked (已配置)"
    else
        echo "✅ $var_name: $var_value"
    fi
    return 0
}

errors=0

echo "【1. 飞书应用凭证】"
check_config "LARK_APP_ID" "required" "cli_example_app_id_change_me" || ((errors++))
check_config "LARK_APP_SECRET" "required" "example_secret_32_chars_change_me" || ((errors++))
echo ""

echo "【2. 数据库配置】"
check_config "DB_HOST" "required" "" || ((errors++))
check_config "DB_PORT" "required" "" || ((errors++))
check_config "DB_NAME" "required" "" || ((errors++))
check_config "DB_USER" "required" "" || ((errors++))
check_config "DB_PASSWORD" "required" "" || ((errors++))
check_config "POSTGRES_HOST" "required" "" || ((errors++))
check_config "POSTGRES_PORT" "required" "" || ((errors++))
echo ""

echo "【3. Token管理】"
check_config "TOKEN_ENCRYPTION_KEY" "required" "test_key_for_local_only_not_for_production_use" || ((errors++))
check_config "TOKEN_REFRESH_THRESHOLD" "optional" "" || ((errors++))
echo ""

echo "【4. 飞书API配置】"
check_config "FEISHU_API_BASE_URL" "required" "" || ((errors++))
check_config "FEISHU_API_TIMEOUT" "optional" "" || ((errors++))
echo ""

echo "【5. 环境标识】"
check_config "ENVIRONMENT" "required" "" || ((errors++))
check_config "APP_NAME" "required" "" || ((errors++))
echo ""

echo "════════════════════════════════════════════════════════════════════════"
echo "📊 检查结果"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

if [ $errors -eq 0 ]; then
    echo "✅ 所有必填配置项都已正确设置！"
    echo ""
    echo "下一步:"
    echo "  1. 加载环境变量: export \$(cat .env.local | grep -v '^#' | xargs)"
    echo "  2. 运行健康检查: cd .. && python scripts/staging_health_check.py"
    echo "  3. 运行集成测试: pytest tests/integration/ -v"
else
    echo "❌ 发现 $errors 个配置问题，请修复后重试"
    echo ""
    echo "修复方式:"
    echo "  vim .env.local"
    echo ""
    echo "重点检查:"
    echo "  • LARK_APP_ID 和 LARK_APP_SECRET 必须替换为真实值"
    echo "  • 不能使用示例值（如 cli_example_app_id_change_me）"
    echo "  • 获取凭证: https://open.feishu.cn/app"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════"

exit $errors
