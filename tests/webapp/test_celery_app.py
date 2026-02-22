"""
webapp/celery_app.py の高品質なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy celery_app tests have been removed in CR-FASTAPI-010. "
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

    # Celery の自動初期化をスキップ
    with patch.dict("os.environ", {"SKIP_CELERY_AUTO_INIT": "1"}):
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


class TestMakeCelery:
    """make_celery() のテスト"""

    def test_make_celery_creates_celery_instance(self, app):
        """make_celery() が Celery インスタンスを作成する"""
        # celery_app モジュールをリロードして celery グローバル変数をクリア
        import nexuscore.webapp.celery_app as celery_module

        celery_module.celery = None

        with patch.dict(
            "os.environ",
            {
                "CELERY_BROKER_URL": "redis://localhost:6379/0",
                "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
            },
        ):
            celery_instance = celery_module.make_celery(app)

            assert celery_instance is not None
            assert celery_instance.main == app.import_name

    def test_make_celery_returns_existing_instance(self, app):
        """make_celery() が既存のインスタンスを返す"""
        import nexuscore.webapp.celery_app as celery_module

        # 最初の呼び出し
        celery_module.celery = None
        celery1 = celery_module.make_celery(app)

        # 2回目の呼び出し
        celery2 = celery_module.make_celery(app)

        # 同じインスタンスが返される
        assert celery1 is celery2

    def test_make_celery_registers_tasks(self, app):
        """make_celery() がタスクを登録する"""
        import nexuscore.webapp.celery_app as celery_module

        celery_module.celery = None
        celery_module.run_orchestrator_task = None

        celery_instance = celery_module.make_celery(app)

        # run_orchestrator_task が登録されている
        assert celery_module.run_orchestrator_task is not None

    def test_make_celery_uses_context_task(self, app):
        """make_celery() が Flask アプリコンテキスト内でタスクを実行するカスタムタスククラスを使用する"""
        import nexuscore.webapp.celery_app as celery_module

        celery_module.celery = None

        celery_instance = celery_module.make_celery(app)

        # ContextTask が設定されている
        assert celery_instance.Task.__name__ == "ContextTask"


class TestInitCelery:
    """init_celery() のテスト"""

    def test_init_celery_returns_existing_instance(self):
        """init_celery() が既存のインスタンスを返す"""
        import nexuscore.webapp.celery_app as celery_module

        # 既存の celery を設定
        existing_celery = Mock()
        celery_module.celery = existing_celery

        celery_instance = celery_module.init_celery()

        # 既存のインスタンスが返される
        assert celery_instance is existing_celery


class TestRunOrchestratorTask:
    """run_orchestrator_task のテスト（基本部分のみ）"""

    def test_run_orchestrator_task_is_registered(self, app):
        """run_orchestrator_task が登録されている"""
        import nexuscore.webapp.celery_app as celery_module

        celery_module.celery = None
        celery_module.run_orchestrator_task = None

        celery_module.make_celery(app)

        assert celery_module.run_orchestrator_task is not None
        assert callable(celery_module.run_orchestrator_task)

    def test_run_orchestrator_task_handles_missing_run(self, app, db_session):
        """run_orchestrator_task が存在しない Run を処理する"""
        import nexuscore.webapp.celery_app as celery_module

        celery_module.celery = None

        celery_instance = celery_module.make_celery(app)

        # 存在しない run_db_id を指定
        with patch("nexuscore.webapp.celery_app.Run.query") as mock_query:
            mock_query.get.return_value = None

            # エラーを投げずに終了する
            try:
                celery_module.run_orchestrator_task(99999)
                # エラーが発生しない
            except Exception as e:
                pytest.fail(f"Unexpected exception: {e}")

    def test_run_orchestrator_task_handles_empty_requirement(self, app, db_session):
        """run_orchestrator_task が空の requirement を処理する"""
        import nexuscore.webapp.celery_app as celery_module
        from nexuscore.webapp.models import Project, Run, User

        celery_module.celery = None
        celery_module.make_celery(app)

        # テストデータを作成
        user = User(github_id="12345", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(owner_id=user.id, name="Test", local_path="/tmp/test")
        db_session.add(project)
        db_session.commit()

        run = Run(
            project_id=project.id,
            run_id="test-run",
            status="PENDING",
            requirement="",  # 空の requirement
        )
        db_session.add(run)
        db_session.commit()

        # run_orchestrator_task を呼ぶ
        celery_module.run_orchestrator_task(run.id)

        # Run が FAILED になっている
        db_session.refresh(run)
        assert run.status == "FAILED"
        assert run.finished_at is not None

    def test_run_orchestrator_task_updates_run_status_on_success(self, app, db_session):
        """run_orchestrator_task が成功時に Run ステータスを更新する"""
        import nexuscore.webapp.celery_app as celery_module
        from nexuscore.webapp.models import Project, Run, User

        celery_module.celery = None
        celery_module.make_celery(app)

        # テストデータを作成
        user = User(github_id="12345", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(owner_id=user.id, name="Test", local_path="/tmp/test")
        db_session.add(project)
        db_session.commit()

        run = Run(
            project_id=project.id,
            run_id="test-run",
            status="PENDING",
            requirement="Fix bugs",
        )
        db_session.add(run)
        db_session.commit()

        # run_orchestrator_sync をモック
        with patch("nexuscore.webapp.celery_app.run_orchestrator_sync"):
            # レポート生成をモック
            with patch("nexuscore.integration.run_report_generator.write_run_report_file"):
                # Notifier をモック
                with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                    celery_module.run_orchestrator_task(run.id)

        # Run が SUCCESS になっている
        db_session.refresh(run)
        assert run.status == "SUCCESS"
        assert run.started_at is not None
        assert run.finished_at is not None

    def test_run_orchestrator_task_updates_run_status_on_failure(self, app, db_session):
        """run_orchestrator_task が失敗時に Run ステータスを更新する"""
        import nexuscore.webapp.celery_app as celery_module
        from nexuscore.webapp.models import Project, Run, User

        celery_module.celery = None
        celery_module.make_celery(app)

        # テストデータを作成
        user = User(github_id="12345", github_login="testuser")
        db_session.add(user)
        db_session.commit()

        project = Project(owner_id=user.id, name="Test", local_path="/tmp/test")
        db_session.add(project)
        db_session.commit()

        run = Run(
            project_id=project.id,
            run_id="test-run",
            status="PENDING",
            requirement="Fix bugs",
        )
        db_session.add(run)
        db_session.commit()

        # run_orchestrator_sync がエラーを投げる
        with patch("nexuscore.webapp.celery_app.run_orchestrator_sync") as mock_sync:
            mock_sync.side_effect = Exception("Test error")

            # レポート生成をモック
            with patch("nexuscore.integration.run_report_generator.write_run_report_file"):
                # Notifier をモック
                with patch("nexuscore.core.notifier.get_notifier", return_value=None):
                    celery_module.run_orchestrator_task(run.id)

        # Run が FAILED になっている
        db_session.refresh(run)
        assert run.status == "FAILED"
        assert run.started_at is not None
        assert run.finished_at is not None
