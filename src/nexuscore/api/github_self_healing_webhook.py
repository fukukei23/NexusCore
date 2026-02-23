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
from typing import Any

from nexuscore.agents.patch_applier import PatchApplier
from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.session_control import SessionController

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
    payload: dict[str, Any],
    config: SelfHealingConfig,
) -> tuple[str, int, str] | None:
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
    result: dict[str, Any],
    project_root: str | None = None,
    repo_full_name: str | None = None,
    pr_number: int | None = None,
    commit_sha: str | None = None,  # CR-E3: 対象コミットの SHA
) -> str:
    """
    Self-Healing の実行結果を GitHub PR コメント形式の Markdown に整形する。

    CR-NEXUS-039: DB/Flask 依存を排除し、result パラメータだけでコメントを生成する。
    """
    from nexuscore.integration.github_pr_comment import PRCommentContext, build_pr_comment

    status = result.get("status", "unknown")
    summary = result.get("summary", "")
    details = result.get("details", {})
    run_id = result.get("run_id", "N/A")
    session_id = result.get("session_id")

    # Guardian 情報を取得
    guardian_status = details.get("guardian_status", "")
    guardian_comment = details.get("guardian_comment", "")
    patch_preview = details.get("patch_preview")

    # Guardian レビューを Markdown 形式に整形
    guardian_review_markdown = ""
    if guardian_status:
        guardian_review_markdown += f"**Status**: `{guardian_status}`\n\n"
    if guardian_comment:
        guardian_review_markdown += f"**Comment**:\n\n{guardian_comment}\n"
    if patch_preview:
        guardian_review_markdown += f"\n### Patch Preview\n\n{patch_preview}\n"
    if not guardian_review_markdown:
        guardian_review_markdown = "_(no review content)_\n"

    # E-4: Before/After 差分サマリーを取得
    diff_summary = details.get("diff_summary")

    # Semantic Diff を取得
    semantic_diffs = details.get("semantic_diffs") if details else None

    # E-3: Run Markdown レポートを取得
    markdown_report = details.get("markdown_report")
    if not markdown_report and run_id != "N/A":
        try:
            from nexuscore.integration.github_pr_comment import load_run_markdown

            markdown_report = load_run_markdown(run_id)
        except Exception as e:
            logger.warning(f"Failed to load run markdown: {e}", exc_info=True)

    # PRCommentContext を作成（run と project は None にして、result から情報を取得）
    ctx = PRCommentContext(
        project=None,  # CR-NEXUS-039: DB 依存を排除
        run=None,  # CR-NEXUS-039: DB 依存を排除
        guardian_review_markdown=guardian_review_markdown,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        commit_sha=commit_sha,
        change_summary=None,  # CR-NEXUS-039: DB 依存のため削除
        diff_summary=diff_summary,
        markdown_report=markdown_report,
        details=details,
        semantic_diffs=semantic_diffs,
    )

    # PR コメントを組み立て
    comment_parts = []

    # CR-NEXUS-039: "Self-Healing Result" ヘッダーを常に含める（run/project が None でも）
    comment_parts.append("## Self-Healing Result\n\n")
    comment_parts.append(f"**Status**: `{status}`\n\n")
    if summary:
        comment_parts.append(f"**Summary**: {summary}\n\n")
    if run_id and run_id != "N/A":
        comment_parts.append(f"**Run ID**: `{run_id}`\n\n")
    if session_id:
        comment_parts.append(f"**Session ID**: `{session_id}`\n\n")

    # CR-NEXUS-039: blocked_test_paths がある場合は "Blocked Test Files" セクションを追加
    blocked_test_paths = details.get("blocked_test_paths")
    if blocked_test_paths:
        comment_parts.append("### Blocked Test Files\n\n")
        for path in blocked_test_paths:
            comment_parts.append(f"- `{path}`\n")
        comment_parts.append("\n")

    # build_pr_comment() で生成されたコメントを追加（Guardian Review など）
    build_comment = build_pr_comment(ctx)

    # CR-NEXUS-039 Follow-up-2: 二重出力防止（build_pr_comment が誤って Self-Healing Result を出した場合の安全弁）
    if "## Self-Healing Result" in build_comment:
        logger.warning(
            "build_pr_comment() returned '## Self-Healing Result' header, "
            "which should be generated by format_pr_comment() instead. Removing duplicate section."
        )
        # セクション全体を除去（## Self-Healing Result から次の ## 見出しまで、または末尾まで）
        lines = build_comment.split("\n")
        filtered_lines = []
        in_section = False
        for line in lines:
            # ## Self-Healing Result 行を検出したら削除開始
            if line.strip() == "## Self-Healing Result":
                in_section = True
                continue
            # 次の見出し（## で始まる行）が現れたら削除終了
            if in_section and line.strip().startswith("## "):
                in_section = False
            # セクション内の行は削除
            if in_section:
                continue
            filtered_lines.append(line)
        build_comment = "\n".join(filtered_lines).strip()

    comment_parts.append(build_comment)

    return "\n".join(comment_parts)


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
    payload: dict[str, Any],
    project_root: str | None = None,
    event: str | None = None,
    delivery: str | None = None,
) -> dict[str, Any]:
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
                    guardian_comment = guardian_result.get("comment") or guardian_result.get(
                        "message"
                    )
                    guardian_status = guardian_result.get("status") or guardian_result.get(
                        "decision"
                    )

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
