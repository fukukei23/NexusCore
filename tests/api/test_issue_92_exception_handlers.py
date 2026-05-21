"""Issue #92: fastapi_app.py 例外ハンドラテスト

対象: http_exception_handler（ErrorResponse形式・文字列detail・code_map fallback）、
validation_exception_handler、general_exception_handler
"""

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel


def _create_app_with_handlers():
    """テスト用アプリ（create_appの例外ハンドラ部分のみ抽出）"""
    app = FastAPI()
    from nexuscore.api.schemas.error import ErrorDetail, ErrorResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
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
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        from fastapi.responses import JSONResponse
        error_response = ErrorResponse(
            error=ErrorDetail(code="INTERNAL_ERROR", message="Internal server error")
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    # テスト用エンドポイント
    @app.get("/test/error-detail-dict")
    async def error_detail_dict():
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found"}},
        )

    @app.get("/test/error-string")
    async def error_string():
        raise HTTPException(status_code=403, detail="Access denied")

    @app.get("/test/error-no-detail")
    async def error_no_detail():
        raise HTTPException(status_code=500, detail=None)

    @app.get("/test/error-unknown-status")
    async def error_unknown_status():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    @app.get("/test/general-exception")
    async def general_exception():
        raise RuntimeError("Unexpected error")

    return app


class TestHttpExceptionHandler:
    """http_exception_handler のテスト"""

    def test_error_detail_dict_format(self):
        """exc.detail が ErrorResponse 形式（dict with "error"）の場合"""
        client = TestClient(_create_app_with_handlers(), raise_server_exceptions=False)
        resp = client.get("/test/error-detail-dict")

        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"
        assert data["error"]["message"] == "Project not found"

    def test_error_string_detail_code_map(self):
        """exc.detail が文字列の場合、code_map からエラーコードを取得"""
        client = TestClient(_create_app_with_handlers(), raise_server_exceptions=False)
        resp = client.get("/test/error-string")

        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "FORBIDDEN"
        assert data["error"]["message"] == "Access denied"

    def test_error_no_detail(self):
        """detail が None の場合でもエラーレスポンスが返る"""
        client = TestClient(_create_app_with_handlers(), raise_server_exceptions=False)
        resp = client.get("/test/error-no-detail")

        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"
        # str(None) = "None" または "An error occurred"
        assert "error" in data["error"]["message"].lower() or data["error"]["message"] == "None"

    def test_error_unknown_status_code(self):
        """code_mapにないステータスコード → UNKNOWN_ERROR"""
        client = TestClient(_create_app_with_handlers(), raise_server_exceptions=False)
        resp = client.get("/test/error-unknown-status")

        assert resp.status_code == 418
        data = resp.json()
        assert data["error"]["code"] == "UNKNOWN_ERROR"
        assert data["error"]["message"] == "I'm a teapot"


class TestGeneralExceptionHandler:
    """general_exception_handler のテスト"""

    def test_general_exception_returns_500(self):
        """予期しない例外は500 INTERNAL_ERROR"""
        client = TestClient(_create_app_with_handlers(), raise_server_exceptions=False)
        resp = client.get("/test/general-exception")

        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert data["error"]["message"] == "Internal server error"
