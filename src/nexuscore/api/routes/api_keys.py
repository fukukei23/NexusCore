"""
API Keys エンドポイント

API Key の発行・一覧取得・削除を提供する FastAPI エンドポイント。
認証済みユーザーが自身の API Key を管理できます。
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import SQLAlchemyError

from ..dependencies.auth import AuthenticatedUser, get_current_user
from ..schemas.api_keys import (
    ApiKeyIssueRequest,
    ApiKeyIssueResponse,
    ApiKeyListResponse,
    ApiKeyMeta,
)
from ..schemas.error import ErrorResponse
from ..utils.errors import (
    make_forbidden_error,
    make_internal_error,
    make_not_found_error,
)

router = APIRouter(tags=["api-keys"])

logger = logging.getLogger(__name__)

# API Key 発行数の上限（1ユーザーあたり）
MAX_API_KEYS_PER_USER = 5


def _get_user_id_from_auth(current_user: AuthenticatedUser) -> int:
    """
    認証済みユーザーからユーザーIDを取得するアダプター

    Args:
        current_user: 認証済みユーザー情報

    Returns:
        int: ユーザーID

    Raises:
        HTTPException: ユーザーIDが無効な場合（500）
    """
    try:
        user_id = int(current_user.user_id)
        return user_id
    except (ValueError, TypeError):
        logger.error(f"Invalid user_id in AuthenticatedUser: {current_user.user_id}")
        raise make_internal_error("Invalid user ID in authentication token") from None


@router.post(
    "/api-keys",
    response_model=ApiKeyIssueResponse,
    summary="Issue API Key",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def issue_api_key(
    request: ApiKeyIssueRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ApiKeyIssueResponse:
    """
    API Key を新規発行する

    POST /api/v1/api-keys

    認証: X-API-Key ヘッダー必須（既存の API Key で認証）

    リクエストボディ:
        {
            "name": "Local Dev Key",      // 任意
            "expires_in_days": 90         // 将来用（現在は無視）
        }

    レスポンス:
        {
            "api_key": {
                "id": 123,
                "name": "Local Dev Key",
                "created_at": "2025-12-08T12:34:56Z"
            },
            "token": "nexus_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }

    制約:
        - 1ユーザーあたり最大5個の API Key を発行可能
        - token はこのレスポンスでのみ返却（他の API では返さない）
        - DB には token_hash のみ保存（生 token は保存しない）

    Raises:
        HTTPException: 認証失敗（401）、上限超過（403）、内部エラー（500）
    """
    try:
        from nexuscore.webapp import db
        from nexuscore.webapp.models import ApiKey

        user_id = _get_user_id_from_auth(current_user)

        # Flask アプリコンテキストが必要な場合の処理
        # FastAPI から Flask の DB セッションを使用するため
        try:
            # 既存の API Key 数を確認
            existing_count = ApiKey.query.filter_by(user_id=user_id).count()

            if existing_count >= MAX_API_KEYS_PER_USER:
                logger.warning(
                    f"User {user_id} attempted to create API key but limit exceeded ({existing_count}/{MAX_API_KEYS_PER_USER})"
                )
                raise make_forbidden_error(
                    f"API key limit exceeded. Maximum {MAX_API_KEYS_PER_USER} keys per user."
                )

            # 新しい API Key を生成
            raw_token = ApiKey.generate_token()
            token_hash = ApiKey.hash_token(raw_token)

            # 名前が指定されていない場合はデフォルト名を付ける
            key_name = request.name or f"API Key {existing_count + 1}"

            # DB に保存
            api_key = ApiKey(
                user_id=user_id,
                token_hash=token_hash,
                name=key_name,
            )

            db.session.add(api_key)
            db.session.commit()

            logger.info(f"API key created for user {user_id}: id={api_key.id}, name={key_name}")

            # レスポンスを構築（token はこの時点でのみ返却）
            return ApiKeyIssueResponse(
                api_key=ApiKeyMeta(
                    id=api_key.id,
                    name=api_key.name,
                    created_at=api_key.created_at,
                ),
                token=raw_token,  # 生 token はこのレスポンスでのみ返却
            )

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during API key creation: {e}", exc_info=True)
            raise make_internal_error("Failed to create API key") from e

    except Exception as e:
        # HTTPException はそのまま再発生
        if hasattr(e, "status_code"):
            raise
        logger.error(f"Unexpected error during API key creation: {e}", exc_info=True)
        raise make_internal_error("Unexpected error during API key creation") from e


@router.get(
    "/api-keys",
    response_model=ApiKeyListResponse,
    summary="List API Keys",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def list_api_keys(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ApiKeyListResponse:
    """
    API Key 一覧を取得する

    GET /api/v1/api-keys

    認証: X-API-Key ヘッダー必須

    レスポンス:
        {
            "items": [
                {
                    "id": 123,
                    "name": "Local Dev Key",
                    "created_at": "2025-12-08T12:34:56Z"
                },
                ...
            ]
        }

    注意: token は返されません（セキュリティ上の理由）。
    """
    try:
        from nexuscore.webapp.models import ApiKey

        user_id = _get_user_id_from_auth(current_user)

        # ユーザーの API Key 一覧を取得
        api_keys = ApiKey.query.filter_by(user_id=user_id).order_by(ApiKey.created_at.desc()).all()

        # レスポンスを構築（token は含めない）
        items = [
            ApiKeyMeta(
                id=key.id,
                name=key.name,
                created_at=key.created_at,
            )
            for key in api_keys
        ]

        return ApiKeyListResponse(items=items)

    except SQLAlchemyError as e:
        logger.error(f"Database error during API key list: {e}", exc_info=True)
        raise make_internal_error("Failed to retrieve API keys") from e

    except Exception as e:
        # HTTPException はそのまま再発生
        if hasattr(e, "status_code"):
            raise
        logger.error(f"Unexpected error during API key list: {e}", exc_info=True)
        raise make_internal_error("Unexpected error during API key list") from e


@router.delete(
    "/api-keys/{api_key_id}",
    summary="Revoke API Key",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def revoke_api_key(
    api_key_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """
    API Key を無効化する

    DELETE /api/v1/api-keys/{api_key_id}

    認証: X-API-Key ヘッダー必須

    振る舞い:
        - 指定された API Key が存在し、かつ現在のユーザーのものである場合のみ削除
        - 他ユーザーの API Key へのアクセスは 403 Forbidden
        - 存在しない API Key へのアクセスは 404 Not Found

    Args:
        api_key_id: 無効化する API Key の ID

    Raises:
        HTTPException: 認証失敗（401）、権限なし（403）、見つからない（404）、内部エラー（500）
    """
    try:
        from nexuscore.webapp import db
        from nexuscore.webapp.models import ApiKey

        user_id = _get_user_id_from_auth(current_user)

        # API Key を取得
        api_key = ApiKey.query.filter_by(id=api_key_id).first()

        if not api_key:
            raise make_not_found_error("API Key", str(api_key_id))

        # 他ユーザーの API Key へのアクセスを拒否
        if api_key.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to delete API key {api_key_id} owned by user {api_key.user_id}"
            )
            raise make_forbidden_error("You do not have permission to delete this API key")

        # 物理削除（現在の ApiKey モデルには revoked_at フィールドがない）
        # 将来の拡張: revoked_at フィールドを追加して logical delete に変更可能
        db.session.delete(api_key)
        db.session.commit()

        logger.info(f"API key {api_key_id} revoked by user {user_id}")

        # 204 No Content を返す（FastAPI は自動的に処理）

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during API key revocation: {e}", exc_info=True)
        raise make_internal_error("Failed to revoke API key") from e

    except Exception as e:
        # HTTPException はそのまま再発生
        if hasattr(e, "status_code"):
            raise
        logger.error(f"Unexpected error during API key revocation: {e}", exc_info=True)
        raise make_internal_error("Unexpected error during API key revocation") from e
