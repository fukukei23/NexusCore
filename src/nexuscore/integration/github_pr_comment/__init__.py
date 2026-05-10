"""
GitHub PR comment assembly subpackage.

Re-exports all public API from the split modules for backward compatibility.
"""

from ._builder import PRCommentContext, build_pr_comment, format_metadata_block
from ._formatters import (
    format_diff_summary_block,
    format_markdown_report_block,
    format_semantic_diff_block,
    load_run_markdown,
    render_summary_card,
)
from ._metrics import (
    HAS_WEBAPP,
    _collect_run_metrics,
    _compute_recent_success_rate,
    _estimate_diff_lines,
    _estimate_diff_lines_separated,
    _format_duration,
    build_project_dashboard_url,
    build_project_logs_url,
    build_run_logs_url,
)

__all__ = [
    # Builder
    "PRCommentContext",
    "build_pr_comment",
    "format_metadata_block",
    # Formatters
    "format_diff_summary_block",
    "format_markdown_report_block",
    "format_semantic_diff_block",
    "load_run_markdown",
    "render_summary_card",
    # Metrics
    "HAS_WEBAPP",
    "_collect_run_metrics",
    "_compute_recent_success_rate",
    "_estimate_diff_lines",
    "_estimate_diff_lines_separated",
    "_format_duration",
    "build_project_dashboard_url",
    "build_project_logs_url",
    "build_run_logs_url",
]
