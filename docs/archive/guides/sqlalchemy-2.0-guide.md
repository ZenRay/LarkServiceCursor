# SQLAlchemy 2.0 使用指南

本项目使用 SQLAlchemy 2.0 现代语法,提供完整的类型安全和更好的开发体验。

## 目录

- [为什么使用 SQLAlchemy 2.0](#为什么使用-sqlalchemy-20)
- [核心概念](#核心概念)
- [模型定义](#模型定义)
- [类型注解](#类型注解)
- [常见模式](#常见模式)
- [迁移指南](#迁移指南)
- [最佳实践](#最佳实践)

---

## 为什么使用 SQLAlchemy 2.0

### 主要优势

1. **完美的类型推断** ✅
   - Mypy 完全理解模型类型
   - IDE 自动补全更准确
   - 重构更安全

2. **现代 Python 语法** ✅
   - 使用 `Mapped[T]` 类型注解
   - 支持 PEP 604 联合类型 (`str | None`)
   - 更简洁易读

3. **更好的错误提示** ✅
   - 编译期发现类型错误
   - 清晰的错误信息
   - 减少运行时bug

4. **向后兼容** ✅
   - 兼容 SQLAlchemy 1.4+
   - 不需要数据库迁移
   - 现有代码继续工作

---

## 核心概念

### 1. DeclarativeBase

使用 `DeclarativeBase` 替代传统的 `declarative_base()`。

```python
# ❌ 旧语法 (SQLAlchemy 1.x)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ✅ 新语法 (SQLAlchemy 2.0)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all models."""
    pass
```

**优势**:
- 可以添加通用方法和属性
- 更好的类型推断
- 符合 Python 类继承习惯

### 2. Mapped[T] 类型注解

使用 `Mapped[T]` 明确字段类型。

```python
# ❌ 旧语法
from sqlalchemy import Column, Integer, String

class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=True)

# ✅ 新语法
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100), default=None)
```

**类型含义**:
- `Mapped[int]` - 必需的整数字段
- `Mapped[str]` - 必需的字符串字段
- `Mapped[str | None]` - 可选的字符串字段
- `Mapped[datetime]` - 必需的日期时间字段

### 3. mapped_column()

使用 `mapped_column()` 替代 `Column()`。

```python
from sqlalchemy import String, Text, func
from sqlalchemy.orm import mapped_column

# 基本用法
id: Mapped[int] = mapped_column(primary_key=True)

# 指定列类型
name: Mapped[str] = mapped_column(String(100))
content: Mapped[str] = mapped_column(Text)

# 可选字段
description: Mapped[str | None] = mapped_column(Text, default=None)

# 默认值
status: Mapped[str] = mapped_column(String(16), default="active")
created_at: Mapped[datetime] = mapped_column(default=func.now())

# 唯一约束
email: Mapped[str] = mapped_column(String(100), unique=True)

# 索引
user_id: Mapped[str] = mapped_column(String(64), index=True)
```

---

## 模型定义

### 完整示例

```python
"""User model example."""

from datetime import datetime

from sqlalchemy import String, Text, Index, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class User(Base):
    """User account model.

    Attributes
    ----------
        id: Primary key
        username: Unique username
        email: User email address
        full_name: User's full name
        bio: User biography (optional)
        status: Account status
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Required fields
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))

    # Optional fields
    bio: Mapped[str | None] = mapped_column(Text, default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(512), default=None)

    # Status field with default
    status: Mapped[str] = mapped_column(String(16), default="active")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        onupdate=func.now()
    )

    # Table constraints
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_status", "status"),
    )

    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == "active"

    def __repr__(self) -> str:
        """String representation."""
        return f"<User(id={self.id}, username='{self.username}')>"
```

---

## 类型注解

### 基本类型映射

| Python 类型 | SQLAlchemy 类型 | 示例 |
|------------|----------------|------|
| `int` | `Integer` | `id: Mapped[int]` |
| `str` | `String`, `Text` | `name: Mapped[str]` |
| `float` | `Float` | `price: Mapped[float]` |
| `bool` | `Boolean` | `is_active: Mapped[bool]` |
| `datetime` | `DateTime` | `created_at: Mapped[datetime]` |
| `date` | `Date` | `birth_date: Mapped[date]` |
| `bytes` | `LargeBinary` | `data: Mapped[bytes]` |

### 可选字段

使用 `T | None` 表示可选字段:

```python
# 可选字符串
description: Mapped[str | None] = mapped_column(Text, default=None)

# 可选整数
age: Mapped[int | None] = mapped_column(default=None)

# 可选日期时间
deleted_at: Mapped[datetime | None] = mapped_column(default=None)
```

### 关系字段

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # 多对一关系
    user: Mapped["User"] = relationship(back_populates="posts")

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))

    # 一对多关系
    posts: Mapped[list["Post"]] = relationship(back_populates="user")
```

---

## 常见模式

### 1. 自增主键

```python
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
```

### 2. UUID 主键

```python
from uuid import uuid4

id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
```

### 3. 时间戳字段

```python
from datetime import datetime
from sqlalchemy import func

# 创建时间 (自动设置)
created_at: Mapped[datetime] = mapped_column(default=func.now())

# 更新时间 (自动更新)
updated_at: Mapped[datetime] = mapped_column(
    default=func.now(),
    onupdate=func.now()
)
```

### 4. 枚举字段

```python
from enum import Enum

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default=UserStatus.ACTIVE.value)
```

### 5. JSON 字段

```python
from sqlalchemy import JSON

class Config(Base):
    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    settings: Mapped[dict] = mapped_column(JSON)
```

### 6. 加密字段

```python
from sqlalchemy import Text

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    app_secret: Mapped[str] = mapped_column(Text)  # Encrypted with Fernet

    def get_decrypted_secret(self, key: bytes) -> str:
        """Decrypt and return secret."""
        from cryptography.fernet import Fernet
        f = Fernet(key)
        return f.decrypt(self.app_secret.encode()).decode()
```

### 7. 复合唯一约束

```python
from sqlalchemy import UniqueConstraint

class TokenStorage(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    app_id: Mapped[str] = mapped_column(String(64))
    token_type: Mapped[str] = mapped_column(String(32))
    token_value: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("app_id", "token_type", name="uq_app_token_type"),
    )
```

### 8. 索引

```python
from sqlalchemy import Index

class UserCache(Base):
    __tablename__ = "user_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    app_id: Mapped[str] = mapped_column(String(64))
    open_id: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column()

    __table_args__ = (
        Index("idx_user_cache_app_open", "app_id", "open_id"),
        Index("idx_user_cache_expires", "expires_at"),
    )
```

---

## 迁移指南

### 从 SQLAlchemy 1.x 迁移

#### 步骤 1: 更新导入

```python
# 旧
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

# 新
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
```

#### 步骤 2: 创建 Base 类

```python
# 旧
Base = declarative_base()

# 新
class Base(DeclarativeBase):
    """Base class for models."""
    pass
```

#### 步骤 3: 更新字段定义

```python
# 旧
class User(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=True)

# 新
class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100), default=None)
```

#### 步骤 4: 运行测试

```bash
# 确保所有测试通过
pytest tests/

# 检查类型
mypy src/
```

---

## 最佳实践

### 1. 始终使用类型注解

```python
# ✅ 好 - 清晰的类型
id: Mapped[int] = mapped_column(primary_key=True)
name: Mapped[str] = mapped_column(String(100))

# ❌ 差 - 缺少类型注解
id = mapped_column(Integer, primary_key=True)
```

### 2. 可选字段使用 `| None`

```python
# ✅ 好 - 明确表示可选
email: Mapped[str | None] = mapped_column(String(100), default=None)

# ❌ 差 - 使用旧式 Optional
from typing import Optional
email: Mapped[Optional[str]] = mapped_column(String(100))
```

### 3. 为所有模型添加 Docstring

```python
class User(Base):
    """User account model.

    Attributes
    ----------
        id: Primary key
        username: Unique username
        email: User email address
    """
    __tablename__ = "users"
    # ...
```

### 4. 使用有意义的表名和列名

```python
# ✅ 好
__tablename__ = "user_auth_sessions"

# ❌ 差
__tablename__ = "uas"
```

### 5. 添加索引到频繁查询的字段

```python
class User(Base):
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
```

### 6. 使用 `func.now()` 而不是 `datetime.now()`

```python
# ✅ 好 - 数据库级别的时间戳
created_at: Mapped[datetime] = mapped_column(default=func.now())

# ❌ 差 - Python 级别的时间戳 (可能有时区问题)
created_at: Mapped[datetime] = mapped_column(default=datetime.now)
```

### 7. 为方法添加类型注解

```python
class User(Base):
    status: Mapped[str] = mapped_column(String(16))

    def is_active(self) -> bool:  # ✅ 有返回类型
        """Check if user is active."""
        return self.status == "active"
```

---

## Mypy 配置

在 `pyproject.toml` 中配置 mypy:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# SQLAlchemy 插件
plugins = ["sqlalchemy.ext.mypy.plugin"]

# 忽略某些第三方库
[[tool.mypy.overrides]]
module = [
    "lark_oapi.*",
]
ignore_missing_imports = true
```

---

## 常见问题

### Q: 为什么使用 `Mapped[T]` 而不是直接用类型注解?

A: `Mapped[T]` 是 SQLAlchemy 的特殊类型,它告诉 ORM 这是一个数据库字段,不仅仅是普通的类属性。这样 SQLAlchemy 可以正确处理它。

### Q: 可以混用新旧语法吗?

A: 可以,但不推荐。建议统一使用新语法以获得最佳类型检查效果。

### Q: 需要修改数据库吗?

A: 不需要!新语法只是 Python 代码层面的改进,不影响数据库 schema。

### Q: 性能有影响吗?

A: 没有。运行时性能完全相同,只是开发体验更好。

---

## 参考资料

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [SQLAlchemy 2.0 Migration Guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [Mapped Column Documentation](https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.mapped_column)
- [DeclarativeBase Documentation](https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase)

---

## 项目中的示例

查看项目中的实际使用:

- `src/lark_service/core/models/application.py` - 应用配置模型
- `src/lark_service/core/models/token_storage.py` - Token 存储模型
- `src/lark_service/core/models/user_cache.py` - 用户缓存模型
- `src/lark_service/core/models/auth_session.py` - 认证会话模型

---

**更新日期**: 2026-01-15
**SQLAlchemy 版本**: 2.0+
**Python 版本**: 3.12+
