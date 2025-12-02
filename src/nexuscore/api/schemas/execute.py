"""
Execute エンドポイントのリクエスト/レスポンススキーマ

Self-healing ジョブ実行のためのリクエストとレスポンスモデル定義。
"""
from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """
    Execute エンドポイントのリクエストモデル

    Attributes:
        requirement: 実行要件（必須）
        project_path: プロジェクトパス（必須）
        constitution_text: 憲法テキスト（オプション、デフォルト: "Default constitution."）
    """
    requirement: str = Field(..., description="実行要件")
    project_path: str = Field(..., description="プロジェクトパス")
    constitution_text: str | None = Field(
        default="Default constitution.",
        description="憲法テキスト（オプション）"
    )


class ExecuteResponse(BaseModel):
    """
    Execute エンドポイントのレスポンスモデル

    Attributes:
        message: メッセージ
        task_id: タスクID（UUID）
        status_url: ステータス確認用URL
    """
    message: str = Field(..., description="タスク受け入れメッセージ")
    task_id: str = Field(..., description="タスクID（UUID）")
    status_url: str = Field(..., description="ステータス確認用URL")

