"""Initial migration - create all tables

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "archived", "deleted", name="session_status_enum"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    # Messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_index("ix_messages_user_id", "messages", ["user_id"])

    # Sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("pdf", "pptx", "image", "txt", "text", "url", name="source_type_enum"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("local_path", sa.String(1000), nullable=True),
        sa.Column(
            "ingest_status",
            sa.Enum("pending", "processing", "complete", "failed", name="ingest_status_enum"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
    )
    op.create_index("ix_sources_session_id", "sources", ["session_id"])
    op.create_index("ix_sources_user_id", "sources", ["user_id"])

    # Source chunks metadata table
    op.create_table(
        "source_chunks_metadata",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("vector_ref", sa.String(255), nullable=True),
        sa.Column("chunk_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
    )
    op.create_index("ix_source_chunks_source_id", "source_chunks_metadata", ["source_id"])

    # Skills table
    op.create_table(
        "skills",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("skill_metadata_json", JSONB, nullable=True),
        sa.Column("install_status", sa.String(50), nullable=True),
        sa.Column("validation_status", sa.String(50), nullable=False),
        sa.Column("validation_errors", JSONB, nullable=True),
        sa.Column("is_globally_enabled", sa.Boolean(), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_user_id", "skills", ["user_id"])

    # Session skills table
    op.create_table(
        "session_skills",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.UniqueConstraint("session_id", "skill_id", name="uq_session_skill"),
    )

    # Agent runs table
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_message_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("current_plan", JSONB, nullable=True),
        sa.Column("final_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"]),
    )
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])

    # Tool runs table
    op.create_table(
        "tool_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_run_id", sa.String(), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("input_json", JSONB, nullable=True),
        sa.Column("output_json", JSONB, nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
    )

    # Artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("artifact_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
    )
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("tool_runs")
    op.drop_table("agent_runs")
    op.drop_table("session_skills")
    op.drop_table("skills")
    op.drop_table("source_chunks_metadata")
    op.drop_table("sources")
    op.drop_table("messages")
    op.drop_table("sessions")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS session_status_enum")
    op.execute("DROP TYPE IF EXISTS source_type_enum")
    op.execute("DROP TYPE IF EXISTS ingest_status_enum")
