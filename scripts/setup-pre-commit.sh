#!/usr/bin/env bash

set -e

echo "🔧 设置 Pre-commit 钩子..."

# 检查是否安装了 pre-commit
if ! command -v pre-commit &> /dev/null; then
    echo "📦 安装 pre-commit..."
    pip install pre-commit
fi

# 安装 Git 钩子
echo "🔗 安装 Git 钩子..."
pre-commit install

# 运行一次检查所有文件
echo "✅ 运行初始检查..."
pre-commit run --all-files || echo "⚠️  发现一些问题,请修复后再提交"

echo ""
echo "✅ Pre-commit 钩子已设置完成!"
echo ""
echo "从现在开始,每次 git commit 时会自动运行:"
echo "  - Ruff (代码格式化和 Linting)"
echo "  - Mypy (类型检查)"
echo "  - 基础检查 (trailing-whitespace, check-yaml 等)"
echo "  - 安全检查 (Bandit)"
echo ""
echo "如需跳过检查 (不推荐): git commit --no-verify"
