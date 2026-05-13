"""Deprecated RunView API endpoints (backward compatibility)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from starlette.requests import Request

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..schemas.error import ErrorResponse
from ..schemas.run_view import RunCreateRequest, RunViewResponse
from .run_view import create_run_view, get_run_view, resume_run_view

deprecated_router = APIRouter(
    tags=["run-view"],
    prefix="/run-view",
    include_in_schema=False,
)

logger = logging.getLogger(__name__)


@deprecated_router.get(
    "/runs/{run_id}",
    response_model=RunViewResponse,
    summary="[Deprecated] Get RunView by run_id",
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
    """[Deprecated] Use GET /api/v1/runs/{run_id} instead."""
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
    """[Deprecated] Use POST /api/v1/runs/{run_id}/resume instead."""
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
    """[Deprecated] Use POST /api/v1/runs instead."""
    logger.info(
        "Deprecated endpoint used",
        extra={
            "deprecated_endpoint_used": True,
            "request_path": str(request.url),
            "canonical_path": "/api/v1/runs",
        },
    )
    return await create_run_view(request_body, current_user)
