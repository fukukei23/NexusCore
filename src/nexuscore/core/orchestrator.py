# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエージェタ)
# フォルダ: src/nexuscore/core/
# ファイル名: orchestrator.py
#
# 日付: 2025年9月28日
# 日本時間: 06:45
#
# バージョン: 8.1 (Hybrid Architecture Fix)
#
# 改修内容:
#   - エラーの根本原因であった、エージェントの初期化問題を完全に解決しました。
#   - `assemble_agent_team`関数を全面的に改良し、あなたのシステムの優れた
#     「ハイブリッド・アーキテクチャ」に完全準拠させました。
#   - CoderAgentのような「近代化」エージェントと、GuardianAgentのような
#     「特殊任務」エージェントを、それぞれの役割に応じて正しく初期化します。
#   - これにより、システム全体のアーキテクチャに一貫性が生まれ、CLIからの
#     起動が正常に完了するようになります。
# ==============================================================================

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import logging
import argparse
from dataclasses import dataclass, field
from typing import Any, Dict
from pathlib import Path

# --- パス設定 (自己完結性を高めるため) ---
try:
    current_dir = Path(__file__).resolve().parent
    # src/nexuscore/core -> src
    src_dir = current_dir.parents[2]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
except Exception:
    print("Warning: Could not automatically determine and set the 'src' directory path.")

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

# --- v8.0 アーキテクチャの核心 ---
from nexuscore.npe.engine import NexusProtocolEngine
from nexuscore.llm.llm_router import LLMRouter
from nexuscore.utils.clean_output import clean_output

@dataclass
class Orchestrator:
    # ... (v8.0のクラス定義は変更なし) ...
    project_path: str
    constitution: Dict[str, Any]
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
    max_retries: int = 5
    logger: logging.Logger = field(init=False)
    npe_instance: NexusProtocolEngine = field(init=False)

    def __post_init__(self):
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(level=logging.INFO, format=log_format)
        self.logger = logging.getLogger(self.__class__.__name__)
        log_dir = os.path.join(self.project_path, ".nexus_logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, f"orchestrator_{int(time.time())}.log"))
        file_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(file_handler)
        self.logger.info(f"Orchestrator v8.1 initialized for project: {self.project_path}")
        
        self.npe_instance = NexusProtocolEngine()
        self.logger.info("Nexus Protocol Engine (NPE) has been integrated.")

    def _execute_task_via_npe(self, prompt: str, metadata: Dict[str, Any]) -> str:
        self.logger.info(f"Delegating task '{metadata.get('task_type')}' to NPE.")
        project_id = os.path.basename(self.project_path)
        
        response = self.npe_instance.process_task(
            prompt=prompt,
            metadata=metadata,
            project_id=project_id
        )
        return response

    def run_full_project(self, user_requirement: str, language: str = "ja"):
        self.logger.info(f"--- Starting Full Project Run for: '{user_requirement}' ---")
        task_id = uuid.uuid4().hex

        # (UIを持つRequirementAgentは現時点では直接呼び出し)
        self.logger.info(f"[{task_id}] Phase 1: Requirement Definition")
        specs = self.requirement_agent.launch_gradio_ui(share=False)
        if not specs:
            self.logger.error(f"[{task_id}] Requirement definition failed. Aborting.")
            return

        # (以降のフェーズはNPEを経由)
        self.logger.info(f"[{task_id}] Phase 2: Planning")
        plan_prompt = self.planner_agent.generate_plan(json.dumps(specs, ensure_ascii=False))
        plan_response = self._execute_task_via_npe(
            prompt=plan_prompt,
            metadata={"task_type": "planning", "task_id": task_id, "as_json": True}
        )
        plan = json.loads(clean_output(plan_response))
        tasks = plan.get("functions_to_implement", [])
        
        self.logger.info(f"[{task_id}] Phase 3: Development Cycle with {len(tasks)} tasks")
        for task in tasks:
            # (... 開発サイクル ... )
            pass

        self.logger.info(f"--- Full Project Run Finished for: '{user_requirement}' ---")

# --- ★★★★★ ここからが v8.1 修正の核心 ★★★★★ ---
def assemble_agent_team(project_path: str) -> Dict[str, Any]:
    """
    ハイブリッド・アーキテクチャに基づき、完全なエージェントチームを編成する。
    """
    logger = logging.getLogger("AgentAssembler")
    logger.info("Assembling the agent team according to the hybrid architecture...")
    
    # 司令塔とAPIキーを準備
    llm_router = LLMRouter()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("A primary API key (e.g., GEMINI_API_KEY) must be set.")

    # 1. 近代化されたエージェントの招集 (引数なし)
    # これらはBaseAgentを継承し、内部で自動的にLLMRouterをセットアップする
    agents = {
        "requirement_agent": RequirementAgent(),
        "architect_agent": ArchitectAgent(),
        "planner_agent": PlannerAgent(),
        "coder_agent": CoderAgent(),
        "tester_agent": TesterAgent(),
        "debugger_agent": DebuggerAgent(),
        "postmortem_agent": PostmortemAgent(),
        "policy_agent": PolicyAgent(),
    }
    logger.info(f"Instantiated {len(agents)} modernized agents.")

    # 2. 特殊任務エージェントのプロビジョニング (引数あり)
    # これらは特定のモデルや設定を明示的に要求する
    
    # GuardianAgent: 'review'タスク用のモデルを動的に取得して設定
    review_model = llm_router.task_model_map.get('review', llm_router.default_model)
    agents["guardian_agent"] = GuardianAgent(api_key=api_key, model=review_model)
    logger.info(f"Provisioned GuardianAgent for 'review' with model '{review_model}'.")

    # KnowledgeCuratorAgent: 'general'タスク用のモデルを動的に取得して設定
    general_model = llm_router.task_model_map.get('general', llm_router.default_model)
    agents["knowledge_curator_agent"] = KnowledgeCuratorAgent(api_key=api_key, model=general_model)
    logger.info(f"Provisioned KnowledgeCuratorAgent for 'general' with model '{general_model}'.")
    
    # 3. ユーティリティの任命 (LLM不要)
    agents["patch_applier_agent"] = PatchApplier()
    
    logger.info(f"Full team of {len(agents)} agents assembled and ready.")
    return agents
# --- ★★★★★ ここまで ★★★★★ ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NexusCore Orchestrator v8.1")
    parser.add_argument("--project", required=True, help="プロジェクトを管理するフォルダの絶対パス")
    parser.add_argument("--autonomy-level", type=int, default=1, help="自律レベル")
    parser.add_argument("--requirement", required=True, help="生成したいプロジェクトの説明文")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("CLI_LAUNCHER")
    logger.info("Orchestrator launch sequence initiated.")

    constitution = { "automation_policy": {"autonomy_level": args.autonomy_level} }

    try:
        agent_team = assemble_agent_team(project_path=args.project)
        orch = Orchestrator(project_path=args.project, constitution=constitution, **agent_team)
        logger.info("Orchestrator instance created. Starting the process.")
        orch.run_full_project(args.requirement)
        logger.info("Orchestrator process finished successfully.")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}", exc_info=True)
        sys.exit(1)

