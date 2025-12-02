"""
FastAPI アプリケーションエントリポイント

NexusCore API の FastAPI ベース実装。
既存の Flask server.py と共存し、段階的に移行するための土台。
"""
from fastapi import FastAPI

from .routes import health, execute


def create_app() -> FastAPI:
    """
    FastAPI アプリケーションインスタンスを作成する。

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

    # Health check router をマウント
    app.include_router(health.router, prefix="/api/v1")

    # Execute router をマウント
    app.include_router(execute.router, prefix="/api/v1")

    # 将来、以下のような router を追加予定:
    # app.include_router(auth.router, prefix="/api/v1")
    # app.include_router(admin.router, prefix="/api/v1")
    # app.include_router(projects.router, prefix="/api/v1")
    # app.include_router(runs.router, prefix="/api/v1")

    return app


# FastAPI アプリケーションインスタンス
app = create_app()

# ローカル実行用コマンド例:
# uvicorn nexuscore.api.fastapi_app:app --reload

