"""
Run Records エンドポイント（DBベースのRun管理）

CR-NEXUS-032: Moved from /api/v1/runs to /api/v1/run-records to avoid collision with RunView endpoints.

Run管理用の FastAPI エンドポイント（DBベース）。
既存の Flask 実装 (`src/nexuscore/webapp/api_external.py`) と互換性を保つ。
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..schemas.error import ErrorResponse
from ..schemas.run import RunListResponse, RunResponse, RunSummary
from ..utils.errors import (
    make_internal_error,
    make_not_found_error,
)

router = APIRouter(tags=["run-records"], prefix="/run-records")

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
    "",
    response_model=RunListResponse,
    summary="List run records",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def list_runs(
    project_id: int | None = Query(None, description="プロジェクトIDでフィルタ"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunListResponse:
    """
    Run一覧を取得する（DBベース）

    GET /api/v1/run-records?project_id=1

    認証: X-API-Key ヘッダー必須

    クエリパラメータ:
        project_id: プロジェクトIDでフィルタ（任意）

    レスポンス:
        {
            "runs": [
                {
                    "id": 1,
                    "run_id": "abc123def456",
                    "project_id": 1,
                    "status": "SUCCESS",
                    "started_at": "2025-01-01T00:00:00",
                    "finished_at": "2025-01-01T00:05:00",
                    "created_at": "2025-01-01T00:00:00"
                }
            ]
        }

    Args:
        project_id: プロジェクトIDでフィルタ（任意）
        current_user: 認証済みユーザー情報

    Returns:
        RunListResponse: Run一覧

    Raises:
        HTTPException: 内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project, Run

        user_id = _get_user_id_from_auth(current_user)

        # ユーザーが所有するプロジェクトのRunのみ取得
        query = Run.query.join(Project).filter(Project.owner_id == user_id)

        if project_id:
            query = query.filter(Run.project_id == project_id)

        runs = query.order_by(desc(Run.created_at)).all()

        data = [
            RunSummary(
                id=r.id,
                run_id=r.run_id,
                project_id=r.project_id,
                status=r.status,
                started_at=r.started_at,
                finished_at=r.finished_at,
                created_at=r.created_at,
            )
            for r in runs
        ]

        return RunListResponse(runs=data)

    except ImportError:
        logger.error("webapp models not available")
        raise make_internal_error("Database models not available") from None
    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise make_internal_error(f"Failed to list runs: {str(e)}") from e


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get run record by ID",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RunResponse:
    """
    Run IDでRunを取得する（DBベース）

    GET /api/v1/run-records/{run_id}

    認証: X-API-Key ヘッダー必須

    レスポンス:
        {
            "id": 1,
            "run_id": "abc123def456",
            "project_id": 1,
            "triggered_by": 1,
            "status": "SUCCESS",
            "started_at": "2025-01-01T00:00:00",
            "finished_at": "2025-01-01T00:05:00",
            "autonomy_level": 2,
            "llm_model_summary": "gpt-4",
            "requirement": "Run self-healing",
            "created_at": "2025-01-01T00:00:00"
        }

    Args:
        run_id: Run ID（UUID形式）
        current_user: 認証済みユーザー情報

    Returns:
        RunResponse: Run情報

    Raises:
        HTTPException: Runが見つからない場合（404）または内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project, Run

        user_id = _get_user_id_from_auth(current_user)

        # Runを取得し、所有権を確認
        run = (
            Run.query.join(Project)
            .filter(Run.run_id == run_id, Project.owner_id == user_id)
            .first()
        )

        if not run:
            raise make_not_found_error("Run", run_id)

        return RunResponse(
            id=run.id,
            run_id=run.run_id,
            project_id=run.project_id,
            triggered_by=run.triggered_by,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            autonomy_level=run.autonomy_level,
            llm_model_summary=run.llm_model_summary,
            requirement=run.requirement,
            created_at=run.created_at,
        )

    except Exception as e:
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Failed to get run: {e}", exc_info=True)
        raise make_internal_error(f"Failed to get run: {str(e)}") from e
