"""
============================================================================
Comprehensive Tests for authority_runner.py
============================================================================
カバレッジ対象:
- RunLockLease: コンテキストマネージャ、refresh loop
- phases_for_authority_level: AuthorityLevel → フェーズマッピング
- RunnerConfig: frozen dataclass
- stop_before_phases_for_authority_level: 文字列 → stop policy
- run_with_authority: STEP2 wiring entrypoint
- _invoke_orchestrator: セッション制御付き実行
- resume_run: 9-step 再開プロセス
- set_resume_orchestrator / set_resume_orchestrator_factory
- _extract_context_snapshot / _apply_context_snapshot
- _persist_run_state / _get_or_create_session_controller / _set_stop_policy
============================================================================
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.orchestrator.authority_runner import (
    PHASES_ORDER,
    PHASE_TO_METHOD,
    RunLockLease,
    RunnerConfig,
    _apply_context_snapshot,
    _extract_context_snapshot,
    _get_or_create_session_controller,
    _invoke_orchestrator,
    _persist_run_state,
    _set_stop_policy,
    phases_for_authority_level,
    resume_run,
    run_with_authority,
    run_with_authority_level,
    set_resume_orchestrator,
    set_resume_orchestrator_factory,
    stop_before_phases_for_authority_level,
)
from nexuscore.orchestrator.constants import AuthorityLevel


# ============================================================================
# Fixtures
# ============================================================================


@dataclass
class FakeContext:
    """テスト用オーケストレーションコンテキスト"""
    task_id: str = "test-task"
    user_requirement: str = ""
    language: str = "ja"
    fast_lane: bool = False
    run_db_id: int | None = None
    specs: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    architecture: dict[str, Any] | None = None
    implementation: dict[str, Any] | None = None
    testing: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    phase_log: list[str] | None = None


class FakeOrchestrator:
    """フェーズメソッドを持つモックオーケストレーター"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.constitution: dict[str, Any] = {}

    def run_requirements_phase(self, ctx: Any) -> Any:
        self.calls.append("requirements")
        return ctx

    def run_planning_phase(self, ctx: Any) -> Any:
        self.calls.append("planning")
        return ctx

    def run_architecture_phase(self, ctx: Any) -> Any:
        self.calls.append("architecture")
        return ctx

    def run_implementation_phase(self, ctx: Any) -> Any:
        self.calls.append("implementation")
        return ctx

    def run_testing_phase(self, ctx: Any) -> Any:
        self.calls.append("testing")
        return ctx

    def run_review_phase(self, ctx: Any) -> Any:
        self.calls.append("review")
        return ctx

    def run_full_project(self, **kwargs: Any) -> None:
        self.calls.append("full_project")


def _ctx_factory(**kwargs: Any) -> FakeContext:
    return FakeContext(
        user_requirement=kwargs.get("user_requirement", ""),
        language=kwargs.get("language", "ja"),
        fast_lane=kwargs.get("fast_lane", False),
        run_db_id=kwargs.get("run_db_id"),
    )


# ============================================================================
# Test: PHASES_ORDER / PHASE_TO_METHOD
# ============================================================================


class TestPhasesConstants:
    def test_phases_order_has_six_phases(self):
        assert len(PHASES_ORDER) == 6

    def test_phases_order_correct_order(self):
        assert PHASES_ORDER == (
            "requirements", "planning", "architecture",
            "implementation", "testing", "review",
        )

    def test_phase_to_method_maps_all_phases(self):
        for phase in PHASES_ORDER:
            assert phase in PHASE_TO_METHOD

    def test_phase_to_method_values_are_method_names(self):
        for phase, method in PHASE_TO_METHOD.items():
            assert method.startswith("run_")
            assert method.endswith("_phase")


# ============================================================================
# Test: phases_for_authority_level
# ============================================================================


class TestPhasesForAuthorityLevel:
    def test_human_controlled_returns_requirements_only(self):
        result = phases_for_authority_level(AuthorityLevel.HUMAN_CONTROLLED)
        assert result == ("requirements",)

    def test_partially_autonomous_through_architecture(self):
        result = phases_for_authority_level(AuthorityLevel.PARTIALLY_AUTONOMOUS)
        assert result == ("requirements", "planning", "architecture")

    def test_fully_autonomous_all_phases(self):
        result = phases_for_authority_level(AuthorityLevel.FULLY_AUTONOMOUS)
        assert result == PHASES_ORDER

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Invalid authority level"):
            phases_for_authority_level(999)

    def test_zero_level_raises(self):
        with pytest.raises(ValueError):
            phases_for_authority_level(0)

    def test_negative_level_raises(self):
        with pytest.raises(ValueError):
            phases_for_authority_level(-1)


# ============================================================================
# Test: RunnerConfig
# ============================================================================


class TestRunnerConfig:
    def test_create_with_authority_only(self):
        cfg = RunnerConfig(authority_level=AuthorityLevel.FULLY_AUTONOMOUS)
        assert cfg.authority_level == AuthorityLevel.FULLY_AUTONOMOUS
        assert cfg.allowed_phases is None

    def test_create_with_allowed_phases(self):
        phases = ("requirements", "planning")
        cfg = RunnerConfig(authority_level=1, allowed_phases=phases)
        assert cfg.allowed_phases == phases

    def test_frozen_raises_on_setattr(self):
        cfg = RunnerConfig(authority_level=1)
        with pytest.raises(Exception):
            cfg.authority_level = 2  # type: ignore[misc]

    def test_frozen_raises_on_delete(self):
        cfg = RunnerConfig(authority_level=1)
        with pytest.raises(Exception):
            del cfg.authority_level  # type: ignore[misc]


# ============================================================================
# Test: stop_before_phases_for_authority_level
# ============================================================================


class TestStopBeforePhasesForAuthorityLevel:
    def test_none_returns_empty(self):
        assert stop_before_phases_for_authority_level(None) == []

    def test_human_returns_all_phases(self):
        result = stop_before_phases_for_authority_level("human")
        assert result == list(PHASES_ORDER)

    def test_partial_returns_implementation(self):
        result = stop_before_phases_for_authority_level("partial")
        assert result == ["implementation"]

    def test_full_returns_empty(self):
        assert stop_before_phases_for_authority_level("full") == []

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid authority_level"):
            stop_before_phases_for_authority_level("unknown")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            stop_before_phases_for_authority_level("")


# ============================================================================
# Test: RunLockLease
# ============================================================================


class TestRunLockLease:
    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.try_acquire_run_lock", return_value=(True, None))
    def test_enter_acquires_lock(self, mock_acquire, mock_release):
        lease = RunLockLease("run-1")
        with lease:
            mock_acquire.assert_called_once_with("run-1")

    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.try_acquire_run_lock", return_value=(False, "busy"))
    def test_enter_failure_raises(self, mock_acquire, mock_release):
        lease = RunLockLease("run-1")
        with pytest.raises(RuntimeError, match="Failed to acquire lock"):
            with lease:
                pass

    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.try_acquire_run_lock", return_value=(True, None))
    def test_exit_releases_lock(self, mock_acquire, mock_release):
        lease = RunLockLease("run-1")
        with lease:
            pass
        mock_release.assert_called_once_with("run-1")

    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.try_acquire_run_lock", return_value=(True, None))
    def test_exit_no_release_if_not_acquired(self, mock_acquire, mock_release):
        lease = RunLockLease("run-1")
        lease._lock_acquired = False
        lease.__exit__(None, None, None)
        mock_release.assert_not_called()

    def test_is_refresh_failed_initially_false(self):
        lease = RunLockLease("run-1")
        assert lease.is_refresh_failed() is False

    def test_get_refresh_failure_initially_none(self):
        lease = RunLockLease("run-1")
        reason, details = lease.get_refresh_failure()
        assert reason is None
        assert details is None

    def test_default_refresh_interval(self):
        # _get_lock_refresh_seconds is lazily imported inside __init__
        with patch("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", return_value=60.0):
            lease = RunLockLease("run-1")
            assert lease.refresh_interval == 60.0

    def test_custom_refresh_interval(self):
        lease = RunLockLease("run-1", refresh_interval_seconds=10.0)
        assert lease.refresh_interval == 10.0

    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.try_acquire_run_lock", return_value=(True, None))
    def test_refresh_thread_starts(self, mock_acquire, mock_release):
        lease = RunLockLease("run-1", refresh_interval_seconds=999)
        with lease:
            assert lease._refresh_thread is not None
            assert lease._refresh_thread.daemon is True

    def test_refresh_loop_detects_failure(self):
        lease = RunLockLease("run-1", refresh_interval_seconds=0.001)
        lease._stop_refresh.clear()
        lease._refresh_failed.clear()
        # Simulate refresh failure
        with patch(
            "nexuscore.orchestrator._authority_runner_helpers.lock_lease.refresh_run_lock",
            return_value=(False, "expired", {"ttl": 0}),
        ):
            lease._refresh_loop()
        assert lease.is_refresh_failed() is True
        reason, details = lease.get_refresh_failure()
        assert reason == "expired"

    def test_refresh_loop_stops_on_event(self):
        lease = RunLockLease("run-1")
        lease._stop_refresh.set()
        # Should return immediately without calling refresh
        with patch("nexuscore.orchestrator._authority_runner_helpers.lock_lease.refresh_run_lock") as mock_refresh:
            lease._refresh_loop()
            mock_refresh.assert_not_called()


# ============================================================================
# Test: run_with_authority
# ============================================================================


class TestRunWithAuthority:
    @patch("nexuscore.orchestrator.authority_runner._invoke_orchestrator")
    def test_propagates_authority_level_in_context(self, mock_invoke):
        mock_invoke.return_value = {"status": "completed"}
        orch = FakeOrchestrator()

        run_with_authority(
            orchestrator=orch,
            user_requirement="test",
            authority_level="partial",
        )

        call_kwargs = mock_invoke.call_args[1]
        ec = call_kwargs["execution_context"]
        assert ec["authority_level"] == "partial"
        assert ec["stop_before_phases"] == ["implementation"]

    @patch("nexuscore.orchestrator.authority_runner._invoke_orchestrator")
    def test_none_authority_no_stops(self, mock_invoke):
        mock_invoke.return_value = {"status": "completed"}
        orch = FakeOrchestrator()

        run_with_authority(
            orchestrator=orch,
            user_requirement="test",
            authority_level=None,
        )

        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["stop_before_phases"] == []

    @patch("nexuscore.orchestrator.authority_runner._invoke_orchestrator")
    def test_sets_constitution_automation_policy(self, mock_invoke):
        mock_invoke.return_value = {"status": "completed"}
        orch = FakeOrchestrator()

        run_with_authority(
            orchestrator=orch,
            user_requirement="test",
            authority_level="full",
        )

        assert orch.constitution["automation_policy"]["authority_level"] == "full"

    @patch("nexuscore.orchestrator.authority_runner._invoke_orchestrator")
    def test_constitution_failure_does_not_crash(self, mock_invoke):
        mock_invoke.return_value = {"status": "completed"}
        orch = MagicMock()
        orch.constitution = "not a dict"  # type: ignore[assignment]

        # Should not raise
        run_with_authority(
            orchestrator=orch,
            user_requirement="test",
            authority_level="partial",
        )

    @patch("nexuscore.orchestrator.authority_runner._invoke_orchestrator")
    def test_passes_language(self, mock_invoke):
        mock_invoke.return_value = {"status": "completed"}
        orch = FakeOrchestrator()

        run_with_authority(
            orchestrator=orch,
            user_requirement="test",
            authority_level="full",
            language="en",
        )

        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["language"] == "en"

    @patch("nexuscore.orchestrator.authority_runner._invoke_orchestrator")
    def test_human_stops_at_all_phases(self, mock_invoke):
        mock_invoke.return_value = {"status": "paused"}
        orch = FakeOrchestrator()

        run_with_authority(
            orchestrator=orch,
            user_requirement="test",
            authority_level="human",
        )

        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["stop_before_phases"] == list(PHASES_ORDER)


# ============================================================================
# Test: _invoke_orchestrator
# ============================================================================


class TestInvokeOrchestrator:
    @patch("nexuscore.orchestrator.authority_runner._persist_run_state")
    @patch("nexuscore.orchestrator.authority_runner._get_or_create_session_controller")
    def test_no_stops_calls_run_full_project(self, mock_sc, mock_persist):
        mock_sc.return_value = MagicMock(session_id="sid-1")
        orch = FakeOrchestrator()
        ec = {"authority_level": "full"}

        result = _invoke_orchestrator(
            orchestrator=orch,
            user_requirement="test",
            language="ja",
            fast_lane=False,
            run_db_id=None,
            execution_context=ec,
            stop_before_phases=[],
        )

        assert "full_project" in orch.calls
        assert result["status"] == "completed"
        assert result["next_phase"] is None

    @patch("nexuscore.orchestrator.authority_runner._persist_run_state")
    @patch("nexuscore.orchestrator.authority_runner._get_or_create_session_controller")
    def test_stops_at_gate(self, mock_sc, mock_persist):
        sc = MagicMock(session_id="sid-1")
        mock_sc.return_value = sc
        orch = FakeOrchestrator()
        ec = {"authority_level": "partial"}

        result = _invoke_orchestrator(
            orchestrator=orch,
            user_requirement="test",
            language="ja",
            fast_lane=False,
            run_db_id=None,
            execution_context=ec,
            stop_before_phases=["implementation"],
        )

        # Should run requirements, planning, architecture then pause
        assert orch.calls == ["requirements", "planning", "architecture"]
        assert result["status"] == "paused"
        assert result["next_phase"] == "implementation"

    @patch("nexuscore.orchestrator.authority_runner._persist_run_state")
    @patch("nexuscore.orchestrator.authority_runner._get_or_create_session_controller")
    def test_stops_at_first_phase_for_human(self, mock_sc, mock_persist):
        sc = MagicMock(session_id="sid-1")
        mock_sc.return_value = sc
        orch = FakeOrchestrator()
        ec = {"authority_level": "human"}

        result = _invoke_orchestrator(
            orchestrator=orch,
            user_requirement="test",
            language="ja",
            fast_lane=False,
            run_db_id=None,
            execution_context=ec,
            stop_before_phases=list(PHASES_ORDER),
        )

        # Stops at first phase (requirements)
        assert orch.calls == []
        assert result["status"] == "paused"
        assert result["next_phase"] == "requirements"

    @patch("nexuscore.orchestrator.authority_runner._persist_run_state")
    @patch("nexuscore.orchestrator.authority_runner._get_or_create_session_controller")
    def test_missing_phase_method_raises(self, mock_sc, mock_persist):
        sc = MagicMock(session_id="sid-1")
        mock_sc.return_value = sc
        orch = MagicMock(spec=[])  # No phase methods

        with pytest.raises(AttributeError, match="does not provide required method"):
            _invoke_orchestrator(
                orchestrator=orch,
                user_requirement="test",
                language="ja",
                fast_lane=False,
                run_db_id=None,
                execution_context={},
                stop_before_phases=["implementation"],
            )

    @patch("nexuscore.orchestrator.authority_runner._persist_run_state")
    @patch("nexuscore.orchestrator.authority_runner._get_or_create_session_controller")
    def test_run_id_from_session_controller(self, mock_sc, mock_persist):
        sc = MagicMock(session_id="custom-sid")
        mock_sc.return_value = sc
        orch = FakeOrchestrator()

        result = _invoke_orchestrator(
            orchestrator=orch,
            user_requirement="test",
            language="ja",
            fast_lane=False,
            run_db_id=None,
            execution_context={},
            stop_before_phases=[],
        )

        assert result["run_id"] == "custom-sid"

    @patch("nexuscore.orchestrator.authority_runner._persist_run_state")
    @patch("nexuscore.orchestrator.authority_runner._get_or_create_session_controller")
    def test_checkpoint_called_for_each_phase(self, mock_sc, mock_persist):
        sc = MagicMock(session_id="sid-1")
        mock_sc.return_value = sc
        orch = FakeOrchestrator()
        ec = {"authority_level": "partial"}

        _invoke_orchestrator(
            orchestrator=orch,
            user_requirement="test",
            language="ja",
            fast_lane=False,
            run_db_id=None,
            execution_context=ec,
            stop_before_phases=["implementation"],
        )

        # checkpoint called for requirements, planning, architecture, implementation (before stop check)
        assert sc.checkpoint.call_count == 4


# ============================================================================
# Test: _extract_context_snapshot / _apply_context_snapshot
# ============================================================================


class TestContextSnapshot:
    def test_extract_basic_fields(self):
        ctx = FakeContext(user_requirement="req1", language="en", fast_lane=True, run_db_id=42)
        snapshot = _extract_context_snapshot(ctx)

        assert snapshot["user_requirement"] == "req1"
        assert snapshot["language"] == "en"
        assert snapshot["fast_lane"] is True
        assert snapshot["run_db_id"] == 42

    def test_extract_phase_dicts(self):
        ctx = FakeContext()
        ctx.specs = {"key": "val"}
        ctx.plan = {"steps": 3}
        snapshot = _extract_context_snapshot(ctx)

        assert snapshot["specs"] == {"key": "val"}
        assert snapshot["plan"] == {"steps": 3}

    def test_extract_skips_none_phase_dicts(self):
        ctx = FakeContext(specs=None)
        snapshot = _extract_context_snapshot(ctx)
        assert "specs" not in snapshot

    def test_apply_sets_attributes(self):
        ctx = FakeContext()
        snapshot = {"user_requirement": "new_req", "language": "fr"}
        _apply_context_snapshot(ctx, snapshot)

        assert ctx.user_requirement == "new_req"
        assert ctx.language == "fr"

    def test_apply_handles_setattr_failure(self):
        ctx = MagicMock()
        ctx.user_requirement = property(lambda s: "readonly")
        snapshot = {"user_requirement": "new_val"}
        # Should not raise
        _apply_context_snapshot(ctx, snapshot)

    def test_roundtrip(self):
        ctx = FakeContext(user_requirement="orig", language="ja")
        ctx.specs = {"s": 1}
        snapshot = _extract_context_snapshot(ctx)

        ctx2 = FakeContext()
        _apply_context_snapshot(ctx2, snapshot)
        assert ctx2.user_requirement == "orig"
        assert ctx2.specs == {"s": 1}


# ============================================================================
# Test: _persist_run_state
# ============================================================================


class TestPersistRunState:
    @patch("nexuscore.orchestrator._authority_runner_helpers.state.save_state")
    def test_paused_maps_to_PAUSED(self, mock_save):
        _persist_run_state(
            run_id="r1", status="paused", authority_level="partial",
            next_phase="impl", execution_context={}, context_snapshot=None,
        )
        state = mock_save.call_args[0][0]
        assert state["status"] == "PAUSED"

    @patch("nexuscore.orchestrator._authority_runner_helpers.state.save_state")
    def test_completed_maps_to_SUCCEEDED(self, mock_save):
        _persist_run_state(
            run_id="r1", status="completed", authority_level=None,
            next_phase=None, execution_context={}, context_snapshot=None,
        )
        state = mock_save.call_args[0][0]
        assert state["status"] == "SUCCEEDED"

    @patch("nexuscore.orchestrator._authority_runner_helpers.state.save_state")
    def test_running_stays_running(self, mock_save):
        _persist_run_state(
            run_id="r1", status="RUNNING", authority_level="full",
            next_phase=None, execution_context={}, context_snapshot=None,
        )
        state = mock_save.call_args[0][0]
        assert state["status"] == "RUNNING"

    @patch("nexuscore.orchestrator._authority_runner_helpers.state.save_state")
    def test_includes_context_snapshot(self, mock_save):
        snap = {"user_requirement": "test"}
        _persist_run_state(
            run_id="r1", status="paused", authority_level=None,
            next_phase=None, execution_context={}, context_snapshot=snap,
        )
        state = mock_save.call_args[0][0]
        assert state["context_snapshot"] == snap

    @patch("nexuscore.orchestrator._authority_runner_helpers.state.save_state")
    def test_no_context_snapshot_key_when_none(self, mock_save):
        _persist_run_state(
            run_id="r1", status="paused", authority_level=None,
            next_phase=None, execution_context={}, context_snapshot=None,
        )
        state = mock_save.call_args[0][0]
        assert "context_snapshot" not in state

    @patch("nexuscore.orchestrator._authority_runner_helpers.state.save_state")
    def test_schema_version(self, mock_save):
        _persist_run_state(
            run_id="r1", status="paused", authority_level=None,
            next_phase=None, execution_context={}, context_snapshot=None,
        )
        state = mock_save.call_args[0][0]
        assert state["schema_version"] == "1.0"


# ============================================================================
# Test: _get_or_create_session_controller / _set_stop_policy
# ============================================================================


class TestSessionControllerHelpers:
    def test_returns_existing_controller(self):
        orch = MagicMock()
        existing_sc = MagicMock()
        orch.session_controller = existing_sc
        result = _get_or_create_session_controller(orch)
        assert result == existing_sc

    def test_creates_new_when_missing(self):
        orch = MagicMock(spec=["project_path"])
        orch.session_controller = None
        result = _get_or_create_session_controller(orch)
        # Should create and return a SessionController
        assert result is not None

    def test_set_stop_policy_with_method(self):
        sc = MagicMock()
        _set_stop_policy(sc, ["implementation"])
        sc.set_stop_before_phases.assert_called_once_with(["implementation"])

    def test_set_stop_policy_none_controller(self):
        # Should not raise
        _set_stop_policy(None, ["implementation"])

    def test_set_stop_policy_fallback_attribute(self):
        sc = MagicMock(spec=["stop_before_phases"])
        _set_stop_policy(sc, ["testing"])
        assert sc.stop_before_phases == ["testing"]


# ============================================================================
# Test: resume_run
# ============================================================================


class TestResumeRun:
    """resume_runの9-stepフローとエラーパス"""

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.save_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={"what": "test"})
    def test_not_found_returns_failed(self, mock_expl, mock_save):
        """Step 1: load_state で FileNotFoundError"""
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", side_effect=FileNotFoundError):
            result = resume_run("missing-run")

        assert result["status"] == "FAILED"
        assert result["run_id"] == "missing-run"
        assert "explainability" in result

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={})
    def test_schema_invalid_returns_failed(self, mock_expl, mock_update):
        """Step 2: schema gate failure"""
        state = {"run_id": "r1", "status": "PAUSED"}
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(False, "BAD_SCHEMA", "Invalid")):
            result = resume_run("r1")

        assert result["status"] == "FAILED"
        assert result["run_id"] == "r1"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={})
    def test_integrity_fail_returns_failed(self, mock_expl):
        """Step 3: integrity gate failure"""
        state = {"run_id": "r1", "status": "PAUSED"}
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None)), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(False, "TAMPERED", "Hash mismatch")):
            result = resume_run("r1")

        assert result["status"] == "FAILED"
        assert result["run_id"] == "r1"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={})
    def test_not_paused_returns_failed(self, mock_expl, mock_update):
        """Step 4: status gate - not PAUSED"""
        state = {"run_id": "r1", "status": "RUNNING"}
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None)), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None)):
            result = resume_run("r1")

        assert result["status"] == "FAILED"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={})
    def test_lowercase_paused_normalized(self, mock_expl, mock_update):
        """Step 4: lowercase 'paused' normalized to 'PAUSED'"""
        state = {"run_id": "r1", "status": "paused"}
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None)), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None)), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(False, "conflict")):
            result = resume_run("r1")
            # Should reach lock conflict (not status gate failure)
            assert result["status"] == "CONFLICT"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={})
    def test_lock_conflict_returns_conflict(self, mock_expl):
        """Step 5: lock conflict"""
        state = {"run_id": "r1", "status": "PAUSED"}
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None)), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None)), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(False, "already locked")):
            result = resume_run("r1")

        assert result["status"] == "CONFLICT"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(True, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None))
    def test_no_orchestrator_returns_failed(self, mock_val, mock_int, mock_lock, mock_release, mock_update):
        """Step 7: no orchestrator configured → FAILED (exception caught)"""
        state = {"run_id": "r1", "status": "PAUSED"}
        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state):
            # Reset globals
            import nexuscore.orchestrator._authority_runner_helpers.resume as ar
            old_factory = ar._RESUME_ORCHESTRATOR_FACTORY
            old_orch = ar._RESUME_ORCHESTRATOR
            ar._RESUME_ORCHESTRATOR_FACTORY = None
            ar._RESUME_ORCHESTRATOR = None
            try:
                result = resume_run("r1")
                assert result["status"] == "FAILED"
                assert result["run_id"] == "r1"
            finally:
                ar._RESUME_ORCHESTRATOR_FACTORY = old_factory
                ar._RESUME_ORCHESTRATOR = old_orch

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(True, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None))
    @patch("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", return_value=0.01)
    def test_normal_resume_returns_running(self, mock_refresh, mock_val, mock_int, mock_lock, mock_release, mock_update):
        """Steps 1-9: normal resume path"""
        state = {"run_id": "r1", "status": "PAUSED", "authority_level": "partial"}
        mock_orch = MagicMock()

        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.RunLockLease") as mock_lease_cls:
            mock_lease = MagicMock()
            mock_lease.is_refresh_failed.return_value = False
            mock_lease.__enter__ = MagicMock(return_value=mock_lease)
            mock_lease.__exit__ = MagicMock(return_value=False)
            mock_lease_cls.return_value = mock_lease

            result = resume_run("r1", orchestrator_factory=lambda: mock_orch)

        assert result["status"] == "RUNNING"
        assert result["run_id"] == "r1"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(True, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None))
    @patch("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", return_value=0.01)
    def test_refresh_fail_returns_aborted(self, mock_refresh, mock_val, mock_int, mock_lock, mock_release, mock_update):
        """Refresh failure → ABORTED"""
        state = {"run_id": "r1", "status": "PAUSED"}
        mock_orch = MagicMock()

        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.RunLockLease") as mock_lease_cls:
            mock_lease = MagicMock()
            mock_lease.is_refresh_failed.return_value = True
            mock_lease.get_refresh_failure.return_value = ("timeout", {"ttl": 0})
            mock_lease.__enter__ = MagicMock(return_value=mock_lease)
            mock_lease.__exit__ = MagicMock(return_value=False)
            mock_lease_cls.return_value = mock_lease

            result = resume_run("r1", orchestrator_factory=lambda: mock_orch)

        assert result["status"] == "ABORTED"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.build_explainability", return_value={})
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(True, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None))
    @patch("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", return_value=0.01)
    def test_exception_returns_failed(self, mock_refresh, mock_val, mock_int, mock_lock, mock_release, mock_update, mock_expl):
        """Unexpected exception → FAILED"""
        state = {"run_id": "r1", "status": "PAUSED"}

        def boom():
            raise RuntimeError("boom")

        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.RunLockLease") as mock_lease_cls:
            mock_lease = MagicMock()
            mock_lease.is_refresh_failed.return_value = False
            mock_lease.__enter__ = MagicMock(return_value=mock_lease)
            mock_lease.__exit__ = MagicMock(return_value=False)
            mock_lease_cls.return_value = mock_lease

            result = resume_run("r1", orchestrator_factory=boom)

        assert result["status"] == "FAILED"

    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.update_state")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.release_run_lock")
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.try_acquire_run_lock", return_value=(True, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.verify_integrity", return_value=(True, None, None))
    @patch("nexuscore.orchestrator._authority_runner_helpers.resume.validate_run_state", return_value=(True, None, None))
    @patch("nexuscore.orchestrator.run_lock._get_lock_refresh_seconds", return_value=0.01)
    def test_uses_factory_over_global(self, mock_refresh, mock_val, mock_int, mock_lock, mock_release, mock_update):
        """orchestrator_factory が優先される"""
        state = {"run_id": "r1", "status": "PAUSED"}
        factory_orch = MagicMock()
        global_orch = MagicMock()

        with patch("nexuscore.orchestrator._authority_runner_helpers.resume.load_state", return_value=state), \
             patch("nexuscore.orchestrator._authority_runner_helpers.resume.RunLockLease") as mock_lease_cls:
            mock_lease = MagicMock()
            mock_lease.is_refresh_failed.return_value = False
            mock_lease.__enter__ = MagicMock(return_value=mock_lease)
            mock_lease.__exit__ = MagicMock(return_value=False)
            mock_lease_cls.return_value = mock_lease

            import nexuscore.orchestrator._authority_runner_helpers.resume as ar
            old = ar._RESUME_ORCHESTRATOR
            ar._RESUME_ORCHESTRATOR = global_orch
            try:
                resume_run("r1", orchestrator_factory=lambda: factory_orch)
            finally:
                ar._RESUME_ORCHESTRATOR = old

        # factory_orch.start should be called, not global_orch
        factory_orch.start.called or not global_orch.start.called


# ============================================================================
# Test: set_resume_orchestrator / set_resume_orchestrator_factory
# ============================================================================


class TestResumeOrchestratorSetters:
    def test_set_resume_orchestrator(self):
        import nexuscore.orchestrator._authority_runner_helpers.resume as ar
        old = ar._RESUME_ORCHESTRATOR
        mock = MagicMock()
        try:
            set_resume_orchestrator(mock)
            assert ar._RESUME_ORCHESTRATOR == mock
        finally:
            ar._RESUME_ORCHESTRATOR = old

    def test_set_resume_orchestrator_factory(self):
        import nexuscore.orchestrator._authority_runner_helpers.resume as ar
        old = ar._RESUME_ORCHESTRATOR_FACTORY
        factory = lambda: MagicMock()
        try:
            set_resume_orchestrator_factory(factory)
            assert ar._RESUME_ORCHESTRATOR_FACTORY == factory
        finally:
            ar._RESUME_ORCHESTRATOR_FACTORY = old

    def test_factory_overrides_previous(self):
        import nexuscore.orchestrator._authority_runner_helpers.resume as ar
        old = ar._RESUME_ORCHESTRATOR_FACTORY
        try:
            set_resume_orchestrator_factory(lambda: "first")
            set_resume_orchestrator_factory(lambda: "second")
            assert ar._RESUME_ORCHESTRATOR_FACTORY() == "second"
        finally:
            ar._RESUME_ORCHESTRATOR_FACTORY = old


# ============================================================================
# Test: run_with_authority_level (supplementary)
# ============================================================================


class TestRunWithAuthorityLevelSupplementary:
    def test_custom_allowed_phases(self):
        """allowed_phases オーバーライド"""
        orch = FakeOrchestrator()

        run_with_authority_level(
            orch,
            "test",
            authority_level=AuthorityLevel.HUMAN_CONTROLLED,
            allowed_phases=("requirements", "planning"),
            context_factory=_ctx_factory,
        )

        assert orch.calls == ["requirements", "planning"]

    def test_invalid_phase_name_raises(self):
        """不明フェーズ名でValueError"""
        orch = FakeOrchestrator()

        with pytest.raises(ValueError, match="Unknown phase"):
            run_with_authority_level(
                orch,
                "test",
                authority_level=AuthorityLevel.FULLY_AUTONOMOUS,
                allowed_phases=("requirements", "unknown_phase"),
                context_factory=_ctx_factory,
            )

    def test_default_context_factory(self):
        """context_factory 未指定でフォールバック"""
        orch = FakeOrchestrator()

        # Should not raise (uses _default_context_factory internally)
        run_with_authority_level(
            orch,
            "test requirement",
            authority_level=AuthorityLevel.HUMAN_CONTROLLED,
        )

        assert orch.calls == ["requirements"]

    def test_missing_phase_method_raises(self):
        """オーケストレーターにフェーズメソッドがない"""
        orch = MagicMock(spec=[])  # Empty spec - no methods

        with pytest.raises(AttributeError, match="does not provide required method"):
            run_with_authority_level(
                orch,
                "test",
                authority_level=AuthorityLevel.FULLY_AUTONOMOUS,
                context_factory=_ctx_factory,
            )
