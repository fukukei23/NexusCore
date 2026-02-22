"""self_healing_config.py のテスト"""

import json

from nexuscore.config.self_healing_config import SelfHealingConfig


def test_self_healing_config_defaults():
    """デフォルト設定のテスト"""
    config = SelfHealingConfig()

    assert config.label == "self-healing"
    assert config.allowed_target_branches is None
    assert config.test_command == "pytest -q"
    assert config.allow_test_modification is False
    assert config.allow_deletions is False


def test_self_healing_config_load_from_file(tmp_path):
    """設定ファイルから読み込むテスト"""
    config_dir = tmp_path / ".nexus"
    config_dir.mkdir()
    config_file = config_dir / "self_healing.config.json"

    config_data = {
        "label": "auto-fix",
        "allowed_target_branches": ["main", "develop"],
        "test_command": "npm test",
        "allow_test_modification": True,
        "allow_deletions": True,
    }

    config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")

    config = SelfHealingConfig.load(str(tmp_path))

    assert config.label == "auto-fix"
    assert config.allowed_target_branches == ["main", "develop"]
    assert config.test_command == "npm test"
    assert config.allow_test_modification is True
    assert config.allow_deletions is True


def test_self_healing_config_load_missing_file(tmp_path):
    """設定ファイルが存在しない場合のテスト"""
    config = SelfHealingConfig.load(str(tmp_path))

    # デフォルト設定が返される
    assert config.label == "self-healing"
    assert config.test_command == "pytest -q"


def test_self_healing_config_load_invalid_json(tmp_path):
    """不正なJSONファイルの場合のテスト"""
    config_dir = tmp_path / ".nexus"
    config_dir.mkdir()
    config_file = config_dir / "self_healing.config.json"

    config_file.write_text("invalid json", encoding="utf-8")

    config = SelfHealingConfig.load(str(tmp_path))

    # デフォルト設定が返される
    assert config.label == "self-healing"


def test_self_healing_config_bool_parsing(tmp_path):
    """bool値のパーステスト（文字列形式も受け付ける）"""
    config_dir = tmp_path / ".nexus"
    config_dir.mkdir()
    config_file = config_dir / "self_healing.config.json"

    config_data = {
        "allow_test_modification": "true",
        "allow_deletions": "yes",
    }

    config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")

    config = SelfHealingConfig.load(str(tmp_path))

    assert config.allow_test_modification is True
    assert config.allow_deletions is True


def test_self_healing_config_empty_allowed_branches(tmp_path):
    """allowed_target_branches が空リストの場合のテスト"""
    config_dir = tmp_path / ".nexus"
    config_dir.mkdir()
    config_file = config_dir / "self_healing.config.json"

    config_data = {
        "allowed_target_branches": [],
    }

    config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")

    config = SelfHealingConfig.load(str(tmp_path))

    assert config.allowed_target_branches == []
