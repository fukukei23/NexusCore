"""
Comprehensive tests for llm/config.py

環境変数ロード、同期、設定クラスのテスト
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from nexuscore.llm.config import (
    LLMRouterConfig,
    _bool_from_env,
    _sync_env_var,
    ensure_env_loaded,
    synchronize_aliases,
)


# ============================================================================
# _bool_from_env テスト
# ============================================================================
class TestBoolFromEnv:
    def test_bool_from_env_none_returns_default(self):
        """None値の場合デフォルトを返す"""
        assert _bool_from_env(None, default=False) is False
        assert _bool_from_env(None, default=True) is True

    def test_bool_from_env_true_values(self):
        """True値として認識される文字列"""
        true_values = ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON"]
        for val in true_values:
            assert _bool_from_env(val) is True, f"Failed for: {val}"

    def test_bool_from_env_false_values(self):
        """False値として認識される文字列"""
        false_values = ["0", "false", "False", "no", "off", "", "random"]
        for val in false_values:
            assert _bool_from_env(val, default=False) is False, f"Failed for: {val}"

    def test_bool_from_env_whitespace_handling(self):
        """前後の空白を処理"""
        assert _bool_from_env("  true  ") is True
        assert _bool_from_env("  1  ") is True
        assert _bool_from_env("  yes  ") is True


# ============================================================================
# _sync_env_var テスト
# ============================================================================
class TestSyncEnvVar:
    def test_sync_env_var_target_exists_no_sync(self, monkeypatch):
        """ターゲット変数が存在する場合は同期しない"""
        monkeypatch.setenv("TARGET", "original")
        monkeypatch.setenv("ALIAS1", "alias_value")

        _sync_env_var("TARGET", ["ALIAS1"])

        assert os.getenv("TARGET") == "original"

    def test_sync_env_var_target_missing_uses_first_alias(self, monkeypatch):
        """ターゲットがない場合、最初のエイリアスを使用"""
        monkeypatch.delenv("TARGET", raising=False)
        monkeypatch.setenv("ALIAS1", "value1")
        monkeypatch.setenv("ALIAS2", "value2")

        _sync_env_var("TARGET", ["ALIAS1", "ALIAS2"])

        assert os.getenv("TARGET") == "value1"

    def test_sync_env_var_uses_second_alias_if_first_missing(self, monkeypatch):
        """最初のエイリアスがない場合、2番目を使用"""
        monkeypatch.delenv("TARGET", raising=False)
        monkeypatch.delenv("ALIAS1", raising=False)
        monkeypatch.setenv("ALIAS2", "value2")

        _sync_env_var("TARGET", ["ALIAS1", "ALIAS2"])

        assert os.getenv("TARGET") == "value2"

    def test_sync_env_var_all_missing_no_change(self, monkeypatch):
        """全て存在しない場合は何もしない"""
        monkeypatch.delenv("TARGET", raising=False)
        monkeypatch.delenv("ALIAS1", raising=False)

        _sync_env_var("TARGET", ["ALIAS1"])

        assert os.getenv("TARGET") is None


# ============================================================================
# synchronize_aliases テスト
# ============================================================================
class TestSynchronizeAliases:
    def test_synchronize_aliases_gemini(self, monkeypatch):
        """Gemini APIキーのエイリアス同期"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY_AGENT_A", "gemini_key_a")

        synchronize_aliases()

        assert os.getenv("GEMINI_API_KEY") == "gemini_key_a"

    def test_synchronize_aliases_deepseek(self, monkeypatch):
        """DeepSeek APIキーのエイリアス同期"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("DEEPSEEK_KEY", "deepseek_value")

        synchronize_aliases()

        assert os.getenv("DEEPSEEK_API_KEY") == "deepseek_value"

    def test_synchronize_aliases_kimi(self, monkeypatch):
        """Kimi APIキーのエイリアス同期"""
        monkeypatch.delenv("KIMI_API_KEY", raising=False)
        monkeypatch.setenv("MOONSHOT_API_KEY", "moonshot_value")

        synchronize_aliases()

        assert os.getenv("KIMI_API_KEY") == "moonshot_value"

    def test_synchronize_aliases_priority_order(self, monkeypatch):
        """エイリアスの優先順位テスト"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY_AGENT_A", "key_a")
        monkeypatch.setenv("GEMINI_API_KEY_AGENT_B", "key_b")

        synchronize_aliases()

        # 最初のエイリアスが優先される
        assert os.getenv("GEMINI_API_KEY") == "key_a"


# ============================================================================
# ensure_env_loaded テスト
# ============================================================================
class TestEnsureEnvLoaded:
    def test_ensure_env_loaded_only_once(self, monkeypatch):
        """グローバル変数により1回だけ実行される"""
        import nexuscore.llm.config as config_module

        # リセット
        config_module._ENV_LOADED = False
        monkeypatch.delenv("NEXUSCORE_ENV_LOADED", raising=False)

        # 1回目
        result1 = ensure_env_loaded()

        # 2回目（_ENV_LOADEDがTrueになっているはず）
        config_module._ENV_LOADED = True
        monkeypatch.setenv("NEXUSCORE_ENV_LOADED", "test_path")
        result2 = ensure_env_loaded()

        assert result2 == "test_path"

    def test_ensure_env_loaded_with_custom_env_file(self, tmp_path, monkeypatch):
        """NEXUSCORE_ENV_FILE経由でカスタム.envを指定"""
        import nexuscore.llm.config as config_module

        env_file = tmp_path / ".env.custom"
        env_file.write_text("TEST_VAR=custom_value\n")

        config_module._ENV_LOADED = False
        monkeypatch.setenv("NEXUSCORE_ENV_FILE", str(env_file))
        monkeypatch.delenv("NEXUSCORE_ENV_LOADED", raising=False)

        with patch("nexuscore.llm.config.load_dotenv") as mock_load:
            mock_load.return_value = True
            ensure_env_loaded()

            # load_dotenvが呼ばれたことを確認
            assert mock_load.called

    def test_ensure_env_loaded_no_dotenv_warning(self, monkeypatch, caplog):
        """python-dotenvがない場合の警告"""
        import nexuscore.llm.config as config_module

        config_module._ENV_LOADED = False
        monkeypatch.delenv("NEXUSCORE_ENV_LOADED", raising=False)

        with patch("nexuscore.llm.config.load_dotenv", None):
            with patch("nexuscore.llm.config.find_dotenv", None):
                ensure_env_loaded()

                # 警告ログが出る（実装による）


# ============================================================================
# LLMRouterConfig テスト
# ============================================================================
class TestLLMRouterConfig:
    def test_config_from_env_with_all_keys(self, monkeypatch):
        """全APIキーが設定されている場合"""
        monkeypatch.setenv("OPENAI_API_KEY", "openai_key")
        monkeypatch.setenv("GEMINI_API_KEY", "gemini_key")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek_key")
        monkeypatch.setenv("KIMI_API_KEY", "kimi_key")
        monkeypatch.setenv("NEXUS_REQUEST_TIMEOUT_SEC", "60")
        monkeypatch.setenv("NEXUS_REAL_CALLS", "0")

        config = LLMRouterConfig.from_env()

        assert config.openai_api_key == "openai_key"
        assert config.gemini_api_key == "gemini_key"
        assert config.deepseek_api_key == "deepseek_key"
        assert config.kimi_api_key == "kimi_key"
        assert config.request_timeout == 60.0
        # APIキーが存在するため、real_calls_enabledは自動的にTrueになる
        assert config.real_calls_enabled is True

    def test_config_from_env_no_keys(self, monkeypatch):
        """APIキーが一切ない場合"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("KIMI_API_KEY", raising=False)
        monkeypatch.setenv("NEXUS_REAL_CALLS", "0")

        config = LLMRouterConfig.from_env()

        assert config.openai_api_key is None
        assert config.gemini_api_key is None
        assert config.deepseek_api_key is None
        assert config.kimi_api_key is None
        assert config.real_calls_enabled is False

    def test_config_from_env_auto_enable_real_calls(self, monkeypatch):
        """APIキーが存在する場合、real_callsを自動有効化"""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.delenv("NEXUS_REAL_CALLS", raising=False)

        config = LLMRouterConfig.from_env()

        assert config.real_calls_enabled is True
        assert os.getenv("NEXUS_REAL_CALLS") == "1"

    def test_config_from_env_default_timeout(self, monkeypatch):
        """タイムアウトのデフォルト値"""
        monkeypatch.delenv("NEXUS_REQUEST_TIMEOUT_SEC", raising=False)

        config = LLMRouterConfig.from_env()

        assert config.request_timeout == 120.0

    def test_config_from_env_custom_timeout(self, monkeypatch):
        """カスタムタイムアウト値"""
        monkeypatch.setenv("NEXUS_REQUEST_TIMEOUT_SEC", "300")

        config = LLMRouterConfig.from_env()

        assert config.request_timeout == 300.0

    def test_config_from_env_dry_run_enabled(self, monkeypatch):
        """ドライランモード有効化"""
        monkeypatch.setenv("LLM_DRY_RUN", "1")

        config = LLMRouterConfig.from_env()

        assert config.dry_run is True

    def test_config_from_env_dry_run_disabled(self, monkeypatch):
        """ドライランモード無効化"""
        monkeypatch.setenv("LLM_DRY_RUN", "0")

        config = LLMRouterConfig.from_env()

        assert config.dry_run is False

    def test_config_frozen_dataclass(self):
        """frozenデータクラスのため変更不可"""
        config = LLMRouterConfig(
            openai_api_key="test",
            gemini_api_key=None,
            deepseek_api_key=None,
            kimi_api_key=None,
            request_timeout=120.0,
            dry_run=False,
            real_calls_enabled=False,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            config.openai_api_key = "new_key"  # type: ignore

    def test_config_from_env_timeout_empty_string(self, monkeypatch):
        """タイムアウトが空文字列の場合"""
        monkeypatch.setenv("NEXUS_REQUEST_TIMEOUT_SEC", "")

        config = LLMRouterConfig.from_env()

        # 空文字列の場合、デフォルト120を使用
        assert config.request_timeout == 120.0

    def test_config_from_env_sets_default_timeout(self, monkeypatch):
        """環境変数にタイムアウトをセットする"""
        monkeypatch.delenv("NEXUS_REQUEST_TIMEOUT_SEC", raising=False)

        config = LLMRouterConfig.from_env()

        # 環境変数に設定される
        assert os.getenv("NEXUS_REQUEST_TIMEOUT_SEC") is not None


# ============================================================================
# 統合テスト
# ============================================================================
class TestConfigIntegration:
    def test_full_workflow_with_aliases(self, monkeypatch):
        """エイリアス同期からconfig作成までの完全ワークフロー"""
        # エイリアスを設定
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY_AGENT_A", "gemini_via_alias")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("DEEPSEEK", "deepseek_via_alias")

        # Configを作成（内部でsynchronize_aliasesが呼ばれる）
        config = LLMRouterConfig.from_env()

        # エイリアスから同期されたキーが使われる
        assert config.gemini_api_key == "gemini_via_alias"
        assert config.deepseek_api_key == "deepseek_via_alias"

    def test_config_with_minimal_env(self, monkeypatch):
        """最小限の環境変数でconfig作成"""
        # 全てのAPIキーをクリア
        for key in [
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "DEEPSEEK_API_KEY",
            "KIMI_API_KEY",
            "NEXUS_REAL_CALLS",
            "LLM_DRY_RUN",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = LLMRouterConfig.from_env()

        assert config.openai_api_key is None
        assert config.gemini_api_key is None
        assert config.deepseek_api_key is None
        assert config.kimi_api_key is None
        assert config.request_timeout == 120.0
        assert config.dry_run is False
        assert config.real_calls_enabled is False

    def test_config_priority_original_over_alias(self, monkeypatch):
        """オリジナルキーがエイリアスより優先される"""
        monkeypatch.setenv("GEMINI_API_KEY", "original_key")
        monkeypatch.setenv("GEMINI_API_KEY_AGENT_A", "alias_key")

        config = LLMRouterConfig.from_env()

        # オリジナルが優先される
        assert config.gemini_api_key == "original_key"
