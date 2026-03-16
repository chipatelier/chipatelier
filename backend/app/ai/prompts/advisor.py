"""
Prompt template for the ORFS configuration advisor endpoint.

Registered prompts:
  - advisor_config — parameter suggestions based on current run PPA metrics

Privacy: NEVER includes GDS/DEF contents, PDK files, or student PII.
Only includes: ppa metrics, config parameters, stage info, design_name.
"""
from app.ai.prompts import register_prompt

# Curated subset of safe student-editable ORFS parameters (from CLAUDE.md)
CURATED_PARAMS = [
    "CORE_UTILIZATION",
    "PLACE_DENSITY",
    "TNS_END_PERCENT",
    "CLOCK_PERIOD",
    "CORE_ASPECT_RATIO",
    "CORE_MARGIN",
    "SETUP_SLACK_MARGIN",
]


@register_prompt("advisor_config")
def advisor_config_prompt(ctx: dict) -> str:
    """Generate a prompt for config parameter suggestions grounded in PPA metrics."""
    design_name = ctx.get("design_name", "unknown")
    stage = ctx.get("stage_completed", "unknown")
    ppa = ctx.get("ppa", {})
    config = ctx.get("config", {})

    # Build current parameter values from config
    param_lines = []
    for param in CURATED_PARAMS:
        value = config.get(param, "(not set)")
        param_lines.append(f"  {param}: {value}")
    params_str = "\n".join(param_lines)

    # Build PPA context section
    if ppa:
        wns = ppa.get("worst_negative_slack")
        tns = ppa.get("total_negative_slack")
        drc = ppa.get("drc_routing_errors")
        core_area = ppa.get("core_area")
        total_power = ppa.get("total_power")
        core_util = ppa.get("core_utilization")
        wirelength = ppa.get("wirelength")

        ppa_lines = []
        if wns is not None:
            ppa_lines.append(f"  Worst Negative Slack (WNS): {wns} ns")
        if tns is not None:
            ppa_lines.append(f"  Total Negative Slack (TNS): {tns} ns")
        if drc is not None:
            ppa_lines.append(f"  DRC routing errors: {drc}")
        if core_util is not None:
            ppa_lines.append(f"  Core utilization (actual): {core_util:.1%}")
        if core_area is not None:
            ppa_lines.append(f"  Core area: {core_area} um²")
        if total_power is not None:
            ppa_lines.append(f"  Total power: {total_power} W")
        if wirelength is not None:
            ppa_lines.append(f"  Total wirelength: {wirelength} um")

        ppa_context = (
            f"Run metrics from stage '{stage}':\n" + "\n".join(ppa_lines)
            if ppa_lines
            else "No run metrics available — providing general guidance."
        )
    else:
        ppa_context = "No run metrics available — providing general guidance."

    return (
        f"You are an expert ASIC design engineer advising a university student on "
        f"OpenROAD Flow Scripts (ORFS) configuration parameters for the sky130hd PDK.\n\n"
        f"Design: {design_name}\n\n"
        f"Current parameter values:\n{params_str}\n\n"
        f"{ppa_context}\n\n"
        f"Please provide concrete suggestions for improving this ORFS configuration. "
        f"For each parameter below, provide a suggestion in exactly this format:\n"
        f"  PARAM_NAME: current_value -> suggested_value | Reason: plain-language explanation\n\n"
        f"Parameters to review:\n"
        + "\n".join(f"  - {p}" for p in CURATED_PARAMS)
        + "\n\n"
        f"Only suggest changes where you have a specific reason grounded in the metrics above. "
        f"If a parameter looks good as-is, write: PARAM_NAME: current_value -> keep | Reason: looks good.\n"
        f"Keep explanations accessible to a university student learning ASIC design."
    )
