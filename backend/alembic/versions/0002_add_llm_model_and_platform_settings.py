"""Add llm_model to sessions and create platform_settings table

Revision ID: 0002
Revises: 0001
Create Date: 2025-03-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add llm_model column to sessions table
    op.add_column(
        "sessions",
        sa.Column("llm_model", sa.String(100), nullable=False, server_default="gemini"),
    )

    # Create platform_settings table
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.String(1000), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_settings_key", "platform_settings", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_platform_settings_key", table_name="platform_settings")
    op.drop_table("platform_settings")
    op.drop_column("sessions", "llm_model")
