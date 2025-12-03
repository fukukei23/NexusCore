"""
認証用 Dependency

FastAPI の Depends で使用する認証関連の Dependency。
API Key 認証（X-API-Key ヘッダー）を実装。

将来 JWT 方式を追加できる拡張性のための抽象構造を提供。
"""
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, Header, status
from pydantic import BaseModel

from ..utils.errors import make_unauthorized_error, make_internal_error

logger = logging.getLogger(__name__)


class AuthenticatedUser(BaseModel):
    """
    認証済みユーザー情報モデル

    Attributes:
        user_id: ユーザーID
        roles: ユーザーのロール一覧（将来の拡張用）
    """
    user_id: str
    roles: List[str] = []


def load_api_key() -> Optional[str]:
    """
    API Key を階層的に読み込む

    優先順位:
    1. 環境変数 `NEXUSCORE_API_KEY`
    2. secrets.json ファイル（プロジェクトルート）

    Returns:
        Optional[str]: API Key（見つからない場合は None）

    Note:
        将来の拡張: .env ファイルからの読み込みも追加可能
    """
    # 1. 環境変数から読み込み
    api_key = os.getenv("NEXUSCORE_API_KEY")
    if api_key:
        logger.debug("API Key loaded from environment variable")
        return api_key.strip()

    # 2. secrets.json から読み込み
    try:
        # プロジェクトルートを取得（src/nexuscore/api/dependencies/ から 3 階層上）
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        secrets_path = project_root / "secrets.json"

        if secrets_path.exists():
            with open(secrets_path, "r", encoding="utf-8") as f:
                secrets = json.load(f)
                api_key = secrets.get("NEXUSCORE_API_KEY")
                if api_key:
                    logger.debug("API Key loaded from secrets.json")
                    return api_key.strip()
    except Exception as e:
        logger.warning(f"Failed to load API Key from secrets.json: {e}")

    return None


# API Key をキャッシュ（起動時に一度だけ読み込む）
_cached_api_key: Optional[str] = None


def get_api_key() -> str:
    """
    有効な API Key を取得する

    Returns:
        str: API Key

    Raises:
        HTTPException: API Key が設定されていない場合（500）
    """
    global _cached_api_key

    if _cached_api_key is None:
        _cached_api_key = load_api_key()

    if not _cached_api_key:
        raise make_internal_error("Server misconfigured: NEXUSCORE_API_KEY is not set")

    return _cached_api_key


def get_current_user(
    x_api_key: str = Header(..., alias="X-API-Key", description="API Key for authentication")
) -> AuthenticatedUser:
    """
    現在の認証済みユーザーを取得する Dependency

    X-API-Key ヘッダーを使用した API Key 認証を実装。
    既存のFlask実装 (`api_key_required`) と互換性を保つため、
    データベースからAPI Keyを検証し、対応するユーザーを取得する。

    Args:
        x_api_key: X-API-Key ヘッダーの値

    Returns:
        AuthenticatedUser: 認証済みユーザー情報（user_id にユーザーIDを含む）

    Raises:
        HTTPException: 認証失敗時（401）またはサーバー設定エラー時（500）
    """
    try:
        from nexuscore.webapp.models import ApiKey, User

        # API Key からユーザーを解決（既存のFlask実装と同じロジック）
        token_hash = ApiKey.hash_token(x_api_key)
        api_key_obj = ApiKey.query.filter_by(token_hash=token_hash).first()

        if not api_key_obj:
            logger.warning("Invalid API Key provided")
            raise make_unauthorized_error("Invalid or missing API key")

        # User を取得
        user = api_key_obj.user if hasattr(api_key_obj, "user") else User.query.get(api_key_obj.user_id)

        if not user:
            logger.warning("User not found for API Key")
            raise make_unauthorized_error("Invalid or missing API key")

        # 認証成功
        logger.debug(f"API Key authentication successful for user {user.id}")
        return AuthenticatedUser(user_id=str(user.id), roles=["api_user"])

    except ImportError:
        # webapp モジュールが利用できない場合（テスト環境など）
        # 環境変数ベースの認証にフォールバック
        expected_api_key = get_api_key()
        if x_api_key != expected_api_key:
            logger.warning("Invalid API Key provided")
            raise make_unauthorized_error("Invalid or missing API key")
        logger.debug("API Key authentication successful (fallback mode)")
        return AuthenticatedUser(user_id="api_user", roles=["api_user"])
    except Exception as e:
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        logger.error(f"Authentication error: {e}", exc_info=True)
        raise make_internal_error("Authentication failed")


def get_current_user_optional(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="API Key for authentication (optional)")
) -> Optional[AuthenticatedUser]:
    """
    オプショナルな認証 Dependency

    認証が不要なエンドポイント（例: /api/v1/health）で使用する。
    ヘッダーが提供されていない場合は None を返す。

    Args:
        x_api_key: X-API-Key ヘッダーの値（オプション）

    Returns:
        Optional[AuthenticatedUser]: 認証済みユーザー情報（ヘッダーがない場合は None）

    Raises:
        HTTPException: API Key が提供されているが無効な場合（401）
    """
    if x_api_key is None:
        return None

    # API Key が提供されている場合は検証
    expected_api_key = get_api_key()
    if x_api_key != expected_api_key:
        logger.warning("Invalid API Key provided")
        raise make_unauthorized_error("Invalid or missing API key")

    return AuthenticatedUser(user_id="api_user", roles=["api_user"])
