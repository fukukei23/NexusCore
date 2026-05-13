from datetime import datetime

from pydantic import BaseModel, Field


class PlanTask(BaseModel):
    """
    計画タスクモデル

    Attributes:
        name: タスク名
        description: タスクの説明
        priority: 優先度（P0, P1, P2）
        status: ステータス（pending, in_progress, completed）
    """

    name: str = Field(..., description="タスク名")
    description: str = Field(..., description="タスクの説明")
    priority: str = Field(..., description="優先度（P0, P1, P2）")
    status: str = Field(default="pending", description="ステータス")


class PlanSummary(BaseModel):
    """
    Plan サマリーモデル（一覧表示用）

    Attributes:
        id: Plan ID
        project_id: プロジェクトID
        name: 計画名
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: int = Field(..., description="Plan ID")
    project_id: int = Field(..., description="プロジェクトID")
    name: str = Field(..., description="計画名")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")


class PlanResponse(PlanSummary):
    """
    Plan 詳細レスポンスモデル

    Attributes:
        id: Plan ID
        project_id: プロジェクトID
        name: 計画名
        tasks: タスク一覧
        created_at: 作成日時
        updated_at: 更新日時
    """

    tasks: list[PlanTask] = Field(default_factory=list, description="タスク一覧")


class PlanListResponse(BaseModel):
    """
    Plan 一覧レスポンスモデル

    Attributes:
        plans: Plan一覧
    """

    plans: list[PlanSummary] = Field(..., description="Plan一覧")

    class Config:
        json_schema_extra = {
            "example": {
                "plans": [
                    {
                        "id": 1,
                        "project_id": 1,
                        "name": "Implementation Plan",
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                    }
                ]
            }
        }
