#!/bin/bash
# Git 提交前自动检查脚本
# 遵循 Constitution XI - Git 提交规范
#
# 用法:
#   ./specify/scripts/bash/pre-commit-check.sh
#
# 功能:
#   1. 代码格式化 (ruff format)
#   2. 代码风格检查 (ruff check)
#   3. 类型检查 (mypy)
#   4. 测试运行 (pytest)
#
# 退出码:
#   0 - 所有检查通过
#   1 - 检查失败

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔍 开始提交前检查..."
echo "📍 项目目录: $PROJECT_ROOT"
echo ""

# 检查是否有待提交的更改
if [ -z "$(git status --porcelain)" ]; then
    echo "⚠️  没有待提交的更改"
    exit 0
fi

# 1. 代码格式化 (git add 前)
echo "1️⃣  运行 Ruff 格式化..."
if ruff format .; then
    echo "✅ 格式化完成"
else
    echo "❌ 格式化失败"
    exit 1
fi
echo ""

# 2. 代码风格检查 (git commit 前)
echo "2️⃣  运行 Ruff 代码风格检查..."
if ruff check src/ tests/ --fix; then
    echo "✅ 代码风格检查通过"
else
    echo "❌ 代码风格检查失败"
    echo ""
    echo "💡 提示: 请修复上述问题后重新运行"
    echo "   查看详细错误: ruff check src/ tests/"
    exit 1
fi
echo ""

# 3. 类型检查 (git commit 前)
echo "3️⃣  运行 Mypy 类型检查..."
if mypy src/; then
    echo "✅ 类型检查通过"
else
    echo "❌ 类型检查失败"
    echo ""
    echo "💡 提示: 请修复类型错误后重新运行"
    echo "   查看详细错误: mypy src/ --show-error-codes"
    exit 1
fi
echo ""

# 4. 运行测试 (git commit 前)
echo "4️⃣  运行测试..."
if pytest tests/ --cov=src -q; then
    echo "✅ 测试通过"
else
    echo "❌ 测试失败"
    echo ""
    echo "💡 提示: 请修复测试失败后重新运行"
    echo "   查看详细错误: pytest tests/ -v"
    echo "   仅运行失败测试: pytest tests/ --lf"
    exit 1
fi
echo ""

echo "🎉 所有检查通过!"
echo ""
echo "📝 下一步:"
echo "  1. 添加更改: git add ."
echo "  2. 提交代码: git commit -m '<type>(<scope>): <description>'"
echo "  3. 推送代码: git push origin <branch-name>  # 需明确指定分支"
echo ""
echo "💡 提交消息格式 (Conventional Commits):"
echo "  类型: feat, fix, docs, style, refactor, test, chore, perf"
echo "  范围: token, storage, config, cli, core, utils 等"
echo ""
echo "  示例:"
echo "    feat(token): 实现自动刷新机制"
echo "    fix(storage): 修复 PostgreSQL 连接池问题"
echo "    docs(readme): 更新安装说明"
echo "    style(core): 代码格式化"
echo "    test(unit): 添加 CredentialPool 测试"
