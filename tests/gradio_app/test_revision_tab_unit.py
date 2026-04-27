import json
from pathlib import Path
from types import SimpleNamespace

from nexuscore.archive.gradio_app import revision_tab


def test_extract_code_and_reason_handles_json_and_fence():
    code, reason = revision_tab.extract_code_and_reason(
        json.dumps({"code": "print('hi')", "reason": "ok"})
    )
    assert code == "print('hi')"
    assert reason == "ok"

    code2, reason2 = revision_tab.extract_code_and_reason("text\n```python\nx=1\n```\nmore")
    assert code2 == "x=1"
    assert "more" in reason2


def test_generate_prompt_includes_sections(tmp_path, monkeypatch):
    sample = tmp_path / "sample.py"
    testf = tmp_path / "test_sample.py"
    sample.write_text("def add(a,b): return a+b", encoding="utf-8")
    testf.write_text("def test_add(): assert add(1,2)==3", encoding="utf-8")

    prompt = revision_tab.generate_prompt(
        str(sample), str(testf), "summary", "hist", "errs", "note"
    )
    assert "sample.py" in prompt
    assert "test_sample.py" in prompt
    assert "summary" in prompt
    assert "note" in prompt


def test_save_patch_history_json_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(revision_tab, "PATCH_HISTORY_DIR", tmp_path)
    monkeypatch.setattr(revision_tab, "RESULT_LOG", str(tmp_path / "log.txt"))
    (tmp_path / "log.txt").write_text("pytest ok", encoding="utf-8")

    out_path = revision_tab.save_patch_history_json("code", "reason", "prompt")
    saved = json.loads(Path(out_path).read_text(encoding="utf-8"))
    assert saved["reason"] == "reason"
    assert saved["test_log"] == "pytest ok"


def test_run_pytest_success(monkeypatch):
    fake_result = SimpleNamespace(returncode=0, stdout="passed", stderr="")
    monkeypatch.setattr(revision_tab.subprocess, "run", lambda *a, **k: fake_result)
    ok, output = revision_tab.run_pytest()
    assert ok is True
    assert "passed" in output


def test_run_pytest_exception(monkeypatch):
    monkeypatch.setattr(
        revision_tab.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    ok, output = revision_tab.run_pytest()
    assert ok is False
    assert "pytest 実行エラー" in output
