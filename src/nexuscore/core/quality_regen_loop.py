from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from nexuscore.logging_standard import get_logger

logger = get_logger(__name__)


@dataclass
class QualityRegenResult:
    """Result of the quality regeneration loop."""

    iterations: int
    final_coverage: float
    final_warnings: int
    success: bool
    message: str


class QualityRegenLoop:
    """Triggers test regeneration when coverage < threshold or critical warnings > 0."""

    def __init__(
        self,
        project_path: str,
        coverage_threshold: float = 85.0,
        max_iterations: int = 3,
        orchestrator: Any | None = None,
    ) -> None:
        self.project_path = project_path
        self.coverage_threshold = coverage_threshold
        self.max_iterations = max_iterations
        self.orchestrator = orchestrator

    def measure_coverage(self, test_path: str = "tests/") -> float:
        """Run pytest with coverage and return total coverage percentage (0.0 on failure)."""
        cmd = [
            "python", "-m", "pytest",
            "--cov=src", "--cov-report=term-missing", "-q",
            test_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + result.stderr
            match = re.search(r"TOTAL\s+\S+\s+\S+\s+(\d+)%", output)
            if match:
                return float(match.group(1))
            logger.warning("Could not parse coverage from pytest output")
            return 0.0
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
            logger.error("Coverage measurement failed: %s", exc)
            return 0.0

    def count_critical_warnings(self, source_path: str = "src/") -> int:
        """Count critical lint errors (E/F) using ruff or flake8 (0 on failure)."""
        linter = self._resolve_linter()
        if linter is None:
            logger.warning("No linter (ruff/flake8) found; treating warnings as 0")
            return 0

        cmd = self._build_lint_command(linter, source_path)
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return self._count_errors_from_output(result.stdout + result.stderr, linter)
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
            logger.error("Lint check failed: %s", exc)
            return 0

    def should_trigger(self, coverage: float, warning_count: int) -> bool:
        """Return True if regeneration should be triggered."""
        return coverage < self.coverage_threshold or warning_count > 0

    def request_regeneration(self, iteration: int) -> bool:
        """Request test/code regeneration via Orchestrator. Returns True on success."""
        logger.info("Requesting regeneration (iteration %d/%d)", iteration, self.max_iterations)
        if self.orchestrator is None:
            return True
        try:
            from nexuscore.core.orchestrator_models import OrchestratorContext
            ctx = OrchestratorContext(
                task_id=f"quality_regen_iter_{iteration}",
                user_requirement="auto-regeneration: improve coverage and fix lint warnings",
            )
            ctx = self.orchestrator.run_testing_phase(ctx)
            self.orchestrator.run_implementation_phase(ctx)
            return True
        except Exception as exc:  # noqa: BLE001 — orchestrator phase failure, returns False
            logger.error("Regeneration request failed at iteration %d: %s", iteration, exc)
            return False

    def run(self, test_path: str = "tests/", source_path: str = "src/") -> QualityRegenResult:
        """Execute the quality-regeneration loop."""
        coverage = self.measure_coverage(test_path)
        warnings = self.count_critical_warnings(source_path)

        logger.info(
            "Initial state: coverage=%.1f%% (threshold=%.1f%%), warnings=%d",
            coverage, self.coverage_threshold, warnings,
        )

        if not self.should_trigger(coverage, warnings):
            return QualityRegenResult(
                iterations=0,
                final_coverage=coverage,
                final_warnings=warnings,
                success=True,
                message="Quality thresholds already met — no regeneration needed",
            )

        for i in range(1, self.max_iterations + 1):
            if not self.request_regeneration(i):
                return QualityRegenResult(
                    iterations=i,
                    final_coverage=coverage,
                    final_warnings=warnings,
                    success=False,
                    message=f"Regeneration request failed at iteration {i}",
                )

            coverage = self.measure_coverage(test_path)
            warnings = self.count_critical_warnings(source_path)
            logger.info(
                "After iteration %d: coverage=%.1f%%, warnings=%d", i, coverage, warnings
            )

            if not self.should_trigger(coverage, warnings):
                return QualityRegenResult(
                    iterations=i,
                    final_coverage=coverage,
                    final_warnings=warnings,
                    success=True,
                    message=f"Quality thresholds met after {i} iteration(s)",
                )

        return QualityRegenResult(
            iterations=self.max_iterations,
            final_coverage=coverage,
            final_warnings=warnings,
            success=False,
            message=(
                f"Max iterations ({self.max_iterations}) reached "
                f"without meeting thresholds — coverage={coverage:.1f}%, warnings={warnings}"
            ),
        )

    @staticmethod
    def _resolve_linter() -> str | None:
        if shutil.which("ruff"):
            return "ruff"
        if shutil.which("flake8"):
            return "flake8"
        return None

    @staticmethod
    def _build_lint_command(linter: str, source_path: str) -> list[str]:
        if linter == "ruff":
            return ["ruff", "check", "--select", "E,F", source_path]
        return ["flake8", "--select=E,F", source_path]

    @staticmethod
    def _count_errors_from_output(output: str, linter: str) -> int:
        if linter == "ruff":
            lines = [
                ln for ln in output.strip().splitlines()
                if ln.strip() and not ln.startswith("Found ") and not ln.startswith("All checks")
            ]
            return len(lines)
        pattern = re.compile(r":\d+:\d+: [EF]\d+ ")
        return sum(1 for ln in output.splitlines() if pattern.search(ln))
