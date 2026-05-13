from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    """
    Execute リクエストモデル

    Attributes:
        requirement: 実行する要件（必須）
        project_path: プロジェクトのパス（必須）
        constitution_text: プロジェクト憲法のテキスト（任意）
    """

    requirement: str = Field(..., description="実行する要件", min_length=1)
    project_path: str = Field(..., description="プロジェクトのパス", min_length=1)
    constitution_text: str | None = Field(
        None, description="プロジェクト憲法のテキスト（デフォルト: 'Default constitution.'）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "requirement": "Add a new feature",
                "project_path": "/path/to/project",
                "constitution_text": "Write clean, maintainable code.",
            }
        }


class ExecuteResponse(BaseModel):
    """
    Execute レスポンスモデル

    Attributes:
        message: メッセージ
        task_id: タスクID（UUID形式）
        status_url: ステータス確認用URL
    """

    message: str = Field(..., description="タスク受け入れメッセージ")
    task_id: str = Field(..., description="タスクID（UUID形式）")
    status_url: str = Field(..., description="ステータス確認用URL（相対パス）")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Task accepted and is running in the background.",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status_url": "/api/v1/status/123e4567-e89b-12d3-a456-426614174000",
            }
        }


class ExecuteStatusResponse(BaseModel):
    """
    Execute Status レスポンスモデル

    タスクの状態を表すモデル。既存のFlask実装では `tasks` 辞書の値がそのまま返されるため、
    柔軟な構造を許容する必要がある。

    Attributes:
        status: タスクの状態（"running", "completed", "error" など）
        message: ステータスメッセージ
    """

    status: str = Field(..., description="タスクの状態")
    message: str = Field(..., description="ステータスメッセージ")

    class Config:
        extra = "allow"  # 既存のFlask実装では追加フィールドが存在する可能性があるため
