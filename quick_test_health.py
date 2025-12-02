#!/usr/bin/env python3
"""Quick health endpoint test"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from fastapi.testclient import TestClient
    from nexuscore.api.fastapi_app import app

    client = TestClient(app)
    resp = client.get("/api/v1/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("✓ All checks passed!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

