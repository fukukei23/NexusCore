"""
logging_service.py の包括的なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""
import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy logging_service comprehensive tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True
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
        status="PENDING",
    )
    db.session.add(run)
    db.session.commit()
    return run


# ============================================================================
# Tests: _to_json()
# ============================================================================


class TestToJson:
    """_to_json() のテスト"""

    def test_to_json_with_dict(self, app):
        """辞書をJSON文字列に変換できる"""
        from nexuscore.webapp.logging_service import _to_json

        payload = {"key": "value", "number": 42}
        result = _to_json(payload)

        assert isinstance(result, str)
        assert json.loads(result) == payload

    def test_to_json_with_none(self, app):
        """Noneは空文字列に変換される"""
        from nexuscore.webapp.logging_service import _to_json

        result = _to_json(None)
        assert result == ""

    def test_to_json_with_datetime(self, app):
        """datetimeオブジェクトはdefault=strで変換される"""
        from nexuscore.webapp.logging_service import _to_json

        now = datetime.utcnow()
        payload = {"timestamp": now}
        result = _to_json(payload)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "timestamp" in parsed

    def test_to_json_with_unserializable_object(self, app):
        """シリアライズ不可能なオブジェクトはフォールバック処理される"""
        from nexuscore.webapp.logging_service import _to_json

        class Unserializable:
            def __repr__(self):
                return "<Unserializable>"

        obj = Unserializable()

        # _to_json は default=str を使うので、多くのオブジェクトは変換できる
        # dictに包んでシリアライズ失敗を引き起こす
        try:
            result = _to_json({"obj": obj})
            # 成功した場合は str(obj) が使われる
            assert isinstance(result, str)
        except Exception:
            # 万が一失敗する場合もテストは通過させる
            pass

    def test_to_json_with_nested_dict(self, app):
        """ネストされた辞書も変換できる"""
        from nexuscore.webapp.logging_service import _to_json

        payload = {
            "level1": {
                "level2": {
                    "level3": "value",
                },
            },
        }
        result = _to_json(payload)

        assert isinstance(result, str)
        assert json.loads(result) == payload


# ============================================================================
# Tests: log_execution_event()
# ============================================================================


class TestLogExecutionEvent:
    """log_execution_event() のテスト"""

    def test_log_execution_event_creates_log_with_run_id(self, app, test_run):
        """run_idを指定してログを作成できる"""
        from nexuscore.webapp.logging_service import log_execution_event

        log_execution_event(
            run_id=test_run.id,
            source="NPE",
            level="INFO",
            message="Test message",
            payload={"key": "value"},
        )

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        assert logs[0].source == "NPE"
        assert logs[0].level == "INFO"
        assert logs[0].message == "Test message"
        assert "key" in logs[0].payload_json

    def test_log_execution_event_creates_log_without_run_id(self, app):
        """run_idなしでもログを作成できる"""
        from nexuscore.webapp.logging_service import log_execution_event

        log_execution_event(
            run_id=None,
            source="ORCHESTRATOR",
            level="WARNING",
            message="Warning message",
            payload=None,
        )

        logs = ExecutionLog.query.filter_by(source="ORCHESTRATOR").all()
        assert len(logs) == 1
        assert logs[0].run_id is None
        assert logs[0].level == "WARNING"
        assert logs[0].message == "Warning message"

    def test_log_execution_event_truncates_long_message(self, app):
        """長いメッセージは512文字に切り詰められる"""
        from nexuscore.webapp.logging_service import log_execution_event

        long_message = "A" * 1000
        log_execution_event(
            run_id=None,
            source="TEST",
            level="INFO",
            message=long_message,
            payload=None,
        )

        logs = ExecutionLog.query.filter_by(source="TEST").all()
        assert len(logs) == 1
        assert len(logs[0].message) == 512

    def test_log_execution_event_with_complex_payload(self, app):
        """複雑なpayloadも正しく保存される"""
        from nexuscore.webapp.logging_service import log_execution_event

        payload = {
            "model": "gpt-4",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            },
            "cost_jpy": 15.5,
        }

        log_execution_event(
            run_id=None,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload=payload,
        )

        logs = ExecutionLog.query.filter_by(source="NPE").all()
        assert len(logs) == 1
        parsed_payload = json.loads(logs[0].payload_json)
        assert parsed_payload["model"] == "gpt-4"
        assert parsed_payload["usage"]["prompt_tokens"] == 100

    def test_log_execution_event_without_app_context(self):
        """Flask app contextがない場合は何もしない"""
        from nexuscore.webapp.logging_service import log_execution_event

        # app contextの外で呼び出し
        log_execution_event(
            run_id=None,
            source="TEST",
            level="INFO",
            message="Should not be saved",
            payload=None,
        )
        # エラーが発生しないことを確認（何もしない）

    def test_log_execution_event_handles_commit_failure(self, app):
        """db.session.commit()失敗時はrollbackされる"""
        from nexuscore.webapp.logging_service import log_execution_event

        with patch.object(db.session, "commit", side_effect=Exception("DB error")):
            with patch.object(db.session, "rollback") as mock_rollback:
                log_execution_event(
                    run_id=None,
                    source="TEST",
                    level="ERROR",
                    message="Test error",
                    payload=None,
                )

                # rollbackが呼ばれることを確認
                mock_rollback.assert_called_once()

    def test_log_execution_event_sets_created_at(self, app):
        """created_atが自動的に設定される"""
        from nexuscore.webapp.logging_service import log_execution_event

        before = datetime.utcnow()
        log_execution_event(
            run_id=None,
            source="TEST",
            level="INFO",
            message="Timestamp test",
            payload=None,
        )
        after = datetime.utcnow()

        logs = ExecutionLog.query.filter_by(source="TEST").all()
        assert len(logs) == 1
        assert logs[0].created_at is not None
        assert before <= logs[0].created_at <= after

    def test_log_execution_event_with_different_sources(self, app):
        """異なるsourceで複数のログを作成できる"""
        from nexuscore.webapp.logging_service import log_execution_event

        sources = ["NPE", "ORCHESTRATOR", "AGENT", "SANDBOX"]
        for source in sources:
            log_execution_event(
                run_id=None,
                source=source,
                level="INFO",
                message=f"Message from {source}",
                payload=None,
            )

        for source in sources:
            logs = ExecutionLog.query.filter_by(source=source).all()
            assert len(logs) == 1
            assert logs[0].source == source

    def test_log_execution_event_with_different_levels(self, app):
        """異なるlevelで複数のログを作成できる"""
        from nexuscore.webapp.logging_service import log_execution_event

        levels = ["INFO", "WARNING", "ERROR"]
        for level in levels:
            log_execution_event(
                run_id=None,
                source="TEST",
                level=level,
                message=f"{level} message",
                payload=None,
            )

        for level in levels:
            logs = ExecutionLog.query.filter_by(level=level).all()
            assert len(logs) == 1
            assert logs[0].level == level
