"""
tester_agent.py のカバレッジ向上テスト

未カバー行: _extract_test_code_from_response, _resolve_test_file_path,
            _count_test_functions, _infer_module_name_from_path,
            _call_llm_for_test_code, generate_tests 等
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestTesterAgentInit:
    """TesterAgent 初期化テスト"""

    def test_init_default(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        assert agent.project_root.is_absolute()

    def test_init_with_project_root(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent(project_root="/tmp")
        assert agent.project_root == Path("/tmp").resolve()


class TestExtractTestCodeFromResponse:
    """_extract_test_code_from_response のテスト"""

    def test_dict_with_test_code_key(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        response = json.dumps({"test_code": "def test_foo(): pass", "testimony": "basic"})
        result = agent._extract_test_code_from_response(response)
        assert "def test_foo" in result

    def test_dict_without_test_code_key(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        response = json.dumps({"other_key": "value"})
        result = agent._extract_test_code_from_response(response)
        # test_codeがない → str(data) が返る
        assert isinstance(result, str)

    def test_invalid_json_returns_as_is(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        response = "not valid json at all"
        result = agent._extract_test_code_from_response(response)
        assert result == "not valid json at all"


class TestResolveTestFilePath:
    """_resolve_test_file_path のテスト"""

    def test_src_prefix_stripped(self):
        from nexuscore.agents.tester_agent import TesterAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)
            result = agent._resolve_test_file_path("src/nexuscore/utils/file_utils.py")
            assert str(result).startswith(tmpdir)
            assert "tests" in str(result)
            assert result.name == "test_file_utils.py"

    def test_nexuscore_prefix(self):
        from nexuscore.agents.tester_agent import TesterAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)
            result = agent._resolve_test_file_path("nexuscore/agents/base.py")
            assert "tests" in str(result)
            assert result.name == "test_base.py"

    def test_already_has_test_prefix(self):
        from nexuscore.agents.tester_agent import TesterAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = TesterAgent(project_root=tmpdir)
            result = agent._resolve_test_file_path("tests/test_foo.py")
            assert result.name == "test_foo.py"


class TestCountTestFunctions:
    """_count_test_functions のテスト"""

    def test_counts_def_test(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        code = "def test_a(): pass\ndef test_b(): pass\ndef helper(): pass"
        count = agent._count_test_functions(code)
        assert count == 2

    def test_no_tests(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        code = "def helper(): pass\nclass Foo: pass"
        count = agent._count_test_functions(code)
        assert count == 0

    def test_indented_test(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        code = "class TestFoo:\n    def test_bar(self): pass"
        count = agent._count_test_functions(code)
        assert count == 1


class TestInferModuleName:
    """_infer_module_name_from_path のテスト"""

    def test_simple_filename(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        assert agent._infer_module_name_from_path("file_utils.py") == "file_utils"

    def test_nested_path(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        assert agent._infer_module_name_from_path("src/nexuscore/agents/base.py") == "base"


class TestGenerateTests:
    """generate_tests のテスト"""

    def test_calls_execute_llm_task(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        with patch.object(agent, "execute_llm_task", return_value='{"test_code":"pass"}') as mock:
            result = agent.generate_tests("要件テスト")
            mock.assert_called_once()
            assert result == '{"test_code":"pass"}'


class TestGenerateTestsAndTestimony:
    """generate_tests_and_testimony のテスト"""

    def test_calls_execute_llm_task(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        with patch.object(agent, "execute_llm_task", return_value='{}') as mock:
            result = agent.generate_tests_and_testimony("code")
            mock.assert_called_once()
            assert result == '{}'


class TestGenerateTestsForModule:
    """generate_tests_for_module のテスト"""

    def test_no_strategy_manager_returns_none(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        agent.strategy_manager = None
        result = agent.generate_tests_for_module("mod", "file.py", "code")
        assert result is None

    def test_no_build_prompt_returns_none(self):
        from nexuscore.agents.tester_agent import TesterAgent

        agent = TesterAgent()
        mock_sm = Mock()
        mock_strategy = Mock()
        mock_strategy.allows_ai_first = True
        mock_strategy.risk = "medium"
        mock_strategy.strategy = "ai_first"
        mock_strategy.min_coverage = 80
        mock_sm.get_strategy.return_value = mock_strategy
        agent.strategy_manager = mock_sm

        with patch("nexuscore.agents.tester_agent.build_test_generation_prompt", None):
            result = agent.generate_tests_for_module("mod", "file.py", "code")
            assert result is None
