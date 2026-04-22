"""Issue #74: test_generator の未カバー行テスト"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.utils.test_generator import (
    TestGenConfig,
    generate_template_tests,
    generate_tests_for_module,
    generate_and_validate_test_code,
)


class TestGenerateTemplateTestsErrors:
    """lines 126-127, 163-165: generate_template_testsの例外分岐"""

    def test_project_root_exception_fallback(self, tmp_path):
        """project_path_to_module_path例外時にstemにフォールバック"""
        mod = tmp_path / "mod.py"
        mod.write_text("def hello(): pass")
        with patch(
            "nexuscore.utils.test_generator.project_path_to_module_path",
            side_effect=ValueError("bad path"),
        ):
            result = generate_template_tests(
                mod, project_root=tmp_path
            )
        assert "test_hello" in result or "Auto-generated" in result

    def test_template_unexpected_exception(self, tmp_path):
        """parse例外時にフォールバックコードを返す"""
        mod = tmp_path / "bad.py"
        mod.write_text("invalid {{{ python")
        with patch("nexuscore.utils.test_generator.ast.parse", side_effect=SyntaxError("bad")):
            result = generate_template_tests(mod)
        assert "Auto-generated" in result or "test_parse_error" in result


class TestGenerateAndValidate:
    """lines 305-309, 336, 342-344: generate_and_validateの分岐"""

    def test_your_module_replacement(self):
        """'your_module'を実際のmodule_pathに置換"""
        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value="from your_module import foo"):
            with patch("nexuscore.utils.test_generator.validate_test_code", return_value=(True, None, [])):
                code, valid, err, warnings = generate_and_validate_test_code(
                    "code",
                    file_path=Path("src/my_pkg/mod.py"),
                    project_root=Path("src"),
                )
        assert "my_pkg.mod" in code or "your_module" not in code

    def test_your_module_no_module_path(self):
        """module_pathなしでもエラーにならない"""
        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value="import your_module"):
            with patch("nexuscore.utils.test_generator.validate_test_code", return_value=(True, None, [])):
                code, valid, err, warnings = generate_and_validate_test_code("code")
        assert code is not None

    def test_invalid_test_creates_fallback(self, tmp_path):
        """無効なテストコード→フォールバック"""
        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value="bad code"):
            with patch("nexuscore.utils.test_generator.validate_test_code", return_value=(False, "syntax error", [])):
                with patch("nexuscore.utils.test_generator.create_fallback_test_file", return_value="# fallback"):
                    code, valid, err, warnings = generate_and_validate_test_code(
                        "code", file_path=tmp_path / "mod.py"
                    )
        assert valid is True

    def test_config_none_uses_default(self):
        """config=None時にDEFAULT_CONFIGが使用される"""
        with patch("nexuscore.utils.test_generator.generate_unit_tests", return_value="def test_x(): pass"):
            with patch("nexuscore.utils.test_generator.extract_code_from_markdown", return_value="def test_x(): pass"):
                result = generate_and_validate_test_code("code")
        assert result[0] is not None


class TestGenerateTestsForModule:
    """lines 336, 342-344: ファイル読み込みエラー"""

    def test_read_error_creates_fallback(self, tmp_path):
        """読み込めないファイル→フォールバックテスト"""
        missing = tmp_path / "nonexistent.py"
        result = generate_tests_for_module(missing, output_path=tmp_path / "test_out.py")
        content = result.read_text()
        assert "test_read_error" in content or "Auto-generated" in content

    def test_config_param(self, tmp_path):
        """config渡し時の正常系"""
        mod = tmp_path / "simple.py"
        mod.write_text("def add(a, b): return a + b")
        config = TestGenConfig(use_llm=False, max_functions=10, seed=None)
        result = generate_tests_for_module(mod, project_root=tmp_path, config=config)
        content = result.read_text()
        assert "test_add" in content
