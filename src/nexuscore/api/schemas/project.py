import re
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

_SAFE_PATH_RE = re.compile(r"\.\.|\0")
_URL_SCHEMES = {"http", "https", "git", "ssh"}


def _validate_path_no_traversal(value: str | None) -> str | None:
    if value is None:
        return value
    if _SAFE_PATH_RE.search(value):
        raise ValueError("Path traversal characters are not allowed")
    return value


def _validate_repo_url(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme not in _URL_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}. Allowed: {', '.join(sorted(_URL_SCHEMES))}")
    return value


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
    repo_url: str | None = Field(None, description="リポジトリURL")
    local_path: str = Field(..., description="ローカルパス", min_length=1)
    context_bundle_path: str | None = Field(None, description="コンテキストバンドルパス")

    @field_validator("local_path", "context_bundle_path")
    @classmethod
    def validate_no_path_traversal(cls, v: str | None) -> str | None:
        return _validate_path_no_traversal(v)

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url_format(cls, v: str | None) -> str | None:
        return _validate_repo_url(v)


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
    repo_url: str | None = Field(None, description="リポジトリURL")
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

    context_bundle_path: str | None = Field(None, description="コンテキストバンドルパス")


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
                        "updated_at": "2025-01-01T00:00:00",
                    }
                ]
            }
        }
