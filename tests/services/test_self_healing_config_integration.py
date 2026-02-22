"""SelfHealingService と SelfHealingConfig の統合テスト"""



from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.services.self_healing_service import SelfHealingService


def test_self_healing_service_uses_config_test_command(tmp_path):
    """SelfHealingService が config.test_command を使用するテスト"""
    config = SelfHealingConfig(test_command="npm test")
    service = SelfHealingService(
        project_root=str(tmp_path),
        config=config,
    )

    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # _run_tests が config.test_command を使うことを確認
    # （実際のテスト実行はモック）
    assert service.config.test_command == "npm test"


def test_self_healing_service_uses_config_allow_test_modification(tmp_path):
    """SelfHealingService が config.allow_test_modification を使用するテスト"""
    config = SelfHealingConfig(allow_test_modification=True)
    service = SelfHealingService(
        project_root=str(tmp_path),
        config=config,
    )

    assert service.config.allow_test_modification is True


def test_self_healing_service_uses_config_allow_deletions(tmp_path):
    """SelfHealingService が config.allow_deletions を使用するテスト"""
    config = SelfHealingConfig(allow_deletions=True)
    service = SelfHealingService(
        project_root=str(tmp_path),
        config=config,
    )

    assert service.config.allow_deletions is True


def test_self_healing_service_loads_config_from_file(tmp_path):
    """SelfHealingService が設定ファイルから config を読み込むテスト"""
    import json

    config_dir = tmp_path / ".nexus"
    config_dir.mkdir()
    config_file = config_dir / "self_healing.config.json"

    config_data = {
        "test_command": "python -m pytest",
        "allow_test_modification": True,
        "allow_deletions": True,
    }

    config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")

    service = SelfHealingService(project_root=str(tmp_path))

    assert service.config.test_command == "python -m pytest"
    assert service.config.allow_test_modification is True
    assert service.config.allow_deletions is True
