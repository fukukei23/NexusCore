# ==============================================================================
# ファイル名: test_orchestrator.py
# 対象: src/nexuscore/core/orchestrator.py
# 作成日: 2025-12-30
#
# 目的: orchestrator.py の高品質なテスト
#      - Test Quality Guidelines に準拠
#      - 外部依存のみモック（agents, LLM, SessionController）
#      - 実際のロジックをテスト
#      - tmp_path で実際のファイルI/O
#      - 80%+ カバレッジを目標
# ==============================================================================

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.core.orchestrator import (
    Orchestrator,
    assemble_agent_team,
)
from nexuscore.core.orchestrator_models import (
    OrchestratorContext,
    OrchestratorPhase,
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_agents():
    """全エージェントのモックを作成（外部依存）"""
    return {
        "requirement_agent": MagicMock(),
        "architect_agent": MagicMock(),
        "planner_agent": MagicMock(),
        "coder_agent": MagicMock(),
        "tester_agent": MagicMock(),
        "debugger_agent": MagicMock(),
        "guardian_agent": MagicMock(),
        "policy_agent": MagicMock(),
        "postmortem_agent": MagicMock(),
        "knowledge_curator_agent": MagicMock(),
        "patch_applier_agent": MagicMock(),
        "llm_router": MagicMock(),
    }


@pytest.fixture
def temp_project(tmp_path):
    """一時的なプロジェクトディレクトリ（実際のファイルシステム）"""
    project_path = tmp_path / "test_project"
    project_path.mkdir()
    return str(project_path)


# ==============================================================================
# TestOrchestratorInit: 初期化とロガー設定
# ==============================================================================


class TestOrchestratorInit:
    """Orchestrator初期化とロガー設定のテスト"""

    def test_orchestrator_initialization_with_all_agents(self, temp_project, mock_agents):
        """全エージェントを渡してOrchestratorを初期化"""
        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **mock_agents,
        )

        # インスタンスが正しく作成される
        assert isinstance(orchestrator, Orchestrator)
        assert orchestrator.project_path == temp_project
        assert orchestrator.constitution == {"automation_policy": {"autonomy_level": 1}}
        assert orchestrator.max_retries == 5  # デフォルト値

    def test_orchestrator_max_retries_custom(self, temp_project, mock_agents):
        """カスタムmax_retriesの設定"""
        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            max_retries=10,
            **mock_agents,
        )

        assert orchestrator.max_retries == 10

    def test_orchestrator_post_init_creates_logger(self, temp_project, mock_agents):
        """__post_init__でロガーが作成される"""
        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        assert orchestrator.logger is not None
        assert orchestrator.logger.name == "Orchestrator"
        assert len(orchestrator.logger.handlers) == 2  # FileHandler + StreamHandler

    def test_setup_logger_creates_log_directory(self, temp_project, mock_agents):
        """_setup_loggerがログディレクトリを作成（実際のファイルI/O）"""
        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        log_dir = Path(temp_project) / "logs" / "orchestrator"
        assert log_dir.exists()
        assert log_dir.is_dir()

        # FileHandlerが正しく設定されている（ファイル作成は実装詳細なのでhandlerの存在を確認）
        file_handlers = [h for h in orchestrator.logger.handlers if hasattr(h, "baseFilename")]
        assert len(file_handlers) == 1
        assert "orchestrator_" in file_handlers[0].baseFilename


# ==============================================================================
# TestExecuteTaskViaNPE: NPE経由のLLM実行
# ==============================================================================


class TestExecuteTaskViaNPE:
    """_execute_task_via_npe メソッドのテスト"""

    def test_execute_task_with_dict_response(self, temp_project, mock_agents):
        """guarded_llm_callがdict形式を返す場合"""
        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        with patch(
            "nexuscore.core.phase_runner_mixin.guarded_llm_call",
            return_value={"ok": True, "content": "Test response content", "usage": {"tokens": 100}},
        ):
            result = orchestrator._execute_task_via_npe(
                prompt="Test prompt", metadata={"task_type": "planning", "as_json": False}
            )

            assert "Test response content" in result

    def test_execute_task_with_string_response(self, temp_project, mock_agents):
        """guarded_llm_callが文字列を返す場合"""
        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        with patch(
            "nexuscore.core.phase_runner_mixin.guarded_llm_call", return_value="Direct string response"
        ):
            result = orchestrator._execute_task_via_npe(
                prompt="Test prompt", metadata={"task_type": "coding"}
            )

            assert result == "Direct string response"

    def test_execute_task_uses_task_model_map(self, temp_project, mock_agents):
        """llm_router.task_model_mapからモデルを選択"""
        mock_agents["llm_router"].task_model_map = {
            "planning": "openai:gpt-4",
            "coding": "anthropic:claude-3",
        }
        mock_agents["llm_router"].default_model = "openai:gpt-3.5"

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        with patch(
            "nexuscore.core.phase_runner_mixin.guarded_llm_call",
            return_value={"ok": True, "content": "Response", "usage": {}},
        ) as mock_call:
            orchestrator._execute_task_via_npe(prompt="Test", metadata={"task_type": "planning"})

            # guarded_llm_callが呼ばれ、モデルが正しく設定されている
            assert mock_call.called
            call_args = mock_call.call_args
            assert call_args[1]["model"] == "openai:gpt-4"

    def test_execute_task_default_task_type(self, temp_project, mock_agents):
        """metadataにtask_typeがない場合は"generic"を使用"""
        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        with patch(
            "nexuscore.core.phase_runner_mixin.guarded_llm_call",
            return_value={"ok": True, "content": "Response", "usage": {}},
        ) as mock_call:
            orchestrator._execute_task_via_npe(prompt="Test", metadata={})  # task_typeなし

            assert mock_call.called
            # デフォルトは"generic"
            call_args = mock_call.call_args
            assert call_args[1]["task"] == "generic"


# ==============================================================================
# TestMaybeStop: SessionController統合
# ==============================================================================


class TestMaybeStop:
    """_maybe_stop メソッドのテスト（SessionController統合）"""

    def test_maybe_stop_without_session_controller(self, temp_project, mock_agents):
        """session_controllerがNoneの場合は何もしない"""
        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            session_controller=None,
            **mock_agents,
        )

        # 例外が発生しないことを確認
        orchestrator._maybe_stop("test_phase")

    def test_maybe_stop_calls_checkpoint(self, temp_project, mock_agents):
        """session_controller.checkpoint が呼ばれる"""
        mock_session_controller = MagicMock()
        mock_session_controller.should_stop.return_value = False

        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            session_controller=mock_session_controller,
            **mock_agents,
        )

        orchestrator._maybe_stop("requirement", {"task_id": "test123"})

        mock_session_controller.checkpoint.assert_called_once_with(
            "requirement", {"task_id": "test123"}
        )

    def test_maybe_stop_raises_when_should_stop(self, temp_project, mock_agents):
        """should_stop() が True の場合 RuntimeError("SessionStopped") を raise"""
        mock_session_controller = MagicMock()
        mock_session_controller.should_stop.return_value = True

        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            session_controller=mock_session_controller,
            **mock_agents,
        )

        with pytest.raises(RuntimeError, match="SessionStopped"):
            orchestrator._maybe_stop("planning")

    def test_maybe_stop_continues_if_checkpoint_fails(self, temp_project, mock_agents):
        """checkpointが失敗してもメイン処理は継続"""
        mock_session_controller = MagicMock()
        mock_session_controller.checkpoint.side_effect = Exception("Checkpoint failed")
        mock_session_controller.should_stop.return_value = False

        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            session_controller=mock_session_controller,
            **mock_agents,
        )

        # 例外が発生せず処理が継続
        orchestrator._maybe_stop("test_phase")


# ==============================================================================
# TestRunFullProject: メインワークフロー
# ==============================================================================


class TestRunFullProject:
    """run_full_project メソッドのテスト"""

    def test_run_full_project_basic_workflow(self, temp_project, mock_agents):
        """基本的なワークフロー（requirement → planning）"""
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            return_value={"requirements": ["req1", "req2"]}
        )
        mock_agents["planner_agent"].generate_plan = MagicMock(
            return_value=json.dumps({"functions_to_implement": ["func1", "func2"]})
        )
        mock_agents["coder_agent"].implement_code = MagicMock(return_value="code content")
        mock_agents["tester_agent"].generate_tests = MagicMock(return_value="test content")

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        orchestrator.run_full_project("Test requirement", language="ja", fast_lane=False)

        # エージェントメソッドが呼ばれた
        mock_agents["requirement_agent"].analyze_requirement.assert_called_once_with(
            "Test requirement"
        )
        mock_agents["planner_agent"].generate_plan.assert_called_once()

    def test_run_full_project_with_fast_lane(self, temp_project, mock_agents):
        """fast_laneモードで並列実行"""
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            return_value={"requirements": ["req1"]}
        )
        mock_agents["planner_agent"].generate_plan = MagicMock(
            return_value=json.dumps({"functions_to_implement": ["func1"]})
        )
        mock_agents["coder_agent"].implement_code = MagicMock(return_value="code")
        mock_agents["tester_agent"].generate_tests = MagicMock(return_value="tests")

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        orchestrator.run_full_project("Test requirement", fast_lane=True)

        # fast_laneモードで last_fastlane_outputs が設定される
        assert hasattr(orchestrator, "last_fastlane_outputs")
        assert "code" in orchestrator.last_fastlane_outputs
        assert "tests" in orchestrator.last_fastlane_outputs
        assert "plan" in orchestrator.last_fastlane_outputs

    def test_run_full_project_requirement_failure(self, temp_project, mock_agents):
        """要件分析フェーズの失敗（例外が伝播される）"""
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            side_effect=Exception("Requirement error")
        )

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        # 例外が伝播される
        with pytest.raises(Exception, match="Requirement error"):
            orchestrator.run_full_project("Test requirement")

    def test_run_full_project_empty_specs_aborts(self, temp_project, mock_agents):
        """空のspecsが返された場合はValueErrorがraiseされる"""
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(return_value={})

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        with pytest.raises(ValueError, match="empty specs"):
            orchestrator.run_full_project("Test requirement")

    def test_run_full_project_planning_failure(self, temp_project, mock_agents):
        """計画フェーズの失敗（例外が伝播される）"""
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            return_value={"req": "test"}
        )
        mock_agents["planner_agent"].generate_plan = MagicMock(
            side_effect=Exception("Planning error")
        )

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        # 例外が伝播される
        with pytest.raises(Exception, match="Planning error"):
            orchestrator.run_full_project("Test requirement")

    def test_run_full_project_with_session_stopped(self, temp_project, mock_agents):
        """SessionStoppedが発生した場合の処理"""
        mock_session_controller = MagicMock()
        mock_session_controller.should_stop.return_value = True

        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            return_value={"requirements": ["req1"]}
        )

        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            session_controller=mock_session_controller,
            **mock_agents,
        )

        # SessionStoppedが内部で発生し、正常に処理される
        orchestrator.run_full_project("Test requirement")

    def test_run_full_project_with_gradio_ui(self, temp_project, mock_agents):
        """Gradio UIを使用する場合"""
        mock_agents["requirement_agent"].use_ui = True
        mock_agents["requirement_agent"].launch_gradio_ui = MagicMock(
            return_value={"specs": "from_ui"}
        )

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        orchestrator.run_full_project("Test requirement")

        mock_agents["requirement_agent"].launch_gradio_ui.assert_called_once()

    def test_run_full_project_raw_requirement_fallback(self, temp_project, mock_agents):
        """analyze_requirementがない場合のフォールバック"""
        mock_agents["requirement_agent"].use_ui = False
        # analyze_requirementを削除
        del mock_agents["requirement_agent"].analyze_requirement

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        # raw_requirementが使用される（クラッシュしない）
        orchestrator.run_full_project("Test requirement")

    @pytest.mark.parametrize(
        "plan_text,expected_type",
        [
            ('{"functions_to_implement": ["func1"]}', dict),  # valid JSON
            ("Not valid JSON", dict),  # invalid JSON -> raw_plan
        ],
    )
    def test_run_full_project_plan_parsing(
        self, temp_project, mock_agents, plan_text, expected_type
    ):
        """計画のJSONパース（成功/失敗）"""
        mock_agents["requirement_agent"].use_ui = False
        mock_agents["requirement_agent"].analyze_requirement = MagicMock(
            return_value={"req": "test"}
        )
        mock_agents["planner_agent"].generate_plan = MagicMock(return_value=plan_text)
        mock_agents["coder_agent"].implement_code = MagicMock(return_value="code")
        mock_agents["tester_agent"].generate_tests = MagicMock(return_value="tests")

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        # JSONパース失敗でもクラッシュしない
        orchestrator.run_full_project("Test requirement")


# ==============================================================================
# TestEnsureFastlaneTests: Fastlaneテスト生成フォールバック
# ==============================================================================


class TestEnsureFastlaneTests:
    """_ensure_fastlane_tests メソッドのテスト"""

    def test_ensure_fastlane_tests_returns_initial_result(self, temp_project, mock_agents):
        """initial_resultがある場合はそのまま返す"""
        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        result = orchestrator._ensure_fastlane_tests(
            initial_result="Existing tests", plan_text="", code_result="", requirement="Test"
        )

        assert result == "Existing tests"

    def test_ensure_fastlane_tests_from_plan(self, temp_project, mock_agents):
        """plan_textからテストを生成"""
        mock_agents["tester_agent"].generate_tests_from_plan = MagicMock(
            return_value="Tests from plan"
        )

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        plan_json = json.dumps({"functions": ["func1"]})
        result = orchestrator._ensure_fastlane_tests(
            initial_result="", plan_text=plan_json, code_result="", requirement="Test"
        )

        assert result == "Tests from plan"

    def test_ensure_fastlane_tests_from_code(self, temp_project, mock_agents):
        """code_resultからテストを生成"""
        mock_agents["tester_agent"].generate_tests_and_testimony = MagicMock(
            return_value="Tests from code"
        )

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        result = orchestrator._ensure_fastlane_tests(
            initial_result="", plan_text="", code_result="def func(): pass", requirement="Test"
        )

        assert result == "Tests from code"

    def test_ensure_fastlane_tests_final_fallback(self, temp_project, mock_agents):
        """最終フォールバック（requirementから生成）"""
        mock_agents["tester_agent"].generate_tests = MagicMock(return_value="Fallback tests")

        orchestrator = Orchestrator(
            project_path=temp_project, constitution={"test": "constitution"}, **mock_agents
        )

        result = orchestrator._ensure_fastlane_tests(
            initial_result="", plan_text="", code_result="", requirement="Test requirement"
        )

        assert result == "Fallback tests"

    def test_ensure_fastlane_tests_no_tester(self, temp_project, mock_agents):
        """tester_agentがNoneの場合"""
        orchestrator = Orchestrator(
            project_path=temp_project,
            constitution={"test": "constitution"},
            tester_agent=None,
            **{k: v for k, v in mock_agents.items() if k != "tester_agent"},
        )

        result = orchestrator._ensure_fastlane_tests(
            initial_result="", plan_text="", code_result="", requirement="Test"
        )

        assert result == ""


# ==============================================================================
# TestAssembleAgentTeam: エージェントチーム組成
# ==============================================================================


class TestAssembleAgentTeam:
    """assemble_agent_team 関数のテスト"""

    def test_assemble_agent_team_creates_all_agents(self, temp_project, monkeypatch):
        """全エージェントとLLMRouterが作成される"""
        monkeypatch.setenv("GLM_API_KEY", "test-api-key")

        result = assemble_agent_team(temp_project)

        # 必須キーが存在
        assert "requirement_agent" in result
        assert "architect_agent" in result
        assert "planner_agent" in result
        assert "coder_agent" in result
        assert "tester_agent" in result
        assert "debugger_agent" in result
        assert "guardian_agent" in result
        assert "policy_agent" in result
        assert "postmortem_agent" in result
        assert "knowledge_curator_agent" in result
        assert "patch_applier_agent" in result
        assert "llm_router" in result

    def test_assemble_agent_team_missing_api_key(self, temp_project, monkeypatch):
        """GLM_API_KEYがない場合はRuntimeError"""
        # 環境変数をクリア
        monkeypatch.delenv("GLM_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="GLM_API_KEY"):
            assemble_agent_team(temp_project)


# ==============================================================================
# Note: CLI tests removed — CLI entry point is now in main_cli.py
# ==============================================================================
