#!/usr/bin/env python3
"""Simple verification script"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Importing FastAPI app...")
from nexuscore.api.fastapi_app import app
print("✓ FastAPI app imported")

print("\nTesting health endpoint...")
from fastapi.testclient import TestClient
client = TestClient(app)

response = client.get("/api/v1/health")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Response: {data}")

    # Verify fields
    assert data.get("status") == "ok", f"Expected 'ok', got '{data.get('status')}'"
    assert "version" in data, "Missing 'version' field"
    assert "timestamp" in data, "Missing 'timestamp' field"

    print("\n✓ All checks passed!")
    print(f"  - status: {data['status']}")
    print(f"  - version: {data['version']}")
    print(f"  - timestamp: {data['timestamp']}")
else:
    print(f"✗ Failed with status {response.status_code}")
    print(f"Response: {response.text}")
    sys.exit(1)

