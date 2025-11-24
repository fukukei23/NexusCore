import pytest

from nexuscore.agents import policy_interface as policy_module
from nexuscore.agents.policy_interface import PolicyInterface


@pytest.fixture(autouse=True)
def disable_gradio(monkeypatch):
    monkeypatch.setattr(policy_module, "GRADIO_AVAILABLE", False)


def test_launch_and_wait_returns_safe_default():
    interface = PolicyInterface()
    policy = interface.launch_and_wait_for_input(timeout=1)
    assert policy["method"] == "safe_default"
    assert policy["test_import_policy"] == "関数を直接埋め込み"


def test_default_policy_method():
    interface = PolicyInterface()
    policy = interface._get_default_policy()
    safe_policy = interface._get_safe_default_policy()
    for key in safe_policy:
        if key == "configured_at":
            continue
        assert policy[key] == safe_policy[key]
