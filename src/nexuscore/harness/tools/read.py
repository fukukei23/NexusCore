"""Task 11: 読む系3道具（read_file / list_dir / search_text）

round7修正条項を反映:
- read_file: 1MB超過時はToolResult(status="too_large")通知（fail-soft継続）
- list_dir: deny_pathsに一致するエントリを返す前に隠蔽（LLMに見せない）
- search_text: plan本文どおり・deny_pathsフィルタは修正条項の対象外
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from nexuscore.harness.tools import ToolResult

MAX_BYTES = 1_000_000  # 1MB cap（暴走防止）

# deny_paths照合対象: 正規化full path（../ 対策・tool_gateと同一）+
# ファイル名単体（".env"等の名前指定パターンにも対応）。
# 非list型は破損扱いで全隠蔽（fail-closed・tool_gate deny-all相当）


def read_file(path: str) -> str | ToolResult:
    """1MB超過時はtoo_large通知（plan本文のValueErrorを修正条項が上書き）"""
    p = Path(path)
    size = p.stat().st_size
    if size > MAX_BYTES:
        return ToolResult(status="too_large", size=size, allowed_max=MAX_BYTES)
    return p.read_text(encoding="utf-8", errors="replace")


def list_dir(path: str, deny_paths: list[str] | None = None) -> list[dict]:
    """deny_paths一致エントリを隠蔽してから返す（修正条項②）"""
    if deny_paths is not None and not isinstance(deny_paths, list):
        return []  # 破損扱いで全隠蔽
    entries = []
    for e in Path(path).iterdir():
        norm = os.path.normpath(str(e))
        denied = any(
            fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(e.name, pat)
            for pat in deny_paths or []
        )
        if not denied:
            entries.append(
                {"name": e.name, "is_dir": e.is_dir(), "size": e.stat().st_size}
            )
    return entries


def search_text(query: str, root: str, patterns: list[str] | None = None) -> list[dict]:
    """queryを含む行を{path, line, snippet}で返す（plan本文どおり）"""
    if patterns is None:
        patterns = ["*.md", "*.txt"]
    hits = []
    for pat in patterns:
        for p in Path(root).rglob(pat):
            try:
                lines = p.read_text(errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    if query in line:
                        hits.append(
                            {"path": str(p), "line": i, "snippet": line[:200]}
                        )
            except Exception:
                continue
    return hits
