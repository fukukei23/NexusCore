"""
views_dashboard.py の包括的なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy views_dashboard comprehensive tests have been removed in CR-FASTAPI-010. "
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
# Tests: GET /dashboard/
# ============================================================================


class TestDashboard:
    """GET /dashboard/ のテスト"""

    def test_dashboard_without_auth_redirects(self, client):
        """認証なしはリダイレクトされる"""
        response = client.get("/dashboard/")
        assert response.status_code in [302, 401]

    def test_dashboard_with_auth_returns_html(self, authenticated_client, test_user):
        """認証済みユーザーはダッシュボードHTMLを取得できる"""
        response = authenticated_client.get("/dashboard/")

        assert response.status_code == 200
        assert b"Dashboard" in response.data
        assert test_user.github_login.encode() in response.data

    def test_dashboard_with_no_projects(self, authenticated_client, test_user):
        """プロジェクトがない場合も正常に表示される"""
        response = authenticated_client.get("/dashboard/")

        assert response.status_code == 200
        assert b"Total Runs: 0" in response.data

    def test_dashboard_displays_statistics(
        self, authenticated_client, test_user, test_project, test_run
    ):
        """統計情報が表示される"""
        response = authenticated_client.get("/dashboard/")

        assert response.status_code == 200
        assert b"Total Runs:" in response.data
        assert b"Success:" in response.data
        assert b"Failed:" in response.data
        assert b"Success Rate:" in response.data

    def test_dashboard_with_project_filter(self, authenticated_client, test_user, test_project):
        """project_idでフィルタリングできる"""
        response = authenticated_client.get(f"/dashboard/?project_id={test_project.id}")

        assert response.status_code == 200
        assert test_project.name.encode() in response.data

    def test_dashboard_with_invalid_project_returns_404(self, authenticated_client, test_user):
        """存在しないproject_idは404エラー"""
        response = authenticated_client.get("/dashboard/?project_id=99999")
        assert response.status_code == 404

    def test_dashboard_only_shows_own_projects(self, authenticated_client, app, test_user):
        """他のユーザーのプロジェクトは表示されない"""
        # 別のユーザーとプロジェクトを作成
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.get("/dashboard/")

        assert response.status_code == 200
        assert b"other_project" not in response.data

    def test_dashboard_displays_llm_stats(
        self, authenticated_client, test_user, test_project, test_run
    ):
        """LLM使用統計が表示される"""
        # ExecutionLogを作成
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json=json.dumps({"model": "gpt-4", "cost_est_usd": 0.05}),
        )
        db.session.add(log)
        db.session.commit()

        response = authenticated_client.get("/dashboard/")

        assert response.status_code == 200
        assert b"LLM Usage" in response.data
        # SQLiteではJSON操作がサポートされていないため、テーブルが空でもOK
        # PostgreSQLなどのDBではgpt-4が表示される

    def test_dashboard_json_response(self, authenticated_client, test_user, test_project, test_run):
        """Accept: application/jsonヘッダーでJSON形式を返す"""
        response = authenticated_client.get("/dashboard/", headers={"Accept": "application/json"})

        assert response.status_code == 200
        data = response.json
        assert "projects" in data
        assert "stats" in data
        assert "llm_stats" in data
        assert data["stats"]["total_runs"] == 1

    def test_dashboard_calculates_success_rate(self, authenticated_client, test_user, test_project):
        """成功率が正しく計算される"""
        # 成功3件、失敗2件
        for _ in range(3):
            run = Run(
                project_id=test_project.id,
                run_id=f"success-{_}",
                triggered_by=test_user.id,
                status="SUCCESS",
            )
            db.session.add(run)

        for _ in range(2):
            run = Run(
                project_id=test_project.id,
                run_id=f"failed-{_}",
                triggered_by=test_user.id,
                status="FAILED",
            )
            db.session.add(run)
        db.session.commit()

        response = authenticated_client.get("/dashboard/", headers={"Accept": "application/json"})

        assert response.status_code == 200
        data = response.json
        assert data["stats"]["success_rate"] == 60.0  # 3/5 = 60%


# ============================================================================
# Tests: GET /dashboard/projects/<id>
# ============================================================================


class TestProjectDashboard:
    """GET /dashboard/projects/<id> のテスト"""

    def test_project_dashboard_without_auth_redirects(self, client, test_project):
        """認証なしはリダイレクトされる"""
        response = client.get(f"/dashboard/projects/{test_project.id}")
        assert response.status_code in [302, 401]

    def test_project_dashboard_with_auth_returns_html(self, authenticated_client, test_project):
        """認証済みユーザーはプロジェクトダッシュボードを取得できる"""
        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Project:" in response.data or test_project.name.encode() in response.data

    def test_project_dashboard_with_invalid_project_returns_404(self, authenticated_client):
        """存在しないproject_idは404エラー"""
        response = authenticated_client.get("/dashboard/projects/99999")
        assert response.status_code == 404

    def test_project_dashboard_only_shows_own_project(self, authenticated_client, app, test_user):
        """他のユーザーのプロジェクトは404エラー"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.get(f"/dashboard/projects/{other_project.id}")
        assert response.status_code == 404

    def test_project_dashboard_displays_statistics(
        self, authenticated_client, test_project, test_run
    ):
        """統計カードが表示される"""
        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Success Rate" in response.data
        assert b"Total Runs" in response.data

    def test_project_dashboard_displays_latest_run(
        self, authenticated_client, test_project, test_run
    ):
        """最新Run情報が表示される"""
        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Latest Run" in response.data
        assert test_run.run_id[:8].encode() in response.data

    def test_project_dashboard_displays_llm_breakdown(
        self, authenticated_client, test_project, test_run
    ):
        """LLMコスト内訳が表示される"""
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json=json.dumps(
                {
                    "model": "gpt-4",
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
                    "estimated_cost": 0.05,
                }
            ),
        )
        db.session.add(log)
        db.session.commit()

        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"LLM Cost Breakdown" in response.data
        assert b"gpt-4" in response.data

    def test_project_dashboard_displays_recent_runs(
        self, authenticated_client, test_project, test_user
    ):
        """直近のRun一覧が表示される"""
        # 5件のRunを作成
        for i in range(5):
            run = Run(
                project_id=test_project.id,
                run_id=f"run-{i}",
                triggered_by=test_user.id,
                status="SUCCESS",
                created_at=datetime.utcnow() - timedelta(hours=i),
            )
            db.session.add(run)
        db.session.commit()

        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Recent Runs" in response.data

    def test_project_dashboard_with_no_runs(self, authenticated_client, test_project):
        """Runがない場合も正常に表示される"""
        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        # エラーが発生しないことを確認

    def test_project_dashboard_with_patches(self, authenticated_client, test_project, test_run):
        """パッチ情報が表示される"""
        patch = PatchRecord(
            run_id=test_run.id,
            file_path="/test/file.py",
            diff_text="test patch",
        )
        db.session.add(patch)
        db.session.commit()

        response = authenticated_client.get(f"/dashboard/projects/{test_project.id}")

        assert response.status_code == 200
        # パッチ数が表示されるはず
        assert b"Patches" in response.data or b"files" in response.data.lower()


# ============================================================================
# Tests: GET /dashboard/gradio/<id>
# ============================================================================


class TestGradioDashboard:
    """GET /dashboard/gradio/<id> のテスト"""

    def test_gradio_dashboard_without_auth_redirects(self, client, test_project):
        """認証なしはリダイレクトされる"""
        response = client.get(f"/dashboard/gradio/{test_project.id}")
        assert response.status_code in [302, 401]

    def test_gradio_dashboard_with_auth_returns_html(self, authenticated_client, test_project):
        """認証済みユーザーはGradioダッシュボードを取得できる"""
        response = authenticated_client.get(f"/dashboard/gradio/{test_project.id}")

        assert response.status_code == 200
        assert b"Gradio" in response.data
        assert test_project.name.encode() in response.data

    def test_gradio_dashboard_with_invalid_project_returns_404(self, authenticated_client):
        """存在しないproject_idは404エラー"""
        response = authenticated_client.get("/dashboard/gradio/99999")
        assert response.status_code == 404

    def test_gradio_dashboard_only_shows_own_project(self, authenticated_client, app, test_user):
        """他のユーザーのプロジェクトは404エラー"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.get(f"/dashboard/gradio/{other_project.id}")
        assert response.status_code == 404

    def test_gradio_dashboard_contains_iframe(self, authenticated_client, test_project):
        """Gradio URLへのiframeが含まれる"""
        response = authenticated_client.get(f"/dashboard/gradio/{test_project.id}")

        assert response.status_code == 200
        assert b"<iframe" in response.data
        assert b"localhost:7860" in response.data
        assert f"project_id={test_project.id}".encode() in response.data


# ============================================================================
# Tests: ヘルパー関数
# ============================================================================


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_render_llm_cost_table_with_data(self, app):
        """_render_llm_cost_table()がテーブルHTMLを生成する"""
        from nexuscore.webapp.views_dashboard import _render_llm_cost_table

        llm_breakdown = {
            "gpt-4": {
                "call_count": 10,
                "token_prompt": 1000,
                "token_completion": 500,
                "token_total": 1500,
                "cost_total": 15.0,
            },
        }

        result = _render_llm_cost_table(llm_breakdown)

        assert "<table" in result
        assert "gpt-4" in result
        assert "10" in result
        assert "1000" in result
        assert "15.0" in result or "15.00" in result

    def test_render_llm_cost_table_with_empty_data(self, app):
        """_render_llm_cost_table()が空データでも動作する"""
        from nexuscore.webapp.views_dashboard import _render_llm_cost_table

        result = _render_llm_cost_table({})

        assert "<table" in result

    def test_render_recent_runs_list_with_runs(self, app, test_project, test_run):
        """_render_recent_runs_list()がRun一覧HTMLを生成する"""
        from nexuscore.webapp.views_dashboard import _render_recent_runs_list

        runs = [test_run]
        result = _render_recent_runs_list(test_project, runs)

        assert "<ul" in result or "<li" in result
        assert test_run.run_id[:8] in result

    def test_render_recent_runs_list_with_no_runs(self, app, test_project):
        """_render_recent_runs_list()がRun 0件でも動作する"""
        from nexuscore.webapp.views_dashboard import _render_recent_runs_list

        result = _render_recent_runs_list(test_project, [])

        assert "No runs" in result

    def test_render_project_dashboard_html(self, app, test_project, test_run):
        """render_project_dashboard_html()が完全なHTMLを生成する"""
        from nexuscore.webapp.views_dashboard import render_project_dashboard_html

        stats = {
            "total_runs": 1,
            "success_runs": 1,
            "failed_runs": 0,
            "success_rate": 1.0,
        }

        html = render_project_dashboard_html(
            project=test_project,
            stats=stats,
            recent_runs=[test_run],
            latest_run=test_run,
            latest_run_metrics={
                "patch_count": 1,
                "affected_files": 1,
                "llm_call_count_total": 5,
                "estimated_cost_total": 10.0,
                "duration_sec": 60.0,
            },
            llm_breakdown={},
        )

        assert "<!DOCTYPE html>" in html
        assert test_project.name in html
        assert "100.0%" in html  # success rate
        assert "1" in html  # total runs
