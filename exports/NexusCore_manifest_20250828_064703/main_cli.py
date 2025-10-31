# ==============================================================================
# ファイル: main_cli.py
# メモ: 【統合・最終版】
#      - RequirementAgentを統合し、全自動開発フローの起点とする。
#      - ユーザー実装の堅牢なCLI引数、ロギング、品質ゲート設定を完全に継承。
#      - これがNexusCoreの新しい中核エントリーポイントとなる。
# ==============================================================================
import sys
import os
import argparse
import logging

# ------------------------------------------------------------------------------
# パス設定
# ------------------------------------------------------------------------------
project_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ------------------------------------------------------------------------------
# 必要なモジュールとエージェントのインポート
# ------------------------------------------------------------------------------
# ▼▼▼▼▼ 統合点 (1/4): RequirementAgentをインポートリストに追加 ▼▼▼▼▼
from nexuscore.agents.requirement_agent import RequirementAgent
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
from nexuscore.core.orchestrator import Orchestrator
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
# from nexuscore.utils.config import config # .envからの読み込みはdotenvで直接行う

def setup_logging(verbose: bool):
    """ロギングの基本設定（旧コードの優れた実装を維持）"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("nexus_core_run.log", mode='w', encoding='utf-8')
        ]
    )
    logging.info(f"Log level set to {logging.getLevelName(log_level)}")

def main():
    """
    コマンドラインからタスクを受け取り、Orchestratorを実行するメイン関数。
    """
    # --- 1. コマンドライン引数の定義（旧コードの堅牢な実装を拡張） ---
    parser = argparse.ArgumentParser(
        description="NexusCore - AI Multi-Agent Development System",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "requirement",
        type=str,
        help="開発したいアプリケーションや機能の自然言語による初期要求。\n例: \"簡単なCRMアプリを作成して。ユーザーを追加、表示できること\""
    )
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="開発プロジェクトが作成される、あるいは対象となるディレクトリのパス。"
    )
    # ▼▼▼▼▼ 統合点 (2/4): --language引数を追加 ▼▼▼▼▼
    parser.add_argument(
        "--language",
        type=str,
        choices=["ja", "en"],
        default="ja",
        help="RequirementAgentが使用する言語（jaまたはen）。"
    )
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    parser.add_argument(
        "--constitution-text",
        type=str,
        default="このプロジェクトのコードは、常にクリーンで読みやすく、保守性が高いこと。また、すべてのコードには型ヒントとdocstringが付与されている必要がある。",
        help="AIチーム全体が従うべきプロジェクトの原則（自然言語）。"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細なデバッグログをコンソールに出力します。"
    )

    args = parser.parse_args()

    # --- 2. ロギングと設定の初期化 ---
    setup_logging(args.verbose)
    
    project_path = os.path.abspath(args.project_path)
    os.makedirs(project_path, exist_ok=True)

    logging.info(f"Project Path: {project_path}")
    logging.info(f"User Initial Requirement: {args.requirement}")
    logging.info(f"Language: {args.language}")

    # --- プロジェクト憲法（品質ゲート含む）の定義（旧コードの優れた実装を維持） ---
    constitution = {
        "description": args.constitution_text,
        "quality_gate": {
            "MIN_COVERAGE": 90,
            "MIN_PYLINT_SCORE": 8.0
        }
    }
    logging.info(f"Full Constitution with Quality Gate: {constitution}")

    try:
        # --- 3. AI開発チーム（エージェント群）の招集 ---
        logging.info("Initializing AI agent team...")
        
        # BaseAgentとLLMRouterにより、APIキーやモデル名は自動で管理される
        
        # ▼▼▼▼▼ 統合点 (3/4): RequirementAgentをチームに追加 ▼▼▼▼▼
        requirement_agent = RequirementAgent(language=args.language)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        architect = ArchitectAgent()
        planner = PlannerAgent()
        coder = CoderAgent()
        tester = TesterAgent()
        # 外部パスの注入（旧コードの堅牢な実装を維持）
        debugger = DebuggerAgent(knowledge_base_path=os.path.join(project_path, "fkb_local.json"), project_path=project_path)
        guardian = GuardianAgent()
        policy_agent = PolicyAgent(policy_rules_path=os.path.join(project_root, "config", "policy_rules.json"))
        postmortem_agent = PostmortemAgent()
        knowledge_curator_agent = KnowledgeCuratorAgent()

        # --- 4. 司令塔 (Orchestrator) の任命 ---
        logging.info("Initializing Orchestrator...")
        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            # ▼▼▼▼▼ 統合点 (4/4): OrchestratorにRequirementAgentを渡す ▼▼▼▼▼
            requirement_agent=requirement_agent,
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            architect=architect,
            planner=planner,
            coder=coder,
            tester=tester,
            debugger=debugger,
            guardian=guardian,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent
        )

        # --- 5. 開発プロセスの開始 ---
        logging.info("Starting full development process...")
        # 新しい一括実行メソッドを、CLI引数を渡して呼び出す
        orchestrator.run_full_project(
            user_initial_request=args.requirement,
            language=args.language
        )
        logging.info("Development process finished successfully.")

    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main CLI: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
