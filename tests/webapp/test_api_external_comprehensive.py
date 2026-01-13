"""
webapp/api_external.py の高品質なテスト

注意: このテストファイルは Flask API (api_external.py) を前提としています。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""
import pytest

# CR-FASTAPI-010: Flask API (api_external.py) は削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask API (api_external.py) has been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True
)


@pytest.fixture(scope="function")
def app():
    """Flask test app with in-memory SQLite database"""
    from nexuscore.webapp import create_app, db

    config_overrides = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    }

    app = create_app(config_overrides=config_overrides)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Database session for tests"""
    from nexuscore.webapp import db
    with app.app_context():
        yield db.session


@pytest.fixture
def test_user(db_session):
    """テスト用ユーザー"""
    user = User(
        github_id="12345",
        github_login="testuser",
        name="Test User",
        email="test@example.com",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_api_key(db_session, test_user):
    """テスト用 API キー"""
    raw_token = ApiKey.generate_token()
    token_hash = ApiKey.hash_token(raw_token)

    api_key = ApiKey(
        user_id=test_user.id,
        token_hash=token_hash,
        name="Test API Key",
    )
    db_session.add(api_key)
    db_session.commit()

    # 生トークンを返す（テストで使用）
    return raw_token


@pytest.fixture
def test_project(db_session, test_user):
    """テスト用プロジェクト"""
    project = Project(
        owner_id=test_user.id,
        name="Test Project",
        repo_url="https://github.com/test/repo",
        local_path="/tmp/test-project",
    )
    db_session.add(project)
    db_session.commit()
    return project


class TestListProjects:
    """list_projects() のテスト"""

    def test_list_projects_without_api_key(self, client):
        """API キーなしでプロジェクト一覧を取得すると 401 が返る"""
        response = client.get("/api/v1/projects")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "api key" in data["error"].lower()

    def test_list_projects_with_invalid_api_key(self, client):
        """無効な API キーでプロジェクト一覧を取得すると 401 が返る"""
        response = client.get(
            "/api/v1/projects",
            headers={"X-Api-Key": "invalid_key"}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    def test_list_projects_with_valid_api_key(self, client, test_user, test_api_key, test_project):
        """有効な API キーでプロジェクト一覧を取得できる"""
        response = client.get(
            "/api/v1/projects",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "projects" in data
        assert len(data["projects"]) == 1

        project = data["projects"][0]
        assert project["id"] == test_project.id
        assert project["name"] == "Test Project"
        assert project["repo_url"] == "https://github.com/test/repo"
        assert project["local_path"] == "/tmp/test-project"
        assert "created_at" in project

    def test_list_projects_with_api_key_query_param(self, client, test_user, test_api_key, test_project):
        """API キーをクエリパラメータで指定してもアクセスできる"""
        response = client.get(
            f"/api/v1/projects?api_key={test_api_key}"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["projects"]) == 1

    def test_list_projects_returns_only_user_projects(self, db_session, client, test_user, test_api_key, test_project):
        """list_projects() がユーザー自身のプロジェクトのみを返す"""
        # 別のユーザーとそのプロジェクトを作成
        other_user = User(github_id="99999", github_login="otheruser")
        db_session.add(other_user)
        db_session.commit()

        other_project = Project(
            owner_id=other_user.id,
            name="Other Project",
            local_path="/tmp/other-project",
        )
        db_session.add(other_project)
        db_session.commit()

        response = client.get(
            "/api/v1/projects",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        # test_user のプロジェクトのみ
        assert len(data["projects"]) == 1
        assert data["projects"][0]["id"] == test_project.id

    def test_list_projects_ordered_by_created_at_desc(self, db_session, client, test_user, test_api_key):
        """list_projects() がプロジェクトを作成日時の降順で返す"""
        # 複数のプロジェクトを作成
        project1 = Project(owner_id=test_user.id, name="Project 1", local_path="/tmp/p1")
        project2 = Project(owner_id=test_user.id, name="Project 2", local_path="/tmp/p2")
        project3 = Project(owner_id=test_user.id, name="Project 3", local_path="/tmp/p3")
        db_session.add_all([project1, project2, project3])
        db_session.commit()

        response = client.get(
            "/api/v1/projects",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["projects"]) == 3

        # 最新が最初に来る
        assert data["projects"][0]["name"] == "Project 3"
        assert data["projects"][1]["name"] == "Project 2"
        assert data["projects"][2]["name"] == "Project 1"

    def test_list_projects_empty_result(self, client, test_user, test_api_key):
        """list_projects() がプロジェクトがない場合空配列を返す"""
        response = client.get(
            "/api/v1/projects",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["projects"] == []


class TestExternalTriggerRun:
    """external_trigger_run() のテスト"""

    def test_trigger_run_without_api_key(self, client, test_project):
        """API キーなしで Run を発火すると 401 が返る"""
        response = client.post(
            f"/api/v1/projects/{test_project.id}/run",
            json={"requirement": "Test requirement"}
        )

        assert response.status_code == 401

    def test_trigger_run_without_requirement(self, client, test_api_key, test_project):
        """requirement 未指定で Run を発火すると 400 が返る"""
        response = client.post(
            f"/api/v1/projects/{test_project.id}/run",
            headers={"X-Api-Key": test_api_key},
            json={}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "requirement" in data["error"].lower()

    def test_trigger_run_with_empty_requirement(self, client, test_api_key, test_project):
        """空の requirement で Run を発火すると 400 が返る"""
        response = client.post(
            f"/api/v1/projects/{test_project.id}/run",
            headers={"X-Api-Key": test_api_key},
            json={"requirement": ""}
        )

        assert response.status_code == 400

    def test_trigger_run_with_nonexistent_project(self, client, test_api_key):
        """存在しないプロジェクトで Run を発火すると 404 が返る"""
        response = client.post(
            "/api/v1/projects/99999/run",
            headers={"X-Api-Key": test_api_key},
            json={"requirement": "Test requirement"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_trigger_run_with_other_users_project(self, db_session, client, test_api_key, test_user):
        """他のユーザーのプロジェクトで Run を発火すると 404 が返る"""
        # 別のユーザーとそのプロジェクトを作成
        other_user = User(github_id="99999", github_login="otheruser")
        db_session.add(other_user)
        db_session.commit()

        other_project = Project(
            owner_id=other_user.id,
            name="Other Project",
            local_path="/tmp/other-project",
        )
        db_session.add(other_project)
        db_session.commit()

        response = client.post(
            f"/api/v1/projects/{other_project.id}/run",
            headers={"X-Api-Key": test_api_key},
            json={"requirement": "Test requirement"}
        )

        # 所有権がないので 404
        assert response.status_code == 404

    def test_trigger_run_sync_mode(self, db_session, client, test_api_key, test_project):
        """同期モードで Run を発火できる（NEXUS_USE_CELERY=0）"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "0"}):
            with patch("nexuscore.webapp.api_external.run_orchestrator_inline") as mock_inline:
                # run_orchestrator_inline が成功する
                mock_inline.return_value = None

                response = client.post(
                    f"/api/v1/projects/{test_project.id}/run",
                    headers={"X-Api-Key": test_api_key},
                    json={
                        "requirement": "Fix all bugs",
                        "autonomy_level": 2,
                        "fast_lane": True,
                    }
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data["queue_mode"] == "sync"
                assert data["project_id"] == test_project.id
                assert "run_id" in data
                assert data["status"] == "PENDING"

                # Run レコードが作成されている
                run = Run.query.filter_by(run_id=data["run_id"]).first()
                assert run is not None
                assert run.requirement == "Fix all bugs"
                assert run.autonomy_level == 2
                assert run.triggered_by == test_project.owner_id

                # run_orchestrator_inline が呼ばれた
                mock_inline.assert_called_once()
                call_kwargs = mock_inline.call_args[1]
                assert call_kwargs["requirement"] == "Fix all bugs"
                assert call_kwargs["autonomy_level"] == 2
                assert call_kwargs["fast_lane"] is True

    def test_trigger_run_async_mode(self, db_session, client, test_api_key, test_project):
        """非同期モードで Run を発火できる（NEXUS_USE_CELERY=1）"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "1"}):
            with patch("nexuscore.webapp.api_external.run_orchestrator_task") as mock_task:
                # Celery タスクが受理される
                mock_result = Mock()
                mock_task.delay.return_value = mock_result

                response = client.post(
                    f"/api/v1/projects/{test_project.id}/run",
                    headers={"X-Api-Key": test_api_key},
                    json={
                        "requirement": "Fix all bugs",
                        "autonomy_level": 3,
                    }
                )

                assert response.status_code == 202  # Accepted
                data = response.get_json()
                assert data["queue_mode"] == "async"
                assert data["project_id"] == test_project.id
                assert "run_id" in data

                # Run レコードが作成されている
                run = Run.query.filter_by(run_id=data["run_id"]).first()
                assert run is not None
                assert run.requirement == "Fix all bugs"
                assert run.autonomy_level == 3

                # Celery タスクが呼ばれた
                mock_task.delay.assert_called_once_with(run.id)

    def test_trigger_run_sync_mode_with_error(self, db_session, client, test_api_key, test_project):
        """同期モードで Run 実行中にエラーが発生した場合 500 を返す"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "0"}):
            with patch("nexuscore.webapp.api_external.run_orchestrator_inline") as mock_inline:
                # run_orchestrator_inline がエラーを投げる
                mock_inline.side_effect = Exception("Orchestrator failed")

                response = client.post(
                    f"/api/v1/projects/{test_project.id}/run",
                    headers={"X-Api-Key": test_api_key},
                    json={"requirement": "Fix all bugs"}
                )

                assert response.status_code == 500
                data = response.get_json()
                assert "error" in data
                assert "Orchestrator failed" in data["error"]
                assert data["queue_mode"] == "sync"

                # Run レコードは作成されている
                assert "run_id" in data

    def test_trigger_run_creates_run_with_uuid(self, db_session, client, test_api_key, test_project):
        """trigger_run() が UUID 形式の run_id を作成する"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "0"}):
            with patch("nexuscore.webapp.api_external.run_orchestrator_inline"):
                response = client.post(
                    f"/api/v1/projects/{test_project.id}/run",
                    headers={"X-Api-Key": test_api_key},
                    json={"requirement": "Test"}
                )

                data = response.get_json()
                run_id = data["run_id"]

                # run_id が32桁の16進数（uuid4().hex）
                assert len(run_id) == 32
                assert all(c in "0123456789abcdef" for c in run_id)

    def test_trigger_run_default_autonomy_level(self, db_session, client, test_api_key, test_project):
        """trigger_run() がデフォルトの autonomy_level を2に設定する"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "0"}):
            with patch("nexuscore.webapp.api_external.run_orchestrator_inline"):
                response = client.post(
                    f"/api/v1/projects/{test_project.id}/run",
                    headers={"X-Api-Key": test_api_key},
                    json={"requirement": "Test"}
                )

                data = response.get_json()
                run = Run.query.filter_by(run_id=data["run_id"]).first()
                assert run.autonomy_level == 2


class TestGetLatestRun:
    """get_latest_run() のテスト"""

    def test_get_latest_run_without_api_key(self, client, test_project):
        """API キーなしで最新 Run を取得すると 401 が返る"""
        response = client.get(f"/api/v1/projects/{test_project.id}/runs/latest")

        assert response.status_code == 401

    def test_get_latest_run_with_nonexistent_project(self, client, test_api_key):
        """存在しないプロジェクトで最新 Run を取得すると 404 が返る"""
        response = client.get(
            "/api/v1/projects/99999/runs/latest",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 404

    def test_get_latest_run_no_runs(self, client, test_api_key, test_project):
        """Run が存在しない場合は null を返す"""
        response = client.get(
            f"/api/v1/projects/{test_project.id}/runs/latest",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["run"] is None

    def test_get_latest_run_returns_most_recent(self, db_session, client, test_api_key, test_project):
        """get_latest_run() が最新の Run を返す"""
        from datetime import datetime, timedelta

        # 複数の Run を作成（started_at の順序で）
        now = datetime.utcnow()

        run1 = Run(
            project_id=test_project.id,
            run_id="run-1",
            status="SUCCESS",
            started_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=1),
        )
        run2 = Run(
            project_id=test_project.id,
            run_id="run-2",
            status="FAILED",
            started_at=now - timedelta(hours=1),
            finished_at=now - timedelta(minutes=30),
        )
        run3 = Run(
            project_id=test_project.id,
            run_id="run-3",
            status="RUNNING",
            started_at=now,
        )
        db_session.add_all([run1, run2, run3])
        db_session.commit()

        response = client.get(
            f"/api/v1/projects/{test_project.id}/runs/latest",
            headers={"X-Api-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["run"] is not None
        assert data["run"]["run_id"] == "run-3"
        assert data["run"]["status"] == "RUNNING"

    def test_get_latest_run_includes_timestamps(self, db_session, client, test_api_key, test_project):
        """get_latest_run() がタイムスタンプを含む"""
        from datetime import datetime

        now = datetime.utcnow()
        run = Run(
            project_id=test_project.id,
            run_id="run-1",
            status="SUCCESS",
            started_at=now,
            finished_at=now,
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f"/api/v1/projects/{test_project.id}/runs/latest",
            headers={"X-Api-Key": test_api_key}
        )

        data = response.get_json()
        assert "started_at" in data["run"]
        assert "finished_at" in data["run"]
        # ISO format
        assert "T" in data["run"]["started_at"]

    def test_get_latest_run_handles_null_timestamps(self, db_session, client, test_api_key, test_project):
        """get_latest_run() が NULL のタイムスタンプを処理する"""
        run = Run(
            project_id=test_project.id,
            run_id="run-1",
            status="PENDING",
            started_at=None,
            finished_at=None,
        )
        db_session.add(run)
        db_session.commit()

        response = client.get(
            f"/api/v1/projects/{test_project.id}/runs/latest",
            headers={"X-Api-Key": test_api_key}
        )

        data = response.get_json()
        assert data["run"]["started_at"] is None
        assert data["run"]["finished_at"] is None

    def test_get_latest_run_only_user_projects(self, db_session, client, test_api_key, test_user):
        """get_latest_run() がユーザー自身のプロジェクトのみアクセス可能"""
        # 別のユーザーとそのプロジェクトを作成
        other_user = User(github_id="99999", github_login="otheruser")
        db_session.add(other_user)
        db_session.commit()

        other_project = Project(
            owner_id=other_user.id,
            name="Other Project",
            local_path="/tmp/other-project",
        )
        db_session.add(other_project)
        db_session.commit()

        response = client.get(
            f"/api/v1/projects/{other_project.id}/runs/latest",
            headers={"X-Api-Key": test_api_key}
        )

        # 所有権がないので 404
        assert response.status_code == 404
