"""
認証用 Dependency

FastAPI の Depends で使用する認証関連の Dependency。
現時点では雛形のみで、実装は CR-FASTAPI-003 で行う。
"""
from typing import Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """
    認証済みユーザー情報モデル

    Attributes:
        user_id: ユーザーID
        # 必要に応じてフィールド追加（email, role など）
    """
    user_id: str


async def get_current_user() -> AuthenticatedUser:
    """
    現在の認証済みユーザーを取得する Dependency

    現時点では未実装のため、常に 401 Unauthorized を返す。
    CR-FASTAPI-003 で JWT / API Key 実装に差し替える予定。

    Returns:
        AuthenticatedUser: 認証済みユーザー情報

    Raises:
        HTTPException: 認証が未実装または認証失敗時（401）
    """
    # TODO: CR-FASTAPI-003 で JWT / API Key 実装に差し替え
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication not implemented yet",
    )

