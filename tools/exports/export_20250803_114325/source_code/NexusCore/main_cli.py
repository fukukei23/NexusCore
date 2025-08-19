# ==============================================================================
# フォルダ: (プロジェクトルート)
# ファイル名: main_cli.py
# メモ: 【品質ゲート対応版】Orchestratorに渡す「憲法(constitution)」に、
#      テストカバレッジやPylintスコアの最低基準値を設定するロジックを追加。
# ==============================================================================
import sys
import os
import argparse
import logging

# ------------------------------------------------------------------------------
# パス設定
# ------------------------------------------------------------------------------
# このスクリプトがプロジェクトのどこから実行されても、
# `src`フォルダ内のモジュールを正しく見つけられるようにするための設定。
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ------------------------------------------------------------------------------
# 必要なモジュールとエージェントのインポート
# ------------------------------------------------------------------------------
from src.core.orchestrator import Orchestrator
from src.agents.architect_agent import ArchitectAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.postmortem_agent import PostmortemAgent
from src.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from src.utils.config import config

def setup_logging(verbose: bool):
    """ロギングの基本設定"""
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
    # --- 1. コマンドライン引数の定義 ---
    parser = argparse.ArgumentParser(
        description="NexusCore - AI Multi-Agent Development System",
        formatter_class=argparse.RawTextHelpFormatter # ヘルプの改行を維持
    )
    
    parser.add_argument(
        "requirement",
        type=str,
        help="作成したいアプリケーションや機能の自然言語による説明。\n例: \"簡単なCRMアプリを作成して。ユーザーを追加、表示できること\""
    )
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="開発プロジェクトが作成される、あるいは対象となるディレクトリのパス。"
    )
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
    logging.info(f"User Requirement: {args.requirement}")
    logging.info(f"Constitution Text: {args.constitution_text}")

    # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
    # プロジェクト憲法を構造化データとして定義します。
    # これにより、品質ゲートのような具体的なルールをシステムに組み込めます。
    constitution = {
        "description": args.constitution_text,
        "quality_gate": {
            "MIN_COVERAGE": 90,       # テストカバレッジの最低基準値 (%)
            "MIN_PYLINT_SCORE": 8.0   # Pylintスコアの最低基準値 (/10)
        }
    }
    logging.info(f"Full Constitution with Quality Gate: {constitution}")
    # --- ★★★★★ ここまで ★★★★★ ---

    try:
        # --- 3. AI開発チーム（エージェント群）の招集 ---
        logging.info("Initializing AI agent team...")
        
        # .envファイルからモデル名とAPIキーを取得
        model_name = "gemini-1.5-pro-latest" 
        api_key = config.GEMINI_API_KEY_AGENT_A 
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY_AGENT_A is not set in the .env file.")

        architect = ArchitectAgent(api_key=api_key, model=model_name)
        planner = PlannerAgent(api_key=api_key, model=model_name)
        coder = CoderAgent(api_key=api_key, model=model_name)
        tester = TesterAgent(api_key=api_key, model=model_name)
        debugger = DebuggerAgent(api_key=api_key, model=model_name, knowledge_base_path="fkb_local.json", project_path=project_path)
        guardian = GuardianAgent(api_key=api_key, model=model_name)
        policy_agent = PolicyAgent(api_key=api_key, model=model_name, policy_rules_path="config/policy_rules.json")
        postmortem_agent = PostmortemAgent(api_key=api_key, model=model_name)
        knowledge_curator_agent = KnowledgeCuratorAgent(api_key=api_key, model=model_name)

        # --- 4. 司令塔 (Orchestrator) の任命 ---
        logging.info("Initializing Orchestrator...")
        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,  # ★ 構造化された憲法を渡す
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
        logging.info("Starting development process...")
        orchestrator.design_phase(args.requirement)
        orchestrator.development_cycle(args.requirement)
        logging.info("Development process finished successfully.")

    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main CLI: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
