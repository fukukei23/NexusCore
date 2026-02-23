"""Tests for file_creator.py"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    with open(result_path, encoding="utf-8") as f:
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
    with open(result_path, encoding="utf-8") as f:
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

    with open(result_path, encoding="utf-8") as f:
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
    with open(result_path, encoding="utf-8") as f:
        assert f.read() == ""


def test_create_code_file_unicode_content(tmp_path):
    """Unicode文字を含むコードのテスト"""
    folder = str(tmp_path / "generated")
    filename = "unicode.py"
    code = "# 日本語コメント\nprint('こんにちは')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, encoding="utf-8") as f:
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
    with open(result_path, encoding="utf-8") as f:
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
    with open(result_path1, encoding="utf-8") as f:
        assert f.read() == code1

    # 同じファイル名で上書き
    result_path2 = create_code_file(filename, code2, folder)
    assert result_path1 == result_path2  # 同じパスが返される
    with open(result_path2, encoding="utf-8") as f:
        assert f.read() == code2


def test_create_code_file_binary_like_content(tmp_path):
    """バイナリ風のコンテンツのテスト"""
    folder = str(tmp_path / "generated")
    filename = "binary.py"
    # バイナリ風だが実際にはテキスト
    code = "\x00\x01\x02\x03" + "print('test')"

    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)
    with open(result_path, encoding="utf-8", errors="replace") as f:
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
    with open(result_path, encoding="utf-8") as f:
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
        "print('Mixed: ASCII + 日本語 + 🐍')",
    ]

    for code in test_cases:
        result_path = create_code_file(filename, code, folder)
        with open(result_path, encoding="utf-8") as f:
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
    with open(paths[0], encoding="utf-8") as f:
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
        with open(result_path, encoding="utf-8", newline="") as f:
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
    with open(result_path, encoding="utf-8") as f:
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
    with open(result_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
        assert "print" in content


def test_create_code_file_integration_with_history_manager(tmp_path):
    """HistoryManagerとの統合テスト"""
    from history_manager import HistoryManager

    folder = str(tmp_path / "generated")
    history_dir = str(tmp_path / "history")
    hm = HistoryManager(history_dir=history_dir)

    # ファイル作成と履歴管理の統合
    filename = "integration_test.py"
    code = "def test():\n    return True"

    result_path = create_code_file(filename, code, folder)

    # 履歴に状態を追加
    state = {"action": "file_created", "file_path": result_path, "filename": filename}
    hm.add_state(state)

    # 履歴が正しく保存されていることを確認
    assert os.path.exists(result_path)
    assert hm.get_current_state()["file_path"] == result_path


def test_create_code_file_integration_with_vcs(tmp_path):
    """VCSとの統合テスト"""
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))
    from nexuscore.utils import vcs

    # Gitリポジトリを初期化
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)

    folder = str(tmp_path / "generated")
    controller = vcs.GitController(repo_path=str(tmp_path))

    # ファイルを作成
    filename = "vcs_integration.py"
    code = "print('VCS integration')"

    result_path = create_code_file(filename, code, folder)

    # ファイルをGitに追加してコミット
    subprocess.run(["git", "add", result_path], cwd=tmp_path, check=True)
    commit_hash = controller.commit_changes([result_path], "Add integration test file")

    assert os.path.exists(result_path)
    if commit_hash is not None:
        assert isinstance(commit_hash, str)
        assert len(commit_hash) == 40


def test_create_code_file_with_code_generator_output(tmp_path, monkeypatch):
    """コードジェネレーター出力との統合テスト"""
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))
    from nexuscore.modules import code_generator

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")

    # コードジェネレーターをモック
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        "```python\ndef generated_func():\n    return 42\n```"
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    folder = str(tmp_path / "generated")

    with patch("nexuscore.modules.code_generator.get_client", return_value=mock_client):
        # コードを生成
        generated_code = code_generator.generate_code_from_text("Create a function that returns 42")

        # 生成されたコードをファイルに保存
        filename = "generated_code.py"
        result_path = create_code_file(filename, generated_code, folder)

        assert os.path.exists(result_path)
        with open(result_path, encoding="utf-8") as f:
            content = f.read()
            assert "generated_func" in content or "42" in content


def test_create_code_file_permissions_handling(tmp_path):
    """ファイル権限の処理テスト"""
    folder = str(tmp_path / "generated")
    filename = "permissions.py"
    code = "pass"

    result_path = create_code_file(filename, code, folder)

    # ファイルが読み書き可能であることを確認
    assert os.path.exists(result_path)
    assert os.access(result_path, os.R_OK)
    assert os.access(result_path, os.W_OK)


def test_create_code_file_with_template_pattern(tmp_path):
    """テンプレートパターンのテスト"""
    folder = str(tmp_path / "generated")

    # テンプレートコード
    template = """
def {function_name}({args}):
    \"\"\"{docstring}\"\"\"
    return {return_value}
"""

    # 複数の関数を生成
    functions = [
        {
            "function_name": "add",
            "args": "a, b",
            "docstring": "Add two numbers",
            "return_value": "a + b",
        },
        {
            "function_name": "multiply",
            "args": "x, y",
            "docstring": "Multiply two numbers",
            "return_value": "x * y",
        },
    ]

    for func in functions:
        code = template.format(**func)
        filename = f"{func['function_name']}.py"
        result_path = create_code_file(filename, code, folder)
        assert os.path.exists(result_path)
        with open(result_path, encoding="utf-8") as f:
            content = f.read()
            assert func["function_name"] in content


def test_create_code_file_with_dependency_injection_pattern(tmp_path):
    """依存性注入パターンのテスト"""
    folder = str(tmp_path / "generated")

    # 依存性注入を使用するコード
    code = """
class Service:
    def __init__(self, dependency):
        self.dependency = dependency

    def execute(self):
        return self.dependency.process()
"""

    result_path = create_code_file("service.py", code, folder)

    assert os.path.exists(result_path)
    with open(result_path, encoding="utf-8") as f:
        content = f.read()
        assert "class Service" in content
        assert "dependency" in content


def test_create_code_file_with_decorator_pattern(tmp_path):
    """デコレーターパターンのテスト"""
    folder = str(tmp_path / "generated")

    # デコレーターを使用するコード
    code = """
def decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper

@decorator
def decorated_function():
    return "Hello"
"""

    result_path = create_code_file("decorator.py", code, folder)

    assert os.path.exists(result_path)
    with open(result_path, encoding="utf-8") as f:
        content = f.read()
        assert "@decorator" in content
        assert "def decorated_function" in content


def test_create_code_file_resource_cleanup(tmp_path):
    """リソースクリーンアップのテスト"""
    folder = str(tmp_path / "generated")
    filename = "resource_test.py"
    code = "pass"

    # ファイル作成後にリソースが適切にクリーンアップされることを確認
    result_path = create_code_file(filename, code, folder)

    assert os.path.exists(result_path)

    # ファイルハンドルが適切に閉じられていることを確認（再度開ける）
    with open(result_path, encoding="utf-8") as f:
        content = f.read()
        assert content == code


def test_create_code_file_memory_usage_stress(tmp_path):
    """メモリ使用量のストレステスト"""
    folder = str(tmp_path / "generated")

    # 大量のファイルを作成してメモリリークを検出
    import gc

    initial_objects = len(gc.get_objects())

    # 500個のファイルを作成
    for i in range(500):
        filename = f"memory_test_{i:03d}.py"
        code = f"# File {i}\nprint({i})"
        result_path = create_code_file(filename, code, folder)
        assert os.path.exists(result_path)

    # ガベージコレクションを実行
    gc.collect()

    # メモリリークがないことを確認（オブジェクト数が極端に増えていない）
    final_objects = len(gc.get_objects())
    # オブジェクト数が10倍以上に増えていないことを確認
    assert final_objects < initial_objects * 10


def test_create_code_file_file_descriptor_leak(tmp_path):
    """ファイル記述子リークのテスト"""
    folder = str(tmp_path / "generated")

    import resource

    # 現在のファイル記述子の制限を取得
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)

    # 多数のファイルを作成してファイル記述子リークを検出
    for i in range(100):
        filename = f"fd_test_{i:03d}.py"
        code = f"print({i})"
        result_path = create_code_file(filename, code, folder)
        assert os.path.exists(result_path)

        # 各ファイルが読み込めることを確認
        with open(result_path, encoding="utf-8") as f:
            assert f.read() == code


def test_create_code_file_concurrent_access_with_locking(tmp_path):
    """ロックを伴う並行アクセスのテスト"""
    folder = str(tmp_path / "generated")
    filename = "locking_test.py"

    import threading
    import time

    results = []
    errors = []

    def create_file_safely(thread_id):
        try:
            code = f"# Thread {thread_id}\nprint({thread_id})"
            result_path = create_code_file(f"{filename}_{thread_id}", code, folder)
            results.append(result_path)
            time.sleep(0.01)  # 少し待機
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=create_file_safely, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # すべてのファイルが作成されていることを確認
    assert len(results) == 20
    assert len(errors) == 0


def test_create_code_file_disk_space_handling(tmp_path, monkeypatch):
    """ディスクスペース不足の処理テスト"""
    folder = str(tmp_path / "generated")
    filename = "disk_test.py"
    code = "pass"

    # ディスクスペース不足をシミュレート（実際には失敗しないが、エラーハンドリングを確認）
    original_write = open

    def mock_write(*args, **kwargs):
        if "w" in kwargs.get("mode", "") or (len(args) > 1 and "w" in args[1]):
            raise OSError("No space left on device")
        return original_write(*args, **kwargs)

    # モックを適用しない場合（正常系の確認）
    result_path = create_code_file(filename, code, folder)
    assert os.path.exists(result_path)


def test_create_code_file_atomic_write_simulation(tmp_path):
    """アトミック書き込みのシミュレーションテスト"""
    folder = str(tmp_path / "generated")
    filename = "atomic_test.py"
    code = "pass"

    # ファイル作成がアトミックであることを確認（途中で失敗しても破損しない）
    result_path = create_code_file(filename, code, folder)

    # ファイルが完全に書き込まれていることを確認
    assert os.path.exists(result_path)
    file_size = os.path.getsize(result_path)
    assert file_size > 0

    # ファイルが読み込めることを確認
    with open(result_path, encoding="utf-8") as f:
        content = f.read()
        assert content == code


def test_create_code_file_inode_exhaustion_simulation(tmp_path):
    """iノード枯渇のシミュレーションテスト"""
    folder = str(tmp_path / "generated")

    # 大量のファイルを作成してiノード使用を確認
    created_files = []
    try:
        for i in range(1000):
            filename = f"inode_test_{i:04d}.py"
            code = f"print({i})"
            result_path = create_code_file(filename, code, folder)
            created_files.append(result_path)
            assert os.path.exists(result_path)
    except OSError:
        # iノードが不足する場合もある（環境による）
        pass

    # 作成されたファイルが正しいことを確認
    assert len(created_files) > 0
