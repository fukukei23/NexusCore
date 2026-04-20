# ruff: noqa: F821
"""
views_logs.py の包括的なテスト

Flask Blueprint `/logs` の2ルートをテスト:
- GET /logs/projects/<int:project_id>
- GET /logs/runs/<string:run_id>

in-memory SQLite + mock で外部依存を分離。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import ExecutionLog, PatchRecord, Project, Run, User


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def app():
    """Flask test app with in-memory SQLite database"""
    test_app = create_app(
        config_overrides={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with test_app.app_context():
        db.create_all()
        yield test_app
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
        run_id="test-run-abc12345",
        triggered_by=test_project.owner_id,
        status="SUCCESS",
        started_at=datetime.utcnow() - timedelta(hours=1),
        finished_at=datetime.utcnow(),
    )
    db.session.add(run)
    db.session.commit()
    return run


@pytest.fixture
def test_execution_log(app, test_run):
    """テスト用ExecutionLog"""
    log = ExecutionLog(
        run_id=test_run.id,
        source="NPE",
        level="INFO",
        message="Test log message",
        payload_json={"model": "gpt-4", "cost": 0.05},
    )
    db.session.add(log)
    db.session.commit()
    return log


@pytest.fixture
def authenticated_client(client, test_user):
    """認証済みクライアント"""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user.id
    return client


# run_logs 用の共通 mock
MOCK_PATCHES = [
    "nexuscore.integration.github_pr_comment._collect_run_metrics",
    "nexuscore.integration.run_report_generator.get_markdown_report_path",
    "nexuscore.webapp.views_projects._compute_run_duration",
    "nexuscore.webapp.views_projects._format_duration",
    "nexuscore.webapp.views_projects._render_run_status_badge",
]


def _mock_run_logs_deps():
    """run_logs の外部依存を一括 mock する context manager を返す"""
    return patch.multiple(
        "nexuscore.integration.github_pr_comment",
        _collect_run_metrics=lambda run: {"estimated_cost_jpy": 15.0},
    )


# ============================================================================
# Tests: GET /logs/projects/<id>
# ============================================================================


class TestProjectLogs:
    """GET /logs/projects/<id> のテスト"""

    def test_project_logs_without_auth_redirects(self, client, test_project):
        """認証なしはリダイレクトされる"""
        response = client.get(f"/logs/projects/{test_project.id}")
        assert response.status_code in [302, 401]

    def test_project_logs_with_auth_returns_html(self, authenticated_client, test_project):
        """認証済みユーザーはログHTMLを取得できる"""
        response = authenticated_client.get(f"/logs/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Logs:" in response.data
        assert test_project.name.encode() in response.data

    def test_project_logs_with_invalid_project_returns_404(self, authenticated_client):
        """存在しないproject_idは404エラー"""
        response = authenticated_client.get("/logs/projects/99999")
        assert response.status_code == 404

    def test_project_logs_only_shows_own_project(self, authenticated_client, test_user):
        """他のユーザーのプロジェクトは404エラー"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        response = authenticated_client.get(f"/logs/projects/{other_project.id}")
        assert response.status_code == 404

    def test_project_logs_displays_logs(
        self, authenticated_client, test_project, test_run, test_execution_log
    ):
        """ログエントリが表示される"""
        response = authenticated_client.get(f"/logs/projects/{test_project.id}")

        assert response.status_code == 200
        assert b"Test log message" in response.data
        assert b"NPE" in response.data

    def test_project_logs_with_source_filter(self, authenticated_client, test_project, test_run):
        """sourceでフィルタリングできる"""
        log1 = ExecutionLog(run_id=test_run.id, source="NPE", level="INFO", message="NPE log")
        log2 = ExecutionLog(
            run_id=test_run.id, source="ORCHESTRATOR", level="INFO", message="Orchestrator log"
        )
        db.session.add_all([log1, log2])
        db.session.commit()

        response = authenticated_client.get(f"/logs/projects/{test_project.id}?source=NPE")

        assert response.status_code == 200
        assert b"NPE log" in response.data

    def test_project_logs_with_level_filter(self, authenticated_client, test_project, test_run):
        """levelでフィルタリングできる"""
        log1 = ExecutionLog(run_id=test_run.id, source="NPE", level="INFO", message="Info log")
        log2 = ExecutionLog(run_id=test_run.id, source="NPE", level="ERROR", message="Error log")
        db.session.add_all([log1, log2])
        db.session.commit()

        response = authenticated_client.get(f"/logs/projects/{test_project.id}?level=ERROR")

        assert response.status_code == 200
        assert b"Error log" in response.data

    def test_project_logs_with_pagination(self, authenticated_client, test_project, test_run):
        """ページネーションが動作する"""
        for i in range(60):
            log = ExecutionLog(
                run_id=test_run.id,
                source="NPE",
                level="INFO",
                message=f"Log {i}",
            )
            db.session.add(log)
        db.session.commit()

        response = authenticated_client.get(f"/logs/projects/{test_project.id}?page=1")
        assert response.status_code == 200

        response = authenticated_client.get(f"/logs/projects/{test_project.id}?page=2")
        assert response.status_code == 200

    def test_project_logs_with_per_page_parameter(
        self, authenticated_client, test_project, test_run
    ):
        """per_pageパラメータでページサイズを変更できる"""
        for i in range(20):
            log = ExecutionLog(
                run_id=test_run.id,
                source="NPE",
                level="INFO",
                message=f"Log {i}",
            )
            db.session.add(log)
        db.session.commit()

        response = authenticated_client.get(f"/logs/projects/{test_project.id}?per_page=5")
        assert response.status_code == 200

    def test_project_logs_json_response(
        self, authenticated_client, test_project, test_run, test_execution_log
    ):
        """Accept: application/jsonヘッダーでJSON形式を返す"""
        response = authenticated_client.get(
            f"/logs/projects/{test_project.id}", headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        data = response.json
        assert "logs" in data
        assert "pagination" in data
        assert len(data["logs"]) >= 1
        assert data["logs"][0]["message"] == "Test log message"


# ============================================================================
# Tests: GET /logs/runs/<run_id>
# ============================================================================


class TestRunLogs:
    """GET /logs/runs/<run_id> のテスト"""

    def _get_run_logs(self, client, run_id, **kwargs):
        """run_logs エンドポイントにアクセス（依存をmock）"""
        headers = kwargs.pop("headers", {})
        mock_path = "nexuscore.integration.github_pr_comment._collect_run_metrics"
        mock_report = "nexuscore.integration.run_report_generator.get_markdown_report_path"
        mock_duration = "nexuscore.webapp.views_projects._compute_run_duration"
        mock_format = "nexuscore.webapp.views_projects._format_duration"
        mock_badge = "nexuscore.webapp.views_projects._render_run_status_badge"

        fake_path = MagicMock()
        fake_path.exists.return_value = False

        with patch(mock_path, return_value={"estimated_cost_jpy": 15.0}), \
             patch(mock_report, return_value=fake_path), \
             patch(mock_duration, return_value=300.0), \
             patch(mock_format, return_value="5 min"), \
             patch(mock_badge, return_value='<span class="status-badge status-success">SUCCESS</span>'):
            return client.get(f"/logs/runs/{run_id}", headers=headers, **kwargs)

    def test_run_logs_without_auth_redirects(self, client, test_project, test_run):
        """認証なしはリダイレクトされる"""
        response = self._get_run_logs(client, test_run.run_id)
        assert response.status_code in [302, 401]

    def test_run_logs_with_auth_returns_html(self, authenticated_client, test_run):
        """認証済みユーザーはRun詳細HTMLを取得できる"""
        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Run:" in response.data
        assert test_run.run_id[:8].encode() in response.data

    def test_run_logs_with_invalid_run_returns_404(self, authenticated_client):
        """存在しないrun_idは404エラー"""
        response = self._get_run_logs(authenticated_client, "invalid-run-id")
        assert response.status_code == 404

    def test_run_logs_only_shows_own_run(self, authenticated_client, test_user):
        """他のユーザーのRunは404エラー"""
        other_user = User(github_id="67890", github_login="otheruser", name="Other")
        db.session.add(other_user)
        db.session.commit()

        other_project = Project(
            owner_id=other_user.id, name="other_project", local_path="/tmp/other"
        )
        db.session.add(other_project)
        db.session.commit()

        other_run = Run(
            project_id=other_project.id,
            run_id="other-run-xyz",
            triggered_by=other_user.id,
            status="SUCCESS",
        )
        db.session.add(other_run)
        db.session.commit()

        response = self._get_run_logs(authenticated_client, other_run.run_id)
        assert response.status_code == 404

    def test_run_logs_displays_self_healing_metrics(self, authenticated_client, test_run):
        """Self-Healingメトリクスが表示される"""
        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Self-Healing Metrics" in response.data
        assert b"Exec Time:" in response.data

    def test_run_logs_displays_execution_logs(
        self, authenticated_client, test_run, test_execution_log
    ):
        """実行ログが表示される"""
        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Test log message" in response.data

    def test_run_logs_with_source_filter(self, authenticated_client, test_run):
        """sourceでフィルタリングできる"""
        log1 = ExecutionLog(run_id=test_run.id, source="NPE", level="INFO", message="NPE log")
        log2 = ExecutionLog(
            run_id=test_run.id, source="ORCHESTRATOR", level="INFO", message="Orchestrator log"
        )
        db.session.add_all([log1, log2])
        db.session.commit()

        response = self._get_run_logs(
            authenticated_client, test_run.run_id, query_string={"source": "NPE"}
        )

        assert response.status_code == 200
        assert b"NPE log" in response.data

    def test_run_logs_with_level_filter(self, authenticated_client, test_run):
        """levelでフィルタリングできる"""
        log1 = ExecutionLog(run_id=test_run.id, source="NPE", level="INFO", message="Info log")
        log2 = ExecutionLog(run_id=test_run.id, source="NPE", level="ERROR", message="Error log")
        db.session.add_all([log1, log2])
        db.session.commit()

        response = self._get_run_logs(
            authenticated_client, test_run.run_id, query_string={"level": "ERROR"}
        )

        assert response.status_code == 200
        assert b"Error log" in response.data

    def test_run_logs_with_pagination(self, authenticated_client, test_run):
        """ページネーションが動作する"""
        for i in range(60):
            log = ExecutionLog(
                run_id=test_run.id,
                source="NPE",
                level="INFO",
                message=f"Log {i}",
            )
            db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(
            authenticated_client, test_run.run_id, query_string={"page": "2"}
        )
        assert response.status_code == 200

    def test_run_logs_json_response(self, authenticated_client, test_run, test_execution_log):
        """Accept: application/jsonヘッダーでJSON形式を返す"""
        response = self._get_run_logs(
            authenticated_client, test_run.run_id, headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        data = response.json
        assert "run" in data
        assert "metrics" in data
        assert "logs" in data
        assert "pagination" in data
        assert data["run"]["run_id"] == test_run.run_id

    def test_run_logs_displays_patch_info(self, authenticated_client, test_run):
        """パッチ情報が表示される"""
        patch = PatchRecord(
            run_id=test_run.id,
            file_path="/test/file.py",
            diff_text="test patch",
        )
        db.session.add(patch)
        db.session.commit()

        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Files Changed" in response.data

    def test_run_logs_displays_cost_estimate(self, authenticated_client, test_run):
        """コスト見積もりが表示される"""
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json={"model": "gpt-4", "cost_est_usd": 0.05},
        )
        db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Cost" in response.data or b"USD" in response.data

    def test_run_logs_displays_duration(self, authenticated_client, test_run):
        """実行時間が表示される"""
        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Exec Time" in response.data

    def test_run_logs_with_retry_count(self, authenticated_client, test_run):
        """リトライ回数が表示される"""
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json={"retry_count": 3, "last_error_class": "rate_limit"},
        )
        db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Retry Count" in response.data

    def test_run_logs_with_model_info(self, authenticated_client, test_run):
        """モデル情報が表示される"""
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json={"model": "claude-3-opus"},
        )
        db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(
            authenticated_client, test_run.run_id, headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        data = response.json
        assert data["metrics"]["model"] == "claude-3-opus"

    def test_run_logs_with_guardian_review(self, authenticated_client, test_run):
        """Guardian Review が表示される"""
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="Guardian check",
            payload_json={
                "guardian_review": {"decision": "approved", "reason": "Changes look safe"},
            },
        )
        db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Guardian Review" in response.data

    def test_run_logs_with_observability_links(self, authenticated_client, test_run):
        """Observabilityリンクが含まれる"""
        response = self._get_run_logs(authenticated_client, test_run.run_id)

        assert response.status_code == 200
        assert b"Observability" in response.data
        assert b"Project Detail" in response.data

    def test_run_logs_json_with_all_metrics(self, authenticated_client, test_run):
        """JSON レスポンスに全メトリクスが含まれる"""
        patch = PatchRecord(
            run_id=test_run.id,
            file_path="/src/main.py",
            diff_text="+1 line",
        )
        db.session.add(patch)

        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="Test",
            payload_json={"retry_count": 2, "last_error_class": "timeout", "model": "gpt-4"},
        )
        db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(
            authenticated_client, test_run.run_id, headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        data = response.json
        assert data["metrics"]["retry_count"] == 2
        assert data["metrics"]["last_error_class"] == "timeout"
        assert data["metrics"]["model"] == "gpt-4"
        assert data["metrics"]["files_changed"] == 1

    def test_run_logs_payload_json_string_handling(self, authenticated_client, test_run):
        """payload_json が文字列の場合も正しく処理される"""
        log = ExecutionLog(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="String payload",
            payload_json='{"retry_count": 5, "model": "test-model"}',
        )
        db.session.add(log)
        db.session.commit()

        response = self._get_run_logs(
            authenticated_client, test_run.run_id, headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        data = response.json
        assert data["metrics"]["retry_count"] == 5
        assert data["metrics"]["model"] == "test-model"
