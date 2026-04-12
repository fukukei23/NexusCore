"""
Comprehensive tests for llm/provider_factory.py

プロバイダーファクトリーとクラスマッピングのテスト
NexusCore uses GLM (Zhipu AI) and MiniMax as the sole LLM providers.
"""

import pytest

from nexuscore.llm.provider_factory import (
    PROVIDER_CLASSES,
    create_provider,
    get_provider_class,
)
from nexuscore.llm.providers import (
    BaseLLM,
    GLMLLM,
    MiniMaxLLM,
)


# ============================================================================
# PROVIDER_CLASSES テスト
# ============================================================================
class TestProviderClasses:
    def test_provider_classes_is_dict(self):
        """PROVIDER_CLASSESが辞書"""
        assert isinstance(PROVIDER_CLASSES, dict)

    def test_provider_classes_contains_glm(self):
        """GLMプロバイダーが登録されている"""
        assert "glm" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["glm"] == GLMLLM

    def test_provider_classes_contains_minimax(self):
        """MiniMaxプロバイダーが登録されている"""
        assert "minimax" in PROVIDER_CLASSES
        assert PROVIDER_CLASSES["minimax"] == MiniMaxLLM

    def test_provider_classes_minimum_count(self):
        """最低限のプロバイダー数が登録されている"""
        assert len(PROVIDER_CLASSES) >= 2

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
    def test_get_provider_class_glm(self):
        """GLMプロバイダークラスを取得"""
        provider_cls = get_provider_class("glm")

        assert provider_cls == GLMLLM

    def test_get_provider_class_minimax(self):
        """MiniMaxプロバイダークラスを取得"""
        provider_cls = get_provider_class("minimax")

        assert provider_cls == MiniMaxLLM

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
        assert get_provider_class("glm") == GLMLLM

        # 大文字は失敗
        with pytest.raises(ValueError):
            get_provider_class("GLM")

    def test_get_provider_class_returns_class_not_instance(self):
        """インスタンスではなくクラスを返す"""
        provider_cls = get_provider_class("glm")

        assert isinstance(provider_cls, type)
        assert issubclass(provider_cls, BaseLLM)


# ============================================================================
# create_provider テスト
# ============================================================================
class TestCreateProvider:
    def test_create_provider_glm_with_colon(self):
        """GLMプロバイダーをコロン形式で作成"""
        provider = create_provider("glm:glm-4-plus")

        assert isinstance(provider, GLMLLM)
        assert isinstance(provider, BaseLLM)

    def test_create_provider_minimax_with_colon(self):
        """MiniMaxプロバイダーをコロン形式で作成"""
        provider = create_provider("minimax:minimax-m2.7")

        assert isinstance(provider, MiniMaxLLM)

    def test_create_provider_without_colon_glm(self):
        """コロンなし（glm接頭辞）でGLMプロバイダー作成"""
        provider = create_provider("glm-4-plus")

        assert isinstance(provider, GLMLLM)

    def test_create_provider_without_colon_minimax(self):
        """コロンなし（minimax接頭辞）でMiniMaxプロバイダー作成"""
        provider = create_provider("minimax-m2.7")

        assert isinstance(provider, MiniMaxLLM)

    def test_create_provider_without_colon_chatglm(self):
        """コロンなし（chatglm接頭辞）でGLMプロバイダー作成"""
        provider = create_provider("chatglm-4")

        assert isinstance(provider, GLMLLM)

    def test_create_provider_unknown_model_fallback_glm(self):
        """未知のモデルはGLMプロバイダーにフォールバック"""
        provider = create_provider("unknown-model-xyz")

        assert isinstance(provider, GLMLLM)

    def test_create_provider_returns_base_llm_instance(self):
        """BaseLLMインスタンスを返す"""
        provider = create_provider("glm:glm-4-plus")

        assert isinstance(provider, BaseLLM)


# ============================================================================
# 統合テスト
# ============================================================================
class TestProviderFactoryIntegration:
    def test_full_workflow_get_class_and_create(self):
        """クラス取得→インスタンス作成のワークフロー"""
        # クラス取得
        provider_cls = get_provider_class("glm")
        assert provider_cls == GLMLLM

        # インスタンス作成
        provider = create_provider("glm:glm-4-plus")
        assert isinstance(provider, provider_cls)

    def test_all_registered_providers_can_be_created(self):
        """全登録プロバイダーがインスタンス化可能"""
        test_models = {
            "glm": "glm-4-plus",
            "minimax": "minimax-m2.7",
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
        provider1 = create_provider("glm:glm-4-plus")
        assert isinstance(provider1, GLMLLM)

        # 接頭辞による推論
        provider2 = create_provider("glm-4-plus")
        assert isinstance(provider2, GLMLLM)

        # 両方とも同じプロバイダー型
        assert type(provider1) is type(provider2)

    def test_error_handling_consistency(self):
        """エラーハンドリングの一貫性"""
        # 存在しないファミリー
        with pytest.raises(ValueError, match="Unsupported"):
            get_provider_class("nonexistent")

        # create_providerでは未知モデルはglmにフォールバック
        provider = create_provider("nonexistent:model")
        assert isinstance(provider, GLMLLM)

    def test_case_sensitivity_consistency(self):
        """大文字小文字の一貫性"""
        # 小文字のみサポート
        assert get_provider_class("glm") == GLMLLM

        # 大文字は失敗
        with pytest.raises(ValueError):
            get_provider_class("GLM")

    def test_provider_instantiation_with_different_models(self):
        """異なるモデル名でのインスタンス化"""
        models = [
            "glm:glm-4-plus",
            "glm:glm-4-flash",
            "glm:glm-5.1",
            "minimax:minimax-m2.7",
            "minimax:MiniMax-M2.7",
        ]

        for model in models:
            provider = create_provider(model)
            assert isinstance(provider, BaseLLM)
