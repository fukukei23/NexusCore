"""
Comprehensive tests for llm/routing_policy.py

ルーティングポリシーとモデルファミリー識別のテスト
"""


from nexuscore.llm.routing_policy import (
    LEGACY_TO_TASK,
    TASK_MODEL_MAP_DEFAULT,
    model_family,
    split_provider,
)


# ============================================================================
# model_family テスト
# ============================================================================
class TestModelFamily:
    def test_model_family_direct_openai(self):
        """直接名 'openai' でOpenAIファミリー"""
        assert model_family("openai") == "openai"

    def test_model_family_direct_gemini(self):
        """直接名 'gemini' でGeminiファミリー"""
        assert model_family("gemini") == "gemini"

    def test_model_family_direct_google_maps_to_gemini(self):
        """直接名 'google' がGeminiにマップされる"""
        assert model_family("google") == "gemini"

    def test_model_family_direct_anthropic(self):
        """直接名 'anthropic' でAnthropicファミリー"""
        assert model_family("anthropic") == "anthropic"

    def test_model_family_direct_deepseek(self):
        """直接名 'deepseek' でDeepSeekファミリー"""
        assert model_family("deepseek") == "deepseek"

    def test_model_family_direct_kimi(self):
        """直接名 'kimi' でKimiファミリー"""
        assert model_family("kimi") == "kimi"

    def test_model_family_direct_local(self):
        """直接名 'local' でLocalファミリー"""
        assert model_family("local") == "local"

    def test_model_family_colon_openai(self):
        """コロン形式 'openai:model' でOpenAIファミリー"""
        assert model_family("openai:gpt-4") == "openai"

    def test_model_family_colon_google(self):
        """コロン形式 'google:model' がGeminiにマップ"""
        assert model_family("google:gemini-pro") == "gemini"

    def test_model_family_colon_anthropic(self):
        """コロン形式 'anthropic:model' でAnthropicファミリー"""
        assert model_family("anthropic:claude-3") == "anthropic"

    def test_model_family_colon_deepseek(self):
        """コロン形式 'deepseek:model' でDeepSeekファミリー"""
        assert model_family("deepseek:coder") == "deepseek"

    def test_model_family_colon_kimi(self):
        """コロン形式 'kimi:model' でKimiファミリー"""
        assert model_family("kimi:moonshot") == "kimi"

    def test_model_family_gpt_prefix(self):
        """gpt- 接頭辞でOpenAIファミリー"""
        assert model_family("gpt-4") == "openai"
        assert model_family("gpt-3.5-turbo") == "openai"
        assert model_family("gpt-5.1-mini") == "openai"

    def test_model_family_o_prefix(self):
        """o 接頭辞（oモデル）でOpenAIファミリー"""
        assert model_family("o1") == "openai"
        assert model_family("o2-preview") == "openai"

    def test_model_family_openai_prefix(self):
        """openai- 接頭辞でOpenAIファミリー"""
        assert model_family("openai-gpt4") == "openai"

    def test_model_family_gemini_prefix(self):
        """gemini 接頭辞でGeminiファミリー"""
        assert model_family("gemini-pro") == "gemini"
        assert model_family("gemini-1.5") == "gemini"
        assert model_family("gemini-ultra") == "gemini"

    def test_model_family_claude_prefix(self):
        """claude 接頭辞でAnthropicファミリー"""
        assert model_family("claude-3-opus") == "anthropic"
        assert model_family("claude-4.5-sonnet") == "anthropic"

    def test_model_family_anthropic_prefix(self):
        """anthropic 接頭辞でAnthropicファミリー"""
        assert model_family("anthropic-v1") == "anthropic"

    def test_model_family_deepseek_prefix(self):
        """deepseek 接頭辞でDeepSeekファミリー"""
        assert model_family("deepseek-coder") == "deepseek"
        assert model_family("deepseek-r1") == "deepseek"

    def test_model_family_kimi_prefix(self):
        """kimi 接頭辞でKimiファミリー"""
        assert model_family("kimi-1") == "kimi"

    def test_model_family_llama_prefix(self):
        """llama 接頭辞でLocalファミリー"""
        assert model_family("llama-2") == "local"
        assert model_family("llama-3-70b") == "local"

    def test_model_family_local_prefix(self):
        """local 接頭辞でLocalファミリー"""
        assert model_family("local-model") == "local"

    def test_model_family_unknown_fallback(self):
        """未知のモデルはLocalにフォールバック"""
        assert model_family("unknown-model") == "local"
        assert model_family("random-xyz") == "local"
        assert model_family("test123") == "local"

    def test_model_family_case_insensitive(self):
        """大文字小文字を区別しない"""
        assert model_family("GPT-4") == "openai"
        assert model_family("GEMINI-PRO") == "gemini"
        assert model_family("Claude-3") == "anthropic"

    def test_model_family_empty_string(self):
        """空文字列はLocalファミリー"""
        assert model_family("") == "local"


# ============================================================================
# split_provider テスト
# ============================================================================
class TestSplitProvider:
    def test_split_provider_with_colon_openai(self):
        """コロン形式のOpenAIモデル分割"""
        vendor, model = split_provider("openai:gpt-4")

        assert vendor == "openai"
        assert model == "gpt-4"

    def test_split_provider_with_colon_gemini(self):
        """コロン形式のGeminiモデル分割"""
        vendor, model = split_provider("gemini:gemini-pro")

        assert vendor == "gemini"
        assert model == "gemini-pro"

    def test_split_provider_with_colon_google(self):
        """コロン形式のGoogle（Gemini）モデル分割"""
        vendor, model = split_provider("google:gemini-1.5")

        assert vendor == "google"
        assert model == "gemini-1.5"

    def test_split_provider_with_colon_anthropic(self):
        """コロン形式のAnthropicモデル分割"""
        vendor, model = split_provider("anthropic:claude-3-opus")

        assert vendor == "anthropic"
        assert model == "claude-3-opus"

    def test_split_provider_with_colon_deepseek(self):
        """コロン形式のDeepSeekモデル分割"""
        vendor, model = split_provider("deepseek:deepseek-coder")

        assert vendor == "deepseek"
        assert model == "deepseek-coder"

    def test_split_provider_with_colon_kimi(self):
        """コロン形式のKimiモデル分割"""
        vendor, model = split_provider("kimi:moonshot-v1")

        assert vendor == "kimi"
        assert model == "moonshot-v1"

    def test_split_provider_without_colon_gpt(self):
        """コロンなしのGPTモデル（推論）"""
        vendor, model = split_provider("gpt-4")

        assert vendor == "openai"  # 推論されたベンダー
        assert model == "gpt-4"

    def test_split_provider_without_colon_gemini(self):
        """コロンなしのGeminiモデル（推論）"""
        vendor, model = split_provider("gemini-pro")

        assert vendor == "gemini"
        assert model == "gemini-pro"

    def test_split_provider_without_colon_claude(self):
        """コロンなしのClaudeモデル（推論）"""
        vendor, model = split_provider("claude-3-sonnet")

        assert vendor == "anthropic"
        assert model == "claude-3-sonnet"

    def test_split_provider_without_colon_deepseek(self):
        """コロンなしのDeepSeekモデル（推論）"""
        vendor, model = split_provider("deepseek-r1")

        assert vendor == "deepseek"
        assert model == "deepseek-r1"

    def test_split_provider_without_colon_unknown(self):
        """コロンなし未知モデル（Localに推論）"""
        vendor, model = split_provider("unknown-model")

        assert vendor == "local"
        assert model == "unknown-model"

    def test_split_provider_strips_whitespace(self):
        """前後の空白を除去"""
        vendor, model = split_provider("  openai : gpt-4  ")

        assert vendor == "openai"
        assert model == "gpt-4"

    def test_split_provider_lowercase_vendor(self):
        """ベンダー名を小文字化"""
        vendor, model = split_provider("OPENAI:gpt-4")

        assert vendor == "openai"

    def test_split_provider_preserves_model_case(self):
        """モデル名の大文字小文字は保持"""
        vendor, model = split_provider("openai:GPT-4-Turbo")

        assert model == "GPT-4-Turbo"

    def test_split_provider_multiple_colons(self):
        """複数コロンは最初のコロンで分割"""
        vendor, model = split_provider("openai:model:version")

        assert vendor == "openai"
        assert model == "model:version"

    def test_split_provider_empty_string(self):
        """空文字列（Localにフォールバック）"""
        vendor, model = split_provider("")

        assert vendor == "local"
        assert model == ""


# ============================================================================
# TASK_MODEL_MAP_DEFAULT テスト
# ============================================================================
class TestTaskModelMapDefault:
    def test_task_model_map_is_dict(self):
        """TASK_MODEL_MAP_DEFAULTが辞書"""
        assert isinstance(TASK_MODEL_MAP_DEFAULT, dict)

    def test_task_model_map_not_empty(self):
        """TASK_MODEL_MAP_DEFAULTが空でない"""
        assert len(TASK_MODEL_MAP_DEFAULT) > 0

    def test_task_model_map_contains_core_tasks(self):
        """コアタスクが含まれる"""
        core_tasks = ["code_generate", "code_review", "test_generate", "debug"]
        for task in core_tasks:
            assert task in TASK_MODEL_MAP_DEFAULT

    def test_task_model_map_entry_structure(self):
        """各エントリが正しい構造を持つ"""
        for task, config in TASK_MODEL_MAP_DEFAULT.items():
            assert "primary" in config
            assert "fallbacks" in config
            assert isinstance(config["primary"], str)
            assert isinstance(config["fallbacks"], list)

    def test_task_model_map_built_from_task_model_configs(self):
        """task_model_map から構築されている"""
        from nexuscore.llm.task_model_map import build_task_model_map_dict

        expected = build_task_model_map_dict()
        assert TASK_MODEL_MAP_DEFAULT == expected


# ============================================================================
# 統合テスト
# ============================================================================
class TestRoutingPolicyIntegration:
    def test_model_family_and_split_provider_consistency(self):
        """model_familyとsplit_providerの一貫性"""
        test_cases = [
            ("openai:gpt-4", "openai"),
            ("gemini:gemini-pro", "gemini"),
            ("anthropic:claude-3", "anthropic"),
            ("deepseek:coder", "deepseek"),
            ("kimi:moonshot", "kimi"),
        ]

        for model_name, expected_family in test_cases:
            # model_family で取得
            family = model_family(model_name)
            assert family == expected_family

            # split_provider で取得
            vendor, _ = split_provider(model_name)
            # google -> gemini へのマッピングを考慮
            if vendor == "google":
                vendor = "gemini"
            assert vendor == expected_family

    def test_prefix_inference_consistency(self):
        """接頭辞による推論の一貫性"""
        test_cases = [
            ("gpt-4", "openai"),
            ("gemini-pro", "gemini"),
            ("claude-3-opus", "anthropic"),
            ("deepseek-coder", "deepseek"),
            ("llama-2", "local"),
        ]

        for model_name, expected_family in test_cases:
            family = model_family(model_name)
            vendor, _ = split_provider(model_name)

            assert family == expected_family
            assert vendor == expected_family

    def test_unknown_model_fallback_consistency(self):
        """未知モデルのフォールバックの一貫性"""
        unknown_models = ["unknown-xyz", "random-model", "test123"]

        for model_name in unknown_models:
            family = model_family(model_name)
            vendor, _ = split_provider(model_name)

            # 両方ともlocalにフォールバック
            assert family == "local"
            assert vendor == "local"

    def test_case_insensitivity_consistency(self):
        """大文字小文字の扱いの一貫性"""
        test_models = ["GPT-4", "GEMINI-PRO", "Claude-3", "DeepSeek-Coder"]

        for model_name in test_models:
            family_lower = model_family(model_name.lower())
            family_upper = model_family(model_name)

            # model_familyは大文字小文字を区別しない
            assert family_lower == family_upper

    def test_legacy_to_task_available(self):
        """LEGACY_TO_TASKが利用可能"""
        assert isinstance(LEGACY_TO_TASK, dict)
        assert len(LEGACY_TO_TASK) > 0

    def test_all_model_families_handled(self):
        """全モデルファミリーが処理される"""
        families = ["openai", "gemini", "anthropic", "deepseek", "kimi", "local"]

        for family in families:
            # 直接名で取得
            assert model_family(family) in families

            # コロン形式で取得
            vendor, model = split_provider(f"{family}:test-model")
            if family == "google":
                assert vendor == "gemini"
            else:
                assert vendor == family

    def test_split_provider_returns_tuple(self):
        """split_providerがタプルを返す"""
        result = split_provider("openai:gpt-4")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_model_family_deterministic(self):
        """model_familyが決定論的"""
        model_name = "gpt-4-turbo"

        result1 = model_family(model_name)
        result2 = model_family(model_name)

        assert result1 == result2
        assert result1 == "openai"
