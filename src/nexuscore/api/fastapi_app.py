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

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routes import (
    api_keys,
    badges,
    execute,
    github_webhook,
    health,
    plans,
    projects,
    run_view,
    runs,
)
from .schemas.error import ErrorDetail, ErrorResponse


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

    # Run Records router をマウント（DBベースのRun管理、/api/v1/run-records）
    app.include_router(runs.router, prefix="/api/v1")

    # Plans router をマウント
    app.include_router(plans.router, prefix="/api/v1")

    # Badges router をマウント（/api/v1 プレフィックス、認証不要）
    app.include_router(badges.router, prefix="/api/v1")

    # API Keys router をマウント（/api/v1 プレフィックス、認証必須）
    app.include_router(api_keys.router, prefix="/api/v1")

    # RunView canonical router をマウント（/api/v1/runs, 認証必須）
    app.include_router(run_view.canonical_router, prefix="/api/v1")

    # RunView deprecated router をマウント（/api/v1/run-view/runs, OpenAPIから除外）
    app.include_router(run_view.deprecated_router, prefix="/api/v1")

    # CR-NEXUS-034: グローバル例外ハンドラでエラー応答をトップレベルerror形式に統一（Option A）
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        HTTPException をトップレベル error 形式に統一するハンドラ

        FastAPI 標準の {"detail": ...} ではなく、{"error": {"code": ..., "message": ...}} 形式で返す。
        """
        # exc.detail が既に ErrorResponse 形式（{"error": ...}）の場合はそのまま使用
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            error_detail = exc.detail["error"]
            error_response = ErrorResponse(
                error=ErrorDetail(
                    code=error_detail.get("code", "UNKNOWN_ERROR"),
                    message=error_detail.get("message", str(exc.detail)),
                )
            )
        else:
            # exc.detail が文字列や他の形式の場合は、適切なエラーコードにマッピング
            code_map = {
                status.HTTP_400_BAD_REQUEST: "INVALID_REQUEST",
                status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
                status.HTTP_403_FORBIDDEN: "FORBIDDEN",
                status.HTTP_404_NOT_FOUND: "NOT_FOUND",
                status.HTTP_409_CONFLICT: "CONFLICT",
                status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
                status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
            }
            error_code = code_map.get(exc.status_code, "UNKNOWN_ERROR")
            error_message = str(exc.detail) if exc.detail else "An error occurred"

            error_response = ErrorResponse(
                error=ErrorDetail(code=error_code, message=error_message)
            )

        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        RequestValidationError（422）をトップレベル error 形式に統一するハンドラ
        """
        errors = exc.errors()
        # 最初のバリデーションエラーメッセージを使用
        error_message = errors[0]["msg"] if errors else "Validation error"
        if errors and "loc" in errors[0]:
            field_path = " -> ".join(str(loc) for loc in errors[0]["loc"])
            error_message = f"{error_message} (field: {field_path})"

        error_response = ErrorResponse(
            error=ErrorDetail(code="VALIDATION_ERROR", message=error_message)
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        その他の例外をトップレベル error 形式に統一するハンドラ
        """
        # HTTPException は既に http_exception_handler で処理されているため、ここには来ない
        # ただし、念のため HTTPException は除外
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            raise exc

        error_response = ErrorResponse(
            error=ErrorDetail(code="INTERNAL_ERROR", message="Internal server error")
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.model_dump()
        )

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
