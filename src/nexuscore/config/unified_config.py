"""
NexusCore 統一設定システム

すべての設定を一元管理し、環境変数とファイルベース設定を統合する。
これにより、4つの独立した設定システムを1つに統合し、設定の妥当性検証を実現する。

Usage:
    from nexuscore.config.unified_config import get_config

    config = get_config()
    print(config.database.uri)
    print(config.llm.default_model)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DatabaseConfig:
    """データベース設定"""

    uri: str
    track_modifications: bool = False

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        return cls(
            uri=os.getenv("DATABASE_URI", "sqlite:///nexuscore.db"),
            track_modifications=os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "false").lower()
            == "true",
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if not self.uri:
            raise ValueError("DATABASE_URI is required")


@dataclass
class CeleryConfig:
    """Celery設定"""

    broker_url: str
    result_backend: str

    @classmethod
    def from_env(cls) -> CeleryConfig:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return cls(
            broker_url=os.getenv("CELERY_BROKER_URL", redis_url),
            result_backend=os.getenv("CELERY_RESULT_BACKEND", redis_url.replace(":0", ":1")),
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if not self.broker_url:
            raise ValueError("CELERY_BROKER_URL is required")


@dataclass
class AutonomyConfig:
    """自律性レベル設定"""

    user: int = 1
    admin: int = 2
    system: int = 3

    @classmethod
    def from_env(cls) -> AutonomyConfig:
        return cls(
            user=int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "1")),
            admin=int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "2")),
            system=int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "3")),
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if not (0 <= self.user <= 5):
            raise ValueError("User autonomy must be 0-5")
        if not (0 <= self.admin <= 5):
            raise ValueError("Admin autonomy must be 0-5")
        if not (0 <= self.system <= 5):
            raise ValueError("System autonomy must be 0-5")


@dataclass
class LLMConfig:
    """LLM設定"""

    default_model: str = "gpt-4"
    timeout: int = 60
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls(
            default_model=os.getenv("NEXUS_DEFAULT_MODEL", "gpt-4"),
            timeout=int(os.getenv("NEXUS_LLM_TIMEOUT", "60")),
            max_retries=int(os.getenv("NEXUS_LLM_MAX_RETRIES", "3")),
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if self.timeout <= 0:
            raise ValueError("LLM timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")


@dataclass
class NexusConfig:
    """
    NexusCore統一設定

    すべての設定を集約し、環境変数とファイルベース設定を統合する。
    """

    flask_secret_key: str
    database: DatabaseConfig
    celery: CeleryConfig
    autonomy: AutonomyConfig
    llm: LLMConfig
    self_healing: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, config_file: Path | None = None) -> NexusConfig:
        """
        環境変数とファイルから設定をロード

        Args:
            config_file: 追加設定ファイルのパス（オプション）

        Returns:
            統一設定オブジェクト
        """
        # Self-healing設定をファイルからロード
        sh_config = cls._load_self_healing_config(config_file)

        # 各サブシステムの設定を作成
        config = cls(
            flask_secret_key=os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production"),
            database=DatabaseConfig.from_env(),
            celery=CeleryConfig.from_env(),
            autonomy=AutonomyConfig.from_env(),
            llm=LLMConfig.from_env(),
            self_healing=sh_config,
        )

        # 設定の妥当性を検証
        config.validate()

        return config

    @staticmethod
    def _load_self_healing_config(config_file: Path | None = None) -> dict[str, Any]:
        """Self-healing設定をファイルからロード"""
        if config_file is None:
            config_file = Path(".nexus/self_healing.config.json")

        if config_file.exists():
            try:
                return json.loads(config_file.read_text())
            except Exception as e:
                print(f"Warning: Failed to load {config_file}: {e}")
                return {}
        return {}

    def validate(self) -> None:
        """すべてのサブ設定の妥当性をチェック"""
        self.database.validate()
        self.celery.validate()
        self.autonomy.validate()
        self.llm.validate()

        # Flask secret keyの検証
        if self.flask_secret_key == "dev-secret-key-change-in-production":
            if os.getenv("FLASK_ENV") == "production":
                raise ValueError("Must set FLASK_SECRET_KEY in production environment")

    def to_flask_config(self) -> dict[str, Any]:
        """Flask設定辞書に変換"""
        return {
            "SECRET_KEY": self.flask_secret_key,
            "SQLALCHEMY_DATABASE_URI": self.database.uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": self.database.track_modifications,
        }


# グローバル設定インスタンス（シングルトン）
_config: NexusConfig | None = None


def get_config(reload: bool = False) -> NexusConfig:
    """
    グローバル設定インスタンスを取得

    Args:
        reload: True の場合、設定を再読み込み

    Returns:
        NexusConfig インスタンス
    """
    global _config
    if _config is None or reload:
        _config = NexusConfig.from_env()
    return _config


def set_config(config: NexusConfig) -> None:
    """
    グローバル設定を上書き（テスト用）

    Args:
        config: 設定オブジェクト
    """
    global _config
    _config = config
