from __future__ import annotations

import os
import logging

import requests
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from nexuscore.webapp import db
from nexuscore.webapp.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:8000/api/v1/auth/github/callback"
)

oauth = OAuth()


def init_oauth(app):
    """OAuthクライアントを初期化。FastAPI app の startup で呼ぶ。"""
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        userinfo_endpoint="https://api.github.com/user",
        client_kwargs={"scope": "read:user user:email"},
    )


@router.get("/login/github")
async def login_github(request: Request):
    """GitHub OAuth ログイン開始"""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return JSONResponse(
            status_code=500,
            content={"error": "GitHub OAuth not configured"},
        )

    redirect_uri = GITHUB_REDIRECT_URI
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback")
async def github_callback(request: Request):
    """GitHub OAuth コールバック処理"""
    try:
        token = await oauth.github.authorize_access_token(request)
        if not token:
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to obtain access token"},
            )

        access_token = token.get("access_token")
        headers = {"Authorization": f"token {access_token}"}

        # GitHub API でユーザー情報を取得
        user_response = requests.get(
            "https://api.github.com/user", headers=headers, timeout=10
        )
        user_response.raise_for_status()
        github_user = user_response.json()

        # メールアドレスを取得
        email = await _fetch_primary_email(headers)

        # User upsert
        user = User.query.filter_by(github_id=str(github_user["id"])).first()
        if user:
            user.github_login = github_user.get("login", "")
            user.name = github_user.get("name")
            user.avatar_url = github_user.get("avatar_url")
            if email:
                user.email = email
        else:
            user = User(
                github_id=str(github_user["id"]),
                github_login=github_user.get("login", ""),
                name=github_user.get("name"),
                avatar_url=github_user.get("avatar_url"),
                email=email,
            )
            db.session.add(user)

        db.session.commit()

        # セッションに user_id を保存
        request.session["user_id"] = user.id
        request.session["github_login"] = user.github_login

        # プロジェクト一覧にリダイレクト
        return RedirectResponse(url="/projects/")

    except Exception as e:  # noqa: BLE001
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Authentication failed. Please try logging in again."}},
        )


@router.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    request.session.clear()
    return RedirectResponse(url="/api/v1/auth/login/github")


async def _fetch_primary_email(headers: dict[str, str]) -> str | None:
    """GitHub API からプライマリメールを取得"""
    try:
        email_response = requests.get(
            "https://api.github.com/user/emails", headers=headers, timeout=10
        )
        if email_response.status_code != 200:
            return None

        emails = email_response.json()
        # プライマリ検証済みメール
        for e in emails:
            if e.get("primary") and e.get("verified"):
                return e.get("email")
        # フォールバック: 最初の検証済みメール
        for e in emails:
            if e.get("verified"):
                return e.get("email")
    except (requests.RequestException, ValueError):
        pass
    return None


def get_current_user_from_session(request: Request) -> User | None:
    """セッションから現在のユーザーを取得"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


async def require_session_auth(request: Request) -> User:
    """セッション認証必須のDependency"""
    user = get_current_user_from_session(request)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
