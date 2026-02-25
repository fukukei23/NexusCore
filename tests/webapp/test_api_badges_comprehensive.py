# ruff: noqa: F821
"""
api_badges.py の包括的なテスト

注意: このテストファイルは Flask API (api_badges.py) を前提としています。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask API (api_badges.py) は削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask API (api_badges.py) has been removed in CR-FASTAPI-010. "
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


def create_run(
    project_id: int, status: str, triggered_by: int, started_at: datetime | None = None
) -> Run:
    """テスト用Runを作成するヘルパー"""
    run = Run(
        project_id=project_id,
        run_id=f"run-{datetime.utcnow().timestamp()}",
        triggered_by=triggered_by,
        status=status,
        started_at=started_at or datetime.utcnow(),
    )
    db.session.add(run)
    db.session.commit()
    return run


# ============================================================================
# Tests: project_success_rate_badge()
# ============================================================================


class TestProjectSuccessRateBadge:
    """project_success_rate_badge() のテスト"""

    def test_success_rate_badge_with_no_runs(self, client, test_project):
        """Runが1つもない場合は成功率0%"""
        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        assert data["schemaVersion"] == 1
        assert data["label"] == "self-healing"
        assert "0.0% success" in data["message"]
        assert data["color"] == "red"

    def test_success_rate_badge_with_100_percent_success(self, client, test_project, test_user):
        """すべてのRunが成功している場合は100%、brightgreen"""
        for _ in range(10):
            create_run(test_project.id, "SUCCESS", test_user.id)

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        assert data["schemaVersion"] == 1
        assert "100.0% success" in data["message"]
        assert data["color"] == "brightgreen"

    def test_success_rate_badge_with_90_percent_success(self, client, test_project, test_user):
        """90%以上の成功率はbrightgreen"""
        for _ in range(9):
            create_run(test_project.id, "SUCCESS", test_user.id)
        create_run(test_project.id, "FAILED", test_user.id)

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        assert "90.0% success" in data["message"]
        assert data["color"] == "brightgreen"

    def test_success_rate_badge_with_70_to_89_percent_success(
        self, client, test_project, test_user
    ):
        """70-89%の成功率はgreen"""
        for _ in range(8):
            create_run(test_project.id, "SUCCESS", test_user.id)
        for _ in range(2):
            create_run(test_project.id, "FAILED", test_user.id)

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        assert "80.0% success" in data["message"]
        assert data["color"] == "green"

    def test_success_rate_badge_with_50_to_69_percent_success(
        self, client, test_project, test_user
    ):
        """50-69%の成功率はyellow"""
        for _ in range(6):
            create_run(test_project.id, "SUCCESS", test_user.id)
        for _ in range(4):
            create_run(test_project.id, "FAILED", test_user.id)

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        assert "60.0% success" in data["message"]
        assert data["color"] == "yellow"

    def test_success_rate_badge_with_below_50_percent_success(
        self, client, test_project, test_user
    ):
        """50%未満の成功率はred"""
        for _ in range(3):
            create_run(test_project.id, "SUCCESS", test_user.id)
        for _ in range(7):
            create_run(test_project.id, "FAILED", test_user.id)

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        assert "30.0% success" in data["message"]
        assert data["color"] == "red"

    def test_success_rate_badge_with_more_than_30_runs(self, client, test_project, test_user):
        """30回を超えるRunがある場合は最新30回のみを使用"""
        # 古いRun: すべて失敗（無視される）
        for i in range(20):
            create_run(
                test_project.id,
                "FAILED",
                test_user.id,
                started_at=datetime.utcnow() - timedelta(days=100 - i),
            )

        # 最新30回: すべて成功
        for i in range(30):
            create_run(
                test_project.id,
                "SUCCESS",
                test_user.id,
                started_at=datetime.utcnow() - timedelta(days=30 - i),
            )

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        # 最新30回はすべて成功なので100%
        assert "100.0% success" in data["message"]
        assert data["color"] == "brightgreen"

    def test_success_rate_badge_with_mixed_statuses(self, client, test_project, test_user):
        """SUCCESS以外のステータスは失敗とカウントされる"""
        for _ in range(5):
            create_run(test_project.id, "SUCCESS", test_user.id)
        for _ in range(2):
            create_run(test_project.id, "FAILED", test_user.id)
        for _ in range(2):
            create_run(test_project.id, "RUNNING", test_user.id)
        create_run(test_project.id, "PENDING", test_user.id)

        response = client.get(f"/api/projects/{test_project.id}/badge/success_rate")

        assert response.status_code == 200
        data = response.json
        # 10件中5件SUCCESS = 50%
        assert "50.0% success" in data["message"]
        assert data["color"] == "yellow"

    def test_success_rate_badge_with_invalid_project_id(self, client):
        """存在しないproject_idは404エラー"""
        response = client.get("/api/projects/99999/badge/success_rate")
        assert response.status_code == 404


# ============================================================================
# Tests: project_last_run_badge()
# ============================================================================


class TestProjectLastRunBadge:
    """project_last_run_badge() のテスト"""

    def test_last_run_badge_with_no_runs(self, client, test_project):
        """Runが1つもない場合はlast: -, lightgrey"""
        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        assert data["schemaVersion"] == 1
        assert data["label"] == "self-healing"
        assert data["message"] == "last: -"
        assert data["color"] == "lightgrey"

    def test_last_run_badge_with_success_status(self, client, test_project, test_user):
        """最新RunがSUCCESSの場合はbrightgreen"""
        create_run(
            test_project.id,
            "FAILED",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        create_run(
            test_project.id,
            "SUCCESS",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        assert data["message"] == "last: SUCCESS"
        assert data["color"] == "brightgreen"

    def test_last_run_badge_with_failed_status(self, client, test_project, test_user):
        """最新RunがFAILEDの場合はred"""
        create_run(
            test_project.id,
            "SUCCESS",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        create_run(
            test_project.id,
            "FAILED",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        assert data["message"] == "last: FAILED"
        assert data["color"] == "red"

    def test_last_run_badge_with_running_status(self, client, test_project, test_user):
        """最新RunがRUNNINGの場合はblue"""
        create_run(
            test_project.id,
            "SUCCESS",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        create_run(
            test_project.id,
            "RUNNING",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        assert data["message"] == "last: RUNNING"
        assert data["color"] == "blue"

    def test_last_run_badge_with_pending_status(self, client, test_project, test_user):
        """最新RunがPENDINGの場合はlightgrey"""
        create_run(
            test_project.id,
            "SUCCESS",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        create_run(
            test_project.id,
            "PENDING",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        # PENDINGは"その他"扱い
        assert "PENDING" in data["message"]
        assert data["color"] == "lightgrey"

    def test_last_run_badge_with_null_status(self, client, test_project, test_user):
        """statusがNullの場合はPENDING扱い"""
        run = Run(
            project_id=test_project.id,
            run_id="run-null-status",
            triggered_by=test_user.id,
            status=None,
            started_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        # statusがNoneの場合、s or "PENDING"が"PENDING"になる
        assert "PENDING" in data["message"]
        assert data["color"] == "lightgrey"

    def test_last_run_badge_with_custom_status(self, client, test_project, test_user):
        """カスタムステータスの場合はlightgrey"""
        run = Run(
            project_id=test_project.id,
            run_id="run-custom-status",
            triggered_by=test_user.id,
            status="CUSTOM_STATUS",
            started_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        assert "CUSTOM_STATUS" in data["message"]
        assert data["color"] == "lightgrey"

    def test_last_run_badge_with_lowercase_status(self, client, test_project, test_user):
        """小文字のステータスも大文字に変換される"""
        run = Run(
            project_id=test_project.id,
            run_id="run-lowercase-status",
            triggered_by=test_user.id,
            status="success",
            started_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        assert "SUCCESS" in data["message"]
        assert data["color"] == "brightgreen"

    def test_last_run_badge_with_invalid_project_id(self, client):
        """存在しないproject_idは404エラー"""
        response = client.get("/api/projects/99999/badge/last_run")
        assert response.status_code == 404

    def test_last_run_badge_orders_by_started_at(self, client, test_project, test_user):
        """started_atが最新のRunを使用する"""
        # 古いRun
        create_run(
            test_project.id,
            "SUCCESS",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=10),
        )
        create_run(
            test_project.id,
            "PENDING",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=8),
        )

        # 最新Run
        create_run(
            test_project.id,
            "FAILED",
            test_user.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = client.get(f"/api/projects/{test_project.id}/badge/last_run")

        assert response.status_code == 200
        data = response.json
        # 最新のRunはFAILED
        assert data["message"] == "last: FAILED"
        assert data["color"] == "red"
