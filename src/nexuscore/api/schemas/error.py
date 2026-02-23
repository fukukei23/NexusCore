"""
標準化されたエラーレスポンススキーマ

すべての API エンドポイントで統一されたエラー構造を提供する。

エラーコードの仕様:
- すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されている必要があります
- 新しいエラーコードを追加する場合は、必ず ERROR_CODE_CATALOG.md にも追記してください
- ERROR_CODE_CATALOG.md がエラーコードの単一のソース（Single Source of Truth）です

詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
"""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    エラー詳細モデル

    Attributes:
        code: エラーコード（例: "NOT_FOUND", "VALIDATION_ERROR", "UNAUTHORIZED"）
            - すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されている必要があります
            - 詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください
        message: 人間が読めるエラーメッセージ
    """

    code: str = Field(
        ..., description="エラーコード（ERROR_CODE_CATALOG.md に定義されたコードのみ使用）"
    )
    message: str = Field(..., description="人間が読めるエラーメッセージ")


class ErrorResponse(BaseModel):
    """
    標準化されたエラーレスポンスモデル

    すべての API エンドポイントで統一されたエラー構造。

    エラーコードの仕様:
    - すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されている必要があります
    - 新しいエラーコードを追加する場合は、必ず ERROR_CODE_CATALOG.md にも追記してください
    - ERROR_CODE_CATALOG.md がエラーコードの単一のソース（Single Source of Truth）です

    Attributes:
        error: エラー詳細情報

    詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """

    error: ErrorDetail = Field(..., description="エラー詳細情報")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {"code": "PROJECT_NOT_FOUND", "message": "Project with id 123 not found"}
            }
        }
