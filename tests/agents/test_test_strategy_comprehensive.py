"""
test_strategy.py の包括的テスト

カバレッジ:
- TestStrategyManager: テスト戦略管理
  - __init__: 設定ファイル読み込み
  - _load_config: YAML設定パース
  - get_strategy: モジュール戦略取得
  - should_generate_tests_automatically: AI先行判定
  - requires_human_review: 人間レビュー必要性判定
  - get_min_coverage: 目標カバレッジ取得
  - get_critical_modules: クリティカルモジュール取得
  - get_modules_by_risk: リスクランク別モジュール取得
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from nexuscore.agents.test_strategy import (
        TestStrategyManager,
        TestStrategyConfig,
        ModuleTestStrategy
    )
    HAS_TEST_STRATEGY = True
except ImportError:
    HAS_TEST_STRATEGY = False
    TestStrategyManager = None


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestModuleTestStrategy:
    """ModuleTestStrategy データクラスのテスト"""

    def test_module_test_strategy_creation(self):
        """ModuleTestStrategyの作成"""
        strategy = ModuleTestStrategy(
            module_name="sandbox_runner",
            risk="S",
            strategy="human_design + ai_augment",
            description="Critical sandbox module",
            min_coverage=95
        )

        assert strategy.module_name == "sandbox_runner"
        assert strategy.risk == "S"
        assert strategy.min_coverage == 95

    def test_requires_human_review_property(self):
        """requires_human_reviewプロパティ"""
        strategy_s = ModuleTestStrategy(risk="S", strategy="strategy", description="desc", min_coverage=90, module_name="mod")
        strategy_a = ModuleTestStrategy(risk="A", strategy="strategy", description="desc", min_coverage=80, module_name="mod")
        strategy_b = ModuleTestStrategy(risk="B", strategy="strategy", description="desc", min_coverage=60, module_name="mod")

        assert strategy_s.requires_human_review is True
        assert strategy_a.requires_human_review is True
        assert strategy_b.requires_human_review is False

    def test_is_critical_property(self):
        """is_criticalプロパティ"""
        strategy_s = ModuleTestStrategy(risk="S", strategy="strategy", description="desc", min_coverage=95, module_name="mod")
        strategy_a = ModuleTestStrategy(risk="A", strategy="strategy", description="desc", min_coverage=80, module_name="mod")

        assert strategy_s.is_critical is True
        assert strategy_a.is_critical is False

    def test_allows_ai_first_property(self):
        """allows_ai_firstプロパティ"""
        strategy1 = ModuleTestStrategy(risk="S", strategy="human_design + ai_augment", description="desc", min_coverage=95, module_name="mod")
        strategy2 = ModuleTestStrategy(risk="A", strategy="ai_first + human_review", description="desc", min_coverage=80, module_name="mod")
        strategy3 = ModuleTestStrategy(risk="B", strategy="ai_first_only", description="desc", min_coverage=60, module_name="mod")

        assert strategy1.allows_ai_first is False
        assert strategy2.allows_ai_first is True
        assert strategy3.allows_ai_first is True


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestTestStrategyConfig:
    """TestStrategyConfig データクラスのテスト"""

    def test_config_creation(self):
        """TestStrategyConfigの作成"""
        modules = {
            "sandbox_runner": ModuleTestStrategy(risk="S", strategy="human_design + ai_augment", description="Critical", min_coverage=95, module_name="sandbox_runner")
        }
        config = TestStrategyConfig(
            modules=modules,
            default_risk="B",
            default_strategy="ai_first_only",
            default_min_coverage=60
        )

        assert len(config.modules) == 1
        assert config.default_risk == "B"
        assert config.default_min_coverage == 60

    def test_get_strategy_existing_module(self):
        """既存モジュールの戦略取得"""
        strategy = ModuleTestStrategy(risk="A", strategy="ai_first + human_review", description="Test", min_coverage=80, module_name="test_mod")
        modules = {"test_mod": strategy}
        config = TestStrategyConfig(modules=modules)

        result = config.get_strategy("test_mod")

        assert result.module_name == "test_mod"
        assert result.risk == "A"

    def test_get_strategy_default_for_unknown_module(self):
        """未知のモジュールにはデフォルト戦略を返す"""
        config = TestStrategyConfig(
            modules={},
            default_risk="B",
            default_strategy="ai_first_only",
            default_min_coverage=60
        )

        result = config.get_strategy("unknown_module")

        assert result.module_name == "unknown_module"
        assert result.risk == "B"
        assert result.strategy == "ai_first_only"
        assert result.min_coverage == 60

    def test_get_modules_by_risk(self):
        """リスクランク別モジュール取得"""
        modules = {
            "mod_s": ModuleTestStrategy(risk="S", strategy="strategy", description="desc", min_coverage=95, module_name="mod_s"),
            "mod_a": ModuleTestStrategy(risk="A", strategy="strategy", description="desc", min_coverage=80, module_name="mod_a"),
            "mod_b": ModuleTestStrategy(risk="B", strategy="strategy", description="desc", min_coverage=60, module_name="mod_b")
        }
        config = TestStrategyConfig(modules=modules)

        s_modules = config.get_modules_by_risk("S")
        a_modules = config.get_modules_by_risk("A")

        assert "mod_s" in s_modules
        assert "mod_a" in a_modules

    def test_get_critical_modules(self):
        """クリティカルモジュール取得"""
        modules = {
            "critical1": ModuleTestStrategy(risk="S", strategy="strategy", description="desc", min_coverage=95, module_name="critical1"),
            "critical2": ModuleTestStrategy(risk="S", strategy="strategy", description="desc", min_coverage=95, module_name="critical2"),
            "normal": ModuleTestStrategy(risk="A", strategy="strategy", description="desc", min_coverage=80, module_name="normal")
        }
        config = TestStrategyConfig(modules=modules)

        critical = config.get_critical_modules()

        assert len(critical) == 2
        assert "critical1" in critical
        assert "critical2" in critical


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestTestStrategyManagerInit:
    """TestStrategyManager 初期化のテスト"""

    def test_init_with_valid_config(self, tmp_path):
        """有効な設定ファイルで初期化"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  sandbox_runner:
    risk: S
    strategy: human_design + ai_augment
    description: Critical sandbox module
    min_coverage: 95
  file_utils:
    risk: A
    strategy: ai_first + human_review
    description: File operations
    min_coverage: 80

global:
  default_risk: B
  default_strategy: ai_first_only
  default_min_coverage: 60
  critical_test_markers:
    - critical
    - safety
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        assert manager.config is not None
        assert len(manager.config.modules) == 2
        assert manager.config.default_risk == "B"

    def test_init_with_nonexistent_config(self):
        """存在しない設定ファイル"""
        manager = TestStrategyManager(config_path="/nonexistent/path.yml")

        # デフォルト設定が使用される
        assert manager.config is not None
        assert len(manager.config.modules) == 0

    def test_init_with_env_variable(self, tmp_path):
        """環境変数からプロジェクトルートを取得"""
        config_file = tmp_path / "tests" / "test_config.yml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("modules: {}\n")

        with patch.dict(os.environ, {"NEXUS_PROJECT_ROOT": str(tmp_path)}):
            manager = TestStrategyManager()

            assert manager.config_path == config_file

    def test_init_with_invalid_yaml(self, tmp_path):
        """無効なYAMLファイル"""
        config_file = tmp_path / "test_config.yml"
        config_file.write_text("invalid: yaml: content:")

        manager = TestStrategyManager(config_path=str(config_file))

        # エラー時はデフォルト設定
        assert len(manager.config.modules) == 0


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestGetStrategy:
    """TestStrategyManager.get_strategy() のテスト"""

    def test_get_strategy_for_existing_module(self, tmp_path):
        """既存モジュールの戦略取得"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  sandbox_runner:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))
        strategy = manager.get_strategy("sandbox_runner")

        assert strategy.module_name == "sandbox_runner"
        assert strategy.risk == "S"
        assert strategy.min_coverage == 95

    def test_get_strategy_for_unknown_module(self, tmp_path):
        """未知のモジュールにはデフォルト戦略"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules: {}
global:
  default_risk: B
  default_strategy: ai_first_only
  default_min_coverage: 60
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))
        strategy = manager.get_strategy("unknown_module")

        assert strategy.module_name == "unknown_module"
        assert strategy.risk == "B"
        assert strategy.strategy == "ai_first_only"


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestShouldGenerateTestsAutomatically:
    """TestStrategyManager.should_generate_tests_automatically() のテスト"""

    def test_should_generate_for_ai_first_only(self, tmp_path):
        """ai_first_onlyモジュールは自動生成可能"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  test_mod:
    risk: B
    strategy: ai_first_only
    description: Test
    min_coverage: 60
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        assert manager.should_generate_tests_automatically("test_mod") is True

    def test_should_not_generate_for_human_design(self, tmp_path):
        """human_design + ai_augmentモジュールは自動生成不可"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  test_mod:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        assert manager.should_generate_tests_automatically("test_mod") is False


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestRequiresHumanReview:
    """TestStrategyManager.requires_human_review() のテスト"""

    def test_requires_review_for_critical(self, tmp_path):
        """クリティカル（S）モジュールは人間レビュー必須"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  critical_mod:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        assert manager.requires_human_review("critical_mod") is True

    def test_no_review_for_low_risk(self, tmp_path):
        """低リスク（B）モジュールは人間レビュー不要"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  low_risk_mod:
    risk: B
    strategy: ai_first_only
    description: Low risk
    min_coverage: 60
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        assert manager.requires_human_review("low_risk_mod") is False


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestGetMinCoverage:
    """TestStrategyManager.get_min_coverage() のテスト"""

    def test_get_min_coverage_for_module(self, tmp_path):
        """モジュールの目標カバレッジを取得"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  test_mod:
    risk: A
    strategy: ai_first + human_review
    description: Test
    min_coverage: 80
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))
        coverage = manager.get_min_coverage("test_mod")

        assert coverage == 80


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestGetCriticalModules:
    """TestStrategyManager.get_critical_modules() のテスト"""

    def test_get_critical_modules(self, tmp_path):
        """クリティカルモジュール一覧を取得"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  sandbox_runner:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
  security_checker:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
  file_utils:
    risk: A
    strategy: ai_first + human_review
    description: Normal
    min_coverage: 80
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))
        critical = manager.get_critical_modules()

        assert len(critical) == 2
        assert "sandbox_runner" in critical
        assert "security_checker" in critical


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestGetModulesByRisk:
    """TestStrategyManager.get_modules_by_risk() のテスト"""

    def test_get_modules_by_risk(self, tmp_path):
        """リスクランク別にモジュールを取得"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  mod_s1:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
  mod_s2:
    risk: S
    strategy: human_design + ai_augment
    description: Critical
    min_coverage: 95
  mod_a:
    risk: A
    strategy: ai_first + human_review
    description: High
    min_coverage: 80
  mod_b:
    risk: B
    strategy: ai_first_only
    description: Normal
    min_coverage: 60
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        s_modules = manager.get_modules_by_risk("S")
        a_modules = manager.get_modules_by_risk("A")
        b_modules = manager.get_modules_by_risk("B")

        assert len(s_modules) == 2
        assert len(a_modules) == 1
        assert len(b_modules) == 1


@pytest.mark.skipif(not HAS_TEST_STRATEGY, reason="test_strategy module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    def test_config_without_global_section(self, tmp_path):
        """global設定がない場合"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  test_mod:
    risk: B
    strategy: ai_first_only
    description: Test
    min_coverage: 70
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))

        # デフォルト値が使用される
        strategy = manager.get_strategy("unknown_mod")
        assert strategy.risk == "B"
        assert strategy.strategy == "ai_first_only"
        assert strategy.min_coverage == 60

    def test_module_without_all_fields(self, tmp_path):
        """一部のフィールドが欠けているモジュール"""
        config_file = tmp_path / "test_config.yml"
        config_content = """
modules:
  incomplete_mod:
    risk: A
    # strategy, description, min_coverage がない
"""
        config_file.write_text(config_content)

        manager = TestStrategyManager(config_path=str(config_file))
        strategy = manager.get_strategy("incomplete_mod")

        # 欠けているフィールドはデフォルト値が使用される
        assert strategy.risk == "A"
        assert strategy.strategy == "ai_first_only"

    def test_empty_config_file(self, tmp_path):
        """空の設定ファイル"""
        config_file = tmp_path / "test_config.yml"
        config_file.write_text("")

        manager = TestStrategyManager(config_path=str(config_file))

        # エラーが発生せず、デフォルト設定が使用される
        assert manager.config is not None
        assert len(manager.config.modules) == 0
