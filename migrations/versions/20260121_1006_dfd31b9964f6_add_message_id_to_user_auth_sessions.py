"""add message_id to user_auth_sessions

Revision ID: dfd31b9964f6
Revises: a8b9c0d1e2f3
Create Date: 2026-01-21 10:06:51.308953+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfd31b9964f6"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add message_id column to user_auth_sessions table
    op.add_column(
        "user_auth_sessions", sa.Column("message_id", sa.String(length=128), nullable=True)
    )


def downgrade() -> None:
    # Remove message_id column from user_auth_sessions table
    op.drop_column("user_auth_sessions", "message_id")
