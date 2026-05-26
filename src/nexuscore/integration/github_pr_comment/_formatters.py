from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_run_markdown(run_id: str) -> str:
    """
    docs/run_reports/<run_id>.md を読み込み文字列で返す。
    ファイルが存在しない場合は空文字を返す。
    """
    try:
        from nexuscore.integration.run_report_generator import get_markdown_report_path

        report_path = get_markdown_report_path(run_id)
        if report_path.exists():
            return report_path.read_text(encoding="utf-8")
        else:
            logger.debug(f"Run report not found: {report_path}")
            return ""
    except (OSError, UnicodeDecodeError, ImportError, RuntimeError) as e:
        logger.warning(f"Failed to load run markdown: {e}", exc_info=True)
        return ""


def format_markdown_report_block(md_text: str) -> str:
    """Markdown の <details><summary>Run Report</summary>...</details> を生成する。"""
    if not md_text.strip():
        return ""

    return f"""<details>
<summary>📄 Run Report (Markdown)</summary>

{md_text}

</details>
"""


def render_summary_card(
    metrics: dict[str, Any],
    details: dict[str, Any] | None = None,
) -> str:
    """
    実行メトリクスをカード形式（Markdown テーブル）でレンダリングする。
    """
    rows: list[str] = []

    execution_ms = details.get("execution_ms") if details else None
    retry_count = details.get("retry_count", 0) if details else 0
    model_name = details.get("model") if details else None
    token_usage = details.get("token_usage") if details else None
    cost_usd = details.get("cost_usd") if details else None
    files_changed = details.get("files_changed") if details else None
    last_error_class = details.get("last_error_class") if details else None

    if model_name:
        model_display = model_name
    elif metrics.get("model_call_counts"):
        first_model = list(metrics["model_call_counts"].keys())[0]
        model_display = first_model
    else:
        model_display = "N/A"

    if execution_ms is not None:
        if execution_ms < 1000:
            exec_time_display = f"{execution_ms:.0f}ms"
        elif execution_ms < 60000:
            exec_time_display = f"{execution_ms / 1000:.1f}s"
        else:
            exec_time_display = f"{execution_ms / 60000:.1f}m"
    else:
        exec_time_display = metrics.get("duration_str", "N/A")

    if cost_usd is not None:
        cost_display = f"${cost_usd:.4f} USD"
    else:
        cost_jpy = metrics.get("estimated_cost_jpy", 0.0)
        if cost_jpy > 0:
            cost_display = f"~{cost_jpy:.2f} JPY"
        else:
            cost_display = "N/A"

    if files_changed is not None:
        files_display = str(files_changed)
    else:
        files_display = str(metrics.get("patch_files_count", 0))

    rows.append(f"| Model | {model_display} |")
    rows.append(f"| Exec Time | {exec_time_display} |")
    if retry_count > 0:
        rows.append(f"| Retry | {retry_count} |")
    rows.append(f"| Files Changed | {files_display} |")
    if token_usage:
        rows.append(f"| Token Usage | {token_usage} |")
    rows.append(f"| Cost | {cost_display} |")
    if last_error_class and retry_count > 0:
        rows.append(f"| Last Error | {last_error_class} |")

    return f"""## 🤖 Self-Healing Summary

| Metric | Value |
|--------|-------|
{chr(10).join(rows)}

"""


def format_diff_summary_block(
    summary_text: str | None = None,
    file_summaries: dict[str, str] | None = None,
) -> str:
    """Before/After 差分の AI 要約を <details> に収める。"""
    if file_summaries:
        parts: list[str] = []
        parts.append("## 🔍 AI Diff Summary (Multiple Files)\n")
        for file_path, summary in file_summaries.items():
            if summary and summary.strip():
                parts.append(
                    f"""<details>
<summary>{file_path}</summary>

{summary}

</details>
"""
                )
        return "\n".join(parts) if parts else ""

    if not summary_text or not summary_text.strip():
        return ""

    return f"""## 🤖 AI Diff Summary (Before → After)

<details>
<summary>差分要約（5行）</summary>

{summary_text}

</details>
"""


def format_semantic_diff_block(
    semantic_diffs: dict[str, dict[str, Any]] | None,
) -> str:
    """semantic_diffs を Markdown (<details>) でレンダリングする。"""
    if not semantic_diffs:
        return ""

    blocks: list[str] = []

    for rel_path, data in semantic_diffs.items():
        functions = data.get("functions") or []
        behavior_hints = data.get("behavior_hints") or []

        table_lines = [
            "| Function | Kind | Before | After |",
            "|----------|------|--------|-------|",
        ]

        for f in functions:
            name = f.get("name", "")
            kind = f.get("kind", "")
            sig_before = f.get("signature_before") or ""
            sig_after = f.get("signature_after") or ""

            if len(sig_before) > 50:
                sig_before = sig_before[:47] + "..."
            if len(sig_after) > 50:
                sig_after = sig_after[:47] + "..."

            table_lines.append(f"| `{name}` | {kind} | `{sig_before}` | `{sig_after}` |")

        behavior_lines = []
        for hint in behavior_hints:
            desc = hint.get("description") or ""
            risk = hint.get("risk_level") or "medium"
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "🟡")
            behavior_lines.append(f"- {risk_emoji} ({risk}) {desc}")

        block = f"""<details>

<summary>🧠 Semantic Diff: `{rel_path}`</summary>

### Functions

{chr(10).join(table_lines) if len(table_lines) > 2 else "_(no function changes)_"}

### Behavior Hints

{chr(10).join(behavior_lines) if behavior_lines else "_(no behavior hints)_"}

</details>"""
        blocks.append(block)

    return "\n\n".join(blocks)
