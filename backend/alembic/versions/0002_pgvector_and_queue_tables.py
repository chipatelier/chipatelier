"""pgvector extension and queue_priority column on runs table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-13

Changes:
  - Installs pgvector extension (zero-cost Phase 1 setup; Phase 3 AI adds vector columns)
  - Adds queue_priority TEXT column to runs table (values: 'normal' | 'high_priority')
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector: zero-cost extension install now, Phase 3 AI adds vector columns
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # queue_priority tracks whether this run goes to high_priority or normal queue
    # Valid values: 'high_priority' (instructor/admin runs), 'normal' (student runs)
    op.execute(
        "ALTER TABLE runs ADD COLUMN queue_priority TEXT NOT NULL DEFAULT 'normal'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE runs DROP COLUMN queue_priority")
    op.execute("DROP EXTENSION IF EXISTS vector")
