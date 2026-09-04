"""Task 11: 読む系toolsパッケージ（spec §6 Phase 1）

ToolResultを先に定義してからread.pyをimportする（read.pyが本パッケージから
ToolResultをimportするため・定義→importの順序が重要）。Task 17/20 の
not_found / ambiguous / would_exceed_limit も本型に統一予定。
"""
from dataclasses import dataclass


@dataclass
class ToolResult:
    """道具が通常の戻り値を返せなかった時の状態通知（round7修正条項）

    read_file の too_large（Task 11）で初出・statusは確定値のみ（YAGNI）。
    "too_large" 通知後も処理継続（LLMへ状態を返して判断させる・fail-soft）。
    """

    status: str
    size: int | None = None
    allowed_max: int | None = None


from nexuscore.harness.tools.read import list_dir, read_file, search_text

__all__ = ["ToolResult", "list_dir", "read_file", "search_text"]
