"""
FastAPI アプリケーションエントリポイント

NexusCore API の FastAPI ベース実装。
既存の Flask server.py と共存し、段階的に移行するための土台。

実装パターン（.cursorrules 準拠）:
- ルートは src/nexuscore/api/routes/ 配下に作成
- レスポンススキーマは src/nexuscore/api/schemas/ 配下の Pydantic BaseModel を使用
- Public API は /api/v1/* プレフィックスを使用
- 認証依存関係は src/nexuscore/api/dependencies/ 配下に配置
"""
import os
from fastapi import FastAPI

from .routes import health, execute, github_webhook, projects, runs, plans, badges, api_keys


def create_app(test_db_path: str | None = None) -> FastAPI:
    """
    FastAPI アプリケーションインスタンスを作成する。

    Args:
        test_db_path: E2E テスト用の DB パス（指定された場合、テスト用 DB を使用）

    Returns:
        FastAPI: 設定済みの FastAPI アプリケーション
    """
    app = FastAPI(
        title="NexusCore API",
        version="1.0.0",
        description="NexusCore API - FastAPI implementation",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Flask アプリケーションを作成（DB アクセスに必要）
    from nexuscore.webapp import create_app as create_flask_app

    if test_db_path:
        # E2E テスト用 DB のオーバーライド
        db_uri = f"sqlite:///{test_db_path}"
        flask_app = create_flask_app(config_overrides={"SQLALCHEMY_DATABASE_URI": db_uri})
        app.state.test_db_path = test_db_path
    else:
        # 通常起動時はデフォルトの DB 設定を使用
        flask_app = create_flask_app()

    # Flask アプリを FastAPI アプリの state に保存
    app.state.flask_app = flask_app

    # FastAPI のミドルウェアで Flask アプリコンテキストを設定（各リクエストごと）
    @app.middleware("http")
    async def setup_flask_context_middleware(request, call_next):
        with flask_app.app_context():
            response = await call_next(request)
            return response

    # Health check router をマウント
    app.include_router(health.router, prefix="/api/v1")

    # Execute router をマウント
    app.include_router(execute.router, prefix="/api/v1")

    # GitHub Webhook router をマウント
    app.include_router(github_webhook.router)

    # Projects router をマウント
    app.include_router(projects.router, prefix="/api/v1")

    # Runs router をマウント
    app.include_router(runs.router, prefix="/api/v1")

    # Plans router をマウント
    app.include_router(plans.router, prefix="/api/v1")

    # Badges router をマウント（/api/v1 プレフィックス、認証不要）
    app.include_router(badges.router, prefix="/api/v1")

    # API Keys router をマウント（/api/v1 プレフィックス、認証必須）
    app.include_router(api_keys.router, prefix="/api/v1")

    # 将来、以下のような router を追加予定:
    # app.include_router(auth.router, prefix="/api/v1")
    # app.include_router(admin.router, prefix="/api/v1")

    return app


# FastAPI アプリケーションインスタンス
app = create_app()

# ローカル実行用コマンド例（WSL Ubuntu）:
# source myenv_linux/bin/activate
# export PYTHONPATH=/home/yn441611/NexusCore/src:$PYTHONPATH
# uvicorn nexuscore.api.fastapi_app:app --reload --host 127.0.0.1 --port 8000
#
# ポート設計:
# - Flask アプリ: ポート 5000（既存の Web UI）
# - FastAPI アプリ: ポート 8000（新規 API）
# 両方を同時に起動可能（別ポートのため）

