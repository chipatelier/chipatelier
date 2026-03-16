"""
Prompt templates for ORFS error and metric explanation endpoints.

Registered prompts:
  - explain_log    — plain-language explanation of log errors
  - explain_timing — explanation of timing (WNS/TNS) violations
  - explain_drc    — explanation of DRC routing errors

Privacy: NEVER includes GDS/DEF contents, PDK files, or student PII.
Only includes: log_tail, ppa metrics, stage info, design_name from config.
"""
from app.ai.prompts import register_prompt


@register_prompt("explain_log")
def explain_log_prompt(ctx: dict) -> str:
    """Generate a prompt explaining ORFS log errors to a university student."""
    stage = ctx.get("stage_completed", "unknown")
    log_lines = ctx.get("log_tail", [])
    # Use last 80 lines to stay within context budget
    log = "\n".join(log_lines[-80:]) if log_lines else "(no log lines available)"
    design_name = ctx.get("design_name", "unknown")
    ppa = ctx.get("ppa", {})
    wns = ppa.get("worst_negative_slack")
    drc = ppa.get("drc_routing_errors")

    ppa_info = ""
    if wns is not None or drc is not None:
        ppa_info = (
            f"\nMetrics from last completed stage: "
            f"WNS={wns} ns, DRC errors={drc}"
        )

    return (
        f"You are an expert ASIC design engineer helping a university student debug "
        f"an OpenROAD Flow Scripts (ORFS) run on the sky130hd PDK.\n\n"
        f"Design: {design_name}\n"
        f"Last completed stage: {stage}"
        f"{ppa_info}\n\n"
        f"Last {min(len(log_lines), 80)} lines of ORFS log:\n"
        f"---\n{log}\n---\n\n"
        f"Please explain in plain language what went wrong in this ORFS run. "
        f"Be specific about which stage failed and what the error messages mean. "
        f"Avoid excessive jargon — this is for a university student learning ASIC design. "
        f"Suggest one or two concrete things the student can try to fix the issue."
    )


@register_prompt("explain_timing")
def explain_timing_prompt(ctx: dict) -> str:
    """Generate a prompt explaining timing violations (WNS/TNS) to a student."""
    stage = ctx.get("stage_completed", "unknown")
    design_name = ctx.get("design_name", "unknown")
    ppa = ctx.get("ppa", {})
    wns = ppa.get("worst_negative_slack")
    tns = ppa.get("total_negative_slack")
    config = ctx.get("config", {})
    clock_period = config.get("CLOCK_PERIOD", "unknown")
    core_util = config.get("CORE_UTILIZATION", "unknown")

    metrics_info = (
        f"WNS (Worst Negative Slack): {wns} ns\n"
        f"TNS (Total Negative Slack): {tns} ns\n"
        f"Clock period: {clock_period} ns\n"
        f"Core utilization: {core_util}%"
    )

    cts_note = ""
    if stage in ("cts", "route", "finish"):
        cts_note = (
            "\n\nNote: After CTS (Clock Tree Synthesis), timing often worsens compared to "
            "placement — this is normal. CTS replaces the ideal clock assumption with real "
            "clock delays. The repair_timing step after CTS tries to fix setup/hold violations, "
            "but may not resolve all of them."
        )

    return (
        f"You are an expert ASIC design engineer helping a university student understand "
        f"timing violations in an OpenROAD Flow Scripts (ORFS) run on sky130hd.\n\n"
        f"Design: {design_name}\n"
        f"Current stage: {stage}\n\n"
        f"Timing metrics:\n{metrics_info}"
        f"{cts_note}\n\n"
        f"Please explain in plain language:\n"
        f"1. What does a WNS of {wns} ns mean for this design?\n"
        f"2. Is this timing result acceptable? What threshold matters?\n"
        f"3. What can the student try to improve timing? "
        f"(Consider CLOCK_PERIOD, CORE_UTILIZATION, PLACE_DENSITY, TNS_END_PERCENT)\n\n"
        f"Keep the explanation accessible to a university student learning ASIC design."
    )


@register_prompt("explain_drc")
def explain_drc_prompt(ctx: dict) -> str:
    """Generate a prompt explaining DRC routing errors to a student."""
    stage = ctx.get("stage_completed", "unknown")
    design_name = ctx.get("design_name", "unknown")
    ppa = ctx.get("ppa", {})
    drc_errors = ppa.get("drc_routing_errors", 0)
    placement_violations = ppa.get("placement_violations", 0)
    config = ctx.get("config", {})
    core_util = config.get("CORE_UTILIZATION", "unknown")
    place_density = config.get("PLACE_DENSITY", "unknown")

    return (
        f"You are an expert ASIC design engineer helping a university student understand "
        f"DRC (Design Rule Check) violations from an OpenROAD Flow Scripts (ORFS) run "
        f"on the sky130hd PDK.\n\n"
        f"Design: {design_name}\n"
        f"Last completed stage: {stage}\n\n"
        f"DRC results:\n"
        f"- Routing DRC errors (detailedroute): {drc_errors}\n"
        f"- Placement violations: {placement_violations}\n"
        f"- Core utilization: {core_util}%\n"
        f"- Place density: {place_density}\n\n"
        f"Please explain in plain language:\n"
        f"1. What are DRC violations in the context of routing?\n"
        f"2. What typically causes routing DRC errors in sky130hd?\n"
        f"3. What can the student try to reduce DRC violations? "
        f"(Consider CORE_UTILIZATION, PLACE_DENSITY, routing settings)\n\n"
        f"Keep the explanation accessible to a university student learning ASIC design."
    )
