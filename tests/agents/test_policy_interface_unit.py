from nexuscore.config.policy_interface import PolicyInterface


def test_safe_default_policy():
    pi = PolicyInterface()
    default = pi._get_safe_default_policy()
    assert default["test_import_policy"] == "関数を直接埋め込み"
    assert default["method"] == "safe_default"


def test_launch_and_wait_gradio_unavailable(monkeypatch):
    pi = PolicyInterface()
    monkeypatch.setattr(pi, "GRADIO_AVAILABLE", False, raising=False)
    result = pi.launch_and_wait_for_input(timeout=0)
    assert result["method"] == "safe_default"


def test_launch_timeout_returns_default(monkeypatch):
    pi = PolicyInterface()
    # force GRADIO_AVAILABLE True but create_gradio_interface raises to hit fallback
    monkeypatch.setattr(
        pi, "create_gradio_interface", lambda: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    result = pi.launch_and_wait_for_input(timeout=0)
    assert result["method"] == "safe_default"
