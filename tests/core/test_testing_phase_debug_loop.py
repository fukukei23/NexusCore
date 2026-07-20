"""
run_testing_phase() のサンドボックス実行+debuggerループの独立テスト（spec §4-2）。

test_orchestrator_comprehensive.py の TestTestingPhaseDebugLoop と同じ4シナリオを
カバーするが、あのファイルは `_build_arg_parser` の削除に伴う壊れたimport（別issueで
追跡中）で HAS_ORCHESTRATOR = False となり、ファイル内の全テストが機械的にskipされて
しまう。そのためこの重要な新規ロジック（sandbox実行+debuggerリトライループ）に対する
実行される形のテストが存在しない状態だった。

本ファイルは Orchestrator / OrchestratorContext を実モジュールから直接importすることで
その壊れたimportチェーンを回避し、上記4シナリオを実際にPASSする形で担保する。
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from nexuscore.core.orchestrator import Orchestrator, OrchestratorContext
from nexuscore.core.phase_runner_mixin import DEBUG_MAX_RETRIES
from nexuscore.core.sandbox_executor import SandboxResult
from nexuscore.llm.llm_router import LLMRouter


def _create_mock_agents() -> dict[str, Any]:
    """モックエージェント群を作成（test_orchestrator_comprehensive.py と同等）"""
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
    return {
        "requirement_agent": requirement_agent,
        "architect_agent": architect_agent,
        "planner_agent": Mock(),
        "coder_agent": Mock(),
        "tester_agent": tester_agent,
        "debugger_agent": debugger_agent,
        "guardian_agent": Mock(),
        "policy_agent": Mock(),
        "postmortem_agent": Mock(),
        "knowledge_curator_agent": Mock(),
        "patch_applier_agent": Mock(),
    }


class TestTestingPhaseDebugLoop:
    """run_testing_phase() のサンドボックス実行+debuggerループのテスト（spec §4-2）"""

    @staticmethod
    def _make_orchestrator(tmp_path, agents=None):
        agents = agents or _create_mock_agents()
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
