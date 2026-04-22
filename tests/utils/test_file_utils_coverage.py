"""Issue #74: file_utils の未カバー行テスト"""

import json
import os
from unittest.mock import MagicMock

from nexuscore.utils.file_utils import (
    create_project_structure,
    download_history,
    extract_file_content,
    file_list_display,
)


class TestExtractFileContent:
    """lines 32-40: cp932フォールバックと例外"""

    def test_utf8_success(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        mock_file = MagicMock()
        mock_file.name = str(f)
        result = extract_file_content(mock_file)
        assert result == "hello world"

    def test_cp932_fallback(self, tmp_path):
        f = tmp_path / "shiftjis.txt"
        f.write_bytes(b"\x82\xb1\x82\xf1\x82\xc9\x82\xbf\x82\xcd")  # "こんにちは" in Shift-JIS
        mock_file = MagicMock()
        mock_file.name = str(f)
        # utf-8 fails, falls back to cp932
        result = extract_file_content(mock_file)
        assert len(result) > 0

    def test_no_name_attr(self):
        mock_file = MagicMock(spec=[])
        result = extract_file_content(mock_file)
        assert result == "" or result is None

    def test_file_not_exists(self, tmp_path):
        mock_file = MagicMock()
        mock_file.name = str(tmp_path / "nonexistent.txt")
        result = extract_file_content(mock_file)
        assert result == "" or result is None


class TestFileListDisplay:
    def test_empty(self):
        assert "未選択" in file_list_display(None)

    def test_single_file(self):
        mock = MagicMock()
        mock.name = "test.py"
        assert "test.py" in file_list_display(mock)

    def test_list_of_strings(self):
        assert "a" in file_list_display(["a", "b"])


class TestDownloadHistory:
    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = download_history([{"k": "v"}])
        assert result.startswith("history_")
        assert os.path.exists(result)
        with open(result, encoding="utf-8") as f:
            assert json.load(f) == [{"k": "v"}]


class TestCreateProjectStructure:
    """lines 110-111: フォルダ/ファイル作成の例外"""

    def test_creates_files_and_folders(self, tmp_path):
        files = [
            {"name": "src", "type": "folder"},
            {"name": "src/main.py", "type": "file", "content": "print('hi')"},
            {"name": "src/utils/__init__.py", "type": "file", "content": ""},
        ]
        create_project_structure(str(tmp_path / "proj"), files)
        assert (tmp_path / "proj" / "src" / "main.py").read_text() == "print('hi')"

    def test_invalid_files_format(self, tmp_path):
        create_project_structure(str(tmp_path / "proj"), "not a list")

    def test_invalid_item_skipped(self, tmp_path):
        create_project_structure(str(tmp_path / "proj"), [{"invalid": True}])

    def test_creation_error(self, tmp_path):
        with open(str(tmp_path / "blocked"), "w") as f:
            f.write("block")
        files = [{"name": "blocked/child.py", "type": "file", "content": "x"}]
        create_project_structure(str(tmp_path), files)
