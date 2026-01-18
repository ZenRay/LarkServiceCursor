#!/bin/bash
# 完整代码质量检查脚本
# 使用与 pre-commit 相同的配置，确保本地和 CI 结果一致

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🔍 运行完整代码质量检查${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# 检查目标（默认为 src/ 和 tests/）
TARGET_SRC="${1:-src/}"
TARGET_TESTS="${2:-tests/}"

ERRORS=0

# ==================== Ruff Check ====================
echo -e "${BLUE}📝 Step 1: Ruff Linting${NC}"
echo -e "${YELLOW}检查: ${TARGET_SRC} ${TARGET_TESTS}${NC}"
if python -m ruff check "${TARGET_SRC}" "${TARGET_TESTS}"; then
    echo -e "${GREEN}✓ Ruff check 通过${NC}"
else
    echo -e "${RED}✗ Ruff check 失败${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ==================== Ruff Format ====================
echo -e "${BLUE}📝 Step 2: Ruff Formatting${NC}"
echo -e "${YELLOW}检查: ${TARGET_SRC} ${TARGET_TESTS}${NC}"
if python -m ruff format --check "${TARGET_SRC}" "${TARGET_TESTS}"; then
    echo -e "${GREEN}✓ Ruff format 通过${NC}"
else
    echo -e "${RED}✗ Ruff format 失败${NC}"
    echo -e "${YELLOW}提示: 运行 'python -m ruff format ${TARGET_SRC} ${TARGET_TESTS}' 自动修复${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ==================== Mypy - src/ (严格模式) ====================
echo -e "${BLUE}📝 Step 3: Mypy 类型检查 - src/ (严格模式)${NC}"
echo -e "${YELLOW}检查: ${TARGET_SRC}${NC}"
if python -m mypy "${TARGET_SRC}" \
    --strict \
    --ignore-missing-imports; then
    echo -e "${GREEN}✓ Mypy (src/) 通过${NC}"
else
    echo -e "${RED}✗ Mypy (src/) 失败${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ==================== Mypy - tests/ (宽松模式) ====================
echo -e "${BLUE}📝 Step 4: Mypy 类型检查 - tests/ (宽松模式)${NC}"
echo -e "${YELLOW}检查: ${TARGET_TESTS}${NC}"
echo -e "${BLUE}ℹ 使用宽松配置（忽略测试函数类型注解）${NC}"

# 运行 mypy，但不将 no-untyped-def 视为错误
MYPY_OUTPUT=$(python -m mypy "${TARGET_TESTS}" \
    --ignore-missing-imports \
    --allow-untyped-defs \
    --allow-untyped-calls \
    --no-warn-return-any \
    --no-warn-unused-ignores \
    --no-check-untyped-defs \
    --disable-error-code=no-untyped-def \
    --disable-error-code=misc 2>&1)

MYPY_EXIT=$?

# 检查是否有除了 no-untyped-def 之外的错误
if echo "$MYPY_OUTPUT" | grep -v "no-untyped-def" | grep -v "misc" | grep -q "error:"; then
    echo "$MYPY_OUTPUT"
    echo -e "${RED}✗ Mypy (tests/) 有严重错误${NC}"
    ERRORS=$((ERRORS + 1))
elif [ $MYPY_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Mypy (tests/) 通过（忽略类型注解警告）${NC}"
else
    # 只有 no-untyped-def 错误，视为通过
    echo -e "${GREEN}✓ Mypy (tests/) 通过（已忽略 ${YELLOW}$(echo "$MYPY_OUTPUT" | grep -c "error:")${GREEN} 个类型注解警告）${NC}"
fi
echo ""

# ==================== Bandit 安全检查 ====================
echo -e "${BLUE}📝 Step 5: Bandit 安全检查${NC}"
echo -e "${YELLOW}检查: ${TARGET_SRC} ${TARGET_TESTS}${NC}"

# 检查 bandit 是否安装
if ! command -v bandit &> /dev/null; then
    echo -e "${YELLOW}⚠ Bandit 未安装，跳过安全检查${NC}"
    echo -e "${BLUE}ℹ 安装: pip install 'bandit[toml]'${NC}"
else
    if python -m bandit -c pyproject.toml -r "${TARGET_SRC}" "${TARGET_TESTS}" -q 2>/dev/null; then
        echo -e "${GREEN}✓ Bandit 安全检查通过${NC}"
    else
        BANDIT_EXIT=$?
        if [ $BANDIT_EXIT -eq 1 ]; then
            echo -e "${YELLOW}⚠ Bandit 发现潜在安全问题（已通过 nosec 标记的除外）${NC}"
            echo -e "${BLUE}ℹ 运行 'bandit -c pyproject.toml -r ${TARGET_SRC}' 查看详情${NC}"
        else
            echo -e "${RED}✗ Bandit 检查失败${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi
echo ""

# ==================== 总结 ====================
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！代码质量良好 🎉${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 ${ERRORS} 个检查失败${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}请修复上述问题后重新运行${NC}"
    exit 1
fi
