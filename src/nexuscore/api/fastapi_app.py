import logging
import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from starlette.middleware.sessions import SessionMiddleware

from .routes import (
    api_keys,
    auth,
    badges,
    execute,
    github_webhook,
    health,
    openrouter_key,
    plans,
    projects,
    run_view,
    runs,
)
from .schemas.error import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _register_routers(app: FastAPI) -> None:
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(execute.router, prefix="/api/v1")
    app.include_router(github_webhook.router)
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(runs.router, prefix="/api/v1")
    app.include_router(plans.router, prefix="/api/v1")
    app.include_router(badges.router, prefix="/api/v1")
    app.include_router(api_keys.router, prefix="/api/v1")
    app.include_router(openrouter_key.router, prefix="/api/v1")
    app.include_router(run_view.canonical_router, prefix="/api/v1")


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            error_detail = exc.detail["error"]
            error_response = ErrorResponse(
                error=ErrorDetail(
                    code=error_detail.get("code", "UNKNOWN_ERROR"),
                    message=error_detail.get("message", str(exc.detail)),
                )
            )
        else:
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
        errors = exc.errors()
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
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            raise exc

        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        error_response = ErrorResponse(
            error=ErrorDetail(code="INTERNAL_ERROR", message="Internal server error")
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.model_dump()
        )


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

    _session_secret = os.getenv("SESSION_SECRET")
    if not _session_secret and os.getenv("ENV") == "production":
        raise RuntimeError("SESSION_SECRET must be set in production")
    app.add_middleware(SessionMiddleware, secret_key=_session_secret or "nexuscore-dev-secret")

    from nexuscore.webapp import create_app as create_flask_app

    if test_db_path:
        db_uri = f"sqlite:///{test_db_path}"
        flask_app = create_flask_app(config_overrides={"SQLALCHEMY_DATABASE_URI": db_uri})
        app.state.test_db_path = test_db_path
    else:
        flask_app = create_flask_app()

    app.state.flask_app = flask_app

    @app.middleware("http")
    async def setup_flask_context_middleware(request, call_next):
        with flask_app.app_context():
            response = await call_next(request)
            return response

    auth.init_oauth(app)
    _register_routers(app)
    _register_exception_handlers(app)

    return app


app = create_app()
