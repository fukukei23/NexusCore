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


# =============================================================================
# 破損根本防止テスト（層1 AST + 層3 実行検証 + 例外安全な最終ロールバック）
# spec: 2026-07-24-nexuscore-debugger-patch破損根本防止 / plan Task4
# =============================================================================
from nexuscore.core.phase_runner_mixin import AST_FAIL_LIMIT  # noqa: E402


class TestDebugLoopCorruptionPrevention:
    """DebuggerAgent 経由の LLM説明文によるファイル破損を根本防止するテスト群。"""

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

    @staticmethod
    def _base_context(tmp_path):
        context = OrchestratorContext(task_id="t1", user_requirement="req")
        context.plan = {"target_files": [{"path": "tests/test_main.py", "role": "test"}]}
        context.implementation = {"files": {"main.py": "print('original')\n"}}
        return context

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_ast_ng_explanation_does_not_corrupt_file(self, mock_sandbox, tmp_path):
        """LLMが説明文(構文NG)を返す場合、ファイルは書き換えられず元のまま。"""
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="fail", returncode=1)
        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "これは修正の説明文です。コードではありません。"
        }
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        # AST NG 連続 AST_FAIL_LIMIT 回で早期脱出・ファイルは不変
        assert agents["debugger_agent"].debug_and_patch.call_count == AST_FAIL_LIMIT
        assert result.debug_retries == AST_FAIL_LIMIT
        assert result.testing["passed"] is False
        main_path = Path(str(tmp_path)) / "main.py"
        assert main_path.read_text(encoding="utf-8") == "print('original')\n"

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_ast_fail_limit_early_exit(self, mock_sandbox, tmp_path):
        """AST NG が連続 AST_FAIL_LIMIT 回に達したら早期脱出（sandbox呼出は初回のみ）。"""
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="fail", returncode=1)
        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "説明文 only"
        }
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        # ループ内 sandbox は呼ばれない（AST NG で pytest 実行前）・初回のみ
        assert mock_sandbox.call_count == 1
        assert result.debug_retries == AST_FAIL_LIMIT

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_ast_ng_ok_ng_does_not_exit_on_non_consecutive(self, mock_sandbox, tmp_path):
        """AST NG→OK→NG は連続ではないので AST_FAIL_LIMIT で早期脱出しない。"""
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="fail", returncode=1)
        orchestrator, agents = self._make_orchestrator(tmp_path)
        # [説明文(NG), 正しいコード(OK・pytest失敗), 説明文(NG)] → 連続1ずつ・脱出しない
        agents["debugger_agent"].debug_and_patch.side_effect = [
            {"fixed_code": "説明文1"},
            {"fixed_code": "x = 1\n"},   # 構文OK・pytest失敗
            {"fixed_code": "説明文2"},   # 連続1（直前OKでリセット）
        ]
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        # DEBUG_MAX_RETRIES(3) 到達で終了・AST_FAIL_LIMIT 早期脱出は起きない
        assert result.debug_retries == DEBUG_MAX_RETRIES
        assert agents["debugger_agent"].debug_and_patch.call_count == DEBUG_MAX_RETRIES

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_empty_fixed_code_breaks_and_rolls_back(self, mock_sandbox, tmp_path):
        """fixed_code 空 → break・not passed なので最終ロールバックで original へ。"""
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="fail", returncode=1)
        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["debugger_agent"].debug_and_patch.return_value = {"fixed_code": ""}
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        assert result.debug_retries == 1  # 1回目で break
        assert result.testing["passed"] is False
        main_path = Path(str(tmp_path)) / "main.py"
        assert main_path.read_text(encoding="utf-8") == "print('original')\n"
        assert any(h.get("status") == "no_fixed_code" for h in result.debug_history)

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_sandbox_exception_triggers_finally_rollback(self, mock_sandbox, tmp_path):
        """run_in_sandbox 例外 → finally で original_source 復元（例外安全）。"""
        # 初回テスト実行は成功（passed=True・ループに入らない）を避けるため初回から例外
        mock_sandbox.side_effect = TimeoutError("sandbox timeout")
        orchestrator, agents = self._make_orchestrator(tmp_path)
        context = self._base_context(tmp_path)

        # 初回 sandbox 例外で run_testing_phase がどう振る舞うかは実装依存。
        # ループ内 sandbox 例外のロールバックを検証するため、初回は失敗させてループに入れる。
        mock_sandbox.side_effect = [
            SandboxResult(stdout="", stderr="fail", returncode=1),  # 初回失敗→ループへ
            TimeoutError("sandbox timeout in loop"),                # ループ内例外
        ]
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "x = 1\n"
        }

        result = orchestrator.run_testing_phase(context)

        assert result.testing["passed"] is False
        main_path = Path(str(tmp_path)) / "main.py"
        assert main_path.read_text(encoding="utf-8") == "print('original')\n"
        assert any(h.get("status") == "sandbox_error" for h in result.debug_history)

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_rolls_back_to_original_on_exhausted_retries(self, mock_sandbox, tmp_path):
        """構文OKだが pytest失敗が続く→DEBUG_MAX_RETRIES枯渇後・original_source へ復元。"""
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="still fail", returncode=1)
        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "x = 999\n"   # 構文OK・意味NG
        }
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        assert result.debug_retries == DEBUG_MAX_RETRIES
        assert result.testing["passed"] is False
        main_path = Path(str(tmp_path)) / "main.py"
        # 最終ロールバックで original へ戻る（破損残存防止）
        assert main_path.read_text(encoding="utf-8") == "print('original')\n"

    @patch("nexuscore.core.phase_runner_mixin.run_in_sandbox")
    def test_debug_history_accumulates(self, mock_sandbox, tmp_path):
        """各試行が debug_history に status キーで記録される。"""
        mock_sandbox.return_value = SandboxResult(stdout="", stderr="fail", returncode=1)
        orchestrator, agents = self._make_orchestrator(tmp_path)
        agents["debugger_agent"].debug_and_patch.return_value = {
            "fixed_code": "x = 1\n"
        }
        context = self._base_context(tmp_path)

        result = orchestrator.run_testing_phase(context)

        assert len(result.debug_history) == DEBUG_MAX_RETRIES
        for h in result.debug_history:
            assert "attempt" in h
            assert "status" in h   # status キー統一

