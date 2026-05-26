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


def build_pr_comment(ctx: PRCommentContext) -> str:
    """
    PR コメント本文を組み立てる

    CR-NEXUS-039 Follow-up: 責務境界の明文化
    - この関数は Guardian/Diff/Links/MarkdownReport 等の付随セクションの組み立てに限定する
    - "## Self-Healing Result" 見出しは出さない（上位の format_pr_comment() が固定で付与する）
    """
    parts: list[str] = []

    # === CR-E3: Self-Healing メタ情報ブロック ===
    if ctx.run is not None and ctx.project is not None:
        try:
            metrics = _collect_run_metrics(ctx.run)

            project_id = 0
            if hasattr(ctx.project, "id"):
                project_id = ctx.project.id

            success_rate = None
            if project_id > 0:
                success_rate = _compute_recent_success_rate(project_id, limit=30)

            run_id = "unknown"
            if hasattr(ctx.run, "run_id"):
                run_id = ctx.run.run_id

            start_time = metrics.get("start_time")
            end_time = metrics.get("end_time")
            duration_seconds = metrics.get("duration_seconds", 0.0)

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
                    aux_models = [model for model, _ in sorted_models[1:]]

            changed_files = metrics.get("patch_files_count", 0)
            added_lines = metrics.get("added_lines", 0)
            removed_lines = metrics.get("removed_lines", 0)

            metadata_block = format_metadata_block(
                run_id=run_id,
                pr_number=ctx.pr_number,
                commit_sha=ctx.commit_sha,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                primary_model=primary_model,
                aux_models=aux_models,
                changed_files=changed_files,
                added_lines=added_lines,
                removed_lines=removed_lines,
                success_rate_last_n=success_rate,
                recent_runs_window=30,
            )
            parts.append(metadata_block)
            parts.append("")

        except Exception as e:  # noqa: BLE001 — メトリクス収集全体のフォールバック
            logger.warning(f"Failed to build Self-Healing metadata block: {e}", exc_info=True)

    # === E-5: Self-Healing Summary (カード形式) ===
    if ctx.run is not None and ctx.project is not None:
        try:
            metrics = _collect_run_metrics(ctx.run)

            project_id = 0
            if hasattr(ctx.project, "id"):
                project_id = ctx.project.id

            success_rate = 0.0
            if project_id > 0:
                success_rate = _compute_recent_success_rate(project_id, limit=30)

            project_name = "Unknown"
            if hasattr(ctx.project, "name"):
                project_name = ctx.project.name

            run_id = "unknown"
            run_status = "UNKNOWN"
            if hasattr(ctx.run, "run_id"):
                run_id = ctx.run.run_id
            if hasattr(ctx.run, "status"):
                run_status = ctx.run.status

            details_for_card = ctx.details

            summary_card = render_summary_card(metrics, details_for_card)

            additional_info = f"""
**Project:** `{project_name}` ({ctx.repo_full_name or '-'})
**Run ID:** `{run_id}` (status: `{run_status}`)
**Recent success rate (last 30 runs):** {success_rate * 100:.1f}%

"""
            parts.append(summary_card)
            parts.append(additional_info)
        except Exception as e:  # noqa: BLE001 — サマリーカード生成全体のフォールバック
            logger.warning(f"Failed to build Self-Healing Summary: {e}", exc_info=True)

    # === Guardian Review ===
    parts.append("## 🔍 Guardian Review\n\n")
    parts.append(ctx.guardian_review_markdown or "_(no review content)_\n")

    # === Change Summary (AI 要約) (B-3) ===
    if ctx.change_summary:
        parts.append("\n---\n\n")
        parts.append("## ✨ Change Summary (AI-generated)\n\n")
        parts.append(ctx.change_summary)
        parts.append("\n")

    # === E-4/E-5: AI Diff Summary (Before → After) ===
    if ctx.diff_summary:
        parts.append("\n---\n\n")
        if isinstance(ctx.diff_summary, dict):
            parts.append(format_diff_summary_block(file_summaries=ctx.diff_summary))
        else:
            parts.append(format_diff_summary_block(summary_text=ctx.diff_summary))
        parts.append("\n")

    # === Semantic Diff ===
    if ctx.semantic_diffs:
        parts.append("\n---\n\n")
        parts.append("## 🧠 Semantic Diff\n\n")
        parts.append(format_semantic_diff_block(ctx.semantic_diffs))
        parts.append("\n")

    # === E-3: Run Markdown Report ===
    if ctx.markdown_report:
        parts.append("\n---\n\n")
        parts.append(format_markdown_report_block(ctx.markdown_report))
        parts.append("\n")
    elif ctx.run is not None:
        try:
            if hasattr(ctx.run, "run_id"):
                run_id = ctx.run.run_id
                markdown_content = load_run_markdown(run_id)
                if markdown_content:
                    parts.append("\n---\n\n")
                    parts.append(format_markdown_report_block(markdown_content))
                    parts.append("\n")
        except (OSError, UnicodeDecodeError, ImportError) as e:
            logger.warning(f"Failed to load run markdown: {e}", exc_info=True)

    # === Observability Links (B-2) ===
    if ctx.project is not None and ctx.run is not None:
        try:
            project_id = 0
            if hasattr(ctx.project, "id"):
                project_id = ctx.project.id

            if project_id > 0:
                run_logs_url = build_run_logs_url(project_id, ctx.run)
                proj_logs_url = build_project_logs_url(project_id)
                proj_dash_url = build_project_dashboard_url(project_id)

                links_md = f"""---

## 📊 Observability Links

- Run logs: {run_logs_url}
- Project logs: {proj_logs_url}
- Project dashboard: {proj_dash_url}

"""
                parts.append(links_md)
        except Exception as e:  # noqa: BLE001 — URL構築全体のフォールバック
            logger.warning(f"Failed to build Observability Links: {e}", exc_info=True)

    return "\n".join(parts)
