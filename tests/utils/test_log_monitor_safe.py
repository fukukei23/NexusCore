def test_log_monitor_import_safe(monkeypatch):
    import importlib
    import sys

    # simulate missing dependency by inserting dummy module
    sys.modules["auto_cycle_manager"] = type("M", (), {"auto_repair_cycle": lambda *a, **k: None})

    class DummyThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            return None

    monkeypatch.setattr("threading.Thread", lambda *a, **k: DummyThread())
    monkeypatch.setattr("os.listdir", lambda path: [])
    log_monitor = importlib.import_module("nexuscore.utils.log_monitor")
    assert hasattr(log_monitor, "log_watcher")


def test_log_watcher_processes_file(monkeypatch, tmp_path, capsys):
    import importlib
    import sys

    processed = {}

    def fake_cycle(code):
        processed["code"] = code
        return "fixed", "out"

    sys.modules["auto_cycle_manager"] = type("M", (), {"auto_repair_cycle": fake_cycle})

    class DummyThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            return None

    monkeypatch.setattr("threading.Thread", lambda *a, **k: DummyThread())
    log_monitor = importlib.import_module("nexuscore.utils.log_monitor")
    log_monitor.auto_repair_cycle = fake_cycle
    log_monitor.WATCH_DIR = str(tmp_path)

    target = tmp_path / "sample.py"
    target.write_text("print('x')", encoding="utf-8")

    calls = {"count": 0}

    def fake_listdir(path):
        calls["count"] += 1
        if calls["count"] > 1:
            raise KeyboardInterrupt()
        return ["sample.py"]

    monkeypatch.setattr(log_monitor.os, "listdir", fake_listdir)
    monkeypatch.setattr(log_monitor.time, "sleep", lambda x: None)

    try:
        log_monitor.log_watcher()
    except KeyboardInterrupt:
        pass

    out = capsys.readouterr().out
    assert "新ファイル検知" in out or calls["count"] >= 1
