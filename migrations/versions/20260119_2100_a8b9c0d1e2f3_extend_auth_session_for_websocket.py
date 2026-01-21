"""extend_auth_session_for_websocket

Extend user_auth_sessions table to support WebSocket-based user authorization.

Adds fields for user information storage and improves indexing for query performance.

Revision ID: a8b9c0d1e2f3
Revises: 6fc3f28b87c8
Create Date: 2026-01-19 21:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "6fc3f28b87c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend user_auth_sessions table for WebSocket authorization.

    Changes:
    1. Add user_id column (to store user_id separate from open_id)
    2. Add union_id column (cross-app unique identifier)
    3. Add user_name column (user display name)
    4. Add mobile column (user phone number, will be encrypted)
    5. Add email column (user email address)
    6. Modify user_access_token column to TEXT type (was VARCHAR(512))
    7. Add composite index on (app_id, user_id) for fast user lookup
    8. Add partial index on token_expires_at for token expiry checks
    9. Add index on created_at for session history queries
    10. Add check constraints for data integrity
    """

    # Add new columns for user information
    op.add_column(
        "user_auth_sessions",
        sa.Column(
            "user_id",
            sa.String(length=64),
            nullable=True,
            comment="Feishu user ID (enterprise unique)",
        ),
    )
    op.add_column(
        "user_auth_sessions",
        sa.Column(
            "union_id",
            sa.String(length=64),
            nullable=True,
            comment="Feishu union ID (cross-app unique)",
        ),
    )
    op.add_column(
        "user_auth_sessions",
        sa.Column("user_name", sa.String(length=128), nullable=True, comment="User display name"),
    )
    op.add_column(
        "user_auth_sessions",
        sa.Column(
            "mobile", sa.String(length=32), nullable=True, comment="User mobile number (encrypted)"
        ),
    )
    op.add_column(
        "user_auth_sessions",
        sa.Column("email", sa.String(length=128), nullable=True, comment="User email address"),
    )

    # Modify user_access_token column type from VARCHAR(512) to TEXT
    # This allows for longer tokens and encrypted tokens
    op.alter_column(
        "user_auth_sessions",
        "user_access_token",
        type_=sa.Text(),
        existing_type=sa.String(length=512),
        existing_nullable=True,
        comment="User access token (encrypted with pg_crypto)",
    )

    # Add composite index for fast user lookup (app_id, user_id)
    op.create_index(
        "idx_auth_session_user",
        "user_auth_sessions",
        ["app_id", "user_id"],
        unique=False,
    )

    # Add partial index on token_expires_at (only for non-null values)
    # This speeds up queries for active tokens
    op.create_index(
        "idx_auth_session_token_expires",
        "user_auth_sessions",
        ["token_expires_at"],
        unique=False,
        postgresql_where=sa.text("token_expires_at IS NOT NULL"),
    )

    # Add index on created_at for session history queries
    op.create_index(
        "idx_auth_session_created",
        "user_auth_sessions",
        [sa.text("created_at DESC")],
        unique=False,
    )

    # Add check constraints for data integrity
    # Constraint 1: State must be one of valid values
    op.create_check_constraint(
        "chk_auth_session_state",
        "user_auth_sessions",
        sa.text("state IN ('pending', 'completed', 'expired')"),
    )

    # Constraint 2: Auth method must be one of valid values
    op.create_check_constraint(
        "chk_auth_session_auth_method",
        "user_auth_sessions",
        sa.text("auth_method IN ('websocket_card', 'oauth', 'http_callback')"),
    )

    # Constraint 3: Completed sessions must have completed_at timestamp
    op.create_check_constraint(
        "chk_auth_session_completed_at",
        "user_auth_sessions",
        sa.text(
            "(state = 'completed' AND completed_at IS NOT NULL) OR "
            "(state != 'completed' AND completed_at IS NULL)"
        ),
    )

    # Constraint 4: Completed sessions must have token and token expiry
    op.create_check_constraint(
        "chk_auth_session_token",
        "user_auth_sessions",
        sa.text(
            "(state = 'completed' AND user_access_token IS NOT NULL AND token_expires_at IS NOT NULL) OR "
            "(state != 'completed')"
        ),
    )


def downgrade() -> None:
    """Reverse the changes made in upgrade.

    This will:
    1. Drop all new check constraints
    2. Drop all new indexes
    3. Revert user_access_token column type
    4. Drop all new columns
    """

    # Drop check constraints
    op.drop_constraint("chk_auth_session_token", "user_auth_sessions", type_="check")
    op.drop_constraint("chk_auth_session_completed_at", "user_auth_sessions", type_="check")
    op.drop_constraint("chk_auth_session_auth_method", "user_auth_sessions", type_="check")
    op.drop_constraint("chk_auth_session_state", "user_auth_sessions", type_="check")

    # Drop indexes
    op.drop_index("idx_auth_session_created", table_name="user_auth_sessions")
    op.drop_index("idx_auth_session_token_expires", table_name="user_auth_sessions")
    op.drop_index("idx_auth_session_user", table_name="user_auth_sessions")

    # Revert user_access_token column type
    op.alter_column(
        "user_auth_sessions",
        "user_access_token",
        type_=sa.String(length=512),
        existing_type=sa.Text(),
        existing_nullable=True,
    )

    # Drop new columns
    op.drop_column("user_auth_sessions", "email")
    op.drop_column("user_auth_sessions", "mobile")
    op.drop_column("user_auth_sessions", "user_name")
    op.drop_column("user_auth_sessions", "union_id")
    op.drop_column("user_auth_sessions", "user_id")
