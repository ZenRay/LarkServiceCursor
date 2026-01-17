# 测试指南

## 📖 概述

本项目使用pytest进行单元测试,要求所有代码保持60%以上的测试覆盖率。

---

## 🚀 快速开始

### 安装测试环境

```bash
# 使用uv环境(推荐)
source .venv-test/bin/activate

# 或安装开发依赖
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块
pytest tests/unit/core/

# 运行特定文件
pytest tests/unit/core/test_credential_pool.py

# 运行特定测试
pytest tests/unit/core/test_credential_pool.py::TestCredentialPool::test_init

# 详细输出
pytest -v

# 显示print输出
pytest -s
```

### 查看覆盖率

```bash
# 终端输出
pytest --cov=src/lark_service --cov-report=term-missing

# 生成HTML报告
pytest --cov=src/lark_service --cov-report=html
open htmlcov/index.html

# 生成XML报告(CI/CD)
pytest --cov=src/lark_service --cov-report=xml
```

---

## 📋 覆盖率要求

### 整体要求
- **最低覆盖率**: 60%
- **目标覆盖率**: 70%+
- **核心模块**: 80%+

### 覆盖率阈值

项目已设置覆盖率阈值60%,低于此值将导致测试失败:

```bash
$ pytest
...
FAILED: Coverage check failed. Required: 60%, Actual: 58%
```

### 模块覆盖率目标

| 模块类型 | 目标覆盖率 | 说明 |
|---------|-----------|------|
| 核心模块 | 80%+ | Token管理、存储、重试等 |
| 业务模块 | 70%+ | Messaging、CloudDoc、Contact |
| 工具模块 | 70%+ | Logger、Validators、Masking |
| Models | 90%+ | 数据模型 |

---

## 🎯 测试编写指南

### 测试结构

```python
"""Unit tests for ModuleName.

Brief description of what is being tested.
"""

import pytest
from unittest.mock import Mock, patch

from lark_service.module import ClassName


# === Fixtures ===

@pytest.fixture
def mock_dependency():
    """Create mock dependency."""
    return Mock()


@pytest.fixture
def instance(mock_dependency):
    """Create instance under test."""
    return ClassName(mock_dependency)


# === Test Classes ===

class TestClassName:
    """Test ClassName functionality."""

    def test_method_success(self, instance):
        """Test method succeeds with valid input."""
        result = instance.method("valid_input")
        assert result == expected_value

    def test_method_invalid_input(self, instance):
        """Test method raises error with invalid input."""
        with pytest.raises(ValueError):
            instance.method("invalid_input")
```

### Mock策略

**完全Mock隔离**:
- ❌ 不使用真实数据库
- ❌ 不调用真实API
- ❌ 不依赖外部服务
- ✅ 使用Mock对象
- ✅ 快速执行
- ✅ 可重复

**示例**:

```python
from unittest.mock import Mock, patch

@pytest.fixture
def mock_credential_pool():
    """Mock credential pool."""
    pool = Mock()
    pool._get_sdk_client.return_value = Mock()
    pool.get_token.return_value = Mock(token_value="mock_token")
    return pool

def test_with_mock(mock_credential_pool):
    """Test using mocked dependencies."""
    client = SomeClient(mock_credential_pool)
    result = client.do_something()

    # Verify mock was called
    mock_credential_pool._get_sdk_client.assert_called_once()
    assert result is not None
```

### 测试覆盖场景

**必须覆盖**:
1. ✅ **正常场景** - 正确输入,成功执行
2. ✅ **异常场景** - 错误输入,抛出异常
3. ✅ **边界条件** - 空值、最大值、最小值
4. ✅ **错误处理** - API失败、超时、重试

**选择性覆盖**:
- 🟡 **并发场景** - 如果涉及多线程
- 🟡 **性能测试** - 如果有性能要求
- 🟡 **集成测试** - 标记为 `@pytest.mark.integration`

---

## 📊 查看覆盖率报告

### HTML报告

```bash
pytest --cov=src/lark_service --cov-report=html
open htmlcov/index.html
```

**功能**:
- 按模块查看覆盖率
- 查看未覆盖代码行
- 可视化覆盖率热图

### 终端报告

```bash
pytest --cov=src/lark_service --cov-report=term-missing
```

**输出**:
```
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
src/lark_service/core/config.py     51      1   98%   93
src/lark_service/core/retry.py      68      5   93%   230-242
---------------------------------------------------------------
TOTAL                              3892   1542   60%
```

---

## 🔧 常用命令

### 测试筛选

```bash
# 只运行单元测试
pytest tests/unit/

# 跳过慢速测试
pytest -m "not slow"

# 只运行标记的测试
pytest -m integration

# 运行失败的测试
pytest --lf

# 先运行失败的测试
pytest --ff
```

### 调试

```bash
# 进入pdb调试
pytest --pdb

# 失败时进入调试
pytest --pdb -x

# 显示详细输出
pytest -vv

# 显示局部变量
pytest -l
```

### 性能

```bash
# 显示最慢的10个测试
pytest --durations=10

# 并行运行(需要pytest-xdist)
pytest -n auto
```

---

## 📝 测试命名规范

### 文件命名
- `test_<module_name>.py` - 单元测试
- `test_<feature>_integration.py` - 集成测试

### 类命名
- `Test<ClassName>` - 测试类名
- `Test<ClassName><Method>` - 测试特定方法

### 方法命名
- `test_<method>_<scenario>` - 测试方法
- `test_<method>_<condition>_<expected>` - 详细描述

**示例**:
```python
class TestCredentialPool:
    def test_get_token_success(self):
        """Test get_token succeeds with valid app_id."""
        pass

    def test_get_token_invalid_app_id_raises_error(self):
        """Test get_token raises error with invalid app_id."""
        pass
```

---

## 🎯 CI/CD集成

### GitHub Actions

测试会在以下情况自动运行:
- Pull Request
- Push to main
- 手动触发

### 覆盖率检查

PR会显示覆盖率变化:
```
Coverage: 60.38% (+0.5%)
✅ Coverage check passed (required: 60%)
```

### 失败处理

如果覆盖率低于60%:
1. 查看覆盖率报告
2. 添加缺失的测试
3. 重新push触发CI

---

## 📚 参考资源

### Pytest文档
- [Pytest官方文档](https://docs.pytest.org/)
- [Pytest-cov插件](https://pytest-cov.readthedocs.io/)
- [Unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

### 项目示例
- `tests/unit/core/test_credential_pool.py` - 完整示例
- `tests/unit/messaging/test_client.py` - Mock示例
- `tests/unit/cardkit/test_cardkit.py` - 简化示例

---

## ❓ 常见问题

### Q: 覆盖率不增加?
A: 确保测试执行了被测代码,检查Mock是否正确

### Q: 如何Mock SDK?
A: 参考 `test_credential_pool.py` 中的Mock模式

### Q: 测试太慢?
A: 使用Mock隔离外部依赖,避免真实IO

### Q: 覆盖率如何提升?
A: 查看HTML报告找到未覆盖代码,针对性添加测试

---

**更新时间**: 2026-01-18
**当前覆盖率**: 60.38%
**测试总数**: 406个
