# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/core/
# ファイル名: orchestrator.py
# バージョン: 4.1 (Governance/Budget Hooks integrated)
#
# 目的:
#  - 既存の v3 系オーケストレータの「観測可能性/堅牢性」を維持しつつ、
#    Step 2（予算フック）、Step 3（コミット抑止）、Step 4（L2ブランチ運用）を追加。
#  - Agent 側の on_budget_tick を一括注入し、constitution の automation_policy に準拠。
# ==============================================================================

from __future__ import annotations

import os
import re
import sys
import json
import time
import uuid
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# --- 依存エージェントとユーティリティ ---
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.patch_applier import PatchApplier
from nexuscore.agents.policy_agent import PolicyAgent

from nexuscore.utils import code_analyzer

# --- データベースモジュール ---
from nexuscore.database.state_manager import state_manager
from nexuscore.database.knowledge_base import knowledge_base


def clean_llm_output(text: str) -> str:
    """``` ～ ``` を剥がして中身だけにする簡易サニタイザ"""
    if not text:
        return ""
    m = re.search(r"```(?:python\n)?(.*)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


@dataclass
class Orchestrator:
    # --- 依存と設定 ---
    project_path: str
    constitution: Dict

    # 主要エージェント（DI可能）
    requirement_agent: RequirementAgent
    architect: ArchitectAgent
    planner: PlannerAgent
    coder: CoderAgent
    tester: TesterAgent
    debugger: DebuggerAgent
    guardian: GuardianAgent
    policy_agent: PolicyAgent
    postmortem_agent: PostmortemAgent
    knowledge_curator_agent: KnowledgeCuratorAgent

    # リトライ等
    max_retries: int = 5
    max_quality_retries: int = 3

    # ロガー
    logger: logging.Logger = field(init=False)
    log_dir: str = field(init=False)
    actor_id: str = "orchestrator-main"

    # 予算状態（タスク毎にリセット）
    _budget_calls: int = field(default=0, init=False)
    _budget_limit: int = field(default=0, init=False)
    _budget_hard_stop: bool = field(default=True, init=False)

    def __post_init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
        self.log_dir = os.path.join(self.project_path, ".nexus_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger.info(f"Production Orchestrator initialized for project: {self.project_path}")
        self.logger.info(f"Logging to: {self.log_dir}")

    # =========================================================
    #  観測可能性: イベント/ステート更新（共通ユーティリティ）
    # =========================================================
    def _emit_event(
        self,
        task_id: str,
        name: str,
        details: Union[str, Dict[str, Any], None] = None,
        *,
        phase: Optional[str] = None,
        attempt: Optional[int] = None,
    ) -> None:
        now = time.time()
        payload = details if isinstance(details, dict) else ({"message": details} if details is not None else {})
        try:
            state_manager.append_event(task_id, {
                "event": name,
                "timestamp": now,
                "phase": phase,
                "attempt": attempt,
                "actor": self.actor_id,
                "details": payload,
            })
        except Exception:
            # ログへのフォールバック
            self.logger.debug(f"[event:{name}] {payload}")

    def _update_task_state(self, task_id: str, phase: str, progress: int,
                           details: Union[str, Dict[str, Any]], attempt: int = 0):
        now = time.time()
        progress = max(0, min(100, int(progress)))  # サニタイズ
        state = {
            "phase": phase,
            "progress": progress,
            "details": details,
            "attempt": attempt,
            "actor": self.actor_id,
            "updated_at": now
        }
        try:
            state_manager.set_task_state(task_id, state)
            self._emit_event(task_id, "state_updated", {"phase": phase, "progress": progress}, phase=phase, attempt=attempt)
        except Exception:
            self.logger.debug(f"[state:{phase}] {details}")

    # =========================================================
    #  予算フック（Step 2）
    # =========================================================
    def _reset_budget(self):
        ap = (self.constitution or {}).get("automation_policy", {})
        budget = ap.get("budget", {})
        self._budget_calls = 0
        self._budget_limit = int(budget.get("max_llm_calls_per_task", 0) or 0)
        self._budget_hard_stop = bool(budget.get("hard_stop_on_exceed", True))

    def _tick_llm_budget(self, step: str, task_id: Optional[str] = None):
        """LLMコールの度に呼ばれる。上限超過で hard_stop なら例外"""
        self._budget_calls += 1
        info = {"step": step, "calls": self._budget_calls, "limit": self._budget_limit}
        if task_id:
            self._emit_event(task_id, "budget_tick", info, phase="BUDGET")
        if self._budget_limit and self._budget_calls > self._budget_limit:
            msg = f"LLM budget exceeded: {self._budget_calls}/{self._budget_limit} at step={step}"
            if self._budget_hard_stop:
                raise RuntimeError(msg)
            self.logger.warning(msg)

    def _bind_budget_hook(self, task_id: Optional[str]):
        """task_id を閉じ込めた on_budget_tick クロージャを返す"""
        return (lambda step: self._tick_llm_budget(step, task_id)) if task_id else (lambda step: self._tick_llm_budget(step))

    # =========================================================
    #  補助: テスト実行/自己修復/品質ゲート
    # =========================================================
    def run_tests(self, test_file_path: str) -> tuple[bool, str]:
        try:
            timeout_sec = int(os.getenv("TEST_TIMEOUT_SEC", "600"))
            result = subprocess.run(
                [sys.executable, "-m", "pytest", os.path.relpath(test_file_path, self.project_path)],
                cwd=self.project_path,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                check=False, timeout=timeout_sec
            )
            return result.returncode == 0, result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Error: TimeoutExpired after {int(os.getenv('TEST_TIMEOUT_SEC', '600'))} seconds."
        except Exception as e:
            return False, f"Error: {e}"

    def _run_and_handle_tests(self, test_file_path: str, task_id: str, attempt: int) -> tuple[bool, str]:
        tests_passed, test_output = self.run_tests(test_file_path)
        if tests_passed:
            self._emit_event(task_id, "tests_passed", {"path": test_file_path}, phase="SELF_HEALING", attempt=attempt + 1)
        else:
            last_line = test_output.strip().splitlines()[-1] if test_output else "unknown error"
            self._emit_event(task_id, "tests_failed", {"error_signature": last_line}, phase="SELF_HEALING", attempt=attempt + 1)
        return tests_passed, test_output

    def _attempt_to_debug(self, test_output: str, source_file_path: str,
                          test_file_path: str, task_id: str, attempt: int) -> bool:
        """DebuggerAgent でパッチ修復を試みる"""
        try:
            files_ctx = {"source_file": source_file_path, "test_file": test_file_path}
            debug_result = self.debugger.debug(test_output, files_ctx)
            if not debug_result or "patch" not in debug_result:
                return False
            patcher = PatchApplier()
            if patcher.apply(debug_result["patch"], self.project_path):
                self._emit_event(task_id, "patch_applied", {"attempt": attempt + 1}, phase="SELF_HEALING", attempt=attempt + 1)
                return True
        except Exception as e:
            self._emit_event(task_id, "patch_apply_failed", {"error": str(e)}, phase="SELF_HEALING", attempt=attempt + 1)
        return False

    def _learn_from_failure(self, test_output: str, source_file_path: str,
                            test_file_path: str, task_id: str, attempt: int) -> bool:
        """失敗知見を KB に残す（可能なら）"""
        try:
            suggestion = self.debugger.summarize_failure(test_output, {"source": source_file_path, "test": test_file_path})
            if not suggestion:
                return False
            ok = knowledge_base.add_entry({"type": "failure", "note": suggestion})
            if ok:
                self._emit_event(task_id, "knowledge_added", {"note": "failure summary"}, phase="LEARNING", attempt=attempt + 1)
                return True
            self._emit_event(task_id, "knowledge_rejected", {"note": "not stored"}, phase="LEARNING", attempt=attempt + 1)
        except Exception as e:
            self._emit_event(task_id, "knowledge_error", {"error": str(e)}, phase="LEARNING", attempt=attempt + 1)
        return False

    def self_healing_cycle(self, test_file_path: str, source_file_path: str, task_id: str) -> bool:
        """テスト→失敗→デバッグ→パッチ→学習を最大 self.max_retries 回"""
        for attempt in range(self.max_retries):
            self._update_task_state(task_id, "SELF_HEALING", 70 + (attempt * 2),
                                    {"event": "attempt", "n": attempt + 1}, attempt + 1)
            tests_passed, test_output = self._run_and_handle_tests(test_file_path, task_id, attempt)
            if tests_passed:
                return True
            if self._attempt_to_debug(test_output, source_file_path, test_file_path, task_id, attempt):
                continue
            if self._learn_from_failure(test_output, source_file_path, test_file_path, task_id, attempt):
                continue
        return False

    def _run_quality_gate(self, source_file_path: str) -> tuple[bool, str]:
        gate = (self.constitution or {}).get("quality_gate", {})
        min_cov = gate.get("MIN_COVERAGE", 90)
        min_pylint = gate.get("MIN_PYLINT_SCORE", 8.0)
        violations: List[str] = []

        cov = code_analyzer.run_pytest_cov(self.project_path)
        if cov < min_cov:
            violations.append(f"Test coverage is {cov}% (required >= {min_cov}%).")

        pylint_score = code_analyzer.run_pylint(source_file_path)
        if pylint_score < float(min_pylint):
            violations.append(f"Pylint score is {pylint_score}/10 (required >= {min_pylint}/10).")

        mypy_ok, mypy_errors = code_analyzer.run_mypy(source_file_path)
        if not mypy_ok:
            violations.append(f"MyPy found type errors:\n{mypy_errors}")

        if not violations:
            return True, "All quality checks passed."
        return False, "Quality gate failed. Please fix:\n- " + "\n- ".join(violations)

    # =========================================================
    #  プロジェクト作成（Architect）
    # =========================================================
    def _create_project_structure(self, files: list):
        root = Path(self.project_path)
        root.mkdir(parents=True, exist_ok=True)
        if not isinstance(files, list):
            self.logger.error(f"Invalid 'files' format: {type(files)}")
            return
        for item in files:
            name = (item or {}).get("name")
            typ = (item or {}).get("type")
            if not name or not typ:
                continue
            p = root / name.replace("\\", "/").lstrip("/")
            if typ == "folder":
                p.mkdir(parents=True, exist_ok=True)
            elif typ == "file":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(item.get("content", "") or "", encoding="utf-8")

    def design_phase(self, user_requirement: str, task_id: Optional[str] = None):
        self.logger.info("--- 🎨 Design Phase ---")
        try:
            design_json = self.architect.design_project_structure(user_requirement)
            design_data = json.loads(design_json) if isinstance(design_json, str) else design_json
            self._create_project_structure((design_data.get("project") or {}).get("files", []))
            if task_id:
                self._update_task_state(task_id, "DESIGN_DONE", 30, "Project structure created.")
        except Exception as e:
            self.logger.error(f"Design phase failed: {e}", exc_info=True)

    # =========================================================
    #  要件定義（Requirement）
    # =========================================================
    def requirement_phase(self, user_initial_request: str, language: str = "ja",
                          task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        self.logger.info("--- 🧾 Requirement Definition Phase ---")
        if task_id:
            self._update_task_state(task_id, "REQUIREMENT_DEFINITION", 5, "Launching requirement UI")
        # 予算リセット & フック作成
        self._reset_budget()
        hook = self._bind_budget_hook(task_id)
        try:
            req = RequirementAgent(language=language)
            # ★ 予算フック注入（Step 2）
            if hasattr(req, "on_budget_tick"):
                req.on_budget_tick = hook
            final_specs = req.launch_ui(user_initial_request, share=False)
            if isinstance(final_specs, dict) and "requirements_specification" in final_specs:
                if task_id:
                    self._update_task_state(task_id, "REQUIREMENT_DEFINITION_DONE", 15, "Specification confirmed.")
                return final_specs["requirements_specification"]
            if task_id:
                self._update_task_state(task_id, "REQUIREMENT_DEFINITION_FAILED", 15, "No specification generated.")
            return None
        except Exception as e:
            self.logger.error(f"Requirement phase error: {e}", exc_info=True)
            if task_id:
                self._update_task_state(task_id, "REQUIREMENT_DEFINITION_FAILED", 15, str(e))
            return None

    # =========================================================
    #  開発サイクル（Planner→Coder→Tester→Policy→Quality→Guardian）
    # =========================================================
    def _autonomy_level(self) -> int:
        return int(((self.constitution or {}).get("automation_policy") or {}).get("autonomy_level", 0))

    @staticmethod
    def _to_snake(s: str) -> str:
        s = re.sub(r"[^\w]+", "_", s).strip("_")
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        return s.lower()[:64] or "task"

    def development_cycle(self, requirements_spec: Dict[str, Any], task_id: Optional[str] = None):
        self.logger.info("--- 🔄 Development Cycle ---")
        if not isinstance(requirements_spec, dict):
            self.logger.error("Invalid requirements_spec")
            return

        # 予算リセット & 予算フック（Planner/Guardian 用）
        self._reset_budget()
        hook = self._bind_budget_hook(task_id)
        if hasattr(self.planner, "on_budget_tick"):
            self.planner.on_budget_tick = hook
        if hasattr(self.guardian, "on_budget_tick"):
            self.guardian.on_budget_tick = hook

        # --- Planner ---
        if task_id:
            self._update_task_state(task_id, "PLANNING", 35, "Planner creating tasks")
        try:
            plan_json = self.planner.create_plan(json.dumps(requirements_spec, ensure_ascii=False))
            plan = json.loads(plan_json) if isinstance(plan_json, str) else plan_json
            tasks = plan.get("functions_to_implement", [])
        except Exception as e:
            self.logger.error(f"Planning failed: {e}", exc_info=True)
            return
        self.logger.info(f"Plan created with {len(tasks)} task(s).")

        # --- タスク実行ループ ---
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            task_name = task.get("name", f"task_{i+1}")
            if task_id:
                prog = 40 + int((i / max(1, len(tasks))) * 55)  # 40%→95%
                self._update_task_state(task_id, "DEVELOPMENT", prog, f"Executing {task_name}")

            try:
                # 1) Coder: 実装
                module_name = task.get("module") or self._to_snake(task_name)
                source_rel = f"app/{module_name}.py"
                test_rel = f"tests/test_{module_name}.py"
                source_abs = os.path.join(self.project_path, source_rel)
                test_abs = os.path.join(self.project_path, test_rel)

                existing = Path(source_abs).read_text(encoding="utf-8") if Path(source_abs).exists() else ""
                code_raw = self.coder.implement_code(json.dumps(task, ensure_ascii=False), existing)
                code_text = clean_llm_output(code_raw)
                Path(source_abs).parent.mkdir(parents=True, exist_ok=True)
                Path(source_abs).write_text(code_text, encoding="utf-8")

                # 2) Tester: テスト生成
                module_path = source_rel.replace(os.path.sep, ".").removesuffix(".py")
                test_raw = self.tester.generate_tests_from_plan(task, module_path)
                test_data = json.loads(test_raw) if isinstance(test_raw, str) else (test_raw or {})
                test_code = clean_llm_output(test_data.get("test_code", ""))
                testimony = test_data.get("testimony", "No testimony provided.")
                Path(test_abs).parent.mkdir(parents=True, exist_ok=True)
                Path(test_abs).write_text(test_code, encoding="utf-8")

                # 3) 自己修復付きの実行
                if not self.self_healing_cycle(test_abs, source_abs, task_id or "default-task"):
                    self.logger.error("Functional tests failed and could not be self-healed. Aborting this task.")
                    continue

                # 4) Policy 実行
                files_for_audit = [{"path": source_rel, "content": Path(source_abs).read_text(encoding="utf-8")}]
                policy_result = self.policy_agent.audit(files_for_audit)
                if (policy_result or {}).get("result") == "REJECTED":
                    fb = self._create_feedback_for_coder(policy_result.get("violations", []))
                    self.logger.warning("Policy check rejected. Coder will receive concrete feedback on next loop.")
                    # 次ループで反映できるよう、task の説明に feedback を追記（簡易）
                    task["description"] = (task.get("description") or "") + f"\n\n[Orchestratorからの具体的指示]:\n{fb}"
                    continue  # 改善ループ

                # 5) Quality Gate
                ok, fb = self._run_quality_gate(source_abs)
                if not ok:
                    self.logger.warning("Quality gate failed. Coder will receive concrete feedback on next loop.")
                    task["description"] = (task.get("description") or "") + f"\n\n[Orchestratorからの具体的指示]:\n{fb}"
                    continue  # 改善ループ

                # 6) Guardian: レビュー＆（必要なら）コミット
                autonomy = self._autonomy_level()
                allow_commit = autonomy >= 2  # L0/L1 は commit 抑止、L2 以上で許可
                branch_name: Optional[str] = None
                if autonomy == 2:
                    short = (task_id or uuid.uuid4().hex)[:8]
                    branch_name = f"feature/nx-{short}-{self._to_snake(task_name)}"

                constitution_text = (self.constitution or {}).get("description", "")
                review_result = self.guardian.review_and_commit(
                    code_draft=Path(source_abs).read_text(encoding="utf-8"),
                    test_code=Path(test_abs).read_text(encoding="utf-8"),
                    test_result=self.run_tests(test_abs)[1],
                    testimony=testimony,
                    constitution=constitution_text,
                    task_description=json.dumps(task, ensure_ascii=False),
                    changed_files=[source_abs, test_abs],
                    debug_info={},
                    allow_commit=allow_commit,
                    branch_name=branch_name
                )
                if (review_result or {}).get("decision") == "APPROVE":
                    self.logger.info(f"✅ Task '{task_name}' APPROVED ({'commit' if allow_commit else 'review-only'}).")
                else:
                    self.logger.warning(f"❌ Task '{task_name}' REJECTED by GuardianAgent.")
            except Exception as e:
                self.logger.error(f"Error in task loop for '{task_name}': {e}", exc_info=True)

        if task_id:
            self._update_task_state(task_id, "DEVELOPMENT_DONE", 100, "All tasks processed.")

    # =========================================================
    #  ランナー
    # =========================================================
    def run_full_project(self, user_requirement: str, language: str = "ja"):
        """ワンショットで Requirement→Design→Development を実行（例示）"""
        task_id = uuid.uuid4().hex
        self._update_task_state(task_id, "INIT", 0, "Project started")
        specs = self.requirement_phase(user_requirement, language, task_id)
        if not specs:
            self._update_task_state(task_id, "FAILED", 100, "No requirements")
            return
        self.design_phase(json.dumps(specs, ensure_ascii=False), task_id)
        self.development_cycle(specs, task_id)

    # =========================================================
    #  補助: Coder へのフィードバック整形
    # =========================================================
    def _create_feedback_for_coder(self, violations: list) -> str:
        lines: List[str] = []
        for v in violations or []:
            path = v.get("file_path") or v.get("file") or "unknown"
            rule = v.get("policy_id") or v.get("rule") or "policy"
            desc = v.get("description") or "violation"
            sugg = v.get("suggestion") or "fix the issue"
            lines.append(f"- {path}: {desc} (rule={rule}). Suggestion: {sugg}")
        return "\n".join(lines) if lines else "Fix policy violations."
