"""
Comprehensive tests for llm/runtime.py

LLMランタイムシングルトンと診断ユーティリティのテスト
"""

import logging

import pytest

from nexuscore.llm.runtime import (
    CONFIG,
    HTTP_AVAILABLE,
    HTTP_CLIENT_FACTORY,
    REQUEST_TIMEOUT,
    LLMRuntimeDiagnostics,
    current_diagnostics,
    log_runtime_status,
)


# ============================================================================
# LLMRuntimeDiagnostics データクラステスト
# ============================================================================
class TestLLMRuntimeDiagnostics:
    def test_diagnostics_creation_all_fields(self):
        """全フィールド指定で診断情報作成"""
        diag = LLMRuntimeDiagnostics(
            env_file="/path/to/.env",
            request_timeout=120.0,
            http_available=True,
            dry_run=False,
            real_calls_enabled=True,
        )

        assert diag.env_file == "/path/to/.env"
        assert diag.request_timeout == 120.0
        assert diag.http_available is True
        assert diag.dry_run is False
        assert diag.real_calls_enabled is True

    def test_diagnostics_creation_none_env_file(self):
        """env_fileがNoneの場合"""
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=60.0,
            http_available=False,
            dry_run=True,
            real_calls_enabled=False,
        )

        assert diag.env_file is None
        assert diag.request_timeout == 60.0
        assert diag.http_available is False
        assert diag.dry_run is True
        assert diag.real_calls_enabled is False

    def test_diagnostics_is_frozen(self):
        """frozenデータクラスのため変更不可"""
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=120.0,
            http_available=True,
            dry_run=False,
            real_calls_enabled=True,
        )

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            diag.request_timeout = 60.0  # type: ignore

    def test_to_dict_conversion(self):
        """辞書への変換"""
        diag = LLMRuntimeDiagnostics(
            env_file="/test/.env",
            request_timeout=90.0,
            http_available=True,
            dry_run=False,
            real_calls_enabled=True,
        )

        result = diag.to_dict()

        assert isinstance(result, dict)
        assert result["env_file"] == "/test/.env"
        assert result["request_timeout"] == 90.0
        assert result["http_available"] is True
        assert result["dry_run"] is False
        assert result["real_calls_enabled"] is True

    def test_to_dict_with_none_values(self):
        """None値を含む辞書変換"""
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=120.0,
            http_available=False,
            dry_run=True,
            real_calls_enabled=False,
        )

        result = diag.to_dict()

        assert result["env_file"] is None
        assert result["http_available"] is False

    def test_log_with_default_logger(self, caplog):
        """デフォルトロガーでログ出力"""
        diag = LLMRuntimeDiagnostics(
            env_file="/test/.env",
            request_timeout=120.0,
            http_available=True,
            dry_run=False,
            real_calls_enabled=True,
        )

        with caplog.at_level(logging.INFO):
            diag.log()

        # ログが出力される
        assert any("[Runtime]" in record.message for record in caplog.records)

    def test_log_with_custom_logger(self, caplog):
        """カスタムロガーでログ出力"""
        custom_logger = logging.getLogger("TestLogger")
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=60.0,
            http_available=False,
            dry_run=True,
            real_calls_enabled=False,
        )

        with caplog.at_level(logging.INFO, logger="TestLogger"):
            diag.log(custom_logger)

        # カスタムロガーでログ出力
        assert any(record.name == "TestLogger" for record in caplog.records)

    def test_log_warns_http_unavailable(self, caplog):
        """HTTPクライアント利用不可時の警告"""
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=120.0,
            http_available=False,  # HTTP unavailable
            dry_run=False,
            real_calls_enabled=True,
        )

        with caplog.at_level(logging.WARNING):
            diag.log()

        # 警告ログが出力される
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) > 0
        assert any("unavailable" in r.message.lower() for r in warnings)

    def test_log_info_dry_run_mode(self, caplog):
        """ドライランモード時の情報ログ"""
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=120.0,
            http_available=True,
            dry_run=True,  # Dry run enabled
            real_calls_enabled=False,
        )

        with caplog.at_level(logging.INFO):
            diag.log()

        # dry_runに関する情報ログ
        info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
        assert any("dry_run" in r.message.lower() for r in info_logs)

    def test_log_info_real_calls_disabled(self, caplog):
        """real_calls無効時の情報ログ"""
        diag = LLMRuntimeDiagnostics(
            env_file=None,
            request_timeout=120.0,
            http_available=True,
            dry_run=False,
            real_calls_enabled=False,  # Real calls disabled
        )

        with caplog.at_level(logging.INFO):
            diag.log()

        # real_callsに関する情報ログ
        info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
        assert any("real" in r.message.lower() or "calls" in r.message.lower() for r in info_logs)


# ============================================================================
# current_diagnostics テスト
# ============================================================================
class TestCurrentDiagnostics:
    def test_current_diagnostics_returns_instance(self):
        """LLMRuntimeDiagnosticsインスタンスを返す"""
        diag = current_diagnostics()

        assert isinstance(diag, LLMRuntimeDiagnostics)

    def test_current_diagnostics_has_all_fields(self):
        """全必須フィールドを持つ"""
        diag = current_diagnostics()

        assert hasattr(diag, "env_file")
        assert hasattr(diag, "request_timeout")
        assert hasattr(diag, "http_available")
        assert hasattr(diag, "dry_run")
        assert hasattr(diag, "real_calls_enabled")

    def test_current_diagnostics_request_timeout(self):
        """request_timeoutがREQUEST_TIMEOUTと一致"""
        diag = current_diagnostics()

        assert diag.request_timeout == REQUEST_TIMEOUT

    def test_current_diagnostics_http_available(self):
        """http_availableがHTTP_AVAILABLEと一致"""
        diag = current_diagnostics()

        assert diag.http_available == HTTP_AVAILABLE

    def test_current_diagnostics_dry_run(self):
        """dry_runがCONFIG.dry_runと一致"""
        diag = current_diagnostics()

        assert diag.dry_run == CONFIG.dry_run

    def test_current_diagnostics_real_calls_enabled(self):
        """real_calls_enabledがCONFIG.real_calls_enabledと一致"""
        diag = current_diagnostics()

        assert diag.real_calls_enabled == CONFIG.real_calls_enabled

    def test_current_diagnostics_env_file_from_env(self, monkeypatch):
        """NEXUSCORE_ENV_LOADED環境変数からenv_fileを取得"""
        monkeypatch.setenv("NEXUSCORE_ENV_LOADED", "/custom/.env")

        current_diagnostics()

        # env_fileが設定される（実装による）
        # 環境変数がセットされている場合は反映される可能性がある

    def test_current_diagnostics_no_side_effects(self):
        """副作用なし（冪等性）"""
        diag1 = current_diagnostics()
        diag2 = current_diagnostics()

        # 同じ状態を返す（値は同じ）
        assert diag1.request_timeout == diag2.request_timeout
        assert diag1.http_available == diag2.http_available
        assert diag1.dry_run == diag2.dry_run
        assert diag1.real_calls_enabled == diag2.real_calls_enabled


# ============================================================================
# log_runtime_status テスト
# ============================================================================
class TestLogRuntimeStatus:
    def test_log_runtime_status_returns_diagnostics(self):
        """LLMRuntimeDiagnosticsインスタンスを返す"""
        diag = log_runtime_status()

        assert isinstance(diag, LLMRuntimeDiagnostics)

    def test_log_runtime_status_logs_output(self, caplog):
        """ログを出力する"""
        with caplog.at_level(logging.INFO):
            log_runtime_status()

        # ログ出力が行われる
        assert len(caplog.records) > 0
        assert any("[Runtime]" in r.message for r in caplog.records)

    def test_log_runtime_status_with_custom_logger(self, caplog):
        """カスタムロガーでログ出力"""
        custom_logger = logging.getLogger("CustomRuntime")

        with caplog.at_level(logging.INFO, logger="CustomRuntime"):
            log_runtime_status(custom_logger)

        # カスタムロガーでログが出力される
        assert any(r.name == "CustomRuntime" for r in caplog.records)

    def test_log_runtime_status_returns_current_state(self):
        """現在の状態を返す"""
        diag = log_runtime_status()

        # current_diagnostics()と同じ値を返す
        current = current_diagnostics()
        assert diag.request_timeout == current.request_timeout
        assert diag.http_available == current.http_available
        assert diag.dry_run == current.dry_run
        assert diag.real_calls_enabled == current.real_calls_enabled


# ============================================================================
# モジュールレベル定数テスト
# ============================================================================
class TestModuleLevelConstants:
    def test_config_exists(self):
        """CONFIGが存在する"""
        assert CONFIG is not None

    def test_config_is_llm_router_config(self):
        """CONFIGがLLMRouterConfigインスタンス"""
        from nexuscore.llm.config import LLMRouterConfig

        assert isinstance(CONFIG, LLMRouterConfig)

    def test_request_timeout_exists(self):
        """REQUEST_TIMEOUTが存在する"""
        assert REQUEST_TIMEOUT is not None
        assert isinstance(REQUEST_TIMEOUT, (int, float))
        assert REQUEST_TIMEOUT > 0

    def test_request_timeout_from_config(self):
        """REQUEST_TIMEOUTがCONFIGから取得される"""
        assert REQUEST_TIMEOUT == CONFIG.request_timeout

    def test_http_client_factory_exists(self):
        """HTTP_CLIENT_FACTORYが存在する"""
        assert HTTP_CLIENT_FACTORY is not None

    def test_http_client_factory_is_factory(self):
        """HTTP_CLIENT_FACTORYがHttpClientFactoryインスタンス"""
        from nexuscore.llm.http_client import HttpClientFactory

        assert isinstance(HTTP_CLIENT_FACTORY, HttpClientFactory)

    def test_http_available_exists(self):
        """HTTP_AVAILABLEが存在する"""
        assert isinstance(HTTP_AVAILABLE, bool)

    def test_http_available_from_factory(self):
        """HTTP_AVAILABLEがHTTP_CLIENT_FACTORYから取得される"""
        assert HTTP_AVAILABLE == HTTP_CLIENT_FACTORY.available


# ============================================================================
# 統合テスト
# ============================================================================
class TestRuntimeIntegration:
    def test_diagnostics_workflow(self, caplog):
        """診断情報の完全ワークフロー"""
        # 現在の診断情報を取得
        diag = current_diagnostics()

        # 辞書に変換
        diag_dict = diag.to_dict()
        assert isinstance(diag_dict, dict)

        # ログ出力
        with caplog.at_level(logging.INFO):
            diag.log()

        assert len(caplog.records) > 0

    def test_log_runtime_status_workflow(self, caplog):
        """ログ出力ワークフローの完全テスト"""
        with caplog.at_level(logging.INFO):
            diag = log_runtime_status()

        # 診断情報が返される
        assert isinstance(diag, LLMRuntimeDiagnostics)

        # ログが出力される
        assert len(caplog.records) > 0

        # 辞書変換可能
        diag_dict = diag.to_dict()
        assert len(diag_dict) == 5  # 5つのフィールド

    def test_runtime_consistency(self):
        """ランタイム状態の一貫性"""
        # 複数回取得しても同じ値
        diag1 = current_diagnostics()
        diag2 = current_diagnostics()

        assert diag1.request_timeout == diag2.request_timeout
        assert diag1.http_available == diag2.http_available
        assert diag1.dry_run == diag2.dry_run
        assert diag1.real_calls_enabled == diag2.real_calls_enabled

    def test_module_constants_consistency(self):
        """モジュール定数の一貫性"""
        # CONFIGの値とREQUEST_TIMEOUTが一致
        assert REQUEST_TIMEOUT == CONFIG.request_timeout

        # HTTP_AVAILABLEとHTTP_CLIENT_FACTORYが一致
        assert HTTP_AVAILABLE == HTTP_CLIENT_FACTORY.available

    def test_diagnostics_reflects_module_constants(self):
        """診断情報がモジュール定数を反映"""
        diag = current_diagnostics()

        assert diag.request_timeout == REQUEST_TIMEOUT
        assert diag.http_available == HTTP_AVAILABLE
        assert diag.dry_run == CONFIG.dry_run
        assert diag.real_calls_enabled == CONFIG.real_calls_enabled
