"""
Context assembly for AI prompt templates.

Pulls from: run record (metrics, config), log buffer (last N lines from Redis).
Phase 3 wires this to actual AI prompts. Phase 1 scaffolds the interface.

Privacy constraint (CLAUDE.md):
  NEVER includes: GDS/DEF file contents, PDK files, student email/name.
  Only includes: log_tail, ppa metrics, config parameters, stage info.
"""
from __future__ import annotations


async def build_run_context(
    run,  # Run ORM object
    redis_client,
    log_lines: int = 100,
) -> dict:
    """Build the context dict injected into AI prompt templates.

    Returns context dict with:
      - run_id, status, stage_completed, target_stage
      - ppa: dict of PPA metrics (WNS, TNS, DRC, area, power)
      - config: dict of config.mk key-value pairs
      - log_tail: last N lines from Redis logbuf:{run_id}
      - design_name: extracted from config['DESIGN_NAME'] if present

    NEVER includes: GDS/DEF file contents, PDK files, student email/name.
    """
    log_key = f"logbuf:{run.id}"
    try:
        raw_lines = await redis_client.lrange(log_key, -log_lines, -1)
        log_tail = [
            line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line
            for line in (raw_lines or [])
        ]
    except Exception:
        log_tail = []

    return {
        "run_id": str(run.id),
        "status": run.status,
        "stage_completed": run.stage_completed,
        "target_stage": run.target_stage,
        "ppa": run.ppa or {},
        "config": run.config or {},
        "log_tail": log_tail,
        "design_name": (run.config or {}).get("DESIGN_NAME", "unknown"),
    }
