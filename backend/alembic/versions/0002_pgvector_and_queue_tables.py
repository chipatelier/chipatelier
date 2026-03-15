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
    # pgvector: best-effort install — skip silently if not available on this host.
    # Phase 3 AI features require it; Phase 1/2 run fine without it.
    op.execute("""
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            NULL;  -- pgvector not installed; skipped
        END
        $$
    """)

    # queue_priority tracks whether this run goes to high_priority or normal queue
    # Valid values: 'high_priority' (instructor/admin runs), 'normal' (student runs)
    op.execute(
        "ALTER TABLE runs ADD COLUMN IF NOT EXISTS queue_priority TEXT NOT NULL DEFAULT 'normal'"
    )

    # celery_task_id stores the Celery async result ID for job cancellation
    op.execute(
        "ALTER TABLE runs ADD COLUMN IF NOT EXISTS celery_task_id TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE runs DROP COLUMN IF EXISTS celery_task_id")
    op.execute("ALTER TABLE runs DROP COLUMN IF EXISTS queue_priority")
    op.execute("DROP EXTENSION IF EXISTS vector")
