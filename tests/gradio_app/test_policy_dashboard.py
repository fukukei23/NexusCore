import json

from nexuscore.archive.gradio_app import policy_dashboard


def test_load_policy_defaults(tmp_path, monkeypatch):
    policy_dashboard.POLICY_FILE = tmp_path / "constitution.json"
    result = policy_dashboard._load_policy()
    assert "meta" in result and result["meta"]["version"] == "1.0"


def test_save_policy_writes_file(tmp_path, monkeypatch):
    policy_dashboard.POLICY_FILE = tmp_path / "constitution.json"
    policy = policy_dashboard._load_policy()
    policy["meta"]["org_name"] = "TestOrg"
    policy_dashboard._save_policy(policy)
    saved = json.loads(policy_dashboard.POLICY_FILE.read_text(encoding="utf-8"))
    assert saved["meta"]["org_name"] == "TestOrg"
    assert saved["meta"]["last_updated"]


def test_validate_policy_detects_errors():
    policy = policy_dashboard._load_policy()
    policy["meta"]["org_name"] = ""
    policy["meta"]["sector"] = "finance"
    policy["redlines"] = []
    policy["pii_policy"]["storage"] = "invalid"
    policy["output_rules"]["language"] = "fr"
    ok, errors = policy_dashboard._validate_policy(policy)
    assert not ok
    assert len(errors) == 4


def test_assemble_policy_payload_builds_defaults():
    assembled, meta = policy_dashboard.assemble_policy_payload(
        "Org",
        "Owner",
        "finance",
        "v2",
        [["RL-1", "text", ""]],
        True,
        False,
        "***",
        "ephemeral",
        30,
        "en",
        "friendly",
        True,
        False,
        "disc",
        "openai",
        "gpt-4o",
        0.5,
        1024,
    )
    assert meta["org_name"] == "Org"
    assert assembled["redlines"][0]["severity"] == "high"
    assert assembled["pii_policy"]["retention_days"] == 30
    assert assembled["model_policy"]["temperature"] == 0.5
    assert assembled["model_policy"]["max_tokens"] == 1024


def test_validation_summary_formats_errors():
    policy = policy_dashboard._load_policy()
    policy["meta"]["org_name"] = ""
    message = policy_dashboard.validation_summary(policy)
    assert message.startswith("⚠️")

    policy["meta"]["org_name"] = "OkOrg"
    policy["meta"]["sector"] = "general"
    policy["output_rules"]["language"] = "ja"
    policy["redlines"] = [{"id": "r1", "text": "t", "severity": "high"}]
    policy["pii_policy"]["storage"] = "forbidden"
    message_ok = policy_dashboard.validation_summary(policy)
    assert message_ok.startswith("✅")


def test_safe_int_and_float_defaults():
    assert policy_dashboard._safe_int("x", 5) == 5
    assert policy_dashboard._safe_float("y", 1.2) == 1.2


def test_assemble_policy_payload_handles_empty(monkeypatch):
    assembled, meta = policy_dashboard.assemble_policy_payload(
        "",
        "",
        "",
        "",
        [],
        False,
        False,
        "",
        "",
        None,
        "",
        "",
        False,
        False,
        "",
        "",
        "",
        None,
        None,
    )
    assert meta["org_name"] == ""
    assert assembled["pii_policy"]["retention_days"] == 0
    assert assembled["model_policy"]["temperature"] == 0.2
