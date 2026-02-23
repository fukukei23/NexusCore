"""
Badge API レスポンススキーマ

FastAPI の Badge エンドポイント用の Pydantic モデル定義。
shields.io 互換形式。
既存の Flask 実装 (`src/nexuscore/webapp/api_badges.py`) の仕様に準拠。
"""

from typing import Literal

from pydantic import BaseModel, Field


class BadgeResponse(BaseModel):
    """
    Badge レスポンスモデル（shields.io 互換）

    Attributes:
        schemaVersion: スキーマバージョン（常に1）
        label: バッジラベル
        message: バッジメッセージ
        color: バッジカラー（brightgreen, green, yellow, red, blue, lightgrey）
    """

    schemaVersion: Literal[1] = Field(1, description="スキーマバージョン")
    label: str = Field(..., description="バッジラベル")
    message: str = Field(..., description="バッジメッセージ")
    color: Literal["brightgreen", "green", "yellow", "red", "blue", "lightgrey"] = Field(
        ..., description="バッジカラー"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "schemaVersion": 1,
                "label": "self-healing",
                "message": "95.0% success",
                "color": "brightgreen",
            }
        }
