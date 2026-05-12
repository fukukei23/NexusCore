"""
Projects Run エンドポイント（trigger_run / get_latest_run）
"""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import desc

from ..dependencies.auth import AuthenticatedUser, get_current_user, get_user_id_from_auth
from ..schemas.error import ErrorResponse
from ..schemas.project_run import (
    LatestRunDetail,
    LatestRunResponse,
    ProjectRunRequest,
    ProjectRunResponse,
)
from ..utils.errors import (
    make_bad_request_error,
    make_internal_error,
    make_not_found_error,
)

router = APIRouter(tags=["projects"])
logger = logging.getLogger(__name__)


@router.post(
    "/projects/{project_id}/run",
    response_model=ProjectRunResponse,
    summary="Trigger project run",
    responses={
        200: {"model": ProjectRunResponse, "description": "Synchronous execution completed"},
        202: {"model": ProjectRunResponse, "description": "Asynchronous execution started"},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def trigger_project_run(
    project_id: int,
    request: ProjectRunRequest,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectRunResponse:
    """
    Self-Healing Run を発火する

    POST /api/v1/projects/{project_id}/run

    認証: X-API-Key ヘッダー必須
    """
    try:
        from nexuscore.webapp import db
        from nexuscore.webapp.celery_app import run_orchestrator_task
        from nexuscore.webapp.models import Project, Run
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        user_id = get_user_id_from_auth(current_user)

        project = Project.query.filter_by(id=project_id, owner_id=user_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        if not request.requirement:
            raise make_bad_request_error("requirement is required")

        run_id = uuid.uuid4().hex
        run = Run(
            project_id=project.id,
            run_id=run_id,
            triggered_by=user_id,
            status="PENDING",
            autonomy_level=request.autonomy_level,
            requirement=request.requirement,
            started_at=None,
            finished_at=None,
        )
        db.session.add(run)
        db.session.commit()

        use_celery = os.getenv("NEXUS_USE_CELERY", "1") == "1"

        if use_celery:
            run_orchestrator_task.delay(run.id)
            queue_mode = "async"
            status_code = status.HTTP_202_ACCEPTED
        else:
            try:
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement=request.requirement,
                    autonomy_level=request.autonomy_level,
                    fast_lane=request.fast_lane,
                )
                queue_mode = "sync"
                status_code = status.HTTP_200_OK
            except Exception as exc:
                db.session.refresh(run)
                logger.error(f"Failed to run orchestrator inline: {exc}", exc_info=True)
                raise make_internal_error(f"Failed to run orchestrator: {str(exc)}") from exc

        db.session.refresh(run)

        response.status_code = status_code

        return ProjectRunResponse(
            run_id=run.run_id,
            project_id=project.id,
            status=run.status,
            queue_mode=queue_mode,  # type: ignore[arg-type]
        )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Failed to trigger project run: {e}", exc_info=True)
        raise make_internal_error("Failed to trigger project run. Please try again later.") from e


@router.get(
    "/projects/{project_id}/runs/latest",
    response_model=LatestRunResponse,
    summary="Get latest run for project",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_latest_run(
    project_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LatestRunResponse:
    """
    最新の Run の概要を取得する

    GET /api/v1/projects/{project_id}/runs/latest

    認証: X-API-Key ヘッダー必須
    """
    try:
        from nexuscore.webapp.models import Project, Run

        user_id = get_user_id_from_auth(current_user)

        project = Project.query.filter_by(id=project_id, owner_id=user_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        run = Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).first()

        if not run:
            return LatestRunResponse(run=None)

        return LatestRunResponse(
            run=LatestRunDetail(
                id=run.id,
                run_id=run.run_id,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
        )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Failed to get latest run: {e}", exc_info=True)
        raise make_internal_error("Failed to get latest run. Please try again later.") from e
