"""Tests for QualityRegenLoop (Issue #51: MC1-3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nexuscore.core.quality_regen_loop import QualityRegenLoop, QualityRegenResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def loop():
    return QualityRegenLoop(project_path="/fake/project", max_iterations=3)


@pytest.fixture
def loop_low_threshold():
    return QualityRegenLoop(project_path="/fake/project", coverage_threshold=50.0, max_iterations=2)


# ---------------------------------------------------------------------------
# measure_coverage
# ---------------------------------------------------------------------------


class TestMeasureCoverage:
    def test_parses_total_coverage(self, loop):
        output = "TOTAL                   100     20     80%\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, stderr="")
            assert loop.measure_coverage() == 80.0

    def test_returns_zero_on_parse_failure(self, loop):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="no coverage here", stderr="")
            assert loop.measure_coverage() == 0.0

    def test_returns_zero_on_subprocess_error(self, loop):
        with patch("subprocess.run", side_effect=OSError("no python")):
            assert loop.measure_coverage() == 0.0

    def test_returns_zero_on_timeout(self, loop):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 300)):
            assert loop.measure_coverage() == 0.0

    def test_100_percent_coverage(self, loop):
        output = "TOTAL    500   0   100%\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, stderr="")
            assert loop.measure_coverage() == 100.0

    def test_uses_project_path_as_cwd(self, loop):
        output = "TOTAL   100  10   90%\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, stderr="")
            loop.measure_coverage("tests/")
            assert mock_run.call_args.kwargs["cwd"] == "/fake/project"

    def test_stderr_also_searched(self, loop):
        stderr = "TOTAL   200  30   85%\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr=stderr)
            assert loop.measure_coverage() == 85.0


# ---------------------------------------------------------------------------
# count_critical_warnings
# ---------------------------------------------------------------------------


class TestCountCriticalWarnings:
    def test_ruff_counts_error_lines(self, loop):
        ruff_output = (
            "src/foo.py:1:1: E501 line too long\n"
            "src/bar.py:5:3: F401 unused import\n"
            "Found 2 errors.\n"
        )
        with patch("shutil.which", return_value="/usr/bin/ruff"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=ruff_output, stderr="")
            assert loop.count_critical_warnings() == 2

    def test_flake8_fallback_when_no_ruff(self, loop):
        flake8_output = (
            "src/foo.py:1:1: E501 line too long\n"
            "src/bar.py:5:3: F401 unused import\n"
        )
        def which(cmd):
            return None if cmd == "ruff" else "/usr/bin/flake8"

        with patch("shutil.which", side_effect=which), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=flake8_output, stderr="")
            assert loop.count_critical_warnings() == 2

    def test_returns_zero_when_no_linter(self, loop):
        with patch("shutil.which", return_value=None):
            assert loop.count_critical_warnings() == 0

    def test_returns_zero_on_subprocess_error(self, loop):
        with patch("shutil.which", return_value="/usr/bin/ruff"), \
             patch("subprocess.run", side_effect=OSError("ruff not found")):
            assert loop.count_critical_warnings() == 0

    def test_clean_output_returns_zero(self, loop):
        with patch("shutil.which", return_value="/usr/bin/ruff"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="All checks passed.\n", stderr="")
            assert loop.count_critical_warnings() == 0


# ---------------------------------------------------------------------------
# should_trigger
# ---------------------------------------------------------------------------


class TestShouldTrigger:
    def test_triggers_when_coverage_below_threshold(self, loop):
        assert loop.should_trigger(80.0, 0) is True

    def test_triggers_when_warnings_present(self, loop):
        assert loop.should_trigger(90.0, 1) is True

    def test_triggers_on_both_conditions(self, loop):
        assert loop.should_trigger(70.0, 5) is True

    def test_no_trigger_when_thresholds_met(self, loop):
        assert loop.should_trigger(85.0, 0) is False

    def test_no_trigger_exactly_at_threshold(self, loop):
        assert loop.should_trigger(85.0, 0) is False

    def test_triggers_just_below_threshold(self, loop):
        assert loop.should_trigger(84.9, 0) is True

    def test_custom_threshold(self, loop_low_threshold):
        assert loop_low_threshold.should_trigger(60.0, 0) is False
        assert loop_low_threshold.should_trigger(49.9, 0) is True


# ---------------------------------------------------------------------------
# request_regeneration
# ---------------------------------------------------------------------------


class TestRequestRegeneration:
    def test_returns_true_when_orchestrator_is_none(self, loop):
        assert loop.request_regeneration(1) is True

    def test_calls_orchestrator_phases(self):
        mock_orch = MagicMock()
        mock_ctx = MagicMock()
        mock_orch.run_testing_phase.return_value = mock_ctx
        loop = QualityRegenLoop(project_path="/p", orchestrator=mock_orch)
        with patch("nexuscore.core.orchestrator.OrchestratorContext") as mock_octx_cls:
            mock_octx_cls.return_value = mock_ctx
            result = loop.request_regeneration(1)
        assert result is True
        mock_orch.run_testing_phase.assert_called_once_with(mock_ctx)
        mock_orch.run_implementation_phase.assert_called_once_with(mock_ctx)

    def test_returns_false_on_orchestrator_exception(self):
        mock_orch = MagicMock()
        mock_orch.run_testing_phase.side_effect = RuntimeError("orchestrator error")
        loop = QualityRegenLoop(project_path="/p", orchestrator=mock_orch)
        assert loop.request_regeneration(1) is False


# ---------------------------------------------------------------------------
# run (main loop)
# ---------------------------------------------------------------------------


class TestRun:
    def test_no_trigger_when_thresholds_already_met(self, loop):
        with patch.object(loop, "measure_coverage", return_value=90.0), \
             patch.object(loop, "count_critical_warnings", return_value=0):
            result = loop.run()
        assert result.success is True
        assert result.iterations == 0
        assert result.final_coverage == 90.0
        assert "already met" in result.message

    def test_success_after_one_iteration(self, loop):
        coverage_vals = iter([70.0, 90.0])
        warnings_vals = iter([0, 0])
        with patch.object(loop, "measure_coverage", side_effect=coverage_vals), \
             patch.object(loop, "count_critical_warnings", side_effect=warnings_vals), \
             patch.object(loop, "request_regeneration", return_value=True):
            result = loop.run()
        assert result.success is True
        assert result.iterations == 1
        assert result.final_coverage == 90.0

    def test_failure_when_max_iterations_reached(self, loop):
        with patch.object(loop, "measure_coverage", return_value=60.0), \
             patch.object(loop, "count_critical_warnings", return_value=3), \
             patch.object(loop, "request_regeneration", return_value=True):
            result = loop.run()
        assert result.success is False
        assert result.iterations == 3
        assert "Max iterations" in result.message

    def test_failure_when_regeneration_request_fails(self, loop):
        with patch.object(loop, "measure_coverage", return_value=60.0), \
             patch.object(loop, "count_critical_warnings", return_value=0), \
             patch.object(loop, "request_regeneration", return_value=False):
            result = loop.run()
        assert result.success is False
        assert "failed" in result.message

    def test_success_after_multiple_iterations(self):
        loop = QualityRegenLoop(project_path="/p", coverage_threshold=85.0, max_iterations=3)
        coverage_seq = iter([60.0, 70.0, 80.0, 90.0])
        warnings_seq = iter([2, 1, 0, 0])
        with patch.object(loop, "measure_coverage", side_effect=coverage_seq), \
             patch.object(loop, "count_critical_warnings", side_effect=warnings_seq), \
             patch.object(loop, "request_regeneration", return_value=True):
            result = loop.run()
        assert result.success is True
        assert result.iterations == 3

    def test_result_contains_final_state(self, loop):
        with patch.object(loop, "measure_coverage", return_value=88.0), \
             patch.object(loop, "count_critical_warnings", return_value=0):
            result = loop.run()
        assert result.final_coverage == 88.0
        assert result.final_warnings == 0


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------


class TestResolveLinter:
    def test_prefers_ruff(self):
        with patch("shutil.which", return_value="/usr/bin/ruff"):
            assert QualityRegenLoop._resolve_linter() == "ruff"

    def test_falls_back_to_flake8(self):
        def which(cmd):
            return None if cmd == "ruff" else "/usr/bin/flake8"
        with patch("shutil.which", side_effect=which):
            assert QualityRegenLoop._resolve_linter() == "flake8"

    def test_returns_none_when_neither_available(self):
        with patch("shutil.which", return_value=None):
            assert QualityRegenLoop._resolve_linter() is None


class TestBuildLintCommand:
    def test_ruff_command(self):
        cmd = QualityRegenLoop._build_lint_command("ruff", "src/")
        assert cmd == ["ruff", "check", "--select", "E,F", "src/"]

    def test_flake8_command(self):
        cmd = QualityRegenLoop._build_lint_command("flake8", "src/")
        assert cmd == ["flake8", "--select=E,F", "src/"]


class TestCountErrorsFromOutput:
    def test_ruff_error_counting(self):
        output = "src/a.py:1:1: E501 long\nsrc/b.py:2:2: F401 unused\nFound 2 errors.\n"
        assert QualityRegenLoop._count_errors_from_output(output, "ruff") == 2

    def test_ruff_clean_output(self):
        assert QualityRegenLoop._count_errors_from_output("All checks passed.\n", "ruff") == 0

    def test_flake8_error_counting(self):
        output = "src/a.py:1:1: E501 line too long\nsrc/b.py:3:5: F401 unused\n"
        assert QualityRegenLoop._count_errors_from_output(output, "flake8") == 2

    def test_flake8_empty_output(self):
        assert QualityRegenLoop._count_errors_from_output("", "flake8") == 0
