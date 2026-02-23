"""
NexusCore SaaS基盤 - GitHub OAuth認証

既存の Orchestrator / NPE とは独立して動作する。
"""

from __future__ import annotations

import os

import requests
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, jsonify, redirect, session, url_for

from nexuscore.webapp import db
from nexuscore.webapp.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")

# OAuth設定（環境変数から読み込み）
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:5000/auth/github/callback")

oauth = OAuth()


def init_oauth(app):
    """
    OAuthクライアントを初期化（create_appから呼ばれる）
    """
    oauth.init_app(app)
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        server_metadata_url="https://github.com/login/oauth/authorize",
        client_kwargs={"scope": "read:user user:email"},
    )


@bp.route("/login/github")
def login_github():
    """
    GitHub OAuth ログイン開始
    GET /auth/login/github
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return jsonify({"error": "GitHub OAuth not configured"}), 500

    redirect_uri = url_for("auth.github_callback", _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@bp.route("/github/callback")
def github_callback():
    """
    GitHub OAuth コールバック処理
    GET /auth/github/callback
    """
    try:
        # トークンを取得
        token = oauth.github.authorize_access_token()
        if not token:
            return jsonify({"error": "Failed to obtain access token"}), 400

        # GitHub API でユーザー情報を取得
        headers = {"Authorization": f"token {token.get('access_token')}"}
        user_response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        user_response.raise_for_status()
        github_user = user_response.json()

        # メールアドレスを取得（別エンドポイント）
        email_response = requests.get(
            "https://api.github.com/user/emails", headers=headers, timeout=10
        )
        email = None
        if email_response.status_code == 200:
            emails = email_response.json()
            # プライマリメールを探す
            for e in emails:
                if e.get("primary") and e.get("verified"):
                    email = e.get("email")
                    break
            # プライマリがなければ最初の検証済みメール
            if not email:
                for e in emails:
                    if e.get("verified"):
                        email = e.get("email")
                        break

        # User を upsert（存在すれば更新、なければ新規作成）
        user = User.query.filter_by(github_id=str(github_user["id"])).first()
        if user:
            # 更新
            user.github_login = github_user.get("login", "")
            user.name = github_user.get("name")
            user.avatar_url = github_user.get("avatar_url")
            if email:
                user.email = email
        else:
            # 新規作成
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
        session["user_id"] = user.id
        session["github_login"] = user.github_login

        # プロジェクト一覧にリダイレクト
        return redirect(url_for("views_projects.list_projects"))

    except Exception as e:
        return jsonify({"error": f"OAuth callback failed: {str(e)}"}), 500


@bp.route("/logout")
def logout():
    """
    ログアウト
    GET /auth/logout
    """
    session.clear()
    return redirect(url_for("auth.login_github"))


def get_current_user():
    """
    現在のログインユーザーを取得（ヘルパー関数）
    """
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def require_auth(f):
    """
    認証必須デコレータ
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("auth.login_github"))
        return f(*args, **kwargs)

    return decorated_function
