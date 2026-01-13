"""
db_logger.py の包括的なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""
import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy db_logger tests have been removed in CR-FASTAPI-010. "
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
# Tests: enhance_log_transaction()
# ============================================================================


class TestEnhanceLogTransaction:
    """enhance_log_transaction() のテスト"""

    def test_enhance_log_transaction_with_llm_call_event(self, app, test_run):
        """event="llm_call"のログを正しく処理する"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "code_generation",
            "model": "gpt-4",
            "ok": True,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "cost_jpy": 15.5,
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        assert logs[0].source == "NPE"
        assert logs[0].level == "INFO"
        assert "code_generation" in logs[0].message
        assert "gpt-4" in logs[0].message

    def test_enhance_log_transaction_with_llm_call_failure(self, app, test_run):
        """LLM呼び出し失敗時はERRORレベルになる"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "test_generation",
            "model": "gpt-4",
            "ok": False,
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        assert logs[0].level == "ERROR"

    def test_enhance_log_transaction_with_llm_blocked_event(self, app, test_run):
        """event="llm_blocked"のログを正しく処理する"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_blocked",
            "source": "NPE",
            "model": "gpt-4",
            "reason": "Budget exceeded",
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        assert logs[0].level == "WARNING"
        assert "blocked" in logs[0].message.lower()
        assert "Budget exceeded" in logs[0].message

    def test_enhance_log_transaction_with_generic_event(self, app, test_run):
        """一般的なeventのログを処理する"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "custom_event",
            "source": "AGENT",
            "task_type": "refactoring",
            "model": "claude-3",
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        assert logs[0].source == "AGENT"
        assert "refactoring" in logs[0].message
        assert "claude-3" in logs[0].message

    def test_enhance_log_transaction_without_run_id(self, app):
        """run_idがない場合も正しく処理する"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "analysis",
            "model": "gpt-3.5",
            "ok": True,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(source="NPE").all()
        assert len(logs) == 1
        assert logs[0].run_id is None

    def test_enhance_log_transaction_with_usage_data(self, app, test_run):
        """usageデータがpayloadに含まれる"""
        from nexuscore.webapp.db_logger import enhance_log_transaction
        import json

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "code_review",
            "model": "gpt-4",
            "ok": True,
            "usage": {"prompt_tokens": 200, "completion_tokens": 100},
            "cost_jpy": 30.0,
            "estimated_cost": 0.25,
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        payload = json.loads(logs[0].payload_json)
        assert "token_usage" in payload
        assert payload["token_usage"]["prompt_tokens"] == 200
        assert "cost_jpy" in payload
        assert payload["cost_jpy"] == 30.0

    def test_enhance_log_transaction_with_minimal_data(self, app):
        """最小限のデータでも処理できる"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "source": "TEST",
            "level": "INFO",
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(source="TEST").all()
        assert len(logs) == 1
        assert logs[0].level == "INFO"

    def test_enhance_log_transaction_handles_import_error(self, app):
        """logging_service.log_execution_eventのimportエラーを処理する"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        # enhance_log_transaction内でimportエラーが発生した場合の処理をテスト
        # 実装上、try-exceptで握りつぶされるため、例外は発生しない
        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "test",
            "model": "gpt-4",
        }
        # エラーが発生しないことを確認（正常に実行される）
        enhance_log_transaction(log_data)
        # ログが作成されたことを確認
        logs = ExecutionLog.query.filter_by(source="NPE").all()
        assert len(logs) >= 1

    def test_enhance_log_transaction_without_task_type_and_model(self, app, test_run):
        """task_typeとmodelがない場合はフォールバックメッセージを使用"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "ok": True,
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        # task_typeとmodelがない場合のメッセージ
        assert "LLM call" in logs[0].message or "NPE transaction" in logs[0].message

    def test_enhance_log_transaction_with_log_file_parameter(self, app, test_run):
        """log_fileパラメータがあっても処理できる（互換性のため）"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "test",
            "model": "gpt-4",
            "ok": True,
            "run_id": test_run.id,
        }

        # log_fileパラメータを渡しても動作する
        enhance_log_transaction(log_data, log_file="/tmp/test.log")

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1

    def test_enhance_log_transaction_with_empty_payload(self, app, test_run):
        """payloadが空の場合はlog_data全体を使用"""
        from nexuscore.webapp.db_logger import enhance_log_transaction
        import json

        log_data = {
            "event": "custom",
            "source": "TEST",
            "level": "INFO",
            "custom_field": "custom_value",
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        payload = json.loads(logs[0].payload_json)
        # payloadが空の場合はlog_data全体がpayloadになる
        assert "custom_field" in payload or "event" in payload

    def test_enhance_log_transaction_multiple_calls(self, app, test_run):
        """複数回呼び出してもすべてログが保存される"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        for i in range(5):
            log_data = {
                "event": "llm_call",
                "source": "NPE",
                "task_type": f"task_{i}",
                "model": "gpt-4",
                "ok": True,
                "run_id": test_run.id,
            }
            enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 5

    def test_enhance_log_transaction_with_default_source(self, app, test_run):
        """sourceが指定されていない場合はデフォルト値"NPE"を使用"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "task_type": "test",
            "model": "gpt-4",
            "ok": True,
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        assert logs[0].source == "NPE"

    def test_enhance_log_transaction_with_default_level(self, app, test_run):
        """levelが指定されていない場合はデフォルト値"INFO"を使用"""
        from nexuscore.webapp.db_logger import enhance_log_transaction

        log_data = {
            "event": "llm_call",
            "source": "NPE",
            "task_type": "test",
            "model": "gpt-4",
            "ok": True,
            "run_id": test_run.id,
        }

        enhance_log_transaction(log_data)

        logs = ExecutionLog.query.filter_by(run_id=test_run.id).all()
        assert len(logs) == 1
        # ok=TrueなのでINFOレベル
        assert logs[0].level == "INFO"
