"""
Comprehensive tests for llm/llm_profiles.py

LLMプロファイルレジストリとヘルパー関数のテスト
NexusCore uses a multi-provider architecture: GPT-5.5, Sonnet 4.6, Gemini 3.1, GLM-5.1, MiniMax M2.7.
"""

import pytest

from nexuscore.llm.llm_profiles import (
    PROFILE_REGISTRY,
    LLMProfile,
    get_profile,
    profile_ids,
    profile_to_model_name,
)


# ============================================================================
# LLMProfile データクラステスト
# ============================================================================
class TestLLMProfile:
    def test_profile_creation_minimal(self):
        """最小限のパラメータでプロファイル作成"""
        profile = LLMProfile(name="test_profile", provider="openai", model="gpt-5.5")

        assert profile.name == "test_profile"
        assert profile.provider == "openai"
        assert profile.model == "gpt-5.5"
        assert profile.description is None
        assert profile.default_temperature == 0.2

    def test_profile_creation_full(self):
        """全パラメータ指定でプロファイル作成"""
        profile = LLMProfile(
            name="custom",
            provider="minimax",
            model="minimax-m2.7",
            description="Test profile",
            default_temperature=0.5,
        )

        assert profile.name == "custom"
        assert profile.provider == "minimax"
        assert profile.model == "minimax-m2.7"
        assert profile.description == "Test profile"
        assert profile.default_temperature == 0.5

    def test_profile_is_frozen(self):
        """frozenデータクラスのため変更不可"""
        profile = LLMProfile(name="test", provider="glm", model="glm-5.1")

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            profile.name = "new_name"  # type: ignore

    def test_profile_default_temperature(self):
        """デフォルトtemperatureは0.2"""
        profile = LLMProfile(name="test", provider="glm", model="glm-5.1")

        assert profile.default_temperature == 0.2


# ============================================================================
# PROFILE_REGISTRY テスト
# ============================================================================
class TestProfileRegistry:
    def test_registry_contains_openai_profiles(self):
        """OpenAI系プロファイルが登録されている"""
        for profile_id in ["gpt5_codex", "gpt5_strict"]:
            assert profile_id in PROFILE_REGISTRY

    def test_registry_contains_anthropic_profiles(self):
        """Anthropic系プロファイルが登録されている"""
        for profile_id in ["sonnet_review", "sonnet_code"]:
            assert profile_id in PROFILE_REGISTRY

    def test_registry_contains_google_profiles(self):
        """Google系プロファイルが登録されている"""
        assert "gemini_secondary" in PROFILE_REGISTRY

    def test_registry_contains_glm_profiles(self):
        """GLM系プロファイルが登録されている"""
        for profile_id in ["glm_default", "glm_strict"]:
            assert profile_id in PROFILE_REGISTRY

    def test_registry_contains_minimax_profiles(self):
        """MiniMax系プロファイルが登録されている"""
        for profile_id in ["minimax_default", "minimax_analytical"]:
            assert profile_id in PROFILE_REGISTRY

    def test_registry_profile_structure_gpt5_codex(self):
        """gpt5_codexの構造を検証"""
        profile = PROFILE_REGISTRY["gpt5_codex"]

        assert profile.name == "gpt5_codex"
        assert profile.provider == "openai"
        assert profile.model == "gpt-5.5"
        assert profile.description is not None
        assert profile.default_temperature == 0.2

    def test_registry_profile_structure_sonnet_review(self):
        """sonnet_reviewの構造を検証"""
        profile = PROFILE_REGISTRY["sonnet_review"]

        assert profile.name == "sonnet_review"
        assert profile.provider == "anthropic"
        assert profile.model == "claude-sonnet-4-6"
        assert profile.default_temperature == 0.15

    def test_registry_profile_structure_glm_default(self):
        """glm_defaultの構造を検証"""
        profile = PROFILE_REGISTRY["glm_default"]

        assert profile.name == "glm_default"
        assert profile.provider == "glm"
        assert profile.model == "glm-5.1"
        assert profile.description is not None
        assert profile.default_temperature == 0.2

    def test_registry_profile_structure_minimax_default(self):
        """minimax_defaultの構造を検証"""
        profile = PROFILE_REGISTRY["minimax_default"]

        assert profile.name == "minimax_default"
        assert profile.provider == "minimax"
        assert profile.model == "minimax-m2.7"
        assert profile.default_temperature == 0.2

    def test_registry_all_profiles_have_required_fields(self):
        """全プロファイルが必須フィールドを持つ"""
        for profile_id, profile in PROFILE_REGISTRY.items():
            assert profile.name == profile_id
            assert isinstance(profile.provider, str)
            assert len(profile.provider) > 0
            assert isinstance(profile.model, str)
            assert len(profile.model) > 0
            assert isinstance(profile.default_temperature, (int, float))

    def test_registry_no_duplicate_profiles(self):
        """プロファイルの重複がない"""
        profile_names = [p.name for p in PROFILE_REGISTRY.values()]
        assert len(profile_names) == len(set(profile_names))

    def test_registry_minimum_profiles_exist(self):
        """最低限のプロファイル数が存在"""
        # OpenAI×2 + Anthropic×2 + Google×1 + GLM×2 + MiniMax×2 = 9
        assert len(PROFILE_REGISTRY) >= 9


# ============================================================================
# get_profile テスト
# ============================================================================
class TestGetProfile:
    def test_get_profile_existing(self):
        """存在するプロファイルを取得"""
        profile = get_profile("gpt5_codex")

        assert profile is not None
        assert profile.name == "gpt5_codex"

    def test_get_profile_nonexistent(self):
        """存在しないプロファイルはNone"""
        profile = get_profile("nonexistent_profile")

        assert profile is None

    def test_get_profile_all_registry_entries(self):
        """全登録プロファイルが取得可能"""
        for profile_id in PROFILE_REGISTRY.keys():
            profile = get_profile(profile_id)
            assert profile is not None
            assert profile.name == profile_id

    def test_get_profile_case_sensitive(self):
        """大文字小文字を区別する"""
        profile_lower = get_profile("glm_default")
        profile_upper = get_profile("GLM_DEFAULT")

        assert profile_lower is not None
        assert profile_upper is None

    def test_get_profile_empty_string(self):
        """空文字列はNone"""
        profile = get_profile("")

        assert profile is None


# ============================================================================
# profile_ids テスト
# ============================================================================
class TestProfileIds:
    def test_profile_ids_returns_list(self):
        """リストを返す"""
        ids = profile_ids()

        assert isinstance(ids, list)

    def test_profile_ids_contains_known_profiles(self):
        """既知のプロファイルIDを含む"""
        ids = profile_ids()

        assert "gpt5_codex" in ids
        assert "sonnet_review" in ids
        assert "gemini_secondary" in ids
        assert "glm_default" in ids
        assert "minimax_default" in ids

    def test_profile_ids_length_matches_registry(self):
        """レジストリのサイズと一致"""
        ids = profile_ids()

        assert len(ids) == len(PROFILE_REGISTRY)

    def test_profile_ids_all_strings(self):
        """全要素が文字列"""
        ids = profile_ids()

        for profile_id in ids:
            assert isinstance(profile_id, str)
            assert len(profile_id) > 0

    def test_profile_ids_no_duplicates(self):
        """重複がない"""
        ids = profile_ids()

        assert len(ids) == len(set(ids))


# ============================================================================
# profile_to_model_name テスト
# ============================================================================
class TestProfileToModelName:
    def test_profile_to_model_name_gpt5_codex(self):
        """gpt5_codexを正しく変換"""
        model_name = profile_to_model_name("gpt5_codex")

        assert model_name == "openai:gpt-5.5"

    def test_profile_to_model_name_sonnet_review(self):
        """sonnet_reviewを正しく変換"""
        model_name = profile_to_model_name("sonnet_review")

        assert model_name == "anthropic:claude-sonnet-4-6"

    def test_profile_to_model_name_gemini_secondary(self):
        """gemini_secondaryを正しく変換"""
        model_name = profile_to_model_name("gemini_secondary")

        assert model_name == "google:gemini-3.1-pro"

    def test_profile_to_model_name_glm_default(self):
        """glm_defaultを正しく変換"""
        model_name = profile_to_model_name("glm_default")

        assert model_name == "glm:glm-5.1"

    def test_profile_to_model_name_minimax_default(self):
        """minimax_defaultを正しく変換"""
        model_name = profile_to_model_name("minimax_default")

        assert model_name == "minimax:minimax-m2.7"

    def test_profile_to_model_name_all_profiles(self):
        """全プロファイルが変換可能"""
        for profile_id in profile_ids():
            model_name = profile_to_model_name(profile_id)

            assert ":" in model_name
            provider, model = model_name.split(":", 1)
            assert len(provider) > 0
            assert len(model) > 0

    def test_profile_to_model_name_unknown_raises_error(self):
        """存在しないプロファイルはValueError"""
        with pytest.raises(ValueError, match="Unknown LLM profile"):
            profile_to_model_name("unknown_profile")

    def test_profile_to_model_name_empty_raises_error(self):
        """空文字列はValueError"""
        with pytest.raises(ValueError, match="Unknown LLM profile"):
            profile_to_model_name("")

    def test_profile_to_model_name_format(self):
        """provider:model形式を返す"""
        model_name = profile_to_model_name("gpt5_strict")

        assert ":" in model_name
        parts = model_name.split(":")
        assert len(parts) == 2
        assert parts[0] == "openai"
        assert parts[1] == "gpt-5.5"


# ============================================================================
# 統合テスト
# ============================================================================
class TestProfilesIntegration:
    def test_full_workflow_get_and_convert(self):
        """プロファイル取得から変換までの完全ワークフロー"""
        profile = get_profile("sonnet_code")
        assert profile is not None

        model_name = profile_to_model_name("sonnet_code")

        assert model_name == f"{profile.provider}:{profile.model}"
        assert model_name == "anthropic:claude-sonnet-4-6"

    def test_all_profiles_convertible(self):
        """全プロファイルが変換可能であることを統合確認"""
        ids = profile_ids()

        for profile_id in ids:
            profile = get_profile(profile_id)
            assert profile is not None

            model_name = profile_to_model_name(profile_id)
            assert model_name == f"{profile.provider}:{profile.model}"

    def test_profile_registry_consistency(self):
        """レジストリの一貫性チェック"""
        ids = profile_ids()
        registry_keys = list(PROFILE_REGISTRY.keys())

        assert set(ids) == set(registry_keys)

    def test_temperature_range_validity(self):
        """全プロファイルのtemperatureが妥当な範囲"""
        for profile in PROFILE_REGISTRY.values():
            assert 0.0 <= profile.default_temperature <= 2.0
            assert 0.1 <= profile.default_temperature <= 1.0

    def test_providers_are_lowercase(self):
        """プロバイダー名が小文字（一貫性）"""
        for profile in PROFILE_REGISTRY.values():
            assert profile.provider == profile.provider.lower()

    def test_all_providers_are_known(self):
        """全プロバイダーが既知のベンダー"""
        known_providers = {"openai", "anthropic", "google", "glm", "minimax"}
        for profile in PROFILE_REGISTRY.values():
            assert profile.provider in known_providers

    def test_profile_names_match_registry_keys(self):
        """プロファイル名がレジストリキーと一致"""
        for key, profile in PROFILE_REGISTRY.items():
            assert profile.name == key
