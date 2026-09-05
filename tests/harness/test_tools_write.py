"""Task 17: 書く系2道具（write_file / edit_file）

round7修正条項: edit_fileの複数マッチ挙動 — 0件=not_found・1件=実行・
2件以上=ambiguous(match_count返却・実行せず・LLMに明示)

Task 11読む系と同一の安全規約を適用（plan雛形からの変更点・write.py docstring記録）:
- deny_paths対応（harness C案束縛の自動供給対象にする・書込経路のfail-open防止）
- 1MB上限（too_large ToolResult・read側MAX_BYTESと対称）
- 非UTF-8ファイルは書き戻しで破壊しない（not_utf8）
"""
from __future__ import annotations

from pathlib import Path

from nexuscore.harness.tools import ToolResult
from nexuscore.harness.tools.write import edit_file, write_file

# --- write_file ---

def test_write_file_creates_with_parent_dirs(tmp_path: Path) -> None:
    p = tmp_path / "sub" / "new.txt"
    out = write_file(str(p), "hello")
    assert p.read_text(encoding="utf-8") == "hello"
    assert isinstance(out, str) and "5 chars" in out


def test_write_file_overwrites_existing(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("old", encoding="utf-8")
    write_file(str(p), "new content")
    assert p.read_text(encoding="utf-8") == "new content"


def test_write_file_deny_path_returns_toolresult(tmp_path: Path) -> None:
    p = tmp_path / "secret.env"
    out = write_file(str(p), "x", deny_paths=["*.env"])
    assert isinstance(out, ToolResult) and out.status == "denied_path"
    assert not p.exists()


def test_write_file_broken_deny_paths_fails_closed(tmp_path: Path) -> None:
    out = write_file(str(tmp_path / "a.txt"), "x", deny_paths="broken")
    assert isinstance(out, ToolResult) and out.status == "denied_path"


def test_write_file_too_large(tmp_path: Path) -> None:
    out = write_file(str(tmp_path / "big.txt"), "x" * (1_000_001))
    assert isinstance(out, ToolResult) and out.status == "too_large"
    assert out.allowed_max == 1_000_000


# --- edit_file ---

def test_edit_file_replaces_single_match(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("AAA", encoding="utf-8")
    out = edit_file(str(p), "AAA", "BBB")
    assert isinstance(out, str)
    assert p.read_text(encoding="utf-8") == "BBB"


def test_edit_file_not_found(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("AAA", encoding="utf-8")
    out = edit_file(str(p), "ZZZ", "BBB")
    assert isinstance(out, ToolResult) and out.status == "not_found"
    assert p.read_text(encoding="utf-8") == "AAA"  # 未変更


def test_edit_file_ambiguous_does_not_touch(tmp_path: Path) -> None:
    """round7修正条項: 2件以上は実行せずmatch_countをLLMへ明示"""
    p = tmp_path / "x.txt"
    p.write_text("AAA AAA", encoding="utf-8")
    out = edit_file(str(p), "AAA", "B")
    assert isinstance(out, ToolResult) and out.status == "ambiguous"
    assert out.match_count == 2
    assert p.read_text(encoding="utf-8") == "AAA AAA"  # 実行せず


def test_edit_file_empty_old_is_invalid(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("AAA", encoding="utf-8")
    out = edit_file(str(p), "", "B")
    assert isinstance(out, ToolResult) and out.status == "invalid_argument"
    assert p.read_text(encoding="utf-8") == "AAA"


def test_edit_file_non_utf8_not_corrupted(tmp_path: Path) -> None:
    """非UTF-8（バイナリ混在）をerrors=replaceで読んで書き戻さない"""
    p = tmp_path / "x.bin"
    p.write_bytes(b"\xff\xfe\x00binary")
    out = edit_file(str(p), "binary", "text")
    assert isinstance(out, ToolResult) and out.status == "not_utf8"
    assert p.read_bytes() == b"\xff\xfe\x00binary"  # 原形保持


def test_edit_file_too_large(tmp_path: Path) -> None:
    p = tmp_path / "big.txt"
    p.write_text("x" * 1_000_001, encoding="utf-8")
    out = edit_file(str(p), "x", "y")
    assert isinstance(out, ToolResult) and out.status == "too_large"


def test_edit_file_deny_path(tmp_path: Path) -> None:
    p = tmp_path / "locked.md"
    p.write_text("AAA", encoding="utf-8")
    out = edit_file(str(p), "AAA", "B", deny_paths=["locked.*"])
    assert isinstance(out, ToolResult) and out.status == "denied_path"
    assert p.read_text(encoding="utf-8") == "AAA"


# --- 3機MLR採用分のテスト（2026-09-06） ---

def test_edit_file_missing_returns_not_found(tmp_path: Path) -> None:
    """MLR採用: 生FileNotFoundErrorでなくnot_found ToolResult（2機独立一致）"""
    out = edit_file(str(tmp_path / "missing.txt"), "AAA", "BBB")
    assert isinstance(out, ToolResult) and out.status == "not_found"


def test_edit_file_old_equals_new_invalid(tmp_path: Path) -> None:
    """MLR採用: no-op書込（mtime/監査汚染）をinvalid_argumentで拒否"""
    p = tmp_path / "x.txt"
    p.write_text("AAA", encoding="utf-8")
    mtime = p.stat().st_mtime_ns
    out = edit_file(str(p), "AAA", "AAA")
    assert isinstance(out, ToolResult) and out.status == "invalid_argument"
    assert p.stat().st_mtime_ns == mtime  # 書込不発


def test_edit_file_old_in_new_single_match(tmp_path: Path) -> None:
    """MLR採用: old⊂new（膨張置換）の1件マッチは正常実行"""
    p = tmp_path / "x.txt"
    p.write_text("A", encoding="utf-8")
    out = edit_file(str(p), "A", "AAAB")
    assert isinstance(out, str)
    assert p.read_text(encoding="utf-8") == "AAAB"


def test_edit_file_expansion_over_cap(tmp_path: Path) -> None:
    """MLR採用: 置換後サイズが1MB突破する置換はtoo_largeで不実行"""
    p = tmp_path / "big.txt"
    p.write_text("A" + "x" * 999_999, encoding="utf-8")  # ちょうど1MB
    out = edit_file(str(p), "A", "xxx")
    assert isinstance(out, ToolResult) and out.status == "too_large"
    assert p.read_text(encoding="utf-8").startswith("A")  # 未変更


def test_write_file_symlink_refused(tmp_path: Path) -> None:
    """MLR採用: symlink対象への書込は拒否（機密迂回の単純攻撃遮断）"""
    real = tmp_path / "real.txt"
    real.write_text("keep", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    out = write_file(str(link), "overwrite")
    assert isinstance(out, ToolResult) and out.status == "symlink_refused"
    assert real.read_text(encoding="utf-8") == "keep"  # 実体は無傷


def test_edit_file_symlink_refused(tmp_path: Path) -> None:
    link = tmp_path / "link.md"
    real = tmp_path / "real.md"
    real.write_text("AAA", encoding="utf-8")
    link.symlink_to(real)
    out = edit_file(str(link), "AAA", "B")
    assert isinstance(out, ToolResult) and out.status == "symlink_refused"
    assert real.read_text(encoding="utf-8") == "AAA"


def test_atomic_write_leaves_no_temp_files(tmp_path: Path) -> None:
    """MLR採用（原子書込）: 成功後にtmp残骸を残さない"""
    p = tmp_path / "x.txt"
    write_file(str(p), "hello")
    edit_file(str(p), "hello", "world")
    leftovers = [q for q in tmp_path.iterdir() if q.name != "x.txt"]
    assert leftovers == []


def test_edit_file_ambiguous_three_matches(tmp_path: Path) -> None:
    """MLR採用: 3件以上でもambiguous・match_count正確"""
    p = tmp_path / "x.txt"
    p.write_text("A A A A", encoding="utf-8")
    out = edit_file(str(p), "A", "B")
    assert isinstance(out, ToolResult) and out.status == "ambiguous"
    assert out.match_count == 4
