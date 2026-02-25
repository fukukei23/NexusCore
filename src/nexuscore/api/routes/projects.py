"""
Projects エンドポイント

プロジェクト管理用の FastAPI エンドポイント。
既存の Flask 実装 (`src/nexuscore/webapp/api_external.py`) と互換性を保つ。
"""

import logging
import os

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import desc

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..schemas.error import ErrorResponse
from ..schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
)
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


def _get_user_id_from_auth(current_user: AuthenticatedUser) -> int:
    """
    認証済みユーザーからユーザーIDを取得するアダプター

    既存のFlask実装では `g.current_api_user.id` を使用しているが、
    FastAPI版では `AuthenticatedUser` から取得する必要がある。

    Args:
        current_user: 認証済みユーザー情報（user_id にユーザーIDが含まれる）

    Returns:
        int: ユーザーID

    Raises:
        HTTPException: ユーザーIDが無効な場合（500）
    """
    try:
        user_id = int(current_user.user_id)
        return user_id
    except (ValueError, TypeError):
        logger.error(f"Invalid user_id in AuthenticatedUser: {current_user.user_id}")
        raise make_internal_error("Invalid user ID in authentication token") from None


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

    レスポンス:
        {
            "projects": [
                {
                    "id": 1,
                    "name": "Project Name",
                    "repo_url": "https://github.com/owner/repo",
                    "local_path": "/path/to/project",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                }
            ]
        }

    Args:
        current_user: 認証済みユーザー情報

    Returns:
        ProjectListResponse: プロジェクト一覧

    Raises:
        HTTPException: 内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project

        user_id = _get_user_id_from_auth(current_user)

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
    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise make_internal_error(f"Failed to list projects: {str(e)}") from e


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

    リクエストボディ:
        {
            "name": "Project Name",
            "repo_url": "https://github.com/owner/repo",
            "local_path": "/path/to/project",
            "context_bundle_path": "/path/to/context.json"
        }

    レスポンス:
        {
            "id": 1,
            "name": "Project Name",
            "repo_url": "https://github.com/owner/repo",
            "local_path": "/path/to/project",
            "context_bundle_path": "/path/to/context.json",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }

    Args:
        payload: プロジェクト作成リクエスト
        current_user: 認証済みユーザー情報

    Returns:
        ProjectResponse: 作成されたプロジェクト情報

    Raises:
        HTTPException: バリデーションエラー時（400）または内部エラー時（500）
    """
    try:
        from nexuscore.webapp import db
        from nexuscore.webapp.models import Project

        user_id = _get_user_id_from_auth(current_user)

        # プロジェクトを作成
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
    except Exception as e:
        logger.error(f"Failed to create project: {e}", exc_info=True)
        db.session.rollback()
        raise make_internal_error(f"Failed to create project: {str(e)}") from e


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

    レスポンス:
        {
            "id": 1,
            "name": "Project Name",
            "repo_url": "https://github.com/owner/repo",
            "local_path": "/path/to/project",
            "context_bundle_path": "/path/to/context.json",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00"
        }

    Args:
        project_id: プロジェクトID
        current_user: 認証済みユーザー情報

    Returns:
        ProjectResponse: プロジェクト情報

    Raises:
        HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project

        user_id = _get_user_id_from_auth(current_user)

        # プロジェクトの所有権を確認
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

    except Exception as e:
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Failed to get project: {e}", exc_info=True)
        raise make_internal_error(f"Failed to get project: {str(e)}") from e


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

    リクエスト JSON:
        {
            "requirement": "Run self-healing for this repo",
            "autonomy_level": 2,
            "fast_lane": true
        }

    レスポンス:
        {
            "run_id": "abc123...",
            "project_id": 1,
            "status": "PENDING",
            "queue_mode": "async" または "sync"
        }

    ステータスコード:
        - 200: 同期実行完了
        - 202: 非同期実行開始（キューに入った）
        - 400: requirement が未指定
        - 404: プロジェクトが見つからない

    Args:
        project_id: プロジェクトID
        request: 実行リクエスト
        current_user: 認証済みユーザー情報

    Returns:
        ProjectRunResponse: 実行結果

    Raises:
        HTTPException: プロジェクトが見つからない場合（404）、requirement が未指定の場合（400）、または内部エラー時（500）
    """
    import uuid

    try:
        from nexuscore.webapp import db
        from nexuscore.webapp.celery_app import run_orchestrator_task
        from nexuscore.webapp.models import Project, Run
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        user_id = _get_user_id_from_auth(current_user)

        # プロジェクトの所有権を確認
        project = Project.query.filter_by(id=project_id, owner_id=user_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        # requirement の検証（Pydantic で既に検証済みだが、念のため）
        if not request.requirement:
            raise make_bad_request_error("requirement is required")

        # Run レコードを作成
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

        # Celery 使用フラグを確認
        use_celery = os.getenv("NEXUS_USE_CELERY", "1") == "1"

        if use_celery:
            # 非同期実行（Celery）
            run_orchestrator_task.delay(run.id)
            queue_mode = "async"
            status_code = status.HTTP_202_ACCEPTED
        else:
            # 同期実行
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
                # エラーが発生した場合でも Run レコードは作成済み
                db.session.refresh(run)
                logger.error(f"Failed to run orchestrator inline: {exc}", exc_info=True)
                raise make_internal_error(f"Failed to run orchestrator: {str(exc)}") from exc

        db.session.refresh(run)

        # ステータスコードを明示的に設定
        response.status_code = status_code

        return ProjectRunResponse(
            run_id=run.run_id,
            project_id=project.id,
            status=run.status,
            queue_mode=queue_mode,  # type: ignore[arg-type]
        )

    except Exception as e:
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Failed to trigger project run: {e}", exc_info=True)
        raise make_internal_error(f"Failed to trigger project run: {str(e)}") from e


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

    レスポンス:
        {
            "run": {
                "id": 1,
                "run_id": "abc123...",
                "status": "SUCCESS",
                "started_at": "2025-01-01T00:00:00",
                "finished_at": "2025-01-01T00:05:00"
            }
        }
        または
        {
            "run": null
        }

    ステータスコード:
        - 200: 成功
        - 404: プロジェクトが見つからない

    Args:
        project_id: プロジェクトID
        current_user: 認証済みユーザー情報

    Returns:
        LatestRunResponse: 最新Run情報

    Raises:
        HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project, Run

        user_id = _get_user_id_from_auth(current_user)

        # プロジェクトの所有権を確認
        project = Project.query.filter_by(id=project_id, owner_id=user_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        # 最新の Run を取得
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
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Failed to get latest run: {e}", exc_info=True)
        raise make_internal_error(f"Failed to get latest run: {str(e)}") from e
