from __future__ import annotations

from typing import Any

from nexuscore.cli.run_view import build_run_view as cli_build_run_view

from ..schemas.run_view import ExplainabilityModel, RunViewResponse


def build_run_view_response(
    result: dict[str, Any], run_state: dict[str, Any] | None = None
) -> RunViewResponse:
    """
    Build RunViewResponse (Pydantic) from runner result and optional RunState.

    Args:
        result: Return value from authority_runner.run_with_authority() or resume_run()
        run_state: Optional RunState dict (for additional fields like authority_level, updated_at)

    Returns:
        RunViewResponse: Pydantic model for API response
    """
    # Reuse CLI's build_run_view logic
    view_dict = cli_build_run_view(result, run_state)

    # Convert explainability dict to Pydantic model if present
    explainability = None
    if view_dict.get("explainability"):
        exp_dict = view_dict["explainability"]
        explainability = ExplainabilityModel(
            what=exp_dict.get("what", ""),
            why=exp_dict.get("why_code") or exp_dict.get("why", ""),
            next_action=exp_dict.get("next_action", ""),
            details=exp_dict.get("details"),
        )

    return RunViewResponse(
        run_id=view_dict.get("run_id", ""),
        status=view_dict.get("status", ""),
        phase=view_dict.get("phase"),
        authority_level=view_dict.get("authority_level"),
        updated_at=view_dict.get("updated_at"),
        explainability=explainability,
    )
