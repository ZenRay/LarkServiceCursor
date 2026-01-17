# Speckit 验证指南

本文档说明如何验证项目各个阶段的完成质量。

## 快速验证命令

### Phase 验证完整流程

当你完成某个 Phase 的开发后,可以使用以下命令进行完整验证:

```bash
# 进入项目根目录
cd /home/ray/Documents/Files/LarkServiceCursor

# 1. 代码格式化检查
ruff format --check src/ tests/

# 2. 代码质量检查 (linting)
ruff check src/ tests/

# 3. 类型检查
mypy src/

# 4. 运行所有测试
pytest tests/ --ignore=tests/performance -v

# 5. 生成覆盖率报告
pytest tests/ --ignore=tests/performance --cov=src/lark_service --cov-report=html --cov-report=term
```

### Phase 2 专项验证

Phase 2 (US1 Token 管理) 的验证命令:

```bash
# 1. 验证代码质量
ruff check src/lark_service/core/ tests/unit/core/ tests/integration/

# 2. 验证类型检查
mypy src/lark_service/core/

# 3. 运行核心模块单元测试
pytest tests/unit/core/ -v

# 4. 运行 CLI 单元测试
pytest tests/unit/cli/ -v

# 5. 运行集成测试
pytest tests/integration/test_credential_pool.py tests/integration/test_token_lifecycle.py -v

# 6. 生成覆盖率报告
pytest tests/unit/core/ tests/unit/cli/ tests/integration/ --cov=src/lark_service/core --cov=src/lark_service/cli --cov-report=html
```

### Phase 3 专项验证 (消息服务)

```bash
# 验证消息模块
ruff check src/lark_service/messaging/ tests/unit/messaging/ tests/contract/
mypy src/lark_service/messaging/
pytest tests/unit/messaging/ tests/contract/test_messaging_contract.py tests/integration/test_messaging_e2e.py -v
```

### Phase 4 专项验证 (云文档 + 通讯录)

```bash
# 验证云文档模块
ruff check src/lark_service/clouddoc/ tests/unit/clouddoc/
mypy src/lark_service/clouddoc/
pytest tests/unit/clouddoc/ tests/contract/test_clouddoc_contract.py tests/integration/test_clouddoc_e2e.py -v

# 验证通讯录模块
ruff check src/lark_service/contact/ tests/unit/contact/
mypy src/lark_service/contact/
pytest tests/unit/contact/ tests/contract/test_contact_contract.py tests/integration/test_contact_e2e.py -v
```

### Phase 5 专项验证 (aPaaS 平台)

```bash
# 验证 aPaaS 模块
ruff check src/lark_service/apaas/ tests/unit/apaas/
mypy src/lark_service/apaas/
pytest tests/unit/apaas/ tests/contract/test_apaas_contract.py tests/integration/test_apaas_e2e.py -v
```

## 验证检查点

### Phase 2 检查点 (已完成)

根据 tasks.md 定义的检查点:

#### ✅ 1. 构建验证
- **状态**: ⚠️ 跳过 (Docker 镜像源网络问题)
- **命令**: `docker build -t lark-service:latest .`
- **预期**: 构建成功

#### ✅ 2. 代码质量
- **状态**: ✅ 通过
- **命令**: `ruff check src/ tests/`
- **结果**: All checks passed!
- **命令**: `mypy src/`
- **结果**: Success: no issues found

#### ✅ 3. 单元测试
- **状态**: ✅ 通过 (53 passed)
- **命令**: `pytest tests/unit/core/ -v`
- **结果**: 53 passed, 12 warnings in 7.87s

#### ✅ 4. 集成测试
- **状态**: ✅ 通过 (15 passed)
- **命令**: `pytest tests/integration/test_credential_pool.py tests/integration/test_token_lifecycle.py -v`
- **结果**: 15 passed, 12 warnings in 35.60s

#### ✅ 5. CLI 测试
- **状态**: ✅ 通过 (13 passed)
- **命令**: `pytest tests/unit/cli/ -v`
- **结果**: 13 passed, 12 warnings in 3.36s

#### ✅ 6. 功能验证
- **状态**: ✅ 通过
- **验证内容**: CredentialPool.get_token() 返回有效 Token,服务重启后从数据库恢复
- **测试覆盖**: 集成测试已验证

### 总结

**Phase 2 验证结果**:
- ✅ 代码质量: ruff + mypy 全部通过
- ✅ 单元测试: 53 个测试通过
- ✅ 集成测试: 15 个测试通过
- ✅ CLI 测试: 13 个测试通过
- ✅ 总计: **81 个测试全部通过**
- ✅ 覆盖率: 核心模块达到 47%+ (集成测试覆盖)

## 常用验证脚本

### 快速验证脚本

创建一个快速验证脚本 `scripts/verify-phase.sh`:

```bash
#!/bin/bash
# 快速验证当前 Phase 的代码质量

set -e

echo "=== 1. 代码格式化检查 ==="
ruff format --check src/ tests/

echo -e "\n=== 2. 代码质量检查 ==="
ruff check src/ tests/

echo -e "\n=== 3. 类型检查 ==="
mypy src/

echo -e "\n=== 4. 运行测试 ==="
pytest tests/ --ignore=tests/performance -q

echo -e "\n✅ 所有检查通过!"
```

使用方法:

```bash
chmod +x scripts/verify-phase.sh
./scripts/verify-phase.sh
```

### Git 提交前检查

在提交代码前,建议运行:

```bash
# 格式化代码
ruff format .

# 检查代码质量并自动修复
ruff check src/ tests/ --fix

# 类型检查
mypy src/

# 运行测试
pytest tests/ --ignore=tests/performance -q
```

## 性能基准测试

对于性能敏感的模块,运行性能测试:

```bash
# 运行性能测试
pytest tests/performance/ -v

# 生成性能报告
pytest tests/performance/ --benchmark-only --benchmark-autosave
```

## 覆盖率报告

生成详细的覆盖率报告:

```bash
# 生成 HTML 覆盖率报告
pytest tests/ --ignore=tests/performance --cov=src/lark_service --cov-report=html

# 打开报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 持续集成 (CI)

GitHub Actions 会自动运行以下检查:

1. **Lint**: `ruff check .`
2. **Format**: `ruff format --check .`
3. **Type Check**: `mypy src/`
4. **Test**: `pytest tests/ --ignore=tests/performance`
5. **Coverage**: `pytest --cov=src/lark_service --cov-report=xml`

查看 `.github/workflows/ci.yml` 了解详细配置。

## 故障排查

### 测试失败

如果测试失败,查看详细输出:

```bash
pytest tests/unit/core/test_credential_pool.py -v --tb=long
```

### 类型检查失败

查看详细的类型错误:

```bash
mypy src/lark_service/core/ --show-error-codes --pretty
```

### 覆盖率不足

查看未覆盖的代码行:

```bash
pytest tests/ --cov=src/lark_service --cov-report=term-missing
```

## 参考资料

- [Constitution 合规性检查清单](../specs/001-lark-service-core/tasks.md#constitution-合规性检查清单)
- [Git Workflow](./git-workflow.md)
- [Performance Baseline](./performance-baseline-2026-01-15.md)
