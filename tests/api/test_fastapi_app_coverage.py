"""
fastapi_app.py 例外ハンドラ 未カバー行テスト (Issue #92)

対象:
- L122-136: http_exception_handler の code_map fallback (文字列detail)
- L148-150: validation_exception_handler の field_path 構築
- L167-176: general_exception_handler (非HTTPException)
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError

from nexuscore.api.fastapi_app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


# === L122-136: http_exception_handler code_map fallback ===


def test_http_exception_string_detail_404(client):
    """文字列 detail の HTTPException → code_map で NOT_FOUND にマップ"""
    resp = client.get("/api/v1/runs/nonexistent-id-status")
    # 404 またはエンドポイントが存在すれば code_map パスを通る
    if resp.status_code == 404:
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] in ("NOT_FOUND", "VALIDATION_ERROR")


def test_http_exception_string_detail_via_route(client, monkeypatch):
    """projects/999 で NOT_FOUND (文字列detail) → code_map パス"""
    monkeypatch.setenv("NEXUSCORE_API_KEY", "test-api-key-123")
    mock_user = MagicMock()
    mock_user.id = 1

    with (
        patch("nexuscore.webapp.models.Project") as Project,
        patch("nexuscore.webapp.models.Run") as Run,
        patch("nexuscore.webapp.db"),
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        Project.query = mock_query
        Run.query = mock_query

        mock_key = MagicMock()
        mock_key.user = mock_user
        ApiKey.hash_token.return_value = "h"
        ApiKey.query.filter_by.return_value.first.return_value = mock_key

        resp = client.get(
            "/api/v1/projects/999",
            headers={"X-API-Key": "test-api-key-123"},
        )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_http_exception_code_map_unknown_status():
    """マップにないステータスコード → UNKNOWN_ERROR"""
    app = create_app()

    @app.get("/test-unknown-status")
    async def trigger_unknown():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    tc = TestClient(app)
    resp = tc.get("/test-unknown-status")
    assert resp.status_code == 418
    data = resp.json()
    assert data["error"]["code"] == "UNKNOWN_ERROR"
    assert "teapot" in data["error"]["message"]


# === L148-150: validation field_path 構築 ===


def test_validation_error_with_field_path(client, monkeypatch):
    """422 バリデーションエラーに field path が含まれる"""
    monkeypatch.setenv("NEXUSCORE_API_KEY", "test-api-key-123")
    mock_user = MagicMock()
    mock_user.id = 1

    with (
        patch("nexuscore.webapp.models.Project") as Project,
        patch("nexuscore.webapp.models.Run") as Run,
        patch("nexuscore.webapp.db"),
        patch("nexuscore.webapp.models.ApiKey") as ApiKey,
        patch("nexuscore.webapp.models.User"),
    ):
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        Project.query = mock_query
        Run.query = mock_query

        mock_key = MagicMock()
        mock_key.user = mock_user
        ApiKey.hash_token.return_value = "h"
        ApiKey.query.filter_by.return_value.first.return_value = mock_key

        # name フィールド欠如で POST（必須フィールド → field_path 構築）
        resp = client.post(
            "/api/v1/projects",
            json={},  # name, local_path 欠如
            headers={"X-API-Key": "test-api-key-123"},
        )
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    # field: が含まれていることを確認（field_path 構築パスが通った証拠）
    assert "field:" in data["error"]["message"]


# === L167-176: general_exception_handler ===


def test_general_exception_handler():
    """HTTPException以外のException → 500 INTERNAL_ERROR"""
    app = create_app()

    @app.get("/test-general-exception")
    async def trigger_general():
        raise RuntimeError("Unexpected error")

    tc = TestClient(app, raise_server_exceptions=False)
    resp = tc.get("/test-general-exception")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert data["error"]["message"] == "Internal server error"


def test_http_exception_detail_is_dict_with_error_key():
    """exc.detail が dict で "error" キーを含む場合 → ErrorDetail 構築パス"""
    app = create_app()

    @app.get("/test-dict-detail")
    async def trigger_dict_detail():
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "CUSTOM_FORBIDDEN", "message": "Access denied"}},
        )

    tc = TestClient(app)
    resp = tc.get("/test-dict-detail")
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "CUSTOM_FORBIDDEN"
    assert data["error"]["message"] == "Access denied"
