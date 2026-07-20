from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.npe.engine import guarded_llm_call
from nexuscore.core.retry_policy import _env_int

DEBUG_MAX_RETRIES: int = _env_int("NEXUS_DEBUG_MAX_RETRIES", 3)
"""デバッグループ（テスト失敗→debugger修正→再テスト）の最大リトライ回数（spec §4-5）"""

REVIEW_MAX_RETRIES: int = _env_int("NEXUS_REVIEW_MAX_RETRIES", 2)
"""レビューループ（guardian REJECT→再実装→再テスト→再レビュー）の最大リトライ回数（spec §4-5）"""

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
        except Exception:  # noqa: BLE001 — チェックポイント失敗は処理を止めない
            self.logger.exception(f"Failed to checkpoint session at phase '{phase}'")
        try:
            if self.session_controller.should_stop():
                self.logger.warning(
                    f"Session stop requested at phase '{phase}'. Aborting gracefully."
                )
                raise RuntimeError("SessionStopped")
        except RuntimeError:
            raise
        except Exception:  # noqa: BLE001 — セッションストップチェックのフォールバック
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
        except Exception:  # noqa: BLE001 — clean_output失敗時は生テキストを返す
            return content

    @staticmethod
    def _coerce_plan(plan_output: Any) -> dict[str, Any]:
        """planner 出力を dict に正規化する（dict / JSON文字列 / fence付き / 非JSON）。

        dict はそのまま返す。文字列は素の JSON・コードフェンス付き JSON
        （```json ... ``` / ``` ... ```）の順に解釈を試み、いずれも失敗する
        場合は {"raw_plan": <元テキスト>} にフォールバックする。
        """
        if isinstance(plan_output, dict):
            return plan_output

        text = str(plan_output or "")
        candidates = [text]

        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines:
                lines = lines[1:]  # 先頭フェンス行（``` / ```json 等）を除去
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]  # 末尾フェンス行を除去
            candidates.append("\n".join(lines))

        try:
            from nexuscore.utils.clean_output import clean_output

            candidates.append(clean_output(text))
        except Exception:  # noqa: BLE001 — clean_output失敗時は他候補で継続
            pass

        for candidate in candidates:
            try:
                parsed = json.loads(candidate.strip())
            except (json.JSONDecodeError, ValueError, AttributeError):
                continue
            if isinstance(parsed, dict):
                return parsed

        return {"raw_plan": text}

    # ------------------------------------------------------------------
    # Phase 0: Context Analysis
    # ------------------------------------------------------------------
    def run_context_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """Phase 0: Analyze project context and set error prevention rules."""
        self.logger.info(f"[{context.task_id}] Phase 0: Context Analysis")
        context_agent = getattr(self, "context_agent", None)
        if context_agent is None:
            self.logger.info(f"[{context.task_id}] ContextAgent not configured, skipping.")
            return context
        try:
            context.context_profile = context_agent.get_context()
            context.error_prevention_rules = context_agent.get_error_prevention_rules()
            self.logger.info(
                f"[{context.task_id}] Context analysis complete: "
                f"{len(context.context_profile)} profile keys, "
                f"{len(context.error_prevention_rules)} prevention rules"
            )
        except Exception as e:  # noqa: BLE001 — optional agent, graceful skip
            self.logger.warning(
                f"[{context.task_id}] ContextAgent failed (graceful skip): {e}"
            )
        return context

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
        except Exception as e:  # noqa: BLE001 — agent failure logging before re-raise
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
        except Exception:  # noqa: BLE001 — DBフック失敗は処理を止めない
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

            plan = self._coerce_plan(plan_text)

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
            except Exception:  # noqa: BLE001 — DBフック失敗は処理を止めない
                pass

        except Exception as e:  # noqa: BLE001 — agent failure logging before re-raise
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
            except Exception:  # noqa: BLE001 — DBフック失敗は処理を止めない
                pass
            raise

        return context

    # ------------------------------------------------------------------
    # Phase 3: Architecture
    # ------------------------------------------------------------------
    def run_architecture_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        """Phase 3: architect にコード設計方針(design_directive)を出させる（spec §4-1）。

        空出力は失敗として扱う（spec §6-1・_generate_one_file の既存パターンに倣う）。
        """
        self.logger.info(f"[{context.task_id}] Phase 3: Architecture")
        context.phase_log.append("ARCHITECTURE")

        if not hasattr(self.architect_agent, "design_architecture"):
            context.architecture = {"design_directive": ""}
            return context

        result = self.architect_agent.design_architecture(context.specs, context.plan)
        directive = (result or {}).get("design_directive", "")
        if not directive or not str(directive).strip():
            raise RuntimeError("ArchitectAgent returned empty design_directive")

        context.architecture = result
        return context

    # ------------------------------------------------------------------
    # Phase 4: Implementation
    # ------------------------------------------------------------------
    def run_implementation_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 4: Implementation")
        context.phase_log.append("IMPLEMENTATION")

        if context.fast_lane and context.implementation:
            return context

        from nexuscore.core.plan_contract import extract_target_files

        target_files, degraded = extract_target_files(context.plan)
        impl_targets = [e for e in target_files if e["role"] in ("implementation", "config")]

        # 生成順は plan の target_files 配列順（planner の列挙順＝依存順とみなす・spec §3-2）。
        # existing_code 連結はファイル数増でトークンが増えるが、Stage 1 の生成規模では許容
        # （選択的コンテキスト/RAG化はスコープ外・必要になったら起票）。
        generated: dict[str, str] = {}
        for entry in impl_targets:
            code = self._generate_one_file(context, entry, generated)
            out_path = Path(self.project_path) / entry["path"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(code, encoding="utf-8")
            generated[entry["path"]] = code
            self.logger.info(f"Generated code saved to: {out_path}")

        context.implementation = {"files": generated, "degraded": degraded}
        self._write_generated_readme(context, generated)
        return context

    def _generate_one_file(
        self,
        context: OrchestratorContext,
        entry: dict[str, str],
        generated: dict[str, str],
    ) -> str:
        """target_files の1エントリ分のコードを coder に生成させる。

        生成済みファイルを existing_code として渡し、ファイル間整合を担保する（spec §3-2）。
        空出力は失敗として扱う（spec §6-1）。
        """
        if not hasattr(self.coder_agent, "implement_code"):
            raise RuntimeError("CoderAgent does not support implement_code")

        design_directive = (context.architecture or {}).get("design_directive", "")
        task_description = (
            f"要件: {context.user_requirement}\n"
            f"生成対象ファイル: {entry['path']}（役割: {entry['role']}）\n"
            f"計画: {json.dumps(context.plan.get('functions_to_implement', []), ensure_ascii=False)}"
            + (f"\n設計方針: {design_directive}" if design_directive else "")
        )
        existing = "\n\n".join(
            f"# ==== {path} ====\n{code}" for path, code in generated.items()
        )
        code = self.coder_agent.implement_code(
            task_description=task_description,
            existing_code=existing,
            code_language=os.getenv("NEXUS_CODE_LANG", "python"),
        )
        if not code or not str(code).strip():
            raise RuntimeError(f"CoderAgent returned empty output for {entry['path']}")
        return str(code)

    def _write_generated_readme(
        self, context: OrchestratorContext, generated: dict[str, str]
    ) -> None:
        """実際の生成ファイル一覧から README を組み立てる（固定文言廃止・spec §3-2）。"""
        if not generated:
            return
        try:
            file_lines = "\n".join(f"- `{p}`" for p in generated)
            readme_content = (
                f"# {Path(self.project_path).name}\n\n"
                f"## 概要\n{context.user_requirement}\n\n"
                f"## 生成されたファイル\n\n{file_lines}\n\n"
                f"## 作成日時\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            readme_path = Path(self.project_path) / "README.md"
            readme_path.write_text(readme_content, encoding="utf-8")
            self.logger.info(f"README.md saved to: {readme_path}")
        except (OSError, UnicodeEncodeError) as e:
            self.logger.warning(f"Failed to save README: {e}")

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
    # Phase 6: Review
    # ------------------------------------------------------------------
    def run_review_phase(self, context: OrchestratorContext) -> OrchestratorContext:
        self.logger.info(f"[{context.task_id}] Phase 6: Review")
        context.phase_log.append("REVIEW")
        context.review = {}

        self._maybe_run_constitutional_review(context)
        return context

    def _maybe_run_constitutional_review(self, context: OrchestratorContext) -> None:
        """Trigger ConstitutionalCouncil when systemic issues are detected."""
        council = getattr(self, "constitutional_council_agent", None)
        if council is None:
            return

        postmortem_data = context.postmortem_report
        if not postmortem_data:
            return

        try:
            knowledge_brief = {
                "pattern": postmortem_data.get("error_signature", "unknown"),
                "suggestion": postmortem_data.get("solution_pattern", {}).get("instruction", ""),
            }
            council.review_and_amend(
                postmortem_report=postmortem_data,
                knowledge_brief=knowledge_brief,
            )
            self.logger.info(f"[{context.task_id}] Constitutional review completed.")
        except Exception as e:  # noqa: BLE001 — optional agent, graceful skip
            self.logger.warning(
                f"[{context.task_id}] ConstitutionalCouncil failed (graceful skip): {e}"
            )

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
            except Exception as err:  # noqa: BLE001 — fallback tester, graceful skip
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
            except (json.JSONDecodeError, ValueError):
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
