"""
Tests for nexuscore.api.dependencies.orchestrator module.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestPrepareLocalKnowledgeBase:
    """Tests for _prepare_local_knowledge_base function."""

    def test_template_not_found(self, tmp_path):
        """Template が存在しない場合は None"""
        from nexuscore.api.dependencies.orchestrator import _prepare_local_knowledge_base

        result = _prepare_local_knowledge_base(str(tmp_path), str(tmp_path / "nonexistent"))
        assert result is None

    def test_project_kb_already_exists(self, tmp_path):
        """プロジェクトに既に KB がある場合はそのパスを返す"""
        from nexuscore.api.dependencies.orchestrator import _prepare_local_knowledge_base

        template = tmp_path / "fkb_local.json"
        template.write_text("{}")
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_kb = project_dir / "fkb_local.json"
        project_kb.write_text("{}")

        result = _prepare_local_knowledge_base(str(project_dir), str(tmp_path))
        assert result == str(project_kb)

    def test_copy_template_success(self, tmp_path):
        """Template からプロジェクトにコピー成功"""
        from nexuscore.api.dependencies.orchestrator import _prepare_local_knowledge_base

        template = tmp_path / "fkb_local.json"
        template.write_text('{"key": "value"}')
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = _prepare_local_knowledge_base(str(project_dir), str(tmp_path))
        assert result == os.path.join(str(project_dir), "fkb_local.json")
        assert os.path.exists(result)

    def test_copy_template_failure(self, tmp_path):
        """コピー失敗時は None"""
        from nexuscore.api.dependencies.orchestrator import _prepare_local_knowledge_base

        template = tmp_path / "fkb_local.json"
        template.write_text("{}")
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("shutil.copy", side_effect=PermissionError("no write")):
            result = _prepare_local_knowledge_base(str(project_dir), str(tmp_path))
        assert result is None


class TestLoadGuardianCredentials:
    """Tests for _load_guardian_credentials function."""

    def test_credentials_from_env(self):
        """環境変数から認証情報を取得"""
        from nexuscore.api.dependencies.orchestrator import _load_guardian_credentials

        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "test-key", "GUARDIAN_MODEL": "test-model"}):
            api_key, model = _load_guardian_credentials()
        assert api_key == "test-key"
        assert model == "test-model"

    def test_credentials_default_empty(self):
        """環境変数が未設定の場合は空文字"""
        from nexuscore.api.dependencies.orchestrator import _load_guardian_credentials

        with patch.dict(os.environ, {}, clear=True):
            api_key, model = _load_guardian_credentials()
        assert api_key == ""
        assert model == ""


class TestGetOrchestrator:
    """Tests for get_orchestrator function."""

    @patch("nexuscore.api.dependencies.orchestrator.LLMRouter")
    @patch("nexuscore.api.dependencies.orchestrator.PatchApplier")
    @patch("nexuscore.api.dependencies.orchestrator.KnowledgeCuratorAgent")
    @patch("nexuscore.api.dependencies.orchestrator.PostmortemAgent")
    @patch("nexuscore.api.dependencies.orchestrator.PolicyAgent")
    @patch("nexuscore.api.dependencies.orchestrator.GuardianAgent")
    @patch("nexuscore.api.dependencies.orchestrator.TesterAgent")
    @patch("nexuscore.api.dependencies.orchestrator.DebuggerAgent")
    @patch("nexuscore.api.dependencies.orchestrator.CoderAgent")
    @patch("nexuscore.api.dependencies.orchestrator.PlannerAgent")
    @patch("nexuscore.api.dependencies.orchestrator.ArchitectAgent")
    @patch("nexuscore.api.dependencies.orchestrator.RequirementAgent")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value=None)
    @patch("nexuscore.api.dependencies.orchestrator._load_guardian_credentials", return_value=("", ""))
    def test_get_orchestrator_with_path(
        self, mock_cred, mock_kb, mock_orch, mock_req, mock_arch, mock_plan,
        mock_coder, mock_test, mock_debug, mock_guard, mock_policy,
        mock_post, mock_curator, mock_patcher, mock_llm, tmp_path,
    ):
        """project_path 指定で Orchestrator 生成"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        result = get_orchestrator(project_path=str(tmp_path))
        mock_orch.assert_called_once()
        assert result == mock_orch.return_value

    @patch("nexuscore.api.dependencies.orchestrator.LLMRouter")
    @patch("nexuscore.api.dependencies.orchestrator.PatchApplier")
    @patch("nexuscore.api.dependencies.orchestrator.KnowledgeCuratorAgent")
    @patch("nexuscore.api.dependencies.orchestrator.PostmortemAgent")
    @patch("nexuscore.api.dependencies.orchestrator.PolicyAgent")
    @patch("nexuscore.api.dependencies.orchestrator.GuardianAgent")
    @patch("nexuscore.api.dependencies.orchestrator.TesterAgent")
    @patch("nexuscore.api.dependencies.orchestrator.DebuggerAgent")
    @patch("nexuscore.api.dependencies.orchestrator.CoderAgent")
    @patch("nexuscore.api.dependencies.orchestrator.PlannerAgent")
    @patch("nexuscore.api.dependencies.orchestrator.ArchitectAgent")
    @patch("nexuscore.api.dependencies.orchestrator.RequirementAgent")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value=None)
    @patch("nexuscore.api.dependencies.orchestrator._load_guardian_credentials", return_value=("key", "model"))
    def test_get_orchestrator_default_path(
        self, mock_cred, mock_kb, mock_orch, mock_req, mock_arch, mock_plan,
        mock_coder, mock_test, mock_debug, mock_guard, mock_policy,
        mock_post, mock_curator, mock_patcher, mock_llm, tmp_path,
    ):
        """project_path 未指定時はデフォルトパスを使用"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        with patch.dict(os.environ, {"NEXUSCORE_PROJECT_PATH": str(tmp_path)}):
            result = get_orchestrator()
        mock_orch.assert_called_once()

    def test_get_orchestrator_with_kb_path(self, tmp_path):
        """Knowledge base パスが渡される"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        with patch("nexuscore.api.dependencies.orchestrator._load_guardian_credentials", return_value=("key", "model")):
            with patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value="/kb/path.json"):
                with patch("nexuscore.api.dependencies.orchestrator.Orchestrator"):
                    with patch("nexuscore.api.dependencies.orchestrator.RequirementAgent"):
                        with patch("nexuscore.api.dependencies.orchestrator.ArchitectAgent"):
                            with patch("nexuscore.api.dependencies.orchestrator.PlannerAgent"):
                                with patch("nexuscore.api.dependencies.orchestrator.CoderAgent"):
                                    with patch("nexuscore.api.dependencies.orchestrator.TesterAgent"):
                                        with patch("nexuscore.api.dependencies.orchestrator.DebuggerAgent") as mock_debug:
                                            with patch("nexuscore.api.dependencies.orchestrator.GuardianAgent"):
                                                with patch("nexuscore.api.dependencies.orchestrator.PolicyAgent"):
                                                    with patch("nexuscore.api.dependencies.orchestrator.PostmortemAgent"):
                                                        with patch("nexuscore.api.dependencies.orchestrator.KnowledgeCuratorAgent"):
                                                            with patch("nexuscore.api.dependencies.orchestrator.PatchApplier"):
                                                                with patch("nexuscore.api.dependencies.orchestrator.LLMRouter"):
                                                                    get_orchestrator(project_path=str(tmp_path))
                                                                    assert mock_debug.call_args[1]["knowledge_base_path"] == "/kb/path.json"
