# CI/CD 流程与自动化

**版本**: 1.0.0
**更新时间**: 2026-01-15
**状态**: Production Ready

---

## 🚀 CI/CD 概览

### 流程图

```
代码提交 → Pre-commit → Push → GitHub Actions → 测试 → 代码质量 → 安全扫描 → 构建 → 部署
```

### 自动化目标

| 阶段 | 目标 | 工具 |
|------|------|------|
| **代码检查** | 格式化、Linting | Ruff, Mypy |
| **测试** | 单元+集成测试 | Pytest |
| **覆盖率** | ≥ 75% | Coverage.py |
| **安全扫描** | 依赖+容器 | Safety, Trivy |
| **构建** | Docker 镜像 | Docker |
| **部署** | 自动化部署 | GitHub Actions |

---

## 🔨 Pre-commit 钩子

### 安装配置

**`.pre-commit-config.yaml`**:
```yaml
repos:
  # Ruff - 代码格式化和 Linting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Mypy - 类型检查
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict, --ignore-missing-imports]

  # 基础检查
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: detect-private-key

  # 安全检查
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: [-c, pyproject.toml]
```

### 安装步骤

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 Git 钩子
pre-commit install

# 手动运行检查
pre-commit run --all-files
```

### 钩子行为

```bash
# 提交时自动运行
git commit -m "feat: 新功能"
# → Ruff format
# → Ruff lint
# → Mypy check
# → Basic checks
# → Security scan
# → 通过后才能提交
```

---

## 🤖 GitHub Actions 工作流

### 主工作流 (CI)

**`.github/workflows/ci.yml`**:
```yaml
name: CI

on:
  push:
    branches:
      - main
      - '[0-9][0-9][0-9]-*'  # Speckit 功能分支 (如 001-lark-service-core)
  pull_request:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: \${{ matrix.python-version }}
          cache: 'pip'

      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov mypy ruff

      - name: 代码风格检查
        run: |
          ruff check src/ tests/
          ruff format --check src/ tests/

      - name: 类型检查
        run: |
          mypy src/ --strict

      - name: 运行测试
        run: |
          pytest tests/ \
            --cov=src/lark_service \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results.xml

      - name: 上传覆盖率报告
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

      - name: 上传测试结果
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results.xml

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 依赖安全扫描
        run: |
          pip install safety
          safety check --json

      - name: 代码安全扫描
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: 上传扫描结果
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json

  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    steps:
      - uses: actions/checkout@v4

      - name: 构建 Docker 镜像
        run: |
          docker build -t lark-service:\${{ github.sha }} .

      - name: 扫描镜像安全
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'lark-service:\${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: 上传 Trivy 结果
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### 发布工作流 (CD)

**`.github/workflows/release.yml`**:
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 构建 Docker 镜像
        run: |
          docker build -t lark-service:\${GITHUB_REF#refs/tags/} .
          docker tag lark-service:\${GITHUB_REF#refs/tags/} lark-service:latest

      - name: 登录 Docker Hub
        uses: docker/login-action@v3
        with:
          username: \${{ secrets.DOCKER_USERNAME }}
          password: \${{ secrets.DOCKER_PASSWORD }}

      - name: 推送镜像
        run: |
          docker push lark-service:\${GITHUB_REF#refs/tags/}
          docker push lark-service:latest

      - name: 创建 Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            lark-service-*.tar.gz
          generate_release_notes: true
        env:
          GITHUB_TOKEN: \${{ secrets.GITHUB_TOKEN }}
```

---

## 📊 质量门禁

### 质量标准

| 指标 | 阈值 | 检查方式 |
|------|------|---------|
| **测试通过率** | 100% | pytest exit code |
| **代码覆盖率** | ≥ 75% | coverage.py |
| **Mypy 覆盖率** | ≥ 99% | mypy --strict |
| **Ruff 错误** | 0 | ruff check |
| **安全漏洞** | 0 high/critical | safety + trivy |

### 门禁规则

```python
# 示例: 在 CI 中检查覆盖率
if coverage < 75%:
    print("❌ 覆盖率不足 75%")
    sys.exit(1)

if mypy_errors > 0:
    print("❌ Mypy 检查失败")
    sys.exit(1)

if high_vulnerabilities > 0:
    print("❌ 发现高危漏洞")
    sys.exit(1)
```

---

## 🔍 代码质量检查

### Ruff 配置

**`pyproject.toml`** (已配置):
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Mypy 配置

**`pyproject.toml`** (已配置):
```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### 运行命令

```bash
# Ruff 检查和修复
ruff check src/ --fix
ruff format src/

# Mypy 类型检查
mypy src/ --strict

# 完整检查
make lint  # 或在 Makefile 中定义
```

---

## 🛡️ 安全扫描

### 依赖扫描 (Safety)

```bash
# 安装 Safety
pip install safety

# 扫描依赖
safety check

# JSON 输出
safety check --json > safety-report.json

# 在 CI 中使用
safety check --exit-code 1  # 发现漏洞则失败
```

### 镜像扫描 (Trivy)

```bash
# 扫描镜像
trivy image lark-service:latest

# 仅显示 HIGH 和 CRITICAL
trivy image --severity HIGH,CRITICAL lark-service:latest

# JSON 输出
trivy image --format json -o trivy-report.json lark-service:latest
```

### 代码扫描 (Bandit)

```bash
# 扫描代码
bandit -r src/

# JSON 输出
bandit -r src/ -f json -o bandit-report.json
```

---

## 🚢 部署流程

### 分支触发策略

| 分支类型 | 触发条件 | CI 行为 |
|---------|---------|---------|
| **main** | push / PR | 完整 CI + 构建 + 安全扫描 |
| **NNN-*** | push / PR | 完整 CI + 构建 |
| **release/*** | push | 完整 CI + 构建 + 部署预发布 |
| **hotfix/*** | push | 完整 CI + 快速验证 |

**分支模式匹配**:
```yaml
branches:
  - main                    # 主分支
  - '[0-9][0-9][0-9]-*'    # Speckit 功能分支 (001-*, 002-*, ...)
  - 'release/**'            # 发布分支
  - 'hotfix/**'             # 热修复分支
```

### 开发环境部署

```bash
# 自动部署 (功能分支推送后)
# → 触发条件: push to NNN-* 分支
# → 构建镜像: lark-service:NNN-branch-name
# → 推送到测试镜像仓库
# → 部署到测试环境
# → 运行冒烟测试
```

**部署工作流**:
```yaml
# .github/workflows/deploy-dev.yml
name: Deploy to Dev

on:
  push:
    branches:
      - '[0-9][0-9][0-9]-*'  # 功能分支

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 构建镜像
        run: |
          BRANCH_NAME=${GITHUB_REF#refs/heads/}
          docker build -t lark-service:$BRANCH_NAME .

      - name: 推送到测试仓库
        run: |
          docker push test-registry/lark-service:$BRANCH_NAME

      - name: 部署到测试环境
        run: |
          kubectl set image deployment/lark-service \\
            lark-service=test-registry/lark-service:$BRANCH_NAME \\
            -n test
```

### 生产环境部署

```bash
# 手动触发 (main 分支 + 标签)
# → 触发条件: push tag v*
# → 代码审查通过
# → CI 全部通过
# → 创建 Release
# → 部署到预发布环境
# → 人工验证
# → 部署到生产环境
# → 监控告警
```

---

## 📋 CI/CD 检查清单

### Pre-commit
- [ ] `.pre-commit-config.yaml` 已配置
- [ ] Git 钩子已安装
- [ ] 本地测试通过

### GitHub Actions
- [ ] CI 工作流已配置
- [ ] CD 工作流已配置
- [ ] Secrets 已设置
- [ ] 工作流运行正常

### 质量门禁
- [ ] 测试覆盖率 ≥ 75%
- [ ] Mypy 检查通过
- [ ] 无 Ruff 错误
- [ ] 无高危漏洞

### 安全扫描
- [ ] 依赖扫描配置
- [ ] 镜像扫描配置
- [ ] 代码扫描配置
- [ ] 扫描结果已审查

---

**维护者**: Lark Service Team
**参考**: [ci-cd.md](./ci-cd.md)
