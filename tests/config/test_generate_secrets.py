import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def env_setup(tmp_path):
    """テスト用の.envファイルとプロジェクト構造を作成"""
    project_root = tmp_path / "proj"
    project_root.mkdir()
    env_file = project_root / ".env"
    env_file.write_text('API_KEY="123"\nEMPTY=\nSECRET_KEY="test-secret"', encoding="utf-8")

    # プロジェクト構造を作成
    config_dir = project_root / "src" / "nexuscore" / "config"
    config_dir.mkdir(parents=True)

    return project_root, config_dir


def test_generate_secrets_creates_files(env_setup, monkeypatch):
    """generate_secrets.pyが正しくファイルを生成することをテスト"""
    project_root, config_dir = env_setup

    # 元のスクリプトを読み込む
    script_source = (
        Path(__file__).resolve().parents[2] / "src" / "nexuscore" / "config" / "generate_secrets.py"
    )
    script_content = script_source.read_text(encoding="utf-8")

    # ROOT_PATHをテスト用に置き換える
    modified_script = script_content.replace(
        "ROOT_PATH = Path(__file__).resolve().parents[3]", f"ROOT_PATH = Path(r'{project_root}')"
    )

    # 実行用のグローバルスコープ
    exec_globals = {
        "__file__": str(config_dir / "generate_secrets.py"),
        "__name__": "__main__",
        "Path": Path,
        "os": os,
    }

    # dotenv_valuesをモック
    with patch("dotenv_values") as mock_dotenv:
        mock_dotenv.return_value = {"API_KEY": "123", "EMPTY": "", "SECRET_KEY": "test-secret"}

        # スクリプトを実行
        exec(modified_script, exec_globals)

    # 生成されたファイルを確認
    secrets_path = config_dir / "secrets.py"
    template_path = project_root / ".env.template"

    assert secrets_path.exists(), "secrets.pyが生成されていない"
    assert template_path.exists(), ".env.templateが生成されていない"

    secrets_text = secrets_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")

    assert "class Secrets:" in secrets_text
    assert 'API_KEY = "123"' in secrets_text
    assert 'EMPTY = ""' in secrets_text
    assert 'SECRET_KEY = "test-secret"' in secrets_text
    assert "API_KEY=" in template_text
    assert "EMPTY=" in template_text
    assert "SECRET_KEY=" in template_text


def test_generate_secrets_raises_error_when_env_missing(tmp_path, monkeypatch):
    """.envファイルが存在しない場合にエラーを発生させることをテスト"""
    project_root = tmp_path / "proj"
    project_root.mkdir()
    config_dir = project_root / "src" / "nexuscore" / "config"
    config_dir.mkdir(parents=True)

    script_source = (
        Path(__file__).resolve().parents[2] / "src" / "nexuscore" / "config" / "generate_secrets.py"
    )
    script_content = script_source.read_text(encoding="utf-8")

    # ROOT_PATHをテスト用に置き換える（.envが存在しないパス）
    modified_script = script_content.replace(
        "ROOT_PATH = Path(__file__).resolve().parents[3]", f"ROOT_PATH = Path(r'{project_root}')"
    )

    exec_globals = {
        "__file__": str(config_dir / "generate_secrets.py"),
        "__name__": "__main__",
        "Path": Path,
        "os": os,
    }

    # FileNotFoundErrorが発生することを確認
    with pytest.raises(FileNotFoundError, match=".env ファイルが存在しません"):
        exec(modified_script, exec_globals)
