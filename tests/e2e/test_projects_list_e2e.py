"""
Projects List E2E テスト

FastAPI の Projects API の E2E テスト。
E2E 用 SQLite DB を使用して、実際の DB 操作をテストする。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.e2e.fixtures.test_db import (
    create_e2e_db,
    setup_test_data,
    e2e_test_api_key,
)


@pytest.fixture(scope="function")
def e2e_app():
    """
    E2E テスト用の FastAPI アプリインスタンスを提供する fixture。

    Returns:
        FastAPI: FastAPI アプリインスタンス
    """
    # E2E 用 DB を作成
    db_path, flask_app = create_e2e_db()
    # 初期データを挿入
    setup_test_data(flask_app)

    # FastAPI アプリを作成（テスト用 DB を指定）
    from nexuscore.api.fastapi_app import create_app
    fastapi_app = create_app(test_db_path=db_path)

    return fastapi_app


@pytest.fixture(scope="function")
def e2e_client(e2e_app):
    """
    E2E テスト用の TestClient を提供する fixture。

    Args:
        e2e_app: FastAPI アプリインスタンス

    Returns:
        TestClient: FastAPI TestClient
    """
    return TestClient(e2e_app)


def test_projects_list_e2e(e2e_client, e2e_test_api_key):
    """
    Projects 一覧取得の E2E テスト。

    正常系: 200 OK でプロジェクト一覧が返る（最低 1 件以上）。
    """
    # API Key を使用してリクエスト
    response = e2e_client.get(
        "/api/v1/projects",
        headers={"X-API-Key": e2e_test_api_key},
    )

    # 200 OK が返ることを確認
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # レスポンスボディを確認
    data = response.json()
    assert "projects" in data, f"Response should contain 'projects' key: {data}"

    # プロジェクトが最低 1 件以上返ることを確認
    projects = data["projects"]
    assert isinstance(projects, list), f"Projects should be a list: {type(projects)}"
    assert len(projects) >= 1, f"Expected at least 1 project, got {len(projects)}"

    # プロジェクトの構造を確認
    project = projects[0]
    assert "id" in project, f"Project should have 'id' key: {project}"
    assert "name" in project, f"Project should have 'name' key: {project}"
    assert "repo_url" in project, f"Project should have 'repo_url' key: {project}"
    assert "local_path" in project, f"Project should have 'local_path' key: {project}"
    assert "created_at" in project, f"Project should have 'created_at' key: {project}"
    assert "updated_at" in project, f"Project should have 'updated_at' key: {project}"

