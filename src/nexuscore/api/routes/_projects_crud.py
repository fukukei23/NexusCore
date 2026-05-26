import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc

from ..dependencies.auth import AuthenticatedUser, get_current_user, get_user_id_from_auth
from ..schemas.error import ErrorResponse
from ..schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
)
from ..utils.errors import make_internal_error

router = APIRouter(tags=["projects"])
logger = logging.getLogger(__name__)


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List projects",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def list_projects(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectListResponse:
    """
    プロジェクト一覧を取得する

    GET /api/v1/projects

    認証: X-API-Key ヘッダー必須
    """
    try:
        from nexuscore.webapp.models import Project

        user_id = get_user_id_from_auth(current_user)

        projects = (
            Project.query.filter_by(owner_id=user_id).order_by(desc(Project.created_at)).all()
        )

        data = [
            ProjectSummary(
                id=p.id,
                name=p.name,
                repo_url=p.repo_url,
                local_path=p.local_path,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in projects
        ]

        return ProjectListResponse(projects=data)

    except ImportError:
        logger.error("webapp models not available")
        raise make_internal_error("Database models not available") from None
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise make_internal_error("Failed to list projects. Please try again later.") from e


@router.post(
    "/projects",
    response_model=ProjectResponse,
    summary="Create project",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectResponse:
    """
    新規プロジェクトを作成する

    POST /api/v1/projects

    認証: X-API-Key ヘッダー必須
    """
    try:
        from nexuscore.webapp import db
        from nexuscore.webapp.models import Project

        user_id = get_user_id_from_auth(current_user)

        project = Project(
            owner_id=user_id,
            name=payload.name,
            repo_url=payload.repo_url,
            local_path=payload.local_path,
            context_bundle_path=payload.context_bundle_path,
        )
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)

        return ProjectResponse(
            id=project.id,
            name=project.name,
            repo_url=project.repo_url,
            local_path=project.local_path,
            context_bundle_path=project.context_bundle_path,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    except ImportError:
        logger.error("webapp models not available")
        raise make_internal_error("Database models not available") from None
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to create project: {e}", exc_info=True)
        db.session.rollback()
        raise make_internal_error("Failed to create project. Please try again later.") from e


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_project(
    project_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProjectResponse:
    """
    プロジェクトIDでプロジェクトを取得する

    GET /api/v1/projects/{project_id}

    認証: X-API-Key ヘッダー必須
    """
    from fastapi import HTTPException

    from ..utils.errors import make_not_found_error

    try:
        from nexuscore.webapp.models import Project

        user_id = get_user_id_from_auth(current_user)

        project = Project.query.filter_by(id=project_id, owner_id=user_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        return ProjectResponse(
            id=project.id,
            name=project.name,
            repo_url=project.repo_url,
            local_path=project.local_path,
            context_bundle_path=project.context_bundle_path,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    except Exception as e:  # noqa: BLE001
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Failed to get project: {e}", exc_info=True)
        raise make_internal_error("Failed to get project details. Please try again later.") from e
