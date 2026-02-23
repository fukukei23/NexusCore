"""
API Keys エンドポイント用の Pydantic スキーマ

API Key の発行・一覧取得・削除に関するリクエスト・レスポンスモデル。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyIssueRequest(BaseModel):
    """
    API Key 発行リクエスト
    """

    name: str | None = Field(
        None,
        description="API Key の名前（任意）。未指定の場合はデフォルト名が付けられます。",
        max_length=255,
    )
    expires_in_days: int | None = Field(
        None,
        description="有効期限（日数）。将来の拡張用。現在は無視されます。",
        ge=1,
        le=3650,  # 最大10年
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Local Dev Key",
                "expires_in_days": 90,
            }
        }


class ApiKeyMeta(BaseModel):
    """
    API Key のメタ情報（token は含まない）
    """

    id: int = Field(..., description="API Key ID")
    name: str = Field(..., description="API Key の名前", max_length=255)
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "name": "Local Dev Key",
                "created_at": "2025-12-08T12:34:56Z",
            }
        }


class ApiKeyIssueResponse(BaseModel):
    """
    API Key 発行レスポンス

    注意: token はこのレスポンスでのみ返却されます。
    他の API では token は返されません。
    """

    api_key: ApiKeyMeta = Field(..., description="API Key のメタ情報")
    token: str = Field(..., description="生の API Key（このレスポンスでのみ返却）")

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": {
                    "id": 123,
                    "name": "Local Dev Key",
                    "created_at": "2025-12-08T12:34:56Z",
                },
                "token": "nexus_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            }
        }


class ApiKeyListResponse(BaseModel):
    """
    API Key 一覧レスポンス
    """

    items: list[ApiKeyMeta] = Field(..., description="API Key のリスト")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 123,
                        "name": "Local Dev Key",
                        "created_at": "2025-12-08T12:34:56Z",
                    },
                    {
                        "id": 124,
                        "name": "CI/CD Key",
                        "created_at": "2025-12-09T10:20:30Z",
                    },
                ]
            }
        }
