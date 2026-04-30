"""
test_test_strategy.py

テスト戦略管理機能のテスト。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from nexuscore.utils.test_strategy import (
    ModuleTestStrategy,
    TestStrategyManager,
)


class TestTestStrategyManager:
    """TestStrategyManager のテスト"""

    def test_load_config_not_found(self):
        """設定ファイルが存在しない場合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yml"
            manager = TestStrategyManager(config_path=str(config_path))

            # デフォルト設定が返される
            strategy = manager.get_strategy("unknown_module")
            assert strategy.risk == "B"
            assert strategy.strategy == "ai_first_only"

    def test_load_config_exists(self):
        """設定ファイルが存在する場合"""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yml"

            # 設定ファイルを作成
            config_data = {
                "modules": {
                    "sandbox_runner": {
                        "risk": "S",
                        "strategy": "human_design + ai_augment",
                        "description": "Critical module",
                        "min_coverage": 90,
                    },
                    "file_utils": {
                        "risk": "B",
                        "strategy": "ai_first_only",
                        "description": "Utility module",
                        "min_coverage": 70,
                    },
                },
                "global": {
                    "default_risk": "B",
                    "default_strategy": "ai_first_only",
                    "default_min_coverage": 60,
                },
            }

            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            manager = TestStrategyManager(config_path=str(config_path))

            # 設定されたモジュール
            strategy = manager.get_strategy("sandbox_runner")
            assert strategy.risk == "S"
            assert strategy.strategy == "human_design + ai_augment"
            assert strategy.min_coverage == 90
            assert strategy.requires_human_review is True
            assert strategy.is_critical is True

            strategy = manager.get_strategy("file_utils")
            assert strategy.risk == "B"
            assert strategy.strategy == "ai_first_only"
            assert strategy.min_coverage == 70
            assert strategy.requires_human_review is False
            assert strategy.is_critical is False

            # 未設定のモジュール（デフォルト）
            strategy = manager.get_strategy("unknown_module")
            assert strategy.risk == "B"
            assert strategy.strategy == "ai_first_only"
            assert strategy.min_coverage == 60

    def test_should_generate_tests_automatically(self):
        """自動テスト生成の判定"""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yml"

            config_data = {
                "modules": {
                    "sandbox_runner": {
                        "risk": "S",
                        "strategy": "human_design + ai_augment",
                        "description": "Critical",
                        "min_coverage": 90,
                    },
                    "file_utils": {
                        "risk": "B",
                        "strategy": "ai_first_only",
                        "description": "Utility",
                        "min_coverage": 70,
                    },
                },
            }

            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            manager = TestStrategyManager(config_path=str(config_path))

            # human_design + ai_augment は自動生成不可
            assert manager.should_generate_tests_automatically("sandbox_runner") is False

            # ai_first_only は自動生成可
            assert manager.should_generate_tests_automatically("file_utils") is True

    def test_get_critical_modules(self):
        """クリティカルモジュール一覧の取得"""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yml"

            config_data = {
                "modules": {
                    "sandbox_runner": {
                        "risk": "S",
                        "strategy": "human_design + ai_augment",
                        "description": "Critical",
                        "min_coverage": 90,
                    },
                    "file_utils": {
                        "risk": "B",
                        "strategy": "ai_first_only",
                        "description": "Utility",
                        "min_coverage": 70,
                    },
                    "guardian_agent": {
                        "risk": "S",
                        "strategy": "human_design + ai_augment",
                        "description": "Critical",
                        "min_coverage": 85,
                    },
                },
            }

            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            manager = TestStrategyManager(config_path=str(config_path))
            critical = manager.get_critical_modules()

            assert "sandbox_runner" in critical
            assert "guardian_agent" in critical
            assert "file_utils" not in critical

    def test_get_modules_by_risk(self):
        """リスクランク別のモジュール一覧取得"""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yml"

            config_data = {
                "modules": {
                    "module_s": {
                        "risk": "S",
                        "strategy": "human_design + ai_augment",
                        "description": "S",
                        "min_coverage": 90,
                    },
                    "module_a": {
                        "risk": "A",
                        "strategy": "ai_first + human_review",
                        "description": "A",
                        "min_coverage": 80,
                    },
                    "module_b": {
                        "risk": "B",
                        "strategy": "ai_first_only",
                        "description": "B",
                        "min_coverage": 60,
                    },
                },
            }

            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            manager = TestStrategyManager(config_path=str(config_path))

            assert "module_s" in manager.get_modules_by_risk("S")
            assert "module_a" in manager.get_modules_by_risk("A")
            assert "module_b" in manager.get_modules_by_risk("B")


class TestModuleTestStrategy:
    """ModuleTestStrategy のテスト"""

    def test_requires_human_review(self):
        """人間レビューの必要性判定"""
        strategy_s = ModuleTestStrategy(
            risk="S",
            strategy="human_design + ai_augment",
            description="Critical",
            min_coverage=90,
        )
        assert strategy_s.requires_human_review is True

        strategy_a = ModuleTestStrategy(
            risk="A",
            strategy="ai_first + human_review",
            description="Important",
            min_coverage=80,
        )
        assert strategy_a.requires_human_review is True

        strategy_b = ModuleTestStrategy(
            risk="B",
            strategy="ai_first_only",
            description="Non-critical",
            min_coverage=60,
        )
        assert strategy_b.requires_human_review is False

    def test_allows_ai_first(self):
        """AI先行生成の許可判定"""
        strategy1 = ModuleTestStrategy(
            risk="A",
            strategy="ai_first + human_review",
            description="AI first",
            min_coverage=80,
        )
        assert strategy1.allows_ai_first is True

        strategy2 = ModuleTestStrategy(
            risk="B",
            strategy="ai_first_only",
            description="AI only",
            min_coverage=60,
        )
        assert strategy2.allows_ai_first is True

        strategy3 = ModuleTestStrategy(
            risk="S",
            strategy="human_design + ai_augment",
            description="Human first",
            min_coverage=90,
        )
        assert strategy3.allows_ai_first is False
