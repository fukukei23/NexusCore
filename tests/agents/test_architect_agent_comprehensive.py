"""
architect_agent.py の包括的テスト

カバレッジ:
- ArchitectAgent: プロジェクトアーキテクチャ設計エージェント
  - __init__: BaseAgentの継承
  - design_project_structure: プロジェクト構造設計
    - JSON形式でのファイル構造生成
    - スケルトンコード生成
    - requirements.txt生成
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_dependencies():
    """各テストの前後で依存モジュールをモック化/復元（テスト分離のため）"""
    # テスト前：元の状態を保存してモック化
    original_modules = {
        'nexuscore.llm.llm_router': sys.modules.get('nexuscore.llm.llm_router'),
        'nexuscore.core.retry_utils': sys.modules.get('nexuscore.core.retry_utils'),
        'nexuscore.core.errors': sys.modules.get('nexuscore.core.errors'),
    }

    sys.modules['nexuscore.llm.llm_router'] = MagicMock()
    sys.modules['nexuscore.core.retry_utils'] = MagicMock()
    sys.modules['nexuscore.core.errors'] = MagicMock()

    yield  # ← ここでテストが実行される

    # テスト後：元の状態に復元
    for module_name, original_module in original_modules.items():
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


try:
    from nexuscore.agents.architect_agent import ArchitectAgent
    from nexuscore.agents.base_agent import BaseAgent
    HAS_ARCHITECT_AGENT = True
except ImportError:
    HAS_ARCHITECT_AGENT = False
    ArchitectAgent = None
    BaseAgent = None


@pytest.mark.skipif(not HAS_ARCHITECT_AGENT, reason="architect_agent module not available")
class TestArchitectAgentInit:
    """ArchitectAgent 初期化のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_inherits_base_agent(self, mock_router_class):
        """BaseAgentを継承している"""
        mock_router_class.return_value = Mock()

        agent = ArchitectAgent()

        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, 'llm_router')
        assert hasattr(agent, 'logger')

    def test_system_prompt_defined(self):
        """SYSTEM_PROMPTが定義されている"""
        assert hasattr(ArchitectAgent, 'SYSTEM_PROMPT')
        assert "アーキテクト" in ArchitectAgent.SYSTEM_PROMPT
        assert "ファイル構造" in ArchitectAgent.SYSTEM_PROMPT


@pytest.mark.skipif(not HAS_ARCHITECT_AGENT, reason="architect_agent module not available")
class TestDesignProjectStructure:
    """ArchitectAgent.design_project_structure() のテスト"""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_design_project_structure_basic(self, mock_router_class):
        """基本的なプロジェクト構造設計"""
        project_json = {
            "project": {
                "files": [
                    {"name": "app/", "type": "folder", "content": ""},
                    {"name": "app/main.py", "type": "file", "content": "def main():\n    pass"},
                    {"name": "requirements.txt", "type": "file", "content": "flask"}
                ]
            }
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(project_json)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        result = agent.design_project_structure("Create a simple Flask app")

        # JSONが返ってくることを確認
        assert result == json.dumps(project_json)
        parsed = json.loads(result)
        assert "project" in parsed
        assert "files" in parsed["project"]
        assert len(parsed["project"]["files"]) == 3

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_design_project_structure_calls_execute_llm_task(self, mock_router_class):
        """execute_llm_taskメソッドを使用している"""
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"project": {"files": []}}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        result = agent.design_project_structure("Test requirement")

        # as_json=Trueで呼ばれることを確認
        call_kwargs = mock_llm.execute.call_args[1]
        assert call_kwargs['as_json'] is True

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_design_project_structure_with_complex_requirement(self, mock_router_class):
        """複雑な要求での設計"""
        project_json = {
            "project": {
                "files": [
                    {"name": "src/", "type": "folder", "content": ""},
                    {"name": "src/models/", "type": "folder", "content": ""},
                    {"name": "src/models/user.py", "type": "file", "content": "class User:\n    pass"},
                    {"name": "src/controllers/", "type": "folder", "content": ""},
                    {"name": "tests/", "type": "folder", "content": ""},
                    {"name": "requirements.txt", "type": "file", "content": "flask\nsqlalchemy"}
                ]
            }
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(project_json)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        requirement = "Create a RESTful API with user management, authentication, and database persistence"
        result = agent.design_project_structure(requirement)

        parsed = json.loads(result)
        assert len(parsed["project"]["files"]) == 6

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_design_project_structure_prompt_contains_requirement(self, mock_router_class):
        """プロンプトに要求が含まれている"""
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"project": {"files": []}}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        requirement = "Build a CLI todo app"
        agent.design_project_structure(requirement)

        # プロンプトに要求が含まれていることを確認
        call_args = mock_llm.execute.call_args[1]
        prompt = call_args['prompt']
        assert "Build a CLI todo app" in prompt


@pytest.mark.skipif(not HAS_ARCHITECT_AGENT, reason="architect_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_empty_requirement(self, mock_router_class):
        """空の要求でも動作する"""
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"project": {"files": []}}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        result = agent.design_project_structure("")

        assert result == '{"project": {"files": []}}'

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_japanese_requirement(self, mock_router_class):
        """日本語の要求が処理される"""
        project_json = {"project": {"files": [{"name": "アプリ.py", "type": "file", "content": ""}]}}

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(project_json, ensure_ascii=False)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        result = agent.design_project_structure("シンプルなTODOアプリを作成")

        parsed = json.loads(result)
        assert "project" in parsed

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_llm_returns_invalid_json(self, mock_router_class):
        """LLMが無効なJSONを返した場合"""
        mock_llm = Mock()
        # execute内でJSONパースに失敗するとInvalidModelOutputErrorが発生する想定
        mock_llm.execute.return_value = "Not a valid JSON"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        result = agent.design_project_structure("Test requirement")

        # BaseAgentがas_json=Trueでエラーをキャッチしてフォールバックするため
        # 結果は空JSON "{}" または無効なJSON文字列になる
        assert result in ["Not a valid JSON", "{}"]

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_very_long_requirement(self, mock_router_class):
        """非常に長い要求でも動作する"""
        mock_llm = Mock()
        mock_llm.execute.return_value = '{"project": {"files": []}}'

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = ArchitectAgent()
        long_requirement = "Create an application " * 1000
        result = agent.design_project_structure(long_requirement)

        assert json.loads(result)  # JSONとしてパース可能

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_no_llm_router_available(self):
        """LLMRouterが利用できない場合"""
        agent = ArchitectAgent()
        result = agent.design_project_structure("Test requirement")

        # BaseAgentのフォールバックで空JSONが返る
        assert result == "{}"
