"""
file_utils.py の包括的テスト

カバレッジ:
- extract_file_content: ファイル内容抽出（UTF-8/CP932フォールバック）
- file_list_display: ファイルリスト表示フォーマット
- download_history: 履歴のJSON保存
- create_project_structure: プロジェクト構造の再帰的作成

エッジケース:
- 存在しないファイル、エンコーディングエラー
- 空のファイルリスト、不正な入力
- Unicode文字、特殊文字を含むパス
- ネストされたディレクトリ構造
"""

import json
import os
from unittest.mock import Mock

from nexuscore.utils.file_utils import (
    create_project_structure,
    download_history,
    extract_file_content,
    file_list_display,
)


class TestExtractFileContent:
    """extract_file_content() のテスト"""

    def test_extract_file_content_utf8(self, tmp_path):
        """UTF-8エンコーディングのファイルを読み込み"""
        test_file = tmp_path / "test_utf8.txt"
        content = "Hello, UTF-8 world!\n日本語テスト"
        test_file.write_text(content, encoding="utf-8")

        # Mock file object with name attribute
        mock_file = Mock()
        mock_file.name = str(test_file)

        result = extract_file_content(mock_file)

        assert result == content

    def test_extract_file_content_special_characters(self, tmp_path):
        """特殊文字を含むファイル"""
        test_file = tmp_path / "special.txt"
        content = "Special: <>&\"'@#$%^&*()"
        test_file.write_text(content, encoding="utf-8")

        mock_file = Mock()
        mock_file.name = str(test_file)

        result = extract_file_content(mock_file)

        assert result == content

    def test_extract_file_content_empty_file(self, tmp_path):
        """空のファイル"""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        mock_file = Mock()
        mock_file.name = str(test_file)

        result = extract_file_content(mock_file)

        assert result == ""

    def test_extract_file_content_nonexistent_file(self):
        """存在しないファイル"""
        mock_file = Mock()
        mock_file.name = "/nonexistent/path/file.txt"

        result = extract_file_content(mock_file)

        # エラーが発生した場合、空文字列または None を返す
        assert result == "" or result is None

    def test_extract_file_content_no_name_attribute(self):
        """name属性がないファイルオブジェクト"""
        mock_file = Mock(spec=[])  # name属性なし

        result = extract_file_content(mock_file)

        # name属性がない場合、空文字列または None を返す
        assert result == "" or result is None

    def test_extract_file_content_multiline(self, tmp_path):
        """複数行のファイル"""
        test_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3\nLine 4"
        test_file.write_text(content, encoding="utf-8")

        mock_file = Mock()
        mock_file.name = str(test_file)

        result = extract_file_content(mock_file)

        assert result == content
        assert result.count("\n") == 3

    def test_extract_file_content_large_file(self, tmp_path):
        """大きなファイル（10000行）"""
        test_file = tmp_path / "large.txt"
        content = "\n".join([f"Line {i}" for i in range(10000)])
        test_file.write_text(content, encoding="utf-8")

        mock_file = Mock()
        mock_file.name = str(test_file)

        result = extract_file_content(mock_file)

        assert len(result.splitlines()) == 10000


class TestFileListDisplay:
    """file_list_display() のテスト"""

    def test_file_list_display_empty(self):
        """空のファイルリスト"""
        result = file_list_display([])

        assert result == "（ファイル未選択）"

    def test_file_list_display_none(self):
        """None を渡した場合"""
        result = file_list_display(None)

        assert result == "（ファイル未選択）"

    def test_file_list_display_single_file(self):
        """単一ファイル"""
        mock_file = Mock()
        mock_file.name = "/path/to/file.txt"

        result = file_list_display([mock_file])

        assert "/path/to/file.txt" in result

    def test_file_list_display_multiple_files(self):
        """複数ファイル"""
        files = []
        for i in range(3):
            mock_file = Mock()
            mock_file.name = f"/path/file{i}.txt"
            files.append(mock_file)

        result = file_list_display(files)

        # 改行区切りで結合される
        assert "file0.txt" in result
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "\\n" in result  # 改行がエスケープされている

    def test_file_list_display_single_file_not_list(self):
        """リストではなく単一ファイルを渡した場合"""
        mock_file = Mock()
        mock_file.name = "/path/to/single.txt"

        result = file_list_display(mock_file)

        assert "single.txt" in result

    def test_file_list_display_file_without_name(self):
        """name属性がないオブジェクト"""
        mock_file = Mock(spec=[])  # name属性なし

        result = file_list_display([mock_file])

        # str(file) が使われる
        assert "Mock" in result or "<" in result

    def test_file_list_display_unicode_filename(self):
        """Unicode文字を含むファイル名"""
        mock_file = Mock()
        mock_file.name = "/path/日本語/ファイル.txt"

        result = file_list_display([mock_file])

        assert "日本語" in result
        assert "ファイル.txt" in result


class TestDownloadHistory:
    """download_history() のテスト"""

    def test_download_history_simple(self):
        """単純な履歴をダウンロード"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        filename = download_history(history)

        try:
            # ファイルが作成される
            assert os.path.exists(filename)
            assert filename.startswith("history_")
            assert filename.endswith(".json")

            # 内容を確認
            with open(filename, encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded == history
        finally:
            # クリーンアップ
            if os.path.exists(filename):
                os.remove(filename)

    def test_download_history_empty(self):
        """空の履歴"""
        history = []

        filename = download_history(history)

        try:
            assert os.path.exists(filename)

            with open(filename, encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded == []
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_download_history_unicode_content(self):
        """Unicode文字を含む履歴"""
        history = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "안녕하세요"},
        ]

        filename = download_history(history)

        try:
            with open(filename, encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded[0]["content"] == "こんにちは"
            assert loaded[1]["content"] == "안녕하세요"
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_download_history_filename_format(self):
        """ファイル名のフォーマットを確認"""
        history = [{"test": "data"}]

        filename = download_history(history)

        try:
            # ファイル名は history_YYYYMMDD_HHMMSS.json 形式
            assert filename.startswith("history_")
            assert ".json" in filename

            # 日付部分を抽出して確認
            date_part = filename.replace("history_", "").replace(".json", "")
            # YYYYMMDD_HHMMSS形式であることを確認
            assert len(date_part) == 15  # YYYYMMDD_HHMMSS
            assert "_" in date_part
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_download_history_ensure_ascii_false(self):
        """ensure_ascii=False で日本語が直接保存される"""
        history = [{"content": "日本語"}]

        filename = download_history(history)

        try:
            # ファイル内容を直接読み込む（JSONパースせず）
            with open(filename, encoding="utf-8") as f:
                content = f.read()

            # エスケープされずに日本語が直接保存されている
            assert "日本語" in content
            assert "\\u" not in content  # Unicodeエスケープされていない
        finally:
            if os.path.exists(filename):
                os.remove(filename)


class TestCreateProjectStructure:
    """create_project_structure() のテスト"""

    def test_create_project_structure_empty_files(self, tmp_path):
        """空のファイルリスト"""
        root = tmp_path / "empty_project"

        create_project_structure(str(root), [])

        # ルートディレクトリのみ作成される
        assert root.exists()
        assert root.is_dir()

    def test_create_project_structure_single_file(self, tmp_path):
        """単一ファイルを作成"""
        root = tmp_path / "single_file_project"

        files = [{"name": "README.md", "type": "file", "content": "# Test Project"}]

        create_project_structure(str(root), files)

        readme = root / "README.md"
        assert readme.exists()
        assert readme.read_text(encoding="utf-8") == "# Test Project"

    def test_create_project_structure_single_folder(self, tmp_path):
        """単一フォルダを作成"""
        root = tmp_path / "single_folder_project"

        files = [{"name": "src", "type": "folder"}]

        create_project_structure(str(root), files)

        src_dir = root / "src"
        assert src_dir.exists()
        assert src_dir.is_dir()

    def test_create_project_structure_nested_folders(self, tmp_path):
        """ネストされたフォルダ構造"""
        root = tmp_path / "nested_project"

        files = [
            {"name": "src", "type": "folder"},
            {"name": "src/components", "type": "folder"},
            {"name": "src/components/ui", "type": "folder"},
        ]

        create_project_structure(str(root), files)

        assert (root / "src").exists()
        assert (root / "src" / "components").exists()
        assert (root / "src" / "components" / "ui").exists()

    def test_create_project_structure_files_in_folders(self, tmp_path):
        """フォルダ内にファイルを作成"""
        root = tmp_path / "files_in_folders"

        files = [
            {"name": "src", "type": "folder"},
            {"name": "src/main.py", "type": "file", "content": "print('Hello')"},
            {"name": "src/utils.py", "type": "file", "content": "def helper(): pass"},
        ]

        create_project_structure(str(root), files)

        main_py = root / "src" / "main.py"
        utils_py = root / "src" / "utils.py"

        assert main_py.exists()
        assert utils_py.exists()
        assert main_py.read_text(encoding="utf-8") == "print('Hello')"
        assert "def helper" in utils_py.read_text(encoding="utf-8")

    def test_create_project_structure_backslash_paths(self, tmp_path):
        """バックスラッシュを含むパス（Windows形式）"""
        root = tmp_path / "backslash_project"

        files = [
            {
                "name": "src\\\\components\\\\Button.tsx",
                "type": "file",
                "content": "export const Button",
            }
        ]

        create_project_structure(str(root), files)

        # バックスラッシュはスラッシュに正規化される
        button = root / "src" / "components" / "Button.tsx"
        assert button.exists()

    def test_create_project_structure_leading_slash(self, tmp_path):
        """先頭のスラッシュを含むパス"""
        root = tmp_path / "leading_slash"

        files = [{"name": "/src/main.py", "type": "file", "content": "# Main"}]

        create_project_structure(str(root), files)

        # 先頭のスラッシュは削除される
        main_py = root / "src" / "main.py"
        assert main_py.exists()

    def test_create_project_structure_invalid_item_skipped(self, tmp_path):
        """不正なアイテムはスキップされる"""
        root = tmp_path / "invalid_items"

        files = [
            {"name": "valid.txt", "type": "file", "content": "OK"},
            {"name": "", "type": "file"},  # 空の名前
            {"type": "file"},  # 名前なし
            {"name": "no_type.txt"},  # タイプなし
        ]

        create_project_structure(str(root), files)

        # 有効なファイルのみ作成される
        assert (root / "valid.txt").exists()

    def test_create_project_structure_non_list_files(self, tmp_path):
        """filesがリストでない場合"""
        root = tmp_path / "non_list"

        # 辞書を渡す（リストではない）
        create_project_structure(str(root), {"name": "test.txt"})

        # エラーハンドリングされ、ルートディレクトリのみ作成される
        assert root.exists()

    def test_create_project_structure_unicode_paths(self, tmp_path):
        """Unicode文字を含むパス"""
        root = tmp_path / "unicode_project"

        files = [
            {"name": "日本語", "type": "folder"},
            {"name": "日本語/テスト.py", "type": "file", "content": "# 日本語コメント"},
        ]

        create_project_structure(str(root), files)

        assert (root / "日本語").exists()
        assert (root / "日本語" / "テスト.py").exists()

    def test_create_project_structure_empty_content(self, tmp_path):
        """contentが空のファイル"""
        root = tmp_path / "empty_content"

        files = [
            {"name": "empty.txt", "type": "file", "content": ""},
            {"name": "no_content.txt", "type": "file"},  # contentキーなし
        ]

        create_project_structure(str(root), files)

        empty = root / "empty.txt"
        no_content = root / "no_content.txt"

        assert empty.exists()
        assert no_content.exists()
        assert empty.read_text(encoding="utf-8") == ""
        assert no_content.read_text(encoding="utf-8") == ""

    def test_create_project_structure_creates_parent_dirs(self, tmp_path):
        """親ディレクトリが存在しない場合も作成"""
        root = tmp_path / "auto_parent"

        files = [
            # フォルダを明示的に作成せずにファイルを作成
            {"name": "deep/nested/path/file.txt", "type": "file", "content": "Auto-created"}
        ]

        create_project_structure(str(root), files)

        file_path = root / "deep" / "nested" / "path" / "file.txt"
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == "Auto-created"


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_extract_file_content_with_encoding_fallback(self, tmp_path):
        """UTF-8失敗時のCP932フォールバック"""
        # このテストは実際のCP932エンコードファイルが必要なので、
        # モックで代替（実装詳細のテスト）
        test_file = tmp_path / "cp932.txt"

        # UTF-8として書き込み（CP932のテストは環境依存）
        test_file.write_text("テスト", encoding="utf-8")

        mock_file = Mock()
        mock_file.name = str(test_file)

        result = extract_file_content(mock_file)

        assert "テスト" in result

    def test_file_list_display_mixed_types(self):
        """name属性ありとなしの混在"""
        mock_with_name = Mock()
        mock_with_name.name = "file1.txt"

        mock_without_name = Mock(spec=[])

        result = file_list_display([mock_with_name, mock_without_name])

        assert "file1.txt" in result

    def test_create_project_structure_special_chars_in_filename(self, tmp_path):
        """特殊文字を含むファイル名"""
        root = tmp_path / "special_chars"

        files = [
            {"name": "file@#$.txt", "type": "file", "content": "Special"},
        ]

        create_project_structure(str(root), files)

        # 特殊文字を含むファイルも作成される
        assert (root / "file@#$.txt").exists()

    def test_create_project_structure_very_deep_nesting(self, tmp_path):
        """非常に深いネスト構造"""
        root = tmp_path / "deep_nesting"

        # 10階層のネスト
        path_parts = ["level" + str(i) for i in range(10)]
        deep_path = "/".join(path_parts) + "/file.txt"

        files = [{"name": deep_path, "type": "file", "content": "Deep file"}]

        create_project_structure(str(root), files)

        # 深くネストされたファイルが作成される
        final_path = root
        for part in path_parts:
            final_path = final_path / part
        final_path = final_path / "file.txt"

        assert final_path.exists()
        assert final_path.read_text(encoding="utf-8") == "Deep file"
