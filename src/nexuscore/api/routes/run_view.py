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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.requests import Request

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..deps.orchestrator import get_orchestrator
from ..schemas.error import ErrorResponse
from ..schemas.run_view import RunCreateRequest, RunViewResponse
from ..utils.errors import make_not_found_error
from ..utils.run_view import build_run_view_response

# Canonical router (primary endpoints)
canonical_router = APIRouter(tags=["runs"])

# Deprecated router (backward compatibility, excluded from OpenAPI)
deprecated_router = APIRouter(
    tags=["run-view"],
    prefix="/run-view",
    include_in_schema=False,
)

logger = logging.getLogger(__name__)


def _get_project_path_from_run_state(run_state: dict[str, Any] | None) -> str:
    """
    Extract project_path from RunState or use default.

    Args:
        run_state: RunState dict (may be None)

    Returns:
        Project path string
    """
    # Try to get from execution_context in RunState
    if run_state and "execution_context" in run_state:
        exec_ctx = run_state["execution_context"]
        if isinstance(exec_ctx, dict) and "project_path" in exec_ctx:
            return exec_ctx["project_path"]

    # Use environment variable or default
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
    """
    Get RunView for a run_id (from RunState).

    GET /api/v1/runs/{run_id}

    Returns RunView projection (not raw RunState JSON).

    Args:
        run_id: Run ID
        current_user: Authenticated user

    Returns:
        RunViewResponse: RunView projection

    Raises:
        HTTPException: RunState not found (404) or internal error (500)
    """
    try:
        from nexuscore.orchestrator.run_state_store import load_state

        try:
            run_state = load_state(run_id)
        except FileNotFoundError:
            raise make_not_found_error("RunState", run_id)

        # Build RunView from RunState
        result = {
            "run_id": run_id,
            "status": run_state.get("status", "UNKNOWN"),
            "next_phase": run_state.get("next_phase"),
        }

        # Add execution_context if available
        if "authority_level" in run_state:
            result["execution_context"] = {"authority_level": run_state.get("authority_level")}

        return build_run_view_response(result, run_state)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run view: {e}", exc_info=True)
        from ..utils.errors import make_internal_error

        raise make_internal_error(f"Failed to get run view: {str(e)}")


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
    """
    Resume a paused run by run_id.

    POST /api/v1/runs/{run_id}/resume

    Returns RunView projection. Returns 409 (CONFLICT) if run is already running,
    400 (BAD_REQUEST) for integrity violations or other failures.

    Args:
        run_id: Run ID to resume
        current_user: Authenticated user

    Returns:
        RunViewResponse: RunView projection

    Raises:
        HTTPException:
            - 404: RunState not found
            - 409: CONFLICT (run is already running/executing)
            - 400: FAILED/ABORTED (integrity violation, schema invalid, etc.)
            - 500: Internal error
    """
    try:
        from nexuscore.orchestrator import authority_runner
        from nexuscore.orchestrator.run_state_store import load_state

        # Load RunState to get project_path and additional fields
        run_state = None
        try:
            run_state = load_state(run_id)
        except FileNotFoundError:
            raise make_not_found_error("RunState", run_id)

        # Get project_path from RunState or default
        project_path = _get_project_path_from_run_state(run_state)
        language = (
            run_state.get("execution_context", {}).get("language", "ja") if run_state else "ja"
        )

        # Create orchestrator factory for this request (request-scoped, no global state)
        def orchestrator_factory():
            return get_orchestrator(project_path=project_path, language=language)

        # Call resume_run with orchestrator_factory argument (CR-NEXUS-030: no global setter)
        result = authority_runner.resume_run(run_id, orchestrator_factory=orchestrator_factory)

        # Reload RunState in case it was updated by resume_run
        try:
            run_state = load_state(run_id)
        except FileNotFoundError:
            pass  # Use previous run_state if reload fails

        # Build RunView response
        run_view = build_run_view_response(result, run_state)

        # Map status to HTTP status codes
        # CONFLICT -> 409, FAILED/ABORTED -> 400 (with explainability in RunView)
        status_code = result.get("status", "").upper()
        if status_code == "CONFLICT":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=run_view.dict(),
            )
        elif status_code in ("FAILED", "ABORTED"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=run_view.dict(),
            )

        return run_view

    except HTTPException:
        raise
    except FileNotFoundError:
        raise make_not_found_error("RunState", run_id)
    except Exception as e:
        logger.error(f"Failed to resume run: {e}", exc_info=True)
        from ..utils.errors import make_internal_error

        raise make_internal_error(f"Failed to resume run: {str(e)}")


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
    """
    Create and start a new run (equivalent to CLI run command).

    POST /api/v1/runs

    Returns RunView projection.

    Args:
        request: Run creation request
        current_user: Authenticated user

    Returns:
        RunViewResponse: RunView projection

    Raises:
        HTTPException:
            - 400: FAILED/ABORTED
            - 500: Internal error
    """
    try:
        from nexuscore.orchestrator import authority_runner
        from nexuscore.orchestrator.run_state_store import load_state

        # Get project_path from environment or default
        project_path = os.getenv(
            "NEXUSCORE_PROJECT_PATH", os.path.join(os.getcwd(), ".nexus", "api_runs")
        )

        # Generate Orchestrator via DI
        orchestrator = get_orchestrator(project_path=project_path, language=request.language)

        # Call run_with_authority
        result = authority_runner.run_with_authority(
            orchestrator=orchestrator,
            user_requirement=request.requirement,
            authority_level=request.authority_level,
            language=request.language,
        )

        # Load RunState if run_id is available
        run_state = None
        run_id = result.get("run_id")
        if run_id:
            try:
                run_state = load_state(run_id)
            except FileNotFoundError:
                pass  # RunState not available, use result only

        # Build RunView response
        run_view = build_run_view_response(result, run_state)

        # Map status to HTTP status codes (run_with_authority doesn't return CONFLICT/FAILED typically)
        # But handle edge cases
        status_code = result.get("status", "").upper()
        if status_code in ("FAILED", "ABORTED"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=run_view.dict(),
            )

        return run_view

    except Exception as e:
        logger.error(f"Failed to create run: {e}", exc_info=True)
        from ..utils.errors import make_internal_error

        raise make_internal_error(f"Failed to create run: {str(e)}")


# Deprecated endpoints (delegate to canonical handlers)
@deprecated_router.get(
    "/runs/{run_id}",
    response_model=RunViewResponse,
    summary="[Deprecated] Get RunView by run_id",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_run_view_deprecated(
    run_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunViewResponse:
    """
    [Deprecated] Get RunView for a run_id (from RunState).

    Use GET /api/v1/runs/{run_id} instead.

    GET /api/v1/run-view/runs/{run_id} (deprecated, delegates to canonical endpoint)
    """
    logger.info(
        "Deprecated endpoint used",
        extra={
            "deprecated_endpoint_used": True,
            "request_path": str(request.url),
            "canonical_path": f"/api/v1/runs/{run_id}",
        },
    )
    return await get_run_view(run_id, current_user)


@deprecated_router.post(
    "/runs/{run_id}/resume",
    response_model=RunViewResponse,
    summary="[Deprecated] Resume a paused run",
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
async def resume_run_view_deprecated(
    run_id: str,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunViewResponse:
    """
    [Deprecated] Resume a paused run by run_id.

    Use POST /api/v1/runs/{run_id}/resume instead.

    POST /api/v1/run-view/runs/{run_id}/resume (deprecated, delegates to canonical endpoint)
    """
    logger.info(
        "Deprecated endpoint used",
        extra={
            "deprecated_endpoint_used": True,
            "request_path": str(request.url),
            "canonical_path": f"/api/v1/runs/{run_id}/resume",
        },
    )
    return await resume_run_view(run_id, current_user)


@deprecated_router.post(
    "/runs",
    response_model=RunViewResponse,
    summary="[Deprecated] Create and start a new run",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": RunViewResponse, "description": "Run created successfully"},
        400: {"model": RunViewResponse, "description": "Run failed/aborted (with explainability)"},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_run_view_deprecated(
    request_body: RunCreateRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunViewResponse:
    """
    [Deprecated] Create and start a new run (equivalent to CLI run command).

    Use POST /api/v1/runs instead.

    POST /api/v1/run-view/runs (deprecated, delegates to canonical endpoint)
    """
    logger.info(
        "Deprecated endpoint used",
        extra={
            "deprecated_endpoint_used": True,
            "request_path": str(request.url),
            "canonical_path": "/api/v1/runs",
        },
    )
    return await create_run_view(request_body, current_user)
