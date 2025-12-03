"""
Badge エンドポイント

README バッジ向けのメトリクス API。
shields.io などで使用できる JSON エンドポイントを提供する。
既存の Flask 実装 (`src/nexuscore/webapp/api_badges.py`) と互換性を保つ。
"""
import logging
from sqlalchemy import desc

from fastapi import APIRouter, status

from ..schemas.badge import BadgeResponse
from ..schemas.error import ErrorResponse
from ..utils.errors import make_not_found_error, make_internal_error

router = APIRouter(tags=["badges"])

logger = logging.getLogger(__name__)


@router.get(
    "/projects/{project_id}/badge/success_rate",
    response_model=BadgeResponse,
    summary="Get project success rate badge",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def project_success_rate_badge(project_id: int) -> BadgeResponse:
    """
    プロジェクトの成功率バッジ用 JSON を返す（shields.io endpoint 互換）

    GET /api/projects/{project_id}/badge/success_rate

    認証: 不要（公開エンドポイント）

    レスポンス:
        {
            "schemaVersion": 1,
            "label": "self-healing",
            "message": "95.0% success",
            "color": "brightgreen"
        }

    ステータスコード:
        - 200: 成功
        - 404: プロジェクトが見つからない

    Args:
        project_id: プロジェクトID

    Returns:
        BadgeResponse: 成功率バッジ情報

    Raises:
        HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project, Run

        project = Project.query.filter_by(id=project_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        # 過去30回のRunを取得
        runs = Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).limit(30).all()

        if not runs:
            success_rate = 0.0
        else:
            success_count = sum(1 for r in runs if r.status == "SUCCESS")
            success_rate = success_count / len(runs) * 100.0

        # カラーを決定
        if success_rate >= 90:
            color = "brightgreen"
        elif success_rate >= 70:
            color = "green"
        elif success_rate >= 50:
            color = "yellow"
        else:
            color = "red"

        return BadgeResponse(
            schemaVersion=1,
            label="self-healing",
            message=f"{success_rate:.1f}% success",
            color=color,
        )

    except Exception as e:
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Failed to get success rate badge: {e}", exc_info=True)
        raise make_internal_error(f"Failed to get success rate badge: {str(e)}")


@router.get(
    "/projects/{project_id}/badge/last_run",
    response_model=BadgeResponse,
    summary="Get project last run badge",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def project_last_run_badge(project_id: int) -> BadgeResponse:
    """
    プロジェクトの最新Runステータスバッジ用 JSON を返す（shields.io endpoint 互換）

    GET /api/projects/{project_id}/badge/last_run

    認証: 不要（公開エンドポイント）

    レスポンス:
        {
            "schemaVersion": 1,
            "label": "self-healing",
            "message": "last: SUCCESS",
            "color": "brightgreen"
        }

    ステータスコード:
        - 200: 成功
        - 404: プロジェクトが見つからない

    Args:
        project_id: プロジェクトID

    Returns:
        BadgeResponse: 最新Runステータスバッジ情報

    Raises:
        HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）
    """
    try:
        from nexuscore.webapp.models import Project, Run

        project = Project.query.filter_by(id=project_id).first()

        if not project:
            raise make_not_found_error("Project", str(project_id))

        # 最新のRunを取得
        latest_run = Run.query.filter_by(project_id=project.id).order_by(desc(Run.started_at)).first()

        if not latest_run:
            return BadgeResponse(
                schemaVersion=1,
                label="self-healing",
                message="last: -",
                color="lightgrey",
            )

        status_str = (latest_run.status or "UNKNOWN").upper()

        # ステータスに応じたカラーとメッセージ
        if status_str == "SUCCESS":
            color = "brightgreen"
            message = "last: SUCCESS"
        elif status_str == "FAILED":
            color = "red"
            message = "last: FAILED"
        elif status_str == "RUNNING":
            color = "blue"
            message = "last: RUNNING"
        else:
            color = "lightgrey"
            message = f"last: {status_str}"

        return BadgeResponse(
            schemaVersion=1,
            label="self-healing",
            message=message,
            color=color,
        )

    except Exception as e:
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Failed to get last run badge: {e}", exc_info=True)
        raise make_internal_error(f"Failed to get last run badge: {str(e)}")

