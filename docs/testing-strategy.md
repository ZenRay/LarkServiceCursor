# 测试策略与最佳实践

**版本**: 1.0.0  
**更新时间**: 2026-01-15  
**状态**: Production Ready

---

## 📋 测试目标

### 覆盖率要求

| 测试类型 | 目标覆盖率 | 当前覆盖率 | 状态 |
|---------|-----------|-----------|------|
| **单元测试** | ≥ 80% | 77.33% | 🟡 接近达标 |
| **集成测试** | ≥ 60% | 45% | 🟡 进行中 |
| **关键路径** | 100% | 90%+ | ✅ 优秀 |
| **整体覆盖** | ≥ 75% | 77.33% | ✅ 达标 |

### 关键路径定义 (CHK137)

**关键路径**: 核心业务流程,失败会导致系统不可用的代码路径。

| 路径 ID | 路径名称 | 模块 | 覆盖率要求 |
|---------|---------|------|-----------|
| **CP001** | Token 获取流程 | `credential_pool.get_token()` | 100% ✅ |
| **CP002** | Token 刷新流程 | `credential_pool.refresh_token()` | 100% ✅ |
| **CP003** | 配置加载流程 | `config.from_env()` | 100% ✅ |
| **CP004** | 应用配置管理 | `ApplicationManager.get_application()` | 95% 🟡 |
| **CP005** | Token 持久化 | `TokenStorageService.get_token()` | 90%+ ✅ |
| **CP006** | 并发锁获取 | `LockManager.acquire_lock()` | 85% 🟡 |
| **CP007** | 重试策略执行 | `RetryStrategy.execute()` | 95% ✅ |

**验证方法**:
```bash
# 生成关键路径覆盖率报告
pytest tests/ --cov=src/lark_service/core \
       --cov-report=html:htmlcov \
       --cov-report=term-missing

# 检查关键模块覆盖率
grep -A 5 "credential_pool.py" htmlcov/index.html
grep -A 5 "config.py" htmlcov/index.html
```

---

## 🧪 Fixtures 复用机制 (CHK128)

### 设计原则

1. **分层设计**: 基础 fixtures → 组合 fixtures → 测试专用 fixtures
2. **作用域优化**: 根据成本选择合适的 scope
3. **依赖注入**: fixtures 之间可以相互依赖
4. **清理机制**: 使用 yield 确保资源清理

### Fixtures 分层架构

```
┌─────────────────────────────────────┐
│   测试专用 Fixtures (function)       │  ← 特定测试场景
│   - specific_test_data             │
│   - mocked_api_response            │
└─────────────┬───────────────────────┘
              │ 依赖
              ▼
┌─────────────────────────────────────┐
│   组合 Fixtures (session/class)      │  ← 组合基础资源
│   - credential_pool                │
│   - initialized_db                 │
└─────────────┬───────────────────────┘
              │ 依赖
              ▼
┌─────────────────────────────────────┐
│   基础 Fixtures (session)           │  ← 最底层资源
│   - test_config                    │
│   - test_db_engine                 │
│   - test_app_id                    │
└─────────────────────────────────────┘
```

### 标准 Fixtures 定义

**`tests/conftest.py`** (全局 fixtures):

```python
"""Global test fixtures for all test modules."""
import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.models.application import ConfigBase
from lark_service.core.models.token_storage import Base


# ============================================================================
# 基础 Fixtures (session scope)
# ============================================================================

@pytest.fixture(scope="session")
def test_config() -> Config:
    """Provide test configuration (session-wide).
    
    使用临时数据库路径,避免污染开发环境。
    """
    return Config(
        config_encryption_key="test-key-for-testing-only-32bytes==",
        config_db_path=":memory:",  # SQLite 内存数据库
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="lark_service_test",
        postgres_user="test_user",
        postgres_password="test_password",
        log_level="DEBUG",
    )


@pytest.fixture(scope="session")
def test_db_engine(test_config: Config):
    """Provide PostgreSQL test database engine.
    
    使用 session scope 以减少数据库连接开销。
    """
    database_url = (
        f"postgresql://{test_config.postgres_user}:"
        f"{test_config.postgres_password}@"
        f"{test_config.postgres_host}:"
        f"{test_config.postgres_port}/"
        f"{test_config.postgres_db}"
    )
    engine = create_engine(database_url, echo=False)
    
    # 创建所有表
    Base.metadata.create_all(engine)
    
    yield engine
    
    # 清理: 删除所有表
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def test_app_id() -> str:
    """Provide standard test application ID."""
    return "cli_test12345678901234"


# ============================================================================
# 组合 Fixtures (class/function scope)
# ============================================================================

@pytest.fixture(scope="function")
def clean_db(test_db_engine):
    """Provide clean database for each test.
    
    每个测试开始前清空数据,确保测试隔离。
    """
    # 清空所有表
    with test_db_engine.connect() as conn:
        conn.execute("DELETE FROM tokens")
        conn.execute("DELETE FROM user_cache")
        conn.execute("DELETE FROM user_auth_sessions")
        conn.commit()
    
    yield test_db_engine


@pytest.fixture
def credential_pool(test_config: Config, clean_db) -> CredentialPool:
    """Provide initialized CredentialPool.
    
    依赖 clean_db 确保每次测试都有干净的数据库。
    """
    pool = CredentialPool(test_config)
    return pool


@pytest.fixture
def test_application(test_config: Config):
    """Provide test application configuration.
    
    自动创建和清理测试应用。
    """
    from lark_service.core.storage.sqlite_storage import ApplicationManager
    
    manager = ApplicationManager(test_config)
    
    # 创建测试应用
    app = manager.create_application(
        app_id="cli_fixture_test_app",
        app_name="Test App",
        app_secret="test_secret_1234567890",
        description="Fixture test app",
    )
    
    yield app
    
    # 清理: 删除测试应用
    try:
        manager.delete_application(app.app_id)
    except Exception:
        pass


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_lark_api(mocker):
    """Mock Feishu API responses.
    
    提供标准的 API mock,避免真实 API 调用。
    """
    mock_response = {
        "code": 0,
        "msg": "success",
        "app_access_token": "t-test_token_12345",
        "expire": 7200,
    }
    
    return mocker.patch(
        "lark_service.core.credential_pool.CredentialPool._fetch_app_access_token",
        return_value="t-test_token_12345"
    )


@pytest.fixture
def mock_token_storage(mocker):
    """Mock token storage operations.
    
    加速测试,避免真实数据库操作。
    """
    from lark_service.core.models.token_storage import TokenStorage
    from datetime import datetime, timedelta
    
    mock_token = TokenStorage(
        app_id="cli_mock_app",
        token_type="app_access_token",
        token_value="t-mock_token",
        expires_at=datetime.now() + timedelta(hours=2),
    )
    
    return mocker.patch(
        "lark_service.core.storage.postgres_storage.TokenStorageService.get_token",
        return_value=mock_token
    )
```

### Fixtures 使用最佳实践

**1. 选择合适的 scope**:
```python
# ❌ 错误: 每次都创建数据库 (慢)
@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(...)
    return engine

# ✅ 正确: session scope,复用连接
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(...)
    yield engine
    engine.dispose()
```

**2. 使用 yield 清理资源**:
```python
# ✅ 推荐模式
@pytest.fixture
def temp_file():
    file_path = Path("/tmp/test_file.txt")
    file_path.write_text("test data")
    
    yield file_path  # 测试代码在这里执行
    
    # 清理代码 (无论测试成功或失败都会执行)
    if file_path.exists():
        file_path.unlink()
```

**3. Fixtures 依赖链**:
```python
# 基础 fixture
@pytest.fixture
def config():
    return Config(...)

# 依赖 config
@pytest.fixture
def storage(config):
    return Storage(config)

# 依赖 storage
@pytest.fixture
def pool(storage):
    return CredentialPool(storage)

# 测试使用最终 fixture
def test_something(pool):
    assert pool.get_token("xxx")
```

---

## 🔀 集成测试隔离策略 (CHK129)

### 隔离原则

1. **数据库隔离**: 每个测试使用独立的数据
2. **文件隔离**: 使用临时目录
3. **网络隔离**: Mock 外部 API 调用
4. **进程隔离**: 避免测试间状态污染

### 数据库隔离方案

**方案 A: 事务回滚 (推荐,快速)**

```python
# tests/integration/conftest.py
import pytest
from sqlalchemy.orm import Session

@pytest.fixture
def db_session(test_db_engine):
    """Provide database session with transaction rollback.
    
    每个测试在事务中执行,结束后回滚,确保数据隔离。
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    # 回滚事务,撤销所有数据变更
    session.close()
    transaction.rollback()
    connection.close()
```

**方案 B: 数据清理 (简单,适中)**

```python
@pytest.fixture
def isolated_db(test_db_engine):
    """Provide isolated database by cleaning data.
    
    测试前后清空所有表。
    """
    # 测试前清空
    with test_db_engine.connect() as conn:
        conn.execute("TRUNCATE tokens, user_cache, user_auth_sessions CASCADE")
        conn.commit()
    
    yield test_db_engine
    
    # 测试后清空 (可选,下次测试前也会清空)
    with test_db_engine.connect() as conn:
        conn.execute("TRUNCATE tokens, user_cache, user_auth_sessions CASCADE")
        conn.commit()
```

**方案 C: 独立数据库 (最隔离,慢)**

```python
@pytest.fixture
def isolated_db_per_test(test_config):
    """Create separate database for each test.
    
    最强隔离,但性能开销大,仅用于关键测试。
    """
    import uuid
    db_name = f"test_db_{uuid.uuid4().hex[:8]}"
    
    # 创建数据库
    admin_engine = create_engine(f"postgresql://admin@localhost/postgres")
    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(f"CREATE DATABASE {db_name}")
    
    # 创建表
    test_engine = create_engine(f"postgresql://admin@localhost/{db_name}")
    Base.metadata.create_all(test_engine)
    
    yield test_engine
    
    # 清理: 删除数据库
    test_engine.dispose()
    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(f"DROP DATABASE {db_name}")
```

### 文件隔离方案

```python
import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    """Provide isolated temporary directory.
    
    每个测试使用独立的临时目录。
    """
    temp_path = Path(tempfile.mkdtemp(prefix="lark_test_"))
    
    yield temp_path
    
    # 清理: 删除临时目录
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def isolated_config_db(temp_dir):
    """Provide isolated SQLite config database.
    
    使用临时目录中的 SQLite 文件。
    """
    db_path = temp_dir / "applications.db"
    config = Config(config_db_path=str(db_path), ...)
    
    yield config
    
    # 清理: 删除数据库文件 (temp_dir fixture 会一起清理)
```

### 网络隔离方案

```python
import pytest
import responses

@pytest.fixture
def mock_feishu_api():
    """Mock all Feishu API calls.
    
    使用 responses 库拦截所有 HTTP 请求。
    """
    with responses.RequestsMock() as rsps:
        # Mock token API
        rsps.add(
            responses.POST,
            "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
            json={
                "code": 0,
                "msg": "success",
                "app_access_token": "t-test_token",
                "expire": 7200,
            },
            status=200,
        )
        
        # Mock user info API
        rsps.add(
            responses.GET,
            "https://open.feishu.cn/open-apis/contact/v3/users/ou_xxxx",
            json={
                "code": 0,
                "msg": "success",
                "data": {
                    "user": {
                        "open_id": "ou_test",
                        "name": "Test User",
                    }
                }
            },
            status=200,
        )
        
        yield rsps


def test_api_call_with_mock(mock_feishu_api, credential_pool):
    """Test with mocked API."""
    token = credential_pool.get_token("cli_test")
    assert token == "t-test_token"
    
    # 验证 API 被调用
    assert len(mock_feishu_api.calls) == 1
```

### 并发测试隔离

```python
import pytest
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_token_acquisition(credential_pool):
    """Test concurrent token acquisition with proper isolation.
    
    确保并发测试不会互相干扰。
    """
    app_ids = [f"cli_test_concurrent_{i}" for i in range(10)]
    
    def get_token_for_app(app_id: str) -> str:
        return credential_pool.get_token(app_id)
    
    # 并发获取 Token
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_token_for_app, app_ids))
    
    # 验证所有结果
    assert len(results) == 10
    assert all(token for token in results)
```

---

## 📊 测试组织结构

### 目录结构

```
tests/
├── conftest.py                  # 全局 fixtures
├── unit/                        # 单元测试
│   ├── conftest.py              # 单元测试专用 fixtures
│   ├── core/
│   │   ├── test_config.py
│   │   ├── test_credential_pool.py
│   │   ├── test_lock_manager.py
│   │   └── test_retry.py
│   ├── cli/
│   │   └── test_app_commands.py
│   └── utils/
│       ├── test_logger.py
│       └── test_validators.py
├── integration/                 # 集成测试
│   ├── conftest.py              # 集成测试专用 fixtures
│   ├── test_credential_pool.py
│   ├── test_token_lifecycle.py
│   └── test_complete_flow.py
├── contract/                    # 契约测试
│   └── test_api_contracts.py
└── performance/                 # 性能测试
    └── test_concurrent_calls.py
```

### 测试命名规范

```python
# ✅ 好的命名 (描述测试目的)
def test_get_token_returns_valid_token_when_app_exists():
    pass

def test_get_token_raises_error_when_app_not_found():
    pass

def test_refresh_token_updates_database_with_new_token():
    pass

# ❌ 差的命名 (不清楚测试什么)
def test_get_token():
    pass

def test_error():
    pass

def test_1():
    pass
```

---

## ✅ 测试检查清单

### 单元测试检查

- [ ] 每个公共方法都有对应的测试
- [ ] 测试覆盖正常流程和异常流程
- [ ] 使用 Mock 隔离外部依赖
- [ ] 测试函数名称清晰描述测试目的
- [ ] 使用 fixtures 复用测试数据

### 集成测试检查

- [ ] 测试真实的数据库交互
- [ ] 测试模块间的集成点
- [ ] 使用隔离策略避免测试污染
- [ ] 测试完整的业务流程
- [ ] 验证并发场景

### 测试质量检查

- [ ] 测试运行时间 < 30秒 (单元测试)
- [ ] 测试运行时间 < 5分钟 (集成测试)
- [ ] 测试成功率 100%
- [ ] 无测试跳过 (skip)
- [ ] 无测试警告 (warnings)

---

## 🔧 常用测试命令

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行特定模块测试
pytest tests/unit/core/test_credential_pool.py

# 运行特定测试函数
pytest tests/unit/core/test_credential_pool.py::test_get_token_success

# 生成覆盖率报告
pytest tests/ --cov=src/lark_service --cov-report=html

# 运行失败的测试
pytest --lf

# 并行运行测试 (需要 pytest-xdist)
pytest tests/ -n auto

# 详细输出
pytest tests/ -v

# 显示打印输出
pytest tests/ -s
```

---

**维护者**: Lark Service Team  
**参考**: [testing-strategy.md](./testing-strategy.md)
