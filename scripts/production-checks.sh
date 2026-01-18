#!/bin/bash
#
# 生产就绪检查脚本
# 执行安全扫描和压力测试
#

echo "========================================="
echo "Lark Service 生产就绪检查"
echo "========================================="
echo ""

# 1. 安全扫描
echo "[1/3] 执行安全扫描..."
echo "----------------------------------------"

# Python 依赖漏洞扫描 (safety)
echo "→ Python 依赖漏洞扫描 (safety)..."
pip install safety > /dev/null 2>&1
safety check --json > safety-report.json 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ 依赖扫描通过,无已知漏洞"
else
    echo "  ⚠ 发现依赖漏洞,请检查 safety-report.json"
fi

# Docker 镜像安全扫描 (trivy)
echo "→ Docker 镜像安全扫描 (trivy)..."
if command -v trivy &> /dev/null; then
    docker build -t lark-service:latest . > /dev/null 2>&1
    trivy image --severity HIGH,CRITICAL lark-service:latest > trivy-report.txt 2>&1
    if [ $? -eq 0 ]; then
        echo "  ✓ 镜像扫描完成,请检查 trivy-report.txt"
    else
        echo "  ⚠ 镜像扫描失败"
    fi
else
    echo "  ⚠ trivy 未安装,跳过镜像扫描"
fi

# 代码安全扫描 (bandit)
echo "→ 代码安全扫描 (bandit)..."
pip install bandit > /dev/null 2>&1
bandit -r src/ -f json -o bandit-report.json > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ 代码扫描通过"
else
    echo "  ⚠ 发现安全问题,请检查 bandit-report.json"
fi

echo ""

# 2. 性能测试
echo "[2/3] 执行性能测试..."
echo "----------------------------------------"

echo "→ 运行单元测试..."
pytest tests/ -v --tb=short > test-report.txt 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ 所有测试通过"
else
    echo "  ⚠ 部分测试失败,请检查 test-report.txt"
fi

echo "→ 测试覆盖率检查..."
pytest tests/ --cov=src/lark_service --cov-report=html --cov-report=term > coverage-report.txt 2>&1
coverage=$(grep "TOTAL" coverage-report.txt | awk '{print $4}' | sed 's/%//')
if [ -n "$coverage" ] && [ $(echo "$coverage >= 75" | bc) -eq 1 ]; then
    echo "  ✓ 测试覆盖率: $coverage% (≥75%)"
else
    echo "  ⚠ 测试覆盖率偏低: $coverage% (建议≥75%)"
fi

echo ""

# 3. 生产配置检查
echo "[3/3] 生产配置检查..."
echo "----------------------------------------"

# 检查环境变量
required_envs=(
    "LARK_CONFIG_ENCRYPTION_KEY"
    "POSTGRES_HOST"
    "POSTGRES_DB"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
)

all_envs_set=true
for env in "${required_envs[@]}"; do
    if [ -z "${!env}" ]; then
        echo "  ⚠ 缺少环境变量: $env"
        all_envs_set=false
    fi
done

if [ "$all_envs_set" = true ]; then
    echo "  ✓ 所有必需环境变量已设置"
fi

# 检查文件权限
if [ -f ".env" ]; then
    perms=$(stat -c "%a" .env 2>/dev/null || stat -f "%A" .env 2>/dev/null)
    if [ "$perms" = "600" ]; then
        echo "  ✓ .env 文件权限正确 (600)"
    else
        echo "  ⚠ .env 文件权限不安全: $perms (应为600)"
    fi
fi

if [ -f "config/applications.db" ]; then
    perms=$(stat -c "%a" config/applications.db 2>/dev/null || stat -f "%A" config/applications.db 2>/dev/null)
    if [ "$perms" = "600" ]; then
        echo "  ✓ SQLite配置文件权限正确 (600)"
    else
        echo "  ⚠ SQLite配置文件权限不安全: $perms (应为600)"
    fi
fi

echo ""
echo "========================================="
echo "检查完成!"
echo "========================================="
echo ""
echo "生成的报告:"
echo "  - safety-report.json (依赖漏洞扫描)"
echo "  - trivy-report.txt (镜像安全扫描)"
echo "  - bandit-report.json (代码安全扫描)"
echo "  - test-report.txt (单元测试结果)"
echo "  - coverage-report.txt (测试覆盖率)"
echo "  - htmlcov/ (覆盖率HTML报告)"
echo ""
