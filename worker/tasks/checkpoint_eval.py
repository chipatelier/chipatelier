"""Checkpoint evaluation Celery task.

Evaluates assignment checkpoint rules against a run's PPA metrics.
Dispatched by the submission route after a student submits a run.

Queue: background (dedicated background worker, not orfs-worker).
"""
import json
import logging

logger = logging.getLogger(__name__)

try:
    from worker.celery_app import app
except ImportError:
    from celery_app import app  # fallback when CWD is worker/ (production entrypoint)


# ---------------------------------------------------------------------------
# Pure evaluation logic — no DB, no Celery, fully unit-testable
# ---------------------------------------------------------------------------

def _compare(actual, op: str, threshold) -> bool:
    """Compare actual metric value against threshold using op."""
    if actual is None:
        return False
    if op == "eq":
        return actual == threshold
    if op == "gte":
        return actual >= threshold
    if op == "lte":
        return actual <= threshold
    if op == "gt":
        return actual > threshold
    if op == "lt":
        return actual < threshold
    logger.warning("Unknown op '%s' in checkpoint rule", op)
    return False


def evaluate_checkpoint_rules(ppa: dict, rules: dict) -> tuple[dict, float]:
    """Evaluate checkpoint rules against PPA metrics.

    ppa: dict with friendly metric names already mapped, e.g.:
        {"worst_negative_slack": -0.05, "drc_violations": 0, ...}

    rules: checkpoint_rules JSONB, e.g.:
        {
            "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
            "scored": [
                {"metric": "worst_negative_slack", "op": "gte", "value": -0.1,
                 "points": 40, "partial": {"threshold": -0.5, "points": 20}}
            ]
        }

    Returns: (checkpoint_results dict, total_score float)

    checkpoint_results structure:
        {
            "hard": [{"metric": ..., "passed": bool, "actual": ...}],
            "scored": [{"metric": ..., "awarded": int, "max_points": int,
                        "passed": bool, "partial_credit": bool, "actual": ...}],
            "hard_gate_blocked": bool  # True if any hard gate failed
        }
    """
    hard_rules = rules.get("hard", [])
    scored_rules = rules.get("scored", [])

    # Evaluate hard gates
    hard_results = []
    hard_gate_passed = True
    for rule in hard_rules:
        metric = rule["metric"]
        op = rule["op"]
        threshold = rule["value"]
        actual = ppa.get(metric)
        passed = _compare(actual, op, threshold)
        if not passed:
            hard_gate_passed = False
        hard_results.append({
            "metric": metric,
            "op": op,
            "threshold": threshold,
            "actual": actual,
            "passed": passed,
        })

    # Evaluate scored criteria (always compute for display, but block score if hard gate failed)
    scored_results = []
    total_score = 0.0
    for rule in scored_rules:
        metric = rule["metric"]
        op = rule["op"]
        threshold = rule["value"]
        max_points = rule.get("points", 0)
        actual = ppa.get(metric)
        partial_config = rule.get("partial")

        passed = _compare(actual, op, threshold)
        partial_credit = False

        if passed:
            awarded = max_points
        elif partial_config and actual is not None:
            # Check partial credit threshold
            partial_threshold = partial_config["threshold"]
            if _compare(actual, op, partial_threshold):
                awarded = partial_config["points"]
                partial_credit = True
            else:
                awarded = 0
        else:
            awarded = 0

        scored_results.append({
            "metric": metric,
            "op": op,
            "threshold": threshold,
            "actual": actual,
            "passed": passed,
            "awarded": awarded,
            "max_points": max_points,
            "partial_credit": partial_credit,
        })

        if hard_gate_passed:
            total_score += awarded

    checkpoint_results = {
        "hard": hard_results,
        "scored": scored_results,
        "hard_gate_blocked": not hard_gate_passed,
    }

    if not hard_gate_passed:
        total_score = 0.0

    return checkpoint_results, total_score


# ---------------------------------------------------------------------------
# Celery task — synchronous DB access (same pattern as tile_generator.py)
# ---------------------------------------------------------------------------

@app.task(name="tasks.checkpoint_eval.evaluate_submission", queue="background")
def evaluate_submission(submission_id: str) -> None:
    """Evaluate checkpoint rules for a submission and publish grade result to Redis.

    Uses synchronous SQLAlchemy (not async) — same pattern as tile_generator.py.

    Steps:
    1. Fetch Submission + Assignment + Run from DB (sync session).
    2. Call evaluate_checkpoint_rules(run.ppa, assignment.checkpoint_rules).
    3. Update submission.checkpoint_results, submission.score, submission.grading_status.
    4. Update run.is_submitted = True.
    5. Commit.
    6. Publish: redis.publish(f"grade:{run_id}", json.dumps(result)).
    7. On exception: set grading_status="failed", commit, re-raise.
    """
    import redis
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    try:
        from config import get_settings
    except ImportError:
        from app.core.config import get_settings

    settings = get_settings()

    # Convert asyncpg URL to sync psycopg2 URL (same pattern as tile_generator.py)
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)

    grading_status = "failed"
    try:
        with Session(engine) as db_session:
            # Fetch submission, run, assignment via raw SQL (avoids ORM model import issues)
            sub_row = db_session.execute(
                text(
                    "SELECT s.id, s.run_id, s.assignment_id, s.user_id "
                    "FROM submissions s WHERE s.id = CAST(:sid AS uuid)"
                ),
                {"sid": submission_id},
            ).fetchone()

            if sub_row is None:
                logger.error("evaluate_submission: submission %s not found", submission_id)
                return

            run_id = str(sub_row.run_id)

            # Fetch run PPA (already has friendly names)
            run_row = db_session.execute(
                text("SELECT ppa FROM runs WHERE id = CAST(:rid AS uuid)"),
                {"rid": run_id},
            ).fetchone()
            ppa = run_row.ppa if run_row and run_row.ppa else {}

            # Fetch assignment checkpoint_rules
            asgn_row = db_session.execute(
                text("SELECT checkpoint_rules FROM assignments WHERE id = CAST(:aid AS uuid)"),
                {"aid": str(sub_row.assignment_id)},
            ).fetchone()
            checkpoint_rules = asgn_row.checkpoint_rules if asgn_row and asgn_row.checkpoint_rules else {}

        # Evaluate rules (pure function — outside DB session)
        checkpoint_results, score = evaluate_checkpoint_rules(ppa, checkpoint_rules)

        with Session(engine) as db_session:
            # Update submission
            db_session.execute(
                text(
                    "UPDATE submissions SET "
                    "checkpoint_results = CAST(:cr AS jsonb), "
                    "score = :score, "
                    "grading_status = 'complete' "
                    "WHERE id = CAST(:sid AS uuid)"
                ),
                {
                    "cr": json.dumps(checkpoint_results),
                    "score": score,
                    "sid": submission_id,
                },
            )
            # Mark run as submitted
            db_session.execute(
                text("UPDATE runs SET is_submitted = TRUE WHERE id = CAST(:rid AS uuid)"),
                {"rid": run_id},
            )
            db_session.commit()
            grading_status = "complete"

        # Publish grade result to Redis channel grade:{run_id}
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
        result_payload = {
            "score": score,
            "checkpoint_results": checkpoint_results,
            "submission_id": submission_id,
        }
        r.publish(f"grade:{run_id}", json.dumps(result_payload).encode("utf-8"))
        logger.info(
            "evaluate_submission: published grade for run %s — score=%.1f", run_id, score
        )

    except Exception as exc:
        logger.exception("evaluate_submission: error for submission %s: %s", submission_id, exc)
        # Set failed status
        try:
            with Session(engine) as db_session:
                db_session.execute(
                    text(
                        "UPDATE submissions SET grading_status = 'failed' "
                        "WHERE id = CAST(:sid AS uuid)"
                    ),
                    {"sid": submission_id},
                )
                db_session.commit()
        except Exception:
            pass
        raise
    finally:
        engine.dispose()
