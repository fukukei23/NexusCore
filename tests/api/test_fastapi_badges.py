"""
FastAPI Badge エンドポイントのテスト

CR-FASTAPI-009 で作成された以下のエンドポイントのテスト:
- GET /api/v1/projects/{project_id}/badge/success_rate
- GET /api/v1/projects/{project_id}/badge/last_run
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import app

client = TestClient(app)


@pytest.fixture
def mock_project():
    """プロジェクトモック"""
    project = MagicMock()
    project.id = 1
    project.name = "Test Project"
    return project


@pytest.fixture
def mock_runs():
    """Runリストモック"""
    runs = []
    for i in range(10):
        run = MagicMock()
        run.status = "SUCCESS" if i < 8 else "FAILED"  # 80% success rate
        runs.append(run)
    return runs


@pytest.fixture
def mock_latest_run():
    """最新Runモック"""
    run = MagicMock()
    run.id = 1
    run.status = "SUCCESS"
    run.started_at = None
    run.finished_at = None
    return run


def test_project_success_rate_badge_success(mock_project, mock_runs):
    """
    GET /api/v1/projects/{project_id}/badge/success_rate が正常に動作することを確認
    """
    with (
        patch("nexuscore.webapp.models.Project") as MockProject,
        patch("nexuscore.webapp.models.Run") as MockRun,
        patch("nexuscore.api.routes.badges.desc") as mock_desc,
    ):

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # desc() をモック（SQLAlchemyのカラムオブジェクトを返す）
        mock_desc.return_value = MagicMock()

        # Run のクエリチェーンをモック
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.limit.return_value.all.return_value = mock_runs
        MockRun.query.filter_by.return_value = mock_query_chain

        response = client.get(f"/api/v1/projects/{mock_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json()
        assert data["schemaVersion"] == 1
        assert data["label"] == "self-healing"
        assert "% success" in data["message"]
        assert data["color"] in ["brightgreen", "green", "yellow", "red"]


def test_project_success_rate_badge_no_runs(mock_project):
    """
    GET /api/v1/projects/{project_id}/badge/success_rate がRunが存在しない場合に0%を返すことを確認
    """
    with (
        patch("nexuscore.webapp.models.Project") as MockProject,
        patch("nexuscore.webapp.models.Run") as MockRun,
        patch("nexuscore.api.routes.badges.desc") as mock_desc,
    ):

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # desc() をモック
        mock_desc.return_value = MagicMock()

        # Run が見つからない場合
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.limit.return_value.all.return_value = []
        MockRun.query.filter_by.return_value = mock_query_chain

        response = client.get(f"/api/v1/projects/{mock_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json()
        assert data["schemaVersion"] == 1
        assert data["label"] == "self-healing"
        assert "0.0% success" in data["message"]
        assert data["color"] == "red"


def test_project_success_rate_badge_project_not_found():
    """
    GET /api/v1/projects/{project_id}/badge/success_rate が存在しないプロジェクトIDで404を返すことを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject:
        # プロジェクトが見つからない場合
        MockProject.query.filter_by.return_value.first.return_value = None

        response = client.get("/api/v1/projects/99999/badge/success_rate")

        assert response.status_code == 404
        error_data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
        assert "error" in error_data
        assert error_data["error"]["code"] == "NOT_FOUND"
        assert "detail" not in error_data


def test_project_last_run_badge_success(mock_project, mock_latest_run):
    """
    GET /api/v1/projects/{project_id}/badge/last_run が正常に動作することを確認
    """
    with (
        patch("nexuscore.webapp.models.Project") as MockProject,
        patch("nexuscore.webapp.models.Run") as MockRun,
        patch("nexuscore.api.routes.badges.desc") as mock_desc,
    ):

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # desc() をモック
        mock_desc.return_value = MagicMock()

        # Run のクエリチェーンをモック
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = mock_latest_run
        MockRun.query.filter_by.return_value = mock_query_chain

        response = client.get(f"/api/v1/projects/{mock_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json()
        assert data["schemaVersion"] == 1
        assert data["label"] == "self-healing"
        assert "last: SUCCESS" in data["message"]
        assert data["color"] == "brightgreen"


def test_project_last_run_badge_no_runs(mock_project):
    """
    GET /api/v1/projects/{project_id}/badge/last_run がRunが存在しない場合に適切なメッセージを返すことを確認
    """
    with (
        patch("nexuscore.webapp.models.Project") as MockProject,
        patch("nexuscore.webapp.models.Run") as MockRun,
        patch("nexuscore.api.routes.badges.desc") as mock_desc,
    ):

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # desc() をモック
        mock_desc.return_value = MagicMock()

        # Run が見つからない場合
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = None
        MockRun.query.filter_by.return_value = mock_query_chain

        response = client.get(f"/api/v1/projects/{mock_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json()
        assert data["schemaVersion"] == 1
        assert data["label"] == "self-healing"
        assert data["message"] == "last: -"
        assert data["color"] == "lightgrey"


def test_project_last_run_badge_different_statuses(mock_project):
    """
    GET /api/v1/projects/{project_id}/badge/last_run が異なるステータスで適切なカラーを返すことを確認
    """
    status_colors = [
        ("SUCCESS", "brightgreen"),
        ("FAILED", "red"),
        ("RUNNING", "blue"),
        ("PENDING", "lightgrey"),
    ]

    for status_str, expected_color in status_colors:
        mock_run = MagicMock()
        mock_run.status = status_str
        mock_run.started_at = None
        mock_run.finished_at = None

        with (
            patch("nexuscore.webapp.models.Project") as MockProject,
            patch("nexuscore.webapp.models.Run") as MockRun,
            patch("nexuscore.api.routes.badges.desc") as mock_desc,
        ):

            MockProject.query.filter_by.return_value.first.return_value = mock_project
            mock_desc.return_value = MagicMock()

            mock_query_chain = MagicMock()
            mock_query_chain.order_by.return_value.first.return_value = mock_run
            MockRun.query.filter_by.return_value = mock_query_chain

            response = client.get(f"/api/v1/projects/{mock_project.id}/badge/last_run")

            assert response.status_code == 200
            data = response.json()
            assert data["color"] == expected_color
            assert f"last: {status_str}" in data["message"]


def test_project_last_run_badge_project_not_found():
    """
    GET /api/v1/projects/{project_id}/badge/last_run が存在しないプロジェクトIDで404を返すことを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject:
        # プロジェクトが見つからない場合
        MockProject.query.filter_by.return_value.first.return_value = None

        response = client.get("/api/v1/projects/99999/badge/last_run")

        assert response.status_code == 404
        error_data = response.json()
        # CR-NEXUS-034: トップレベル error 形式（Option A）
        assert "error" in error_data
        assert error_data["error"]["code"] == "NOT_FOUND"
        assert "detail" not in error_data


def test_badge_endpoints_no_authentication_required(mock_project, mock_runs):
    """
    Badge エンドポイントが認証不要であることを確認
    """
    with (
        patch("nexuscore.webapp.models.Project") as MockProject,
        patch("nexuscore.webapp.models.Run") as MockRun,
        patch("nexuscore.api.routes.badges.desc") as mock_desc,
    ):

        MockProject.query.filter_by.return_value.first.return_value = mock_project
        mock_desc.return_value = MagicMock()

        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.limit.return_value.all.return_value = mock_runs
        MockRun.query.filter_by.return_value = mock_query_chain

        # 認証ヘッダーなしでリクエスト
        response = client.get(f"/api/v1/projects/{mock_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json()
        assert "schemaVersion" in data
