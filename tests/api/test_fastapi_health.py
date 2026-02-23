"""
FastAPI Health エンドポイントのテスト

CR-FASTAPI-001 で作成された /api/v1/health エンドポイントのテスト。
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI TestClient のフィクスチャ"""
    # インポートを遅延させて、テスト実行時のパフォーマンスを向上
    from nexuscore.api.fastapi_app import app

    return TestClient(app)


def test_health_check_status_code(client: TestClient):
    """
    Health check エンドポイントが 200 を返すことを確認
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_check_response_format(client: TestClient):
    """
    Health check レスポンスが期待される形式であることを確認
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "version" in data
    assert isinstance(data["version"], str)
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)  # ISO形式の文字列


def test_health_check_openapi_definition(client: TestClient):
    """
    OpenAPI スキーマに /api/v1/health が定義されていることを確認
    """
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "paths" in openapi_schema
    assert "/api/v1/health" in openapi_schema["paths"]

    health_path = openapi_schema["paths"]["/api/v1/health"]
    assert "get" in health_path

    get_operation = health_path["get"]
    assert "responses" in get_operation
    assert "200" in get_operation["responses"]
