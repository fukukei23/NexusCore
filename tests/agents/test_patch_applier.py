import types

from nexuscore.agents import patch_applier as pa_module
from nexuscore.agents.patch_applier import PatchApplier


class DummyPatchSet:
    def __init__(self, should_apply=True):
        self.should_apply = should_apply

    def apply(self, root, strip=0):
        self.root = root
        self.strip = strip
        return self.should_apply


def test_apply_returns_false_on_empty_cap(monkeypatch):
    applier = PatchApplier()
    assert applier.apply("", "/tmp") is False


def test_apply_success(monkeypatch, tmp_path):
    dummy_set = DummyPatchSet()

    def fake_fromstring(data):
        fake_fromstring.received = data
        return dummy_set

    fake_fromstring.received = None
    fake_patch = types.SimpleNamespace(fromstring=fake_fromstring)
    monkeypatch.setattr(pa_module, "patch", fake_patch)

    applier = PatchApplier()
    assert applier.apply("--- diff", str(tmp_path)) is True
    assert fake_fromstring.received == b"--- diff"
    assert dummy_set.root == str(tmp_path)


def test_apply_handles_parse_failure(monkeypatch):
    fake_patch = types.SimpleNamespace(fromstring=lambda data: None)
    monkeypatch.setattr(pa_module, "patch", fake_patch)

    applier = PatchApplier()
    assert applier.apply("bad", "/tmp") is False
