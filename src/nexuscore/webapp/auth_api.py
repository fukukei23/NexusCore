"""
APIキー認証ヘルパー

外部統合 API 用の認証デコレータを提供する。
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, Any, Optional, cast

from flask import request, jsonify, g

from nexuscore.webapp.models import ApiKey, User

F = TypeVar("F", bound=Callable[..., Any])


def _resolve_user_from_api_key(raw_token: str) -> Optional[User]:
    """
    API キーから User を解決する

    Args:
        raw_token: 生の API キー（X-Api-Key ヘッダまたは api_key クエリパラメータ）

    Returns:
        有効な API キーの場合、対応する User オブジェクト。無効な場合は None。
    """
    if not raw_token:
        return None

    # 1. hash_token + token_hash で検索
    hash_fn = getattr(ApiKey, "hash_token", None)
    if callable(hash_fn):
        token_hash = hash_fn(raw_token)
        api_key_obj = ApiKey.query.filter_by(token_hash=token_hash).first()
    else:
        # フォールバック: token_hash 直接比較（MVP フォールバック）
        api_key_obj = ApiKey.query.filter_by(token_hash=raw_token).first()

    if not api_key_obj:
        return None

    # User を取得
    user = getattr(api_key_obj, "user", None)
    if user is None:
        # リレーションが読み込まれていない場合は明示的に取得
        from nexuscore.webapp.models import User
        user = User.query.get(api_key_obj.user_id)

    return user


def api_key_required(func: F) -> F:
    """
    API キー認証を要求するデコレータ

    使用例:
        @api_key_required
        def my_api_endpoint():
            user = g.current_api_user
            ...

    X-Api-Key ヘッダまたは api_key クエリパラメータから API キーを取得し、
    有効な場合は g.current_api_user に User をセットする。
    無効な場合は 401 JSON を返す。
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        raw_token = request.headers.get("X-Api-Key") or request.args.get("api_key")
        user = _resolve_user_from_api_key(raw_token or "")

        if user is None:
            return jsonify({"error": "Invalid or missing API key"}), 401

        g.current_api_user = user
        return func(*args, **kwargs)

    return cast(F, wrapper)

