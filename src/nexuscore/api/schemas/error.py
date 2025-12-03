"""
標準化されたエラーレスポンススキーマ

すべての API エンドポイントで統一されたエラー構造を提供する。
"""
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    エラー詳細モデル

    Attributes:
        code: エラーコード（例: "PROJECT_NOT_FOUND", "VALIDATION_ERROR"）
        message: 人間が読めるエラーメッセージ
    """
    code: str = Field(..., description="エラーコード")
    message: str = Field(..., description="人間が読めるエラーメッセージ")


class ErrorResponse(BaseModel):
    """
    標準化されたエラーレスポンスモデル

    すべての API エンドポイントで統一されたエラー構造。

    Attributes:
        error: エラー詳細情報
    """
    error: ErrorDetail = Field(..., description="エラー詳細情報")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "PROJECT_NOT_FOUND",
                    "message": "Project with id 123 not found"
                }
            }
        }

