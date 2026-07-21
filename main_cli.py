# ==============================================================================
# ファイル: main_cli.py
# レジストリ: Git (NexusCore repo)
# 日付・日時: 2025-11-15 04:51:11 JST
# 使用/操作メモ: WSL上のVSCodeから本CLIを編集・デバッグ
# メモ: 【統合・最終版】
#      - RequirementAgentを統合し、全自動開発フローの起点とする。
#      - ユーザー実装の堅牢なCLI引数、ロギング、品質ゲート設定を完全に継承。
#      - これがNexusCoreの新しい中核エントリーポイントとなる。
# ==============================================================================
import argparse
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime

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
from nexuscore.agents.architect_agent import ArchitectAgent
from nexuscore.agents.coder_agent import CoderAgent
from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
from nexuscore.agents.debugger_agent import DebuggerAgent
from nexuscore.agents.guardian_agent import GuardianAgent
from nexuscore.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from nexuscore.agents.planner_agent import PlannerAgent
from nexuscore.agents.policy_agent import PolicyAgent
from nexuscore.agents.postmortem_agent import PostmortemAgent
from nexuscore.agents.requirement_agent import RequirementAgent
from nexuscore.agents.tester_agent import TesterAgent
from nexuscore.core.dynamic_orchestrator import DynamicRunLoop
from nexuscore.core.dynamic_router import ActionRegistry

# CR-NEXUS-054: 動的オーケストレーション
from nexuscore.core.goal_spec import GoalSpec, standard_criteria
from nexuscore.core.llm_assisted_router import LLMAssistedRouter

# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
from nexuscore.core.orchestrator import Orchestrator
from nexuscore.llm.llm_router import LLMRouter
from nexuscore.services.patch_applier import PatchApplier

# from nexuscore.utils.config import config # .envからの読み込みはdotenvで直接行う

# ------------------------------------------------------------------------------
# Codex連携フォルダ設定
# ------------------------------------------------------------------------------
CODEX_HISTORY_DIR = os.path.join(project_root, "codex_history")

def setup_logging(verbose: bool):
    """ロギングの基本設定（旧コードの優れた実装を維持）"""
    from nexuscore.utils.log_config import get_logs_dir

    log_level = logging.DEBUG if verbose else logging.INFO
    logs_dir = get_logs_dir()
    log_path = logs_dir / "nexus_core_run.log"

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, mode='a', encoding='utf-8')
        ]
    )
    logging.info(f"Log level set to {logging.getLevelName(log_level)}")
    logging.info(f"Log file: {log_path}")

def _prepare_local_knowledge_base(project_path: str) -> str | None:
    """
    Ensure each project has its own writable knowledge base copy so DebuggerAgent
    can learn locally without touching the global template.
    """
    template_path = os.path.join(project_root, "fkb_local.json")
    project_kb_path = os.path.join(project_path, "fkb_local.json")

    if not os.path.exists(template_path):
        logging.warning("Global knowledge base template not found at %s", template_path)
        return None

    if os.path.exists(project_kb_path):
        return project_kb_path

    try:
        shutil.copy(template_path, project_kb_path)
        logging.info("Copied fkb_local.json template into project directory.")
    except PermissionError as copy_error:
        logging.error("Failed to copy knowledge base template: %s", copy_error, exc_info=True)
        logging.info("Falling back to shared template at %s", template_path)
        return template_path
    except Exception as copy_error:
        logging.error("Failed to copy knowledge base template: %s", copy_error, exc_info=True)
        return None

    return project_kb_path


def _save_codex_artifacts(status_tag: str) -> None:
    """
    nexus_core_run.log と git diff を codex_history に自動保存する。
    """
    try:
        os.makedirs(CODEX_HISTORY_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = f"{timestamp}_{status_tag}"

        run_log_path = os.path.join(project_root, "nexus_core_run.log")
        if os.path.exists(run_log_path):
            shutil.copy(run_log_path, os.path.join(CODEX_HISTORY_DIR, f"{base_name}_run.log"))

        diff_result = subprocess.run(
            ["git", "diff"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False
        )
        diff_output = diff_result.stdout.strip()
        if diff_output:
            diff_path = os.path.join(CODEX_HISTORY_DIR, f"{base_name}_changes.diff")
            with open(diff_path, "w", encoding="utf-8") as diff_file:
                diff_file.write(diff_output)
        else:
            logging.info("Git diff is empty; skipping diff export for %s.", base_name)
    except Exception as artifact_error:
        logging.warning("Codex artifact export failed: %s", artifact_error, exc_info=True)


def run_smoke_gate(
    project_path: str, target_files: list[dict[str, str]]
) -> tuple[bool, list[str]]:
    """成果物チェック（Smoke Test Gate）。

    plan の target_files 全実在 + .py の py_compile 通過を成功条件とする（spec §3-3）。
    role=test のファイルは Stage 1 時点では未生成のため検査対象外。
    """
    import py_compile

    errors: list[str] = []
    for entry in target_files:
        if entry.get("role") == "test":
            continue
        rel = entry.get("path", "")
        abs_path = os.path.join(project_path, rel)
        if not os.path.exists(abs_path):
            errors.append(f"missing artifact: {rel}")
            continue
        if rel.endswith(".py"):
            try:
                py_compile.compile(abs_path, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"syntax error in {rel}: {e.msg}")
    return (not errors), errors


def run_dynamic_mode(orchestrator, llm_router, args) -> int:
    """CR-NEXUS-054: 動的オーケストレーションループを実行する。

    Args:
        orchestrator: 初期化済みの Orchestrator インスタンス。
        llm_router: LLMルーティング用インスタンス（--dynamic-llm-routing 時に使用）。
        args: コマンドライン引数（requirement / language / dynamic_llm_routing /
              max_actions / skip_actions を参照）。

    Returns:
        int: 成功なら 0、ゴール未達なら 1。
    """
    skip_actions = frozenset(
        action.strip() for action in args.skip_actions.split(",") if action.strip()
    )

    goal = GoalSpec(
        description=args.requirement,
        criteria=standard_criteria(),
        max_actions=args.max_actions,
        skip_actions=skip_actions,
    )

    router = None
    if args.dynamic_llm_routing:
        registry = ActionRegistry.from_orchestrator(orchestrator)
        router = LLMAssistedRouter.from_llm_router(
            llm_router=llm_router,
            registry=registry,
            goal_description=args.requirement,
            skip_actions=skip_actions,
        )

    run_loop = DynamicRunLoop(orchestrator=orchestrator, goal=goal, router=router)
    result = run_loop.run(user_requirement=args.requirement, language=args.language)

    logging.info(result.message)
    logging.info("実行アクション数: %d", result.actions_executed)
    logging.info("=== Decision Trace ===\n%s", result.trace.summary())

    if not result.success:
        logging.error("未達条件: %s", ", ".join(result.unsatisfied_criteria))
        return 1
    return 0


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
    parser.add_argument(
        "--requirement-ui",
        action="store_true",
        help="RequirementAgentのGradio UIを起動して対話的に要件を決める場合に指定します。"
    )
    # ▼▼▼ CR-NEXUS-054: 動的オーケストレーション ▼▼▼
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="ゴール駆動の動的オーケストレーションで実行します（固定パイプラインの代わり）。"
    )
    parser.add_argument(
        "--dynamic-llm-routing",
        action="store_true",
        help="--dynamic 時に、軽量LLMによる次アクション提案を有効にします（無効提案は自動でルールベースにフォールバック）。"
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=12,
        help="--dynamic 時の最大アクション数（暴走防止予算。既定: 12）。"
    )
    parser.add_argument(
        "--skip-actions",
        type=str,
        default="",
        help="--dynamic 時にスキップするアクションのカンマ区切りリスト。例: architecture,review"
    )
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    args = parser.parse_args()

    # --- 2. ロギングと設定の初期化 ---
    setup_logging(args.verbose)

    project_path = os.path.abspath(args.project_path)
    os.makedirs(project_path, exist_ok=True)

    logging.info(f"Project Path: {project_path}")
    logging.info(f"User Initial Requirement: {args.requirement}")
    logging.info(f"Language: {args.language}")
    local_kb_path = _prepare_local_knowledge_base(project_path)

    # --- プロジェクト憲法（品質ゲート含む）の定義（旧コードの優れた実装を維持） ---
    constitution = {
        "description": args.constitution_text,
        "quality_gate": {
            "MIN_COVERAGE": 90,
            "MIN_PYLINT_SCORE": 8.0
        }
    }
    logging.info(f"Full Constitution with Quality Gate: {constitution}")

    run_status = "success"
    try:
        # --- 3. AI開発チーム（エージェント群）の招集 ---
        logging.info("Initializing AI agent team...")

        # BaseAgentとLLMRouterにより、APIキーやモデル名は自動で管理される

        # ▼▼▼▼▼ 統合点 (3/4): RequirementAgentをチームに追加 ▼▼▼▼▼
        requirement_agent = RequirementAgent(language=args.language)
        if hasattr(requirement_agent, "set_initial_requirement"):
            requirement_agent.set_initial_requirement(args.requirement)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        architect = ArchitectAgent()
        planner = PlannerAgent()
        coder = CoderAgent()
        tester = TesterAgent()
        # 外部パスの注入（旧コードの堅牢な実装を維持）
        debugger = DebuggerAgent(knowledge_base_path=local_kb_path)
        guardian = GuardianAgent()  # cred は GuardianAgent.__init__ 内で env 読込（GUARDIAN_MODEL/ANTHROPIC_API_KEY）
        policy_agent = PolicyAgent(policy_rules_path=os.path.join(project_root, "config", "policy_rules.json"))
        postmortem_agent = PostmortemAgent()
        knowledge_curator_agent = KnowledgeCuratorAgent()
        patch_applier = PatchApplier()

        # Optional agents (pre-pipeline context + post-review governance)
        context_agent = None
        try:
            from nexuscore.analyzer.context_agent import ContextAgent
            context_agent = ContextAgent(project_root=project_path)
        except Exception as e:
            logging.warning(f"ContextAgent initialization skipped: {e}")

        constitutional_council_agent = None
        try:
            constitutional_council_agent = ConstitutionalCouncilAgent(
                policy_path=os.path.join(project_path, "config", "policy_rules.json"),
                amendments_dir=os.path.join(project_path, "amendments"),
            )
        except Exception as e:
            logging.warning(f"ConstitutionalCouncilAgent initialization skipped: {e}")

        llm_router = LLMRouter()

        # --- 4. 司令塔 (Orchestrator) の任命 ---
        logging.info("Initializing Orchestrator...")
        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            # ▼▼▼▼▼ 統合点 (4/4): OrchestratorにRequirementAgentを渡す ▼▼▼▼▼
            requirement_agent=requirement_agent,
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            architect_agent=architect,
            planner_agent=planner,
            coder_agent=coder,
            tester_agent=tester,
            debugger_agent=debugger,
            guardian_agent=guardian,
            policy_agent=policy_agent,
            postmortem_agent=postmortem_agent,
            knowledge_curator_agent=knowledge_curator_agent,
            patch_applier_agent=patch_applier,
            context_agent=context_agent,
            constitutional_council_agent=constitutional_council_agent,
            llm_router=llm_router
        )

        # --- 5. 開発プロセスの開始 ---
        result_context = None
        if args.dynamic:
            # CR-NEXUS-054: ゴール駆動の動的オーケストレーション
            logging.info("Starting dynamic goal-driven process (CR-NEXUS-054)...")
            dynamic_exit = run_dynamic_mode(orchestrator, llm_router, args)
            if dynamic_exit != 0:
                run_status = "failure"
                raise SystemExit(dynamic_exit)
        else:
            logging.info("Starting full development process...")
            # 従来の固定パイプライン（後方互換）
            result_context = orchestrator.run_full_project(
                user_requirement=args.requirement,
                language=args.language
            )
        logging.info("Development process finished successfully.")

        # --- 6. 成果物チェック（Smoke Test Gate・spec §3-3）+ 品質ループ終端状態（spec §4-4） ---
        exit_code = 0
        if not args.dynamic and result_context is not None:
            from nexuscore.core.plan_contract import extract_target_files

            target_files, _degraded = extract_target_files(result_context.plan)
            ok, smoke_errors = run_smoke_gate(project_path, target_files)
            if ok:
                logging.info("Smoke Test PASSED: all artifacts exist and compile")
            else:
                for err in smoke_errors:
                    logging.error(f"Smoke Test FAILED: {err}")
                exit_code = 1

            terminal_state = getattr(result_context, "terminal_state", "APPROVED")
            if terminal_state == "NEEDS_HUMAN_REVIEW":
                logging.warning(
                    "Quality loop terminal state: NEEDS_HUMAN_REVIEW — see review_report.md"
                )
                exit_code = 2
            elif terminal_state == "APPROVED" and exit_code == 0:
                logging.info("Quality loop terminal state: APPROVED")

        if exit_code != 0:
            run_status = "failure"
            raise SystemExit(exit_code)

    except SystemExit:
        raise
    except Exception as e:
        run_status = "failure"
        logging.critical(f"An unexpected error occurred in the main CLI: {e}", exc_info=True)
        raise SystemExit(1) from e
    finally:
        _save_codex_artifacts(run_status)

if __name__ == "__main__":
    main()
