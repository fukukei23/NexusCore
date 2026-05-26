from __future__ import annotations

def summarize_patch(patch_str: str) -> tuple[int, int]:
    """
    unified diff から行数とファイル数を計算する。

    Args:
        patch_str: unified diff 形式の文字列

    Returns:
        (patch_line_count, affected_files)
        - patch_line_count: "+" または "-" で始まる行の数（ファイルヘッダー除く）
        - affected_files: "+++ b/path/to/file.py" 形式のファイル数のユニーク数
    """
    lines = patch_str.splitlines()
    patch_line_count = 0
    affected_files = set()

    for line in lines:
        # ファイルヘッダーの検出（+++ b/path/to/file.py）
        if line.startswith("+++ b/"):
            # "+++ b/path/to/file.py" から "path/to/file.py" を抽出
            file_path = line[6:].strip()
            if file_path:
                affected_files.add(file_path)
        # パッチ行のカウント（+ または - で始まる行）
        elif line.startswith("+") or line.startswith("-"):
            # "+++", "---" などのファイルヘッダーは除外
            if not line.startswith("+++") and not line.startswith("---"):
                patch_line_count += 1

    return patch_line_count, len(affected_files)


_STATUS_EMOJI = {
    "fixed": "✅",
    "not_fixed": "⚠️",
    "no_issues": "ℹ️",
    "blocked": "🚫",
    "error": "❌",
}


def _build_main_table(
    run_id: str,
    result_status: str,
    started_at: str,
    finished_at: str,
    duration_seconds: float,
    model_name: str,
    patch_str: str,
    success_rate_30: float,
    success_count_30: int,
    total_count_30: int,
) -> list[str]:
    emoji = _STATUS_EMOJI.get(result_status, "❓")
    status_display = result_status.upper().replace("_", " ")

    patch_line_count = 0
    affected_files = 0
    if patch_str:
        patch_line_count, affected_files = summarize_patch(patch_str)

    lines = [
        "### 🤖 NexusCore Self-Healing Report",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| Run ID | `{run_id}` |",
        f"| Result | {emoji} {status_display} |",
        f"| Execution Time | {duration_seconds:.2f}s (`{started_at}` → `{finished_at}`) |",
        f"| Model | `{model_name}` |",
    ]

    if patch_str:
        lines.append(f"| Patch | {patch_line_count} lines / {affected_files} files |")
    else:
        lines.append("| Patch | N/A |")

    if total_count_30 > 0:
        lines.append(f"| Last 30 Runs | {success_rate_30:.1f}% ({success_count_30} / {total_count_30}) |")
    else:
        lines.append("| Last 30 Runs | N/A (insufficient data) |")

    lines.append("")
    lines.append("**Notes**")
    lines.append("- This report is generated automatically by NexusCore Self-Healing.")
    lines.append("")
    return lines


def _build_patch_preview(patch_str: str) -> list[str]:
    lines = ["<details>", "<summary>Patch Preview</summary>", "", "```diff"]
    patch_lines = patch_str.splitlines()
    if len(patch_lines) > 1000:
        lines.extend(patch_lines[:1000])
        lines.append("...")
        lines.append(f"(truncated: {len(patch_lines)} total lines)")
    else:
        lines.extend(patch_lines)
    lines.append("```")
    lines.append("</details>")
    return lines


def build_self_healing_pr_comment(
    run_id: str,
    result_status: str,  # "fixed" / "not_fixed" / "no_issues" / "blocked" / "error"
    started_at: str,  # ISO8601 文字列
    finished_at: str,  # ISO8601 文字列
    duration_seconds: float,
    model_name: str,
    patch_str: str = "",
    success_rate_30: float = 0.0,
    success_count_30: int = 0,
    total_count_30: int = 0,
    summary: str = "",
    guardian_status: str = "",
    guardian_comment: str = "",
    blocked_test_paths: list[str] | None = None,
) -> str:
    """
    Self-Healing 実行結果を GitHub PR コメント形式の Markdown に整形する。

    Args:
        run_id: 実行ID
        result_status: 結果ステータス
        started_at: 開始時刻（ISO8601）
        finished_at: 終了時刻（ISO8601）
        duration_seconds: 実行時間（秒）
        model_name: 使用モデル名
        patch_str: unified diff 文字列（オプション）
        success_rate_30: 過去30回の成功率（%）
        success_count_30: 過去30回の成功数
        total_count_30: 過去30回の総数
        summary: サマリー
        guardian_status: Guardian のステータス（オプション）
        guardian_comment: Guardian のコメント（オプション）
        blocked_test_paths: ブロックされたテストファイルパス（オプション）

    Returns:
        Markdown 形式の PR コメント本文
    """
    lines = _build_main_table(
        run_id, result_status, started_at, finished_at,
        duration_seconds, model_name, patch_str,
        success_rate_30, success_count_30, total_count_30,
    )

    if summary:
        lines.extend(["**Summary**", f"{summary}", ""])

    if guardian_status or guardian_comment:
        lines.append("### 🔍 Guardian Review")
        if guardian_status:
            lines.append(f"**Status**: `{guardian_status}`")
        if guardian_comment:
            lines.append(f"**Comment**: {guardian_comment}")
        lines.append("")

    if blocked_test_paths:
        lines.append("### 🚫 Blocked Test Files")
        lines.append("The following test files were blocked from modification:")
        for path in blocked_test_paths:
            lines.append(f"- `{path}`")
        lines.append("")

    if patch_str:
        lines.extend(_build_patch_preview(patch_str))

    return "\n".join(lines)
