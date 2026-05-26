from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from ._formatters import (
    format_diff_summary_block,
    format_markdown_report_block,
    format_semantic_diff_block,
    load_run_markdown,
    render_summary_card,
)
from ._metrics import (
    _collect_run_metrics,
    _compute_recent_success_rate,
    build_project_dashboard_url,
    build_project_logs_url,
    build_run_logs_url,
)

logger = logging.getLogger(__name__)


class PRCommentContext(BaseModel):
    """PR コメント組み立てに必要なコンテキスト情報"""

    project: object | None = None
    run: object | None = None
    guardian_review_markdown: str = ""
    repo_full_name: str | None = None
    pr_number: int | None = None
    branch_name: str | None = None
    commit_sha: str | None = None  # CR-E3
    change_summary: str | None = None  # B-3
    diff_summary: str | dict[str, str] | None = None  # E-4/E-5
    markdown_report: str | None = None  # E-3
    details: dict[str, Any] | None = None  # E-5
    semantic_diffs: dict[str, dict[str, Any]] | None = None


def format_metadata_block(
    run_id: str,
    pr_number: int | None,
    commit_sha: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    duration_seconds: float,
    primary_model: str,
    aux_models: list[str],
    changed_files: int,
    added_lines: int,
    removed_lines: int,
    success_rate_last_n: float | None = None,
    recent_runs_window: int = 30,
) -> str:
    """CR-E3: Self-Healing メタ情報ブロックを生成する"""
    parts: list[str] = []

    parts.append("### 🛠 Self-Healing Summary\n")

    parts.append(f"- Run ID: `{run_id}`")
    if pr_number:
        parts.append(f"- PR: #{pr_number}")
    if commit_sha:
        short_sha = commit_sha[:7] if len(commit_sha) > 7 else commit_sha
        parts.append(f"- Commit: `{short_sha}`")
    parts.append("")

    parts.append("**Execution**")
    if start_time:
        parts.append(f"- Start: {start_time.isoformat()}Z")
    else:
        parts.append("- Start: N/A")
    if end_time:
        parts.append(f"- End:   {end_time.isoformat()}Z")
    else:
        parts.append("- End:   N/A")

    if duration_seconds > 0:
        if duration_seconds < 60:
            duration_str = f"{duration_seconds:.1f}s"
        elif duration_seconds < 3600:
            duration_str = f"{duration_seconds / 60:.1f}m"
        else:
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            duration_str = f"{hours}h {minutes}m"
    else:
        duration_str = "N/A"
    parts.append(f"- Duration: {duration_str}")

    model_parts = [primary_model]
    if aux_models:
        model_parts.extend(aux_models)
    if len(model_parts) == 1:
        parts.append(f"- Model: {primary_model}")
    else:
        parts.append(f"- Model: {primary_model} (primary), {', '.join(aux_models)} (aux)")
    parts.append("")

    parts.append("**Effect**")
    parts.append(f"- Changed files: {changed_files}")
    parts.append(f"- +{added_lines} / -{removed_lines} lines")
    parts.append("")

    parts.append("**Reliability**")
    if success_rate_last_n is not None:
        success_rate_percent = success_rate_last_n * 100
        parts.append(
            f"- Success rate (last {recent_runs_window} runs): {success_rate_percent:.1f}%"
        )
    else:
        parts.append(f"- Success rate (last {recent_runs_window} runs): N/A")
    parts.append("")

    return "\n".join(parts)


def _build_metadata_section(ctx: PRCommentContext) -> str | None:
    if ctx.run is None or ctx.project is None:
        return None
    try:
        metrics = _collect_run_metrics(ctx.run)
        project_id = getattr(ctx.project, "id", 0)
        success_rate = _compute_recent_success_rate(project_id, limit=30) if project_id > 0 else None
        run_id = getattr(ctx.run, "run_id", "unknown")

        model_call_counts = metrics.get("model_call_counts", {})
        primary_model = "N/A"
        aux_models: list[str] = []
        if ctx.details:
            model_name = ctx.details.get("model") or ctx.details.get("model_name")
            if model_name:
                primary_model = str(model_name)
        if primary_model == "N/A" and model_call_counts:
            sorted_models = sorted(model_call_counts.items(), key=lambda x: x[1], reverse=True)
            if sorted_models:
                primary_model = sorted_models[0][0]
                aux_models = [m for m, _ in sorted_models[1:]]

        return format_metadata_block(
            run_id=run_id,
            pr_number=ctx.pr_number,
            commit_sha=ctx.commit_sha,
            start_time=metrics.get("start_time"),
            end_time=metrics.get("end_time"),
            duration_seconds=metrics.get("duration_seconds", 0.0),
            primary_model=primary_model,
            aux_models=aux_models,
            changed_files=metrics.get("patch_files_count", 0),
            added_lines=metrics.get("added_lines", 0),
            removed_lines=metrics.get("removed_lines", 0),
            success_rate_last_n=success_rate,
            recent_runs_window=30,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to build Self-Healing metadata block: {e}", exc_info=True)
        return None


def _build_summary_card_section(ctx: PRCommentContext) -> str | None:
    if ctx.run is None or ctx.project is None:
        return None
    try:
        metrics = _collect_run_metrics(ctx.run)
        project_id = getattr(ctx.project, "id", 0)
        success_rate = _compute_recent_success_rate(project_id, limit=30) if project_id > 0 else 0.0
        project_name = getattr(ctx.project, "name", "Unknown")
        run_id = getattr(ctx.run, "run_id", "unknown")
        run_status = getattr(ctx.run, "status", "UNKNOWN")

        summary_card = render_summary_card(metrics, ctx.details)
        return f"""{summary_card}
**Project:** `{project_name}` ({ctx.repo_full_name or '-'})
**Run ID:** `{run_id}` (status: `{run_status}`)
**Recent success rate (last 30 runs):** {success_rate * 100:.1f}%

"""
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to build Self-Healing Summary: {e}", exc_info=True)
        return None


def _build_report_section(ctx: PRCommentContext) -> str | None:
    if ctx.markdown_report:
        return format_markdown_report_block(ctx.markdown_report)
    if ctx.run is None:
        return None
    try:
        run_id = getattr(ctx.run, "run_id", None)
        if not run_id:
            return None
        content = load_run_markdown(run_id)
        return format_markdown_report_block(content) if content else None
    except (OSError, UnicodeDecodeError, ImportError) as e:
        logger.warning(f"Failed to load run markdown: {e}", exc_info=True)
        return None


def _build_links_section(ctx: PRCommentContext) -> str | None:
    if ctx.project is None or ctx.run is None:
        return None
    try:
        project_id = getattr(ctx.project, "id", 0)
        if project_id <= 0:
            return None
        run_logs_url = build_run_logs_url(project_id, ctx.run)
        proj_logs_url = build_project_logs_url(project_id)
        proj_dash_url = build_project_dashboard_url(project_id)
        return f"""---

## 📊 Observability Links

- Run logs: {run_logs_url}
- Project logs: {proj_logs_url}
- Project dashboard: {proj_dash_url}

"""
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to build Observability Links: {e}", exc_info=True)
        return None


def build_pr_comment(ctx: PRCommentContext) -> str:
    """
    PR コメント本文を組み立てる

    CR-NEXUS-039 Follow-up: 責務境界の明文化
    - この関数は Guardian/Diff/Links/MarkdownReport 等の付随セクションの組み立てに限定する
    - "## Self-Healing Result" 見出しは出さない（上位の format_pr_comment() が固定で付与する）
    """
    parts: list[str] = []

    metadata = _build_metadata_section(ctx)
    if metadata:
        parts.append(metadata)
        parts.append("")

    summary_card = _build_summary_card_section(ctx)
    if summary_card:
        parts.append(summary_card)

    parts.append("## 🔍 Guardian Review\n\n")
    parts.append(ctx.guardian_review_markdown or "_(no review content)_\n")

    if ctx.change_summary:
        parts.append("\n---\n\n## ✨ Change Summary (AI-generated)\n\n")
        parts.append(ctx.change_summary)
        parts.append("\n")

    if ctx.diff_summary:
        parts.append("\n---\n\n")
        if isinstance(ctx.diff_summary, dict):
            parts.append(format_diff_summary_block(file_summaries=ctx.diff_summary))
        else:
            parts.append(format_diff_summary_block(summary_text=ctx.diff_summary))
        parts.append("\n")

    if ctx.semantic_diffs:
        parts.append("\n---\n\n## 🧠 Semantic Diff\n\n")
        parts.append(format_semantic_diff_block(ctx.semantic_diffs))
        parts.append("\n")

    report = _build_report_section(ctx)
    if report:
        parts.append("\n---\n\n")
        parts.append(report)
        parts.append("\n")

    links = _build_links_section(ctx)
    if links:
        parts.append(links)

    return "\n".join(parts)
