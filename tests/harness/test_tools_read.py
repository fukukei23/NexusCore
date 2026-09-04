"""Task 11: read tools 3種（read_file/list_dir/search_text）

round7修正条項: ①read_file上限超過時はToolResult(status="too_large")を返す
②list_dirはdeny_pathsを事前フィルタしてから返す（LLMに見せない）
"""
from nexuscore.harness.tools import ToolResult, list_dir, read_file, search_text


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
    names = [e["name"] for e in entries]
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
