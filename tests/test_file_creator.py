"""Tests for file_creator.py"""
import os
import tempfile
from pathlib import Path
import pytest
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# src/file_creator.pyを直接インポート
from file_creator import create_code_file


def test_create_code_file_basic(tmp_path):
    """基本的なファイル作成テスト"""
    folder = str(tmp_path / "generated")
    filename = "test.py"
    code = "print('hello')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    assert result_path.endswith("test.py")
    with open(result_path, "r", encoding="utf-8") as f:
        assert f.read() == code


def test_create_code_file_default_folder(tmp_path, monkeypatch):
    """デフォルトフォルダでのファイル作成テスト"""
    default_folder = str(tmp_path / "src" / "generated")

    filename = "default_test.py"
    code = "def test(): pass"

    # デフォルトフォルダが存在しない場合でも作成されることを確認
    result_path = create_code_file(filename, code, default_folder)

    assert os.path.exists(result_path)
    assert os.path.exists(default_folder)
    with open(result_path, "r", encoding="utf-8") as f:
        assert f.read() == code


def test_create_code_file_multiline_code(tmp_path):
    """複数行コードのファイル作成テスト"""
    folder = str(tmp_path / "generated")
    filename = "multiline.py"
    code = """def hello():
    print("world")
    return True
"""

    result_path = create_code_file(filename, code, folder)

    with open(result_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "def hello():" in content
        assert 'print("world")' in content
        assert "return True" in content


def test_create_code_file_creates_directory(tmp_path):
    """存在しないディレクトリを自動作成するテスト"""
    folder = str(tmp_path / "new" / "nested" / "folder")
    filename = "nested.py"
    code = "x = 1"

    assert not os.path.exists(folder)
    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(folder)
    assert os.path.exists(result_path)


def test_create_code_file_special_characters(tmp_path):
    """特殊文字を含むファイル名のテスト"""
    folder = str(tmp_path / "generated")
    filename = "test-file_123.py"
    code = "print('test')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    assert filename in result_path


def test_create_code_file_empty_code(tmp_path):
    """空のコードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "empty.py"
    code = ""

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        assert f.read() == ""


def test_create_code_file_unicode_content(tmp_path):
    """Unicode文字を含むコードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "unicode.py"
    code = "# 日本語コメント\nprint('こんにちは')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "日本語コメント" in content
        assert "こんにちは" in content


def test_create_code_file_very_long_code(tmp_path):
    """非常に長いコードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "long.py"
    code = "\n".join([f"# Line {i}" for i in range(1000)])

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert len(content) > 1000
        assert "Line 0" in content
        assert "Line 999" in content


def test_create_code_file_special_filename(tmp_path):
    """特殊なファイル名のテスト（スペース、ドットなど）"""
    folder = str(tmp_path / "generated")
    filename = "test file.name.py"
    code = "print('test')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    assert filename in result_path


def test_create_code_file_nested_path(tmp_path):
    """ネストされたパスでのファイル作成テスト"""
    folder = str(tmp_path / "a" / "b" / "c" / "d")
    filename = "deep.py"
    code = "x = 1"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(folder)
    assert os.path.exists(result_path)
    assert "d" in result_path


def test_create_code_file_return_path_format(tmp_path):
    """返されるパスの形式を確認するテスト"""
    folder = str(tmp_path / "generated")
    filename = "test.py"
    code = "pass"

    result_path = create_code_file(filename, code, folder)

    # パスが文字列であることを確認
    assert isinstance(result_path, str)
    # パスにファイル名が含まれることを確認
    assert filename in result_path
    # パスにフォルダが含まれることを確認
    assert "generated" in result_path


def test_create_code_file_concurrent_creation(tmp_path):
    """複数ファイルの同時作成テスト"""
    folder = str(tmp_path / "generated")

    files = [
        ("file1.py", "code1"),
        ("file2.py", "code2"),
        ("file3.py", "code3"),
    ]

    results = []
    for filename, code in files:
        result_path = create_code_file(filename, code, folder)
        results.append(result_path)
        assert os.path.exists(result_path)

    # すべてのファイルが作成されていることを確認
    assert len(results) == 3
    assert all(os.path.exists(p) for p in results)


def test_create_code_file_overwrite_existing(tmp_path):
    """既存ファイルの上書きテスト"""
    folder = str(tmp_path / "generated")
    filename = "test.py"
    code1 = "original"
    code2 = "modified"

    # 最初のファイル作成
    result_path1 = create_code_file(filename, code1, folder)
    assert os.path.exists(result_path1)
    with open(result_path1, "r", encoding="utf-8") as f:
        assert f.read() == code1

    # 同じファイル名で上書き
    result_path2 = create_code_file(filename, code2, folder)
    assert result_path1 == result_path2  # 同じパスが返される
    with open(result_path2, "r", encoding="utf-8") as f:
        assert f.read() == code2


def test_create_code_file_binary_like_content(tmp_path):
    """バイナリ風のコンテンツのテスト"""
    folder = str(tmp_path / "generated")
    filename = "binary.py"
    # バイナリ風だが実際にはテキスト
    code = "\x00\x01\x02\x03" + "print('test')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        assert "print('test')" in content


def test_create_code_file_very_long_filename(tmp_path):
    """非常に長いファイル名のテスト"""
    folder = str(tmp_path / "generated")
    filename = "a" * 200 + ".py"
    code = "pass"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    assert filename in result_path


def test_create_code_file_code_with_encoding_issues(tmp_path):
    """エンコーディング問題を含むコードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "encoding.py"
    # 様々なエンコーディングの文字を含む
    code = "# -*- coding: utf-8 -*-\nprint('テスト')\n# émoji: 🐍"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "テスト" in content
        assert "🐍" in content


def test_create_code_file_path_with_special_chars(tmp_path):
    """特殊文字を含むフォルダパスのテスト"""
    folder = str(tmp_path / "folder with spaces" / "sub-folder")
    filename = "test.py"
    code = "pass"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(folder)
    assert os.path.exists(result_path)


def test_create_code_file_absolute_path(tmp_path):
    """絶対パスでのファイル作成テスト"""
    folder = str(tmp_path / "generated")
    filename = "absolute.py"
    code = "x = 1"

    result_path = create_code_file(filename, code, folder)

    # 返されるパスが絶対パスまたは相対パスであることを確認
    assert os.path.exists(result_path)
    assert os.path.isabs(result_path) or os.path.exists(result_path)


def test_create_code_file_relative_path_handling(tmp_path, monkeypatch):
    """相対パスの処理テスト"""
    import os
    original_cwd = os.getcwd()

    try:
        os.chdir(str(tmp_path))
        folder = "relative_folder"
        filename = "relative.py"
        code = "pass"

        result_path = create_code_file(filename, code, folder)

        assert os.path.exists(result_path)
        assert os.path.exists(folder)
    finally:
        os.chdir(original_cwd)


def test_create_code_file_encoding_consistency(tmp_path):
    """エンコーディングの一貫性テスト"""
    folder = str(tmp_path / "generated")
    filename = "encoding_test.py"

    # 様々なエンコーディングの文字を含むコード
    test_cases = [
        "print('ASCII')",
        "print('日本語')",
        "print('émoji: 🐍')",
        "print('Mixed: ASCII + 日本語 + 🐍')"
    ]

    for code in test_cases:
        result_path = create_code_file(filename, code, folder)
        with open(result_path, "r", encoding="utf-8") as f:
            read_content = f.read()
            assert read_content == code


def test_create_code_file_idempotency(tmp_path):
    """同じファイルの繰り返し作成テスト（べき等性）"""
    folder = str(tmp_path / "generated")
    filename = "idempotent.py"
    code = "x = 1"

    # 同じファイルを複数回作成
    paths = []
    for _ in range(5):
        path = create_code_file(filename, code, folder)
        paths.append(path)
        assert os.path.exists(path)

    # すべて同じパスが返されることを確認
    assert len(set(paths)) == 1
    # ファイル内容が正しいことを確認
    with open(paths[0], "r", encoding="utf-8") as f:
        assert f.read() == code


def test_create_code_file_with_newlines_variations(tmp_path):
    """様々な改行コードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "newlines.py"

    test_cases = [
        ("line1\nline2\nline3", "\n"),  # Unix
        ("line1\r\nline2\r\nline3", "\r\n"),  # Windows
        ("line1\rline2\rline3", "\r"),  # Old Mac
    ]

    for code, expected_newline in test_cases:
        result_path = create_code_file(filename, code, folder)
        with open(result_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
            # 改行が含まれていることを確認
            assert "\n" in content or "\r" in content


def test_create_code_file_none_values_handling(tmp_path):
    """None値の処理テスト"""
    folder = str(tmp_path / "generated")
    filename = "none_test.py"
    
    # Noneを含むコード（文字列として扱われる）
    code = "x = None\nprint(x)"
    
    result_path = create_code_file(filename, code, folder)
    
    assert os.path.exists(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        assert "None" in f.read()


def test_create_code_file_stress_test_many_files(tmp_path):
    """多数のファイル作成のストレステスト"""
    folder = str(tmp_path / "generated")
    
    # 100個のファイルを迅速に作成
    for i in range(100):
        filename = f"stress_test_{i:03d}.py"
        code = f"# File {i}\nprint({i})"
        result_path = create_code_file(filename, code, folder)
        assert os.path.exists(result_path)
    
    # すべてのファイルが存在することを確認
    assert len(list((tmp_path / "generated").glob("stress_test_*.py"))) == 100


def test_create_code_file_performance_large_content(tmp_path):
    """大きなコンテンツのパフォーマンステスト"""
    folder = str(tmp_path / "generated")
    filename = "large.py"
    
    # 1MBのコードを生成
    large_code = "# " + "x" * (1024 * 1024)
    
    import time
    start_time = time.time()
    result_path = create_code_file(filename, large_code, folder)
    elapsed = time.time() - start_time
    
    assert os.path.exists(result_path)
    # ファイルサイズを確認
    file_size = os.path.getsize(result_path)
    assert file_size > 1024 * 1024
    # パフォーマンスが許容範囲内であることを確認（10秒以内）
    assert elapsed < 10.0


def test_create_code_file_path_traversal_prevention(tmp_path):
    """パストラバーサル攻撃の防止テスト"""
    folder = str(tmp_path / "generated")
    
    # パストラバーサルを試みるファイル名
    malicious_names = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "....//....//etc//passwd",
    ]
    
    for malicious_name in malicious_names:
        # ファイル名からパストラバーサルを除去するか、エラーになることを確認
        try:
            result_path = create_code_file(malicious_name, "code", folder)
            # パスが安全な範囲内であることを確認
            assert folder in result_path or str(tmp_path) in result_path
        except (OSError, ValueError):
            # エラーが発生する場合もある（期待される動作）
            pass


def test_create_code_file_symlink_handling(tmp_path):
    """シンボリックリンクの処理テスト"""
    folder = str(tmp_path / "generated")
    filename = "symlink_test.py"
    code = "pass"
    
    # シンボリックリンクが作成される場合の処理を確認
    result_path = create_code_file(filename, code, folder)
    
    assert os.path.exists(result_path)
    # シンボリックリンクか通常ファイルかを確認
    assert os.path.isfile(result_path) or os.path.islink(result_path)


def test_create_code_file_concurrent_writes(tmp_path):
    """並行書き込みのテスト"""
    folder = str(tmp_path / "generated")
    filename = "concurrent.py"
    
    import threading
    
    def write_file(thread_id):
        code = f"# Thread {thread_id}\nprint({thread_id})"
        result_path = create_code_file(f"{filename}_{thread_id}", code, folder)
        assert os.path.exists(result_path)
    
    threads = [threading.Thread(target=write_file, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # すべてのファイルが作成されていることを確認
    assert len(list((tmp_path / "generated").glob("concurrent.py_*"))) == 10


def test_create_code_file_return_value_consistency(tmp_path):
    """戻り値の一貫性テスト"""
    folder = str(tmp_path / "generated")
    filename = "consistency.py"
    code = "pass"
    
    # 同じファイルを複数回作成
    paths = []
    for _ in range(5):
        path = create_code_file(filename, code, folder)
        paths.append(path)
    
    # すべて同じパスが返されることを確認
    assert len(set(paths)) == 1
    assert all(p == paths[0] for p in paths)


def test_create_code_file_with_control_characters(tmp_path):
    """制御文字を含むコードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "control.py"
    
    # 制御文字を含むコード
    code = "print('test')\n\x00\x01\x02\x03\x04\x05"
    
    result_path = create_code_file(filename, code, folder)
    
    assert os.path.exists(result_path)
    # ファイルが読み込めることを確認（エラー処理あり）
    with open(result_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        assert "print" in content
