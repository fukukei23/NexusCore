from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class ModuleTestStrategy:
    """モジュールのテスト戦略設定"""

    risk: str  # "S" | "A" | "B"
    strategy: str  # "human_design + ai_augment" | "ai_first + human_review" | "ai_first_only"
    description: str
    min_coverage: int  # 目標カバレッジ（%）
    module_name: str = ""

    @property
    def requires_human_review(self) -> bool:
        """人間レビューが必要かどうか"""
        return self.risk in ("S", "A")

    @property
    def is_critical(self) -> bool:
        """クリティカルなモジュールかどうか"""
        return self.risk == "S"

    @property
    def allows_ai_first(self) -> bool:
        """AI先行生成が許可されているか"""
        return self.strategy in ("ai_first + human_review", "ai_first_only")


@dataclass
class TestStrategyConfig:
    """テスト戦略設定全体"""

    modules: dict[str, ModuleTestStrategy]
    default_risk: str = "B"
    default_strategy: str = "ai_first_only"
    default_min_coverage: int = 60
    critical_test_markers: list[str] | None = None

    def __post_init__(self) -> None:
        if self.critical_test_markers is None:
            self.critical_test_markers = ["critical", "safety", "security"]

    def get_strategy(self, module_name: str) -> ModuleTestStrategy:
        """
        モジュール名からテスト戦略を取得する。

        見つからない場合はデフォルト設定を返す。
        """
        if module_name in self.modules:
            strategy = self.modules[module_name]
            strategy.module_name = module_name
            return strategy

        # デフォルト設定を返す
        return ModuleTestStrategy(
            module_name=module_name,
            risk=self.default_risk,
            strategy=self.default_strategy,
            description=f"Default strategy for {module_name}",
            min_coverage=self.default_min_coverage,
        )

    def get_modules_by_risk(self, risk: str) -> list[str]:
        """指定されたリスクランクのモジュール一覧を取得"""
        return [name for name, strategy in self.modules.items() if strategy.risk == risk]

    def get_critical_modules(self) -> list[str]:
        """クリティカルなモジュール（ランクS）一覧を取得"""
        return self.get_modules_by_risk("S")


class TestStrategyManager:
    """
    テスト戦略を管理するマネージャークラス。

    設定ファイルを読み込み、モジュールごとのテスト生成戦略を提供します。
    """

    def __init__(self, config_path: str | None = None) -> None:
        """
        :param config_path: 設定ファイルのパス（省略時は tests/test_config.yml）
        """
        if config_path is None:
            # プロジェクトルートを探す
            project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())
            config_path = os.path.join(project_root, "tests", "test_config.yml")

        self.config_path = Path(config_path)
        self.config: TestStrategyConfig | None = None
        self._load_config()

    def _load_config(self) -> None:
        """設定ファイルを読み込む"""
        if not self.config_path.exists():
            logger.warning(f"Test strategy config not found: {self.config_path}. Using defaults.")
            self.config = TestStrategyConfig(modules={})
            return

        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                if yaml is None:
                    raise ImportError("pyyaml required for test strategy loading")
                data = yaml.safe_load(f)

            modules = {}
            for module_name, module_data in data.get("modules", {}).items():
                modules[module_name] = ModuleTestStrategy(
                    module_name=module_name,
                    risk=module_data.get("risk", "B"),
                    strategy=module_data.get("strategy", "ai_first_only"),
                    description=module_data.get("description", ""),
                    min_coverage=module_data.get("min_coverage", 60),
                )

            global_config = data.get("global", {})
            self.config = TestStrategyConfig(
                modules=modules,
                default_risk=global_config.get("default_risk", "B"),
                default_strategy=global_config.get("default_strategy", "ai_first_only"),
                default_min_coverage=global_config.get("default_min_coverage", 60),
                critical_test_markers=global_config.get(
                    "critical_test_markers", ["critical", "safety", "security"]
                ),
            )

            logger.info(f"Loaded test strategy config: {len(modules)} modules")
        except Exception as e:
            logger.error(f"Failed to load test strategy config: {e}", exc_info=True)
            self.config = TestStrategyConfig(modules={})

    def get_strategy(self, module_name: str) -> ModuleTestStrategy:
        """
        モジュール名からテスト戦略を取得する。

        :param module_name: モジュール名（例: "sandbox_runner", "file_utils"）
        :return: テスト戦略設定
        """
        if self.config is None:
            self._load_config()

        return self.config.get_strategy(module_name)  # type: ignore[union-attr]

    def should_generate_tests_automatically(self, module_name: str) -> bool:
        """
        モジュールに対して自動テスト生成を行うべきかどうかを判定する。

        :param module_name: モジュール名
        :return: 自動生成が許可されている場合 True
        """
        strategy = self.get_strategy(module_name)
        return strategy.allows_ai_first

    def requires_human_review(self, module_name: str) -> bool:
        """
        モジュールのテストに人間レビューが必要かどうかを判定する。

        :param module_name: モジュール名
        :return: 人間レビューが必要な場合 True
        """
        strategy = self.get_strategy(module_name)
        return strategy.requires_human_review

    def get_min_coverage(self, module_name: str) -> int:
        """
        モジュールの目標カバレッジを取得する。

        :param module_name: モジュール名
        :return: 目標カバレッジ（%）
        """
        strategy = self.get_strategy(module_name)
        return strategy.min_coverage

    def get_critical_modules(self) -> list[str]:
        """クリティカルなモジュール（ランクS）一覧を取得"""
        if self.config is None:
            self._load_config()
        return self.config.get_critical_modules()  # type: ignore[union-attr]

    def get_modules_by_risk(self, risk: str) -> list[str]:
        """指定されたリスクランクのモジュール一覧を取得"""
        if self.config is None:
            self._load_config()
        return self.config.get_modules_by_risk(risk)  # type: ignore[union-attr]
