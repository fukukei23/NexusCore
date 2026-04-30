"""
API認証ユーティリティ

JWTトークンベースの認証を提供する。
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from functools import wraps

from flask import jsonify, request

try:
    import jwt

    HAS_JWT = True
except Exception as e:
    HAS_JWT = False
    jwt = None  # type: ignore
    logging.warning(
        f"PyJWT not available ({type(e).__name__}). JWT authentication will be disabled."
    )

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-INSECURE-DEFAULT")
ALGORITHM = "HS256"


def require_auth(f):
    """
    API認証デコレータ

    使用方法:
        @app.route('/api/v1/secure-endpoint', methods=['POST'])
        @require_auth
        def secure_endpoint():
            ...

    認証方法:
        Authorization: Bearer <JWT_TOKEN>

    Returns:
        401: トークンがない、または無効
        403: トークンの権限不足
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not HAS_JWT:
            return jsonify({"error": "JWT authentication not available. Install PyJWT."}), 503

        # Authorization ヘッダーからトークンを取得
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401

        # "Bearer <token>" 形式を想定
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return (
                jsonify({"error": "Invalid authorization header format. Use: Bearer <token>"}),
                401,
            )

        token = parts[1]

        try:
            # トークンを検証
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # デコードされたペイロードを request にアタッチ（必要に応じて使用可能）
            request.auth_payload = payload
        except Exception as e:
            # jwt.ExpiredSignatureError, jwt.InvalidTokenError など
            error_name = type(e).__name__
            if "ExpiredSignature" in error_name:
                return jsonify({"error": "Token has expired"}), 401
            else:
                return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        return f(*args, **kwargs)

    return decorated_function


def generate_token(user_id: str, expires_in_hours: int = 24) -> str:
    """
    JWTトークンを生成する

    Args:
        user_id: ユーザーID
        expires_in_hours: トークンの有効期限（時間）

    Returns:
        JWT トークン文字列

    Example:
        >>> token = generate_token("admin-user", expires_in_hours=1)
        >>> # このトークンを Authorization: Bearer <token> で使用
    """
    if not HAS_JWT:
        raise ImportError("PyJWT not available. Install with: pip install pyjwt")

    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=expires_in_hours),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """
    トークンを検証してペイロードを返す

    Args:
        token: JWTトークン

    Returns:
        検証成功時: ペイロード辞書
        検証失敗時: None
    """
    if not HAS_JWT:
        logging.warning("PyJWT not available. Cannot verify token.")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        # jwt.InvalidTokenError など
        return None
