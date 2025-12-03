"""
Project API リクエスト・レスポンススキーマ

FastAPI の Project エンドポイント用の Pydantic モデル定義。
既存の Flask 実装 (`src/nexuscore/webapp/api_external.py`) の仕様に準拠。
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """
    Project の基本フィールド

    Attributes:
        name: プロジェクト名
        repo_url: リポジトリURL（任意）
        local_path: ローカルパス（必須）
        context_bundle_path: コンテキストバンドルパス（任意）
    """
    name: str = Field(..., description="プロジェクト名", min_length=1)
    repo_url: Optional[str] = Field(None, description="リポジトリURL")
    local_path: str = Field(..., description="ローカルパス", min_length=1)
    context_bundle_path: Optional[str] = Field(None, description="コンテキストバンドルパス")


class ProjectCreateRequest(ProjectBase):
    """
    Project 作成リクエストモデル

    Attributes:
        name: プロジェクト名（必須）
        repo_url: リポジトリURL（任意）
        local_path: ローカルパス（必須）
        context_bundle_path: コンテキストバンドルパス（任意）
    """
    pass


class ProjectSummary(BaseModel):
    """
    Project サマリーモデル（一覧表示用）

    Attributes:
        id: プロジェクトID
        name: プロジェクト名
        repo_url: リポジトリURL
        local_path: ローカルパス
        created_at: 作成日時
        updated_at: 更新日時
    """
    id: int = Field(..., description="プロジェクトID")
    name: str = Field(..., description="プロジェクト名")
    repo_url: Optional[str] = Field(None, description="リポジトリURL")
    local_path: str = Field(..., description="ローカルパス")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")


class ProjectResponse(ProjectSummary):
    """
    Project 詳細レスポンスモデル

    Attributes:
        id: プロジェクトID
        name: プロジェクト名
        repo_url: リポジトリURL
        local_path: ローカルパス
        context_bundle_path: コンテキストバンドルパス
        created_at: 作成日時
        updated_at: 更新日時
    """
    context_bundle_path: Optional[str] = Field(None, description="コンテキストバンドルパス")


class ProjectListResponse(BaseModel):
    """
    Project 一覧レスポンスモデル

    Attributes:
        projects: プロジェクト一覧
    """
    projects: list[ProjectSummary] = Field(..., description="プロジェクト一覧")

    class Config:
        json_schema_extra = {
            "example": {
                "projects": [
                    {
                        "id": 1,
                        "name": "My Project",
                        "repo_url": "https://github.com/owner/repo",
                        "local_path": "/path/to/project",
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00"
                    }
                ]
            }
        }

