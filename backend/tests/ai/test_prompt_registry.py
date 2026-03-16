"""
Unit tests for the PROMPT_REGISTRY and all registered prompt templates.
"""
import pytest

from app.ai.prompts import PROMPT_REGISTRY


def _make_context(ppa=None, config=None, log_tail=None):
    """Build a sample context dict matching build_run_context() output."""
    return {
        "run_id": "00000000-0000-0000-0000-000000000001",
        "status": "complete",
        "stage_completed": "route",
        "target_stage": "finish",
        "ppa": ppa if ppa is not None else {
            "worst_negative_slack": -2.3,
            "total_negative_slack": -15.7,
            "drc_routing_errors": 0,
            "core_area": 1070.65,
            "total_power": 0.00073,
        },
        "config": config if config is not None else {
            "DESIGN_NAME": "gcd",
            "PLATFORM": "sky130hd",
            "CLOCK_PERIOD": "10",
            "CORE_UTILIZATION": "40",
        },
        "log_tail": log_tail if log_tail is not None else [
            "[INFO FLW-0012] Running stage route",
            "[WARNING DRT-0001] 3 DRC violations found",
            "[INFO FLW-0036] Elapsed time: 0:02:15",
        ],
        "design_name": "gcd",
    }


def test_all_required_prompts_registered():
    """PROMPT_REGISTRY contains all 4 required prompt keys."""
    required = {"explain_log", "explain_timing", "explain_drc", "advisor_config"}
    assert required.issubset(PROMPT_REGISTRY.keys()), (
        f"Missing prompts: {required - PROMPT_REGISTRY.keys()}"
    )


def test_explain_log_prompt_contains_log_tail():
    """explain_log prompt includes content from the log_tail context."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["explain_log"](ctx)
    # At least one log line should appear in the prompt
    assert any(line in result for line in ctx["log_tail"]), (
        "No log tail lines found in explain_log prompt"
    )


def test_explain_log_prompt_contains_design_name():
    """explain_log prompt includes the design name."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["explain_log"](ctx)
    assert "gcd" in result


def test_explain_log_prompt_does_not_contain_pii():
    """explain_log prompt does not contain PII-like paths or keywords."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["explain_log"](ctx)
    assert "email" not in result.lower()
    assert "/data/artifacts" not in result
    assert "password" not in result.lower()


def test_explain_timing_prompt_contains_wns():
    """explain_timing prompt includes WNS value from context."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["explain_timing"](ctx)
    assert "-2.3" in result


def test_explain_timing_prompt_contains_clock_period():
    """explain_timing prompt references the CLOCK_PERIOD config value."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["explain_timing"](ctx)
    assert "10" in result  # CLOCK_PERIOD = 10


def test_explain_drc_prompt_contains_drc_count():
    """explain_drc prompt includes DRC error count from context."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["explain_drc"](ctx)
    # drc_routing_errors = 0 in sample context
    assert "0" in result


def test_advisor_config_prompt_references_curated_params():
    """advisor_config prompt includes all 7 curated parameter names."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["advisor_config"](ctx)
    required_params = [
        "CORE_UTILIZATION",
        "PLACE_DENSITY",
        "TNS_END_PERCENT",
        "CLOCK_PERIOD",
        "CORE_ASPECT_RATIO",
        "CORE_MARGIN",
        "SETUP_SLACK_MARGIN",
    ]
    for param in required_params:
        assert param in result, f"Curated param {param} not found in advisor_config prompt"


def test_advisor_config_includes_ppa_when_present():
    """advisor_config prompt includes PPA metrics when context has run data."""
    ctx = _make_context()
    result = PROMPT_REGISTRY["advisor_config"](ctx)
    # WNS value should appear in the prompt
    assert "-2.3" in result or "route" in result


def test_advisor_config_no_ppa_handles_empty():
    """advisor_config prompt handles empty PPA context gracefully."""
    ctx = _make_context(ppa={})
    result = PROMPT_REGISTRY["advisor_config"](ctx)
    # Should mention no metrics available
    assert "general guidance" in result.lower() or "No run metrics" in result


def test_all_prompts_return_strings():
    """All registered prompts return non-empty strings when called."""
    ctx = _make_context()
    for name, fn in PROMPT_REGISTRY.items():
        result = fn(ctx)
        assert isinstance(result, str), f"Prompt {name!r} did not return a string"
        assert len(result) > 10, f"Prompt {name!r} returned suspiciously short string: {result!r}"


def test_explain_prompts_mention_sky130hd():
    """Explain prompts reference the sky130hd PDK or OpenROAD context."""
    ctx = _make_context()
    for name in ("explain_log", "explain_timing", "explain_drc"):
        result = PROMPT_REGISTRY[name](ctx)
        assert "sky130" in result.lower() or "openroad" in result.lower() or "orfs" in result.lower(), (
            f"Prompt {name!r} does not mention the PDK or flow context"
        )
