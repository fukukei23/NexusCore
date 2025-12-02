#!/usr/bin/env python3
"""
FastAPI Health エンドポイントの手動動作確認スクリプト
"""
import sys
import os

# パスを設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from nexuscore.api.fastapi_app import app

def test_health_endpoint():
    """Health エンドポイントの動作確認"""
    client = TestClient(app)

    print("=" * 60)
    print("Testing /api/v1/health endpoint")
    print("=" * 60)

    # 1. ステータスコード確認
    print("\n1. Testing status code...")
    response = client.get("/api/v1/health")
    print(f"   Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("   ✓ Status code is 200")

    # 2. レスポンス形式確認
    print("\n2. Testing response format...")
    data = response.json()
    print(f"   Response: {data}")

    assert "status" in data, "Missing 'status' field"
    assert data["status"] == "ok", f"Expected 'ok', got '{data['status']}'"
    print("   ✓ status field is 'ok'")

    assert "version" in data, "Missing 'version' field"
    assert isinstance(data["version"], str), "version should be string"
    print(f"   ✓ version field: {data['version']}")

    assert "timestamp" in data, "Missing 'timestamp' field"
    assert isinstance(data["timestamp"], str), "timestamp should be string"
    print(f"   ✓ timestamp field: {data['timestamp']}")

    # 3. OpenAPI スキーマ確認
    print("\n3. Testing OpenAPI schema...")
    openapi_response = client.get("/api/openapi.json")
    assert openapi_response.status_code == 200, "OpenAPI endpoint failed"

    openapi_schema = openapi_response.json()
    assert "paths" in openapi_schema, "Missing 'paths' in OpenAPI schema"
    assert "/api/v1/health" in openapi_schema["paths"], "Missing /api/v1/health in OpenAPI paths"
    print("   ✓ /api/v1/health is defined in OpenAPI schema")

    health_path = openapi_schema["paths"]["/api/v1/health"]
    assert "get" in health_path, "Missing GET method in OpenAPI schema"
    print("   ✓ GET method is defined")

    get_operation = health_path["get"]
    assert "responses" in get_operation, "Missing responses in OpenAPI schema"
    assert "200" in get_operation["responses"], "Missing 200 response in OpenAPI schema"
    print("   ✓ 200 response is defined")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_health_endpoint()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

