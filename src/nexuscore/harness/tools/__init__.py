"""Task 11: 読む系toolsパッケージ（spec §6 Phase 1）

ToolResultを先に定義してからread.pyをimportする（read.pyが本パッケージから
ToolResultをimportするため・定義→importの順序が重要）。Task 17/20 の
not_found / ambiguous / would_exceed_limit も本型に統一予定。
"""
import fnmatch
import os
from dataclasses import dataclass


def is_denied(path: str, deny_paths: list[str] | None) -> bool:
    """deny_paths照合（glob×normpath・full pathとファイル名単体の両方）

    Task 17 MLR採用分でread.pyの _is_denied からpublic化・共通化した
    （private importの流用は将来リファクタで壊れるため）。非list型は破損扱いで
    常にTrue（全拒否fail-closed・tool_gate deny-all相当）。
    """
    if deny_paths is None:
        return False
    if not isinstance(deny_paths, list):
        return True  # 破損扱い
    norm = os.path.normpath(path)
    return any(
        fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(os.path.basename(norm), pat)
        for pat in deny_paths
    )


@dataclass
class ToolResult:
    """道具が通常の戻り値を返せなかった時の状態通知（round7修正条項）

    read_file の too_large（Task 11）で初出・statusは確定値のみ（YAGNI）。
    "too_large" 通知後も処理継続（LLMへ状態を返して判断させる・fail-soft）。
    """

    status: str
    size: int | None = None
    allowed_max: int | None = None
    match_count: int | None = None  # Task 17 edit_file ambiguous時のマッチ数
    path: str | None = None  # Task 17 denied_path時の対象パス
    detail: str | None = None  # Task 20 exec_error時の例外文言


from nexuscore.harness.tools.read import list_dir, read_file, search_text

__all__ = ["ToolResult", "list_dir", "read_file", "search_text"]
