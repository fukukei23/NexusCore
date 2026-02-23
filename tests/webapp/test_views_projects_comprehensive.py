"""
views_projects.py の包括的なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy views_projects comprehensive tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def app():
    """Flask test app with in-memory SQLite database"""
    from nexuscore.webapp import create_app

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
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """テスト用ユーザー"""
    user = User(
        github_id="12345",
        github_login="testuser",
        name="Test User",
        email="test@example.com",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_project(app, test_user):
    """テスト用プロジェクト"""
    project = Project(
        owner_id=test_user.id,
        name="test_project",
        local_path="/tmp/test",
        repo_url="https://github.com/test/repo",
    )
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture
def test_run(app, test_project):
    """テスト用Run"""
    run = Run(
        project_id=test_project.id,
        run_id="test-run-123",
        triggered_by=test_project.owner_id,
        status="SUCCESS",
        started_at=datetime.utcnow() - timedelta(hours=1),
        finished_at=datetime.utcnow(),
    )
    db.session.add(run)
    db.session.commit()
    return run


@pytest.fixture
def authenticated_client(client, app, test_user):
    """認証済みクライアント"""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user.id
    return client


# ============================================================================
# Tests: ヘルパー関数
# ============================================================================


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_format_duration_with_seconds(self, app):
        """_format_duration()が秒を正しくフォーマットする"""
        from nexuscore.webapp.views_projects import _format_duration

        assert _format_duration(45) == "45s"
        assert _format_duration(59) == "59s"

    def test_format_duration_with_minutes(self, app):
        """_format_duration()が分を正しくフォーマットする"""
        from nexuscore.webapp.views_projects import _format_duration

        assert _format_duration(90) == "1m 30s"
        assert _format_duration(3599) == "59m 59s"

    def test_format_duration_with_hours(self, app):
        """_format_duration()が時間を正しくフォーマットする"""
        from nexuscore.webapp.views_projects import _format_duration

        assert _format_duration(3600) == "1h 0m"
        assert _format_duration(7200) == "2h 0m"

    def test_format_duration_with_none(self, app):
        """_format_duration()がNoneの場合は"-"を返す"""
        from nexuscore.webapp.views_projects import _format_duration

        assert _format_duration(None) == "-"

    def test_compute_run_duration_with_both_times(self, app, test_run):
        """_compute_run_duration()が実行時間を計算する"""
        from nexuscore.webapp.views_projects import _compute_run_duration

        duration = _compute_run_duration(test_run)
        assert duration is not None
        assert duration > 0

    def test_compute_run_duration_without_times(self, app, test_project):
        """_compute_run_duration()がタイムスタンプなしの場合Noneを返す"""
        from nexuscore.webapp.views_projects import _compute_run_duration

        run = Run(
            project_id=test_project.id,
            run_id="test",
            triggered_by=test_project.owner_id,
            status="PENDING",
        )
        db.session.add(run)
        db.session.commit()

        assert _compute_run_duration(run) is None

    def test_render_run_status_badge_success(self, app):
        """_render_run_status_badge()がSUCCESSバッジを生成する"""
        from nexuscore.webapp.views_projects import _render_run_status_badge

        result = _render_run_status_badge("SUCCESS")
        assert "status-success" in result
        assert "✔" in result
        assert "SUCCESS" in result

    def test_render_run_status_badge_failed(self, app):
        """_render_run_status_badge()がFAILEDバッジを生成する"""
        from nexuscore.webapp.views_projects import _render_run_status_badge

        result = _render_run_status_badge("FAILED")
        assert "status-failed" in result
        assert "✖" in result
        assert "FAILED" in result

    def test_render_run_status_badge_running(self, app):
        """_render_run_status_badge()がRUNNINGバッジを生成する"""
        from nexuscore.webapp.views_projects import _render_run_status_badge

        result = _render_run_status_badge("RUNNING")
        assert "status-running" in result
        assert "▶" in result
        assert "RUNNING" in result

    def test_render_run_status_badge_pending(self, app):
        """_render_run_status_badge()がPENDINGバッジを生成する"""
        from nexuscore.webapp.views_projects import _render_run_status_badge

        result = _render_run_status_badge("PENDING")
        assert "status-pending" in result
        assert "⏱" in result

    def test_render_run_table_with_runs(self, app, test_project, test_run):
        """render_run_table()がRun一覧テーブルを生成する"""
        from nexuscore.webapp.views_projects import render_run_table

        result = render_run_table(test_project, [test_run])

        assert "<table" in result
        assert test_run.run_id[:8] in result
        assert "SUCCESS" in result

    def test_render_run_table_with_no_runs(self, app, test_project):
        """render_run_table()がRun 0件でも動作する"""
        from nexuscore.webapp.views_projects import render_run_table

        result = render_run_table(test_project, [])

        assert "<table" in result


# ============================================================================
# Tests: GET /projects/
# ============================================================================


class TestListProjects:
    """GET /projects/ のテスト"""

    def test_list_projects_without_auth_redirects(self, client):
        """認証なしはリダイレクトされる"""
        response = client.get("/projects/")
        assert response.status_code in [302, 401]

    def test_list_projects_with_auth_returns_html(self, authenticated_client, test_user):
        """認証済みユーザーはプロジェクト一覧HTMLを取得できる"""
        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        assert b"Projects" in response.data
        assert test_user.github_login.encode() in response.data

    def test_list_projects_displays_projects(self, authenticated_client, test_project):
        """プロジェクトが表示される"""
        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        assert test_project.name.encode() in response.data

    def test_list_projects_with_no_projects(self, authenticated_client, test_user):
        """プロジェクト 0件でも正常に表示される"""
        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        # エラーが発生しないことを確認

    def test_list_projects_only_shows_own_projects(self, authenticated_client, app, test_user):
        """他のユーザーのプロジェクトは表示されない"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        assert b"other_project" not in response.data

    def test_list_projects_displays_success_rate(
        self, authenticated_client, test_project, test_user
    ):
        """成功率が表示される"""
        # Runを作成
        for _ in range(10):
            run = Run(
                project_id=test_project.id,
                run_id=f"run-{_}",
                triggered_by=test_user.id,
                status="SUCCESS",
                started_at=datetime.utcnow() - timedelta(hours=_),
            )
            db.session.add(run)
        db.session.commit()

        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        assert b"Success Rate" in response.data

    def test_list_projects_displays_latest_run_status(
        self, authenticated_client, test_project, test_run
    ):
        """最新Runステータスが表示される"""
        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        assert b"Latest Status" in response.data or b"SUCCESS" in response.data

    def test_list_projects_json_response(self, authenticated_client, test_project):
        """Accept: application/jsonヘッダーでJSON形式を返す"""
        response = authenticated_client.get("/projects/", headers={"Accept": "application/json"})

        assert response.status_code == 200
        data = response.json
        assert "projects" in data
        assert len(data["projects"]) >= 1
        assert data["projects"][0]["name"] == test_project.name

    def test_list_projects_has_create_link(self, authenticated_client, test_user):
        """新規作成リンクが含まれる"""
        response = authenticated_client.get("/projects/")

        assert response.status_code == 200
        assert b"Create New Project" in response.data or b"/projects/new" in response.data


# ============================================================================
# Tests: GET /projects/<id>
# ============================================================================


class TestProjectDetail:
    """GET /projects/<id> のテスト"""

    def test_project_detail_without_auth_redirects(self, client, test_project):
        """認証なしはリダイレクトされる"""
        response = client.get(f"/projects/{test_project.id}")
        assert response.status_code in [302, 401]

    def test_project_detail_with_auth_returns_html(self, authenticated_client, test_project):
        """認証済みユーザーはプロジェクト詳細HTMLを取得できる"""
        response = authenticated_client.get(f"/projects/{test_project.id}")

        assert response.status_code == 200
        assert test_project.name.encode() in response.data

    def test_project_detail_with_invalid_project_returns_404(self, authenticated_client):
        """存在しないproject_idは404エラー"""
        response = authenticated_client.get("/projects/99999")
        assert response.status_code == 404

    def test_project_detail_only_shows_own_project(self, authenticated_client, app, test_user):
        """他のユーザーのプロジェクトは404エラー"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.get(f"/projects/{other_project.id}")
        assert response.status_code == 404

    def test_project_detail_displays_project_info(self, authenticated_client, test_project):
        """プロジェクト情報が表示される"""
        response = authenticated_client.get(f"/projects/{test_project.id}")

        assert response.status_code == 200
        assert test_project.name.encode() in response.data
        assert test_project.local_path.encode() in response.data
        if test_project.repo_url:
            assert test_project.repo_url.encode() in response.data

    def test_project_detail_displays_runs_table(self, authenticated_client, test_project, test_run):
        """Run一覧テーブルが表示される"""
        response = authenticated_client.get(f"/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Recent Runs" in response.data or b"<table" in response.data
        assert test_run.run_id[:8].encode() in response.data

    def test_project_detail_with_no_runs(self, authenticated_client, test_project):
        """Run 0件でも正常に表示される"""
        response = authenticated_client.get(f"/projects/{test_project.id}")

        assert response.status_code == 200
        # エラーが発生しないことを確認

    def test_project_detail_json_response(self, authenticated_client, test_project, test_run):
        """Accept: application/jsonヘッダーでJSON形式を返す"""
        response = authenticated_client.get(
            f"/projects/{test_project.id}", headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        data = response.json
        assert "project" in data
        assert "runs" in data
        assert data["project"]["name"] == test_project.name

    def test_project_detail_has_dashboard_link(self, authenticated_client, test_project):
        """ダッシュボードリンクが含まれる"""
        response = authenticated_client.get(f"/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Project Dashboard" in response.data or b"/dashboard/" in response.data


# ============================================================================
# Tests: GET/POST /projects/new
# ============================================================================


class TestCreateProject:
    """GET/POST /projects/new のテスト"""

    def test_create_project_get_without_auth_redirects(self, client):
        """認証なしはリダイレクトされる"""
        response = client.get("/projects/new")
        assert response.status_code in [302, 401]

    def test_create_project_get_with_auth_returns_form(self, authenticated_client):
        """認証済みユーザーは作成フォームを取得できる"""
        response = authenticated_client.get("/projects/new")

        assert response.status_code == 200
        assert b"Create New Project" in response.data
        assert b"<form" in response.data
        assert b'name="name"' in response.data
        assert b'name="local_path"' in response.data

    def test_create_project_post_creates_project(self, authenticated_client, test_user):
        """POSTでプロジェクトを作成できる"""
        response = authenticated_client.post(
            "/projects/new",
            data={
                "name": "New Project",
                "local_path": "/tmp/new",
                "repo_url": "https://github.com/test/new",
            },
        )

        assert response.status_code == 302  # リダイレクト

        # プロジェクトが作成されたことを確認
        project = Project.query.filter_by(name="New Project").first()
        assert project is not None
        assert project.owner_id == test_user.id
        assert project.local_path == "/tmp/new"

    def test_create_project_post_without_name_returns_error(self, authenticated_client):
        """nameなしはエラー"""
        response = authenticated_client.post(
            "/projects/new",
            data={
                "local_path": "/tmp/new",
            },
        )

        assert response.status_code == 400
        assert b"error" in response.data.lower() or b"required" in response.data.lower()

    def test_create_project_post_without_local_path_returns_error(self, authenticated_client):
        """local_pathなしはエラー"""
        response = authenticated_client.post(
            "/projects/new",
            data={
                "name": "New Project",
            },
        )

        assert response.status_code == 400

    def test_create_project_post_without_repo_url_is_ok(self, authenticated_client, test_user):
        """repo_urlなしでも作成できる"""
        response = authenticated_client.post(
            "/projects/new",
            data={
                "name": "New Project",
                "local_path": "/tmp/new",
            },
        )

        assert response.status_code == 302

        project = Project.query.filter_by(name="New Project").first()
        assert project is not None
        assert project.repo_url is None


# ============================================================================
# Tests: POST /projects/<id>/run
# ============================================================================


class TestTriggerRun:
    """POST /projects/<id>/run のテスト"""

    def test_trigger_run_without_auth_redirects(self, client, test_project):
        """認証なしはリダイレクトされる"""
        response = client.post(f"/projects/{test_project.id}/run")
        assert response.status_code in [302, 401]

    def test_trigger_run_without_requirement_returns_error(
        self, authenticated_client, test_project
    ):
        """requirementなしはエラー"""
        response = authenticated_client.post(f"/projects/{test_project.id}/run", json={})

        assert response.status_code == 400

    @patch.dict("os.environ", {"NEXUS_USE_CELERY": "1"})
    @patch("nexuscore.webapp.celery_app.run_orchestrator_task")
    def test_trigger_run_with_celery(self, mock_task, authenticated_client, test_project):
        """Celery使用時はタスクをキューに入れる"""
        mock_task.delay.return_value = Mock(id="task-123")

        response = authenticated_client.post(
            f"/projects/{test_project.id}/run", json={"requirement": "Fix bugs"}
        )

        # Runが作成されている
        run = Run.query.filter_by(project_id=test_project.id).first()
        assert run is not None
        assert run.status == "PENDING"
        assert run.requirement == "Fix bugs"

        # Celeryタスクが呼ばれた
        mock_task.delay.assert_called_once()

    @patch.dict("os.environ", {"NEXUS_USE_CELERY": "0"})
    @patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_inline")
    def test_trigger_run_without_celery(self, mock_inline, authenticated_client, test_project):
        """Celery未使用時は同期実行"""
        response = authenticated_client.post(
            f"/projects/{test_project.id}/run", json={"requirement": "Run tests"}
        )

        # Runが作成されている
        run = Run.query.filter_by(project_id=test_project.id).first()
        assert run is not None

        # run_orchestrator_inlineが呼ばれた
        mock_inline.assert_called_once()

    def test_trigger_run_with_autonomy_level(self, authenticated_client, test_project):
        """autonomy_levelパラメータを受け入れる"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "1"}):
            with patch("nexuscore.webapp.celery_app.run_orchestrator_task") as mock_task:
                mock_task.delay.return_value = Mock(id="task-123")

                response = authenticated_client.post(
                    f"/projects/{test_project.id}/run",
                    json={"requirement": "Test", "autonomy_level": 2},
                )

                run = Run.query.filter_by(project_id=test_project.id).first()
                assert run.autonomy_level == 2

    def test_trigger_run_with_fast_lane(self, authenticated_client, test_project):
        """fast_laneパラメータを受け入れる"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "1"}):
            with patch("nexuscore.webapp.celery_app.run_orchestrator_task") as mock_task:
                mock_task.delay.return_value = Mock(id="task-123")

                response = authenticated_client.post(
                    f"/projects/{test_project.id}/run",
                    json={"requirement": "Test", "fast_lane": True},
                )

                # Runが作成されている
                run = Run.query.filter_by(project_id=test_project.id).first()
                assert run is not None

    def test_trigger_run_only_own_project(self, authenticated_client, app, test_user):
        """他のユーザーのプロジェクトは404エラー"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.post(
            f"/projects/{other_project.id}/run", json={"requirement": "Test"}
        )

        assert response.status_code == 404

    def test_trigger_run_json_response(self, authenticated_client, test_project):
        """JSON形式で応答を返す"""
        with patch.dict("os.environ", {"NEXUS_USE_CELERY": "1"}):
            with patch("nexuscore.webapp.celery_app.run_orchestrator_task") as mock_task:
                mock_task.delay.return_value = Mock(id="task-123")

                response = authenticated_client.post(
                    f"/projects/{test_project.id}/run",
                    json={"requirement": "Test"},
                    headers={"Accept": "application/json"},
                )

                assert response.status_code == 202
                data = response.json
                assert "run_id" in data
                assert "status" in data
