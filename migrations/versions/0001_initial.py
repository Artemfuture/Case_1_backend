"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("program", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("status_label", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("issues", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("extracted", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "check_documents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("check_id", sa.String(length=36), sa.ForeignKey("checks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("detected_type", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("size_kb", sa.Float(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_check_documents_check_id"), "check_documents", ["check_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_check_documents_check_id"), table_name="check_documents")
    op.drop_table("check_documents")
    op.drop_table("checks")