"""CR-NEXUS-054 Phase B: measured_criteria のユニットテスト（MiniMax生成・Fable検証済み）。"""

from unittest.mock import MagicMock

from nexuscore.core.measured_criteria import (
    PhaseCachedCheck,
    coverage_criterion,
    lint_clean_criterion,
)
from nexuscore.core.orchestrator_models import OrchestratorContext


def _build_context(phase_log=None):
    return OrchestratorContext(task_id="t", user_requirement="r", phase_log=phase_log or [])


class TestPhaseCachedCheck:
    """PhaseCachedCheckのキャッシュ挙動を検証する。"""

    def test_フェーズログが変わらなければ再計測されない(self):
        """同一の phase_log 状態では measure が1回しか呼ばれないことを検証する。"""
        counter = {"n": 0}

        def measure():
            counter["n"] += 1
            return True

        check = PhaseCachedCheck(measure)
        ctx = _build_context(phase_log=["a"])

        assert check(ctx) is True
        assert check(ctx) is True
        assert check(ctx) is True
        assert counter["n"] == 1

    def test_フェーズログが増えたら再計測される(self):
        """phase_log が進んだら measure が再実行されることを検証する。"""
        counter = {"n": 0}

        def measure():
            counter["n"] += 1
            return True

        check = PhaseCachedCheck(measure)
        ctx = _build_context(phase_log=["a"])

        assert check(ctx) is True
        ctx.phase_log.append("b")
        assert check(ctx) is True
        assert counter["n"] == 2

    def test_invalidateで次回呼び出し時に強制再計測される(self):
        """invalidate() 後の呼び出しでは phase_log が同じでも再計測されることを検証する。"""
        counter = {"n": 0}

        def measure():
            counter["n"] += 1
            return True

        check = PhaseCachedCheck(measure)
        ctx = _build_context(phase_log=["a"])

        assert check(ctx) is True
        assert check(ctx) is True
        check.invalidate()
        assert check(ctx) is True
        assert counter["n"] == 2

    def test_measureが例外を投げたらFalseを返す(self):
        """計測の失敗は例外ではなく未達（False）として扱われることを検証する。"""

        def measure():
            raise RuntimeError("計測失敗")

        check = PhaseCachedCheck(measure)
        ctx = _build_context(phase_log=["a"])

        assert check(ctx) is False


class TestCoverageCriterion:
    """coverage_criterionの挙動を検証する。"""

    def test_カバレッジが閾値以上ならTrue(self):
        """measure_coverage が閾値以上を返すと条件達成になることを検証する。"""
        quality_loop = MagicMock()
        quality_loop.measure_coverage.return_value = 85.0

        criterion = coverage_criterion("/tmp/proj", threshold=80.0, quality_loop=quality_loop)
        assert criterion.name == "coverage_ge_80"

        ctx = _build_context()
        assert criterion.check(ctx) is True

    def test_カバレッジが閾値未満ならFalse(self):
        """measure_coverage が閾値未満を返すと条件未達になることを検証する。"""
        quality_loop = MagicMock()
        quality_loop.measure_coverage.return_value = 70.0

        criterion = coverage_criterion("/tmp/proj", threshold=80.0, quality_loop=quality_loop)

        ctx = _build_context()
        assert criterion.check(ctx) is False


class TestLintCleanCriterion:
    """lint_clean_criterionの挙動を検証する。"""

    def test_重要な警告が0件ならTrue(self):
        """count_critical_warnings が 0 を返すと条件達成になることを検証する。"""
        quality_loop = MagicMock()
        quality_loop.count_critical_warnings.return_value = 0

        criterion = lint_clean_criterion("/tmp/proj", quality_loop=quality_loop)
        assert criterion.name == "lint_clean"

        ctx = _build_context()
        assert criterion.check(ctx) is True

    def test_重要な警告が3件ならFalse(self):
        """count_critical_warnings が正の数を返すと条件未達になることを検証する。"""
        quality_loop = MagicMock()
        quality_loop.count_critical_warnings.return_value = 3

        criterion = lint_clean_criterion("/tmp/proj", quality_loop=quality_loop)

        ctx = _build_context()
        assert criterion.check(ctx) is False
