"""
orchestrator.py の包括的テスト

カバレッジ:
- Orchestrator: オーケストレータクラス
  - __post_init__: 初期化とロガー設定
  - _setup_logger: ログハンドラ設定
  - _maybe_stop: セッション制御の中断判定
  - _execute_task_via_npe: NPE経由でのLLM実行
  - run_full_project: フルプロジェクトフロー
  - _ensure_fastlane_tests: FastLaneモードのテスト生成
- assemble_agent_team: エージェントチーム組成
- CLI: コマンドライン引数パース
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

# orchestrator.py が依存する全モジュールをモック
# Note: save originals and restore after import to avoid leaking into other test modules
_AGENT_MOCK_KEYS = [
    "gradio",
    "nexuscore.agents.requirement_agent",
    "nexuscore.agents.architect_agent",
    "nexuscore.agents.planner_agent",
    "nexuscore.agents.coder_agent",
    "nexuscore.agents.tester_agent",
    "nexuscore.agents.debugger_agent",
    "nexuscore.agents.guardian_agent",
    "nexuscore.agents.policy_agent",
    "nexuscore.agents.postmortem_agent",
    "nexuscore.agents.knowledge_curator_agent",
    "nexuscore.services.patch_applier",
]
_agent_sys_modules_saved: dict[str, object] = {}
for _key in _AGENT_MOCK_KEYS:
    _agent_sys_modules_saved[_key] = sys.modules.get(_key)
    sys.modules[_key] = MagicMock()

try:
    from nexuscore.core.orchestrator import (
        Orchestrator,
        _build_arg_parser,
        assemble_agent_team,
    )
    from nexuscore.core.session_control import SessionController
    from nexuscore.llm.llm_router import LLMRouter

    HAS_ORCHESTRATOR = True
except ImportError:
    HAS_ORCHESTRATOR = False
    Orchestrator = None
    assemble_agent_team = None
    _build_arg_parser = None
    SessionController = None
    LLMRouter = None

# Restore sys.modules so other test files see real modules (not MagicMock)
for _key in _AGENT_MOCK_KEYS:
    _original = _agent_sys_modules_saved[_key]
    if _original is None:
        sys.modules.pop(_key, None)
    else:
        sys.modules[_key] = _original


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestOrchestratorInit:
    """Orchestrator 初期化のテスト"""

    def test_init_basic(self, tmp_path):
        """基本的な初期化テスト"""
        project_path = str(tmp_path)
        constitution = {"automation_policy": {"autonomy_level": 1}}

        # モックエージェントとルーターを作成
        agents = self._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            llm_router=llm_router,
            **agents,
        )

        assert orchestrator.project_path == project_path
        assert orchestrator.constitution == constitution
        assert orchestrator.llm_router == llm_router
        assert orchestrator.max_retries == 5
        assert orchestrator.session_controller is None
        assert hasattr(orchestrator, "logger")

    def test_init_with_session_controller(self, tmp_path):
        """SessionController付き初期化"""
        project_path = str(tmp_path)
        constitution = {"automation_policy": {"autonomy_level": 2}}

        agents = self._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)
        session_controller = Mock(spec=SessionController)

        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            llm_router=llm_router,
            session_controller=session_controller,
            **agents,
        )

        assert orchestrator.session_controller == session_controller

    def test_init_with_custom_max_retries(self, tmp_path):
        """カスタムmax_retriesでの初期化"""
        project_path = str(tmp_path)
        constitution = {}

        agents = self._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            llm_router=llm_router,
            max_retries=10,
            **agents,
        )

        assert orchestrator.max_retries == 10

    def test_logger_setup(self, tmp_path):
        """ロガーが正しくセットアップされる"""
        project_path = str(tmp_path)
        constitution = {}

        agents = self._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        orchestrator = Orchestrator(
            project_path=project_path,
            constitution=constitution,
            llm_router=llm_router,
            **agents,
        )

        # ログディレクトリが作成されているか確認
        log_dir = tmp_path / "logs" / "orchestrator"
        assert log_dir.exists()

        # ロガーが設定されているか確認
        assert orchestrator.logger.name == "Orchestrator"
        assert orchestrator.logger.level == logging.INFO
        assert len(orchestrator.logger.handlers) >= 2  # FileHandler + StreamHandler

    @staticmethod
    def _create_mock_agents() -> dict[str, Any]:
        """モックエージェント群を作成"""
        requirement_agent = Mock()
        requirement_agent.use_ui = False  # Mockのtruthy属性でGradio UIパスに入らないようにする
        return {
            "requirement_agent": requirement_agent,
            "architect_agent": Mock(),
            "planner_agent": Mock(),
            "coder_agent": Mock(),
            "tester_agent": Mock(),
            "debugger_agent": Mock(),
            "guardian_agent": Mock(),
            "policy_agent": Mock(),
            "postmortem_agent": Mock(),
            "knowledge_curator_agent": Mock(),
            "patch_applier_agent": Mock(),
        }


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestOrchestratorMaybeStop:
    """Orchestrator._maybe_stop() のテスト"""

    def test_maybe_stop_without_session_controller(self, tmp_path):
        """SessionControllerがない場合は何もしない"""
        orchestrator = self._create_orchestrator(tmp_path, session_controller=None)

        # 例外が発生しないことを確認
        orchestrator._maybe_stop("test_phase")

    def test_maybe_stop_with_checkpoint(self, tmp_path):
        """チェックポイントが保存される"""
        session_controller = Mock(spec=SessionController)
        session_controller.should_stop.return_value = False

        orchestrator = self._create_orchestrator(tmp_path, session_controller=session_controller)

        extra_data = {"key": "value"}
        orchestrator._maybe_stop("test_phase", extra_data)

        session_controller.checkpoint.assert_called_once_with("test_phase", extra_data)

    def test_maybe_stop_with_stop_request(self, tmp_path):
        """stop指示がある場合はRuntimeErrorを投げる"""
        session_controller = Mock(spec=SessionController)
        session_controller.should_stop.return_value = True

        orchestrator = self._create_orchestrator(tmp_path, session_controller=session_controller)

        with pytest.raises(RuntimeError, match="SessionStopped"):
            orchestrator._maybe_stop("test_phase")

    def test_maybe_stop_checkpoint_failure_continues(self, tmp_path):
        """チェックポイント保存失敗でも処理は継続"""
        session_controller = Mock(spec=SessionController)
        session_controller.checkpoint.side_effect = Exception("Checkpoint failed")
        session_controller.should_stop.return_value = False

        orchestrator = self._create_orchestrator(tmp_path, session_controller=session_controller)

        # 例外が発生せず継続することを確認
        orchestrator._maybe_stop("test_phase")

    def test_maybe_stop_should_stop_check_failure_continues(self, tmp_path):
        """should_stopチェック失敗でも処理は継続"""
        session_controller = Mock(spec=SessionController)
        session_controller.checkpoint.return_value = None
        session_controller.should_stop.side_effect = ValueError("Check failed")

        orchestrator = self._create_orchestrator(tmp_path, session_controller=session_controller)

        # 例外が発生せず継続することを確認
        orchestrator._maybe_stop("test_phase")

    @staticmethod
    def _create_orchestrator(tmp_path, session_controller=None):
        """テスト用Orchestratorインスタンスを作成"""
        agents = TestOrchestratorInit._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        return Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            session_controller=session_controller,
            **agents,
        )


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestOrchestratorExecuteTaskViaNPE:
    """Orchestrator._execute_task_via_npe() のテスト"""

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    @patch("nexuscore.core.orchestrator.clean_output")
    def test_execute_task_basic(self, mock_clean, mock_guarded_call, tmp_path):
        """基本的なタスク実行"""
        mock_guarded_call.return_value = {"ok": True, "content": "LLM response", "usage": {}}
        mock_clean.side_effect = lambda x: x

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {"planning": "gpt-4"}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()
        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        result = orchestrator._execute_task_via_npe(
            prompt="Test prompt", metadata={"task_type": "planning"}
        )

        assert result == "LLM response"
        mock_guarded_call.assert_called_once()
        assert mock_guarded_call.call_args[1]["model"] == "gpt-4"
        assert mock_guarded_call.call_args[1]["task"] == "planning"

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    @patch("nexuscore.core.orchestrator.clean_output")
    def test_execute_task_default_model(self, mock_clean, mock_guarded_call, tmp_path):
        """デフォルトモデルを使用"""
        mock_guarded_call.return_value = {"ok": True, "content": "Default response", "usage": {}}
        mock_clean.side_effect = lambda x: x

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()
        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        result = orchestrator._execute_task_via_npe(
            prompt="Test prompt", metadata={"task_type": "unknown_task"}
        )

        assert result == "Default response"
        assert mock_guarded_call.call_args[1]["model"] == "gpt-3.5-turbo"

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    @patch("nexuscore.core.orchestrator.clean_output")
    def test_execute_task_string_response(self, mock_clean, mock_guarded_call, tmp_path):
        """NPEが文字列を返す場合"""
        mock_guarded_call.return_value = "Direct string response"
        mock_clean.side_effect = lambda x: x

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()
        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        result = orchestrator._execute_task_via_npe(
            prompt="Test prompt", metadata={"task_type": "generic"}
        )

        assert result == "Direct string response"

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    @patch("nexuscore.core.orchestrator.clean_output")
    def test_execute_task_no_task_type(self, mock_clean, mock_guarded_call, tmp_path):
        """task_typeが指定されていない場合"""
        mock_guarded_call.return_value = {"ok": True, "content": "Generic response", "usage": {}}
        mock_clean.side_effect = lambda x: x

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()
        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        result = orchestrator._execute_task_via_npe(prompt="Test prompt", metadata={})

        assert result == "Generic response"
        assert mock_guarded_call.call_args[1]["task"] == "generic"


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestOrchestratorRunFullProject:
    """Orchestrator.run_full_project() のテスト"""

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    def test_run_full_project_basic(self, mock_guarded_call, tmp_path):
        """基本的なプロジェクト実行フロー"""
        mock_guarded_call.return_value = {
            "ok": True,
            "content": '{"functions_to_implement": []}',
            "usage": {},
        }

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()

        # requirement_agentにanalyze_requirementメソッドを追加
        agents["requirement_agent"].use_ui = False
        agents["requirement_agent"].analyze_requirement = Mock(
            return_value={"raw_requirement": "Test requirement"}
        )

        # planner_agentにgenerate_planメソッドを追加
        agents["planner_agent"].generate_plan = Mock(return_value='{"functions_to_implement": []}')

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={"automation_policy": {"autonomy_level": 1}},
            llm_router=llm_router,
            **agents,
        )

        orchestrator.run_full_project(
            user_requirement="Test requirement",
            language="ja",
            fast_lane=False,
        )

        # requirement_agentが呼ばれたことを確認
        agents["requirement_agent"].analyze_requirement.assert_called_once_with("Test requirement")

        # planner_agentが呼ばれたことを確認
        agents["planner_agent"].generate_plan.assert_called_once()

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    def test_run_full_project_with_session_stop(self, mock_guarded_call, tmp_path):
        """セッション中断時の動作"""
        session_controller = Mock(spec=SessionController)
        session_controller.checkpoint.return_value = None
        session_controller.should_stop.return_value = True  # 最初の呼び出しで中断

        llm_router = Mock(spec=LLMRouter)
        agents = TestOrchestratorInit._create_mock_agents()

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            session_controller=session_controller,
            **agents,
        )

        # SessionStoppedで中断されることを確認
        orchestrator.run_full_project(
            user_requirement="Test requirement",
            language="ja",
            fast_lane=False,
        )

        # チェックポイントが呼ばれたことを確認
        assert session_controller.checkpoint.call_count > 0

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    def test_run_full_project_requirement_failure(self, mock_guarded_call, tmp_path):
        """要件定義フェーズ失敗時に例外が発生することを確認"""
        # guarded_llm_callがserializableなdictを返すように設定
        mock_guarded_call.return_value = {"functions_to_implement": []}

        llm_router = Mock(spec=LLMRouter)
        agents = TestOrchestratorInit._create_mock_agents()

        # requirement_agentが例外を投げる
        agents["requirement_agent"].analyze_requirement = Mock(
            side_effect=Exception("Requirement failed")
        )
        # Mockのuse_uiがtruthyになるのを防ぐ
        agents["requirement_agent"].use_ui = False

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        # 要件定義フェーズで例外が発生することを確認
        with pytest.raises(Exception, match="Requirement failed"):
            orchestrator.run_full_project(
                user_requirement="Test requirement",
                language="ja",
                fast_lane=False,
            )

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    def test_run_full_project_empty_specs(self, mock_guarded_call, tmp_path):
        """要件定義が空の場合、ValueErrorが発生することを確認"""
        llm_router = Mock(spec=LLMRouter)
        agents = TestOrchestratorInit._create_mock_agents()

        # requirement_agentが空の辞書を返す
        agents["requirement_agent"].analyze_requirement = Mock(return_value={})
        # Mockのuse_uiがtruthyになるのを防ぐ
        agents["requirement_agent"].use_ui = False

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        # 空specsでValueErrorが発生することを確認
        with pytest.raises(ValueError, match="empty specs"):
            orchestrator.run_full_project(
                user_requirement="Test requirement",
                language="ja",
                fast_lane=False,
            )

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    def test_run_full_project_fast_lane(self, mock_guarded_call, tmp_path):
        """FastLaneモードでの実行"""
        mock_guarded_call.return_value = {
            "ok": True,
            "content": '{"functions_to_implement": []}',
            "usage": {},
        }

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()

        agents["requirement_agent"].use_ui = False
        agents["requirement_agent"].analyze_requirement = Mock(
            return_value={"raw_requirement": "Test"}
        )
        agents["planner_agent"].generate_plan = Mock(return_value='{"functions_to_implement": []}')
        agents["coder_agent"].implement_code = Mock(return_value="# code")
        agents["tester_agent"].generate_tests = Mock(return_value="# tests")

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        orchestrator.run_full_project(
            user_requirement="Test requirement",
            language="ja",
            fast_lane=True,
        )

        # FastLaneモードで並列実行されたことを確認
        assert hasattr(orchestrator, "last_fastlane_outputs")
        assert "code" in orchestrator.last_fastlane_outputs
        assert "tests" in orchestrator.last_fastlane_outputs
        assert "plan" in orchestrator.last_fastlane_outputs


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestOrchestratorEnsureFastlaneTests:
    """Orchestrator._ensure_fastlane_tests() のテスト"""

    def test_ensure_fastlane_tests_with_initial_result(self, tmp_path):
        """初期結果がある場合はそれを返す"""
        orchestrator = self._create_orchestrator(tmp_path)

        result = orchestrator._ensure_fastlane_tests(
            initial_result="Initial tests",
            plan_text="",
            code_result="",
            requirement="",
        )

        assert result == "Initial tests"

    def test_ensure_fastlane_tests_with_plan_json(self, tmp_path):
        """プランJSONから生成"""
        orchestrator = self._create_orchestrator(tmp_path)

        # tester_agentにgenerate_tests_from_planメソッドを追加
        orchestrator.tester_agent.generate_tests_from_plan = Mock(return_value="Tests from plan")

        plan = {"functions_to_implement": [{"name": "test_func"}]}

        result = orchestrator._ensure_fastlane_tests(
            initial_result="",
            plan_text=json.dumps(plan),
            code_result="",
            requirement="Test requirement",
        )

        assert result == "Tests from plan"
        orchestrator.tester_agent.generate_tests_from_plan.assert_called_once()

    def test_ensure_fastlane_tests_with_code_result(self, tmp_path):
        """コード結果から生成"""
        orchestrator = self._create_orchestrator(tmp_path)

        # tester_agentにgenerate_tests_and_testimonyメソッドを追加
        orchestrator.tester_agent.generate_tests_and_testimony = Mock(
            return_value="Tests from code"
        )

        result = orchestrator._ensure_fastlane_tests(
            initial_result="",
            plan_text="",
            code_result="def test_func(): pass",
            requirement="Test requirement",
        )

        assert result == "Tests from code"
        orchestrator.tester_agent.generate_tests_and_testimony.assert_called_once_with(
            "def test_func(): pass"
        )

    def test_ensure_fastlane_tests_fallback_to_requirement(self, tmp_path):
        """要件からのフォールバック生成"""
        orchestrator = self._create_orchestrator(tmp_path)

        # tester_agentにgenerate_testsメソッドを追加
        orchestrator.tester_agent.generate_tests = Mock(return_value="Tests from requirement")

        result = orchestrator._ensure_fastlane_tests(
            initial_result="",
            plan_text="",
            code_result="",
            requirement="Test requirement",
        )

        assert result == "Tests from requirement"
        orchestrator.tester_agent.generate_tests.assert_called_once_with("Test requirement")

    def test_ensure_fastlane_tests_no_tester_agent(self, tmp_path):
        """tester_agentがない場合"""
        agents = TestOrchestratorInit._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        # tester_agentを削除
        orchestrator.tester_agent = None

        result = orchestrator._ensure_fastlane_tests(
            initial_result="",
            plan_text="",
            code_result="",
            requirement="Test requirement",
        )

        assert result == ""

    @staticmethod
    def _create_orchestrator(tmp_path):
        """テスト用Orchestratorを作成"""
        agents = TestOrchestratorInit._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        return Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestAssembleAgentTeam:
    """assemble_agent_team() のテスト"""

    @patch.dict(os.environ, {"GLM_API_KEY": "test-key"})
    @patch("nexuscore.core.orchestrator.RequirementAgent")
    @patch("nexuscore.core.orchestrator.ArchitectAgent")
    @patch("nexuscore.core.orchestrator.PlannerAgent")
    @patch("nexuscore.core.orchestrator.CoderAgent")
    @patch("nexuscore.core.orchestrator.TesterAgent")
    @patch("nexuscore.core.orchestrator.DebuggerAgent")
    @patch("nexuscore.core.orchestrator.GuardianAgent")
    @patch("nexuscore.core.orchestrator.PolicyAgent")
    @patch("nexuscore.core.orchestrator.PostmortemAgent")
    @patch("nexuscore.core.orchestrator.KnowledgeCuratorAgent")
    @patch("nexuscore.core.orchestrator.PatchApplier")
    @patch("nexuscore.core.orchestrator.LLMRouter")
    def test_assemble_agent_team_success(
        self,
        mock_router,
        mock_patch_applier,
        mock_curator,
        mock_postmortem,
        mock_policy,
        mock_guardian,
        mock_debugger,
        mock_tester,
        mock_coder,
        mock_planner,
        mock_architect,
        mock_requirement,
        tmp_path,
    ):
        """エージェントチームの正常な組成"""
        # 各モックの戻り値を設定
        for mock in [
            mock_requirement,
            mock_architect,
            mock_planner,
            mock_coder,
            mock_tester,
            mock_debugger,
            mock_guardian,
            mock_policy,
            mock_postmortem,
            mock_curator,
            mock_patch_applier,
            mock_router,
        ]:
            mock.return_value = Mock()

        result = assemble_agent_team(str(tmp_path))

        # 全エージェントとルーターが含まれることを確認
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

        # KnowledgeCuratorAgentがAPI keyとmodelで初期化されることを確認
        mock_curator.assert_called_once_with(
            api_key="test-key",
            model="glm-4-plus",
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_assemble_agent_team_no_api_key(self, tmp_path):
        """API keyがない場合はRuntimeErrorを投げる"""
        with pytest.raises(RuntimeError, match="GLM_API_KEY"):
            assemble_agent_team(str(tmp_path))

    @patch.dict(
        os.environ, {"GLM_API_KEY": "test-key", "NEXUS_TASK_MODEL_KNOWLEDGE": "glm-4-custom"}
    )
    @patch("nexuscore.core.orchestrator.RequirementAgent")
    @patch("nexuscore.core.orchestrator.ArchitectAgent")
    @patch("nexuscore.core.orchestrator.PlannerAgent")
    @patch("nexuscore.core.orchestrator.CoderAgent")
    @patch("nexuscore.core.orchestrator.TesterAgent")
    @patch("nexuscore.core.orchestrator.DebuggerAgent")
    @patch("nexuscore.core.orchestrator.GuardianAgent")
    @patch("nexuscore.core.orchestrator.PolicyAgent")
    @patch("nexuscore.core.orchestrator.PostmortemAgent")
    @patch("nexuscore.core.orchestrator.KnowledgeCuratorAgent")
    @patch("nexuscore.core.orchestrator.PatchApplier")
    @patch("nexuscore.core.orchestrator.LLMRouter")
    def test_assemble_agent_team_custom_model(
        self,
        mock_router,
        mock_patch_applier,
        mock_curator,
        mock_postmortem,
        mock_policy,
        mock_guardian,
        mock_debugger,
        mock_tester,
        mock_coder,
        mock_planner,
        mock_architect,
        mock_requirement,
        tmp_path,
    ):
        """カスタムモデル設定"""
        for mock in [
            mock_requirement,
            mock_architect,
            mock_planner,
            mock_coder,
            mock_tester,
            mock_debugger,
            mock_guardian,
            mock_policy,
            mock_postmortem,
            mock_curator,
            mock_patch_applier,
            mock_router,
        ]:
            mock.return_value = Mock()

        assemble_agent_team(str(tmp_path))

        # カスタムモデルで初期化されることを確認
        mock_curator.assert_called_once_with(
            api_key="test-key",
            model="glm-4-custom",
        )


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestCLI:
    """CLI引数パースのテスト"""

    def test_arg_parser_defaults(self):
        """デフォルト引数"""
        parser = _build_arg_parser()
        args = parser.parse_args([])

        assert args.project == str(Path.cwd())
        assert args.requirement == "サンプルの要件です。"
        assert args.autonomy_level == 1
        assert args.fast_lane is False
        assert args.session_id is None

    def test_arg_parser_custom_values(self):
        """カスタム引数"""
        parser = _build_arg_parser()
        args = parser.parse_args(
            [
                "--project",
                "/path/to/project",
                "--requirement",
                "Custom requirement",
                "--autonomy-level",
                "2",
                "--fast-lane",
                "--session-id",
                "test-session-123",
            ]
        )

        assert args.project == "/path/to/project"
        assert args.requirement == "Custom requirement"
        assert args.autonomy_level == 2
        assert args.fast_lane is True
        assert args.session_id == "test-session-123"

    def test_arg_parser_only_fast_lane(self):
        """--fast-laneのみ指定"""
        parser = _build_arg_parser()
        args = parser.parse_args(["--fast-lane"])

        assert args.fast_lane is True
        assert args.autonomy_level == 1  # デフォルト値


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    def test_orchestrator_with_empty_constitution(self, tmp_path):
        """空のconstitutionでの初期化"""
        agents = TestOrchestratorInit._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        assert orchestrator.constitution == {}

    @patch("nexuscore.core.orchestrator.guarded_llm_call")
    @patch("nexuscore.core.orchestrator.clean_output")
    def test_execute_task_with_empty_content(self, mock_clean, mock_guarded_call, tmp_path):
        """NPEが空のcontentを返す場合"""
        mock_guarded_call.return_value = {"ok": True, "content": "", "usage": {}}
        mock_clean.side_effect = lambda x: x

        llm_router = Mock(spec=LLMRouter)
        llm_router.task_model_map = {}
        llm_router.default_model = "gpt-3.5-turbo"
        llm_router.complete = Mock()

        agents = TestOrchestratorInit._create_mock_agents()
        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        result = orchestrator._execute_task_via_npe(
            prompt="Test prompt", metadata={"task_type": "generic"}
        )

        assert result == ""

    def test_logger_duplicate_initialization(self, tmp_path):
        """複数回初期化してもハンドラが重複しない"""
        agents = TestOrchestratorInit._create_mock_agents()
        llm_router = Mock(spec=LLMRouter)

        # 1回目の初期化
        orchestrator1 = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **agents,
        )

        handler_count_1 = len(orchestrator1.logger.handlers)

        # 2回目の初期化（同じロガー名）
        orchestrator2 = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=llm_router,
            **TestOrchestratorInit._create_mock_agents(),
        )

        handler_count_2 = len(orchestrator2.logger.handlers)

        # ハンドラ数が増えていないことを確認
        assert handler_count_1 == handler_count_2

    def test_ensure_fastlane_tests_with_invalid_json_plan(self, tmp_path):
        """無効なJSON planの場合"""
        orchestrator = TestOrchestratorEnsureFastlaneTests._create_orchestrator(tmp_path)

        orchestrator.tester_agent.generate_tests_and_testimony = Mock(
            return_value="Tests from code"
        )

        result = orchestrator._ensure_fastlane_tests(
            initial_result="",
            plan_text="invalid json {",
            code_result="def test(): pass",
            requirement="Test requirement",
        )

        # JSONパースに失敗してもコードからテスト生成に移行する
        assert result == "Tests from code"
