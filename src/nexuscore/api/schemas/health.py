"""
Health check レスポンススキーマ

Health check エンドポイントのレスポンスモデル定義。
"""
from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """
    Health check レスポンスモデル

    Attributes:
        status: API の稼働状況（"ok" など）
        version: API のバージョン（オプション）
    """
    status: str
    version: str | None = None

