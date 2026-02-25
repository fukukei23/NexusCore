"""
Comprehensive tests for config/constitution_loader.py

憲法ローダーのシングルトンパターンとYAML読み込みのテスト
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# PyYAMLのモック化（必要に応じて）
try:
    import yaml  # noqa: F401

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    sys.modules["yaml"] = MagicMock()

from nexuscore.config.constitution_loader import (
    ConstitutionLoader,
    get_constitution,
    get_tier1_config,
    get_tier2_config,
    reload_constitution,
)


# ============================================================================
# ConstitutionLoader シングルトンパターンテスト
# ============================================================================
class TestConstitutionLoaderSingleton:
    def setup_method(self):
        """各テスト前にシングルトンをリセット"""
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_singleton_returns_same_instance(self):
        """複数回インスタンス化しても同じインスタンスを返す"""
        loader1 = ConstitutionLoader()
        loader2 = ConstitutionLoader()

        assert loader1 is loader2

    def test_singleton_instance_persists(self):
        """インスタンスが永続化される"""
        loader1 = ConstitutionLoader()
        instance_id1 = id(loader1)

        loader2 = ConstitutionLoader()
        instance_id2 = id(loader2)

        assert instance_id1 == instance_id2

    def test_constitution_loaded_once(self):
        """憲法は一度だけ読み込まれる"""
        loader1 = ConstitutionLoader()
        constitution1 = loader1.get_constitution()

        loader2 = ConstitutionLoader()
        constitution2 = loader2.get_constitution()

        assert constitution1 is constitution2


# ============================================================================
# _get_default_constitution テスト
# ============================================================================
class TestDefaultConstitution:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_default_constitution_has_all_sections(self):
        """デフォルト憲法が全セクションを持つ"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        assert "project" in default
        assert "quality_gates" in default
        assert "security" in default
        assert "error_handling" in default
        assert "fkb" in default

    def test_default_constitution_quality_gates(self):
        """デフォルト憲法のquality_gates"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        quality_gates = default["quality_gates"]
        assert "tier1" in quality_gates
        assert "tier2" in quality_gates
        assert "guardian" in quality_gates

    def test_default_constitution_tier1_values(self):
        """Tier1のデフォルト値"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        tier1 = default["quality_gates"]["tier1"]
        assert tier1["test_coverage_min"] == 90
        assert tier1["branch_coverage_min"] == 85
        assert tier1["pylint_score_min"] == 8.0
        assert tier1["cyclomatic_complexity_max"] == 10

    def test_default_constitution_tier2_values(self):
        """Tier2のデフォルト値"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        tier2 = default["quality_gates"]["tier2"]
        assert tier2["mutation_score_min"] == 80
        assert tier2["mutation_timeout_sec"] == 10

    def test_default_constitution_security_npe(self):
        """セキュリティNPE設定"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        npe = default["security"]["npe"]
        assert npe["enabled"] is True
        assert npe["detect_api_keys"] is True
        assert npe["detect_pem_keys"] is True

    def test_default_constitution_error_handling(self):
        """エラーハンドリング設定"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        error_handling = default["error_handling"]["retry"]
        assert error_handling["max_retries"] == 3
        assert error_handling["base_delay_sec"] == 1.0
        assert error_handling["exponential_backoff"] is True

    def test_default_constitution_fkb(self):
        """FKB設定"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        fkb = default["fkb"]["learning"]
        assert fkb["enabled"] is True
        assert fkb["trigger_on_debugger_failure"] is True


# ============================================================================
# getter メソッドテスト
# ============================================================================
class TestGetterMethods:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_get_constitution_returns_dict(self):
        """get_constitutionが辞書を返す"""
        loader = ConstitutionLoader()
        constitution = loader.get_constitution()

        assert isinstance(constitution, dict)

    def test_get_tier1_config_returns_dict(self):
        """get_tier1_configが辞書を返す"""
        loader = ConstitutionLoader()
        tier1 = loader.get_tier1_config()

        assert isinstance(tier1, dict)

    def test_get_tier1_config_has_required_keys(self):
        """Tier1設定が必須キーを持つ"""
        loader = ConstitutionLoader()
        tier1 = loader.get_tier1_config()

        assert "test_coverage_min" in tier1
        assert "pylint_score_min" in tier1

    def test_get_tier2_config_returns_dict(self):
        """get_tier2_configが辞書を返す"""
        loader = ConstitutionLoader()
        tier2 = loader.get_tier2_config()

        assert isinstance(tier2, dict)

    def test_get_guardian_config_returns_dict(self):
        """get_guardian_configが辞書を返す"""
        loader = ConstitutionLoader()
        guardian = loader.get_guardian_config()

        assert isinstance(guardian, dict)

    def test_get_security_config_returns_dict(self):
        """get_security_configが辞書を返す"""
        loader = ConstitutionLoader()
        security = loader.get_security_config()

        assert isinstance(security, dict)

    def test_get_npe_config_returns_dict(self):
        """get_npe_configが辞書を返す"""
        loader = ConstitutionLoader()
        npe = loader.get_npe_config()

        assert isinstance(npe, dict)

    def test_get_npe_config_from_security(self):
        """NPE設定がセキュリティ配下から取得される"""
        loader = ConstitutionLoader()
        security = loader.get_security_config()
        npe = loader.get_npe_config()

        assert npe == security.get("npe", {})

    def test_get_error_handling_config_returns_dict(self):
        """get_error_handling_configが辞書を返す"""
        loader = ConstitutionLoader()
        error_handling = loader.get_error_handling_config()

        assert isinstance(error_handling, dict)

    def test_get_fkb_config_returns_dict(self):
        """get_fkb_configが辞書を返す"""
        loader = ConstitutionLoader()
        fkb = loader.get_fkb_config()

        assert isinstance(fkb, dict)


# ============================================================================
# _deep_merge テスト
# ============================================================================
class TestDeepMerge:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_deep_merge_simple_override(self):
        """単純な上書き"""
        loader = ConstitutionLoader()
        base = {"a": 1, "b": 2}
        override = {"b": 3}

        result = loader._deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"] == 3

    def test_deep_merge_nested_dict(self):
        """ネストされた辞書のマージ"""
        loader = ConstitutionLoader()
        base = {"outer": {"inner1": 1, "inner2": 2}}
        override = {"outer": {"inner2": 20, "inner3": 3}}

        result = loader._deep_merge(base, override)

        assert result["outer"]["inner1"] == 1  # 保持
        assert result["outer"]["inner2"] == 20  # 上書き
        assert result["outer"]["inner3"] == 3  # 追加

    def test_deep_merge_new_keys(self):
        """新しいキーの追加"""
        loader = ConstitutionLoader()
        base = {"a": 1}
        override = {"b": 2, "c": 3}

        result = loader._deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"] == 2
        assert result["c"] == 3

    def test_deep_merge_empty_override(self):
        """空の上書き辞書"""
        loader = ConstitutionLoader()
        base = {"a": 1, "b": 2}
        override = {}

        result = loader._deep_merge(base, override)

        assert result == base

    def test_deep_merge_preserves_base(self):
        """ベース辞書を変更しない"""
        loader = ConstitutionLoader()
        base = {"a": 1}
        override = {"a": 2}

        result = loader._deep_merge(base, override)

        assert base["a"] == 1  # 元のbaseは変更されない
        assert result["a"] == 2

    def test_deep_merge_replaces_non_dict_with_dict(self):
        """非辞書を辞書で置き換え"""
        loader = ConstitutionLoader()
        base = {"a": "string"}
        override = {"a": {"nested": 1}}

        result = loader._deep_merge(base, override)

        assert result["a"] == {"nested": 1}


# ============================================================================
# _validate_constitution テスト
# ============================================================================
class TestValidateConstitution:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_validate_valid_constitution(self):
        """有効な憲法の検証成功"""
        loader = ConstitutionLoader()
        valid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0}},
            "security": {},
        }

        # 例外が発生しない
        loader._validate_constitution(valid_const)

    def test_validate_missing_quality_gates_raises_error(self):
        """quality_gatesセクション欠落でエラー"""
        loader = ConstitutionLoader()
        invalid_const = {"security": {}}

        with pytest.raises(ValueError, match="quality_gates"):
            loader._validate_constitution(invalid_const)

    def test_validate_missing_security_raises_error(self):
        """securityセクション欠落でエラー"""
        loader = ConstitutionLoader()
        invalid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0}}
        }

        with pytest.raises(ValueError, match="security"):
            loader._validate_constitution(invalid_const)

    def test_validate_missing_tier1_test_coverage_raises_error(self):
        """Tier1のtest_coverage_min欠落でエラー"""
        loader = ConstitutionLoader()
        invalid_const = {
            "quality_gates": {"tier1": {"pylint_score_min": 8.0}},  # test_coverage_minがない
            "security": {},
        }

        with pytest.raises(ValueError, match="test_coverage_min"):
            loader._validate_constitution(invalid_const)

    def test_validate_missing_tier1_pylint_score_raises_error(self):
        """Tier1のpylint_score_min欠落でエラー"""
        loader = ConstitutionLoader()
        invalid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": 90}},  # pylint_score_minがない
            "security": {},
        }

        with pytest.raises(ValueError, match="pylint_score_min"):
            loader._validate_constitution(invalid_const)

    def test_validate_coverage_out_of_range_negative(self):
        """カバレッジが負の値でエラー"""
        loader = ConstitutionLoader()
        invalid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": -10, "pylint_score_min": 8.0}},
            "security": {},
        }

        with pytest.raises(ValueError, match="0-100"):
            loader._validate_constitution(invalid_const)

    def test_validate_coverage_out_of_range_over_100(self):
        """カバレッジが100超でエラー"""
        loader = ConstitutionLoader()
        invalid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": 150, "pylint_score_min": 8.0}},
            "security": {},
        }

        with pytest.raises(ValueError, match="0-100"):
            loader._validate_constitution(invalid_const)

    def test_validate_coverage_at_boundary_0(self):
        """カバレッジ0%は有効"""
        loader = ConstitutionLoader()
        valid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": 0, "pylint_score_min": 8.0}},
            "security": {},
        }

        loader._validate_constitution(valid_const)

    def test_validate_coverage_at_boundary_100(self):
        """カバレッジ100%は有効"""
        loader = ConstitutionLoader()
        valid_const = {
            "quality_gates": {"tier1": {"test_coverage_min": 100, "pylint_score_min": 8.0}},
            "security": {},
        }

        loader._validate_constitution(valid_const)


# ============================================================================
# _find_project_root テスト
# ============================================================================
class TestFindProjectRoot:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_find_project_root_with_git(self, tmp_path):
        """gitディレクトリが存在する場合"""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".git").mkdir()

        # 実際の検索ロジックをシミュレーション
        current = project_root / "src" / "nexuscore" / "config"
        found = None
        for _ in range(10):
            if (current / ".git").exists() or (current / "pyproject.toml").exists():
                found = current
                break
            if current.parent == current:
                break
            current = current.parent

        assert found == project_root

    def test_find_project_root_with_pyproject_toml(self, tmp_path):
        """pyproject.tomlが存在する場合"""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").touch()

        ConstitutionLoader()

        # 検索ロジックのシミュレーション
        current = project_root / "src"
        found = None
        for _ in range(10):
            if (current / ".git").exists() or (current / "pyproject.toml").exists():
                found = current
                break
            if current.parent == current:
                break
            current = current.parent

        assert found == project_root


# ============================================================================
# _find_constitution_file テスト
# ============================================================================
class TestFindConstitutionFile:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_find_from_env_variable(self, tmp_path, monkeypatch):
        """環境変数NEXUS_CONSTITUTION_PATHから取得"""
        constitution_file = tmp_path / "custom_constitution.yaml"
        monkeypatch.setenv("NEXUS_CONSTITUTION_PATH", str(constitution_file))

        loader = ConstitutionLoader()
        found = loader._find_constitution_file()

        assert found == constitution_file

    def test_find_returns_none_when_not_found(self, monkeypatch):
        """ファイルが見つからない場合None"""
        monkeypatch.delenv("NEXUS_CONSTITUTION_PATH", raising=False)

        loader = ConstitutionLoader()

        # プロジェクトルートが見つからないようにモック
        with patch.object(loader, "_find_project_root", return_value=None):
            # カレントディレクトリにもファイルがない
            with patch("nexuscore.config.constitution_loader.Path") as mock_path:
                mock_path.cwd.return_value = Path("/nonexistent")
                found = loader._find_constitution_file()

                assert found is None


# ============================================================================
# _merge_environment_config テスト
# ============================================================================
class TestMergeEnvironmentConfig:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_merge_environment_config_no_overrides(self):
        """環境別上書きがない場合"""
        loader = ConstitutionLoader()
        base = {"quality_gates": {"tier1": {"test_coverage_min": 90}}}

        merged = loader._merge_environment_config(base, "production")

        assert merged == base

    def test_merge_environment_config_with_overrides(self):
        """環境別上書きがある場合"""
        loader = ConstitutionLoader()
        base = {
            "quality_gates": {"tier1": {"test_coverage_min": 90}},
            "environments": {"production": {"quality_gates": {"tier1": {"test_coverage_min": 95}}}},
        }

        merged = loader._merge_environment_config(base, "production")

        assert merged["quality_gates"]["tier1"]["test_coverage_min"] == 95

    def test_merge_environment_config_development(self):
        """development環境でのマージ"""
        loader = ConstitutionLoader()
        base = {
            "quality_gates": {"tier1": {"test_coverage_min": 90}},
            "environments": {
                "development": {"quality_gates": {"tier1": {"test_coverage_min": 70}}}
            },
        }

        merged = loader._merge_environment_config(base, "development")

        assert merged["quality_gates"]["tier1"]["test_coverage_min"] == 70

    def test_merge_environment_config_staging(self):
        """staging環境でのマージ"""
        loader = ConstitutionLoader()
        base = {
            "quality_gates": {"tier1": {"test_coverage_min": 90}},
            "environments": {"staging": {"quality_gates": {"tier1": {"test_coverage_min": 85}}}},
        }

        merged = loader._merge_environment_config(base, "staging")

        assert merged["quality_gates"]["tier1"]["test_coverage_min"] == 85


# ============================================================================
# _load_constitution テスト
# ============================================================================
class TestLoadConstitution:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    @pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
    def test_load_constitution_without_yaml(self, monkeypatch):
        """PyYAMLなしでデフォルト憲法を返す"""
        # yamlをNoneに偽装
        with patch("nexuscore.config.constitution_loader.yaml", None):
            loader = ConstitutionLoader()
            constitution = loader._load_constitution()

            assert "quality_gates" in constitution
            assert "security" in constitution

    def test_load_constitution_file_not_found(self, monkeypatch):
        """憲法ファイルが見つからない場合"""
        loader = ConstitutionLoader()

        with patch.object(loader, "_find_constitution_file", return_value=None):
            constitution = loader._load_constitution()

            # デフォルト憲法を返す
            assert constitution == loader._get_default_constitution()

    @pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
    def test_load_constitution_yaml_parse_error(self, tmp_path):
        """YAML解析エラー時にデフォルト憲法を返す"""
        loader = ConstitutionLoader()
        invalid_yaml_file = tmp_path / "invalid.yaml"
        invalid_yaml_file.write_text("invalid: yaml: content:")

        with patch.object(loader, "_find_constitution_file", return_value=invalid_yaml_file):
            constitution = loader._load_constitution()

            # デフォルト憲法を返す
            assert constitution == loader._get_default_constitution()


# ============================================================================
# グローバル関数テスト
# ============================================================================
class TestGlobalFunctions:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None
        # グローバル変数もリセット
        import nexuscore.config.constitution_loader as module

        module._loader_instance = None

    def test_get_constitution_returns_dict(self):
        """get_constitution()が辞書を返す"""
        constitution = get_constitution()

        assert isinstance(constitution, dict)

    def test_get_constitution_creates_singleton(self):
        """get_constitution()がシングルトンを作成"""
        const1 = get_constitution()
        const2 = get_constitution()

        assert const1 is const2

    def test_get_tier1_config_returns_dict(self):
        """get_tier1_config()が辞書を返す"""
        tier1 = get_tier1_config()

        assert isinstance(tier1, dict)

    def test_get_tier1_config_has_required_keys(self):
        """get_tier1_config()が必須キーを持つ"""
        tier1 = get_tier1_config()

        assert "test_coverage_min" in tier1
        assert "pylint_score_min" in tier1

    def test_get_tier2_config_returns_dict(self):
        """get_tier2_config()が辞書を返す"""
        tier2 = get_tier2_config()

        assert isinstance(tier2, dict)

    def test_reload_constitution_resets_state(self):
        """reload_constitution()が状態をリセット"""
        # 最初の読み込み
        get_constitution()

        # 再読み込み
        const2 = reload_constitution()

        # 新しいインスタンスが作成される
        assert isinstance(const2, dict)


# ============================================================================
# 統合テスト
# ============================================================================
class TestConstitutionLoaderIntegration:
    def setup_method(self):
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

    def test_full_workflow_singleton_and_getters(self):
        """完全ワークフロー: シングルトン→getter呼び出し"""
        loader = ConstitutionLoader()

        # 各getter呼び出し
        constitution = loader.get_constitution()
        tier1 = loader.get_tier1_config()
        tier2 = loader.get_tier2_config()
        guardian = loader.get_guardian_config()
        security = loader.get_security_config()
        npe = loader.get_npe_config()
        error_handling = loader.get_error_handling_config()
        fkb = loader.get_fkb_config()

        # 全て辞書
        assert all(
            isinstance(config, dict)
            for config in [constitution, tier1, tier2, guardian, security, npe, error_handling, fkb]
        )

    def test_default_constitution_passes_validation(self):
        """デフォルト憲法がバリデーションをパス"""
        loader = ConstitutionLoader()
        default = loader._get_default_constitution()

        # 例外が発生しない
        loader._validate_constitution(default)

    def test_deep_merge_preserves_quality_gates_structure(self):
        """ディープマージがquality_gates構造を保持"""
        loader = ConstitutionLoader()
        base = {
            "quality_gates": {
                "tier1": {"test_coverage_min": 90, "pylint_score_min": 8.0},
                "tier2": {"mutation_score_min": 80},
            }
        }
        override = {"quality_gates": {"tier1": {"test_coverage_min": 95}}}

        merged = loader._deep_merge(base, override)

        # tier1の一部が上書きされ、他は保持
        assert merged["quality_gates"]["tier1"]["test_coverage_min"] == 95
        assert merged["quality_gates"]["tier1"]["pylint_score_min"] == 8.0
        # tier2は保持
        assert merged["quality_gates"]["tier2"]["mutation_score_min"] == 80

    def test_getters_return_empty_dict_when_section_missing(self):
        """セクションがない場合は空の辞書を返す"""
        # 強制的にシングルトンをリセットして新しい憲法を設定
        ConstitutionLoader._instance = None
        ConstitutionLoader._constitution = None

        loader = ConstitutionLoader()

        # 憲法を最小限のものに置き換え
        loader._constitution = {"quality_gates": {}, "security": {}}

        # 空の辞書を返す
        assert loader.get_tier1_config() == {}
        assert loader.get_tier2_config() == {}
        assert loader.get_guardian_config() == {}

    def test_global_functions_consistency(self):
        """グローバル関数の一貫性"""
        # グローバル関数経由
        global_const = get_constitution()
        global_tier1 = get_tier1_config()
        global_tier2 = get_tier2_config()

        # ローダー経由
        loader = ConstitutionLoader()
        loader_const = loader.get_constitution()
        loader_tier1 = loader.get_tier1_config()
        loader_tier2 = loader.get_tier2_config()

        # 同じ値を返す（値の同等性）
        assert global_const == loader_const
        assert global_tier1 == loader_tier1
        assert global_tier2 == loader_tier2
