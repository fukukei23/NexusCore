import os
from pathlib import Path

import pytest


@pytest.fixture
def env_setup(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    env_file = project_root / ".env"
    env_file.write_text('API_KEY="123"\nEMPTY=\n', encoding="utf-8")
    return project_root


def test_generate_secrets_creates_files(tmp_path, env_setup, monkeypatch):
    project_root = env_setup
    config_dir = project_root / "src" / "nexuscore" / "config"
    config_dir.mkdir(parents=True)

    script_source = Path(__file__).resolve().parents[2] / "src" / "nexuscore" / "config" / "generate_secrets.py"
    script_path = config_dir / "generate_secrets.py"
    script_path.write_text(script_source.read_text(), encoding="utf-8")

    monkeypatch.chdir(config_dir)
    exec_globals = {"__file__": str(script_path)}
    exec(script_path.read_text(), exec_globals)

    secrets_path = config_dir / "secrets.py"
    template_path = project_root / ".env.template"

    secrets_text = secrets_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")

    assert 'class Secrets:' in secrets_text
    assert 'API_KEY = "123"' in secrets_text
    assert 'EMPTY = ""' in secrets_text
    assert "API_KEY=" in template_text
    assert "EMPTY=" in template_text
