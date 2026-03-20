# backend/alembic/versions/0004_project_file_versioning.py
"""Add config_version, verilog_version, latest_source_path to projects.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("config_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("projects", sa.Column("verilog_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("projects", sa.Column("latest_source_path", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "latest_source_path")
    op.drop_column("projects", "verilog_version")
    op.drop_column("projects", "config_version")
