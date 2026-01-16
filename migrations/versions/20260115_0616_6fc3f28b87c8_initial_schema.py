"""initial_schema

Revision ID: 6fc3f28b87c8
Revises:
Create Date: 2026-01-15 06:16:30.053437+00:00

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6fc3f28b87c8"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema for tokens, user_cache, and user_auth_sessions tables."""
    # Create tokens table
    op.create_table(
        "tokens",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("token_type", sa.String(length=32), nullable=False),
        sa.Column("token_value", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id", "token_type", name="uq_app_token_type"),
    )
    op.create_index("idx_tokens_expires", "tokens", ["expires_at"], unique=False)

    # Create user_cache table
    op.create_table(
        "user_cache",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("open_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("union_id", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=128), nullable=True),
        sa.Column("mobile", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("department_ids", sa.String(length=512), nullable=True),
        sa.Column("employee_no", sa.String(length=64), nullable=True),
        sa.Column("cached_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id", "open_id", name="uq_app_open_id"),
    )
    op.create_index("idx_user_cache_expires", "user_cache", ["expires_at"], unique=False)
    op.create_index("idx_user_cache_user_id", "user_cache", ["user_id"], unique=False)
    op.create_index("idx_user_cache_union_id", "user_cache", ["union_id"], unique=False)

    # Create user_auth_sessions table
    op.create_table(
        "user_auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("auth_method", sa.String(length=32), nullable=False),
        sa.Column("redirect_uri", sa.String(length=512), nullable=True),
        sa.Column("open_id", sa.String(length=64), nullable=True),
        sa.Column("user_access_token", sa.String(length=512), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_session_id"),
    )
    op.create_index("idx_auth_session_state", "user_auth_sessions", ["state"], unique=False)
    op.create_index("idx_auth_session_expires", "user_auth_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    """Drop all tables created in upgrade."""
    op.drop_index("idx_auth_session_expires", table_name="user_auth_sessions")
    op.drop_index("idx_auth_session_state", table_name="user_auth_sessions")
    op.drop_table("user_auth_sessions")

    op.drop_index("idx_user_cache_union_id", table_name="user_cache")
    op.drop_index("idx_user_cache_user_id", table_name="user_cache")
    op.drop_index("idx_user_cache_expires", table_name="user_cache")
    op.drop_table("user_cache")

    op.drop_index("idx_tokens_expires", table_name="tokens")
    op.drop_table("tokens")
