"""Initial schema — users, projects, runs, vnc_sessions with indexes.

Revision ID: 0001
Revises: (none — initial migration)
Create Date: 2026-03-13
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ------------------------------------------------------------------ #
    # users
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email           TEXT UNIQUE NOT NULL,
            display_name    TEXT,
            role            TEXT NOT NULL DEFAULT 'student',
            password_hash   TEXT,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            storage_used_bytes BIGINT NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login_at   TIMESTAMPTZ
        )
    """)

    # ------------------------------------------------------------------ #
    # projects
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE projects (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            pdk             TEXT NOT NULL DEFAULT 'sky130hd',
            storage_bytes   BIGINT NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # ------------------------------------------------------------------ #
    # runs
    # ppa   — PPA metrics only: WNS, TNS, DRC, power, area, wirelength
    # config — config.mk snapshot: CLOCK_PERIOD, CORE_UTILIZATION, etc.
    # These are SEPARATE JSONB columns by design (simplifies filtering).
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE runs (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            status              TEXT NOT NULL DEFAULT 'queued',
            target_stage        TEXT,
            stage_completed     TEXT,
            is_submitted        BOOLEAN NOT NULL DEFAULT FALSE,
            is_starred          BOOLEAN NOT NULL DEFAULT FALSE,
            notes               TEXT,
            artifact_path       TEXT,
            ppa                 JSONB,
            config              JSONB,
            stage_metrics       JSONB,
            storage_bytes       BIGINT NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at        TIMESTAMPTZ,
            expires_at          TIMESTAMPTZ
        )
    """)

    # ------------------------------------------------------------------ #
    # vnc_sessions
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE vnc_sessions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id),
            run_id          UUID NOT NULL REFERENCES runs(id),
            container_id    TEXT,
            port            INTEGER,
            status          TEXT NOT NULL DEFAULT 'starting',
            token           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at      TIMESTAMPTZ
        )
    """)

    # ------------------------------------------------------------------ #
    # Indexes
    #
    # GIN indexes for full-JSONB queries (instructors, leaderboard):
    op.execute("CREATE INDEX idx_runs_ppa ON runs USING GIN (ppa)")
    op.execute("CREATE INDEX idx_runs_config ON runs USING GIN (config)")
    #
    # Functional B-tree indexes for hot ordering/filtering queries:
    op.execute("CREATE INDEX idx_runs_wns ON runs ((ppa->>'worst_negative_slack'))")
    op.execute("CREATE INDEX idx_runs_clock ON runs ((config->>'CLOCK_PERIOD'))")
    # ------------------------------------------------------------------ #


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vnc_sessions")
    op.execute("DROP TABLE IF EXISTS runs")
    op.execute("DROP TABLE IF EXISTS projects")
    op.execute("DROP TABLE IF EXISTS users")
