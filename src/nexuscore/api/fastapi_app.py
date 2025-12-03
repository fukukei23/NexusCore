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
from fastapi import FastAPI

from .routes import health, execute, github_webhook, projects, runs, plans, badges


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

    # GitHub Webhook router をマウント
    app.include_router(github_webhook.router)

    # Projects router をマウント
    app.include_router(projects.router, prefix="/api/v1")

    # Runs router をマウント
    app.include_router(runs.router, prefix="/api/v1")

    # Plans router をマウント
    app.include_router(plans.router, prefix="/api/v1")

    # Badges router をマウント（/api プレフィックス、認証不要）
    app.include_router(badges.router, prefix="/api")

    # 将来、以下のような router を追加予定:
    # app.include_router(auth.router, prefix="/api/v1")
    # app.include_router(admin.router, prefix="/api/v1")
    # app.include_router(projects.router, prefix="/api/v1")
    # app.include_router(runs.router, prefix="/api/v1")

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

