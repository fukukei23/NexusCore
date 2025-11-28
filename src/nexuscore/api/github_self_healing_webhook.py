"""
github_self_healing_webhook.py

GitHub pull_request Webhook を受信して Self-Healing Service を実行するエンドポイント。

安全ガード:
  - PR ラベル "self-healing" が付いているものだけ実行
  - GuardianAgent によるレビュー統合
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.session_control import SessionController
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.agents.patch_applier import PatchApplier

logger = logging.getLogger(__name__)

# エージェントのインポート（オプション）
try:
    from nexuscore.agents.debugger_agent import DebuggerAgent
except ImportError:
    DebuggerAgent = None  # type: ignore

try:
    from nexuscore.agents.guardian_agent import GuardianAgent
except ImportError:
    GuardianAgent = None  # type: ignore

try:
    from nexuscore.services.self_healing_service import SelfHealingService
except ImportError:
    SelfHealingService = None  # type: ignore


def parse_pull_request_event(
    payload: Dict[str, Any],
    config: SelfHealingConfig,
) -> Optional[Tuple[str, int, str]]:
    """
    GitHub pull_request イベントから必要な情報を抜き出す。

    ガード:
      - PR に config.label ラベルが付いているか？
      - base ブランチが config.allowed_target_branches に含まれているか？
    """
    repository = payload.get("repository") or {}
    pr = payload.get("pull_request") or {}
    action = payload.get("action")

    # 対象アクションのみ処理
    allowed_actions = {"opened", "reopened", "synchronize", "ready_for_review"}
    if action not in allowed_actions:
        logger.info(f"Ignoring PR action: {action}")
        return None

    # draft PR はスキップ
    if pr.get("draft"):
        logger.info("Ignoring draft PR (draft=True).")
        return None

    # ▼ ベースブランチチェック
    base = pr.get("base") or {}
    base_ref = base.get("ref")
    if config.allowed_target_branches:
        if base_ref not in config.allowed_target_branches:
            logger.info(
                f"Ignoring PR with base branch '{base_ref}' "
                f"(allowed: {config.allowed_target_branches})"
            )
            return None

    # ▼ ラベルチェック (config.label)
    labels = pr.get("labels") or []
    label_names = {lbl.get("name", "") for lbl in labels}
    required_label = config.label
    if required_label not in label_names:
        logger.info(
            f"Ignoring PR without required label: '{required_label}'. "
            f"labels={sorted(label_names)}"
        )
        return None

    repo_full_name = repository.get("full_name")
    pr_number = pr.get("number")
    head = pr.get("head") or {}
    head_sha = head.get("sha")

    if not all([repo_full_name, pr_number, head_sha]):
        logger.warning("PR event missing required fields.")
        return None

    return str(repo_full_name), int(pr_number), str(head_sha)


def format_pr_comment(
    result: Dict[str, Any],
    project_root: Optional[str] = None,
    repo_full_name: Optional[str] = None,
    pr_number: Optional[int] = None,
) -> str:
    """
    Self-Healing の実行結果を GitHub PR コメント形式の Markdown に整形する。

    新しいメタ情報付きフォーマット（Self-Healing Summary + Guardian Review + Change Summary + Links）を使用する。
    """
    from nexuscore.integration.github_pr_comment import PRCommentContext, build_pr_comment
    from nexuscore.integration.github_pr_summary import generate_pr_change_summary

    # Webapp モデルが利用可能か確認
    try:
        from nexuscore.webapp.models import Run, Project
        from nexuscore.webapp import db
        HAS_WEBAPP = True
    except ImportError:
        HAS_WEBAPP = False
        Run = None  # type: ignore
        Project = None  # type: ignore
        db = None  # type: ignore

    status = result.get("status", "unknown")
    summary = result.get("summary", "")
    details = result.get("details", {})
    run_id = result.get("run_id", "N/A")

    # Run と Project を取得（webapp が利用可能な場合）
    run = None
    project = None
    if HAS_WEBAPP and Run and db:
        try:
            # run_id で Run を検索
            run = Run.query.filter_by(run_id=run_id).first()  # type: ignore
            if run and hasattr(run, "project_id"):
                project = Project.query.filter_by(id=run.project_id).first()  # type: ignore
        except Exception as e:
            logger.warning(f"Failed to load Run/Project from DB: {e}", exc_info=True)

    # Guardian 情報を取得
    guardian_status = details.get("guardian_status", "")
    guardian_comment = details.get("guardian_comment", "")

    # Guardian レビューを Markdown 形式に整形
    guardian_review_markdown = ""
    if guardian_status:
        guardian_review_markdown += f"**Status**: `{guardian_status}`\n\n"
    if guardian_comment:
        guardian_review_markdown += f"**Comment**:\n\n{guardian_comment}\n"
    if not guardian_review_markdown:
        guardian_review_markdown = "_(no review content)_\n"

    # AI による修正要約を生成（webapp が利用可能で run が存在する場合）
    change_summary = None
    if HAS_WEBAPP and run:
        try:
            change_summary = generate_pr_change_summary(
                run=run,
                guardian_review_markdown=guardian_review_markdown,
                max_tokens=512,
            )
        except Exception as e:
            logger.warning(f"Failed to generate change summary: {e}", exc_info=True)

    # E-4: Before/After 差分サマリーを取得
    diff_summary = details.get("diff_summary")

    # E-3: Run Markdown レポートを取得
    markdown_report = details.get("markdown_report")
    if not markdown_report and run_id != "N/A":
        try:
            from nexuscore.integration.github_pr_comment import load_run_markdown
            markdown_report = load_run_markdown(run_id)
        except Exception as e:
            logger.warning(f"Failed to load run markdown: {e}", exc_info=True)

    # PRCommentContext を作成
    ctx = PRCommentContext(
        project=project,
        run=run,
        guardian_review_markdown=guardian_review_markdown,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        change_summary=change_summary,
        diff_summary=diff_summary,
        markdown_report=markdown_report,
        details=details,  # E-5: メトリクス統合用
    )

    # PR コメントを組み立て
    return build_pr_comment(ctx)


def _init_self_healing_service(
    project_root: str,
    config: SelfHealingConfig,
) -> Any:
    """
    SelfHealingService + DebuggerAgent + GuardianAgent を初期化するヘルパー。

    project_root と SelfHealingConfig を受け取り、
    SelfHealingService に渡す。
    """
    if SelfHealingService is None:
        raise ImportError("SelfHealingService is not available")

    session_id = "self_healing_webhook"
    sessions_dir = os.path.join(project_root, ".nexus", "sessions")
    session_controller = SessionController(session_id=session_id, root_dir=sessions_dir)

    patch_applier = PatchApplier()
    history_logger = RunHistoryLogger(project_root=project_root)

    debugger = None
    guardian = None

    if DebuggerAgent is not None:
        try:
            debugger = DebuggerAgent()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to initialize DebuggerAgent: {e}", exc_info=True)

    if GuardianAgent is not None:
        try:
            guardian = GuardianAgent()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to initialize GuardianAgent: {e}", exc_info=True)

    service = SelfHealingService(
        project_root=project_root,
        session_controller=session_controller,
        debugger_agent=debugger,
        patch_applier=patch_applier,
        history_logger=history_logger,
        config=config,
    )
    service._guardian_agent = guardian  # type: ignore[attr-defined]

    return service


def github_webhook(
    payload: Dict[str, Any],
    project_root: Optional[str] = None,
    event: Optional[str] = None,
    delivery: Optional[str] = None,
) -> Dict[str, Any]:
    """
    GitHub pull_request Webhook を処理して Self-Healing を実行する。

    :param payload: GitHub Webhook のペイロード
    :param project_root: NexusCore プロジェクトのルート（省略時は環境変数から取得）
    :param event: GitHub イベントタイプ（デバッグ用）
    :param delivery: GitHub Webhook delivery ID（デバッグ用）
    :return: 実行結果の辞書
    """
    # デバッグログ
    logger.info(
        "GitHub webhook received: event=%s delivery=%s",
        event or "unknown",
        delivery or "unknown",
    )

    # プロジェクトルートを決定 (NEXUS_PROJECT_ROOT or CWD)
    if project_root is None:
        project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())

    config = SelfHealingConfig.load(project_root)

    # PR イベントをパース
    parsed = parse_pull_request_event(payload, config)
    if not parsed:
        return {
            "status": "skipped",
            "summary": "PR does not meet criteria for self-healing (missing label, draft, etc.)",
        }

    repo_full_name, pr_number, head_sha = parsed

    logger.info(
        f"Processing self-healing for {repo_full_name} PR #{pr_number} (head={head_sha[:7]})"
    )

    # Self-Healing Service を初期化
    service = _init_self_healing_service(project_root=project_root, config=config)
    guardian_agent = getattr(service, "_guardian_agent", None)

    # Self-Healing を実行
    try:
        result = service.run_for_pull_request(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
        )

        # GuardianAgent のレビューを統合
        if guardian_agent is not None:
            try:
                guardian_result = None

                # 優先: review_self_healing(result) があればそれを使う
                if hasattr(guardian_agent, "review_self_healing"):
                    guardian_result = guardian_agent.review_self_healing(result)
                # 互換: review(result) があればそちらを使う
                elif hasattr(guardian_agent, "review"):
                    guardian_result = guardian_agent.review(result)

                if guardian_result:
                    details = result.get("details") or {}

                    # Guardian のコメント・ステータスを統合
                    guardian_comment = guardian_result.get("comment") or guardian_result.get("message")
                    guardian_status = guardian_result.get("status") or guardian_result.get("decision")

                    if guardian_comment:
                        details["guardian_comment"] = guardian_comment
                    if guardian_status:
                        details["guardian_status"] = guardian_status

                    # 必要であれば、Guardian の judgment で status を上書きすることもできる
                    # 例: guardian_result["override_status"] に "needs_manual_review" などが入っていれば採用
                    override_status = guardian_result.get("override_status")
                    if override_status:
                        result["status"] = override_status

                    result["details"] = details

            except Exception as e:  # noqa: BLE001
                logger.error(f"GuardianAgent review failed: {e}", exc_info=True)

        # モデル名を result に追加（PRコメント用）
        if guardian_agent is not None and hasattr(guardian_agent, "model"):
            model_name = guardian_agent.model or "NexusCore Auto-Reviewer"
            details = result.get("details") or {}
            details["model_name"] = model_name
            result["details"] = details

        return result

    except Exception as e:
        logger.error(f"Self-healing execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "summary": f"Self-healing execution failed: {str(e)}",
            "details": {},
        }

