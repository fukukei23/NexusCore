"""
unified_config.py の包括的テスト

カバレッジ:
- NexusConfig: 統一設定クラス
- DatabaseConfig: データベース設定
- CeleryConfig: Celery設定
- AutonomyConfig: 自律性レベル設定
- LLMConfig: LLM設定
- get_config / set_config: グローバル設定アクセス
"""

import os

import pytest

from nexuscore.config.unified_config import (
    AutonomyConfig,
    CeleryConfig,
    DatabaseConfig,
    LLMConfig,
    NexusConfig,
    get_config,
    set_config,
)


class TestDatabaseConfig:
    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URI", raising=False)
        cfg = DatabaseConfig.from_env()
        assert "sqlite" in cfg.uri

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URI", "postgresql://user:pass@localhost/db")
        cfg = DatabaseConfig.from_env()
        assert cfg.uri == "postgresql://user:pass@localhost/db"

    def test_validate_empty_raises(self):
        cfg = DatabaseConfig(uri="")
        with pytest.raises(ValueError, match="DATABASE_URI"):
            cfg.validate()


class TestCeleryConfig:
    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        cfg = CeleryConfig.from_env()
        assert "redis://" in cfg.broker_url

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://custom:6379/0")
        monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://custom:6379/1")
        cfg = CeleryConfig.from_env()
        assert cfg.broker_url == "redis://custom:6379/0"
        assert cfg.result_backend == "redis://custom:6379/1"

    def test_validate_empty_raises(self):
        cfg = CeleryConfig(broker_url="", result_backend="redis://localhost:6379/1")
        with pytest.raises(ValueError, match="CELERY_BROKER_URL"):
            cfg.validate()


class TestAutonomyConfig:
    def test_defaults(self):
        cfg = AutonomyConfig()
        assert cfg.user == 1
        assert cfg.admin == 2
        assert cfg.system == 3

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "5")
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "3")
        monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "4")
        cfg = AutonomyConfig.from_env()
        assert cfg.user == 5
        assert cfg.admin == 3
        assert cfg.system == 4

    def test_validate_out_of_range(self):
        cfg = AutonomyConfig(user=10)
        with pytest.raises(ValueError):
            cfg.validate()


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.timeout == 60
        assert cfg.max_retries == 3

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("NEXUS_LLM_TIMEOUT", "120")
        cfg = LLMConfig.from_env()
        assert cfg.timeout == 120

    def test_validate_negative_timeout(self):
        cfg = LLMConfig(timeout=-1)
        with pytest.raises(ValueError, match="timeout"):
            cfg.validate()


class TestNexusConfig:
    def test_webapp_base_url_default(self, monkeypatch):
        monkeypatch.delenv("WEBAPP_BASE_URL", raising=False)
        cfg = NexusConfig.from_env()
        assert cfg.webapp_base_url == "http://localhost:5000"

    def test_webapp_base_url_custom(self, monkeypatch):
        monkeypatch.setenv("WEBAPP_BASE_URL", "https://nexus.example.com")
        cfg = NexusConfig.from_env()
        assert cfg.webapp_base_url == "https://nexus.example.com"

    def test_to_flask_config(self, monkeypatch):
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        cfg = NexusConfig.from_env()
        flask_cfg = cfg.to_flask_config()
        assert "SECRET_KEY" in flask_cfg
        assert "SQLALCHEMY_DATABASE_URI" in flask_cfg


class TestGetSetConfig:
    def test_get_config_returns_nexus_config(self):
        cfg = get_config()
        assert isinstance(cfg, NexusConfig)

    def test_get_config_caches(self):
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_set_config_overrides(self):
        original = get_config()
        custom = NexusConfig(
            flask_secret_key="test",
            database=DatabaseConfig(uri="sqlite:///test.db"),
            celery=CeleryConfig(broker_url="redis://localhost:6379/0", result_backend="redis://localhost:6379/1"),
            autonomy=AutonomyConfig(),
            llm=LLMConfig(),
        )
        set_config(custom)
        assert get_config() is custom
        set_config(original)
