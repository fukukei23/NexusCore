"""Task 11: read tools 3種（read_file/list_dir/search_text）

round7修正条項: ①read_file上限超過時はToolResult(status="too_large")を返す
②list_dirはdeny_pathsを事前フィルタしてから返す（LLMに見せない）
MLR 3機レビュー採用分: search_textにもdeny_pathsフィルタ+サイズ/件数上限・
壊れたsymlinkスキップ・順序非依存アサート
"""
from nexuscore.harness.tools import ToolResult, list_dir, read_file, search_text
from nexuscore.harness.tools import read as read_mod


def test_read_file_returns_content(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hello\n")
    assert read_file(str(f)) == "hello\n"


def test_read_file_too_large_returns_tool_result(tmp_path):
    # 修正条項①: 1MB超過時はValueErrorでなくToolResult通知
    f = tmp_path / "big.bin"
    f.write_bytes(b"a" * 1_000_001)
    r = read_file(str(f))
    assert isinstance(r, ToolResult)
    assert r.status == "too_large"
    assert r.size == 1_000_001
    assert r.allowed_max == 1_000_000


def test_list_dir_returns_entry_structure(tmp_path):
    (tmp_path / "a.txt").write_text("abc")
    (tmp_path / "sub").mkdir()
    entries = list_dir(str(tmp_path))
    by_name = {e["name"]: e for e in entries}
    assert by_name["a.txt"]["is_dir"] is False
    assert by_name["a.txt"]["size"] == 3
    assert by_name["sub"]["is_dir"] is True


def test_list_dir_filters_denied_paths(tmp_path):
    # 修正条項②: deny_paths一致エントリは返さない（LLMに見せない）
    (tmp_path / "a.txt").write_text("ok")
    (tmp_path / ".env").write_text("SECRET=1")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "k.txt").write_text("x")
    entries = list_dir(str(tmp_path), deny_paths=[".env", "*secrets*"])
    names = sorted(e["name"] for e in entries)
    assert names == ["a.txt"]


def test_list_dir_non_list_deny_paths_is_fail_closed(tmp_path):
    # deny_pathsが非list型（文字列等）は破損扱いで全隠蔽（tool_gateのdeny-all相当）
    (tmp_path / "a.txt").write_text("ok")
    assert list_dir(str(tmp_path), deny_paths="*.txt") == []


def test_search_text_finds_hits(tmp_path):
    (tmp_path / "a.md").write_text("alpha\nbeta\n")
    hits = search_text("alpha", root=str(tmp_path), patterns=["*.md"])
    assert any("alpha" in h["snippet"] for h in hits)


def test_search_text_returns_empty_when_no_match(tmp_path):
    (tmp_path / "a.md").write_text("alpha\n")
    assert search_text("zeta", root=str(tmp_path), patterns=["*.md"]) == []


def test_search_text_excludes_denied_paths(tmp_path):
    # MLR採用#1: list_dirで隠したファイルの中身が検索で漏れない
    (tmp_path / "a.md").write_text("alpha ok\n")
    (tmp_path / ".env").write_text("SECRET=1\n")
    hits = search_text(
        "SECRET", root=str(tmp_path), patterns=["*"], deny_paths=[".env"]
    )
    assert hits == []
    # deny_paths非一致の通常検索は従来どおりヒットする
    hits = search_text(
        "alpha", root=str(tmp_path), patterns=["*.md"], deny_paths=[".env"]
    )
    assert len(hits) == 1


def test_search_text_skips_oversized_files(monkeypatch, tmp_path):
    # MLR採用#2a: read_fileと同一のサイズ上限を超えるファイルはスキップ
    monkeypatch.setattr(read_mod, "MAX_BYTES", 5)
    (tmp_path / "big.md").write_text("needle needle needle\n")
    hits = search_text("needle", root=str(tmp_path), patterns=["*.md"])
    assert hits == []


def test_search_text_caps_hits(monkeypatch, tmp_path):
    # MLR採用#2b: ヒット件数上限（LLMコンテキスト保護）
    monkeypatch.setattr(read_mod, "MAX_HITS", 2)
    for i in range(3):
        (tmp_path / f"f{i}.md").write_text("needle\n")
    hits = search_text("needle", root=str(tmp_path), patterns=["*.md"])
    assert len(hits) == 2


def test_list_dir_skips_broken_symlink(tmp_path):
    # MLR採用#3: 壊れたsymlinkでクラッシュしない（スキップ）
    (tmp_path / "a.txt").write_text("ok")
    (tmp_path / "broken").symlink_to(tmp_path / "no_such_target")
    entries = list_dir(str(tmp_path))
    assert [e["name"] for e in entries] == ["a.txt"]
