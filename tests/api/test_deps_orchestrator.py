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


class TestGetOrchestrator:
    """Tests for get_orchestrator function (assemble_agent_team 統合後)."""

    @patch("nexuscore.api.dependencies.orchestrator.assemble_agent_team")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value=None)
    def test_get_orchestrator_uses_assemble_agent_team(
        self, mock_kb, mock_orch, mock_assemble, tmp_path,
    ):
        """get_orchestrator は assemble_agent_team 経由でエージェントを構築する（A'案の統合）"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        mock_assemble.return_value = {"llm_router": MagicMock()}
        result = get_orchestrator(project_path=str(tmp_path))
        mock_assemble.assert_called_once()
        mock_orch.assert_called_once()
        assert result == mock_orch.return_value

    @patch("nexuscore.api.dependencies.orchestrator.assemble_agent_team")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value=None)
    def test_get_orchestrator_passes_language(
        self, mock_kb, mock_orch, mock_assemble, tmp_path,
    ):
        """language 引数が assemble_agent_team に伝搬する"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        mock_assemble.return_value = {"llm_router": MagicMock()}
        get_orchestrator(project_path=str(tmp_path), language="en")
        _, kwargs = mock_assemble.call_args
        assert kwargs.get("language") == "en"

    @patch("nexuscore.api.dependencies.orchestrator.assemble_agent_team")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value="/kb/path.json")
    def test_get_orchestrator_passes_kb_path(
        self, mock_kb, mock_orch, mock_assemble, tmp_path,
    ):
        """knowledge base パスが assemble_agent_team に伝搬する"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        mock_assemble.return_value = {"llm_router": MagicMock()}
        get_orchestrator(project_path=str(tmp_path))
        _, kwargs = mock_assemble.call_args
        assert kwargs.get("knowledge_base_path") == "/kb/path.json"

    @patch("nexuscore.api.dependencies.orchestrator.assemble_agent_team")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value=None)
    def test_get_orchestrator_default_path(
        self, mock_kb, mock_orch, mock_assemble, tmp_path,
    ):
        """project_path 未指定時はデフォルトパスを使用"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        mock_assemble.return_value = {"llm_router": MagicMock()}
        with patch.dict(os.environ, {"NEXUSCORE_PROJECT_PATH": str(tmp_path)}):
            get_orchestrator()
        mock_assemble.assert_called_once()

    @patch("nexuscore.api.dependencies.orchestrator.assemble_agent_team")
    @patch("nexuscore.api.dependencies.orchestrator.Orchestrator")
    @patch("nexuscore.api.dependencies.orchestrator._prepare_local_knowledge_base", return_value=None)
    def test_get_orchestrator_passes_agents_to_orchestrator(
        self, mock_kb, mock_orch, mock_assemble, tmp_path,
    ):
        """assemble_agent_team の戻り値が Orchestrator に渡される"""
        from nexuscore.api.dependencies.orchestrator import get_orchestrator

        fake_agents = {"requirement_agent": MagicMock(), "llm_router": MagicMock()}
        mock_assemble.return_value = fake_agents
        get_orchestrator(project_path=str(tmp_path))
        _, kwargs = mock_orch.call_args
        assert kwargs["requirement_agent"] is fake_agents["requirement_agent"]
        assert kwargs["llm_router"] is fake_agents["llm_router"]
