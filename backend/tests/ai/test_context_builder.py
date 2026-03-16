"""
Unit tests for build_run_context() in app.ai.context_builder.

All tests use mock run objects and mock redis clients to avoid
database and Redis dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.context_builder import build_run_context


def _make_run(
    run_id="00000000-0000-0000-0000-000000000001",
    status="complete",
    stage_completed="route",
    target_stage="finish",
    ppa=None,
    config=None,
):
    """Create a mock run object with the expected attributes."""
    run = MagicMock()
    run.id = run_id
    run.status = status
    run.stage_completed = stage_completed
    run.target_stage = target_stage
    run.ppa = ppa or {"worst_negative_slack": -2.3, "drc_routing_errors": 0}
    run.config = config or {"DESIGN_NAME": "gcd", "PLATFORM": "sky130hd"}
    return run


def _make_redis(log_lines=None):
    """Create a mock async redis client."""
    redis = AsyncMock()
    if log_lines is None:
        log_lines = [b"[INFO FLW-0012] Running stage route"]
    redis.lrange = AsyncMock(return_value=log_lines)
    return redis


async def test_build_run_context_returns_expected_keys():
    """build_run_context() returns dict with all required keys."""
    run = _make_run()
    redis = _make_redis()

    ctx = await build_run_context(run, redis, log_lines=100)

    required_keys = {"run_id", "status", "stage_completed", "target_stage", "ppa", "config", "log_tail", "design_name"}
    assert required_keys.issubset(ctx.keys()), f"Missing keys: {required_keys - ctx.keys()}"


async def test_build_run_context_values_correct():
    """build_run_context() maps run attributes to context dict correctly."""
    run = _make_run(status="failed", stage_completed="cts", target_stage="route")
    redis = _make_redis()

    ctx = await build_run_context(run, redis)

    assert ctx["status"] == "failed"
    assert ctx["stage_completed"] == "cts"
    assert ctx["target_stage"] == "route"
    assert ctx["design_name"] == "gcd"


async def test_build_run_context_caps_log_lines():
    """build_run_context() respects the log_lines cap."""
    # Create 200 log lines in Redis
    many_lines = [f"[INFO] Line {i}".encode() for i in range(200)]
    redis = AsyncMock()
    # Simulate Redis lrange returning exactly the requested slice
    # build_run_context calls lrange(key, -log_lines, -1)
    redis.lrange = AsyncMock(return_value=many_lines[-50:])

    run = _make_run()
    ctx = await build_run_context(run, redis, log_lines=50)

    # lrange should have been called with -50 offset
    redis.lrange.assert_called_once()
    call_args = redis.lrange.call_args
    assert call_args[0][1] == -50 or call_args[1].get("start", call_args[0][1]) == -50


async def test_build_run_context_handles_redis_failure():
    """build_run_context() returns empty log_tail on Redis error without raising."""
    redis = AsyncMock()
    redis.lrange = AsyncMock(side_effect=ConnectionError("Redis down"))

    run = _make_run()
    # Should NOT raise
    ctx = await build_run_context(run, redis, log_lines=100)

    assert ctx["log_tail"] == []
    assert "run_id" in ctx  # other fields still populated


async def test_build_run_context_never_includes_pii():
    """build_run_context() does not include any PII-like keys in the returned dict."""
    run = _make_run()
    redis = _make_redis()

    ctx = await build_run_context(run, redis)

    for key in ctx.keys():
        # No key should suggest email, password, or user identity
        assert "email" not in key.lower(), f"PII-like key found: {key}"
        assert "password" not in key.lower(), f"PII-like key found: {key}"
        # design_name is explicitly allowed
        assert key not in ("user_email", "user_name", "password_hash"), f"PII key: {key}"

    # Values should not contain file path artifacts
    assert "/data/artifacts" not in str(ctx.get("run_id", ""))


async def test_build_run_context_decodes_bytes_log_lines():
    """build_run_context() decodes byte strings from Redis to str."""
    redis = AsyncMock()
    redis.lrange = AsyncMock(
        return_value=[b"[INFO] byte line", "[INFO] str line"]
    )
    run = _make_run()
    ctx = await build_run_context(run, redis)

    for line in ctx["log_tail"]:
        assert isinstance(line, str), f"Expected str, got {type(line)}: {line!r}"


async def test_build_run_context_design_name_from_config():
    """build_run_context() extracts design_name from config DESIGN_NAME key."""
    run = _make_run(config={"DESIGN_NAME": "picorv32", "PLATFORM": "sky130hd"})
    redis = _make_redis()
    ctx = await build_run_context(run, redis)
    assert ctx["design_name"] == "picorv32"


async def test_build_run_context_design_name_fallback():
    """build_run_context() falls back to 'unknown' when DESIGN_NAME not in config."""
    run = _make_run(config={"PLATFORM": "sky130hd"})
    redis = _make_redis()
    ctx = await build_run_context(run, redis)
    assert ctx["design_name"] == "unknown"
