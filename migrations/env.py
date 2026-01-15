"""Alembic 环境配置文件"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 导入所有模型以便 Alembic 检测
# 注意: 需要在实际实现模型后取消注释
# from lark_service.core.models.token_storage import Base as TokenBase
# from lark_service.core.models.user_cache import Base as UserBase
# from lark_service.core.models.auth_session import Base as AuthBase

# Alembic Config 对象
config = context.config

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# 从环境变量读取数据库连接 URL
def get_url() -> str:
    """从环境变量构建数据库连接 URL"""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "lark_service")
    user = os.getenv("POSTGRES_USER", "lark")
    password = os.getenv("POSTGRES_PASSWORD", "lark_password_123")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


# 覆盖配置文件中的 URL
config.set_main_option("sqlalchemy.url", get_url())

# 目标元数据 (所有模型的 Base.metadata)
# 注意: 需要在实际实现模型后设置
# target_metadata = TokenBase.metadata
target_metadata = None  # 暂时设置为 None


def run_migrations_offline() -> None:
    """在离线模式下运行迁移

    这种模式只生成 SQL 脚本,不实际连接数据库
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在在线模式下运行迁移

    这种模式会实际连接数据库并执行迁移
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
