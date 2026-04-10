import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.gradio_app import auto_revision_runner as runner


def test_load_policy_context_prefers_context_file(tmp_path, monkeypatch):
    src_root = tmp_path / "srcroot"
    ctx_dir = src_root / "gradio_app"
    ctx_dir.mkdir(parents=True)
    context_file = ctx_dir / ".nexus_context.json"
    context_file.write_text(
        json.dumps({"policy_profile": "alpha", "policy_version": "v9", "policy_icon": "🔥"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "SRC_ROOT", src_root)
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    result = runner.load_policy_context()
    assert result == {"policy_profile": "alpha", "policy_version": "v9", "policy_icon": "🔥"}


def test_load_policy_context_env_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "SRC_ROOT", tmp_path / "srcroot")
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("NEXUS_POLICY_PROFILE", "env")
    monkeypatch.setenv("NEXUS_POLICY_VERSION", "v2")
    monkeypatch.setenv("NEXUS_POLICY_ICON", "🧪")
    result = runner.load_policy_context()
    assert result == {"policy_profile": "env", "policy_version": "v2", "policy_icon": "🧪"}


@pytest.mark.parametrize(
    "ret, expected",
    [
        ((True, "log"), (True, "log")),
        (True, (True, "")),
        ("error", (False, "error")),
    ],
)
def test_coerce_bool_log(ret, expected):
    assert runner._coerce_bool_log(ret) == expected


def test_snapshot_sandbox_files(tmp_path, monkeypatch):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    file_path = sandbox / "foo.py"
    file_path.write_text("# sample", encoding="utf-8")
    monkeypatch.setattr(runner, "SANDBOX_DIRS", [sandbox])
    result = runner.snapshot_sandbox_files()
    assert result == {"foo.py": "# sample"}


def test_build_unified_diff(tmp_path):
    diff = runner.build_unified_diff({"a.py": "print(1)"}, {"a.py": "print(2)"})
    assert "a/a.py" in diff and "b/a.py" in diff


def test_write_patch_json(tmp_path, monkeypatch):
    patch_dir = tmp_path / "patch_history"
    patch_dir.mkdir()
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    monkeypatch.setattr(runner, "PATCH_DIR", patch_dir)
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "SANDBOX_DIRS", [sandbox])
    monkeypatch.setattr(runner, "now_iso", lambda: "2025-01-01T00:00:00+0900")
    out = runner.write_patch_json(
        timestamp="20250101_000000",
        status="success",
        reason="fixed",
        test_log="ok",
        code_diff="diff",
        policy={"policy_profile": "p", "policy_version": "v", "policy_icon": "🎯"},
        attempts=1,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["policy_icon"] == "🎯"


class TestReadJsonSafeException:
    def test_directory_returns_empty(self, tmp_path):
        p = tmp_path / "dir"
        p.mkdir()
        assert runner.read_json_safe(p) == {}


class TestStatusAttempt:
    def test_format(self):
        assert runner._status_attempt(3) == "attempt_3/5"


class TestReadFileTextException:
    def test_directory_returns_empty(self, tmp_path):
        p = tmp_path / "dir"
        p.mkdir()
        assert runner.read_file_text(p) == ""


class TestRunPytestOnceSubprocessException:
    def test_subprocess_error(self, monkeypatch):
        monkeypatch.setattr(runner, "RT", None)
        monkeypatch.setattr(runner, "PROJECT_ROOT", Path("/dummy"))
        with patch("subprocess.run", side_effect=OSError("no pytest")):
            ok, log = runner.run_pytest_once()
        assert ok is False
        assert "no pytest" in log


class TestAttemptAutoFixRT:
    def test_rt_auto_fix_success(self, monkeypatch):
        mock_rt = MagicMock()
        mock_rt.auto_fix_once.return_value = (True, "fixed", {"f.py": "code"})
        monkeypatch.setattr(runner, "RT", mock_rt)
        ok, log, changes = runner.attempt_auto_fix("error_log")
        assert ok is True
        assert changes == {"f.py": "code"}

    def test_rt_exception(self, monkeypatch):
        mock_rt = MagicMock()
        mock_rt.auto_fix_once.side_effect = RuntimeError("boom")
        monkeypatch.setattr(runner, "RT", mock_rt)
        ok, log, changes = runner.attempt_auto_fix("error_log")
        assert ok is False
        assert "boom" in log

    def test_no_rt_returns_fallback(self, monkeypatch):
        monkeypatch.setattr(runner, "RT", None)
        ok, log, changes = runner.attempt_auto_fix("error_log")
        assert ok is False
        assert "no available function" in log


class TestMainFunction:
    def test_initial_pass(self, tmp_path, monkeypatch):
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir()
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        monkeypatch.setattr(runner, "PATCH_DIR", patch_dir)
        monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(runner, "SANDBOX_DIRS", [sandbox])
        monkeypatch.setattr(runner, "RT", None)
        monkeypatch.setattr(
            runner, "load_policy_context",
            lambda: {"policy_profile": "test", "policy_version": "v1", "policy_icon": "X"},
        )
        monkeypatch.setattr(runner, "snapshot_sandbox_files", lambda: {})
        monkeypatch.setattr(runner, "run_pytest_once", lambda: (True, "all passed"))
        runner.main()
        # patch JSON should exist
        jsons = list(patch_dir.glob("patch_*.json"))
        assert len(jsons) == 1
        data = json.loads(jsons[0].read_text(encoding="utf-8"))
        assert data["status"] == "initial_pass"

    def test_initial_fail_then_auto_fix_success(self, tmp_path, monkeypatch):
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir()
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        monkeypatch.setattr(runner, "PATCH_DIR", patch_dir)
        monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(runner, "SANDBOX_DIRS", [sandbox])
        monkeypatch.setattr(runner, "RT", None)
        monkeypatch.setattr(
            runner, "load_policy_context",
            lambda: {"policy_profile": "test", "policy_version": "v1", "policy_icon": "X"},
        )
        monkeypatch.setattr(runner, "snapshot_sandbox_files", lambda: {})
        call_count = {"n": 0}

        def mock_run_pytest():
            call_count["n"] += 1
            if call_count["n"] == 1:
                return (False, "initial fail")
            return (True, "fixed")

        monkeypatch.setattr(runner, "run_pytest_once", mock_run_pytest)
        monkeypatch.setattr(
            runner, "attempt_auto_fix",
            lambda log: (True, "fixed", {}),
        )
        runner.main()
        jsons = sorted(patch_dir.glob("patch_*.json"))
        statuses = [json.loads(j.read_text(encoding="utf-8"))["status"] for j in jsons]
        assert "attempt_error" in statuses or "success" in statuses

    def test_auto_fix_with_changes(self, tmp_path, monkeypatch):
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir()
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        monkeypatch.setattr(runner, "PATCH_DIR", patch_dir)
        monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(runner, "SANDBOX_DIRS", [sandbox])
        monkeypatch.setattr(runner, "RT", None)
        monkeypatch.setattr(
            runner, "load_policy_context",
            lambda: {"policy_profile": "test", "policy_version": "v1", "policy_icon": "X"},
        )
        monkeypatch.setattr(runner, "snapshot_sandbox_files", lambda: {})
        call_count = {"n": 0}

        def mock_run_pytest():
            call_count["n"] += 1
            if call_count["n"] == 1:
                return (False, "initial fail")
            return (True, "fixed")

        monkeypatch.setattr(runner, "run_pytest_once", mock_run_pytest)
        monkeypatch.setattr(
            runner, "attempt_auto_fix",
            lambda log: (True, "fixed", {"subdir/fix.py": "print('fixed')"}),
        )
        runner.main()
        # sandbox file should be written
        written = (sandbox / "subdir" / "fix.py")
        assert written.exists()
        assert written.read_text(encoding="utf-8") == "print('fixed')"

    def test_auto_fix_loop_exception(self, tmp_path, monkeypatch):
        patch_dir = tmp_path / "patch_history"
        patch_dir.mkdir()
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        monkeypatch.setattr(runner, "PATCH_DIR", patch_dir)
        monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(runner, "SANDBOX_DIRS", [sandbox])
        monkeypatch.setattr(runner, "RT", None)
        monkeypatch.setattr(
            runner, "load_policy_context",
            lambda: {"policy_profile": "test", "policy_version": "v1", "policy_icon": "X"},
        )
        monkeypatch.setattr(runner, "snapshot_sandbox_files", lambda: {})
        monkeypatch.setattr(runner, "run_pytest_once", lambda: (False, "fail"))
        monkeypatch.setattr(
            runner, "attempt_auto_fix",
            MagicMock(side_effect=RuntimeError("unexpected")),
        )
        runner.main()
        jsons = sorted(patch_dir.glob("patch_*.json"))
        statuses = [json.loads(j.read_text(encoding="utf-8"))["status"] for j in jsons]
        assert any("attempt_error" in s for s in statuses)
