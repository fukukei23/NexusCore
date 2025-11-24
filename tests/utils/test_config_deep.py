import importlib
from typing import List

import pytest

import nexuscore.config.config as config_module


@pytest.fixture(autouse=True)
def reload_config_module():
    """各テストの前後で config モジュールを再読み込みし、環境変数の影響をリセットする."""
    importlib.reload(config_module)
    yield
    importlib.reload(config_module)


def get_config_instance():
    return config_module.config


def test_app_config_defaults_present():
    """AppConfig に基本的な属性が定義されていることを確認."""
    config = get_config_instance()

    assert hasattr(config, "FLASK_SECRET_KEY")
    assert hasattr(config, "DATABASE_URI")
    assert config.ROLE_MAX_AUTONOMY.get("user") == 1
    assert config.SERVER_MAX_LIMITS["max_llm_calls_per_task"] == 12
    assert config.BASELINE_AUTOMATION_POLICY["budget"]["hard_stop_on_exceed"]
    globs = config.BASELINE_AUTOMATION_POLICY["scope"]["include_globs"]
    assert isinstance(globs, list)
    assert "src/**" in globs


def test_scope_include_respects_env(monkeypatch):
    """環境変数で include_globs が上書きされることを確認."""
    monkeypatch.setenv("NEXUS_SCOPE_INCLUDE", "alpha/**, beta/**, , gamma/**")
    importlib.reload(config_module)
    config = get_config_instance()

    include_globs: List[str] = config.BASELINE_AUTOMATION_POLICY["scope"]["include_globs"]
    assert include_globs == ["alpha/**", "beta/**", "gamma/**"]


def test_role_autonomy_env_override(monkeypatch):
    """環境変数で ROLE_MAX_AUTONOMY が変更できること."""
    monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "5")
    monkeypatch.setenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "4")
    importlib.reload(config_module)
    config = get_config_instance()

    assert config.ROLE_MAX_AUTONOMY["admin"] == 5
    assert config.ROLE_MAX_AUTONOMY["system"] == 4


def test_secret_detection_patterns_contains_openai():
    """シークレット検出パターンが sk- トークンを含むことを保証."""
    patterns: List[str] = config_module.config.BASELINE_AUTOMATION_POLICY["secret_detection_patterns"]
    assert any("sk-" in pattern for pattern in patterns)


def test_split_csv_strips_empty_entries():
    """_split_csv が空白行を除去することを確認."""
    result = config_module.AppConfig._split_csv("NEXUS_SCOPE_INCLUDE", "a,  ,b")
    assert result == ["a", "b"]
