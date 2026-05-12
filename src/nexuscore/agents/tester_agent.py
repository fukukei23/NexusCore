# -----------------------------------------------------------------------------
# FILE:         src/nexuscore/agents/tester_agent.py
# DATE:         2025-11-02 20:30 (JST)
# REGISTRY:     nexuscore.agents.TesterAgent
# -----------------------------------------------------------------------------

import logging
import os
from pathlib import Path

from .base_agent import BaseAgent
from .tester._generation import (
    build_tests_and_testimony_prompt,
    build_tests_from_plan_prompt,
    build_tests_from_requirement_prompt,
    extract_test_code_from_response,
)
from .tester._coverage import (
    count_test_functions,
    get_coverage_for_module,
    run_tests_and_get_coverage,
)
from .tester._file_ops import (
    infer_module_name_from_path,
    resolve_test_file_path,
    write_test_file,
)

try:
    from nexuscore.utils.test_generator_prompt import build_test_generation_prompt
    from nexuscore.utils.test_strategy import TestStrategyManager
    from nexuscore.core.test_metrics import TestMetricsCollector
except ImportError:
    TestStrategyManager = None
    build_test_generation_prompt = None
    TestMetricsCollector = None

logger = logging.getLogger(__name__)


class TesterAgent(BaseAgent):
    """
    品質保証（QA）エンジニアとして機能するエージェント。
    コードや実装計画に基づき、pytest形式のテストコードと設計証言を生成します。
    """

    SYSTEM_PROMPT = """
あなたは、細部まで見逃さない、経験豊富な品質保証（QA）エンジニアです。
専門はpytestを用いた自動テストの作成です。
あなたの仕事は、与えられたPythonコードや実装計画に対して、その正しさを証明するための
高品質なテストコードと、そのテスト設計に関する「証言」を生成することです。
"""

    def __init__(self, project_root: str | None = None) -> None:
        super().__init__()
        if project_root is None:
            project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())
        self.project_root = Path(project_root).resolve()

        if TestStrategyManager is not None:
            self.strategy_manager = TestStrategyManager()
        else:
            self.strategy_manager = None
            logger.warning("TestStrategyManager is not available. Test strategy features will be disabled.")

        if TestMetricsCollector is not None:
            self.test_metrics = TestMetricsCollector(project_root=str(self.project_root))
        else:
            self.test_metrics = None
            logger.warning("TestMetricsCollector is not available. Test metrics will not be recorded.")

    # -----------------------------------------------------------------
    # Public API — simple generation via LLM
    # -----------------------------------------------------------------

    def generate_tests_and_testimony(self, code_to_test: str) -> str:
        prompt = build_tests_and_testimony_prompt(code_to_test)
        return self.execute_llm_task(prompt, as_json=True)

    def generate_tests_from_plan(self, plan: dict, module_to_import: str) -> str:
        prompt = build_tests_from_plan_prompt(plan, module_to_import)
        return self.execute_llm_task(prompt, as_json=True)

    def generate_tests(self, requirement_summary: str) -> str:
        prompt = build_tests_from_requirement_prompt(requirement_summary)
        return self.execute_llm_task(prompt, as_json=True)

    # -----------------------------------------------------------------
    # Public API — strategy-based test generation
    # -----------------------------------------------------------------

    def generate_tests_for_module(
        self,
        module_name: str,
        target_file_path: str,
        target_code: str,
        test_level: str | None = None,
        existing_tests: str | None = None,
    ) -> dict | None:
        if self.strategy_manager is None:
            logger.warning("TestStrategyManager is not available. Skipping test generation.")
            return None

        strategy = self.strategy_manager.get_strategy(module_name)
        if not strategy.allows_ai_first:
            logger.info(
                "Module '%s' uses strategy '%s'. Auto-generation is disabled. Skipping.",
                module_name, strategy.strategy,
            )
            return None

        effective_test_level = test_level or "unit"
        logger.info("Generating tests for module '%s' (risk=%s, level=%s)", module_name, strategy.risk, effective_test_level)

        if build_test_generation_prompt is None:
            logger.error("build_test_generation_prompt is not available.")
            return None

        prompt = build_test_generation_prompt(
            target_file_path=target_file_path,
            target_code=target_code,
            existing_tests=existing_tests,
            test_level=effective_test_level,
            risk_level=strategy.risk,
            strategy=strategy.strategy,
            min_coverage=strategy.min_coverage,
            module_name=module_name,
        )

        try:
            llm_response = self.execute_llm_task(prompt, as_json=True, task_type="test_generate")
            test_code = extract_test_code_from_response(llm_response)
        except Exception as e:
            logger.error("Failed to generate test code via LLM: %s", e, exc_info=True)
            return None

        if not test_code:
            logger.warning("LLM did not generate test code.")
            return None

        try:
            test_file_path, test_count, coverage_before, coverage_after = self._apply_generated_test_code(
                module_name=module_name,
                test_code=test_code,
                target_file_path=target_file_path,
            )
        except Exception as e:
            logger.error("Failed to apply generated test code: %s", e, exc_info=True)
            return None

        if self.test_metrics is not None:
            try:
                self.test_metrics.record_test_generation(
                    module_name=module_name,
                    risk_level=strategy.risk,
                    strategy=strategy.strategy,
                    test_file_path=str(test_file_path),
                    test_count=test_count,
                    generated_by="ai",
                    coverage_before=coverage_before,
                    coverage_after=coverage_after,
                )
            except Exception as e:
                logger.warning("Failed to record test generation metrics: %s", e, exc_info=True)

        return {
            "test_code": test_code,
            "test_file_path": str(test_file_path),
            "test_count": test_count,
            "coverage_before": coverage_before,
            "coverage_after": coverage_after,
        }

    def handle_changed_files(self, changed_files: list[str]) -> dict[str, dict | None]:
        results: dict[str, dict | None] = {}
        for file_path in changed_files:
            try:
                module_name = infer_module_name_from_path(file_path)
                full_path = self.project_root / file_path
                if not full_path.exists():
                    logger.warning("File not found: %s. Skipping.", full_path)
                    continue

                code = full_path.read_text(encoding="utf-8")
                existing_tests = None
                test_fp = resolve_test_file_path(self.project_root, file_path)
                if test_fp.exists():
                    existing_tests = test_fp.read_text(encoding="utf-8")

                result = self.generate_tests_for_module(
                    module_name=module_name,
                    target_file_path=file_path,
                    target_code=code,
                    existing_tests=existing_tests,
                )
                results[module_name] = result
            except Exception as e:
                logger.error("Failed to process file '%s': %s", file_path, e, exc_info=True)
                results[file_path] = None
        return results

    # -----------------------------------------------------------------
    # Internal helpers — delegated to submodules
    # -----------------------------------------------------------------

    # Legacy method aliases (backward compat)
    def _extract_test_code_from_response(self, llm_response: str) -> str:
        return extract_test_code_from_response(llm_response)

    def _resolve_test_file_path(self, target_file_path: str) -> Path:
        return resolve_test_file_path(self.project_root, target_file_path)

    def _infer_module_name_from_path(self, file_path: str) -> str:
        return infer_module_name_from_path(file_path)

    def _count_test_functions(self, test_code: str) -> int:
        return count_test_functions(test_code)

    def _write_or_merge_test_file(self, test_file_path: Path, test_code: str) -> None:
        write_test_file(test_file_path, test_code)

    def _get_coverage_for_module(self, module_name: str) -> float:
        return get_coverage_for_module(self.project_root, module_name)

    def _run_tests_and_get_coverage(self, module_name: str, test_file_path: Path) -> float:
        return run_tests_and_get_coverage(self.project_root, module_name, test_file_path)

    def _apply_generated_test_code(
        self,
        module_name: str,
        test_code: str,
        target_file_path: str,
    ) -> tuple[str, int, float, float]:
        test_file_path = resolve_test_file_path(self.project_root, target_file_path)
        write_test_file(test_file_path, test_code)
        test_count = count_test_functions(test_code)
        coverage_before = get_coverage_for_module(self.project_root, module_name)
        coverage_after = run_tests_and_get_coverage(self.project_root, module_name, test_file_path)
        return str(test_file_path), test_count, coverage_before, coverage_after
