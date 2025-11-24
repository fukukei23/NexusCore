import json
import pytest
from nexuscore.gradio_app import policy_console


def test_save_profile_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(policy_console, "POLICY_DIR", tmp_path)
    ok, msg = policy_console.save_profile("name", "{ bad")
    assert ok is False
    assert "読み取れません" in msg


def test_delete_profile_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(policy_console, "POLICY_DIR", tmp_path)
    msg = policy_console.delete_profile("missing")
    assert "見つかりません" in msg


def test_evaluate_text_engine_exception(monkeypatch):
    class Engine:
        def evaluate(self, text):
            raise RuntimeError("boom")

    monkeypatch.setattr(policy_console, "_init_engine", lambda pj: ("real", Engine()))
    status, violations, suggestion = policy_console.evaluate_text("{}", "text")
    assert "エラー" in status or "boom" in status
    assert violations == []


def test_render_template_profile_unknown_key():
    text, msg = policy_console.render_template_profile("name", "unknown_key")
    data = json.loads(text)
    assert data["profile_name"] == "name"
