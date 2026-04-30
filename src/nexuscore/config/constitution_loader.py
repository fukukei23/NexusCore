# ==============================================================================
# ファイル: src/nexuscore/config/constitution_loader.py
# 目的  : 憲法（constitution.yaml）を読み込み、環境別設定をマージする
# ==============================================================================
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ConstitutionLoader:
    """
    憲法（品質基準）を読み込み、環境に応じた設定を提供する。

    機能:
        - constitution.yaml の読み込み
        - 環境変数 NEXUS_ENV に基づく設定のマージ
        - デフォルト値のフォールバック
        - バリデーション
    """

    _instance: ConstitutionLoader | None = None
    _constitution: dict[str, Any] | None = None

    def __new__(cls):
        """シングルトンパターン"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """憲法を一度だけ読み込む"""
        if self._constitution is None:
            self._constitution = self._load_constitution()

    def get_constitution(self) -> dict[str, Any]:
        """
        現在の環境に適用される憲法を取得

        Returns:
            Dict[str, Any]: 憲法の辞書
        """
        return self._constitution or self._get_default_constitution()

    def get_tier1_config(self) -> dict[str, Any]:
        """Tier 1 品質ゲート設定を取得"""
        return self.get_constitution().get("quality_gates", {}).get("tier1", {})

    def get_tier2_config(self) -> dict[str, Any]:
        """Tier 2 品質ゲート設定を取得"""
        return self.get_constitution().get("quality_gates", {}).get("tier2", {})

    def get_guardian_config(self) -> dict[str, Any]:
        """Guardian 最終承認設定を取得"""
        return self.get_constitution().get("quality_gates", {}).get("guardian", {})

    def get_security_config(self) -> dict[str, Any]:
        """セキュリティ設定を取得"""
        return self.get_constitution().get("security", {})

    def get_npe_config(self) -> dict[str, Any]:
        """NPE (Nexus Protocol Engine) 設定を取得"""
        return self.get_security_config().get("npe", {})

    def get_error_handling_config(self) -> dict[str, Any]:
        """エラーハンドリング設定を取得"""
        return self.get_constitution().get("error_handling", {})

    def get_fkb_config(self) -> dict[str, Any]:
        """FKB (Fault Knowledge Base) 設定を取得"""
        return self.get_constitution().get("fkb", {})

    def _load_constitution(self) -> dict[str, Any]:
        """
        憲法ファイルを読み込み、環境別設定をマージ

        Returns:
            Dict[str, Any]: マージ済みの憲法
        """
        if yaml is None:
            logger.warning("PyYAML がインストールされていません。デフォルト憲法を使用します。")
            return self._get_default_constitution()

        # 憲法ファイルのパスを決定
        constitution_path = self._find_constitution_file()
        if not constitution_path or not constitution_path.exists():
            logger.warning(
                f"憲法ファイルが見つかりません: {constitution_path}. デフォルトを使用します。"
            )
            return self._get_default_constitution()

        # YAMLファイルを読み込み
        try:
            with open(constitution_path, encoding="utf-8") as f:
                base_constitution = yaml.safe_load(f)

            logger.info(f"憲法を読み込みました: {constitution_path}")

            # 環境別設定をマージ
            environment = os.getenv("NEXUS_ENV", "development")
            merged = self._merge_environment_config(base_constitution, environment)

            # バリデーション
            self._validate_constitution(merged)

            return merged

        except Exception as e:
            logger.error(f"憲法読み込みエラー: {e}", exc_info=True)
            return self._get_default_constitution()

    def _find_constitution_file(self) -> Path | None:
        """
        憲法ファイルを検索

        検索順序:
            1. 環境変数 NEXUS_CONSTITUTION_PATH
            2. プロジェクトルート/config/constitution.yaml
            3. カレントディレクトリ/config/constitution.yaml
        """
        # 環境変数から
        env_path = os.getenv("NEXUS_CONSTITUTION_PATH")
        if env_path:
            return Path(env_path)

        # プロジェクトルートから検索
        project_root = self._find_project_root()
        if project_root:
            constitution_path = project_root / "config" / "constitution.yaml"
            if constitution_path.exists():
                return constitution_path

        # カレントディレクトリから
        cwd_path = Path.cwd() / "config" / "constitution.yaml"
        if cwd_path.exists():
            return cwd_path

        return None

    def _find_project_root(self) -> Path | None:
        """
        プロジェクトルートを検索（.git または pyproject.toml の存在で判定）
        """
        current = Path(__file__).resolve().parent

        # 最大10階層まで遡る
        for _ in range(10):
            if (current / ".git").exists() or (current / "pyproject.toml").exists():
                return current
            if current.parent == current:
                break
            current = current.parent

        return None

    def _merge_environment_config(self, base: dict[str, Any], environment: str) -> dict[str, Any]:
        """
        環境別設定をベース設定にマージ

        Args:
            base: ベース憲法
            environment: 環境名 ("development", "staging", "production")

        Returns:
            Dict[str, Any]: マージ済み憲法
        """
        env_overrides = base.get("environments", {}).get(environment, {})

        if not env_overrides:
            logger.info(f"環境 '{environment}' の上書き設定はありません。")
            return base

        # ディープマージ
        merged = self._deep_merge(base, env_overrides)

        logger.info(f"環境 '{environment}' の設定をマージしました。")
        return merged

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        辞書の再帰的マージ

        Args:
            base: ベース辞書
            override: 上書き辞書

        Returns:
            Dict: マージされた辞書
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_constitution(self, constitution: dict[str, Any]) -> None:
        """
        憲法の妥当性を検証

        Raises:
            ValueError: 必須項目が不足している場合
        """
        # 必須セクションのチェック
        required_sections = ["quality_gates", "security"]

        for section in required_sections:
            if section not in constitution:
                raise ValueError(f"憲法に必須セクション '{section}' がありません。")

        # Tier 1 の必須項目
        tier1 = constitution.get("quality_gates", {}).get("tier1", {})
        required_tier1_keys = ["test_coverage_min", "pylint_score_min"]

        for key in required_tier1_keys:
            if key not in tier1:
                raise ValueError(f"Tier 1 設定に必須項目 '{key}' がありません。")

        # 値の範囲チェック
        coverage = tier1.get("test_coverage_min", 0)
        if not (0 <= coverage <= 100):
            raise ValueError(f"test_coverage_min は 0-100 の範囲で指定してください: {coverage}")

        logger.info("憲法のバリデーションに成功しました。")

    def _get_default_constitution(self) -> dict[str, Any]:
        """
        デフォルト憲法（フォールバック）

        Returns:
            Dict[str, Any]: デフォルト憲法
        """
        return {
            "project": {"name": "NexusCore", "version": "7.25.0"},
            "quality_gates": {
                "tier1": {
                    "test_coverage_min": 90,
                    "branch_coverage_min": 85,
                    "pylint_score_min": 8.0,
                    "cyclomatic_complexity_max": 10,
                    "bandit_severity_max": "MEDIUM",
                },
                "tier2": {"mutation_score_min": 80, "mutation_timeout_sec": 10},
                "guardian": {
                    "check_architecture_consistency": True,
                    "prohibit_circular_dependencies": True,
                },
            },
            "security": {
                "npe": {
                    "enabled": True,
                    "detect_api_keys": True,
                    "detect_pem_keys": True,
                    "mask_before_llm_call": True,
                }
            },
            "error_handling": {
                "retry": {"max_retries": 3, "base_delay_sec": 1.0, "exponential_backoff": True}
            },
            "fkb": {"learning": {"enabled": True, "trigger_on_debugger_failure": True}},
        }


# ------------------------------------------------------------------------------
# グローバル関数（便利な関数）
# ------------------------------------------------------------------------------

_loader_instance: ConstitutionLoader | None = None


def get_constitution() -> dict[str, Any]:
    """
    現在の環境に適用される憲法を取得（シングルトン）

    Returns:
        Dict[str, Any]: 憲法の辞書

    Example:
        >>> from nexuscore.config.constitution_loader import get_constitution
        >>> constitution = get_constitution()
        >>> min_coverage = constitution["quality_gates"]["tier1"]["test_coverage_min"]
        >>> print(f"最低カバレッジ: {min_coverage}%")
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ConstitutionLoader()
    return _loader_instance.get_constitution()


def get_tier1_config() -> dict[str, Any]:
    """Tier 1 品質ゲート設定を取得"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ConstitutionLoader()
    return _loader_instance.get_tier1_config()


def get_tier2_config() -> dict[str, Any]:
    """Tier 2 品質ゲート設定を取得"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ConstitutionLoader()
    return _loader_instance.get_tier2_config()


def reload_constitution() -> dict[str, Any]:
    """
    憲法を強制的に再読み込み（テスト用）

    Returns:
        Dict[str, Any]: 再読み込み後の憲法
    """
    global _loader_instance
    ConstitutionLoader._constitution = None
    _loader_instance = ConstitutionLoader()
    return _loader_instance.get_constitution()
