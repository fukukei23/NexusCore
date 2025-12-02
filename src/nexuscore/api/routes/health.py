"""
Health check エンドポイント

API の稼働状況を確認するためのエンドポイント。
認証不要な公開 API として扱う。
"""
from datetime import datetime

from fastapi import APIRouter

from ..schemas.health import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check エンドポイント

    API の稼働状況を返す。
    認証不要な公開エンドポイント。

    Returns:
        HealthCheckResponse: API の稼働状況とバージョン情報
    """
    return HealthCheckResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now()
    )

