"""Task 17: 書く系2道具（write_file / edit_file）— Phase 2

本モジュールの道具はPhase 2でask確認フロー（Task 18）導入後に実使用可。
それまではpolicy未登録=ゲートが全拒否（fail-closed）。

plan雛形からの変更点（実装時判断・round7修正条項の反映）:
- **edit_file複数マッチ挙動**（round7修正条項・plan本文のValueErrorを上書き）:
  0件=status="not_found"・1件=実行・2件以上=status="ambiguous"（match_count返却・
  実行せず・LLMに明示）
- **deny_paths対応**（Task 11読む系と同一規約）: harness初期化時のC案束縛
  （loop.py:110-115）がdeny_paths引数の実在を検査してpolicy値を束縛するため、
  書込経路でも引数を持たないとfail-openになる。plan雛形は引数なし=構造的穴
- **1MB上限**（読む系MAX_BYTESと対称・暴走防止）: 超過時はtoo_large ToolResult
- **非UTF-8保護**: edit_fileはstrict UTF-8で読み、失敗時not_utf8（errors=replaceで
  読んで書き戻すとバイナリを破壊するため・read_fileのreplaceは読み専用だから合法）
"""
from __future__ import annotations

from pathlib import Path

from nexuscore.harness.tools import ToolResult
from nexuscore.harness.tools.read import MAX_BYTES, _is_denied

MAX_WRITE_BYTES = MAX_BYTES  # 1MB（読む系と対称）


def write_file(path: str, content: str,
               deny_paths: list[str] | None = None) -> str | ToolResult:
    """テキストファイルを書き込む（親ディレクトリ作成・1MB上限・deny_paths対応）"""
    if _is_denied(path, deny_paths):
        return ToolResult(status="denied_path", path=path)
    data = content.encode("utf-8")
    if len(data) > MAX_WRITE_BYTES:
        return ToolResult(status="too_large", size=len(data),
                          allowed_max=MAX_WRITE_BYTES)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {p}"


def edit_file(path: str, old: str, new: str,
              deny_paths: list[str] | None = None) -> str | ToolResult:
    """ファイル内のold→newを置換する（1件マッチのみ実行・複数はambiguous）

    複数マッチ時に機械的に1箇所へ決め打ちせず、LLMへmatch_countを返して
    判断させる（round7修正条項・誤書込防止）。
    """
    if _is_denied(path, deny_paths):
        return ToolResult(status="denied_path", path=path)
    p = Path(path)
    if p.stat().st_size > MAX_WRITE_BYTES:
        return ToolResult(status="too_large", size=p.stat().st_size,
                          allowed_max=MAX_WRITE_BYTES)
    try:
        txt = p.read_text(encoding="utf-8")  # strict・非UTF-8は書き戻さない
    except UnicodeDecodeError:
        return ToolResult(status="not_utf8", path=str(p))
    if not old:
        return ToolResult(status="invalid_argument", path=str(p))
    count = txt.count(old)
    if count == 0:
        return ToolResult(status="not_found", path=str(p))
    if count > 1:
        return ToolResult(status="ambiguous", match_count=count, path=str(p))
    p.write_text(txt.replace(old, new, 1), encoding="utf-8")
    return f"edited {p}"
