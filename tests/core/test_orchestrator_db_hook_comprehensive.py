"""
============================================================================
Comprehensive Tests for orchestrator_db_hook.py
============================================================================
高品質テストの原則:
- 外部依存（webapp logging_service）をモック
- Webappがない環境でも安全に動作することをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Optional


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_webapp_module():
    """各テスト前後でwebappモジュールをリセット"""
    # テスト前の状態を保存
    webapp_module = sys.modules.get('nexuscore.webapp')
    logging_service_module = sys.modules.get('nexuscore.webapp.logging_service')

    yield

    # テスト後に復元
    if 'nexuscore.core.orchestrator_db_hook' in sys.modules:
        del sys.modules['nexuscore.core.orchestrator_db_hook']

    if webapp_module is not None:
        sys.modules['nexuscore.webapp'] = webapp_module
    else:
        sys.modules.pop('nexuscore.webapp', None)

    if logging_service_module is not None:
        sys.modules['nexuscore.webapp.logging_service'] = logging_service_module
    else:
        sys.modules.pop('nexuscore.webapp.logging_service', None)


# ============================================================================
# Tests: log_orchestrator_event with webapp available
# ============================================================================


class TestLogOrchestratorEventWithWebapp:
    def test_log_event_with_all_parameters(self):
        """全てのパラメータを指定してログイベントを記録"""
        # webapp モジュールをモック
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        # モジュールを再インポート
        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=123,
            phase="planning",
            status="SUCCESS",
            message="Planning completed",
            extra={"duration": 5.2, "files": 10}
        )

        mock_log_func.assert_called_once()
        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["run_id"] == 123
        assert call_kwargs["source"] == "ORCHESTRATOR"
        assert call_kwargs["level"] == "INFO"
        assert call_kwargs["message"] == "Planning completed"
        assert call_kwargs["payload"]["phase"] == "planning"
        assert call_kwargs["payload"]["status"] == "SUCCESS"
        assert call_kwargs["payload"]["duration"] == 5.2
        assert call_kwargs["payload"]["files"] == 10

    def test_log_event_failed_status(self):
        """FAILEDステータスでERRORレベルになる"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=123,
            phase="coding",
            status="FAILED",
            message="Coding failed"
        )

        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["level"] == "ERROR"

    def test_log_event_error_status(self):
        """errorステータス（小文字）でERRORレベルになる"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=123,
            phase="testing",
            status="error",
            message="Test error"
        )

        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["level"] == "ERROR"

    def test_log_event_without_extra(self):
        """extraなしでログイベントを記録"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=123,
            phase="startup",
            status="STARTED",
            message="Orchestrator started"
        )

        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["payload"]["phase"] == "startup"
        assert call_kwargs["payload"]["status"] == "STARTED"
        assert "duration" not in call_kwargs["payload"]

    def test_log_event_with_none_run_id(self):
        """run_db_id=Noneでも動作する"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=None,
            phase="review",
            status="SUCCESS",
            message="Review completed"
        )

        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["run_id"] is None

    def test_log_event_with_empty_extra(self):
        """空のextraディクショナリ"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=123,
            phase="shutdown",
            status="FINISHED",
            message="Orchestrator shutdown",
            extra={}
        )

        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["payload"]["phase"] == "shutdown"
        assert call_kwargs["payload"]["status"] == "FINISHED"

    def test_log_event_multiple_phases(self):
        """複数のフェーズでログイベントを記録"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        phases = ["startup", "requirement", "planning", "coding", "testing", "review", "shutdown"]

        for phase in phases:
            log_orchestrator_event(
                run_db_id=123,
                phase=phase,
                status="SUCCESS",
                message=f"{phase} completed"
            )

        assert mock_log_func.call_count == len(phases)

        # 各フェーズが正しく記録されているか確認
        for i, phase in enumerate(phases):
            call_kwargs = mock_log_func.call_args_list[i][1]
            assert call_kwargs["payload"]["phase"] == phase

    def test_log_event_with_complex_extra(self):
        """複雑なextraデータ"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        complex_extra = {
            "duration": 10.5,
            "files_changed": 25,
            "tests_run": 150,
            "coverage": 85.5,
            "metadata": {
                "agent": "guardian",
                "version": "1.0.0"
            },
            "errors": ["error1", "error2"]
        }

        log_orchestrator_event(
            run_db_id=123,
            phase="testing",
            status="SUCCESS",
            message="Testing completed",
            extra=complex_extra
        )

        call_kwargs = mock_log_func.call_args[1]
        assert call_kwargs["payload"]["duration"] == 10.5
        assert call_kwargs["payload"]["metadata"]["agent"] == "guardian"
        assert call_kwargs["payload"]["errors"] == ["error1", "error2"]


# ============================================================================
# Tests: log_orchestrator_event without webapp (CLI mode)
# ============================================================================


class TestLogOrchestratorEventWithoutWebapp:
    def test_log_event_without_webapp_module(self):
        """webappモジュールがない場合は何もしない"""
        # webappモジュールを削除
        sys.modules.pop('nexuscore.webapp', None)
        sys.modules.pop('nexuscore.webapp.logging_service', None)

        # モジュールを再インポート
        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        # 例外が発生しないことを確認
        log_orchestrator_event(
            run_db_id=123,
            phase="planning",
            status="SUCCESS",
            message="Planning completed"
        )

    def test_log_event_with_import_error(self):
        """webappのインポートがImportErrorの場合"""
        # ImportErrorをシミュレート
        sys.modules.pop('nexuscore.webapp', None)
        sys.modules.pop('nexuscore.webapp.logging_service', None)

        # モジュールを再インポート
        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        # 例外が発生しないことを確認
        log_orchestrator_event(
            run_db_id=None,
            phase="startup",
            status="STARTED",
            message="Orchestrator started in CLI mode"
        )

    def test_log_event_cli_mode_multiple_calls(self):
        """CLI モードで複数回呼び出しても安全"""
        sys.modules.pop('nexuscore.webapp', None)
        sys.modules.pop('nexuscore.webapp.logging_service', None)

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        # 複数回呼び出しても例外が発生しない
        for i in range(10):
            log_orchestrator_event(
                run_db_id=None,
                phase=f"phase{i}",
                status="SUCCESS",
                message=f"Phase {i} completed"
            )


# ============================================================================
# Tests: Status level mapping
# ============================================================================


class TestStatusLevelMapping:
    def test_status_to_level_mapping(self):
        """ステータスからログレベルへのマッピング"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        # ERROR レベルになるステータス
        error_statuses = ["FAILED", "ERROR", "failed", "error", "Failed", "Error"]

        for status in error_statuses:
            mock_log_func.reset_mock()
            log_orchestrator_event(
                run_db_id=123,
                phase="test",
                status=status,
                message=f"Status: {status}"
            )

            call_kwargs = mock_log_func.call_args[1]
            assert call_kwargs["level"] == "ERROR", f"Status {status} should map to ERROR level"

        # INFO レベルになるステータス
        info_statuses = ["SUCCESS", "STARTED", "FINISHED", "RUNNING", "success", "started"]

        for status in info_statuses:
            mock_log_func.reset_mock()
            log_orchestrator_event(
                run_db_id=123,
                phase="test",
                status=status,
                message=f"Status: {status}"
            )

            call_kwargs = mock_log_func.call_args[1]
            assert call_kwargs["level"] == "INFO", f"Status {status} should map to INFO level"


# ============================================================================
# Tests: Payload construction
# ============================================================================


class TestPayloadConstruction:
    def test_payload_always_includes_phase_and_status(self):
        """payloadには常にphaseとstatusが含まれる"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        log_orchestrator_event(
            run_db_id=123,
            phase="coding",
            status="RUNNING",
            message="Coding in progress"
        )

        call_kwargs = mock_log_func.call_args[1]
        payload = call_kwargs["payload"]

        assert "phase" in payload
        assert "status" in payload
        assert payload["phase"] == "coding"
        assert payload["status"] == "RUNNING"

    def test_payload_merges_extra_correctly(self):
        """extraがpayloadに正しくマージされる"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        extra = {
            "custom_field": "value",
            "count": 42,
            "nested": {"key": "value"}
        }

        log_orchestrator_event(
            run_db_id=123,
            phase="review",
            status="SUCCESS",
            message="Review completed",
            extra=extra
        )

        call_kwargs = mock_log_func.call_args[1]
        payload = call_kwargs["payload"]

        assert payload["phase"] == "review"
        assert payload["status"] == "SUCCESS"
        assert payload["custom_field"] == "value"
        assert payload["count"] == 42
        assert payload["nested"]["key"] == "value"

    def test_payload_extra_does_not_overwrite_phase_status(self):
        """extraがphaseやstatusを上書きできるか確認"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        # extraでphaseとstatusを上書きしようとする
        extra = {
            "phase": "fake_phase",
            "status": "fake_status",
            "other": "value"
        }

        log_orchestrator_event(
            run_db_id=123,
            phase="real_phase",
            status="REAL_STATUS",
            message="Test",
            extra=extra
        )

        call_kwargs = mock_log_func.call_args[1]
        payload = call_kwargs["payload"]

        # extraで上書きされている（update()の動作）
        assert payload["phase"] == "fake_phase"
        assert payload["status"] == "fake_status"
        assert payload["other"] == "value"


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_orchestrator_lifecycle(self):
        """Orchestratorの完全なライフサイクル"""
        mock_log_func = MagicMock()
        mock_webapp = MagicMock()
        mock_webapp.logging_service.log_execution_event = mock_log_func

        sys.modules['nexuscore.webapp'] = mock_webapp
        sys.modules['nexuscore.webapp.logging_service'] = mock_webapp.logging_service

        from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

        run_id = 123

        # Startup
        log_orchestrator_event(
            run_db_id=run_id,
            phase="startup",
            status="STARTED",
            message="Orchestrator started"
        )

        # Requirement
        log_orchestrator_event(
            run_db_id=run_id,
            phase="requirement",
            status="SUCCESS",
            message="Requirements analyzed",
            extra={"requirement_count": 5}
        )

        # Planning
        log_orchestrator_event(
            run_db_id=run_id,
            phase="planning",
            status="SUCCESS",
            message="Plan created",
            extra={"steps": 10}
        )

        # Coding
        log_orchestrator_event(
            run_db_id=run_id,
            phase="coding",
            status="SUCCESS",
            message="Code generated",
            extra={"files": 15}
        )

        # Testing (failed)
        log_orchestrator_event(
            run_db_id=run_id,
            phase="testing",
            status="FAILED",
            message="Tests failed",
            extra={"failures": 3}
        )

        # Shutdown
        log_orchestrator_event(
            run_db_id=run_id,
            phase="shutdown",
            status="FINISHED",
            message="Orchestrator finished"
        )

        # 6回呼ばれているはず
        assert mock_log_func.call_count == 6

        # 各ログエントリの確認
        calls = mock_log_func.call_args_list

        assert calls[0][1]["payload"]["phase"] == "startup"
        assert calls[1][1]["payload"]["phase"] == "requirement"
        assert calls[2][1]["payload"]["phase"] == "planning"
        assert calls[3][1]["payload"]["phase"] == "coding"
        assert calls[4][1]["payload"]["phase"] == "testing"
        assert calls[4][1]["level"] == "ERROR"  # FAILED -> ERROR level
        assert calls[5][1]["payload"]["phase"] == "shutdown"
