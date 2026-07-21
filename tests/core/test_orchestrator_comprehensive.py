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
        OrchestratorContext,
        assemble_agent_team,
    )
    from nexuscore.core.phase_runner_mixin import DEBUG_MAX_RETRIES
    from nexuscore.core.sandbox_executor import SandboxResult
    from nexuscore.core.session_control import SessionController
    from nexuscore.llm.llm_router import LLMRouter

    HAS_ORCHESTRATOR = True
except ImportError:
    HAS_ORCHESTRATOR = False
    Orchestrator = None
    OrchestratorContext = None
    assemble_agent_team = None
    DEBUG_MAX_RETRIES = None
    SandboxResult = None
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
        architect_agent = Mock()
        architect_agent.design_architecture.return_value = {
            "design_directive": "test design directive"
        }
        tester_agent = Mock()
        tester_agent.generate_tests = Mock(return_value="# generated tests")
        debugger_agent = Mock()
        debugger_agent.debug_and_patch = Mock(
            return_value={"fixed_code": "# fixed code", "patch": ""}
        )
        guardian_agent = Mock()
        # Phase6(review)がguardianループになったため、未設定Mockが自動生成する
        # MagicMockはdecision=="APPROVE"を満たさずREJECTループに入ってしまう。
        # 他フェーズのテストが影響を受けないようデフォルトはAPPROVE即承認にしておく。
        guardian_agent.review = Mock(return_value={"decision": "APPROVE", "reason": "ok"})
        return {
            "requirement_agent": requirement_agent,
            "architect_agent": architect_agent,
            "planner_agent": Mock(),
            "coder_agent": Mock(),
            "tester_agent": tester_agent,
            "debugger_agent": debugger_agent,
            "guardian_agent": guardian_agent,
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
    @patch("nexuscore.utils.clean_output.clean_output")
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
    @patch("nexuscore.utils.clean_output.clean_output")
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
    @patch("nexuscore.utils.clean_output.clean_output")
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
    @patch("nexuscore.utils.clean_output.clean_output")
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

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
    def test_run_full_project_basic(self, mock_guarded_call, mock_sandbox, tmp_path):
        """基本的なプロジェクト実行フロー"""
        mock_guarded_call.return_value = {
            "ok": True,
            "content": '{"functions_to_implement": []}',
            "usage": {},
        }
        mock_sandbox.return_value = Mock(stdout="1 passed", stderr="", returncode=0)

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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
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
    """assemble_agent_team() のテスト

    2026-04-29 の God Class 分割（agent_factory.py 抽出）以降、実装は
    AgentRegistry ベースのプラグイン discovery に変わっている（個別クラスの
    直接 import/直接 instantiate ではない）。旧テストは `nexuscore.core.orchestrator.
    RequirementAgent` 等を patch していたが、そのモジュールはもう assemble_agent_team
    の実装に関与しないため機能しなくなっていた。BaseAgent は API key 欠落時も
    例外を投げず遅延解決するため、モック無しの実インスタンス化で検証する。
    """

    def test_assemble_agent_team_returns_full_team(self, tmp_path):
        """全エージェント・ルーター・サービスが結果dictに含まれることを確認"""
        result = assemble_agent_team(str(tmp_path))

        for key in (
            "requirement_agent",
            "architect_agent",
            "planner_agent",
            "coder_agent",
            "tester_agent",
            "debugger_agent",
            "guardian_agent",
            "policy_agent",
            "postmortem_agent",
            "knowledge_curator_agent",
            "constitutional_council_agent",
            "patch_applier_agent",
            "llm_router",
        ):
            assert key in result, f"{key} が assemble_agent_team() の結果に含まれていない"

    def test_assemble_agent_team_language_propagates_to_requirement_agent(self, tmp_path):
        """language引数がAgentRegistry経由でRequirementAgentに渡されることを確認

        agent_factory.assemble_agent_team() は AgentRegistry.get(name)() で
        エージェントを生成する。本ファイル冒頭の sys.modules モック（他モジュール
        importの隔離用）が nexuscore.plugins.builtin_agents の登録内容に漏れ込む
        ため、実クラスの挙動に依存せず AgentRegistry を直接 patch して検証する。
        """
        from nexuscore.plugins.registry import AgentRegistry

        class FakeRequirementAgent:
            def __init__(self, language="ja"):
                self.language = language

        with (
            patch.object(AgentRegistry, "has", return_value=True),
            patch.object(AgentRegistry, "get", return_value=FakeRequirementAgent),
        ):
            result = assemble_agent_team(str(tmp_path), language="en")

        assert result["requirement_agent"].language == "en"

    def test_assemble_agent_team_knowledge_base_path_propagates_to_debugger(self, tmp_path):
        """knowledge_base_path引数がAgentRegistry経由でDebuggerAgentに渡されることを確認"""
        from nexuscore.plugins.registry import AgentRegistry

        class FakeDebuggerAgent:
            def __init__(self, knowledge_base_path=None, **_ignored):
                self.knowledge_base_path = knowledge_base_path

        with (
            patch.object(AgentRegistry, "has", return_value=True),
            patch.object(AgentRegistry, "get", return_value=FakeDebuggerAgent),
        ):
            result = assemble_agent_team(str(tmp_path), knowledge_base_path="/tmp/kb.json")

        assert result["debugger_agent"].knowledge_base_path == "/tmp/kb.json"


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

    @patch("nexuscore.core.phase_runner_mixin.guarded_llm_call")
    @patch("nexuscore.utils.clean_output.clean_output")
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


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestOrchestratorArchitecturePhase:
    """run_architecture_phase() のテスト（Stage 2・spec §4-1）"""

    def test_architecture_phase_calls_architect_and_stores_result(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["architect_agent"].design_architecture.return_value = {
            "design_directive": "レイヤードアーキテクチャ"
        }
        orchestrator = Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.specs = {"raw_requirement": "req"}
        context.plan = {"functions_to_implement": ["a"]}

        result = orchestrator.run_architecture_phase(context)

        agents["architect_agent"].design_architecture.assert_called_once_with(
            context.specs, context.plan
        )
        assert result.architecture == {"design_directive": "レイヤードアーキテクチャ"}

    def test_architecture_phase_empty_directive_raises(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["architect_agent"].design_architecture.return_value = {"design_directive": ""}
        orchestrator = Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )
        context = OrchestratorContext(task_id="t1", user_requirement="req")

        with pytest.raises(RuntimeError, match="ArchitectAgent returned empty design_directive"):
            orchestrator.run_architecture_phase(context)


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestGenerateOneFileWithArchitecture:
    """_generate_one_file() への design_directive 注入テスト（spec §4-1）"""

    def test_generate_one_file_injects_design_directive_into_prompt(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["coder_agent"].implement_code.return_value = "print('ok')"
        orchestrator = Orchestrator(
            project_path=str(tmp_path), constitution={}, llm_router=Mock(spec=LLMRouter), **agents,
        )
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {"functions_to_implement": []}
        context.architecture = {"design_directive": "レイヤードアーキテクチャで実装せよ"}

        orchestrator._generate_one_file(context, {"path": "app.py", "role": "implementation"}, {})

        call_kwargs = agents["coder_agent"].implement_code.call_args.kwargs
        assert "レイヤードアーキテクチャで実装せよ" in call_kwargs["task_description"]


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestTestingPhaseDebugLoop:
    """run_testing_phase() のサンドボックス実行+debuggerループのテスト（spec §4-2）"""

    @staticmethod
    def _make_orchestrator(tmp_path, agents=None):
        agents = agents or TestOrchestratorInit._create_mock_agents()
        orchestrator = Orchestrator(
            project_path=str(tmp_path),
            constitution={},
            llm_router=Mock(spec=LLMRouter),
            **agents,
        )
        return orchestrator, agents

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_passes_without_debug_loop(self, mock_sandbox, tmp_path):
        """初回のサンドボックス実行で成功する場合、debuggerは呼ばれない"""
        mock_sandbox.return_value = SandboxResult(stdout="1 passed", stderr="", returncode=0)

        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["tester_agent"].generate_tests.return_value = "def test_ok():\n    assert True"

        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {
            "target_files": [{"path": "tests/test_main.py", "role": "test"}]
        }
        context.implementation = {"files": {"main.py": "print('ok')"}}

        result = orchestrator.run_testing_phase(context)

        agents["debugger_agent"].debug_and_patch.assert_not_called()
        assert mock_sandbox.call_count == 1
        assert result.debug_retries == 0
        assert result.testing["passed"] is True
        assert result.testing["tests"] == "def test_ok():\n    assert True"
        assert result.testing["test_path"].endswith("test_main.py")

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_debugs_and_recovers(self, mock_sandbox, tmp_path):
        """初回失敗後、debuggerの修正で2回目に成功する場合"""
        mock_sandbox.side_effect = [
            SandboxResult(stdout="", stderr="AssertionError", returncode=1),
            SandboxResult(stdout="1 passed", stderr="", returncode=0),
        ]

        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["tester_agent"].generate_tests.return_value = "def test_ok():\n    assert False"
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "print('fixed')",
            "patch": "",
        }

        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {
            "target_files": [{"path": "tests/test_main.py", "role": "test"}]
        }
        context.implementation = {"files": {"main.py": "print('broken')"}}

        result = orchestrator.run_testing_phase(context)

        agents["debugger_agent"].debug_and_patch.assert_called_once()
        call_args = agents["debugger_agent"].debug_and_patch.call_args
        assert call_args[0][1] == {"main.py": "print('broken')"}
        assert call_args[0][2] == str(tmp_path)

        assert mock_sandbox.call_count == 2
        assert result.debug_retries == 1
        assert result.testing["passed"] is True
        assert result.implementation["files"]["main.py"] == "print('fixed')"

        fixed_path = Path(str(tmp_path)) / "main.py"
        assert fixed_path.read_text(encoding="utf-8") == "print('fixed')"

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_exhausts_debug_retries(self, mock_sandbox, tmp_path):
        """debuggerが修正してもテストが失敗し続ける場合、DEBUG_MAX_RETRIES回で打ち切る"""
        mock_sandbox.return_value = SandboxResult(
            stdout="", stderr="still failing", returncode=1
        )

        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["tester_agent"].generate_tests.return_value = "def test_bad():\n    assert False"
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "print('still broken')",
            "patch": "",
        }

        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {
            "target_files": [{"path": "tests/test_main.py", "role": "test"}]
        }
        context.implementation = {"files": {"main.py": "print('broken')"}}

        result = orchestrator.run_testing_phase(context)

        assert result.debug_retries == 3
        assert result.debug_retries == DEBUG_MAX_RETRIES
        assert agents["debugger_agent"].debug_and_patch.call_count == DEBUG_MAX_RETRIES
        # 初回 + リトライ毎の再テスト = DEBUG_MAX_RETRIES + 1 回
        assert mock_sandbox.call_count == DEBUG_MAX_RETRIES + 1
        assert result.testing["passed"] is False

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_missing_test_role_falls_back(self, mock_sandbox, tmp_path, caplog):
        """plan.target_filesにrole=testが無い場合はtests/test_main.pyにフォールバックしWARNログを出す"""
        mock_sandbox.return_value = SandboxResult(stdout="1 passed", stderr="", returncode=0)

        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["tester_agent"].generate_tests.return_value = "def test_ok():\n    assert True"

        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {"target_files": [{"path": "main.py", "role": "implementation"}]}
        context.implementation = {"files": {"main.py": "print('ok')"}}

        with caplog.at_level("WARNING"):
            result = orchestrator.run_testing_phase(context)

        assert result.testing["test_path"].endswith("test_main.py")
        assert any(
            "No role=test entry" in rec.message and rec.levelname == "WARNING"
            for rec in caplog.records
        )
        written = Path(str(tmp_path)) / "tests" / "test_main.py"
        assert written.read_text(encoding="utf-8") == "def test_ok():\n    assert True"


@pytest.mark.skipif(not HAS_ORCHESTRATOR, reason="orchestrator module not available")
class TestReviewPhaseGuardianLoop:
    """run_review_phase() のテスト（Stage 2・spec §4-3/4-4）"""

    def _make_orchestrator(self, tmp_path, agents):
        return Orchestrator(
            project_path=str(tmp_path),
            constitution={"rule": "x"},
            llm_router=Mock(spec=LLMRouter),
            **agents,
        )

    def _context_with_passing_tests(self, tmp_path):
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {
            "tests": "def test(): pass",
            "passed": True,
            "stdout": "1 passed",
            "stderr": "",
        }
        return context

    def test_review_phase_approves_on_first_pass(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["guardian_agent"].review.return_value = {"decision": "APPROVE", "reason": "ok"}

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 0
        agents["coder_agent"].implement_code.assert_not_called()

    def test_review_phase_reimplements_on_reject_then_approves(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["guardian_agent"].review.side_effect = [
            {
                "decision": "REJECT",
                "reason": "命名規則違反",
                "feedback_for_coder": "スネークケースにせよ",
            },
            {"decision": "APPROVE", "reason": "ok"},
        ]
        agents["coder_agent"].implement_code.return_value = "fixed code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "APPROVED"
        assert result.review_retries == 1
        reimpl_kwargs = agents["coder_agent"].implement_code.call_args.kwargs
        assert "スネークケースにせよ" in reimpl_kwargs["task_description"]

    def test_review_phase_exhausts_retries_needs_human_review(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()
        agents["guardian_agent"].review.return_value = {
            "decision": "REJECT",
            "reason": "重大な問題",
            "feedback_for_coder": "全面修正が必要",
        }
        agents["coder_agent"].implement_code.return_value = "still bad code"

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = self._context_with_passing_tests(tmp_path)

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        assert result.review_retries == 2  # REVIEW_MAX_RETRIES
        report_path = tmp_path / "review_report.md"
        assert report_path.exists()
        assert "全面修正が必要" in report_path.read_text(encoding="utf-8")

    def test_review_phase_skips_guardian_when_tests_still_failing(self, tmp_path):
        agents = TestOrchestratorInit._create_mock_agents()

        orchestrator = self._make_orchestrator(tmp_path, agents)
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.implementation = {"files": {"app.py": "code"}}
        context.testing = {"tests": "t", "passed": False, "stdout": "", "stderr": "still failing"}

        result = orchestrator.run_review_phase(context)

        assert result.terminal_state == "NEEDS_HUMAN_REVIEW"
        agents["guardian_agent"].review.assert_not_called()
        report_path = tmp_path / "review_report.md"
        assert report_path.exists()
