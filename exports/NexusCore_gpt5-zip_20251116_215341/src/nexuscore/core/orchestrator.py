# ==============================================================================
# 操作するソフト : VSCode（推奨）
# フォルダ       : src/nexuscore/core/
# ファイル名     : orchestrator.py
#
# 日付 (JST)     : 2025-11-14
# バージョン     : 8.2.0J (NPE Function-Based Integration + WSL Safe)
#
# 要旨:
#   - 旧設計の NexusProtocolEngine クラス依存を完全に排除。
#   - NPE は engine.guardedd_llm_call() を中核とする「関数ベース・プロトコル」として統合。
#   - Orchestrator に LLMRouter を正式に注入し、NPE → Router → Provider の経路を確立。
#   - WSL/Windows の差異に依存しないよう、ファイルパス/ログ周りをシンプル化。
#   - main_cli.py からの import 時に ImportError が出ないことを最優先設計。
# ==============================================================================

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

# ------------------------------------------------------------------------------
# パス設定 (自己完結性を高めるため: src/ を sys.path に追加)
# ------------------------------------------------------------------------------
try:
    current_dir = Path(__file__).resolve().parent          # .../src/nexuscore/core
    src_dir = current_dir.parents[2]                       # .../src
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
except Exception:
    print("[orchestrator] Warning: could not determine src directory.", file=sys.stderr)

# ------------------------------------------------------------------------------
# 依存モジュール (Agents / NPE / Router / Utils)
# ------------------------------------------------------------------------------

# エージェント群
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.patch_applier import PatchApplier

# NPE: クラスではなく「関数ベース・プロトコル」として利用
from nexuscore.npe.engine import guarded_llm_call

# LLM ルーター
from nexuscore.llm.llm_router import LLMRouter

# ユーティリティ (必要に応じて使用)
try:
    from nexuscore.utils.clean_output import clean_output
except Exception:
    # クリーンアップ関数が存在しない場合でも Orchestrator 自体は動作させる
    def clean_output(x: str) -> str:
        return x


# ==============================================================================
# Orchestrator 本体
# ==============================================================================

@dataclass
class Orchestrator:
    """
    NexusCore の中核となるオーケストレータ。
    - Requirement → Planning → Architecture → Coding → Testing → Review → Postmortem
    の大まかな流れを制御する。
    - 実際の LLM 呼び出しは「NPE (guarded_llm_call) → LLMRouter.complete」に委譲する。
    """

    project_path: str
    constitution: Dict[str, Any]

    # --- エージェント群 ---
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

    # --- LLM Router / 設定 ---
    llm_router: LLMRouter
    max_retries: int = 5

    # --- 内部状態 ---
    logger: logging.Logger = field(init=False)

    # ------------------------------------------------------------------
    # 初期化
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        # ロガーの準備
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

        # 重複ハンドラ防止
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

    # ------------------------------------------------------------------
    # NPE 経由で LLM を叩くヘルパー
    # ------------------------------------------------------------------
    def _execute_task_via_npe(self, prompt: str, metadata: Dict[str, Any]) -> str:
        """
        最新 NPE 仕様に基づき、guarded_llm_call() 経由で LLMRouter を呼び出す。
        - 予算ガード / ログ / ポリシーは NPE 側の engine/budget/logger/policies に委譲。
        """
        task_type = metadata.get("task_type") or "generic"
        self.logger.info(f"[NPE] Delegating task '{task_type}' to guarded_llm_call().")

        # Router 側の task_model_map / default_model を尊重
        task_model_map = getattr(self.llm_router, "task_model_map", {}) or {}
        default_model = getattr(self.llm_router, "default_model", None)
        model = task_model_map.get(task_type, default_model)

        # system_prompt は軽量な規律程度に留める（必要なら今後強化）
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

        # NPE 戻り値の標準形: dict {"ok": bool, "reason": str, "content": str, "usage": {...}}
        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = str(result)

        return clean_output(content)

    # ------------------------------------------------------------------
    # メインフロー (必要に応じて段階的に強化していく)
    # ------------------------------------------------------------------
    def run_full_project(self, user_requirement: str, language: str = "ja") -> None:
        """
        高レベルな「フルプロジェクト」実行フロー。
        - 現時点では Requirement → Planning までを安全に通すことを優先。
        - 以降のフェーズ（Architecture / Coding / Testing ...）は今後拡張。
        """
        self.logger.info(f"=== Full Project Run Start === requirement='{user_requirement}'")
        task_id = uuid.uuid4().hex

        # --------------------------------------------------------------
        # Phase 1: Requirement Definition
        # --------------------------------------------------------------
        self.logger.info(f"[{task_id}] Phase 1: Requirement Definition")
        specs: Dict[str, Any] = {}

        try:
            use_ui = bool(getattr(self.requirement_agent, "use_ui", False))
            if use_ui and hasattr(self.requirement_agent, "launch_gradio_ui"):
                specs = self.requirement_agent.launch_gradio_ui(share=False)
            elif hasattr(self.requirement_agent, "analyze_requirement"):
                specs = self.requirement_agent.analyze_requirement(user_requirement)
            else:
                # 最低限、テキストとして持っておく
                specs = {"raw_requirement": user_requirement}
        except Exception as e:
            self.logger.error(f"[{task_id}] Requirement phase failed: {e}", exc_info=True)
            return

        if not specs:
            self.logger.error(f"[{task_id}] Requirement definition returned empty specs. Aborting.")
            return

        # --------------------------------------------------------------
        # Phase 2: Planning (NPE 経由)
        # --------------------------------------------------------------
        self.logger.info(f"[{task_id}] Phase 2: Planning via NPE")
        plan: Dict[str, Any] = {}

        try:
            if hasattr(self.planner_agent, "generate_plan"):
                # エージェント固有メソッドがある場合はそれを優先
                req_json = json.dumps(specs, ensure_ascii=False, indent=2)
                plan_text = self.planner_agent.generate_plan(req_json)
            else:
                # NPE を経由して LLM にプラン生成を委譲
                plan_prompt = (
                    "以下の要件仕様に基づき、実装タスクの計画を立ててください。\n"
                    "可能であれば JSON 形式で 'functions_to_implement' 配列を含めてください。\n\n"
                    f"{json.dumps(specs, ensure_ascii=False, indent=2)}"
                )
                plan_text = self._execute_task_via_npe(
                    prompt=plan_prompt,
                    metadata={"task_type": "planning", "as_json": False},
                )

            # JSON っぽければパースを試みるが、失敗しても致命傷にはしない
            try:
                plan = json.loads(plan_text)
            except Exception:
                plan = {"raw_plan": plan_text}
        except Exception as e:
            self.logger.error(f"[{task_id}] Planning phase failed: {e}", exc_info=True)
            plan = {"error": str(e), "raw_specs": specs}

        # --------------------------------------------------------------
        # Phase 3 以降は将来拡張用のフック
        # --------------------------------------------------------------
        tasks = plan.get("functions_to_implement", []) if isinstance(plan, dict) else []
        self.logger.info(f"[{task_id}] Phase 3: Development Cycle (tasks={len(tasks)})")

        # ここではまだ実際のコード生成・テストは行わず、拡張ポイントとして残しておく。
        # 既存の CoderAgent / TesterAgent / GuardianAgent 等は、今後ここに順次統合していく。
        # for task in tasks:
        #     ...
        #     code_result = self.coder_agent.generate_code(...)
        #     test_result = self.tester_agent.generate_and_run_tests(...)
        #     review_result = self.guardian_agent.review(...)
        #     ...

        self.logger.info(f"=== Full Project Run Finished === requirement='{user_requirement}'")


# ==============================================================================
# Agent チームの組成
# ==============================================================================

def assemble_agent_team(project_path: str) -> Dict[str, Any]:
    """
    ハイブリッド・アーキテクチャに基づき、Orchestrator に渡すエージェント群と LLMRouter を生成する。

    戻り値:
        {
            "requirement_agent": RequirementAgent(...),
            "architect_agent":   ArchitectAgent(...),
            ...
            "patch_applier_agent": PatchApplier(...),
            "llm_router":        LLMRouter(...),
        }
    """
    logger = logging.getLogger("AgentAssembler")
    logger.info("Assembling agent team for NexusCore Orchestrator v8.2...")

    # LLM Router を最初に作成しておく（必要ならエージェントに渡せるようにする）
    llm_router = LLMRouter()

    # ここでは、各 Agent がデフォルトコンストラクタで生成できる前提とし、
    # 追加の依存は将来的に渡せるよう拡張余地を残す。
    requirement_agent = RequirementAgent()
    architect_agent = ArchitectAgent()
    planner_agent = PlannerAgent()
    coder_agent = CoderAgent()
    tester_agent = TesterAgent()
    debugger_agent = DebuggerAgent()
    guardian_agent = GuardianAgent()
    policy_agent = PolicyAgent()
    postmortem_agent = PostmortemAgent()
    knowledge_curator_agent = KnowledgeCuratorAgent()
    patch_applier_agent = PatchApplier()

    agents: Dict[str, Any] = {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": planner_agent,
        "coder_agent": coder_agent,
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": guardian_agent,
        "policy_agent": policy_agent,
        "postmortem_agent": postmortem_agent,
        "knowledge_curator_agent": knowledge_curator_agent,
        "patch_applier_agent": patch_applier_agent,
        "llm_router": llm_router,
    }

    logger.info(f"Agent team assembled. total={len(agents)} (including llm_router).")
    return agents


# ==============================================================================
# CLI エントリポイント (main_cli.py からも直接 import されることを想定)
# ==============================================================================

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NexusCore Orchestrator v8.2 (NPE + Router Integrated)"
    )
    parser.add_argument(
        "--project",
        type=str,
        default=str(Path.cwd()),
        help="プロジェクトのルートパス（デフォルト: カレントディレクトリ）",
    )
    parser.add_argument(
        "--requirement",
        type=str,
        default="サンプルの要件です。",
        help="自然言語での要件（デモ・テスト用）",
    )
    parser.add_argument(
        "--autonomy-level",
        type=int,
        default=1,
        help="自動化レベル（0=対話中心, 1=半自動, 2=ほぼ全自動）",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = _build_arg_parser()
    args = parser.parse_args()

    logger = logging.getLogger("CLI_LAUNCHER")
    logger.info("Orchestrator launch sequence initiated (v8.2).")

    constitution = {
        "automation_policy": {
            "autonomy_level": args.autonomy_level,
        }
    }

    try:
        agent_team = assemble_agent_team(project_path=args.project)
        orch = Orchestrator(
            project_path=args.project,
            constitution=constitution,
            **agent_team,
        )
        logger.info("Orchestrator instance created. Starting full project run.")
        orch.run_full_project(args.requirement)
        logger.info("Orchestrator process finished successfully.")
    except Exception as e:
        logger.critical(f"A critical error occurred in Orchestrator: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
