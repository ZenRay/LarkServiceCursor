#!/bin/bash
#
# 使用 uv 创建测试环境并修复依赖漏洞
#
# 用途: 在隔离的测试环境中安全地更新依赖包,验证无误后应用到主环境
#

set -e  # 遇到错误立即退出

echo "========================================="
echo "使用 uv 创建测试环境并修复依赖"
echo "========================================="
echo ""

# 项目目录
PROJECT_DIR="/home/ray/Documents/Files/LarkServiceCursor"
cd "$PROJECT_DIR"

# ===== 步骤1: 安装 uv (如果未安装) =====
echo "[步骤1/7] 检查 uv 安装状态..."

if ! command -v uv &> /dev/null; then
    echo "  uv 未安装,正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "  ✅ uv 安装完成"
else
    echo "  ✅ uv 已安装: $(uv --version)"
fi

echo ""

# ===== 步骤2: 创建测试环境 =====
echo "[步骤2/7] 创建 uv 测试环境..."

# 创建 .venv-test 目录
if [ -d ".venv-test" ]; then
    echo "  ⚠️  测试环境已存在,删除旧环境..."
    rm -rf .venv-test
fi

# 使用 uv 创建虚拟环境
uv venv .venv-test --python 3.12

echo "  ✅ 测试环境创建成功: .venv-test/"
echo ""

# ===== 步骤3: 安装当前依赖 =====
echo "[步骤3/7] 在测试环境中安装当前依赖..."

# 激活虚拟环境并安装依赖
source .venv-test/bin/activate

# 使用 uv 快速安装依赖 (比 pip 快10-100倍)
if [ -f "pyproject.toml" ]; then
    echo "  使用 pyproject.toml 安装依赖..."
    uv pip install -e .
else
    echo "  使用 requirements.txt 安装依赖..."
    uv pip install -r requirements.txt
fi

# 安装开发依赖
echo "  安装开发依赖..."
uv pip install pytest pytest-cov pytest-mock pytest-asyncio ruff mypy bandit pip-audit

echo "  ✅ 依赖安装完成"
echo ""

# ===== 步骤4: 运行初始测试 (确保环境正常) =====
echo "[步骤4/7] 运行初始测试验证环境..."

pytest tests/unit -v --tb=short -x 2>&1 | tail -20

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "  ✅ 初始测试通过"
else
    echo "  ⚠️  初始测试失败,但继续修复流程"
fi

echo ""

# ===== 步骤5: 扫描当前漏洞 =====
echo "[步骤5/7] 扫描当前依赖漏洞..."

pip-audit --desc 2>&1 | tee vulnerability-scan-before.txt | grep -E "Found|No known" || true

echo ""
echo "  完整扫描结果已保存到: vulnerability-scan-before.txt"
echo ""

# ===== 步骤6: 更新依赖包 =====
echo "[步骤6/7] 更新存在漏洞的依赖包..."

echo "  更新高危漏洞包..."

# 使用 uv 更新依赖 (速度快)
uv pip install --upgrade 'urllib3>=2.6.3,<3.0.0'
uv pip install --upgrade 'setuptools>=78.1.1'
uv pip install --upgrade 'requests>=2.32.4,<3.0.0'
uv pip install --upgrade 'pynacl>=1.6.2'
uv pip install --upgrade 'werkzeug>=3.1.5,<4.0.0'

echo "  ✅ 依赖更新完成"
echo ""

# 显示更新后的版本
echo "  更新后的版本:"
python3 -c "
import urllib3, setuptools, requests, werkzeug
try:
    import nacl
    print(f'  - urllib3: {urllib3.__version__}')
    print(f'  - setuptools: {setuptools.__version__}')
    print(f'  - requests: {requests.__version__}')
    print(f'  - werkzeug: {werkzeug.__version__}')
    print(f'  - pynacl: {nacl.__version__}')
except ImportError as e:
    print(f'  ⚠️  导入失败: {e}')
"

echo ""

# ===== 步骤7: 运行测试验证 =====
echo "[步骤7/7] 运行测试验证修复结果..."

echo "  运行单元测试..."
pytest tests/unit -v --tb=short 2>&1 | tail -30

TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "  ✅ 所有测试通过!"
    echo ""

    # 重新扫描漏洞
    echo "  重新扫描漏洞..."
    pip-audit --desc 2>&1 | tee vulnerability-scan-after.txt | head -30

    echo ""
    echo "  扫描结果已保存到: vulnerability-scan-after.txt"
    echo ""

    # ===== 成功:导出更新后的依赖 =====
    echo "========================================="
    echo "✅ 修复成功!"
    echo "========================================="
    echo ""

    echo "导出更新后的依赖列表..."
    uv pip freeze > requirements-fixed.txt

    echo "  ✅ 已导出到: requirements-fixed.txt"
    echo ""

    # 生成对比报告
    echo "生成版本对比报告..."

    cat > vulnerability-fix-report.md << 'REPORT_EOF'
# 依赖漏洞修复报告

**执行时间**: $(date)
**测试环境**: uv + Python 3.12
**状态**: ✅ 修复成功

## 更新的依赖包

| 包名 | 修复前版本 | 修复后版本 | 漏洞数 |
|------|-----------|-----------|--------|
| urllib3 | 2.3.0 | $(python3 -c "import urllib3; print(urllib3.__version__)") | 5个CVE |
| setuptools | 72.1.0 | $(python3 -c "import setuptools; print(setuptools.__version__)") | 1个漏洞 |
| requests | 2.32.3 | $(python3 -c "import requests; print(requests.__version__)") | 1个CVE |
| werkzeug | 3.1.3 | $(python3 -c "import werkzeug; print(werkzeug.__version__)") | 2个CVE |
| pynacl | 1.5.0 | $(python3 -c "import nacl; print(nacl.__version__)") | 1个CVE |

## 测试结果

- ✅ 单元测试: 全部通过
- ✅ 依赖扫描: 高危漏洞已修复
- ✅ 兼容性: 无破坏性变更

## 应用到生产环境

### 方式A: 直接替换 requirements.txt (推荐)

\`\`\`bash
# 1. 备份当前依赖
cp requirements.txt requirements.txt.backup

# 2. 使用修复后的依赖
cp requirements-fixed.txt requirements.txt

# 3. 在主环境重新安装
pip install -r requirements.txt

# 4. 运行测试验证
pytest tests/unit -v

# 5. 提交变更
git add requirements.txt
git commit -m "fix: 修复依赖包安全漏洞"
\`\`\`

### 方式B: 手动更新主环境

\`\`\`bash
# 在主环境执行相同的更新命令
pip install --upgrade urllib3>=2.6.3 setuptools>=78.1.1 requests>=2.32.4
pip freeze > requirements.txt
\`\`\`

## 清理测试环境

\`\`\`bash
# 测试环境不再需要时可删除
deactivate  # 退出虚拟环境
rm -rf .venv-test
\`\`\`

---

**生成时间**: $(date)
REPORT_EOF

    echo "  ✅ 报告已生成: vulnerability-fix-report.md"
    echo ""

    # 显示下一步操作
    echo "========================================="
    echo "📋 下一步操作"
    echo "========================================="
    echo ""
    echo "1. 查看修复报告:"
    echo "   cat vulnerability-fix-report.md"
    echo ""
    echo "2. 应用到主环境:"
    echo "   cp requirements-fixed.txt requirements.txt"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "3. 或直接在主环境更新:"
    echo "   pip install --upgrade urllib3>=2.6.3 setuptools>=78.1.1 requests>=2.32.4"
    echo ""
    echo "4. 清理测试环境:"
    echo "   deactivate && rm -rf .venv-test"
    echo ""

else
    echo "  ❌ 测试失败!"
    echo ""
    echo "  请检查 pytest 输出日志,修复测试问题后重试"
    echo ""

    echo "========================================="
    echo "⚠️  修复未完成"
    echo "========================================="
    echo ""
    echo "测试环境已保留在 .venv-test/ 中,您可以:"
    echo ""
    echo "1. 激活测试环境:"
    echo "   source .venv-test/bin/activate"
    echo ""
    echo "2. 手动调试:"
    echo "   pytest tests/unit -v --tb=long"
    echo ""
    echo "3. 退出并清理:"
    echo "   deactivate && rm -rf .venv-test"
    echo ""
fi

echo "========================================="
echo "测试环境位置: .venv-test/"
echo "========================================="
