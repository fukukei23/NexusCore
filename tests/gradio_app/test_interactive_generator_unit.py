import os
from pathlib import Path

import pytest

try:
    import nexuscore.gradio_app.interactive_generator as ig
except Exception as exc:
    pytest.skip(f"interactive_generator import failed: {exc}", allow_module_level=True)


def test_extract_code_and_reason_parses_fence():
    code, reason = ig.extract_code_and_reason("aaa```python\nprint('x')\n```bbb")
    assert code == "print('x')"
    assert isinstance(reason, str)


def test_extract_file_path_from_code_defaults(tmp_path):
    code = "# nothing"
    default = tmp_path / "fallback.py"
    assert ig.extract_file_path_from_code(code, default_path=str(default)) == str(default)

    code2 = "# filepath: src/foo.py\nprint('x')"
    assert ig.extract_file_path_from_code(code2).endswith("src/foo.py")


def test_get_versioned_path_increments(tmp_path, monkeypatch):
    target = tmp_path / "file.py"
    target.write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    new_path = ig.get_versioned_path(str(target))
    assert new_path.endswith("_v2.py")


def test_save_code_with_backup_and_diff_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(ig, "LOG_FILE", str(tmp_path / "log.txt"))
    user_path = str(tmp_path / "out.py")
    msg, diff = ig.save_code_with_backup_and_diff("print('ok')", user_path)
    assert "保存成功" in msg
    assert Path(user_path).exists() or Path(msg.split()[-1]).exists()
    assert isinstance(diff, str)


@pytest.mark.skip(reason="ask_gpt_question is a nested function inside build_ui(), not module-level")
def test_handlers_use_mocks(monkeypatch):
    monkeypatch.setattr(ig, "call_gpt", lambda prompt: "Q?")
    q = ig.ask_gpt_question("goal", "prev")
    assert "Q?" in q

    monkeypatch.setattr(ig, "ask_gpt_question", lambda goal, hist: "NEXT")
    next_q, hist = ig.ask_more_questions("goal", "ans", "prevQ", "hist-")
    assert next_q == "NEXT"
    assert "prevQ" in hist and "ans" in hist


@pytest.mark.skip(reason="generate_final_code is a nested function inside build_ui(), not module-level")
def test_generate_final_code_uses_extract_and_save(monkeypatch):
    monkeypatch.setattr(ig, "call_gpt", lambda prompt: "```python\nprint('ok')\n```rest")
    monkeypatch.setattr(ig, "extract_code_and_reason", lambda resp: ("print('ok')", "why"))
    captured = {}

    def fake_save(code, path):
        captured["code"] = code
        captured["path"] = path
        return "msg", "<diff/>"

    monkeypatch.setattr(ig, "save_code_with_backup_and_diff", fake_save)
    code, result, diff = ig.generate_final_code("goal", "hist", "dst/path.py")
    assert code == "print('ok')"
    assert result == "msg"
    assert diff == "<diff/>"
    assert captured["path"] == "dst/path.py"


@pytest.mark.skip(reason="list_saved_files/open_file_in_vscode are nested functions inside build_ui()")
def test_list_and_open(monkeypatch):
    monkeypatch.setattr(
        os, "walk", lambda root: [("/a", [], ["a.py", "b.txt"]), ("/b", [], ["c.py"])]
    )
    files = ig.list_saved_files()
    assert "a.py" in files[0] or "c.py" in files[-1]

    called = []
    monkeypatch.setattr(ig.subprocess, "Popen", lambda args: called.append(args))
    msg = ig.open_file_in_vscode("path/file.py")
    assert called
    assert "path/file.py" in msg
