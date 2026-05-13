from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.npe.engine import guarded_llm_call

if TYPE_CHECKING:
    import logging

    from nexuscore.agents.base_agent import BaseAgent
    from nexuscore.core.session_controller import SessionController
    from nexuscore.llm.router import LLMRouter


class PhaseRunnerMixin:
    """Mixin providing phase execution methods for Orchestrator.

    Expects the host class (Orchestrator) to provide:
    logger, session_controller, llm_router, requirement_agent,
    planner_agent, coder_agent, tester_agent, project_path.
    """

    if TYPE_CHECKING:
        logger: logging.Logger
        session_controller: SessionController | None
        llm_router: LLMRouter
        requirement_agent: BaseAgent
        planner_agent: BaseAgent
        coder_agent: BaseAgent
        tester_agent: BaseAgent
        project_path: str

    def _maybe_stop(self, phase: str, extra: dict[str, Any] | None = None) -> None:
        if not self.session_controller:
            return
        try:
            self.session_controller.checkpoint(phase, extra or {})
        except Exception:
            self.logger.exception(f"Failed to checkpoint session at phase '{phase}'")
        try:
            if self.session_controller.should_stop():
                self.logger.warning(
                    f"Session stop requested at phase '{phase}'. Aborting gracefully."
                )
                raise RuntimeError("SessionStopped")
        except RuntimeError:
            raise
        except Exception:
            self.logger.exception("Error while checking session stop request.")

    def _execute_task_via_npe(self, prompt: str, metadata: dict[str, Any]) -> str:
        task_type = metadata.get("task_type") or "generic"
        self.logger.info(f"[NPE] Delegating task '{task_type}' to guarded_llm_call().")

        task_model_map = getattr(self.llm_router, "task_model_map", {}) or {}
        default_model = getattr(self.llm_router, "default_model", None)
        model = task_model_map.get(task_type, default_model)

        system_prompt = (
            "You are the NexusCore Orchestration LLM. "
            "Follow metadata.task_type and return concise, machine-consumable output. "
            "If metadata.as_json is True, return strictly valid JSON."
        )

        result = guarded_llm_call(
            model=model,
            task=task_type,
            system_prompt=system_prompt,
            user_prompt=prompt,
            llm_complete_fn=self.llm_router.complete,
        )

        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = str(result)

        try:
            from nexuscore.utils.clean_output import clean_output

            return clean_output(content)
        except Exception:
            return content

    # ------------------------------------------------------------------
    # Phase 1: Requirements
    # ------------------------------------------------------------------
    def run_requirements_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 1: Requirement Definition")
        self._maybe_stop("before_requirement", {"task_id": context.task_id})
        context.phase_log.append("REQUIREMENTS")

        specs: dict[str, Any] = {}
        try:
            if hasattr(self.requirement_agent, "analyze_requirement"):
                specs = self.requirement_agent.analyze_requirement(context.user_requirement)
            else:
                specs = {"raw_requirement": context.user_requirement}
        except Exception as e:
            self.logger.error(f"[{context.task_id}] Requirement phase failed: {e}", exc_info=True)
            raise

        if not specs:
            self.logger.error(
                f"[{context.task_id}] Requirement definition returned empty specs. Aborting."
            )
            raise ValueError("Requirement definition returned empty specs")

        context.specs = specs
        self._maybe_stop("after_requirement", {"specs_summary": str(specs)[:500] if specs else ""})

        try:
            from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

            log_orchestrator_event(
                run_db_id=context.run_db_id,
                phase="requirement",
                status="SUCCESS",
                message="Requirement phase completed",
            )
        except Exception:
            pass

        return context

    # ------------------------------------------------------------------
    # Phase 2: Planning (with FastLane support)
    # ------------------------------------------------------------------
    def run_planning_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 2: Planning (fast_lane={context.fast_lane})")
        self._maybe_stop("before_planning", {})
        context.phase_log.append("PLAN")

        def _run_plan():
            if hasattr(self.planner_agent, "generate_plan"):
                req_json = json.dumps(context.specs, ensure_ascii=False, indent=2)
                return self.planner_agent.generate_plan(req_json)
            plan_prompt = (
                "以下の要件仕様に基づき、実装タスクの計画を立ててください。\n"
                "可能であれば JSON 形式で 'functions_to_implement' 配列を含めてください。\n\n"
                f"{json.dumps(context.specs, ensure_ascii=False, indent=2)}"
            )
            return self._execute_task_via_npe(
                prompt=plan_prompt,
                metadata={"task_type": "planning", "as_json": False},
            )

        def _run_code():
            if hasattr(self.coder_agent, "implement_code"):
                return self.coder_agent.implement_code(
                    task_description=context.user_requirement,
                    existing_code="",
                    code_language=os.getenv("NEXUS_CODE_LANG", "python"),
                )
            return ""

        def _run_test():
            if hasattr(self.tester_agent, "generate_tests"):
                return self.tester_agent.generate_tests(context.user_requirement)
            return ""

        try:
            if context.fast_lane:
                with ThreadPoolExecutor(max_workers=3) as ex:
                    future_plan = ex.submit(_run_plan)
                    future_code = ex.submit(_run_code)
                    future_test = ex.submit(_run_test)
                    plan_text = future_plan.result()
                    code_result = future_code.result()
                    test_result = future_test.result()

                test_result = self._ensure_fastlane_tests(
                    initial_result=test_result,
                    plan_text=plan_text,
                    code_result=code_result,
                    requirement=context.user_requirement,
                )

                context.implementation = {"code": code_result}
                context.testing = {"tests": test_result}
            else:
                plan_text = _run_plan()

            try:
                plan = json.loads(plan_text)
            except Exception:
                plan = {"raw_plan": plan_text}

            context.plan = plan
            self._maybe_stop(
                "after_planning", {"plan_preview": str(plan_text)[:500] if plan_text else ""}
            )

            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=context.run_db_id,
                    phase="planning",
                    status="SUCCESS",
                    message="Planning phase completed",
                    extra={"fast_lane": context.fast_lane},
                )
            except Exception:
                pass

        except Exception as e:
            self.logger.error(f"[{context.task_id}] Planning phase failed: {e}", exc_info=True)
            context.plan = {"error": str(e), "raw_specs": context.specs}
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=context.run_db_id,
                    phase="planning",
                    status="FAILED",
                    message=f"Planning phase failed: {str(e)[:200]}",
                )
            except Exception:
                pass
            raise

        return context

    # ------------------------------------------------------------------
    # Phase 3: Architecture (stub)
    # ------------------------------------------------------------------
    def run_architecture_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 3: Architecture")
        context.phase_log.append("ARCHITECTURE")
        context.architecture = {}
        return context

    # ------------------------------------------------------------------
    # Phase 4: Implementation
    # ------------------------------------------------------------------
    def run_implementation_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 4: Implementation")
        context.phase_log.append("IMPLEMENTATION")

        if context.fast_lane and context.implementation:
            return context

        def _run_code():
            if hasattr(self.coder_agent, "implement_code"):
                return self.coder_agent.implement_code(
                    task_description=context.user_requirement,
                    existing_code="",
                    code_language=os.getenv("NEXUS_CODE_LANG", "python"),
                )
            return ""

        code_result = _run_code()
        context.implementation = {"code": code_result}

        if code_result:
            try:
                hello_path = Path(self.project_path) / "hello.py"
                hello_path.parent.mkdir(parents=True, exist_ok=True)
                hello_path.write_text(code_result, encoding="utf-8")
                self.logger.info(f"Generated code saved to: {hello_path}")

                readme_path = Path(self.project_path) / "README.md"
                readme_content = f"""# {Path(self.project_path).name}

## 概要
{context.user_requirement}

## 実行方法

```bash
python hello.py
```

## 生成されたファイル

- `hello.py` - Hello World を表示する Python スクリプト

## 作成日時
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                readme_path.write_text(readme_content, encoding="utf-8")
                self.logger.info(f"README.md saved to: {readme_path}")
            except Exception as e:
                self.logger.warning(f"Failed to save files: {e}")

        return context

    # ------------------------------------------------------------------
    # Phase 5: Testing
    # ------------------------------------------------------------------
    def run_testing_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 5: Testing")
        context.phase_log.append("TESTING")

        if context.fast_lane and context.testing:
            return context

        def _run_test():
            if hasattr(self.tester_agent, "generate_tests"):
                return self.tester_agent.generate_tests(context.user_requirement)
            return ""

        test_result = _run_test()
        context.testing = {"tests": test_result}
        return context

    # ------------------------------------------------------------------
    # Phase 6: Review (stub)
    # ------------------------------------------------------------------
    def run_review_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 6: Review")
        context.phase_log.append("REVIEW")
        context.review = {}
        return context

    # ------------------------------------------------------------------
    # FastLane helper
    # ------------------------------------------------------------------
    def _ensure_fastlane_tests(
        self,
        initial_result: str,
        plan_text: str,
        code_result: str,
        requirement: str,
    ) -> str:
        result = initial_result or ""
        tester = getattr(self, "tester_agent", None)
        if not tester:
            return result

        def _call_with_logging(func_name: str, *args, **kwargs) -> str:
            func = getattr(tester, func_name, None)
            if not callable(func):
                return ""
            try:
                self.logger.info("[FastLane] tester fallback via %s", func_name)
                return func(*args, **kwargs) or ""
            except Exception as err:
                self.logger.warning(
                    "[FastLane] tester fallback %s failed: %s",
                    func_name,
                    err,
                    exc_info=True,
                )
                return ""

        if result:
            return result

        if plan_text:
            try:
                plan_json = json.loads(plan_text)
            except Exception:
                plan_json = None
            if plan_json:
                module_hint = os.getenv("FAST_LANE_TEST_MODULE", "fast_lane.regression_suite")
                result = _call_with_logging(
                    "generate_tests_from_plan",
                    plan_json,
                    module_hint,
                )
                if result:
                    return result

        if code_result:
            result = _call_with_logging(
                "generate_tests_and_testimony",
                code_result,
            )
            if result:
                return result

        if hasattr(tester, "generate_tests"):
            fallback = tester.generate_tests(requirement) or ""
            return fallback

        return result
