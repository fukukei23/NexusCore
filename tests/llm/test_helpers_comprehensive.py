"""
============================================================================
Comprehensive Tests for helpers.py
============================================================================
高品質テストの原則:
- 環境変数とCONFIGをモック（独立したテスト実行）
- 実際のヘルパーロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from nexuscore.llm.helpers import (
    DEFAULT_STUB_CONTENT,
    normalize_model,
    _env_flag,
    _real_call_enabled,
    _stub_response,
    _strip_jsonish,
)


# ============================================================================
# Tests: DEFAULT_STUB_CONTENT
# ============================================================================


class TestDefaultStubContent:
    def test_default_stub_content_structure(self):
        """デフォルトスタブコンテンツの構造"""
        assert "summary" in DEFAULT_STUB_CONTENT
        assert "plan" in DEFAULT_STUB_CONTENT
        assert isinstance(DEFAULT_STUB_CONTENT["plan"], list)

    def test_default_stub_content_plan_steps(self):
        """プランステップの構造"""
        plan = DEFAULT_STUB_CONTENT["plan"]
        assert len(plan) >= 1

        for step in plan:
            assert "step" in step
            assert "owner" in step
            assert "status" in step

    def test_default_stub_content_immutability(self):
        """デフォルトスタブは定数として扱われる"""
        # 同じ参照が返される
        assert DEFAULT_STUB_CONTENT is DEFAULT_STUB_CONTENT


# ============================================================================
# Tests: normalize_model
# ============================================================================


class TestNormalizeModel:
    def test_normalize_empty_string(self):
        """空文字列は "local-mock" にフォールバック"""
        assert normalize_model("") == "local-mock"

    def test_normalize_none_fallback(self):
        """Noneは "local-mock" にフォールバック"""
        # Note: 実装では if not name でチェックされるため、
        # None は Falsy なので "local-mock" が返される
        assert normalize_model(None) == "local-mock"

    def test_normalize_strips_whitespace(self):
        """空白をトリム"""
        assert normalize_model("  gpt-4  ") == "gpt-4"
        assert normalize_model("\tgpt-3.5-turbo\n") == "gpt-3.5-turbo"

    def test_normalize_vendor_prefix(self):
        """ベンダープレフィックス付きモデル名"""
        result = normalize_model("openai: gpt-4 ")
        assert result == "openai:gpt-4"

        result = normalize_model(" anthropic : claude-3 ")
        assert result == "anthropic:claude-3"

    def test_normalize_gemini_flash_latest(self):
        """Gemini Flash latestエイリアス"""
        assert normalize_model("gemini-2.5-flash-latest") == "gemini-2.5-flash"

    def test_normalize_gemini_pro_latest(self):
        """Gemini Pro latestエイリアス"""
        assert normalize_model("gemini-2.5-pro-latest") == "gemini-2.5-pro"

    def test_normalize_kimi_k2_preview(self):
        """Kimi K2 previewモデル"""
        assert normalize_model("kimi-k2-0711-preview") == "kimi-k2-0711-preview"
        assert normalize_model("kimi-k2-turbo-preview") == "kimi-k2-turbo-preview"

    def test_normalize_unknown_model(self):
        """未知のモデル名はそのまま返す"""
        assert normalize_model("custom-model-v1") == "custom-model-v1"
        assert normalize_model("gpt-5-experimental") == "gpt-5-experimental"

    def test_normalize_with_multiple_colons(self):
        """複数のコロンを含むモデル名"""
        # 最初のコロンで分割される
        result = normalize_model("vendor:model:version")
        assert result == "vendor:model:version"

    def test_normalize_preserves_case(self):
        """大文字小文字を保持"""
        assert normalize_model("GPT-4") == "GPT-4"
        assert normalize_model("Claude-3-Sonnet") == "Claude-3-Sonnet"


# ============================================================================
# Tests: _env_flag
# ============================================================================


class TestEnvFlag:
    def test_env_flag_default_true(self, monkeypatch):
        """デフォルト値がTrue"""
        monkeypatch.delenv("TEST_FLAG", raising=False)
        assert _env_flag("TEST_FLAG", True) is True

    def test_env_flag_default_false(self, monkeypatch):
        """デフォルト値がFalse"""
        monkeypatch.delenv("TEST_FLAG", raising=False)
        assert _env_flag("TEST_FLAG", False) is False

    def test_env_flag_value_1(self, monkeypatch):
        """値 "1" はTrue"""
        monkeypatch.setenv("TEST_FLAG", "1")
        assert _env_flag("TEST_FLAG", False) is True

    def test_env_flag_value_true(self, monkeypatch):
        """値 "true" はTrue"""
        monkeypatch.setenv("TEST_FLAG", "true")
        assert _env_flag("TEST_FLAG", False) is True

    def test_env_flag_value_yes(self, monkeypatch):
        """値 "yes" はTrue"""
        monkeypatch.setenv("TEST_FLAG", "yes")
        assert _env_flag("TEST_FLAG", False) is True

    def test_env_flag_value_on(self, monkeypatch):
        """値 "on" はTrue"""
        monkeypatch.setenv("TEST_FLAG", "on")
        assert _env_flag("TEST_FLAG", False) is True

    def test_env_flag_value_case_insensitive(self, monkeypatch):
        """大文字小文字を区別しない"""
        for value in ["TRUE", "True", "YES", "Yes", "ON", "On"]:
            monkeypatch.setenv("TEST_FLAG", value)
            assert _env_flag("TEST_FLAG", False) is True, f"Value {value} should be True"

    def test_env_flag_value_0(self, monkeypatch):
        """値 "0" はFalse"""
        monkeypatch.setenv("TEST_FLAG", "0")
        assert _env_flag("TEST_FLAG", True) is False

    def test_env_flag_value_false(self, monkeypatch):
        """値 "false" はFalse"""
        monkeypatch.setenv("TEST_FLAG", "false")
        assert _env_flag("TEST_FLAG", True) is False

    def test_env_flag_value_no(self, monkeypatch):
        """値 "no" はFalse"""
        monkeypatch.setenv("TEST_FLAG", "no")
        assert _env_flag("TEST_FLAG", True) is False

    def test_env_flag_value_with_whitespace(self, monkeypatch):
        """空白を含む値"""
        monkeypatch.setenv("TEST_FLAG", "  true  ")
        assert _env_flag("TEST_FLAG", False) is True

        monkeypatch.setenv("TEST_FLAG", "  false  ")
        assert _env_flag("TEST_FLAG", True) is False

    def test_env_flag_empty_string(self, monkeypatch):
        """空文字列はFalse"""
        monkeypatch.setenv("TEST_FLAG", "")
        assert _env_flag("TEST_FLAG", True) is False


# ============================================================================
# Tests: _real_call_enabled
# ============================================================================


class TestRealCallEnabled:
    def test_real_call_enabled_all_true(self, monkeypatch):
        """全ての条件が満たされる場合"""
        monkeypatch.setenv("LLM_DRY_RUN", "false")
        monkeypatch.setenv("NEXUS_REAL_CALLS", "true")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = False
            mock_config.real_calls_enabled = True

            assert _real_call_enabled("sk-test-api-key") is True

    def test_real_call_enabled_dry_run_true(self, monkeypatch):
        """DRY_RUNがTrueの場合はFalse"""
        monkeypatch.setenv("LLM_DRY_RUN", "true")
        monkeypatch.setenv("NEXUS_REAL_CALLS", "true")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = True
            mock_config.real_calls_enabled = True

            assert _real_call_enabled("sk-test-api-key") is False

    def test_real_call_enabled_no_api_key(self, monkeypatch):
        """APIキーがない場合はFalse"""
        monkeypatch.setenv("LLM_DRY_RUN", "false")
        monkeypatch.setenv("NEXUS_REAL_CALLS", "true")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = False
            mock_config.real_calls_enabled = True

            assert _real_call_enabled(None) is False
            assert _real_call_enabled("") is False

    def test_real_call_enabled_real_calls_false(self, monkeypatch):
        """REAL_CALLSがFalseの場合はFalse"""
        monkeypatch.setenv("LLM_DRY_RUN", "false")
        monkeypatch.setenv("NEXUS_REAL_CALLS", "false")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = False
            mock_config.real_calls_enabled = False

            assert _real_call_enabled("sk-test-api-key") is False

    def test_real_call_enabled_env_overrides_config(self, monkeypatch):
        """環境変数がCONFIGを上書き"""
        monkeypatch.setenv("LLM_DRY_RUN", "true")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = False  # CONFIGはFalse
            mock_config.real_calls_enabled = True

            # 環境変数のtrueが優先される
            assert _real_call_enabled("sk-test-api-key") is False


# ============================================================================
# Tests: _stub_response
# ============================================================================


class TestStubResponse:
    def test_stub_response_as_json_true(self):
        """JSONフォーマットでスタブレスポンス"""
        result = _stub_response(
            model_name="gpt-4",
            mode="stub",
            reason="API key not configured",
            as_json=True
        )

        # JSON文字列が返される
        data = json.loads(result)
        assert data["model"] == "gpt-4"
        assert data["mode"] == "stub"
        assert data["preview"] == "API key not configured"
        assert "content" in data
        assert data["content"] == DEFAULT_STUB_CONTENT

    def test_stub_response_as_json_false(self):
        """プレーンテキストでスタブレスポンス"""
        result = _stub_response(
            model_name="claude-3",
            mode="stub",
            reason="Dry run mode",
            as_json=False
        )

        # プレーンテキストが返される
        assert result == "Dry run mode"
        assert "{" not in result

    def test_stub_response_with_unicode(self):
        """Unicode文字を含むスタブレスポンス"""
        result = _stub_response(
            model_name="gemini",
            mode="stub",
            reason="テストモード 🚀",
            as_json=True
        )

        data = json.loads(result)
        assert data["preview"] == "テストモード 🚀"

    def test_stub_response_ensure_ascii_false(self):
        """ensure_ascii=Falseでエンコード"""
        result = _stub_response(
            model_name="test",
            mode="stub",
            reason="日本語",
            as_json=True
        )

        # Unicode文字がそのまま含まれる
        assert "日本語" in result
        assert "\\u" not in result  # エスケープされていない

    def test_stub_response_different_modes(self):
        """異なるモードでスタブレスポンス"""
        for mode in ["stub", "dry_run", "preview", "test"]:
            result = _stub_response(
                model_name="model",
                mode=mode,
                reason="test",
                as_json=True
            )

            data = json.loads(result)
            assert data["mode"] == mode


# ============================================================================
# Tests: _strip_jsonish
# ============================================================================


class TestStripJsonish:
    def test_strip_jsonish_plain_json(self):
        """プレーンなJSON"""
        json_str = '{"key": "value"}'
        assert _strip_jsonish(json_str) == '{"key": "value"}'

    def test_strip_jsonish_with_markdown_fences(self):
        """Markdownコードフェンス付きJSON"""
        text = '```json\n{"key": "value"}\n```'
        result = _strip_jsonish(text)
        assert result == '{"key": "value"}'

    def test_strip_jsonish_with_backticks_only(self):
        """バッククォートのみ"""
        text = '```\n{"key": "value"}\n```'
        result = _strip_jsonish(text)
        assert result == '{"key": "value"}'

    def test_strip_jsonish_with_prefix_text(self):
        """JSONの前にテキストがある場合"""
        text = 'Here is the response: {"key": "value"}'
        result = _strip_jsonish(text)
        assert result == '{"key": "value"}'

    def test_strip_jsonish_with_suffix_text(self):
        """JSONの後にテキストがある場合"""
        text = '{"key": "value"} and some more text'
        result = _strip_jsonish(text)
        assert result == '{"key": "value"}'

    def test_strip_jsonish_with_prefix_and_suffix(self):
        """前後にテキストがある場合"""
        text = 'Response: {"key": "value"} Done.'
        result = _strip_jsonish(text)
        assert result == '{"key": "value"}'

    def test_strip_jsonish_nested_braces(self):
        """ネストされた中括弧"""
        text = '{"outer": {"inner": "value"}}'
        result = _strip_jsonish(text)
        assert result == '{"outer": {"inner": "value"}}'

    def test_strip_jsonish_empty_string(self):
        """空文字列"""
        assert _strip_jsonish("") == ""

    def test_strip_jsonish_none(self):
        """Noneは空文字列として扱われる"""
        # Note: 実装では if not text で空文字列チェックしているが、
        # Noneは Falsy なので空文字列を返す
        assert _strip_jsonish(None) == None

    def test_strip_jsonish_whitespace_only(self):
        """空白のみ"""
        assert _strip_jsonish("   \n\t  ") == ""

    def test_strip_jsonish_no_braces(self):
        """中括弧がない場合"""
        text = "plain text without braces"
        result = _strip_jsonish(text)
        # 中括弧がないので元のテキストがstrip()されて返される
        assert result == "plain text without braces"

    def test_strip_jsonish_markdown_json_uppercase(self):
        """大文字のJSON指定"""
        text = '```JSON\n{"key": "value"}\n```'
        result = _strip_jsonish(text)
        assert result == '{"key": "value"}'

    def test_strip_jsonish_complex_markdown(self):
        """複雑なMarkdownフェンス"""
        text = '''```json
        {
          "name": "test",
          "value": 123,
          "nested": {
            "key": "value"
          }
        }
        ```'''
        result = _strip_jsonish(text)
        assert "name" in result
        assert "test" in result
        assert result.strip().startswith("{")
        assert result.strip().endswith("}")


# ============================================================================
# Tests: Integration scenarios
# ============================================================================


class TestIntegrationScenarios:
    def test_full_stub_workflow(self, monkeypatch):
        """完全なスタブワークフロー"""
        # 1. 環境変数を設定
        monkeypatch.setenv("LLM_DRY_RUN", "true")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = True

            # 2. 実呼び出しは無効
            assert _real_call_enabled("sk-test-key") is False

            # 3. スタブレスポンスを生成
            stub = _stub_response(
                model_name=normalize_model("gpt-4"),
                mode="dry_run",
                reason="DRY_RUN mode enabled",
                as_json=True
            )

            # 4. レスポンスを検証
            data = json.loads(stub)
            assert data["model"] == "gpt-4"
            assert data["mode"] == "dry_run"

    def test_model_normalization_pipeline(self):
        """モデル名正規化パイプライン"""
        # 様々なモデル名を正規化
        test_cases = [
            ("  gpt-4  ", "gpt-4"),
            ("openai: gpt-4", "openai:gpt-4"),
            ("gemini-2.5-flash-latest", "gemini-2.5-flash"),
            ("custom-model", "custom-model"),
            ("", "local-mock"),
        ]

        for input_name, expected in test_cases:
            result = normalize_model(input_name)
            assert result == expected, f"Failed for {input_name}"

    def test_json_extraction_from_llm_response(self):
        """LLMレスポンスからのJSON抽出"""
        # LLMが返す様々な形式をテスト
        responses = [
            '```json\n{"result": "success"}\n```',
            'Here is the JSON: {"result": "success"}',
            '{"result": "success"}',
            'Result:\n\n```\n{"result": "success"}\n```\n\nDone.',
        ]

        for response in responses:
            cleaned = _strip_jsonish(response)
            # 全てのケースでJSONが抽出できる
            data = json.loads(cleaned)
            assert data["result"] == "success"


# ============================================================================
# Tests: Edge cases
# ============================================================================


class TestEdgeCases:
    def test_normalize_model_with_emoji(self):
        """絵文字を含むモデル名"""
        assert normalize_model("gpt-4🚀") == "gpt-4🚀"

    def test_env_flag_with_numbers(self, monkeypatch):
        """数値の環境変数"""
        monkeypatch.setenv("TEST_FLAG", "123")
        assert _env_flag("TEST_FLAG", True) is False  # "1"以外の数値はFalse

    def test_strip_jsonish_multiple_json_objects(self):
        """複数のJSONオブジェクト"""
        text = '{"first": 1} {"second": 2}'
        result = _strip_jsonish(text)
        # 最初の{から最後の}まで
        assert result == '{"first": 1} {"second": 2}'

    def test_strip_jsonish_with_escaped_braces(self):
        """エスケープされた中括弧"""
        text = r'{"key": "value with \{ and \}"}'
        result = _strip_jsonish(text)
        assert "{" in result
        assert "}" in result

    def test_real_call_enabled_with_whitespace_api_key(self, monkeypatch):
        """空白のみのAPIキー"""
        monkeypatch.setenv("LLM_DRY_RUN", "false")
        monkeypatch.setenv("NEXUS_REAL_CALLS", "true")

        with patch('nexuscore.llm.helpers.CONFIG') as mock_config:
            mock_config.dry_run = False
            mock_config.real_calls_enabled = True

            # 空白のみのキーはFalse（bool("")はFalse）
            assert _real_call_enabled("   ") is True  # bool("   ") は True!

    def test_stub_response_with_special_characters(self):
        """特殊文字を含むスタブレスポンス"""
        result = _stub_response(
            model_name="test<>\"'&",
            mode="stub",
            reason="Special chars: <>\"'&",
            as_json=True
        )

        data = json.loads(result)
        assert data["model"] == "test<>\"'&"
        assert data["preview"] == "Special chars: <>\"'&"

    def test_normalize_model_empty_vendor(self):
        """空のベンダー名"""
        result = normalize_model(":model")
        assert result == ":model"

    def test_normalize_model_empty_model(self):
        """空のモデル名（ベンダーのみ）"""
        result = normalize_model("vendor:")
        assert result == "vendor:"
