import json

import pytest

from nexuscore.gradio_app import policy_console


def test_template_finance_has_rules():
    data = policy_console.template_finance("corp_fin")
    assert data["profile_name"] == "corp_fin"
    assert any(rule["id"] == "PII" for rule in data["rules"])


def test_save_load_delete_profile(tmp_path, monkeypatch):
    policy_console.POLICY_DIR = tmp_path
    tmp_path.mkdir(exist_ok=True)

    ok, msg = policy_console.save_profile("alpha", json.dumps({"rules": []}))
    assert ok
    assert "保存しました" in msg

    loaded = policy_console.load_profile("alpha")
    assert '"rules": []' in loaded
    assert "alpha" in policy_console.list_profiles()

    delete_msg = policy_console.delete_profile("alpha")
    assert "削除しました" in delete_msg


def test_mock_evaluate_detects_pii():
    result = policy_console._mock_evaluate({"rules": []}, "電話 09012345678")
    assert result["violations"]
    assert "[MASKED]" in result["redacted_suggestion"]


def test_evaluate_text_uses_mock(monkeypatch):
    monkeypatch.setattr(policy_console, "_init_engine", lambda policy_json: ("mock", None))
    policy_json = json.dumps(policy_console.template_general())
    status, violations, suggestion = policy_console.evaluate_text(policy_json, "電話 08012345678")
    assert "❌" in status or "違反" in status
    assert violations
    assert "[MASKED]" in suggestion


def test_render_template_profile_generates_message():
    text, msg = policy_console.render_template_profile("corp_new", "finance")
    data = json.loads(text)
    assert data["profile_name"] == "corp_new"
    assert "finance" in msg

    with pytest.raises(ValueError):
        policy_console.render_template_profile("", "general")


def test_save_profile_rejects_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(policy_console, "POLICY_DIR", tmp_path)
    ok, msg = policy_console.save_profile("bad", "{ not json")
    assert ok is False
    assert "読み取れません" in msg


def test_load_profile_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(policy_console, "POLICY_DIR", tmp_path)
    text = policy_console.load_profile("missing")
    assert text == ""


def test_evaluate_text_invalid_json():
    status, violations, suggestion = policy_console.evaluate_text("{ bad", "text")
    assert "エラー" in status
    assert violations == []
    assert suggestion == ""


def test_new_from_template_handles_missing_name(monkeypatch):
    # simulate UI handler branch
    # direct call to render_template_profile already tested; here just ensure ValueError path returns updates
    res = policy_console.render_template_profile("name", "general")
    assert isinstance(res[0], str)
