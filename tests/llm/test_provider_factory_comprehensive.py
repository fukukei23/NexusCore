"""
Comprehensive tests for llm/provider_factory.py

プロバイダーファクトリーとクラスマッピングのテスト
"""

import pytest

from nexuscore.llm.provider_factory import (
    PROVIDER_CLASSES,
    create_provider,
    get_provider_class,
)
from nexuscore.llm.providers import (
    AnthropicLLM,
    BaseLLM,
    DeepSeekLLM,
    GeminiLLM,
    LocalLLM,
    MoonshotLLM,
    OpenAILLM,
)


# ============================================================================
# PROVIDER_CLASSES テスト
# ============================================================================
class TestProviderClasses:
    def test_provider_classes_is_dict(self):
        """PROVIDER_CLASSESが辞書"""
        assert isinstance(PROVIDER_CLASSES, dict)

    def test_provider_classes_contains_openai(self):
        """OpenAIプロバイダーが登録されている"""
        assert "openai" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["openai"] == OpenAILLM

    def test_provider_classes_contains_gemini(self):
        """Geminiプロバイダーが登録されている"""
        assert "gemini" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["gemini"] == GeminiLLM

    def test_provider_classes_contains_kimi(self):
        """Kimiプロバイダーが登録されている"""
        assert "kimi" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["kimi"] == MoonshotLLM

    def test_provider_classes_contains_anthropic(self):
        """Anthropicプロバイダーが登録されている"""
        assert "anthropic" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["anthropic"] == AnthropicLLM

    def test_provider_classes_contains_deepseek(self):
        """DeepSeekプロバイダーが登録されている"""
        assert "deepseek" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["deepseek"] == DeepSeekLLM

    def test_provider_classes_contains_local(self):
        """Localプロバイダーが登録されている"""
        assert "local" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["local"] == LocalLLM

    def test_provider_classes_minimum_count(self):
        """最低限のプロバイダー数が登録されている"""
        assert len(PROVIDER_CLASSES) >= 6

    def test_all_provider_classes_are_types(self):
        """全プロバイダークラスが型である"""
        for family, provider_cls in PROVIDER_CLASSES.items():
            assert isinstance(provider_cls, type), f"{family} is not a type"

    def test_all_provider_classes_inherit_base_llm(self):
        """全プロバイダークラスがBaseLLMを継承"""
        for family, provider_cls in PROVIDER_CLASSES.items():
            assert issubclass(provider_cls, BaseLLM), f"{family} doesn't inherit from BaseLLM"

    def test_provider_classes_keys_are_lowercase(self):
        """全キーが小文字"""
        for key in PROVIDER_CLASSES.keys():
            assert key == key.lower(), f"Key '{key}' is not lowercase"


# ============================================================================
# get_provider_class テスト
# ============================================================================
class TestGetProviderClass:
    def test_get_provider_class_openai(self):
        """OpenAIプロバイダークラスを取得"""
        provider_cls = get_provider_class("openai")

        assert provider_cls == OpenAILLM

    def test_get_provider_class_gemini(self):
        """Geminiプロバイダークラスを取得"""
        provider_cls = get_provider_class("gemini")

        assert provider_cls == GeminiLLM

    def test_get_provider_class_kimi(self):
        """Kimiプロバイダークラスを取得"""
        provider_cls = get_provider_class("kimi")

        assert provider_cls == MoonshotLLM

    def test_get_provider_class_anthropic(self):
        """Anthropicプロバイダークラスを取得"""
        provider_cls = get_provider_class("anthropic")

        assert provider_cls == AnthropicLLM

    def test_get_provider_class_deepseek(self):
        """DeepSeekプロバイダークラスを取得"""
        provider_cls = get_provider_class("deepseek")

        assert provider_cls == DeepSeekLLM

    def test_get_provider_class_local(self):
        """Localプロバイダークラスを取得"""
        provider_cls = get_provider_class("local")

        assert provider_cls == LocalLLM

    def test_get_provider_class_unknown_raises_error(self):
        """存在しないプロバイダーはValueError"""
        with pytest.raises(ValueError, match="Unsupported model family"):
            get_provider_class("unknown_provider")

    def test_get_provider_class_empty_string_raises_error(self):
        """空文字列はValueError"""
        with pytest.raises(ValueError, match="Unsupported model family"):
            get_provider_class("")

    def test_get_provider_class_case_sensitive(self):
        """大文字小文字を区別する"""
        # 小文字は成功
        assert get_provider_class("openai") == OpenAILLM

        # 大文字は失敗
        with pytest.raises(ValueError):
            get_provider_class("OpenAI")

    def test_get_provider_class_returns_class_not_instance(self):
        """インスタンスではなくクラスを返す"""
        provider_cls = get_provider_class("openai")

        assert isinstance(provider_cls, type)
        assert issubclass(provider_cls, BaseLLM)


# ============================================================================
# create_provider テスト
# ============================================================================
class TestCreateProvider:
    def test_create_provider_openai_with_colon(self):
        """OpenAI プロバイダーをコロン形式で作成"""
        provider = create_provider("openai:gpt-4")

        assert isinstance(provider, OpenAILLM)
        assert isinstance(provider, BaseLLM)

    def test_create_provider_gemini_with_colon(self):
        """Gemini プロバイダーをコロン形式で作成"""
        provider = create_provider("gemini:gemini-pro")

        assert isinstance(provider, GeminiLLM)

    def test_create_provider_anthropic_with_colon(self):
        """Anthropic プロバイダーをコロン形式で作成"""
        provider = create_provider("anthropic:claude-3")

        assert isinstance(provider, AnthropicLLM)

    def test_create_provider_deepseek_with_colon(self):
        """DeepSeek プロバイダーをコロン形式で作成"""
        provider = create_provider("deepseek:deepseek-coder")

        assert isinstance(provider, DeepSeekLLM)

    def test_create_provider_kimi_with_colon(self):
        """Kimi プロバイダーをコロン形式で作成"""
        provider = create_provider("kimi:moonshot-v1")

        assert isinstance(provider, MoonshotLLM)

    def test_create_provider_without_colon_gpt(self):
        """コロンなし（GPT接頭辞）でOpenAIプロバイダー作成"""
        provider = create_provider("gpt-4")

        assert isinstance(provider, OpenAILLM)

    def test_create_provider_without_colon_gemini(self):
        """コロンなし（gemini接頭辞）でGeminiプロバイダー作成"""
        provider = create_provider("gemini-pro")

        assert isinstance(provider, GeminiLLM)

    def test_create_provider_without_colon_claude(self):
        """コロンなし（claude接頭辞）でAnthropicプロバイダー作成"""
        provider = create_provider("claude-3-opus")

        assert isinstance(provider, AnthropicLLM)

    def test_create_provider_without_colon_deepseek(self):
        """コロンなし（deepseek接頭辞）でDeepSeekプロバイダー作成"""
        provider = create_provider("deepseek-coder")

        assert isinstance(provider, DeepSeekLLM)

    def test_create_provider_without_colon_kimi(self):
        """コロンなし（kimi接頭辞）でKimiプロバイダー作成"""
        provider = create_provider("kimi-1")

        assert isinstance(provider, MoonshotLLM)

    def test_create_provider_without_colon_local(self):
        """コロンなし（local接頭辞）でLocalプロバイダー作成"""
        provider = create_provider("local-model")

        assert isinstance(provider, LocalLLM)

    def test_create_provider_unknown_model_fallback_local(self):
        """未知のモデルはLocalプロバイダーにフォールバック"""
        provider = create_provider("unknown-model-xyz")

        assert isinstance(provider, LocalLLM)

    def test_create_provider_returns_base_llm_instance(self):
        """BaseLLMインスタンスを返す"""
        provider = create_provider("openai:gpt-4")

        assert isinstance(provider, BaseLLM)

    def test_create_provider_google_alias(self):
        """googleエイリアスがgeminiにマップされる"""
        provider = create_provider("google:gemini-pro")

        assert isinstance(provider, GeminiLLM)


# ============================================================================
# 統合テスト
# ============================================================================
class TestProviderFactoryIntegration:
    def test_full_workflow_get_class_and_create(self):
        """クラス取得→インスタンス作成のワークフロー"""
        # クラス取得
        provider_cls = get_provider_class("openai")
        assert provider_cls == OpenAILLM

        # インスタンス作成
        provider = create_provider("openai:gpt-4")
        assert isinstance(provider, provider_cls)

    def test_all_registered_providers_can_be_created(self):
        """全登録プロバイダーがインスタンス化可能"""
        test_models = {
            "openai": "gpt-4",
            "gemini": "gemini-pro",
            "kimi": "moonshot-v1",
            "anthropic": "claude-3",
            "deepseek": "deepseek-coder",
            "local": "llama-2",
        }

        for family, model in test_models.items():
            # クラス取得
            provider_cls = get_provider_class(family)
            assert issubclass(provider_cls, BaseLLM)

            # インスタンス作成（コロン形式）
            provider = create_provider(f"{family}:{model}")
            assert isinstance(provider, provider_cls)

    def test_provider_class_consistency(self):
        """プロバイダークラスの一貫性"""
        for family in PROVIDER_CLASSES.keys():
            # get_provider_classで取得
            cls_from_get = get_provider_class(family)

            # PROVIDER_CLASSESから直接取得
            cls_from_dict = PROVIDER_CLASSES[family]

            # 同じクラスを返す
            assert cls_from_get == cls_from_dict

    def test_create_provider_model_name_extraction(self):
        """モデル名抽出のテスト"""
        # コロン形式
        provider1 = create_provider("openai:gpt-4-turbo")
        assert isinstance(provider1, OpenAILLM)

        # 接頭辞による推論
        provider2 = create_provider("gpt-4-turbo")
        assert isinstance(provider2, OpenAILLM)

        # 両方とも同じプロバイダー型
        assert type(provider1) is type(provider2)

    def test_error_handling_consistency(self):
        """エラーハンドリングの一貫性"""
        # 存在しないファミリー
        with pytest.raises(ValueError, match="Unsupported"):
            get_provider_class("nonexistent")

        # create_providerでは未知モデルはlocalにフォールバック
        provider = create_provider("nonexistent:model")
        assert isinstance(provider, LocalLLM)

    def test_case_sensitivity_consistency(self):
        """大文字小文字の一貫性"""
        # 小文字のみサポート
        assert get_provider_class("openai") == OpenAILLM

        # 大文字は失敗
        with pytest.raises(ValueError):
            get_provider_class("OPENAI")

    def test_provider_instantiation_with_different_models(self):
        """異なるモデル名でのインスタンス化"""
        models = [
            "openai:gpt-4",
            "openai:gpt-3.5-turbo",
            "gemini:gemini-pro",
            "gemini:gemini-ultra",
            "claude-3-opus",
            "claude-3-sonnet",
        ]

        for model in models:
            provider = create_provider(model)
            assert isinstance(provider, BaseLLM)
