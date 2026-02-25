# ruff: noqa: F821
"""
webapp/orchestrator_inline.py の高品質なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy orchestrator_inline tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True,
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
def db_session(app):
    """Database session for tests"""
    from nexuscore.webapp import db

    with app.app_context():
        yield db.session


@pytest.fixture
def test_data(db_session):
    """テストデータを作成"""
    user = User(github_id="12345", github_login="testuser")
    db_session.add(user)
    db_session.commit()

    project = Project(
        owner_id=user.id,
        name="Test Project",
        local_path="/tmp/test-project",
    )
    db_session.add(project)
    db_session.commit()

    run = Run(
        project_id=project.id,
        run_id="test-run-123",
        status="PENDING",
    )
    db_session.add(run)
    db_session.commit()

    return {"user": user, "project": project, "run": run}


class TestRunOrchestratorInline:
    """run_orchestrator_inline() のテスト"""

    def test_run_orchestrator_inline_sets_run_to_running(self, app, db_session, test_data):
        """run_orchestrator_inline() が Run を RUNNING にする"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync"):
            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

        # Run が RUNNING になり started_at が設定される
        db_session.refresh(run)
        # 実行前に RUNNING、実行後に SUCCESS
        assert run.status == "SUCCESS"
        assert run.started_at is not None

    def test_run_orchestrator_inline_calls_run_orchestrator_sync(self, app, db_session, test_data):
        """run_orchestrator_inline() が run_orchestrator_sync を呼ぶ"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix all bugs",
                    autonomy_level=2,
                    fast_lane=True,
                )

                # run_orchestrator_sync が正しいパラメータで呼ばれる
                mock_sync.assert_called_once_with(
                    project_path="/tmp/test-project",
                    user_requirement="Fix all bugs",
                    run_db_id=run.id,
                    autonomy_level=2,
                    language="ja",
                    fast_lane=True,
                )

    def test_run_orchestrator_inline_sets_run_to_success_on_completion(
        self, app, db_session, test_data
    ):
        """run_orchestrator_inline() が成功時に Run を SUCCESS にする"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync"):
            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

        db_session.refresh(run)
        assert run.status == "SUCCESS"
        assert run.finished_at is not None

    def test_run_orchestrator_inline_sets_run_to_failed_on_error(self, app, db_session, test_data):
        """run_orchestrator_inline() がエラー時に Run を FAILED にする"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            mock_sync.side_effect = Exception("Orchestrator error")

            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                with pytest.raises(Exception, match="Orchestrator error"):
                    run_orchestrator_inline(
                        run=run,
                        project=project,
                        requirement="Fix bugs",
                    )

        db_session.refresh(run)
        assert run.status == "FAILED"
        assert run.finished_at is not None

    def test_run_orchestrator_inline_sets_finished_at_in_finally_block(
        self, app, db_session, test_data
    ):
        """run_orchestrator_inline() が finally ブロックで finished_at を設定"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            mock_sync.side_effect = Exception("Error")

            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                try:
                    run_orchestrator_inline(
                        run=run,
                        project=project,
                        requirement="Fix bugs",
                    )
                except Exception:
                    pass

        # エラーが発生しても finished_at は設定される
        db_session.refresh(run)
        assert run.finished_at is not None

    def test_run_orchestrator_inline_sends_slack_notification_on_success(
        self, app, db_session, test_data
    ):
        """run_orchestrator_inline() が成功時に Slack 通知を送信"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        mock_notifier = Mock()

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync"):
            with patch("nexuscore.core.notifier.get_notifier", return_value=mock_notifier):
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

                # Slack 通知が送信される
                mock_notifier.notify_orchestrator_complete.assert_called_once()
                call_kwargs = mock_notifier.notify_orchestrator_complete.call_args[1]
                assert call_kwargs["project_path"] == "/tmp/test-project"
                assert call_kwargs["requirement"] == "Fix bugs"
                assert call_kwargs["status"] == "success"
                assert call_kwargs["session_id"] == "test-run-123"

    def test_run_orchestrator_inline_sends_slack_notification_on_failure(
        self, app, db_session, test_data
    ):
        """run_orchestrator_inline() が失敗時に Slack 通知を送信"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        mock_notifier = Mock()

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            mock_sync.side_effect = Exception("Orchestrator error")

            with patch("nexuscore.core.notifier.get_notifier", return_value=mock_notifier):
                with pytest.raises(Exception):  # noqa: B017
                    run_orchestrator_inline(
                        run=run,
                        project=project,
                        requirement="Fix bugs",
                    )

                # Slack 通知が送信される（status=error）
                mock_notifier.notify_orchestrator_complete.assert_called_once()
                call_kwargs = mock_notifier.notify_orchestrator_complete.call_args[1]
                assert call_kwargs["status"] == "error"

    def test_run_orchestrator_inline_handles_notification_error(self, app, db_session, test_data):
        """run_orchestrator_inline() が通知エラーを処理"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        mock_notifier = Mock()
        mock_notifier.notify_orchestrator_complete.side_effect = Exception("Notification error")

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync"):
            with patch("nexuscore.core.notifier.get_notifier", return_value=mock_notifier):
                # 通知エラーがあっても本処理は成功
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

        db_session.refresh(run)
        # Run は SUCCESS のまま
        assert run.status == "SUCCESS"

    def test_run_orchestrator_inline_works_without_notifier(self, app, db_session, test_data):
        """run_orchestrator_inline() が Notifier なしでも動作"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync"):
            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                # Notifier が None でも正常に動作
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

        db_session.refresh(run)
        assert run.status == "SUCCESS"

    def test_run_orchestrator_inline_uses_default_autonomy_level(self, app, db_session, test_data):
        """run_orchestrator_inline() がデフォルトの autonomy_level=1 を使用"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

                # autonomy_level=1 で呼ばれる
                call_kwargs = mock_sync.call_args[1]
                assert call_kwargs["autonomy_level"] == 1

    def test_run_orchestrator_inline_uses_default_fast_lane(self, app, db_session, test_data):
        """run_orchestrator_inline() がデフォルトの fast_lane=False を使用"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                run_orchestrator_inline(
                    run=run,
                    project=project,
                    requirement="Fix bugs",
                )

                # fast_lane=False で呼ばれる
                call_kwargs = mock_sync.call_args[1]
                assert call_kwargs["fast_lane"] is False

    def test_run_orchestrator_inline_propagates_exception_after_cleanup(
        self, app, db_session, test_data
    ):
        """run_orchestrator_inline() がクリーンアップ後にエラーを伝播"""
        from nexuscore.webapp.orchestrator_inline import run_orchestrator_inline

        run = test_data["run"]
        project = test_data["project"]

        with patch("nexuscore.webapp.orchestrator_inline.run_orchestrator_sync") as mock_sync:
            mock_sync.side_effect = Exception("Test error")

            with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                # エラーが伝播される
                with pytest.raises(Exception, match="Test error"):
                    run_orchestrator_inline(
                        run=run,
                        project=project,
                        requirement="Fix bugs",
                    )

                # クリーンアップ（finished_at 設定）が完了している
                db_session.refresh(run)
                assert run.finished_at is not None
                assert run.status == "FAILED"
