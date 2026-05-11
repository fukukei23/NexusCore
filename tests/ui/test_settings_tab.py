"""Tests for settings_tab.py — P2-2 Settings UI タブ。"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


@pytest.fixture()
def _clean_import():
    """settings_tab を毎回再import して環境変数の変更を反映させる。"""
    import importlib

    import nexuscore.ui.settings_tab as mod

    importlib.reload(mod)
    yield mod


class TestProviderStatusTable:
    def test_all_providers_shown(self, _clean_import):
        """全プロバイダーがテーブルに含まれる。"""
        result = _clean_import._provider_status_table()
        assert "OpenAI" in result
        assert "Anthropic" in result
        assert "Google Gemini" in result
        assert "GLM (Zhipu AI)" in result
        assert "MiniMax" in result
        assert "DeepSeek" in result
        assert "Moonshot" in result

    def test_configured_provider_shows_check(self, _clean_import):
        """設定済みプロバイダーは ✅。"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            import importlib

            importlib.reload(_clean_import)
            result = _clean_import._provider_status_table()
            assert "✅ 設定済み" in result.split("OpenAI")[1].split("\n")[0]

    def test_missing_provider_shows_cross(self, _clean_import):
        """未設定プロバイダーは ❌。"""
        with patch.dict(os.environ, {}, clear=False):
            if "MOONSHOT_API_KEY" in os.environ:
                del os.environ["MOONSHOT_API_KEY"]
            import importlib

            importlib.reload(_clean_import)
            result = _clean_import._provider_status_table()
            assert "❌ 未設定" in result.split("Moonshot")[1].split("\n")[0]

    def test_table_has_markdown_format(self, _clean_import):
        """Markdown テーブル形式。"""
        result = _clean_import._provider_status_table()
        assert "| プロバイダー | API キー |" in result
        assert "|---|---|" in result


class TestProfilesTable:
    def test_profiles_loaded(self, _clean_import):
        """プロファイルがテーブルに表示される。"""
        result = _clean_import._profiles_table()
        assert "gpt_codex" in result
        assert "sonnet_review" in result
        assert "glm_default" in result
        assert "minimax_default" in result

    def test_table_has_columns(self, _clean_import):
        """テーブルに必要なカラムがある。"""
        result = _clean_import._profiles_table()
        assert "プロファイル" in result
        assert "プロバイダー" in result
        assert "モデル" in result
        assert "温度" in result


class TestTaskMapSummary:
    def test_tasks_listed(self, _clean_import):
        """タスクがリストされる。"""
        result = _clean_import._task_map_summary()
        assert "code_generate" in result
        assert "debug" in result
        assert "chat_general" in result

    def test_tier_headers(self, _clean_import):
        """ティアヘッダーが含まれる。"""
        result = _clean_import._task_map_summary()
        assert "Quality Tier" in result
        assert "Lightweight Tier" in result


class TestRuntimeStatus:
    def test_runtime_info(self, _clean_import):
        """ランタイム情報が含まれる。"""
        result = _clean_import._runtime_status()
        assert "LLM Router" in result
        assert "Whisper" in result
        assert "Self-Healing" in result


class TestBuildSettingsTab:
    def test_build_does_not_raise(self):
        """build_settings_tab が例外を投げない。"""
        import gradio as gr

        from nexuscore.ui.settings_tab import build_settings_tab
        from nexuscore.ui._state import AppState

        with gr.Blocks():
            state = gr.State(value=AppState())
            build_settings_tab(state)
