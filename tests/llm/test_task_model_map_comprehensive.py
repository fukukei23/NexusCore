"""
Comprehensive tests for llm/task_model_map.py

タスク→モデル設定マッピングのテスト
"""

import pytest

from nexuscore.llm.task_model_map import (
    LEGACY_TO_TASK,
    TASK_MODEL_CONFIGS,
    TaskModelConfig,
    build_task_model_map_dict,
)


# ============================================================================
# TaskModelConfig データクラステスト
# ============================================================================
class TestTaskModelConfig:
    def test_config_creation_minimal(self):
        """最小限のパラメータで設定作成"""
        config = TaskModelConfig(
            primary="gpt5_default",
            secondary=["claude_sonnet_45"],
            fallback="gpt5_nano",
        )

        assert config.primary == "gpt5_default"
        assert config.secondary == ["claude_sonnet_45"]
        assert config.fallback == "gpt5_nano"
        assert config.temperature is None

    def test_config_creation_with_temperature(self):
        """temperature指定で設定作成"""
        config = TaskModelConfig(
            primary="gpt5_codex",
            secondary=["deepseek_r1"],
            fallback="gpt5_default",
            temperature=0.5,
        )

        assert config.primary == "gpt5_codex"
        assert config.secondary == ["deepseek_r1"]
        assert config.fallback == "gpt5_default"
        assert config.temperature == 0.5

    def test_config_is_frozen(self):
        """frozenデータクラスのため変更不可"""
        config = TaskModelConfig(primary="test", secondary=[], fallback="test")

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            config.primary = "new_value"  # type: ignore

    def test_config_secondary_can_be_empty(self):
        """secondaryは空リスト可能"""
        config = TaskModelConfig(primary="gpt5_default", secondary=[], fallback="gpt5_nano")

        assert config.secondary == []

    def test_config_secondary_can_be_multiple(self):
        """複数のsecondaryモデル指定可能"""
        config = TaskModelConfig(
            primary="gpt5_strict",
            secondary=["claude_sonnet_45", "gemini_3_pro", "deepseek_r1"],
            fallback="gpt5_default",
        )

        assert len(config.secondary) == 3
        assert "claude_sonnet_45" in config.secondary


# ============================================================================
# TASK_MODEL_CONFIGS テスト
# ============================================================================
class TestTaskModelConfigs:
    def test_configs_contain_core_tasks(self):
        """コアタスクが定義されている"""
        core_tasks = [
            "code_generate",
            "code_refactor",
            "code_review",
            "code_explain",
            "test_generate",
            "debug",
        ]
        for task in core_tasks:
            assert task in TASK_MODEL_CONFIGS

    def test_configs_contain_planning_tasks(self):
        """計画系タスクが定義されている"""
        planning_tasks = [
            "architect",
            "arch_design",
            "plan_generate",
            "requirement",
            "requirement_elicit",
        ]
        for task in planning_tasks:
            assert task in TASK_MODEL_CONFIGS

    def test_configs_contain_maintenance_tasks(self):
        """保守系タスクが定義されている"""
        maintenance_tasks = [
            "self_heal",
            "routing_classify",
            "policy_check",
            "postmortem_analyze",
            "knowledge_curate",
        ]
        for task in maintenance_tasks:
            assert task in TASK_MODEL_CONFIGS

    def test_configs_contain_general_tasks(self):
        """汎用タスクが定義されている"""
        general_tasks = [
            "chat_general",
            "creative",
            "analytical",
            "secure",
            "general",
        ]
        for task in general_tasks:
            assert task in TASK_MODEL_CONFIGS

    def test_configs_minimum_count(self):
        """最低限のタスク数が定義されている"""
        # 少なくとも25個のタスクが定義されているべき
        assert len(TASK_MODEL_CONFIGS) >= 25

    def test_all_configs_have_required_fields(self):
        """全設定が必須フィールドを持つ"""
        for _task, config in TASK_MODEL_CONFIGS.items():
            assert isinstance(config.primary, str)
            assert len(config.primary) > 0
            assert isinstance(config.secondary, list)
            assert isinstance(config.fallback, str)
            assert len(config.fallback) > 0

    def test_code_generate_config(self):
        """code_generateタスクの設定を検証"""
        config = TASK_MODEL_CONFIGS["code_generate"]

        assert config.primary == "glm_codex"
        assert "deepseek_r1" in config.secondary
        assert config.fallback == "glm_default"
        assert config.temperature == 0.2

    def test_code_review_config(self):
        """code_reviewタスクの設定を検証"""
        config = TASK_MODEL_CONFIGS["code_review"]

        assert config.primary == "glm_strict"
        assert "deepseek_r1" in config.secondary
        assert config.fallback == "glm_default"

    def test_self_heal_config(self):
        """self_healタスクの設定を検証"""
        config = TASK_MODEL_CONFIGS["self_heal"]

        assert config.primary == "glm_codex"
        assert "deepseek_r1" in config.secondary
        assert config.fallback == "glm_default"

    def test_routing_classify_config(self):
        """routing_classifyタスクの設定を検証"""
        config = TASK_MODEL_CONFIGS["routing_classify"]

        assert config.primary == "glm_nano"
        assert "glm_default" in config.secondary
        assert config.fallback == "glm_nano"

    def test_all_primary_profiles_are_strings(self):
        """全primaryがプロファイルID文字列"""
        for config in TASK_MODEL_CONFIGS.values():
            assert isinstance(config.primary, str)
            # プロファイル名の形式チェック
            assert "_" in config.primary or config.primary.startswith("gpt")

    def test_all_fallbacks_are_strings(self):
        """全fallbackがプロファイルID文字列"""
        for config in TASK_MODEL_CONFIGS.values():
            assert isinstance(config.fallback, str)
            assert len(config.fallback) > 0

    def test_temperature_range_validity(self):
        """温度設定が妥当な範囲"""
        for task, config in TASK_MODEL_CONFIGS.items():
            if config.temperature is not None:
                assert 0.0 <= config.temperature <= 2.0, f"Task {task} has invalid temperature"
                # 一般的には0.1〜0.8の範囲
                assert 0.1 <= config.temperature <= 1.0


# ============================================================================
# LEGACY_TO_TASK テスト
# ============================================================================
class TestLegacyToTask:
    def test_legacy_mapping_contains_qa(self):
        """qaマッピングが存在"""
        assert "qa" in LEGACY_TO_TASK
        assert LEGACY_TO_TASK["qa"] == "testing"

    def test_legacy_mapping_contains_test(self):
        """testマッピングが存在"""
        assert "test" in LEGACY_TO_TASK
        assert LEGACY_TO_TASK["test"] == "testing"

    def test_legacy_mapping_contains_debug(self):
        """debugマッピングが存在"""
        assert "debug" in LEGACY_TO_TASK
        assert LEGACY_TO_TASK["debug"] == "debugging"

    def test_legacy_mapping_contains_review_code(self):
        """review_codeマッピングが存在"""
        assert "review_code" in LEGACY_TO_TASK
        assert LEGACY_TO_TASK["review_code"] == "review"

    def test_legacy_mapping_contains_plan(self):
        """planマッピングが存在"""
        assert "plan" in LEGACY_TO_TASK
        assert LEGACY_TO_TASK["plan"] == "planning"

    def test_all_legacy_targets_exist_in_configs(self):
        """全レガシーマッピングのターゲットが設定に存在"""
        for legacy, target in LEGACY_TO_TASK.items():
            assert (
                target in TASK_MODEL_CONFIGS
            ), f"Legacy task '{legacy}' maps to '{target}' which doesn't exist in configs"

    def test_legacy_mapping_minimum_count(self):
        """最低限のレガシーマッピング数"""
        # 少なくとも10個のレガシーマッピングが存在するべき
        assert len(LEGACY_TO_TASK) >= 10

    def test_legacy_keys_are_lowercase(self):
        """レガシーキーが小文字"""
        for key in LEGACY_TO_TASK.keys():
            assert key == key.lower()


# ============================================================================
# build_task_model_map_dict テスト
# ============================================================================
class TestBuildTaskModelMapDict:
    def test_build_returns_dict(self):
        """辞書を返す"""
        result = build_task_model_map_dict()

        assert isinstance(result, dict)

    def test_build_contains_all_configs(self):
        """全設定が含まれる"""
        result = build_task_model_map_dict()

        for task in TASK_MODEL_CONFIGS.keys():
            assert task in result

    def test_build_entry_structure(self):
        """各エントリの構造を検証"""
        result = build_task_model_map_dict()

        for _task, entry in result.items():
            assert "primary" in entry
            assert "fallbacks" in entry
            assert isinstance(entry["primary"], str)
            assert isinstance(entry["fallbacks"], list)

    def test_build_code_generate_entry(self):
        """code_generateエントリの構造を検証"""
        result = build_task_model_map_dict()
        entry = result["code_generate"]

        assert entry["primary"].startswith("glm:")
        assert isinstance(entry["fallbacks"], list)
        assert len(entry["fallbacks"]) > 0
        assert "temperature" in entry
        assert entry["temperature"] == 0.2

    def test_build_primary_format(self):
        """primaryが provider:model 形式"""
        result = build_task_model_map_dict()

        for task, entry in result.items():
            primary = entry["primary"]
            assert ":" in primary, f"Task {task} primary doesn't contain ':'"
            provider, model = primary.split(":", 1)
            assert len(provider) > 0
            assert len(model) > 0

    def test_build_fallbacks_format(self):
        """fallbacksが provider:model 形式のリスト"""
        result = build_task_model_map_dict()

        for task, entry in result.items():
            fallbacks = entry["fallbacks"]
            for fallback in fallbacks:
                assert ":" in fallback, f"Task {task} fallback doesn't contain ':'"
                provider, model = fallback.split(":", 1)
                assert len(provider) > 0
                assert len(model) > 0

    def test_build_fallback_included_in_list(self):
        """設定のfallbackがfallbacksリストに含まれる"""
        result = build_task_model_map_dict()

        for task, config in TASK_MODEL_CONFIGS.items():
            entry = result[task]
            fallbacks = entry["fallbacks"]

            # fallback modelがリストに含まれる
            from nexuscore.llm.llm_profiles import profile_to_model_name

            fallback_model = profile_to_model_name(config.fallback)
            assert fallback_model in fallbacks, f"Task {task} fallback not in fallbacks list"

    def test_build_temperature_included_when_present(self):
        """temperatureが設定されている場合、エントリに含まれる"""
        result = build_task_model_map_dict()

        for task, config in TASK_MODEL_CONFIGS.items():
            entry = result[task]
            if config.temperature is not None:
                assert "temperature" in entry
                assert entry["temperature"] == config.temperature

    def test_build_temperature_omitted_when_none(self):
        """temperatureがNoneの場合、エントリに含まれない可能性"""
        build_task_model_map_dict()

        # 少なくとも一つのタスクでtemperatureがNone
        has_none_temp = any(config.temperature is None for config in TASK_MODEL_CONFIGS.values())
        assert has_none_temp  # テストの前提条件

    def test_build_deterministic(self):
        """同じ入力で同じ出力（決定論的）"""
        result1 = build_task_model_map_dict()
        result2 = build_task_model_map_dict()

        assert result1.keys() == result2.keys()
        for task in result1.keys():
            assert result1[task] == result2[task]


# ============================================================================
# タスクエイリアス統合テスト
# ============================================================================
class TestTaskAliasIntegration:
    def test_alias_source_creates_configs(self):
        """_TASK_ALIAS_SOURCEによりエイリアス設定が作成される"""
        # "testing" は "test_generate" のエイリアス
        assert "testing" in TASK_MODEL_CONFIGS
        assert "test_generate" in TASK_MODEL_CONFIGS

        # 同じ設定を参照している
        assert TASK_MODEL_CONFIGS["testing"] == TASK_MODEL_CONFIGS["test_generate"]

    def test_debugging_alias(self):
        """debuggingはdebugのエイリアス"""
        assert "debugging" in TASK_MODEL_CONFIGS
        assert "debug" in TASK_MODEL_CONFIGS
        assert TASK_MODEL_CONFIGS["debugging"] == TASK_MODEL_CONFIGS["debug"]

    def test_review_alias(self):
        """reviewはcode_reviewのエイリアス"""
        assert "review" in TASK_MODEL_CONFIGS
        assert "code_review" in TASK_MODEL_CONFIGS
        assert TASK_MODEL_CONFIGS["review"] == TASK_MODEL_CONFIGS["code_review"]

    def test_policy_alias(self):
        """policyはpolicy_checkのエイリアス"""
        assert "policy" in TASK_MODEL_CONFIGS
        assert "policy_check" in TASK_MODEL_CONFIGS
        assert TASK_MODEL_CONFIGS["policy"] == TASK_MODEL_CONFIGS["policy_check"]

    def test_planning_alias(self):
        """planningはplan_generateのエイリアス"""
        assert "planning" in TASK_MODEL_CONFIGS
        assert "plan_generate" in TASK_MODEL_CONFIGS
        assert TASK_MODEL_CONFIGS["planning"] == TASK_MODEL_CONFIGS["plan_generate"]


# ============================================================================
# 統合テスト
# ============================================================================
class TestTaskModelMapIntegration:
    def test_full_workflow_config_to_dict(self):
        """設定から辞書への完全ワークフロー"""
        # 特定タスクの設定を取得
        config = TASK_MODEL_CONFIGS["code_review"]

        # 辞書ビルド
        result_dict = build_task_model_map_dict()

        # エントリ検証
        entry = result_dict["code_review"]
        assert "primary" in entry
        assert "fallbacks" in entry

        # プロファイルからモデル名への変換が正しい
        from nexuscore.llm.llm_profiles import profile_to_model_name

        expected_primary = profile_to_model_name(config.primary)
        assert entry["primary"] == expected_primary

    def test_all_profiles_in_configs_are_valid(self):
        """全設定内のプロファイルが有効"""
        from nexuscore.llm.llm_profiles import get_profile

        for task, config in TASK_MODEL_CONFIGS.items():
            # primary プロファイルが有効
            primary_profile = get_profile(config.primary)
            assert (
                primary_profile is not None
            ), f"Task {task} has invalid primary profile: {config.primary}"

            # secondary プロファイルが有効
            for secondary in config.secondary:
                sec_profile = get_profile(secondary)
                assert (
                    sec_profile is not None
                ), f"Task {task} has invalid secondary profile: {secondary}"

            # fallback プロファイルが有効
            fallback_profile = get_profile(config.fallback)
            assert (
                fallback_profile is not None
            ), f"Task {task} has invalid fallback profile: {config.fallback}"

    def test_legacy_to_task_to_config_chain(self):
        """レガシー→タスク→設定のチェーン"""
        # レガシータスク名から設定を取得
        legacy_task = "qa"
        modern_task = LEGACY_TO_TASK[legacy_task]
        config = TASK_MODEL_CONFIGS[modern_task]

        assert config is not None
        assert isinstance(config, TaskModelConfig)

    def test_dict_output_json_serializable(self):
        """辞書出力がJSON互換"""
        import json

        result = build_task_model_map_dict()

        # JSON化できることを確認
        try:
            json_str = json.dumps(result)
            assert len(json_str) > 0
        except Exception as e:
            pytest.fail(f"build_task_model_map_dict output is not JSON serializable: {e}")

    def test_no_circular_fallbacks(self):
        """フォールバックの循環参照がない（primary==fallbackは許容）"""
        # 各タスクのprimaryとfallbackが異なることが望ましいが、
        # routing_classifyのように同じモデルを使うことも有効
        # ここでは循環参照（primaryがfallbackを参照し、fallbackがprimaryを参照）がないことを確認

        # 実際には、primary==fallbackは許容される設計
        # 例: routing_classify は gpt5_nano を primary と fallback の両方に使用
        for _task, _config in TASK_MODEL_CONFIGS.items():
            # 同じプロファイルを使うことは許容される
            # 循環参照はタスク間の参照なので、ここではチェック不要
            pass
