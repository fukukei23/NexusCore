"""
context_agent.py の包括的テスト

カバレッジ:
- ContextAgent: プロジェクトコンテキスト管理エージェント
  - __init__: ContextAnalyzer, PolicyInterface初期化
  - _find_project_root: .git, pyproject.tomlベースのルート探索
  - load_or_create_context: キャッシュロードまたは新規作成
  - create_new_context: 安全版+高度版コンテキスト作成
  - _create_safe_base_context: 基本情報収集
  - _safe_detect_frameworks: requirements.txt解析
  - _safe_count_files: ファイル数カウント
  - request_human_dev_policy: Gradio UIまたはCLI
  - get_error_prevention_rules: ポリシーからルール抽出
  - update_context: コンテキスト更新
"""

import json
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_dependencies():
    """各テストの前後で依存モジュールをモック化/復元（テスト分離のため）"""
    # テスト前：元の状態を保存してモック化
    original_modules = {
        "nexuscore.agents.context_analyzer": sys.modules.get("nexuscore.agents.context_analyzer"),
        "nexuscore.agents.policy_interface": sys.modules.get("nexuscore.agents.policy_interface"),
    }

    sys.modules["nexuscore.agents.context_analyzer"] = MagicMock()
    sys.modules["nexuscore.agents.policy_interface"] = MagicMock()

    yield  # ← ここでテストが実行される

    # テスト後：元の状態に復元
    for module_name, original_module in original_modules.items():
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


try:
    from nexuscore.agents.context_agent import ContextAgent

    HAS_CONTEXT_AGENT = True
except ImportError:
    HAS_CONTEXT_AGENT = False
    ContextAgent = None


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestContextAgentInit:
    """ContextAgent 初期化のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_init_with_all_components(self, mock_policy_class, mock_analyzer_class):
        """ContextAnalyzerとPolicyInterfaceが正常に初期化される"""
        mock_analyzer_class.return_value = Mock()
        mock_policy_class.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ContextAgent(project_root=tmpdir)

            assert agent.project_root == tmpdir
            assert agent.analyzer is not None
            assert agent.policy_interface is not None
            assert agent.context_profile is not None

    @patch("builtins.input", side_effect=["0", "0", "", ""])
    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface", None)
    def test_init_without_policy_interface(self, mock_analyzer_class, mock_input):
        """PolicyInterfaceが利用できない場合でも初期化成功"""
        mock_analyzer_class.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ContextAgent(project_root=tmpdir)

            assert agent.analyzer is not None
            assert agent.policy_interface is None

    @patch("builtins.input", side_effect=["0", "0", "", ""])
    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_init_analyzer_failure(self, mock_policy_class, mock_analyzer_class, mock_input):
        """ContextAnalyzer初期化失敗時でも継続"""
        mock_analyzer_class.side_effect = Exception("Analyzer init failed")
        mock_policy_class.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ContextAgent(project_root=tmpdir)

            assert agent.analyzer is None
            assert agent.policy_interface is None


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestFindProjectRoot:
    """ContextAgent._find_project_root() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_find_project_root_with_git(self, mock_policy, mock_analyzer, tmp_path):
        """.gitフォルダが見つかる場合"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # .gitディレクトリを作成
        (tmp_path / ".git").mkdir()

        with patch("os.path.abspath", return_value=str(tmp_path / "src" / "nexuscore")):
            with patch("os.path.isdir") as mock_isdir:
                with patch("os.path.isfile", return_value=False):
                    mock_isdir.side_effect = lambda p: p == str(tmp_path / ".git")

                    agent = ContextAgent()
                    root = agent._find_project_root()

                    # ルートが見つかることを確認（階層を遡る）
                    assert root is not None

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_find_project_root_with_pyproject(self, mock_policy, mock_analyzer, tmp_path):
        """pyproject.tomlが見つかる場合"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # pyproject.tomlを作成
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\n")

        with patch("os.path.abspath", return_value=str(tmp_path / "src")):
            with patch("os.path.isfile") as mock_isfile:
                mock_isfile.side_effect = lambda p: "pyproject.toml" in p

                agent = ContextAgent()
                root = agent._find_project_root()

                assert root is not None


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestLoadOrCreateContext:
    """ContextAgent.load_or_create_context() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_load_existing_context(self, mock_policy, mock_analyzer, tmp_path):
        """既存のコンテキストファイルが存在する場合"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # 既存のコンテキストファイルを作成
        context_file = tmp_path / ".nexus_context.json"
        cached_context = {"tech_stack": {"frameworks": ["gradio"]}, "version": "2.1-stable"}
        context_file.write_text(json.dumps(cached_context))

        agent = ContextAgent(project_root=str(tmp_path))

        assert agent.context_profile["tech_stack"]["frameworks"] == ["gradio"]
        assert agent.context_profile["version"] == "2.1-stable"

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    @patch("builtins.input", side_effect=["0", "0", "", ""])
    def test_create_new_context_when_no_cache(
        self, mock_input, mock_policy, mock_analyzer, tmp_path
    ):
        """キャッシュがない場合は新規作成"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))

        # 新規作成されたコンテキストを確認
        assert "tech_stack" in agent.context_profile
        assert "file_structure" in agent.context_profile
        assert "version" in agent.context_profile


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestCreateSafeBaseContext:
    """ContextAgent._create_safe_base_context() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_safe_base_context_structure(self, mock_policy, mock_analyzer, tmp_path):
        """安全な基本コンテキストの構造が正しい"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        base_context = agent._create_safe_base_context()

        assert "tech_stack" in base_context
        assert "file_structure" in base_context
        assert "dependencies" in base_context
        assert "environment" in base_context
        assert "last_updated" in base_context
        assert base_context["version"] == "2.1-stable"


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestSafeDetectFrameworks:
    """ContextAgent._safe_detect_frameworks() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_detect_frameworks_from_requirements(self, mock_policy, mock_analyzer, tmp_path):
        """requirements.txtからフレームワークを検出"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # requirements.txtを作成
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("gradio==3.0.0\nopenai>=1.0.0\npytest\n")

        agent = ContextAgent(project_root=str(tmp_path))
        frameworks = agent._safe_detect_frameworks()

        assert "gradio" in frameworks
        assert "openai" in frameworks
        assert "pytest" in frameworks

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_detect_frameworks_no_requirements_file(self, mock_policy, mock_analyzer, tmp_path):
        """requirements.txtがない場合"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        frameworks = agent._safe_detect_frameworks()

        assert isinstance(frameworks, list)


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestSafeCountFiles:
    """ContextAgent._safe_count_files() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_safe_count_files_basic(self, mock_policy, mock_analyzer, tmp_path):
        """ファイル数を正しくカウント"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # テストファイルを作成
        (tmp_path / "file1.py").write_text("# test")
        (tmp_path / "file2.txt").write_text("test")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "file3.py").write_text("# test")

        agent = ContextAgent(project_root=str(tmp_path))
        count = agent._safe_count_files()

        assert count >= 3

    @patch("builtins.input", side_effect=["0", "0", "", ""])
    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_safe_count_files_ignores_git(self, mock_policy, mock_analyzer, mock_input, tmp_path):
        """.gitディレクトリを無視"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # .gitディレクトリを作成
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("# config")
        (tmp_path / "file1.py").write_text("# test")

        agent = ContextAgent(project_root=str(tmp_path))
        count = agent._safe_count_files()

        # .git内のファイルはカウントされない (.nexus_context.jsonも作成されるので2)
        assert count >= 1  # file1.py + .nexus_context.json
        assert count <= 2


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestGetErrorPreventionRules:
    """ContextAgent.get_error_prevention_rules() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_get_error_prevention_rules_basic(self, mock_policy, mock_analyzer, tmp_path):
        """エラー予防ルールを取得"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        agent.context_profile = {
            "dev_policy": {
                "test_import_policy": "関数を直接埋め込み",
                "error_language": "日本語",
                "quality_requirements": ["docstring必須", "エラーハンドリング必須"],
                "security_policy": ["APIキー環境変数管理"],
            }
        }

        rules = agent.get_error_prevention_rules()

        assert rules["embed_functions_in_tests"] is True
        assert rules["use_japanese_errors"] is True
        assert rules["require_docstring"] is True
        assert rules["require_error_handling"] is True
        assert rules["use_env_vars"] is True


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestGenerateEnhancedTestPrompt:
    """ContextAgent.generate_enhanced_test_prompt() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_generate_enhanced_test_prompt_structure(self, mock_policy, mock_analyzer, tmp_path):
        """プロンプトが正しい構造を持つ"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        source_code = "def add(a, b):\n    return a + b"
        prompt = agent.generate_enhanced_test_prompt(source_code)

        assert "インポート文は一切使用しない" in prompt
        assert "完全に自己完結したテストファイル" in prompt
        assert source_code in prompt


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestUpdateContext:
    """ContextAgent.update_context() のテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_update_context_updates_last_updated(self, mock_policy, mock_analyzer, tmp_path):
        """update_contextでlast_updatedが更新される"""
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.detect_tech_stack.return_value = {"frameworks": []}
        mock_analyzer.return_value = mock_analyzer_instance
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        original_time = agent.context_profile.get("last_updated", "")

        # 少し待機
        import time

        time.sleep(0.1)

        updated_context = agent.update_context()

        # last_updatedが更新されていることを確認
        assert updated_context["last_updated"] != original_time


@pytest.mark.skipif(not HAS_CONTEXT_AGENT, reason="context_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_save_and_load_context_roundtrip(self, mock_policy, mock_analyzer, tmp_path):
        """save → loadのラウンドトリップ"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        original_context = {"tech_stack": {"frameworks": ["test"]}, "version": "test"}
        agent.context_profile = original_context
        agent.save_context(original_context)

        # 新しいインスタンスで読み込み
        agent2 = ContextAgent(project_root=str(tmp_path))
        loaded_context = agent2.load_cached_context()

        assert loaded_context["tech_stack"]["frameworks"] == ["test"]

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_analyze_code_request_basic(self, mock_policy, mock_analyzer, tmp_path):
        """コード要求を分析"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        agent = ContextAgent(project_root=str(tmp_path))
        agent.context_profile = {
            "dev_policy": {
                "test_import_policy": "関数を直接埋め込み",
                "error_language": "日本語",
                "quality_requirements": ["docstring必須"],
                "security_policy": ["APIキー環境変数管理"],
            }
        }

        analysis = agent.analyze_code_request("テストコードを作成してください")

        assert "context" in analysis
        assert "prevention_rules" in analysis
        assert "recommendations" in analysis
        assert len(analysis["recommendations"]) > 0

    @patch("nexuscore.agents.context_agent.ContextAnalyzer")
    @patch("nexuscore.agents.context_agent.PolicyInterface")
    def test_safe_count_python_files_limit(self, mock_policy, mock_analyzer, tmp_path):
        """Pythonファイル数カウントの制限"""
        mock_analyzer.return_value = Mock()
        mock_policy.return_value = Mock()

        # 多数のファイルを作成
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text("# test")

        agent = ContextAgent(project_root=str(tmp_path))
        count = agent._safe_count_python_files()

        assert count == 10
