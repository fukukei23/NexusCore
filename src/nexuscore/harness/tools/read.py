"""Task 11: 読む系3道具（read_file / list_dir / search_text）

round7修正条項を反映:
- read_file: 1MB超過時はToolResult(status="too_large")通知（fail-soft継続）
- list_dir: deny_pathsに一致するエントリを返す前に隠蔽（LLMに見せない）
- search_text: MLR採用分でdeny_pathsフィルタ+サイズ/件数上限を追加
  （list_dirで隠したファイルの中身が検索で漏れる構造的穴対策・
   MiniMax+Geminiが独立にcritical指摘・2026-09-04 3機レビュー）

deny_paths照合はglob×normpath（full path+ファイル名単体）。
**供給経路の注意**: 本関数群はdeny_pathsを引数で受け取るのみで自身ではpolicyを
読まない（policy読取はゲート/ハーネス側責務・plan §4）。ハーネス側（Task 14）が
tool_registry構築時にpolicyのdeny_pathsを束縛して渡すこと（バックログ起票済み・
未束縛のままLLM引数だけ渡すとdeny_paths=None=無フィルタのfail-openになる）。
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from nexuscore.harness.tools import ToolResult

MAX_BYTES = 1_000_000  # 1MB cap（暴走防止）
MAX_HITS = 100  # search_textのヒット件数上限（LLMコンテキスト保護）


def _is_denied(path: str, deny_paths: list[str] | None) -> bool:
    """deny_paths照合（glob×normpath・full pathと名前の両方）

    非list型は破損扱いで常にTrue（全隠蔽fail-closed・tool_gate deny-all相当）。
    名前単体マッチはtool_gateより広い（=隠しすぎる方向・意図的）。
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


def read_file(path: str) -> str | ToolResult:
    """1MB超過時はtoo_large通知（plan本文のValueErrorを修正条項が上書き）"""
    p = Path(path)
    size = p.stat().st_size
    if size > MAX_BYTES:
        return ToolResult(status="too_large", size=size, allowed_max=MAX_BYTES)
    return p.read_text(encoding="utf-8", errors="replace")


def list_dir(path: str, deny_paths: list[str] | None = None) -> list[dict]:
    """deny_paths一致エントリを隠蔽してから返す（修正条項②）"""
    entries = []
    for e in Path(path).iterdir():
        try:
            size = e.stat().st_size
        except OSError:
            continue  # 壊れたsymlink等・1エントリで全体が死なない
        if _is_denied(str(e), deny_paths):
            continue
        entries.append({"name": e.name, "is_dir": e.is_dir(), "size": size})
    return entries


def search_text(
    query: str,
    root: str,
    patterns: list[str] | None = None,
    deny_paths: list[str] | None = None,
) -> list[dict]:
    """queryを含む行を{path, line, snippet}で返す

    MLR採用分: deny_paths一致ファイルは検索対象から除外・MAX_BYTES超過ファイルは
    スキップ・ヒットはMAX_HITS件で打ち止め。deny_pathsが非list型なら全除外
    （fail-closed・list_dirと対称）。
    """
    if patterns is None:
        patterns = ["*.md", "*.txt"]
    if deny_paths is not None and not isinstance(deny_paths, list):
        return []  # 破損扱いで全除外
    hits: list[dict] = []
    for pat in patterns:
        for p in Path(root).rglob(pat):
            if _is_denied(str(p), deny_paths):
                continue
            try:
                if not p.is_file():
                    continue  # rglobがディレクトリにマッチした場合（round2採用）
                if p.stat().st_size > MAX_BYTES:
                    continue  # 巨大ファイルスキップ（メモリ暴走防止）
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue  # 消えたファイル・権限等（1ファイルで全体が死なない）
            for i, line in enumerate(lines, 1):
                if query in line:
                    hits.append({"path": str(p), "line": i, "snippet": line[:200]})
                    if len(hits) >= MAX_HITS:
                        return hits
    return hits
