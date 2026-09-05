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

3機MLR採用分（2026-09-06・25+2+10件から採用7・review_log参照）:
- **原子書込**（temp作成→os.replace・書込途中死で元ファイル破壊を防ぐ・OR#9）
- **edit対象ファイル不在はnot_found**（生FileNotFoundErrorをLLMへ出さない・
  Gemini#2+OR#3の2機独立一致）
- **置換後サイズの上限検査**（old→new膨張で1MB突破を防ぐ・Gemini#1）
- **old==newはinvalid_argument**（no-op書込でmtime/監査を汚さない・MiniMax#1/7）
- **symlink対象の書込拒否**（LLM指定パスがsymlinkで機密ファイルへ迂回する
  単純攻撃を遮断・MiniMax TOCTOU指摘の軽量対策）
- **is_deniedのpublic化**（tools/__init__.pyへ共通移動・MiniMax private import指摘）
- **上限はbytes単位**の明記（read側MAX_BYTESと同じ意味・MiniMax#5）

既知制限（docstring明記・将来対処）:
- TOCTOU競合の完全排除（O_NOFOLLOW）は未実装・symlink事前チェックは軽量対策
- 親ディレクトリがsymlinkの場合の検査なし
- `..` を含むパストラバーサルはdeny_paths/askフロー（Task 18）とPhase 3 policyで対処
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from nexuscore.harness.tools import ToolResult, is_denied
from nexuscore.harness.tools.read import MAX_BYTES

MAX_WRITE_BYTES = MAX_BYTES  # 1MB（読む系と対称・bytes単位）


def _atomic_write_text(p: Path, text: str) -> None:
    """同dir一時ファイルへ書いてos.replace（書込途中死でも元ファイルを壊さない）"""
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=p.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _check_writable(path: str, deny_paths: list[str] | None) -> tuple[Path, ToolResult | None]:
    """write/edit共通の事前検査（deny_paths・symlink）」

    戻り値は (Path, None) または (Path, ToolResult)。
    """
    if is_denied(path, deny_paths):
        return Path(path), ToolResult(status="denied_path", path=path)
    p = Path(path)
    if p.is_symlink():
        # LLM指定パスがsymlink経由で機密ファイルへ迂回する単純攻撃を遮断
        # （TOCTOU競合までは閉じない・既知制限）
        return p, ToolResult(status="symlink_refused", path=str(p))
    return p, None


def write_file(path: str, content: str,
               deny_paths: list[str] | None = None) -> str | ToolResult:
    """テキストファイルを書き込む（親dir作成・1MB上限・原子書込・deny_paths対応）"""
    p, err = _check_writable(path, deny_paths)
    if err is not None:
        return err
    try:
        data = content.encode("utf-8")
    except UnicodeEncodeError:
        return ToolResult(status="invalid_argument", path=path)
    if len(data) > MAX_WRITE_BYTES:
        return ToolResult(status="too_large", size=len(data),
                          allowed_max=MAX_WRITE_BYTES)
    p.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(p, content)
    return f"wrote {len(content)} chars to {p}"


def edit_file(path: str, old: str, new: str,
              deny_paths: list[str] | None = None) -> str | ToolResult:
    """ファイル内のold→newを置換する（1件マッチのみ実行・複数はambiguous）

    複数マッチ時に機械的に1箇所へ決め打ちせず、LLMへmatch_countを返して
    判断させる（round7修正条項・誤書込防止）。
    """
    p, err = _check_writable(path, deny_paths)
    if err is not None:
        return err
    if not p.is_file():
        return ToolResult(status="not_found", path=str(p))
    if p.stat().st_size > MAX_WRITE_BYTES:
        return ToolResult(status="too_large", size=p.stat().st_size,
                          allowed_max=MAX_WRITE_BYTES)
    try:
        txt = p.read_text(encoding="utf-8")  # strict・非UTF-8は書き戻さない
    except UnicodeDecodeError:
        return ToolResult(status="not_utf8", path=str(p))
    if not old:
        return ToolResult(status="invalid_argument", path=str(p))
    if old == new:
        # no-op書込を避ける（mtime更新・監査汚染防止・MLR採用）
        return ToolResult(status="invalid_argument", path=str(p))
    count = txt.count(old)
    if count == 0:
        return ToolResult(status="not_found", path=str(p))
    if count > 1:
        return ToolResult(status="ambiguous", match_count=count, path=str(p))
    new_txt = txt.replace(old, new, 1)
    if len(new_txt.encode("utf-8")) > MAX_WRITE_BYTES:
        # old→newの膨張で上限突破する置換は実行しない（MLR採用・Gemini#1）
        return ToolResult(status="too_large", size=len(new_txt.encode("utf-8")),
                          allowed_max=MAX_WRITE_BYTES)
    _atomic_write_text(p, new_txt)
    return f"edited {p}"
