"""
coder_agent.py のカバレッジ向上テスト

未カバー行: 38-39, 98-111, 147-156
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest


class TestValidatePythonSyntax:
    """_validate_python_syntax のテスト"""

    def test_valid_syntax(self):
        """正しいPythonコードはTrueを返す"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        ok, err = agent._validate_python_syntax("x = 1 + 2\n")
        assert ok is True
        assert err == ""

    def test_syntax_error(self):
        """SyntaxErrorの場合、False + エラーメッセージ"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        ok, err = agent._validate_python_syntax("def foo(\n")
        assert ok is False
        assert "SyntaxError" in err

    def test_parse_error_generic_exception(self):
        """SyntaxError以外の例外（行38-39）"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        with patch("nexuscore.agents.coder_agent.ast.parse", side_effect=ValueError("bad value")):
            ok, err = agent._validate_python_syntax("x = 1\n")
            assert ok is False
            assert "ParseError" in err


class TestExtractCodeFromResponse:
    """_extract_code_from_response のテスト（行98-111）"""

    def test_extract_from_code_block(self):
        """マークダウンコードブロックからコードを抽出"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        response = "以下がコードです。\n```python\ndef hello():\n    return 'hello'\n```"
        result = agent._extract_code_from_response(response)
        assert "def hello():" in result
        assert "以下がコードです" not in result

    def test_extract_code_block_with_import_start(self):
        """import文から始まるコードブロックの先頭調整"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        response = "```python\nHere is the code\nimport os\n\ndef main():\n    pass\n```"
        result = agent._extract_code_from_response(response)
        assert result.startswith("import os")

    def test_extract_code_block_with_class_start(self):
        """class定義から始まるコードブロック"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        response = "```python\nHere is code\nclass Foo:\n    pass\n```"
        result = agent._extract_code_from_response(response)
        assert result.startswith("class Foo")

    def test_extract_code_block_with_print_start(self):
        """print文から始まるコードブロック"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        response = "```python\nSome intro\nprint('hello')\n```"
        result = agent._extract_code_from_response(response)
        assert "print('hello')" in result

    def test_no_code_block_returns_cleaned_response(self):
        """コードブロックがない場合、レスポンスから不要な前置きを削除"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        response = "Sure! Here is the code:\ndef hello():\n    return 'hello'\n"
        result = agent._extract_code_from_response(response)
        assert "def hello():" in result

    def test_no_code_block_no_code_lines_returns_full(self):
        """コードブロックもコード行もない場合、レスポンス全体を返す"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        response = "Just plain text without code"
        result = agent._extract_code_from_response(response)
        assert result == "Just plain text without code"


class TestValidateCode:
    """_validate_code のテスト（行147-156）"""

    def test_python_language_calls_validate_python_syntax(self):
        """language='python' は _validate_python_syntax を呼ぶ"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        ok, err = agent._validate_code("python", "x = 1\n")
        assert ok is True

    def test_non_python_tree_sitter_unavailable(self):
        """Tree-sitterが利用不可の場合、Trueを返す（行147-148）"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        with patch(
            "nexuscore.agents.coder_agent.SemanticAnalyzer",
            create=True,
        ) as mock_sa_cls:
            mock_instance = Mock()
            mock_instance.check_availability.return_value = (False, "not installed")
            mock_sa_cls.return_value = mock_instance

            # importが失敗するようにpatch
            import sys

            original = sys.modules.get("nexuscore.utils.tree_sitter_checker")
            sys.modules["nexuscore.utils.tree_sitter_checker"] = Mock(
                SemanticAnalyzer=mock_sa_cls
            )
            try:
                ok, err = agent._validate_code("javascript", "var x = 1;")
                assert ok is True
            finally:
                if original is not None:
                    sys.modules["nexuscore.utils.tree_sitter_checker"] = original
                else:
                    del sys.modules["nexuscore.utils.tree_sitter_checker"]

    def test_non_python_tree_sitter_language_unsupported(self):
        """Tree-sitterが言語未対応の場合、Trueを返す（行149-150）"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        mock_analyzer = Mock()
        mock_analyzer.check_availability.return_value = (True, "ok")
        mock_analyzer.setup_parsers.return_value = False

        with patch.dict(
            "sys.modules",
            {"nexuscore.utils.tree_sitter_checker": Mock(SemanticAnalyzer=Mock(return_value=mock_analyzer))},
        ):
            ok, err = agent._validate_code("cobol", "MOVE A TO B")
            assert ok is True

    def test_non_python_tree_sitter_success(self):
        """Tree-sitterが成功した場合、Trueを返す（行151-155）"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {"errors": {"has_syntax_errors": False}}

        mock_analyzer = Mock()
        mock_analyzer.check_availability.return_value = (True, "ok")
        mock_analyzer.setup_parsers.return_value = True
        mock_analyzer.analyze_source_code.return_value = mock_result

        with patch.dict(
            "sys.modules",
            {"nexuscore.utils.tree_sitter_checker": Mock(SemanticAnalyzer=Mock(return_value=mock_analyzer))},
        ):
            ok, err = agent._validate_code("javascript", "var x = 1;")
            assert ok is True

    def test_non_python_tree_sitter_has_errors(self):
        """Tree-sitterがエラー検出した場合、Falseを返す（行156）"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {"errors": {"has_syntax_errors": True}}

        mock_analyzer = Mock()
        mock_analyzer.check_availability.return_value = (True, "ok")
        mock_analyzer.setup_parsers.return_value = True
        mock_analyzer.analyze_source_code.return_value = mock_result

        with patch.dict(
            "sys.modules",
            {"nexuscore.utils.tree_sitter_checker": Mock(SemanticAnalyzer=Mock(return_value=mock_analyzer))},
        ):
            ok, err = agent._validate_code("javascript", "var x = ???")
            assert ok is False
            assert "Tree-sitter" in err

    def test_non_python_tree_sitter_import_fails(self):
        """Tree-sitter import失敗時はTrueを返す（行157-158）"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        # SemanticAnalyzerのimportが例外を投げるケース
        with patch.dict("sys.modules", {"nexuscore.utils.tree_sitter_checker": None}):
            ok, err = agent._validate_code("rust", "fn main() {}")
            assert ok is True


class TestImplementCode:
    """implement_code のテスト"""

    def test_implement_code_returns_valid_code(self):
        """正常系: LLMが有効コードを返す"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        agent.llm_router = None  # execute_llm_task は空文字を返す

        result = agent.implement_code("hello world関数を作って", "")
        # llm_router=Noneなのでexecute_llm_task="" → _extract_code("")=""
        assert isinstance(result, str)

    def test_implement_code_with_mock_llm(self):
        """モックLLMがコードブロックを返す場合"""
        from nexuscore.agents.coder_agent import CoderAgent

        agent = CoderAgent()
        mock_llm = Mock()
        mock_llm.execute.return_value = "```python\ndef greet():\n    return 'hi'\n```"
        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        agent.llm_router = mock_router

        result = agent.implement_code("greet関数を作って", "")
        assert "def greet():" in result
