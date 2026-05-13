from datetime import datetime

from fastapi import APIRouter

from ..schemas.error import ErrorResponse
from ..schemas.health import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        500: {"model": ErrorResponse},
    },
)
async def health_check() -> HealthCheckResponse:
    """
    Health check エンドポイント

    API の稼働状況を返す。
    認証不要な公開エンドポイント。

    将来的に認証が必要になった場合は、以下のように変更可能:
    ```python
    async def health_check(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> HealthCheckResponse:
    ```

    Returns:
        HealthCheckResponse: API の稼働状況とバージョン情報
    """
    return HealthCheckResponse(status="ok", version="1.0.0", timestamp=datetime.now())
