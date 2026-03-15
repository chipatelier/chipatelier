"""Courses, course_enrollments, assignments, and submissions tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15

Changes:
  - Creates courses table with enrollment_code unique index
  - Creates course_enrollments table with (course_id, user_id) unique constraint
  - Creates assignments table with JSONB locked_params, editable_params, checkpoint_rules
  - Creates submissions table with JSONB checkpoint_results and grading_status
  - Adds functional B-tree index idx_runs_wns_numeric for leaderboard ordering
  - Adds composite index idx_submissions_score for leaderboard ranking
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # courses
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE courses (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instructor_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            term            TEXT,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            enrollment_code TEXT UNIQUE NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_courses_enrollment_code "
        "ON courses(enrollment_code)"
    )

    # ------------------------------------------------------------------ #
    # course_enrollments
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE course_enrollments (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            course_id   UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (course_id, user_id)
        )
    """)

    # ------------------------------------------------------------------ #
    # assignments
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE assignments (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            course_id        UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            title            TEXT NOT NULL,
            description      TEXT,
            pdk              TEXT NOT NULL DEFAULT 'sky130hd',
            target_stage     TEXT NOT NULL DEFAULT 'route',
            locked_params    JSONB NOT NULL DEFAULT '{}',
            editable_params  JSONB NOT NULL DEFAULT '[]',
            checkpoint_rules JSONB NOT NULL DEFAULT '{}',
            due_at           TIMESTAMPTZ,
            is_open          BOOLEAN NOT NULL DEFAULT FALSE,
            orfs_version     TEXT,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ------------------------------------------------------------------ #
    # submissions
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE submissions (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            assignment_id       UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            run_id              UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            checkpoint_results  JSONB,
            score               NUMERIC,
            grading_status      TEXT NOT NULL DEFAULT 'pending',
            submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ------------------------------------------------------------------ #
    # Indexes
    #
    # Functional B-tree for leaderboard ordering with ::numeric cast
    # (GIN cannot support ORDER BY — must be B-tree with explicit cast)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_wns_numeric ON runs "
        "(((ppa->>'worst_negative_slack')::numeric))"
    )
    # Composite index for leaderboard score ordering per assignment
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_submissions_score ON submissions "
        "(assignment_id, score DESC NULLS LAST)"
    )
    # ------------------------------------------------------------------ #


def downgrade() -> None:
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_submissions_score")
    op.execute("DROP INDEX IF EXISTS idx_runs_wns_numeric")
    op.execute("DROP INDEX IF EXISTS idx_courses_enrollment_code")

    # Drop tables in reverse dependency order
    op.execute("DROP TABLE IF EXISTS submissions")
    op.execute("DROP TABLE IF EXISTS assignments")
    op.execute("DROP TABLE IF EXISTS course_enrollments")
    op.execute("DROP TABLE IF EXISTS courses")
