"""CR-NEXUS-054 Phase B: 外部計測を伴う成功条件。

カバレッジ%・lint警告数など実測ベースの SuccessCriterion を提供する。
計測は高コスト（pytest/ruff実行）のため、phase_log が進んだ時だけ
再計測するキャッシュ（PhaseCachedCheck）でラップする。
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from nexuscore.core.goal_spec import SuccessCriterion
from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.quality_regen_loop import QualityRegenLoop

_logger = logging.getLogger(__name__)


class PhaseCachedCheck:
    """高コスト計測のキャッシュ。phase_log の長さが変わった時だけ再計測する。

    SuccessCriterion.check として渡せる callable。同一フェーズ状態での
    再評価（DynamicRunLoop は毎ステップ評価する）で pytest 等を
    何度も走らせないための仕組み。
    """

    def __init__(self, measure: Callable[[], bool]) -> None:
        self._measure = measure
        self._cached_at: int | None = None
        self._cached_result = False

    def __call__(self, context: OrchestratorContext) -> bool:
        key = len(context.phase_log)
        if key != self._cached_at:
            try:
                self._cached_result = bool(self._measure())
            except Exception as e:  # noqa: BLE001 — 計測失敗は未達扱い
                _logger.warning("Measured criterion failed: %s", e)
                self._cached_result = False
            self._cached_at = key
        return self._cached_result

    def invalidate(self) -> None:
        """強制的に次回再計測させる。"""
        self._cached_at = None


def coverage_criterion(
    project_path: str,
    threshold: float = 80.0,
    quality_loop: QualityRegenLoop | None = None,
    test_path: str = "tests/",
) -> SuccessCriterion:
    """テストカバレッジが threshold% 以上であることを要求する条件。"""
    loop = quality_loop or QualityRegenLoop(project_path, coverage_threshold=threshold)

    def measure() -> bool:
        coverage = loop.measure_coverage(test_path=test_path)
        _logger.info("coverage_criterion: measured %.1f%% (threshold %.1f%%)", coverage, threshold)
        return coverage >= threshold

    return SuccessCriterion(
        name=f"coverage_ge_{int(threshold)}",
        check=PhaseCachedCheck(measure),
        description=f"テストカバレッジが {threshold}% 以上",
    )


def lint_clean_criterion(
    project_path: str,
    quality_loop: QualityRegenLoop | None = None,
    source_path: str = "src/",
) -> SuccessCriterion:
    """Critical lint警告（E/F系）がゼロであることを要求する条件。"""
    loop = quality_loop or QualityRegenLoop(project_path)

    def measure() -> bool:
        warnings = loop.count_critical_warnings(source_path=source_path)
        _logger.info("lint_clean_criterion: %d critical warnings", warnings)
        return warnings == 0

    return SuccessCriterion(
        name="lint_clean",
        check=PhaseCachedCheck(measure),
        description="Critical lint警告（E/F系）がゼロ",
    )
