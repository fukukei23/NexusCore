"""
pr_comments.py

GitHub PR コメントを組み立てるユーティリティ。
"""

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
    # ステータスに応じた絵文字
    status_emoji = {
        "fixed": "✅",
        "not_fixed": "⚠️",
        "no_issues": "ℹ️",
        "blocked": "🚫",
        "error": "❌",
    }
    emoji = status_emoji.get(result_status, "❓")

    # ステータス表示用のテキスト
    status_display = result_status.upper().replace("_", " ")

    # パッチ情報の計算
    patch_line_count = 0
    affected_files = 0
    if patch_str:
        patch_line_count, affected_files = summarize_patch(patch_str)

    # テーブル行の組み立て
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

    # パッチ情報があれば追加
    if patch_str:
        lines.append(f"| Patch | {patch_line_count} lines / {affected_files} files |")
    else:
        lines.append("| Patch | N/A |")

    # 過去30回の成功率
    if total_count_30 > 0:
        lines.append(
            f"| Last 30 Runs | {success_rate_30:.1f}% ({success_count_30} / {total_count_30}) |"
        )
    else:
        lines.append("| Last 30 Runs | N/A (insufficient data) |")

    lines.append("")
    lines.append("**Notes**")
    lines.append("- This report is generated automatically by NexusCore Self-Healing.")
    lines.append("")

    # サマリーがあれば追加
    if summary:
        lines.append("**Summary**")
        lines.append(f"{summary}")
        lines.append("")

    # Guardian のレビューがあれば追加
    if guardian_status or guardian_comment:
        lines.append("### 🔍 Guardian Review")
        if guardian_status:
            lines.append(f"**Status**: `{guardian_status}`")
        if guardian_comment:
            lines.append(f"**Comment**: {guardian_comment}")
        lines.append("")

    # ブロックされたテストファイルがあれば追加
    if blocked_test_paths:
        lines.append("### 🚫 Blocked Test Files")
        lines.append("The following test files were blocked from modification:")
        for path in blocked_test_paths:
            lines.append(f"- `{path}`")
        lines.append("")

    # パッチプレビューがあれば追加
    if patch_str:
        lines.append("<details>")
        lines.append("<summary>Patch Preview</summary>")
        lines.append("")
        lines.append("```diff")
        # 長すぎる場合は切り詰める（最初の1000行程度）
        patch_lines = patch_str.splitlines()
        if len(patch_lines) > 1000:
            lines.extend(patch_lines[:1000])
            lines.append("...")
            lines.append(f"(truncated: {len(patch_lines)} total lines)")
        else:
            lines.extend(patch_lines)
        lines.append("```")
        lines.append("</details>")

    return "\n".join(lines)
