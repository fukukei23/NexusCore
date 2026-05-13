"""
RunView API endpoints (CR-NEXUS-028/029/032).

RunState-based RunView projection API endpoints.
External API returns RunView only, not raw RunState JSON.
Orchestrator Dependency Injection for API (CR-NEXUS-029).

CR-NEXUS-032: Canonical paths are /api/v1/runs.
Deprecated paths /api/v1/run-view/runs are kept for backward compatibility (excluded from OpenAPI).
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..dependencies.orchestrator import get_orchestrator
from ..schemas.error import ErrorResponse
from ..schemas.run_view import RunCreateRequest, RunViewResponse
from ..utils.errors import make_not_found_error
from ..utils.run_view_adapter import build_run_view_response

# Canonical router (primary endpoints)
canonical_router = APIRouter(tags=["runs"])

logger = logging.getLogger(__name__)


def _get_project_path_from_run_state(run_state: dict[str, Any] | None) -> str:
    """Extract project_path from RunState or use default."""
    if run_state and "execution_context" in run_state:
        exec_ctx = run_state["execution_context"]
        if isinstance(exec_ctx, dict) and "project_path" in exec_ctx:
            return exec_ctx["project_path"]

    default_path = os.path.join(os.getcwd(), ".nexus", "api_runs")
    return os.getenv("NEXUSCORE_PROJECT_PATH", default_path)


@canonical_router.get(
    "/runs/{run_id}",
    response_model=RunViewResponse,
    summary="Get RunView by run_id",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_run_view(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunViewResponse:
    """Get RunView for a run_id (from RunState)."""
    try:
        from nexuscore.orchestrator.run_state_store import load_state

        try:
            run_state = load_state(run_id)
        except FileNotFoundError:
            raise make_not_found_error("RunState", run_id) from None

        result = {
            "run_id": run_id,
            "status": run_state.get("status", "UNKNOWN"),
            "next_phase": run_state.get("next_phase"),
        }

        if "authority_level" in run_state:
            result["execution_context"] = {"authority_level": run_state.get("authority_level")}

        return build_run_view_response(result, run_state)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run view: {e}", exc_info=True)
        from ..utils.errors import make_internal_error

        raise make_internal_error("Failed to get run view. Please try again later.") from e


@canonical_router.post(
    "/runs/{run_id}/resume",
    response_model=RunViewResponse,
    summary="Resume a paused run",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": RunViewResponse, "description": "Run resumed successfully"},
        400: {"model": RunViewResponse, "description": "Run failed/aborted (with explainability)"},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "RunState not found"},
        409: {"model": RunViewResponse, "description": "Resume conflict (with explainability)"},
        500: {"model": ErrorResponse},
    },
)
async def resume_run_view(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunViewResponse:
    """Resume a paused run by run_id."""
    try:
        from nexuscore.orchestrator import authority_runner
        from nexuscore.orchestrator.run_state_store import load_state

        run_state = None
        try:
            run_state = load_state(run_id)
        except FileNotFoundError:
            raise make_not_found_error("RunState", run_id) from None

        project_path = _get_project_path_from_run_state(run_state)
        language = (
            run_state.get("execution_context", {}).get("language", "ja") if run_state else "ja"
        )

        def orchestrator_factory():
            return get_orchestrator(project_path=project_path, language=language)

        result = authority_runner.resume_run(run_id, orchestrator_factory=orchestrator_factory)

        try:
            run_state = load_state(run_id)
        except FileNotFoundError:
            pass

        run_view = build_run_view_response(result, run_state)

        status_code = result.get("status", "").upper()
        if status_code == "CONFLICT":
            return JSONResponse(  # type: ignore[return-value]
                status_code=status.HTTP_409_CONFLICT,
                content=run_view.dict(),
            )
        elif status_code in ("FAILED", "ABORTED"):
            return JSONResponse(  # type: ignore[return-value]
                status_code=status.HTTP_400_BAD_REQUEST,
                content=run_view.dict(),
            )

        return run_view

    except HTTPException:
        raise
    except FileNotFoundError:
        raise make_not_found_error("RunState", run_id) from None
    except Exception as e:
        logger.error(f"Failed to resume run: {e}", exc_info=True)
        from ..utils.errors import make_internal_error

        raise make_internal_error("Failed to resume run. Please try again later.") from e


@canonical_router.post(
    "/runs",
    response_model=RunViewResponse,
    summary="Create and start a new run",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": RunViewResponse, "description": "Run created successfully"},
        400: {"model": RunViewResponse, "description": "Run failed/aborted (with explainability)"},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_run_view(
    request: RunCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunViewResponse:
    """Create and start a new run (equivalent to CLI run command)."""
    try:
        from nexuscore.orchestrator import authority_runner
        from nexuscore.orchestrator.run_state_store import load_state

        project_path = os.getenv(
            "NEXUSCORE_PROJECT_PATH", os.path.join(os.getcwd(), ".nexus", "api_runs")
        )

        orchestrator = get_orchestrator(project_path=project_path, language=request.language)

        result = authority_runner.run_with_authority(
            orchestrator=orchestrator,
            user_requirement=request.requirement,
            authority_level=request.authority_level,
            language=request.language,
        )

        run_state = None
        run_id = result.get("run_id")
        if run_id:
            try:
                run_state = load_state(run_id)
            except FileNotFoundError:
                pass

        run_view = build_run_view_response(result, run_state)

        status_code = result.get("status", "").upper()
        if status_code in ("FAILED", "ABORTED"):
            return JSONResponse(  # type: ignore[return-value]
                status_code=status.HTTP_400_BAD_REQUEST,
                content=run_view.dict(),
            )

        return run_view

    except Exception as e:
        logger.error(f"Failed to create run: {e}", exc_info=True)
        from ..utils.errors import make_internal_error

        raise make_internal_error("Failed to create run. Please try again later.") from e
