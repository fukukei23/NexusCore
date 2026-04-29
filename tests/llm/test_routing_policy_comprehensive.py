"""
Comprehensive tests for llm/routing_policy.py

ルーティングポリシーとモデルファミリー識別のテスト
NexusCore supports multiple LLM providers: OpenAI, Anthropic, Google Gemini,
GLM (Zhipu AI), MiniMax, DeepSeek, and Moonshot.
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
    def test_model_family_direct_glm(self):
        """直接名 'glm' でGLMファミリー"""
        assert model_family("glm") == "glm"

    def test_model_family_direct_minimax(self):
        """直接名 'minimax' でMiniMaxファミリー"""
        assert model_family("minimax") == "minimax"

    def test_model_family_colon_glm(self):
        """コロン形式 'glm:model' でGLMファミリー"""
        assert model_family("glm:glm-4-plus") == "glm"

    def test_model_family_colon_minimax(self):
        """コロン形式 'minimax:model' でMiniMaxファミリー"""
        assert model_family("minimax:minimax-m2.7") == "minimax"

    def test_model_family_glm_prefix(self):
        """glm- 接頭辞でGLMファミリー"""
        assert model_family("glm-4-plus") == "glm"
        assert model_family("glm-4-flash") == "glm"
        assert model_family("glm-5.1") == "glm"

    def test_model_family_chatglm_prefix(self):
        """chatglm 接頭辞でGLMファミリー"""
        assert model_family("chatglm-4") == "glm"

    def test_model_family_minimax_prefix(self):
        """minimax 接頭辞でMiniMaxファミリー"""
        assert model_family("minimax-m2.7") == "minimax"
        assert model_family("MiniMax-M2.7") == "minimax"

    def test_model_family_unknown_fallback_to_glm(self):
        """未知のモデルはGLMにフォールバック"""
        assert model_family("unknown-model") == "glm"
        assert model_family("random-xyz") == "glm"
        assert model_family("test123") == "glm"

    def test_model_family_case_insensitive(self):
        """大文字小文字を区別しない"""
        assert model_family("GLM-4-PLUS") == "glm"
        assert model_family("MINIMAX-M2.7") == "minimax"

    def test_model_family_empty_string(self):
        """空文字列はGLMにフォールバック"""
        assert model_family("") == "glm"


# ============================================================================
# split_provider テスト
# ============================================================================
class TestSplitProvider:
    def test_split_provider_with_colon_glm(self):
        """コロン形式のGLMモデル分割"""
        vendor, model = split_provider("glm:glm-4-plus")

        assert vendor == "glm"
        assert model == "glm-4-plus"

    def test_split_provider_with_colon_minimax(self):
        """コロン形式のMiniMaxモデル分割"""
        vendor, model = split_provider("minimax:minimax-m2.7")

        assert vendor == "minimax"
        assert model == "minimax-m2.7"

    def test_split_provider_without_colon_glm(self):
        """コロンなしのGLMモデル（推論）"""
        vendor, model = split_provider("glm-4-plus")

        assert vendor == "glm"
        assert model == "glm-4-plus"

    def test_split_provider_without_colon_minimax(self):
        """コロンなしのMiniMaxモデル（推論）"""
        vendor, model = split_provider("minimax-m2.7")

        assert vendor == "minimax"
        assert model == "minimax-m2.7"

    def test_split_provider_without_colon_unknown(self):
        """コロンなし未知モデル（GLMにフォールバック）"""
        vendor, model = split_provider("unknown-model")

        assert vendor == "glm"
        assert model == "unknown-model"

    def test_split_provider_strips_whitespace(self):
        """前後の空白を除去"""
        vendor, model = split_provider("  glm : glm-4-plus  ")

        assert vendor == "glm"
        assert model == "glm-4-plus"

    def test_split_provider_lowercase_vendor(self):
        """ベンダー名を小文字化"""
        vendor, model = split_provider("GLM:glm-4-plus")

        assert vendor == "glm"

    def test_split_provider_preserves_model_case(self):
        """モデル名の大文字小文字は保持"""
        vendor, model = split_provider("minimax:MiniMax-M2.7")

        assert model == "MiniMax-M2.7"

    def test_split_provider_multiple_colons(self):
        """複数コロンは最初のコロンで分割"""
        vendor, model = split_provider("glm:model:version")

        assert vendor == "glm"
        assert model == "model:version"

    def test_split_provider_empty_string(self):
        """空文字列（GLMにフォールバック）"""
        vendor, model = split_provider("")

        assert vendor == "glm"
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
        for _task, config in TASK_MODEL_MAP_DEFAULT.items():
            assert "primary" in config
            assert "fallbacks" in config
            assert isinstance(config["primary"], str)
            assert isinstance(config["fallbacks"], list)

    def test_task_model_map_built_from_task_model_configs(self):
        """task_model_map から構築されている"""
        from nexuscore.llm.task_model_map import build_task_model_map_dict

        expected = build_task_model_map_dict()
        assert TASK_MODEL_MAP_DEFAULT == expected

    def test_all_providers_are_valid(self):
        """全プロバイダーが既知のプロバイダー"""
        valid_prefixes = ("openai:", "anthropic:", "google:", "glm:", "minimax:", "deepseek:", "moonshot:", "local:")
        for task, config in TASK_MODEL_MAP_DEFAULT.items():
            primary = config["primary"]
            assert primary.startswith(valid_prefixes), \
                f"Task {task} has unknown provider primary: {primary}"
            for fb in config["fallbacks"]:
                assert fb.startswith(valid_prefixes), \
                    f"Task {task} has unknown provider fallback: {fb}"


# ============================================================================
# 統合テスト
# ============================================================================
class TestRoutingPolicyIntegration:
    def test_model_family_and_split_provider_consistency(self):
        """model_familyとsplit_providerの一貫性"""
        test_cases = [
            ("glm:glm-4-plus", "glm"),
            ("minimax:minimax-m2.7", "minimax"),
        ]

        for model_name, expected_family in test_cases:
            family = model_family(model_name)
            assert family == expected_family

            vendor, _ = split_provider(model_name)
            assert vendor == expected_family

    def test_prefix_inference_consistency(self):
        """接頭辞による推論の一貫性"""
        test_cases = [
            ("glm-4-plus", "glm"),
            ("minimax-m2.7", "minimax"),
            ("chatglm-4", "glm"),
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

            # 両方ともglmにフォールバック
            assert family == "glm"
            assert vendor == "glm"

    def test_case_insensitivity_consistency(self):
        """大文字小文字の扱いの一貫性"""
        test_models = ["GLM-4-PLUS", "MINIMAX-M2.7"]

        for model_name in test_models:
            family_lower = model_family(model_name.lower())
            family_upper = model_family(model_name)

            assert family_lower == family_upper

    def test_legacy_to_task_available(self):
        """LEGACY_TO_TASKが利用可能"""
        assert isinstance(LEGACY_TO_TASK, dict)
        assert len(LEGACY_TO_TASK) > 0

    def test_all_model_families_handled(self):
        """全モデルファミリーが処理される"""
        families = ["glm", "minimax"]

        for family in families:
            assert model_family(family) in families

            vendor, model = split_provider(f"{family}:test-model")
            assert vendor == family

    def test_split_provider_returns_tuple(self):
        """split_providerがタプルを返す"""
        result = split_provider("glm:glm-4-plus")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_model_family_deterministic(self):
        """model_familyが決定論的"""
        model_name = "glm-4-plus"

        result1 = model_family(model_name)
        result2 = model_family(model_name)

        assert result1 == result2
        assert result1 == "glm"
