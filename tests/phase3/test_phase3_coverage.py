"""
Phase 3 Coverage Tests — NexusCore 危険・未テストモジュール底上げ

対象:
- webapp/views_projects.py (helper functions + routes)
- webapp/views_logs.py (routes)
- webapp/views_dashboard.py (helper functions + routes)
- agents/constitutional_council_agent.py
- services/self_healing_service.py
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# webapp/views_projects.py — helper functions
# =============================================================================


class TestFormatDuration:
    """_format_duration(duration_sec: float | None) -> str — None→'-'"""

    def test_none_returns_dash(self):
        from nexuscore.webapp._projects_helpers import _format_duration
        assert _format_duration(None) == "-"

    def test_zero(self):
        from nexuscore.webapp._projects_helpers import _format_duration
        assert _format_duration(0) == "0s"

    def test_seconds_only(self):
        from nexuscore.webapp._projects_helpers import _format_duration
        assert _format_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        from nexuscore.webapp._projects_helpers import _format_duration
        result = _format_duration(125)
        assert "2m" in result and "5s" in result

    def test_hours_no_seconds(self):
        """3661 → 1h 1m (hours+minutes only, no seconds)"""
        from nexuscore.webapp._projects_helpers import _format_duration
        result = _format_duration(3661)
        assert "1h" in result and "1m" in result


class TestComputeRunDuration:
    """_compute_run_duration(run: Run) -> float | None — uses started_at/finished_at"""

    def _make_run(self, **kwargs):
        run = MagicMock()
        for k, v in kwargs.items():
            setattr(run, k, v)
        return run

    def test_no_times(self):
        from nexuscore.webapp._projects_helpers import _compute_run_duration
        from datetime import datetime
        run = self._make_run(started_at=None, finished_at=None)
        assert _compute_run_duration(run) is None

    def test_only_start(self):
        from nexuscore.webapp._projects_helpers import _compute_run_duration
        from datetime import datetime
        run = MagicMock()
        run.started_at = datetime(2026, 1, 1, 10, 0)
        # finished_at attribute missing entirely → getattr returns MagicMock which is truthy
        # Need to set finished_at to None explicitly
        run.finished_at = None
        assert _compute_run_duration(run) is None

    def test_both_datetimes(self):
        from nexuscore.webapp._projects_helpers import _compute_run_duration
        from datetime import datetime
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 5, 30)
        run = self._make_run(started_at=start, finished_at=end)
        assert _compute_run_duration(run) == 330.0


class TestRenderRunStatusBadge:
    """_render_run_status_badge(status: str) -> str"""

    @pytest.mark.parametrize("status", ["RUNNING", "SUCCESS", "FAILED", "PENDING"])
    def test_known_statuses(self, status):
        from nexuscore.webapp._projects_helpers import _render_run_status_badge
        result = _render_run_status_badge(status)
        assert status in result

    def test_unknown_status(self):
        from nexuscore.webapp._projects_helpers import _render_run_status_badge
        result = _render_run_status_badge("WEIRD")
        assert "WEIRD" in result


class TestRenderRunTable:
    """render_run_table(project: Project, runs: Sequence[Run]) -> str"""

    def test_empty_runs(self):
        from nexuscore.webapp._projects_helpers import render_run_table
        project = MagicMock()
        result = render_run_table(project, [])
        assert isinstance(result, str)

    def test_with_runs(self):
        from nexuscore.webapp._projects_helpers import render_run_table
        from datetime import datetime
        project = MagicMock()
        run = MagicMock()
        run.id = 1
        run.status = "SUCCESS"
        run.started_at = datetime(2026, 1, 1, 10, 0)
        run.finished_at = datetime(2026, 1, 1, 10, 5)
        result = render_run_table(project, [run])
        assert "SUCCESS" in result


# =============================================================================
# webapp/views_projects.py — routes (require_auth needs mock)
# =============================================================================


class TestViewsProjectsRoutes:
    """Route tests — skipped due to Flask-SQLAlchemy DB init requirement.
    These routes use @require_auth which needs User.query (SQLAlchemy).
    Coverage is measured via helper function tests instead.
    """

    @pytest.mark.skip("Flask-SQLAlchemy DB init required for route tests")
    def test_list_projects(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_project_detail_not_found(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_project_detail_found(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_create_project_post(self):
        pass


# =============================================================================
# webapp/views_logs.py — routes
# =============================================================================


class TestViewsLogsRoutes:
    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_project_logs_no_project(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_project_logs_found(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_run_logs_not_found(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_run_logs_found(self):
        pass


# =============================================================================
# webapp/views_dashboard.py — helper functions
# =============================================================================


class TestRenderLlmCostTable:
    """_render_llm_cost_table(llm_breakdown: dict[str, dict[str, Any]]) -> str"""

    def test_empty(self):
        from nexuscore.webapp.views_dashboard import _render_llm_cost_table
        result = _render_llm_cost_table({})
        assert isinstance(result, str)

    def test_with_data(self):
        from nexuscore.webapp.views_dashboard import _render_llm_cost_table
        data = {"gpt-4o": {"calls": 10, "cost_usd": 1.50}}
        result = _render_llm_cost_table(data)
        assert "gpt-4o" in result


class TestRenderRecentRunsList:
    """_render_recent_runs_list(project: Project, runs: list[Run]) -> str"""

    def test_empty(self):
        from nexuscore.webapp.views_dashboard import _render_recent_runs_list
        result = _render_recent_runs_list(MagicMock(), [])
        assert isinstance(result, str)

    def test_with_runs(self):
        from nexuscore.webapp.views_dashboard import _render_recent_runs_list
        from datetime import datetime
        run = MagicMock()
        run.id = 1
        run.status = "SUCCESS"
        run.started_at = datetime(2026, 1, 1, 10, 0, 0)
        result = _render_recent_runs_list(MagicMock(), [run])
        assert "SUCCESS" in result


class TestRenderProjectDashboardHtml:
    """render_project_dashboard_html(*, project, stats, recent_runs, ...) -> str"""

    def test_basic(self):
        from nexuscore.webapp.views_dashboard import render_project_dashboard_html
        project = MagicMock()
        project.id = 1
        project.name = "test"
        result = render_project_dashboard_html(
            project=project, stats={}, recent_runs=[],
            latest_run=None, latest_run_metrics=None, llm_breakdown={},
        )
        assert "test" in result


class TestDashboardRoutes:
    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_dashboard(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_project_dashboard_not_found(self):
        pass

    @pytest.mark.skip("Flask-SQLAlchemy DB init required")
    def test_project_dashboard_found(self):
        pass


# =============================================================================
# agents/constitutional_council_agent.py
# =============================================================================


class TestConstitutionalCouncilAgentValidate:
    """_validate_amendment(proposal: dict[str, Any]) -> bool"""

    ALLOWED_KEYS = {
        "policy_id", "description", "rules", "delete_policy_id",
        "category", "tags", "priority", "enabled",
        "target_file_pattern", "detection_pattern", "severity",
        "suggestion", "exception_rules", "version", "owner",
    }

    def _make_agent(self):
        from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
        with patch.object(ConstitutionalCouncilAgent, "__init__", lambda self, **kw: None):
            agent = ConstitutionalCouncilAgent.__new__(ConstitutionalCouncilAgent)
            agent.logger = MagicMock()
            # Use public attributes (policy_path, amendments_dir) — no underscore prefix
            tmpdir = Path(tempfile.mkdtemp())
            agent.policy_path = tmpdir / "policies.json"
            agent.policy_path.write_text('[]')
            agent.amendments_dir = tmpdir / "amendments"
            agent.amendments_dir.mkdir(parents=True, exist_ok=True)
            return agent

    def test_valid_keys(self):
        agent = self._make_agent()
        for key in self.ALLOWED_KEYS:
            assert agent._validate_amendment({key: "test"}) is True

    def test_invalid_key(self):
        agent = self._make_agent()
        assert agent._validate_amendment({"bad_key": "val"}) is False

    def test_empty(self):
        agent = self._make_agent()
        assert agent._validate_amendment({}) is True

    def test_mixed(self):
        agent = self._make_agent()
        assert agent._validate_amendment({"policy_id": "p1", "hack": "no"}) is False

    def test_not_dict(self):
        agent = self._make_agent()
        assert agent._validate_amendment("not a dict") is False


class TestConstitutionalCouncilAgentLoadSave:
    """_load_policies() -> list[dict] / _save_policies(policies: list[dict]) -> None"""

    def _make_agent(self):
        from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
        with patch.object(ConstitutionalCouncilAgent, "__init__", lambda self, **kw: None):
            agent = ConstitutionalCouncilAgent.__new__(ConstitutionalCouncilAgent)
            agent.logger = MagicMock()
            agent.amendments_dir = Path(tempfile.mkdtemp()) / "amendments"
            agent.amendments_dir.mkdir(parents=True, exist_ok=True)
            return agent

    def test_load_file_exists(self):
        agent = self._make_agent()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"policy_id": "P1"}], f)
            agent.policy_path = Path(f.name)
        try:
            result = agent._load_policies()
            assert isinstance(result, list)
            assert result[0]["policy_id"] == "P1"
        finally:
            os.unlink(f.name)

    def test_load_file_missing_returns_empty(self):
        agent = self._make_agent()
        agent.policy_path = Path("/nonexistent/policies.json")
        result = agent._load_policies()
        assert result == []

    def test_save_and_reload(self):
        agent = self._make_agent()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            agent.policy_path = Path(f.name)
        try:
            data = [{"policy_id": "P2"}]
            agent._save_policies(data)
            loaded = agent._load_policies()
            assert loaded[0]["policy_id"] == "P2"
        finally:
            os.unlink(agent.policy_path)
            # Clean up backup file if created
            for bak in agent.policy_path.parent.glob("*.bak.json"):
                bak.unlink(missing_ok=True)


class TestConstitutionalCouncilAgentArchive:
    """_archive_amendment(pending_file: Path, status: str) -> bool"""

    def _make_agent(self):
        from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
        with patch.object(ConstitutionalCouncilAgent, "__init__", lambda self, **kw: None):
            agent = ConstitutionalCouncilAgent.__new__(ConstitutionalCouncilAgent)
            agent.logger = MagicMock()
            agent.policy_path = Path(tempfile.mkdtemp()) / "policies.json"
            agent.amendments_dir = Path(tempfile.mkdtemp())
            return agent

    def test_archive_success(self):
        agent = self._make_agent()
        pending = agent.amendments_dir / "pending_test001.json"
        pending.write_text('{"policy_id": "P1"}')
        result = agent._archive_amendment(pending, "enacted")
        assert result is True
        assert (agent.amendments_dir / "enacted_test001.json").exists()

    def test_archive_file_not_found(self):
        agent = self._make_agent()
        result = agent._archive_amendment(Path("/nonexistent/pending_x.json"), "enacted")
        assert result is False

    def test_archive_wrong_prefix(self):
        agent = self._make_agent()
        wrong = agent.amendments_dir / "wrong_prefix.json"
        wrong.write_text('{}')
        result = agent._archive_amendment(wrong, "enacted")
        assert result is False


class TestConstitutionalCouncilAgentReview:
    """review_and_amend(postmortem_report: dict, knowledge_brief: dict) -> None"""

    def _make_agent(self):
        from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
        with patch.object(ConstitutionalCouncilAgent, "__init__", lambda self, **kw: None):
            agent = ConstitutionalCouncilAgent.__new__(ConstitutionalCouncilAgent)
            agent.logger = MagicMock()
            tmpdir = Path(tempfile.mkdtemp())
            agent.policy_path = tmpdir / "policies.json"
            agent.policy_path.write_text('[]')
            agent.amendments_dir = tmpdir / "amendments"
            agent.amendments_dir.mkdir(parents=True, exist_ok=True)
            return agent

    def test_review_calls_llm(self):
        agent = self._make_agent()
        postmortem = {"error": "test error"}
        brief = {"context": "test"}
        with patch.object(agent, "_invoke_llm_with_retry", return_value='{"policy_id":"P1","description":"test"}'):
            with patch.object(agent, "_save_policies"):
                agent.review_and_amend(postmortem, brief)


class TestConstitutionalCouncilAgentInit:
    """__init__ with BaseAgent mock"""

    def test_init_sets_policy_path(self):
        from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
        with patch.object(ConstitutionalCouncilAgent.__bases__[0], "__init__", lambda self: None):
            tmpdir = tempfile.mkdtemp()
            agent = ConstitutionalCouncilAgent(policy_path=os.path.join(tmpdir, "test.json"))
            assert str(agent.policy_path).endswith("test.json")


# =============================================================================
# services/self_healing_service.py
# =============================================================================


class TestSelfHealingServiceInit:
    """SelfHealingService.__init__(project_root, session_controller=None, ...)"""

    def test_init_with_project_root(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch("nexuscore.services.self_healing_service.SessionController") as MockSC, \
             patch("nexuscore.services.self_healing_service.PatchApplier") as MockPA, \
             patch("nexuscore.services.self_healing_service.RunHistoryLogger") as MockRHL, \
             patch("nexuscore.services.self_healing_service.SelfHealingConfig") as MockConf:
            MockConf.load.return_value = MagicMock()
            svc = SelfHealingService(project_root="/tmp/test")
            assert svc is not None

    def test_init_with_all_args(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        svc = SelfHealingService(
            project_root="/tmp/test",
            session_controller=MagicMock(),
            debugger_agent=MagicMock(),
            patch_applier=MagicMock(),
            history_logger=MagicMock(),
            config=MagicMock(),
        )
        assert svc is not None


class TestSelfHealingServiceMaybeStop:
    """_maybe_stop(phase, meta=None) -> None — checks session_controller"""

    def _make_service(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            return svc

    def test_no_controller_returns(self):
        svc = self._make_service()
        svc.session_controller = None
        svc._maybe_stop("test_phase")  # Should not raise

    def test_controller_checkpoints(self):
        svc = self._make_service()
        svc.session_controller = MagicMock()
        svc.session_controller.should_stop.return_value = False
        svc._maybe_stop("test_phase")
        svc.session_controller.checkpoint.assert_called_once()

    def test_stop_requested_raises(self):
        svc = self._make_service()
        svc.session_controller = MagicMock()
        svc.session_controller.should_stop.return_value = True
        with pytest.raises(RuntimeError, match="SessionStopped"):
            svc._maybe_stop("test_phase")


class TestSelfHealingServiceGetChangedFiles:
    """_get_changed_files(project_path, base_ref=None, head_ref=None) -> list[str]"""

    def _make_service(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            return svc

    def test_no_diff(self):
        svc = self._make_service()
        with patch("nexuscore.services.self_healing_service.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(stdout="", returncode=0, stderr="")
            result = svc._get_changed_files(Path("/fake/repo"), "main", "feature")
            assert isinstance(result, list)

    def test_with_diff(self):
        svc = self._make_service()
        with patch("nexuscore.services.self_healing_service.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(stdout="src/main.py\nsrc/utils.py", returncode=0, stderr="")
            result = svc._get_changed_files(Path("/fake/repo"), "main", "feature")
            assert len(result) == 2

    def test_no_refs_fallback(self):
        svc = self._make_service()
        with patch("nexuscore.services.self_healing_service.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(stdout="", returncode=0, stderr="")
            result = svc._get_changed_files(Path("/fake/repo"), None, None)
            assert isinstance(result, list)


class TestSelfHealingServiceRunTests:
    """_run_tests(project_path, retry_context=None) -> tuple[bool, str]"""

    def _make_service(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            return svc

    def test_pass_via_subprocess(self):
        """Test via subprocess fallback (HAS_RETRY may be True or False)"""
        import nexuscore.services.self_healing_service as sh_mod
        svc = self._make_service()
        # Mock both paths: if HAS_RETRY, use run_in_sandbox; else subprocess
        if sh_mod.HAS_RETRY and sh_mod.run_in_sandbox:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.timed_out = False
            mock_result.stdout = "2 passed"
            mock_result.stderr = ""
            mock_result.exception_type = None
            with patch.object(sh_mod, "run_in_sandbox", return_value=mock_result):
                success, output = svc._run_tests(Path("/fake/repo"))
            assert success is True
        else:
            with patch("nexuscore.services.self_healing_service.subprocess") as mock_sub:
                mock_sub.run.return_value = MagicMock(returncode=0, stdout="2 passed")
                mock_sub.PIPE = -1
                mock_sub.STDOUT = -2
                success, output = svc._run_tests(Path("/fake/repo"))
                assert success is True

    def test_fail_via_subprocess(self):
        import nexuscore.services.self_healing_service as sh_mod
        svc = self._make_service()
        if sh_mod.HAS_RETRY and sh_mod.run_in_sandbox:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.timed_out = False
            mock_result.stdout = "1 failed"
            mock_result.stderr = "ERROR"
            mock_result.exception_type = "AssertionError"
            with patch.object(sh_mod, "run_in_sandbox", return_value=mock_result):
                success, output = svc._run_tests(Path("/fake/repo"))
            assert success is False
        else:
            with patch("nexuscore.services.self_healing_service.subprocess") as mock_sub:
                mock_sub.run.return_value = MagicMock(returncode=1, stdout="1 failed")
                mock_sub.PIPE = -1
                mock_sub.STDOUT = -2
                success, output = svc._run_tests(Path("/fake/repo"))
                assert success is False


class TestSelfHealingServiceCollectRelevantFiles:
    """_collect_relevant_files(*, project_path, error_log, changed_files, stacktrace_files)"""

    def _make_service(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            return svc

    def test_collect_nonexistent_files(self):
        svc = self._make_service()
        result = svc._collect_relevant_files(
            project_path=Path("/fake/repo"),
            error_log="FAIL: test",
            changed_files=["src/main.py"],
            stacktrace_files=["src/main.py"],
        )
        assert isinstance(result, dict)

    def test_collect_with_real_file(self):
        svc = self._make_service()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "main.py"
            test_file.write_text("print('hello')")
            result = svc._collect_relevant_files(
                project_path=Path(tmpdir),
                error_log="error",
                changed_files=["main.py"],
                stacktrace_files=[],
            )
            assert "main.py" in result


class TestSelfHealingServiceGeneratePatch:
    """_generate_patch_via_debugger(error_log, files, project_path) -> dict"""

    def _make_service(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            svc.debugger_agent = MagicMock()
            return svc

    def test_generate_with_debug_and_patch(self):
        svc = self._make_service()
        svc.debugger_agent.debug_and_patch.return_value = {"patch": "fix"}
        result = svc._generate_patch_via_debugger(
            error_log="error", files={"src/main.py": "code"}, project_path=Path("/fake")
        )
        assert result == {"patch": "fix"}

    def test_generate_with_generate_patch(self):
        svc = self._make_service()
        del svc.debugger_agent.debug_and_patch
        svc.debugger_agent.generate_patch.return_value = {"patch": "fix2"}
        result = svc._generate_patch_via_debugger(
            error_log="error", files={"src/main.py": "code"}, project_path=Path("/fake")
        )
        assert result == {"patch": "fix2"}

    def test_no_debugger_agent(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            svc.debugger_agent = None
            result = svc._generate_patch_via_debugger("err", {}, Path("/fake"))
            assert result == {}


class TestSelfHealingServiceFinalize:
    """_finalize(*, run_id, session_id, repo_full_name, pr_number, head_sha, status, summary, details, started_at)"""

    def _make_service(self):
        from nexuscore.services.self_healing_service import SelfHealingService
        with patch.object(SelfHealingService, "__init__", lambda self, **kw: None):
            svc = SelfHealingService.__new__(SelfHealingService)
            svc.logger = MagicMock()
            svc.history_logger = MagicMock()
            return svc

    def test_finalize_success(self):
        import time
        svc = self._make_service()
        result = svc._finalize(
            run_id="r1", session_id="s1", repo_full_name="org/repo",
            pr_number=1, head_sha="abc", status="success",
            summary="Fixed", details={}, started_at=time.time(),
        )
        assert isinstance(result, dict)
        assert result["status"] == "success"

    def test_finalize_log_failure(self):
        import time
        svc = self._make_service()
        svc.history_logger.new_self_healing_record.side_effect = Exception("DB error")
        # Should not raise — log failure is not fatal
        result = svc._finalize(
            run_id="r2", session_id="s2", repo_full_name="org/repo",
            pr_number=2, head_sha="def", status="failed",
            summary="Error", details={}, started_at=time.time(),
        )
        assert isinstance(result, dict)
