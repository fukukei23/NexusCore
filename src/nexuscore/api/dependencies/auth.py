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
        # CR-NEXUS-038: サーバー設定エラーを確実に検出するため、認証前に get_api_key() を呼ぶ
        try:
            get_api_key()
        except Exception:  # noqa: BLE001
            # get_api_key() が 500 を返す場合（サーバー設定エラー）はそのまま raise
            raise

        from sqlalchemy.exc import SQLAlchemyError

        from nexuscore.webapp.models import ApiKey, User

        # API Key からユーザーを解決（既存のFlask実装と同じロジック）
        try:
            token_hash = ApiKey.hash_token(x_api_key)
            # ApiKey.query が存在しない場合（DB が初期化されていない場合）は認証フェイルとして扱う
            if not hasattr(ApiKey, "query") or ApiKey.query is None:
                logger.warning("ApiKey.query is not available (database not initialized)")
                raise make_unauthorized_error("Invalid or missing API key")
            api_key_obj = ApiKey.query.filter_by(token_hash=token_hash).first()
        except (AttributeError, RuntimeError) as e:
            # ApiKey.query が存在しない場合、または DB が初期化されていない場合
            # RuntimeError は SQLAlchemy が DB コンテキストを持っていない場合に発生する可能性がある
            logger.warning(f"Database not initialized or query unavailable: {e}")
            raise make_unauthorized_error("Invalid or missing API key") from e
        except SQLAlchemyError as e:
            # DB アクセスエラー（接続エラーなど）
            logger.error(f"Database error during API Key lookup: {e}", exc_info=True)
            raise make_internal_error("Database connection error during authentication") from e
        except Exception as e:  # noqa: BLE001
            # HTTPException はそのまま再発生（make_error で生成されたもの）
            if isinstance(e, Exception) and hasattr(e, "status_code"):
                raise
            # その他の予期しないエラー（hash_token のエラーなど）
            # ただし、DB が初期化されていない可能性があるため、認証フェイルとして扱う
            error_str = str(e).lower()
            if "no application" in error_str or "context" in error_str or "query" in error_str:
                logger.warning(f"Database context error (likely DB not initialized): {e}")
                raise make_unauthorized_error("Invalid or missing API key") from None
            logger.error(f"Unexpected error during API Key hash: {e}", exc_info=True)
            raise make_internal_error("Unexpected error during authentication") from e

        # API Key が見つからない場合は認証フェイル（401）
        if not api_key_obj:
            logger.warning("Invalid API Key provided")
            raise make_unauthorized_error("Invalid or missing API key")

        # User を取得
        try:
            # User.query が存在しない場合（DB が初期化されていない場合）は認証フェイルとして扱う
            if hasattr(api_key_obj, "user") and api_key_obj.user is not None:
                user = api_key_obj.user
            else:
                if not hasattr(User, "query") or User.query is None:
                    logger.warning("User.query is not available (database not initialized)")
                    raise make_unauthorized_error("Invalid or missing API key")
                user = User.query.get(api_key_obj.user_id)
        except (AttributeError, RuntimeError) as e:
            # User.query が存在しない場合、または DB が初期化されていない場合
            # RuntimeError は SQLAlchemy が DB コンテキストを持っていない場合に発生する可能性がある
            logger.warning(f"Database not initialized or query unavailable: {e}")
            raise make_unauthorized_error("Invalid or missing API key") from e
        except SQLAlchemyError as e:
            # DB アクセスエラー（接続エラーなど）
            logger.error(f"Database error during User lookup: {e}", exc_info=True)
            raise make_internal_error("Database connection error during user lookup") from e
        except Exception as e:  # noqa: BLE001
            # HTTPException はそのまま再発生（make_error で生成されたもの）
            if isinstance(e, Exception) and hasattr(e, "status_code"):
                raise
            # その他の予期しないエラー
            # ただし、DB が初期化されていない可能性があるため、認証フェイルとして扱う
            error_str = str(e).lower()
            if "no application" in error_str or "context" in error_str or "query" in error_str:
                logger.warning(f"Database context error (likely DB not initialized): {e}")
                raise make_unauthorized_error("Invalid or missing API key") from None
            logger.error(f"Unexpected error during User lookup: {e}", exc_info=True)
            raise make_internal_error("Unexpected error during user lookup") from e

        # User が見つからない場合は認証フェイル（401）
        if not user:
            logger.warning("User not found for API Key")
            raise make_unauthorized_error("Invalid or missing API key")

        # 認証成功
        logger.debug(f"API Key authentication successful for user {user.id}")
        return AuthenticatedUser(user_id=str(user.id), roles=["api_user"])

    except ImportError:
        # webapp モジュールが利用できない場合（テスト環境など）
        # 環境変数ベースの認証にフォールバック
        try:
            expected_api_key = get_api_key()
        except Exception:  # noqa: BLE001
            # get_api_key() が 500 を返す場合（サーバー設定エラー）
            # これは認証フェイルではなく、サーバー側の問題なので 500 をそのまま返す
            raise

        if x_api_key != expected_api_key:
            logger.warning("Invalid API Key provided")
            raise make_unauthorized_error("Invalid or missing API key") from None
        logger.debug("API Key authentication successful (fallback mode)")
        return AuthenticatedUser(user_id="api_user", roles=["api_user"])
    except Exception as e:  # noqa: BLE001
        # HTTPException はそのまま再発生（make_error で生成されたもの）
        if isinstance(e, Exception) and hasattr(e, "status_code"):
            raise
        # この時点で到達するのは、予期しない例外のみ
        # 認証フェイルではないことを明示
        logger.error(
            f"Unexpected error during authentication (not an authentication failure): {e}",
            exc_info=True,
        )
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
