import logging

from fastapi import APIRouter, Depends, Query, status

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..schemas.error import ErrorResponse
from ..schemas.plan import PlanListResponse

router = APIRouter(tags=["plans"])

logger = logging.getLogger(__name__)


@router.get(
    "/plans",
    response_model=PlanListResponse,
    summary="List plans",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def list_plans(
    project_id: int | None = Query(None, description="プロジェクトIDでフィルタ"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> PlanListResponse:
    """
    Plan一覧を取得する

    GET /api/v1/plans?project_id=1

    認証: X-API-Key ヘッダー必須

    クエリパラメータ:
        project_id: プロジェクトIDでフィルタ（任意）

    レスポンス:
        {
            "plans": [
                {
                    "id": 1,
                    "project_id": 1,
                    "name": "Implementation Plan",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                }
            ]
        }

    注意: 現時点では Plan モデルがデータベースに存在しないため、
    空のリストを返します。将来的に Plan モデルが実装されたら、
    実際のデータを返すように更新されます。

    Args:
        project_id: プロジェクトIDでフィルタ（任意）
        current_user: 認証済みユーザー情報

    Returns:
        PlanListResponse: Plan一覧（現時点では空のリスト）

    Raises:
        HTTPException: 内部エラー時（500）
    """
    # 現時点では Plan モデルが存在しないため、空のリストを返す
    # 将来的に Plan モデルが実装されたら、実際のデータを返すように更新
    logger.info("Plan list endpoint called (not yet implemented)")
    return PlanListResponse(plans=[])
