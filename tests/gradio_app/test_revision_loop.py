import json
from types import SimpleNamespace

from nexuscore.gradio_app import revision_loop


def test_save_and_read_file(tmp_path):
    target = tmp_path / "file.txt"
    revision_loop.save_file(str(target), "hello")
    assert revision_loop.read_file(str(target)) == "hello"


def test_generate_prompt_contains_sections():
    prompt = revision_loop.generate_prompt(
        "main.py",
        "utils.py",
        "v1",
        "history",
        "tests failing",
        "extra instruction",
    )
    assert "main.py" in prompt
    assert "extra instruction" in prompt


def test_extract_code_and_reason():
    response = """【修正版コード】
```python
print("ok")
```
【修正理由・要約】
理由です
"""
    code, reason = revision_loop.extract_code_and_reason(response)
    assert 'print("ok")' in code
    assert "理由" in reason


def test_run_pytest_success(monkeypatch, tmp_path):
    revision_loop.TEST_FILE = str(tmp_path / "test_sample.py")
    revision_loop.RESULT_LOG = str(tmp_path / "result.log")

    def fake_run(cmd, stdout, stderr, text):
        assert cmd == ["pytest", revision_loop.TEST_FILE]
        return SimpleNamespace(stdout="ok", stderr="err", returncode=0)

    monkeypatch.setattr(revision_loop.subprocess, "run", fake_run)
    output = revision_loop.run_pytest()
    assert "ok" in output and "err" in output


def test_save_patch_history(tmp_path, monkeypatch):
    log_file = tmp_path / "result.log"
    log_file.write_text("pytest log", encoding="utf-8")
    revision_loop.RESULT_LOG = str(log_file)
    revision_loop.HISTORY_DIR = str(tmp_path / "patch_history")
    (tmp_path / "patch_history").mkdir(parents=True, exist_ok=True)

    revision_loop.save_patch_history("print('ok')", "reason", "prompt")

    files = list((tmp_path / "patch_history").glob("patch_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["code"] == "print('ok')"
    assert data["reason"] == "reason"
