"""
Project Run API リクエスト・レスポンススキーマ

FastAPI の Project Run エンドポイント用の Pydantic モデル定義。
既存の Flask 実装 (`src/nexuscore/webapp/api_external.py`) の仕様に準拠。
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProjectRunRequest(BaseModel):
    """
    Project Run リクエストモデル

    Attributes:
        requirement: ユーザー要件（必須）
        autonomy_level: 自律レベル（デフォルト: 2）
        fast_lane: 高速レーン実行フラグ（デフォルト: False）
    """

    requirement: str = Field(..., description="ユーザー要件", min_length=1)
    autonomy_level: int = Field(2, description="自律レベル", ge=1, le=5)
    fast_lane: bool = Field(False, description="高速レーン実行フラグ")


class ProjectRunResponse(BaseModel):
    """
    Project Run レスポンスモデル

    Attributes:
        run_id: Run ID（UUID形式）
        project_id: プロジェクトID
        status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）
        queue_mode: キューモード（"async" または "sync"）
    """

    run_id: str = Field(..., description="Run ID（UUID形式）")
    project_id: int = Field(..., description="プロジェクトID")
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(
        ..., description="ステータス"
    )
    queue_mode: Literal["async", "sync"] = Field(..., description="キューモード")

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "abc123def456",
                "project_id": 1,
                "status": "PENDING",
                "queue_mode": "async",
            }
        }


class LatestRunResponse(BaseModel):
    """
    最新Runレスポンスモデル

    Attributes:
        run: 最新Run情報（存在しない場合は null）
    """

    run: Optional["LatestRunDetail"] = Field(None, description="最新Run情報")

    class Config:
        json_schema_extra = {
            "example": {
                "run": {
                    "id": 1,
                    "run_id": "abc123def456",
                    "status": "SUCCESS",
                    "started_at": "2025-01-01T00:00:00",
                    "finished_at": "2025-01-01T00:05:00",
                }
            }
        }


class LatestRunDetail(BaseModel):
    """
    最新Run詳細モデル

    Attributes:
        id: Run ID（データベースID）
        run_id: Run ID（UUID形式）
        status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）
        started_at: 開始日時
        finished_at: 終了日時
    """

    id: int = Field(..., description="Run ID（データベースID）")
    run_id: str = Field(..., description="Run ID（UUID形式）")
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(
        ..., description="ステータス"
    )
    started_at: datetime | None = Field(None, description="開始日時")
    finished_at: datetime | None = Field(None, description="終了日時")


# Forward reference を解決
LatestRunResponse.model_rebuild()
