"""
FastAPI Project Run エンドポイントのテスト

CR-FASTAPI-009 で作成された以下のエンドポイントのテスト:
- POST /api/v1/projects/{project_id}/run
- GET /api/v1/projects/{project_id}/runs/latest
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from nexuscore.api.fastapi_app import app
from nexuscore.api.dependencies.auth import AuthenticatedUser

# os モジュールをインポート（getenv のモック用）
import os as os_module

client = TestClient(app)

# テスト用のAPIキー
TEST_API_KEY = "test-api-key-123"


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """各テストの前に環境変数を設定するフィクスチャ"""
    monkeypatch.setenv("NEXUSCORE_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("NEXUS_USE_CELERY", "1")  # デフォルトは非同期実行


@pytest.fixture(autouse=True)
def mock_auth():
    """認証をモックするフィクスチャ（全テストで自動適用）"""
    # get_current_user 内で使用される webapp.models をモック
    with patch("nexuscore.webapp.models.ApiKey") as MockApiKey, \
         patch("nexuscore.webapp.models.User") as MockUser:

        # API Key認証のモック
        mock_user = MagicMock()
        mock_user.id = 1

        mock_api_key_obj = MagicMock()
        mock_api_key_obj.user = mock_user
        mock_api_key_obj.user_id = 1

        MockApiKey.hash_token.return_value = "hashed_key"
        MockApiKey.query.filter_by.return_value.first.return_value = mock_api_key_obj

        yield {
            "ApiKey": MockApiKey,
            "User": MockUser,
            "user": mock_user,
        }


@pytest.fixture
def mock_db_session():
    """データベースセッションをモックするフィクスチャ"""
    with patch("nexuscore.webapp.db.session") as mock_session:
        yield mock_session


@pytest.fixture
def mock_project():
    """プロジェクトモック"""
    project = MagicMock()
    project.id = 1
    project.name = "Test Project"
    project.owner_id = 1
    project.local_path = "/tmp/test_project"
    return project


@pytest.fixture
def mock_run():
    """Runモック"""
    run = MagicMock()
    run.id = 1
    run.run_id = "test-run-id-123"
    run.project_id = 1
    run.status = "PENDING"
    run.started_at = None
    run.finished_at = None
    return run


def test_trigger_project_run_success(mock_db_session, mock_project, mock_run):
    """
    POST /api/v1/projects/{project_id}/run が正常に動作することを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject, \
         patch("nexuscore.webapp.models.Run") as MockRun, \
         patch("nexuscore.webapp.celery_app.run_orchestrator_task") as mock_celery_task:

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # Run の作成をモック
        MockRun.return_value = mock_run
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Celery タスクをモック
        mock_celery_task.delay.return_value = MagicMock()

        headers = {"X-API-Key": TEST_API_KEY}
        payload = {
            "requirement": "Test requirement",
            "autonomy_level": 2,
            "fast_lane": False
        }

        response = client.post(
            f"/api/v1/projects/{mock_project.id}/run",
            json=payload,
            headers=headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data
        assert data["project_id"] == mock_project.id
        assert data["status"] == "PENDING"
        assert data["queue_mode"] == "async"


def test_trigger_project_run_sync_mode(mock_db_session, mock_project, mock_run, monkeypatch):
    """
    POST /api/v1/projects/{project_id}/run が同期実行モードで正常に動作することを確認
    """
    # 環境変数を設定
    monkeypatch.setenv("NEXUS_USE_CELERY", "0")

    # os.getenv を直接パッチ（モジュールレベルでインポートされている os をパッチ）
    # projects.py の trigger_project_run 関数内で使用される os.getenv をパッチ
    import nexuscore.api.routes.projects as projects_module

    with patch.object(projects_module.os, "getenv") as mock_getenv, \
         patch("nexuscore.webapp.models.Project") as MockProject, \
         patch("nexuscore.webapp.models.Run") as MockRun, \
         patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_inline") as mock_inline:

        # os.getenv のモックを設定
        def getenv_side_effect(key, default=None):
            if key == "NEXUS_USE_CELERY":
                return "0"  # 同期モード
            return os_module.getenv(key, default)

        mock_getenv.side_effect = getenv_side_effect

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # Run の作成をモック
        MockRun.return_value = mock_run
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # インライン実行をモック
        mock_inline.return_value = None

        headers = {"X-API-Key": TEST_API_KEY}
        payload = {
            "requirement": "Test requirement",
            "autonomy_level": 2,
            "fast_lane": False
        }

        response = client.post(
            f"/api/v1/projects/{mock_project.id}/run",
            json=payload,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["project_id"] == mock_project.id
        assert data["queue_mode"] == "sync"
        mock_inline.assert_called_once()
        mock_db_session.add.assert_called_once_with(mock_run)
        mock_db_session.commit.assert_called()


def test_trigger_project_run_project_not_found(mock_db_session):
    """
    POST /api/v1/projects/{project_id}/run が存在しないプロジェクトIDで404を返すことを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject:
        # プロジェクトが見つからない場合
        MockProject.query.filter_by.return_value.first.return_value = None

        headers = {"X-API-Key": TEST_API_KEY}
        payload = {
            "requirement": "Test requirement",
            "autonomy_level": 2,
            "fast_lane": False
        }

        response = client.post(
            "/api/v1/projects/99999/run",
            json=payload,
            headers=headers
        )

        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "error" in error_data["detail"]
        assert error_data["detail"]["error"]["code"] == "NOT_FOUND"


def test_trigger_project_run_missing_requirement(mock_db_session, mock_project):
    """
    POST /api/v1/projects/{project_id}/run が requirement なしで422を返すことを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject:
        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        headers = {"X-API-Key": TEST_API_KEY}
        payload = {
            "autonomy_level": 2,
            "fast_lane": False
            # requirement が欠けている
        }

        response = client.post(
            f"/api/v1/projects/{mock_project.id}/run",
            json=payload,
            headers=headers
        )

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data


def test_get_latest_run_success(mock_db_session, mock_project, mock_run):
    """
    GET /api/v1/projects/{project_id}/runs/latest が正常に動作することを確認
    """
    from datetime import datetime

    mock_run.started_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_run.finished_at = datetime(2025, 1, 1, 0, 5, 0)
    mock_run.status = "SUCCESS"

    with patch("nexuscore.webapp.models.Project") as MockProject, \
         patch("nexuscore.webapp.models.Run") as MockRun, \
         patch("nexuscore.api.routes.projects.desc") as mock_desc:

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # desc() をモック
        mock_desc.return_value = MagicMock()

        # Run のクエリチェーンをモック
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = mock_run
        MockRun.query.filter_by.return_value = mock_query_chain

        headers = {"X-API-Key": TEST_API_KEY}

        response = client.get(
            f"/api/v1/projects/{mock_project.id}/runs/latest",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "run" in data
        assert data["run"] is not None
        assert data["run"]["id"] == mock_run.id
        assert data["run"]["run_id"] == mock_run.run_id
        assert data["run"]["status"] == "SUCCESS"


def test_get_latest_run_no_runs(mock_db_session, mock_project):
    """
    GET /api/v1/projects/{project_id}/runs/latest がRunが存在しない場合にnullを返すことを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject, \
         patch("nexuscore.webapp.models.Run") as MockRun, \
         patch("nexuscore.api.routes.projects.desc") as mock_desc:

        # プロジェクトのクエリをモック
        MockProject.query.filter_by.return_value.first.return_value = mock_project

        # desc() をモック
        mock_desc.return_value = MagicMock()

        # Run が見つからない場合
        mock_query_chain = MagicMock()
        mock_query_chain.order_by.return_value.first.return_value = None
        MockRun.query.filter_by.return_value = mock_query_chain

        headers = {"X-API-Key": TEST_API_KEY}

        response = client.get(
            f"/api/v1/projects/{mock_project.id}/runs/latest",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "run" in data
        assert data["run"] is None


def test_get_latest_run_project_not_found(mock_db_session):
    """
    GET /api/v1/projects/{project_id}/runs/latest が存在しないプロジェクトIDで404を返すことを確認
    """
    with patch("nexuscore.webapp.models.Project") as MockProject:
        # プロジェクトが見つからない場合
        MockProject.query.filter_by.return_value.first.return_value = None

        headers = {"X-API-Key": TEST_API_KEY}

        response = client.get(
            "/api/v1/projects/99999/runs/latest",
            headers=headers
        )

        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "error" in error_data["detail"]
        assert error_data["detail"]["error"]["code"] == "NOT_FOUND"


def test_trigger_project_run_requires_authentication(mock_db_session):
    """
    POST /api/v1/projects/{project_id}/run が認証なしで422を返すことを確認
    （FastAPIのバリデーションエラー：必須ヘッダー欠如）
    """
    payload = {
        "requirement": "Test requirement",
        "autonomy_level": 2,
        "fast_lane": False
    }

    response = client.post(
        "/api/v1/projects/1/run",
        json=payload
        # ヘッダーなし
    )

    # FastAPIの必須パラメータ（X-API-Key）が欠如しているため422が返る
    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data


def test_get_latest_run_requires_authentication(mock_db_session):
    """
    GET /api/v1/projects/{project_id}/runs/latest が認証なしで422を返すことを確認
    （FastAPIのバリデーションエラー：必須ヘッダー欠如）
    """
    response = client.get(
        "/api/v1/projects/1/runs/latest"
        # ヘッダーなし
    )

    # FastAPIの必須パラメータ（X-API-Key）が欠如しているため422が返る
    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data

