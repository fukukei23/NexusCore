import json
import logging
import os
from pathlib import Path

from fastapi import Header
from pydantic import BaseModel

from ..utils.errors import make_internal_error, make_unauthorized_error

logger = logging.getLogger(__name__)


class AuthenticatedUser(BaseModel):
    """
    認証済みユーザー情報モデル

    Attributes:
        user_id: ユーザーID
        roles: ユーザーのロール一覧（将来の拡張用）
    """

    user_id: str
    roles: list[str] = []


def load_api_key() -> str | None:
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
            with open(secrets_path, encoding="utf-8") as f:
                secrets = json.load(f)
                api_key = secrets.get("NEXUSCORE_API_KEY")
                if api_key:
                    logger.debug("API Key loaded from secrets.json")
                    return api_key.strip()
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to load API Key from secrets.json: {e}")

    return None


# API Key をキャッシュ（起動時に一度だけ読み込む）
_cached_api_key: str | None = None


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


def _resolve_api_key_obj(x_api_key: str):
    """API Key ハッシュから ApiKey オブジェクトを検索する。見つからない場合は例外を投げる。"""
    from sqlalchemy.exc import SQLAlchemyError

    from nexuscore.webapp.models import ApiKey

    try:
        token_hash = ApiKey.hash_token(x_api_key)
        if not hasattr(ApiKey, "query") or ApiKey.query is None:
            logger.warning("ApiKey.query is not available (database not initialized)")
            raise make_unauthorized_error("Invalid or missing API key")
        return ApiKey.query.filter_by(token_hash=token_hash).first()
    except (AttributeError, RuntimeError) as e:
        logger.warning(f"Database not initialized or query unavailable: {e}")
        raise make_unauthorized_error("Invalid or missing API key") from e
    except SQLAlchemyError as e:
        logger.error(f"Database error during API Key lookup: {e}", exc_info=True)
        raise make_internal_error("Database connection error during authentication") from e
    except Exception as e:  # noqa: BLE001
        if hasattr(e, "status_code"):
            raise
        error_str = str(e).lower()
        if "no application" in error_str or "context" in error_str or "query" in error_str:
            raise make_unauthorized_error("Invalid or missing API key") from None
        logger.error(f"Unexpected error during API Key hash: {e}", exc_info=True)
        raise make_internal_error("Unexpected error during authentication") from e


def _resolve_user(api_key_obj):
    """ApiKey オブジェクトから User を取得する。見つからない場合は例外を投げる。"""
    from sqlalchemy.exc import SQLAlchemyError

    from nexuscore.webapp.models import User

    try:
        if hasattr(api_key_obj, "user") and api_key_obj.user is not None:
            return api_key_obj.user
        if not hasattr(User, "query") or User.query is None:
            raise make_unauthorized_error("Invalid or missing API key")
        return User.query.get(api_key_obj.user_id)
    except (AttributeError, RuntimeError) as e:
        logger.warning(f"Database not initialized or query unavailable: {e}")
        raise make_unauthorized_error("Invalid or missing API key") from e
    except SQLAlchemyError as e:
        logger.error(f"Database error during User lookup: {e}", exc_info=True)
        raise make_internal_error("Database connection error during user lookup") from e
    except Exception as e:  # noqa: BLE001
        if hasattr(e, "status_code"):
            raise
        error_str = str(e).lower()
        if "no application" in error_str or "context" in error_str or "query" in error_str:
            raise make_unauthorized_error("Invalid or missing API key") from None
        logger.error(f"Unexpected error during User lookup: {e}", exc_info=True)
        raise make_internal_error("Unexpected error during user lookup") from e


def get_current_user(
    x_api_key: str = Header(..., alias="X-API-Key", description="API Key for authentication")
) -> AuthenticatedUser:
    """
    現在の認証済みユーザーを取得する Dependency

    X-API-Key ヘッダーを使用した API Key 認証を実装。
    """
    try:
        get_api_key()

        api_key_obj = _resolve_api_key_obj(x_api_key)
        if not api_key_obj:
            raise make_unauthorized_error("Invalid or missing API key")

        user = _resolve_user(api_key_obj)
        if not user:
            raise make_unauthorized_error("Invalid or missing API key")

        return AuthenticatedUser(user_id=str(user.id), roles=["api_user"])

    except ImportError:
        expected_api_key = get_api_key()
        if x_api_key != expected_api_key:
            raise make_unauthorized_error("Invalid or missing API key") from None
        return AuthenticatedUser(user_id="api_user", roles=["api_user"])
    except Exception as e:  # noqa: BLE001
        if hasattr(e, "status_code"):
            raise
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        raise make_internal_error("Unexpected server error during authentication") from e


def get_current_user_optional(
    x_api_key: str | None = Header(
        None, alias="X-API-Key", description="API Key for authentication (optional)"
    )
) -> AuthenticatedUser | None:
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


def get_user_id_from_auth(current_user: AuthenticatedUser) -> int:
    """認証済みユーザーからユーザーIDを取得するアダプター

    FastAPI版では AuthenticatedUser.user_id (str) を int に変換する。
    """
    return int(current_user.user_id)
