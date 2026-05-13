from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    """
    Run サマリーモデル（一覧表示用）

    Attributes:
        id: Run ID（データベースID）
        run_id: Run ID（UUID形式）
        project_id: プロジェクトID
        status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）
        started_at: 開始日時
        finished_at: 終了日時
        created_at: 作成日時
    """

    id: int = Field(..., description="Run ID（データベースID）")
    run_id: str = Field(..., description="Run ID（UUID形式）")
    project_id: int = Field(..., description="プロジェクトID")
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(
        ..., description="ステータス"
    )
    started_at: datetime | None = Field(None, description="開始日時")
    finished_at: datetime | None = Field(None, description="終了日時")
    created_at: datetime = Field(..., description="作成日時")


class RunResponse(RunSummary):
    """
    Run 詳細レスポンスモデル

    Attributes:
        id: Run ID（データベースID）
        run_id: Run ID（UUID形式）
        project_id: プロジェクトID
        triggered_by: トリガーしたユーザーID
        status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）
        started_at: 開始日時
        finished_at: 終了日時
        autonomy_level: 自律レベル
        llm_model_summary: 使用されたLLMモデルの概要
        requirement: ユーザー要件
        created_at: 作成日時
    """

    triggered_by: int | None = Field(None, description="トリガーしたユーザーID")
    autonomy_level: int | None = Field(None, description="自律レベル")
    llm_model_summary: str | None = Field(None, description="使用されたLLMモデルの概要")
    requirement: str | None = Field(None, description="ユーザー要件")


class RunListResponse(BaseModel):
    """
    Run 一覧レスポンスモデル

    Attributes:
        runs: Run一覧
    """

    runs: list[RunSummary] = Field(..., description="Run一覧")

    class Config:
        json_schema_extra = {
            "example": {
                "runs": [
                    {
                        "id": 1,
                        "run_id": "abc123def456",
                        "project_id": 1,
                        "status": "SUCCESS",
                        "started_at": "2025-01-01T00:00:00",
                        "finished_at": "2025-01-01T00:05:00",
                        "created_at": "2025-01-01T00:00:00",
                    }
                ]
            }
        }
