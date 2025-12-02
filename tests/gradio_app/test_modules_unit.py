from pathlib import Path
from types import SimpleNamespace

import pytest

from nexuscore.modules import chat_handler, code_generator, diff_viewer, history_viewer, tester, whisper_handler


# whisper がインストールされていない環境では、
# このモジュール全体をスキップする
pytestmark = pytest.mark.skipif(
    getattr(whisper_handler, "WHISPER_AVAILABLE", False) is False,
    reason="whisper is not installed; skipping whisper-dependent module tests",
)


def test_chat_handler_returns_error_on_exception(monkeypatch):
    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("boom")

    monkeypatch.setattr(chat_handler, "client", FakeClient())
    msg, history = chat_handler.handle_chat("hi", [])
    assert "エラー" in msg and isinstance(history, list)


def test_code_generator_returns_error(monkeypatch):
    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("fail")

    monkeypatch.setattr(code_generator, "client", FakeClient())
    out = code_generator.generate_code_from_text("do something")
    assert "failed" in out or "⚠️" in out


def test_diff_viewer_simple():
    diff = diff_viewer.generate_diff("a\n", "b\n")
    assert "-a" in diff and "+b" in diff


def test_history_viewer_loads_and_formats(tmp_path, monkeypatch):
    (tmp_path / "patch_history").mkdir()
    data = {"timestamp": "20250101", "test_log": "failed", "reason": "something bad"}
    (tmp_path / "patch_history" / "patch_1.json").write_text(
        '{"timestamp":"20250101","test_log":"failed","reason":"reason text"}', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    entries = history_viewer.load_history(directory="patch_history")
    assert entries
    md = history_viewer.format_history_markdown(entries)
    assert "修正履歴一覧" in md


def test_tester_save_and_test_code(monkeypatch, tmp_path):
    monkeypatch.setattr(tester, "SANDBOX_DIR", tmp_path)
    monkeypatch.setattr(tester, "SAMPLE_FILE", str(tmp_path / "sample.py"))
    monkeypatch.setattr(tester, "TEST_FILE", str(tmp_path / "test_sample.py"))
    monkeypatch.setattr(tester, "RESULT_LOG", str(tmp_path / "test_result.log"))

    fake = SimpleNamespace(returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(tester.subprocess, "run", lambda *a, **k: fake)

    out = tester.save_and_test_code("def foo():\n    return 1")
    assert "ok" in out
    assert Path(tester.RESULT_LOG).exists()


def test_whisper_handler_transcribe_error(monkeypatch):
    class FakeModel:
        def transcribe(self, audio_path):
            raise RuntimeError("no audio")

    # _get_model() をモックして FakeModel を返すようにする
    monkeypatch.setattr(whisper_handler, "_get_model", lambda: FakeModel())
    text = whisper_handler.transcribe_audio("none.wav")
    assert "エラー" in text or "error" in text.lower()
