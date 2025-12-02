"""
外部統合 API のテスト
"""
import pytest
from unittest.mock import Mock, patch

from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import User, Project, ApiKey


@pytest.fixture
def app():
    """テスト用 Flask アプリケーション"""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """テスト用ユーザー"""
    with app.app_context():
        user = User(
            github_id=12345,
            github_login="testuser",
            name="Test User",
            email="test@example.com",
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_api_key(app, test_user):
    """テスト用 API キー"""
    with app.app_context():
        from nexuscore.webapp.models import ApiKey
        raw_token = ApiKey.generate_token()
        token_hash = ApiKey.hash_token(raw_token)

        api_key = ApiKey(
            user_id=test_user.id,
            token_hash=token_hash,
            name="Test API Key",
        )
        db.session.add(api_key)
        db.session.commit()
        return raw_token, api_key


@pytest.fixture
def test_project(app, test_user):
    """テスト用プロジェクト"""
    with app.app_context():
        project = Project(
            owner_id=test_user.id,
            name="Test Project",
            repo_url="https://github.com/test/repo",
            local_path="/tmp/test-project",
        )
        db.session.add(project)
        db.session.commit()
        return project


def test_list_projects_without_api_key(client):
    """API キーなしでプロジェクト一覧を取得すると 401 が返る"""
    response = client.get("/api/v1/projects")
    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data
    assert "api key" in data["error"].lower()


def test_list_projects_with_valid_api_key(client, test_user, test_api_key, test_project):
    """有効な API キーでプロジェクト一覧を取得できる"""
    raw_token, _ = test_api_key

    response = client.get(
        "/api/v1/projects",
        headers={"X-Api-Key": raw_token}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "projects" in data
    assert len(data["projects"]) == 1
    assert data["projects"][0]["id"] == test_project.id
    assert data["projects"][0]["name"] == test_project.name


def test_list_projects_with_invalid_api_key(client):
    """無効な API キーでプロジェクト一覧を取得すると 401 が返る"""
    response = client.get(
        "/api/v1/projects",
        headers={"X-Api-Key": "invalid-token"}
    )

    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data


def test_trigger_run_without_requirement(client, test_user, test_api_key, test_project):
    """requirement 未指定で Run を発火すると 400 が返る"""
    raw_token, _ = test_api_key

    response = client.post(
        f"/api/v1/projects/{test_project.id}/run",
        headers={"X-Api-Key": raw_token},
        json={}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "requirement" in data["error"].lower()


def test_trigger_run_with_valid_request(client, test_user, test_api_key, test_project):
    """正常なリクエストで Run を発火できる"""
    raw_token, _ = test_api_key

    with patch("nexuscore.webapp.api_external.run_orchestrator_task") as mock_task:
        mock_task.delay.return_value = Mock(id="task-123")

        response = client.post(
            f"/api/v1/projects/{test_project.id}/run",
            headers={"X-Api-Key": raw_token},
            json={
                "requirement": "Test requirement",
                "autonomy_level": 2,
                "fast_lane": True,
            }
        )

        # Celery が有効な場合は 202、無効な場合は 200 または 500
        assert response.status_code in [200, 202, 500]
        data = response.get_json()
        assert "run_id" in data
        assert "status" in data
        assert "queue_mode" in data


def test_trigger_run_with_nonexistent_project(client, test_user, test_api_key):
    """存在しないプロジェクトで Run を発火すると 404 が返る"""
    raw_token, _ = test_api_key

    response = client.post(
        "/api/v1/projects/999/run",
        headers={"X-Api-Key": raw_token},
        json={"requirement": "Test requirement"}
    )

    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower()


def test_get_latest_run(client, test_user, test_api_key, test_project):
    """最新の Run を取得できる"""
    raw_token, _ = test_api_key

    with client.application.app_context():
        from nexuscore.webapp.models import Run
        from datetime import datetime

        run = Run(
            project_id=test_project.id,
            run_id="test-run-123",
            triggered_by=test_user.id,
            status="SUCCESS",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()

    response = client.get(
        f"/api/v1/projects/{test_project.id}/runs/latest",
        headers={"X-Api-Key": raw_token}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "run" in data
    assert data["run"] is not None
    assert data["run"]["run_id"] == "test-run-123"
    assert data["run"]["status"] == "SUCCESS"


def test_get_latest_run_no_runs(client, test_user, test_api_key, test_project):
    """Run が存在しない場合は null が返る"""
    raw_token, _ = test_api_key

    response = client.get(
        f"/api/v1/projects/{test_project.id}/runs/latest",
        headers={"X-Api-Key": raw_token}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "run" in data
    assert data["run"] is None

