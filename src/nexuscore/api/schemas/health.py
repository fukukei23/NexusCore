"""
Health check レスポンススキーマ

Health check エンドポイントのレスポンスモデル定義。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """
    Health check レスポンスモデル

    Attributes:
        status: API の稼働状況（"ok" 固定）
        version: API のバージョン
        timestamp: レスポンス生成時刻
    """

    status: Literal["ok"]
    version: str
    timestamp: datetime
