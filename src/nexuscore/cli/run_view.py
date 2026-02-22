"""
run_view.py

CR-NEXUS-027: RunView projection for CLI UX.

Transforms internal RunState / Explainability into human-readable CLI output.
"""

from __future__ import annotations

from typing import Any


def build_run_view(
    result: dict[str, Any], run_state: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Build RunView projection from runner result and optional RunState.

    Args:
        result: Return value from authority_runner.run_with_authority() or resume_run()
        run_state: Optional RunState dict (for additional fields like authority_level, updated_at)

    Returns:
        RunView dict with:
        - run_id
        - status
        - phase (next_phase or equivalent)
        - authority_level (if available)
        - updated_at (if available)
        - explainability (if status is CONFLICT/FAILED/ABORTED)
    """
    view: dict[str, Any] = {
        "run_id": result.get("run_id"),
        "status": result.get("status"),
    }

    # Extract phase from result or run_state
    phase = result.get("next_phase")
    if not phase and run_state:
        phase = run_state.get("next_phase")
    view["phase"] = phase

    # Extract authority_level from run_state or execution_context
    authority_level = None
    if run_state:
        authority_level = run_state.get("authority_level")
    if not authority_level and "execution_context" in result:
        authority_level = result.get("execution_context", {}).get("authority_level")
    view["authority_level"] = authority_level

    # Extract updated_at from run_state
    if run_state:
        view["updated_at"] = run_state.get("updated_at")

    # Extract explainability (required for CONFLICT/FAILED/ABORTED)
    status = view["status"]
    if status in ("CONFLICT", "FAILED", "ABORTED"):
        explainability = result.get("explainability", {})
        if explainability:
            view["explainability"] = explainability
        else:
            # Fallback: create minimal explainability if missing
            view["explainability"] = {
                "what": f"Run {status.lower()}: {view['run_id']}",
                "why": status,
                "next_action": "Check logs for details",
            }

    return view


def format_run_view_cli(run_view: dict[str, Any]) -> str:
    """
    Format RunView as human-readable CLI output.

    Status-based formatting:
    - RUNNING / completed: Simple status + run_id
    - PAUSED / paused: Status + phase + resume instruction
    - CONFLICT: Error message with explainability
    - FAILED / ABORTED: Error message with explainability

    Returns:
        Formatted string for CLI stdout
    """
    status = run_view.get("status", "").upper()
    run_id = run_view.get("run_id", "unknown")
    phase = run_view.get("phase")
    authority_level = run_view.get("authority_level")
    explainability = run_view.get("explainability")

    lines: list[str] = []

    # Status-specific formatting
    if status in ("RUNNING", "COMPLETED", "SUCCEEDED"):
        prefix = "[RUN STARTED]" if status == "RUNNING" else "[RUN COMPLETED]"
        lines.append(f"{prefix}")
        lines.append(f"run_id: {run_id}")
        if authority_level:
            lines.append(f"authority_level: {authority_level}")
        if phase:
            lines.append(f"phase: {phase}")

    elif status in ("PAUSED", "paused"):
        lines.append("[PAUSED]")
        lines.append(f"run_id: {run_id}")
        if phase:
            lines.append(f"paused at phase: {phase}")
        lines.append(f"Resume with: --resume-run-id {run_id}")
        if authority_level:
            lines.append(f"authority_level: {authority_level}")

    elif status == "CONFLICT":
        lines.append("[RESUME BLOCKED]")
        lines.append(f"run_id: {run_id}")
        if explainability:
            lines.append("")
            _format_explainability(lines, explainability)

    elif status in ("FAILED", "ABORTED"):
        error_label = "[RESUME FAILED]" if "resume" in str(run_view).lower() else "[RUN FAILED]"
        if status == "ABORTED":
            error_label = "[RUN ABORTED]"
        lines.append(error_label)
        lines.append(f"run_id: {run_id}")
        if explainability:
            lines.append("")
            _format_explainability(lines, explainability)

    else:
        # Fallback for unknown status
        lines.append(f"[{status}]")
        lines.append(f"run_id: {run_id}")
        if phase:
            lines.append(f"phase: {phase}")
        if explainability:
            lines.append("")
            _format_explainability(lines, explainability)

    return "\n".join(lines)


def _format_explainability(lines: list[str], explainability: dict[str, Any]) -> None:
    """
    Append explainability fields to lines list.

    Handles key variations: why_code / why, what, next_action.
    """
    # Extract why (handle both why_code and why)
    why = explainability.get("why_code") or explainability.get("why")
    what = explainability.get("what", "")
    next_action = explainability.get("next_action", "")

    if what:
        lines.append(f"Error: {what}")
    if why:
        lines.append(f"Reason: {why}")
    if next_action:
        lines.append(f"Next: {next_action}")
