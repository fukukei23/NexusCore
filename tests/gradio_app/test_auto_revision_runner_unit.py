import json
from pathlib import Path

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
