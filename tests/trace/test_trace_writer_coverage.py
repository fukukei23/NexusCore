"""Issue #74: trace_writer の未カバー行テスト"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from nexuscore.guard.policy_engine import GuardDecision, GuardInput, GuardResult, SecurityInput
from nexuscore.trace.trace_writer import (
    TraceWriter,
    _build_trace_event,
    _get_git_commit,
    _get_repo_dirty,
    write_guard_decision_event,
)


def _make_guard_input(**overrides):
    defaults = {
        "environment": "test",
        "security": SecurityInput(check_status="PASS"),
        "override": False,
    }
    defaults.update(overrides)
    return GuardInput(**defaults)


def _make_guard_result(decision=GuardDecision.ALLOW, reasons=None):
    return GuardResult(
        decision=decision,
        reasons=reasons or ["ok"],
    )


class TestGitHelpers:
    """lines 47-49, 66-68: git例外時の分岐"""

    def test_git_commit_exception(self):
        with patch("subprocess.run", side_effect=OSError("no git")):
            assert _get_git_commit() is None

    def test_git_commit_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            assert _get_git_commit() is None

    def test_repo_dirty_exception(self):
        with patch("subprocess.run", side_effect=OSError("no git")):
            assert _get_repo_dirty() is None


class TestBuildTraceEvent:
    """lines 117, 123: code_identityのnull分岐"""

    def test_git_commit_none(self):
        with patch("nexuscore.trace.trace_writer._get_git_commit", return_value=None):
            with patch("nexuscore.trace.trace_writer._get_repo_dirty", return_value=None):
                event = _build_trace_event(
                    "test", GuardDecision.ALLOW, ["ok"], _make_guard_input()
                )
        assert event["code_identity"]["git_commit"] is None
        assert event["code_identity"]["repo_dirty"] is None

    def test_with_override(self):
        inp = _make_guard_input(override=True)
        event = _build_trace_event("test", GuardDecision.ALLOW, ["ok"], inp)
        assert event["override"] is not None
        assert event["override"]["override"] is True

    def test_without_override(self):
        inp = _make_guard_input(override=False)
        event = _build_trace_event("test", GuardDecision.ALLOW, ["ok"], inp)
        assert event["override"] is None


class TestWriteGuardDecisionEvent:
    """line 162: デフォルトtrace_file"""

    def test_default_trace_file(self, tmp_path):
        with patch("nexuscore.trace.trace_writer.DEFAULT_TRACE_FILE", tmp_path / "trace.jsonl"):
            result = _make_guard_result()
            inp = _make_guard_input()
            write_guard_decision_event(result, inp)
            content = (tmp_path / "trace.jsonl").read_text()
            assert "guard_decision" in content


class TestTraceWriter:
    def test_write(self, tmp_path):
        trace_file = tmp_path / "out.jsonl"
        writer = TraceWriter(trace_file)
        result = _make_guard_result()
        inp = _make_guard_input()
        writer.write_guard_decision(result, inp)
        content = trace_file.read_text()
        assert "guard_decision" in content

    def test_default_file(self):
        writer = TraceWriter()
        assert writer.trace_file is not None
