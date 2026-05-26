from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any


class OrchestratorPhase(IntEnum):
    """Orchestrator execution phases in order."""
    REQUIREMENTS = 1
    PLAN = 2
    ARCHITECTURE = 3
    IMPLEMENTATION = 4
    TESTING = 5
    REVIEW = 6

# ------------------------------------------------------------------------------
# パス設定 (自己完結性を高めるため: src/ を sys.path に追加)
# ------------------------------------------------------------------------------
try:
    current_dir = Path(__file__).resolve().parent  # .../src/nexuscore/core
    src_dir = current_dir.parents[2]  # .../src
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
except Exception:  # noqa: BLE001 — パス操作のフォールバック
    logging.getLogger(__name__).warning("Could not determine src directory.")

# ------------------------------------------------------------------------------
# 依存モジュール (Agents / NPE / Router / Utils)
# ------------------------------------------------------------------------------

from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
from nexuscore.services.patch_applier import PatchApplier
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.tester_agent import TesterAgent

from nexuscore.core.session_control import SessionController
from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin
from nexuscore.core.agent_factory import assemble_agent_team  # noqa: F401 backward-compat
from nexuscore.llm.llm_router import LLMRouter


# ==============================================================================
# Orchestrator 本体
# ==============================================================================


@dataclass
class Orchestrator(PhaseRunnerMixin):
    """NexusCore Orchestrator – coordinates the 6-phase development pipeline.

    Phase execution methods are inherited from PhaseRunnerMixin.
    """

    project_path: str
    constitution: dict[str, Any]

    # --- agents ---
    requirement_agent: RequirementAgent
    architect_agent: ArchitectAgent
    planner_agent: PlannerAgent
    coder_agent: CoderAgent
    tester_agent: TesterAgent
    debugger_agent: DebuggerAgent
    guardian_agent: GuardianAgent
    policy_agent: PolicyAgent
    postmortem_agent: PostmortemAgent
    knowledge_curator_agent: KnowledgeCuratorAgent
    patch_applier_agent: PatchApplier

    # --- LLM Router / config ---
    llm_router: LLMRouter
    max_retries: int = 5

    # --- optional agents (not required for pipeline) ---
    constitutional_council_agent: ConstitutionalCouncilAgent | None = None

    session_controller: SessionController | None = None

    logger: logging.Logger = field(init=False)

    def __post_init__(self) -> None:
        self._setup_logger()
        self.logger.info("Orchestrator v8.2 initialized.")
        self.logger.info(f"Project path: {self.project_path}")
        self.logger.info("NPE (function-based guarded_llm_call) is ready.")
        self.logger.info("LLMRouter is attached to Orchestrator.")

    def _setup_logger(self) -> None:
        log_dir = os.path.join(self.project_path, "logs", "orchestrator")
        os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            log_path = os.path.join(log_dir, f"orchestrator_{int(time.time())}.log")
            fh = logging.FileHandler(log_path, encoding="utf-8")
            ch = logging.StreamHandler(sys.stdout)

            fmt = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fh.setFormatter(fmt)
            ch.setFormatter(fmt)

            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def run_full_project(
        self,
        user_requirement: str,
        language: str = "ja",
        fast_lane: bool = False,
        run_db_id: int | None = None,
    ) -> None:
        """
        高レベルな「フルプロジェクト」実行フロー。

        フェーズ分割後の簡素化版: 各フェーズメソッドを順番に呼び出すだけの構造。

        Args:
            user_requirement: ユーザー要件
            language: 言語（デフォルト: "ja"）
            fast_lane: 高速レーン実行フラグ
            run_db_id: Run.id（Webapp側でRunレコードを作成したときのID、CLI実行時はNone）
        """
        self.logger.info(f"=== Full Project Run Start === requirement='{user_requirement}'")
        task_id = uuid.uuid4().hex

        # Orchestrator ログフック（開始時）
        try:
            from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

            log_orchestrator_event(
                run_db_id=run_db_id,
                phase="startup",
                status="STARTED",
                message="Orchestrator run started",
                extra={
                    "task_id": task_id,
                    "requirement": user_requirement[:200],
                    "autonomy_level": self.constitution.get("automation_policy", {}).get(
                        "autonomy_level"
                    ),
                },
            )
        except Exception:  # noqa: BLE001 — ログ失敗は既存の処理を止めない
            pass

        # 初期コンテキストの作成
        context = OrchestratorContext(
            task_id=task_id,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
        )

        try:
            # Phase 0: 開始直後のチェックポイント
            self._maybe_stop("start", {"task_id": task_id, "requirement": user_requirement})

            # Phase 0: Context Analysis (pre-pipeline)
            context = self.run_context_phase(context)

            # フェーズを順番に実行
            context = self.run_requirements_phase(context)
            context = self.run_planning_phase(context)
            context = self.run_architecture_phase(context)
            context = self.run_implementation_phase(context)
            context = self.run_testing_phase(context)
            context = self.run_review_phase(context)

            # FastLane の場合の後処理（ログ出力）
            if fast_lane:
                code_result = context.implementation.get("code", "")
                test_result = context.testing.get("tests", "")
                plan_text = json.dumps(context.plan, ensure_ascii=False, indent=2)
                self.logger.info(
                    "[FastLane] coder output length=%s, tester output length=%s",
                    len(code_result) if code_result else 0,
                    len(test_result) if test_result else 0,
                )
                if not hasattr(self, "last_fastlane_outputs"):
                    self.last_fastlane_outputs = {}
                self.last_fastlane_outputs = {
                    "code": code_result,
                    "tests": test_result,
                    "plan": plan_text,
                }

            # Phase 3 以降の開発サイクル（将来拡張用）
            tasks = (
                context.plan.get("functions_to_implement", [])
                if isinstance(context.plan, dict)
                else []
            )
            self.logger.info(f"[{task_id}] Phase 3: Development Cycle (tasks={len(tasks)})")

            self.logger.info(f"=== Full Project Run Finished === requirement='{user_requirement}'")

            # Orchestrator ログフック（完了）
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=run_db_id,
                    phase="shutdown",
                    status="FINISHED",
                    message="Orchestrator run finished",
                )
            except Exception:  # noqa: BLE001 — DBフック失敗は処理を止めない
                pass

        except RuntimeError as e:
            if str(e) == "SessionStopped":
                self.logger.info(
                    "Project run stopped by user request. "
                    "All generated files remain on disk for session resume."
                )
                # Orchestrator ログフック（中断）
                try:
                    from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                    log_orchestrator_event(
                        run_db_id=run_db_id,
                        phase="shutdown",
                        status="INTERRUPTED",
                        message="Orchestrator run stopped by user request",
                    )
                except Exception:  # noqa: BLE001 — DBフック失敗は処理を止めない
                    pass
                return
            # それ以外の RuntimeError は従来通り上位に投げる
            raise
        except Exception as e:
            self.logger.error(f"[{task_id}] Orchestrator run failed: {e}", exc_info=True)
            # Orchestrator ログフック（例外）
            try:
                from nexuscore.core.orchestrator_db_hook import log_orchestrator_event

                log_orchestrator_event(
                    run_db_id=run_db_id,
                    phase="orchestrator",
                    status="FAILED",
                    message=f"Orchestrator run failed: {str(e)[:200]}",
                )
            except Exception:  # noqa: BLE001 — DBフック失敗は処理を止めない
                pass
            raise



# CLI entry point: use main_cli.py
