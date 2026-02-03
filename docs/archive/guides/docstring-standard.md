# Docstring 编写标准

**版本**: 1.0.0
**更新时间**: 2026-01-15
**适用范围**: 所有 Python 代码

---

## 📋 需求概述 (FR-096, FR-097, FR-098, CHK134)

### 强制要求 (MUST)

- ✅ **FR-096**: 所有公共 API(模块、类、函数)MUST 包含 Docstring,覆盖率 100%
- ✅ **FR-097**: Docstring MUST 采用 Google 风格
- ✅ **FR-098**: 私有方法 SHOULD 包含 Docstring,至少说明用途和参数

### Docstring 必需部分

1. **功能简述** (单行,MUST)
2. **详细说明** (可选,复杂 API 推荐)
3. **Args** (参数列表,MUST if有参数)
4. **Returns** (返回值,MUST if有返回)
5. **Raises** (异常,MUST if抛出异常)
6. **Example** (使用示例,可选,推荐用于复杂 API)

---

## 📐 Google 风格 Docstring

### 模块 Docstring

```python
"""Short description of the module.

Detailed description of what this module does, its purpose,
and any important notes about usage.

Example:
    >>> from lark_service import core
    >>> config = core.Config()
"""
```

### 类 Docstring

```python
class CredentialPool:
    """Manages Feishu API credentials with automatic refresh.

    The CredentialPool handles token acquisition, caching, and
    automatic refresh for multiple applications. It supports
    both app_access_token and tenant_access_token.

    Attributes:
        config: Configuration object
        token_storage: Token persistence layer
        lock_manager: Concurrency control manager

    Example:
        >>> pool = CredentialPool(config)
        >>> token = pool.get_token(app_id="cli_12345678")
        >>> print(token)
        't-xxxxx...'
    """
```

### 函数/方法 Docstring (完整示例)

```python
def get_token(
    self,
    app_id: str,
    token_type: str = "app_access_token",
    force_refresh: bool = False,
) -> str:
    """Get access token for specified application.

    Retrieves token from cache if available and not expired,
    otherwise fetches new token from Feishu API. Supports
    automatic refresh when token is about to expire.

    Args:
        app_id: Application ID (format: cli_[16-32 alphanumeric])
        token_type: Type of token to retrieve.
            Supported values:
            - "app_access_token": Application access token (default)
            - "tenant_access_token": Tenant access token
        force_refresh: If True, bypass cache and fetch new token.
            Default: False

    Returns:
        Valid access token string (format: t-xxxxxx...)

    Raises:
        ValidationError: If app_id format is invalid
        TokenAcquisitionError: If failed to fetch token from API
            after 3 retries
        ConfigError: If application not found in database

    Example:
        >>> pool = CredentialPool(config)
        >>>
        >>> # Get app token (with auto-refresh)
        >>> token = pool.get_token("cli_12345678")
        >>>
        >>> # Force refresh
        >>> new_token = pool.get_token(
        ...     "cli_12345678",
        ...     force_refresh=True
        ... )
        >>>
        >>> # Get tenant token
        >>> tenant_token = pool.get_token(
        ...     "cli_12345678",
        ...     token_type="tenant_access_token"
        ... )

    Note:
        - Token is cached in PostgreSQL for 2 hours
        - Automatic refresh triggered at 90% of lifetime
        - Concurrent refresh is protected by distributed lock
    """
```

### 简化版 Docstring (简单函数)

```python
def validate_app_id(app_id: str) -> None:
    """Validate application ID format.

    Args:
        app_id: Application ID to validate

    Raises:
        ValidationError: If format is invalid
    """
```

### 私有方法 Docstring

```python
def _fetch_app_access_token(self, app_id: str) -> str:
    """Fetch app access token from Feishu API.

    Internal method, not for public use.

    Args:
        app_id: Application ID

    Returns:
        Raw token string from API response

    Raises:
        TokenAcquisitionError: If API call fails
    """
```

---

## 🎯 不同场景的 Docstring

### 1. 简单工具函数

```python
def mask_secret(value: str, prefix_len: int = 4) -> str:
    """Mask sensitive string for logging.

    Args:
        value: Original secret value
        prefix_len: Number of prefix characters to show

    Returns:
        Masked string (e.g., "test****")

    Example:
        >>> mask_secret("test_secret_12345")
        'test****'
    """
```

### 2. 数据类

```python
@dataclass
class Config:
    """Configuration for Lark Service.

    Loads configuration from environment variables and provides
    validation and default values.

    Attributes:
        config_encryption_key: Fernet key for encrypting secrets
        config_db_path: Path to SQLite configuration database
        postgres_host: PostgreSQL server hostname
        postgres_port: PostgreSQL server port (default: 5432)
        log_level: Logging level (default: "INFO")

    Raises:
        ConfigError: If required environment variables are missing

    Example:
        >>> config = Config.from_env()
        >>> print(config.log_level)
        'INFO'
    """
```

### 3. 异常类

```python
class TokenAcquisitionError(Exception):
    """Raised when token acquisition fails.

    This error indicates that the system failed to obtain
    a valid token from Feishu API after all retry attempts.

    Attributes:
        message: Error description
        app_id: Application ID that failed
        token_type: Type of token being requested
        retry_count: Number of retries attempted

    Example:
        >>> raise TokenAcquisitionError(
        ...     "Failed after 3 retries",
        ...     app_id="cli_12345678",
        ...     token_type="app_access_token",
        ...     retry_count=3
        ... )
    """
```

### 4. 生成器函数

```python
def iterate_tokens(
    self,
    app_id: str | None = None
) -> Generator[TokenStorage, None, None]:
    """Iterate over tokens in storage.

    Yields tokens one by one, optionally filtered by app_id.

    Args:
        app_id: Filter by application ID (optional)

    Yields:
        TokenStorage: Token object

    Example:
        >>> for token in storage.iterate_tokens():
        ...     print(token.token_type)
        'app_access_token'
        'tenant_access_token'
    """
```

### 5. 异步方法

```python
async def send_message_async(
    self,
    receive_id: str,
    msg_type: str,
    content: str,
) -> StandardResponse:
    """Send message asynchronously.

    Non-blocking message sending using asyncio.

    Args:
        receive_id: User or group ID
        msg_type: Message type ("text", "post", "interactive")
        content: Message content (JSON string or text)

    Returns:
        Standard response with message ID

    Raises:
        APIError: If message sending fails

    Example:
        >>> import asyncio
        >>>
        >>> async def main():
        ...     response = await client.send_message_async(
        ...         "ou_xxxx",
        ...         "text",
        ...         "Hello"
        ...     )
        ...     print(response.data["message_id"])
        >>>
        >>> asyncio.run(main())
    """
```

---

## ✅ Docstring 检查清单

在编写完 Docstring 后,检查以下项目:

### 必需项 (MUST)

- [ ] 是否有功能简述 (单行)?
- [ ] 参数列表是否完整 (Args)?
- [ ] 返回值是否说明 (Returns)?
- [ ] 可能的异常是否列出 (Raises)?
- [ ] 类型注解是否完整?

### 推荐项 (SHOULD)

- [ ] 复杂 API 是否有使用示例 (Example)?
- [ ] 是否有详细说明 (多行)?
- [ ] 是否有重要提示 (Note/Warning)?
- [ ] 参数是否有默认值说明?
- [ ] 返回值格式是否明确?

### 质量项 (NICE TO HAVE)

- [ ] 示例代码是否可运行?
- [ ] 是否有性能提示?
- [ ] 是否有线程安全说明?
- [ ] 是否有相关 API 链接?

---

## 🚫 常见错误

### ❌ 错误示例 1: 缺少参数说明

```python
def get_token(self, app_id: str) -> str:
    """Get token."""  # ❌ 太简略,没有参数和返回值说明
```

### ✅ 正确示例 1

```python
def get_token(self, app_id: str) -> str:
    """Get access token for specified application.

    Args:
        app_id: Application ID

    Returns:
        Access token string
    """
```

---

### ❌ 错误示例 2: 缺少异常说明

```python
def validate_app_id(app_id: str) -> None:
    """Validate app ID."""  # ❌ 没有说明会抛出什么异常
    if not app_id.startswith("cli_"):
        raise ValidationError("Invalid format")
```

### ✅ 正确示例 2

```python
def validate_app_id(app_id: str) -> None:
    """Validate application ID format.

    Args:
        app_id: Application ID to validate

    Raises:
        ValidationError: If format is invalid
    """
```

---

### ❌ 错误示例 3: 使用错误的风格

```python
def send_message(msg: str) -> bool:
    """
    Send a message.

    :param msg: Message content
    :return: True if success
    :raises: APIError
    """  # ❌ 使用了 Sphinx 风格,不是 Google 风格
```

### ✅ 正确示例 3

```python
def send_message(msg: str) -> bool:
    """Send message to user.

    Args:
        msg: Message content

    Returns:
        True if message sent successfully

    Raises:
        APIError: If API call fails
    """
```

---

## 🔧 工具支持

### Mypy 类型检查

```bash
# 检查类型注解完整性
mypy src/lark_service/ --strict
```

### Pydocstyle 文档检查

```bash
# 安装
pip install pydocstyle

# 检查 Docstring 规范
pydocstyle src/lark_service/

# 或在 pyproject.toml 中配置
[tool.pydocstyle]
convention = "google"
```

### IDE 支持

**VSCode**:
- 安装 "Python Docstring Generator" 扩展
- 快捷键: 输入 `"""` 后按 Enter 自动生成模板

**PyCharm**:
- Settings → Tools → Python Integrated Tools → Docstring format → Google
- 快捷键: `"""` + Enter 自动生成

---

## 📚 参考资料

- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [PEP 257 - Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)

---

**维护者**: Lark Service Team
**反馈**: 如有疑问或建议,请提交 Issue
