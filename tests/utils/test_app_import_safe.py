import importlib
import sys


def test_app_imports_with_mocks(monkeypatch):
    class DummyFlask:
        def __init__(self, *a, **k):
            pass

        def register_blueprint(self, bp):
            self.bp = bp

        def run(self, *a, **k):
            return None

    # monkeypatch.setitem を使って sys.modules を安全に変更（テスト終了後に自動復元）
    monkeypatch.setitem(sys.modules, "flask", type("M", (), {"Flask": DummyFlask}))
    monkeypatch.setitem(sys.modules, "routes_ai_repair", type("M", (), {"bp": object()}))
    monkeypatch.setitem(sys.modules, "gradio_ui", type("M", (), {"gradio_launch": lambda: None}))

    class DummyThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            return None

    monkeypatch.setattr("threading.Thread", lambda *a, **k: DummyThread())

    app_mod = importlib.import_module("nexuscore.utils.app")
    assert hasattr(app_mod, "app")
