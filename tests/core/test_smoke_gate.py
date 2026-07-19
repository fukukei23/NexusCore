"""main_cli の Smoke Test 再定義テスト。spec §3-3"""
from __future__ import annotations

import sys
from pathlib import Path

# main_cli はリポジトリルート直下のためパスを通す
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main_cli import run_smoke_gate  # noqa: E402


def test_all_files_exist_and_compile(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app/calc.py").write_text("def add(a, b):\n    return a + b\n")
    target_files = [{"path": "app/calc.py", "role": "implementation"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is True
    assert errors == []


def test_missing_file_fails(tmp_path):
    target_files = [{"path": "app/missing.py", "role": "implementation"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is False
    assert any("missing.py" in e for e in errors)


def test_syntax_error_fails(tmp_path):
    (tmp_path / "bad.py").write_text("def broken(:\n")
    target_files = [{"path": "bad.py", "role": "implementation"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is False
    assert any("bad.py" in e for e in errors)


def test_config_files_skip_py_compile(tmp_path):
    (tmp_path / "config.toml").write_text("[tool]\nname = 'x'\n")
    target_files = [{"path": "config.toml", "role": "config"}]
    ok, errors = run_smoke_gate(str(tmp_path), target_files)
    assert ok is True
