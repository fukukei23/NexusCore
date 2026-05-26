from __future__ import annotations

import logging
import os
from typing import Any

from nexuscore.services.patch_applier import PatchApplier
from nexuscore.config.self_healing_config import SelfHealingConfig
from nexuscore.core.run_history import RunHistoryLogger
from nexuscore.core.session_control import SessionController

logger = logging.getLogger(__name__)

# エージェントのインポート（オプション）
try:
    from nexuscore.agents.debugger_agent import DebuggerAgent
except ImportError:
    DebuggerAgent = None

try:
    from nexuscore.agents.guardian_agent import GuardianAgent
except ImportError:
    GuardianAgent = None

try:
    from nexuscore.services.self_healing_service import SelfHealingService
except ImportError:
    SelfHealingService = None


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

    return str(repo_full_name), int(pr_number), str(head_sha)  # type: ignore[arg-type]


def _build_guardian_review_markdown(details: dict[str, Any]) -> str:
    guardian_status = details.get("guardian_status", "")
    guardian_comment = details.get("guardian_comment", "")
    patch_preview = details.get("patch_preview")

    md = ""
    if guardian_status:
        md += f"**Status**: `{guardian_status}`\n\n"
    if guardian_comment:
        md += f"**Comment**:\n\n{guardian_comment}\n"
    if patch_preview:
        md += f"\n### Patch Preview\n\n{patch_preview}\n"
    return md or "_(no review content)_\n"


def _remove_duplicate_self_healing_result(comment: str) -> str:
    if "## Self-Healing Result" not in comment:
        return comment
    lines = comment.split("\n")
    filtered = []
    in_section = False
    for line in lines:
        if line.strip() == "## Self-Healing Result":
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            in_section = False
        if in_section:
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def format_pr_comment(
    result: dict[str, Any],
    project_root: str | None = None,
    repo_full_name: str | None = None,
    pr_number: int | None = None,
    commit_sha: str | None = None,
) -> str:
    """Self-Healing の実行結果を GitHub PR コメント形式の Markdown に整形する。"""
    from nexuscore.integration.github_pr_comment import PRCommentContext, build_pr_comment

    status = result.get("status", "unknown")
    summary = result.get("summary", "")
    details = result.get("details", {})
    run_id = result.get("run_id", "N/A")

    guardian_review_markdown = _build_guardian_review_markdown(details)

    markdown_report = details.get("markdown_report")
    if not markdown_report and run_id != "N/A":
        try:
            from nexuscore.integration.github_pr_comment import load_run_markdown
            markdown_report = load_run_markdown(run_id)
        except (ImportError, OSError) as e:
            logger.warning(f"Failed to load run markdown: {e}", exc_info=True)

    ctx = PRCommentContext(
        project=None,
        run=None,
        guardian_review_markdown=guardian_review_markdown,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        commit_sha=commit_sha,
        diff_summary=details.get("diff_summary"),
        markdown_report=markdown_report,
        details=details,
        semantic_diffs=details.get("semantic_diffs") if details else None,
    )

    parts = ["## Self-Healing Result\n\n", f"**Status**: `{status}`\n\n"]
    if summary:
        parts.append(f"**Summary**: {summary}\n\n")
    if run_id and run_id != "N/A":
        parts.append(f"**Run ID**: `{run_id}`\n\n")
    session_id = result.get("session_id")
    if session_id:
        parts.append(f"**Session ID**: `{session_id}`\n\n")

    blocked = details.get("blocked_test_paths")
    if blocked:
        parts.append("### Blocked Test Files\n\n")
        for path in blocked:
            parts.append(f"- `{path}`\n")
        parts.append("\n")

    build_comment = build_pr_comment(ctx)
    parts.append(_remove_duplicate_self_healing_result(build_comment))

    return "\n".join(parts)


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
    service._guardian_agent = guardian

    return service


def _integrate_guardian_review(result: dict[str, Any], guardian_agent: Any) -> None:
    """GuardianAgent のレビュー結果を result に統合する（in-place）"""
    try:
        guardian_result = None
        if hasattr(guardian_agent, "review_self_healing"):
            guardian_result = guardian_agent.review_self_healing(result)
        elif hasattr(guardian_agent, "review"):
            guardian_result = guardian_agent.review(result)

        if guardian_result:
            details = result.get("details") or {}
            guardian_comment = guardian_result.get("comment") or guardian_result.get("message")
            guardian_status = guardian_result.get("status") or guardian_result.get("decision")

            if guardian_comment:
                details["guardian_comment"] = guardian_comment
            if guardian_status:
                details["guardian_status"] = guardian_status

            override_status = guardian_result.get("override_status")
            if override_status:
                result["status"] = override_status

            result["details"] = details
    except Exception as e:  # noqa: BLE001
        logger.error(f"GuardianAgent review failed: {e}", exc_info=True)

    if hasattr(guardian_agent, "model"):
        details = result.get("details") or {}
        details["model_name"] = guardian_agent.model or "NexusCore Auto-Reviewer"
        result["details"] = details


def github_webhook(
    payload: dict[str, Any],
    project_root: str | None = None,
    event: str | None = None,
    delivery: str | None = None,
) -> dict[str, Any]:
    """GitHub pull_request Webhook を処理して Self-Healing を実行する。"""
    logger.info("GitHub webhook received: event=%s delivery=%s", event or "unknown", delivery or "unknown")

    if project_root is None:
        project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())

    config = SelfHealingConfig.load(project_root)
    parsed = parse_pull_request_event(payload, config)
    if not parsed:
        return {"status": "skipped", "summary": "PR does not meet criteria for self-healing"}

    repo_full_name, pr_number, head_sha = parsed
    logger.info(f"Processing self-healing for {repo_full_name} PR #{pr_number} (head={head_sha[:7]})")

    service = _init_self_healing_service(project_root=project_root, config=config)
    guardian_agent = getattr(service, "_guardian_agent", None)

    try:
        result = service.run_for_pull_request(
            repo_full_name=repo_full_name, pr_number=pr_number, head_sha=head_sha,
        )

        if guardian_agent is not None:
            _integrate_guardian_review(result, guardian_agent)

        return result

    except Exception as e:  # noqa: BLE001
        logger.error(f"Self-healing execution failed: {e}", exc_info=True)
        return {"status": "error", "summary": f"Self-healing execution failed: {str(e)}", "details": {}}
