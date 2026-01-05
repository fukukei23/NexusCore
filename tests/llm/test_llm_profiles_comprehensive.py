"""
Comprehensive tests for llm/llm_profiles.py

LLMプロファイルレジストリとヘルパー関数のテスト
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
        profile = LLMProfile(
            name="test_profile", provider="openai", model="gpt-4"
        )

        assert profile.name == "test_profile"
        assert profile.provider == "openai"
        assert profile.model == "gpt-4"
        assert profile.description is None
        assert profile.default_temperature == 0.2

    def test_profile_creation_full(self):
        """全パラメータ指定でプロファイル作成"""
        profile = LLMProfile(
            name="custom",
            provider="anthropic",
            model="claude-3",
            description="Test profile",
            default_temperature=0.5,
        )

        assert profile.name == "custom"
        assert profile.provider == "anthropic"
        assert profile.model == "claude-3"
        assert profile.description == "Test profile"
        assert profile.default_temperature == 0.5

    def test_profile_is_frozen(self):
        """frozenデータクラスのため変更不可"""
        profile = LLMProfile(
            name="test", provider="openai", model="gpt-4"
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            profile.name = "new_name"  # type: ignore

    def test_profile_default_temperature(self):
        """デフォルトtemperatureは0.2"""
        profile = LLMProfile(
            name="test", provider="openai", model="gpt-4"
        )

        assert profile.default_temperature == 0.2


# ============================================================================
# PROFILE_REGISTRY テスト
# ============================================================================
class TestProfileRegistry:
    def test_registry_contains_gpt5_profiles(self):
        """GPT-5系プロファイルが登録されている"""
        gpt5_profiles = [
            "gpt5_default",
            "gpt5_strict",
            "gpt5_codex",
            "gpt5_nano",
        ]
        for profile_id in gpt5_profiles:
            assert profile_id in PROFILE_REGISTRY

    def test_registry_contains_claude_profile(self):
        """Claude系プロファイルが登録されている"""
        assert "claude_sonnet_45" in PROFILE_REGISTRY

    def test_registry_contains_gemini_profile(self):
        """Gemini系プロファイルが登録されている"""
        assert "gemini_3_pro" in PROFILE_REGISTRY

    def test_registry_contains_deepseek_profile(self):
        """DeepSeek系プロファイルが登録されている"""
        assert "deepseek_r1" in PROFILE_REGISTRY

    def test_registry_profile_structure_gpt5_default(self):
        """gpt5_defaultの構造を検証"""
        profile = PROFILE_REGISTRY["gpt5_default"]

        assert profile.name == "gpt5_default"
        assert profile.provider == "openai"
        assert profile.model == "gpt-5.1-mini"
        assert "Fast" in profile.description or "fast" in profile.description
        assert profile.default_temperature == 0.2

    def test_registry_profile_structure_claude(self):
        """Claude Sonnet 4.5の構造を検証"""
        profile = PROFILE_REGISTRY["claude_sonnet_45"]

        assert profile.name == "claude_sonnet_45"
        assert profile.provider == "anthropic"
        assert profile.model == "claude-4.5-sonnet"
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
        # 少なくとも7つのプロファイルが定義されているべき
        assert len(PROFILE_REGISTRY) >= 7


# ============================================================================
# get_profile テスト
# ============================================================================
class TestGetProfile:
    def test_get_profile_existing(self):
        """存在するプロファイルを取得"""
        profile = get_profile("gpt5_default")

        assert profile is not None
        assert profile.name == "gpt5_default"

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
        profile_lower = get_profile("gpt5_default")
        profile_upper = get_profile("GPT5_DEFAULT")

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

        assert "gpt5_default" in ids
        assert "claude_sonnet_45" in ids
        assert "gemini_3_pro" in ids
        assert "deepseek_r1" in ids

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
    def test_profile_to_model_name_gpt5_default(self):
        """gpt5_defaultを正しく変換"""
        model_name = profile_to_model_name("gpt5_default")

        assert model_name == "openai:gpt-5.1-mini"

    def test_profile_to_model_name_claude(self):
        """claude_sonnet_45を正しく変換"""
        model_name = profile_to_model_name("claude_sonnet_45")

        assert model_name == "anthropic:claude-4.5-sonnet"

    def test_profile_to_model_name_gemini(self):
        """gemini_3_proを正しく変換"""
        model_name = profile_to_model_name("gemini_3_pro")

        assert model_name == "google:gemini-3.0-pro"

    def test_profile_to_model_name_deepseek(self):
        """deepseek_r1を正しく変換"""
        model_name = profile_to_model_name("deepseek_r1")

        assert model_name == "deepseek:deepseek-r1"

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
        assert parts[0] == "openai"  # provider
        assert parts[1] == "gpt-5.1"  # model


# ============================================================================
# 統合テスト
# ============================================================================
class TestProfilesIntegration:
    def test_full_workflow_get_and_convert(self):
        """プロファイル取得から変換までの完全ワークフロー"""
        # プロファイル取得
        profile = get_profile("gpt5_codex")
        assert profile is not None

        # モデル名に変換
        model_name = profile_to_model_name("gpt5_codex")

        assert model_name == f"{profile.provider}:{profile.model}"
        assert model_name == "openai:gpt-5.1-codex"

    def test_all_profiles_convertible(self):
        """全プロファイルが変換可能であることを統合確認"""
        ids = profile_ids()

        for profile_id in ids:
            # get_profile経由で取得
            profile = get_profile(profile_id)
            assert profile is not None

            # profile_to_model_name経由で変換
            model_name = profile_to_model_name(profile_id)
            assert model_name == f"{profile.provider}:{profile.model}"

    def test_profile_registry_consistency(self):
        """レジストリの一貫性チェック"""
        # profile_ids()の結果とREGISTRYのキーが一致
        ids = profile_ids()
        registry_keys = list(PROFILE_REGISTRY.keys())

        assert set(ids) == set(registry_keys)

    def test_temperature_range_validity(self):
        """全プロファイルのtemperatureが妥当な範囲"""
        for profile in PROFILE_REGISTRY.values():
            assert 0.0 <= profile.default_temperature <= 2.0
            # 一般的には0.15〜0.5の範囲
            assert 0.1 <= profile.default_temperature <= 1.0

    def test_providers_are_lowercase(self):
        """プロバイダー名が小文字（一貫性）"""
        for profile in PROFILE_REGISTRY.values():
            assert profile.provider == profile.provider.lower()

    def test_profile_names_match_registry_keys(self):
        """プロファイル名がレジストリキーと一致"""
        for key, profile in PROFILE_REGISTRY.items():
            assert profile.name == key
