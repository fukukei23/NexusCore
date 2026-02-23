from nexuscore.gradio_app import policy_dashboard


def test_validation_summary_invalid_language():
    policy = policy_dashboard._load_policy()
    policy["meta"]["org_name"] = "Org"
    policy["output_rules"]["language"] = "xx"
    msg = policy_dashboard.validation_summary(policy)
    assert msg.startswith("⚠️")


def test_assemble_policy_payload_bad_numbers():
    assembled, meta = policy_dashboard.assemble_policy_payload(
        "Org",
        "Owner",
        "finance",
        "v1",
        [],
        True,
        True,
        "",
        "",
        "not-int",
        "ja",
        "professional",
        False,
        True,
        "",
        "openai",
        "model",
        "bad-float",
        "bad-int",
    )
    assert assembled["pii_policy"]["retention_days"] == 0
    assert assembled["model_policy"]["max_tokens"] == 2000


def test_validate_policy_warns_finance_without_redline():
    policy = policy_dashboard._load_policy()
    policy["meta"]["org_name"] = "Org"
    policy["meta"]["sector"] = "finance"
    policy["redlines"] = []
    ok, errs = policy_dashboard._validate_policy(policy)
    assert ok is False
    assert any("レッドライン" in e for e in errs)
