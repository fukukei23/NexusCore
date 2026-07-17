"""run_implementation_phase の target_files 契約対応テスト。spec §3-2"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin


class _Host(PhaseRunnerMixin):
    def __init__(self, coder, project_path):
        self.logger = logging.getLogger("test_host")
        self.session_controller = None
        self.llm_router = MagicMock()
        self.requirement_agent = MagicMock()
        self.planner_agent = MagicMock()
        self.coder_agent = coder
        self.tester_agent = MagicMock(spec=[])
        self.project_path = str(project_path)


def _ctx(plan) -> OrchestratorContext:
    ctx = OrchestratorContext(task_id="t1", user_requirement="電卓CLIを作る")
    ctx.plan = plan
    return ctx


def test_writes_each_target_file(tmp_path):
    coder = MagicMock()
    coder.implement_code.side_effect = ["# calc code", "# cli code"]
    host = _Host(coder, tmp_path)
    plan = {
        "target_files": [
            {"path": "app/calc.py", "role": "implementation"},
            {"path": "app/cli.py", "role": "implementation"},
            {"path": "tests/test_calc.py", "role": "test"},
        ]
    }
    ctx = host.run_implementation_phase(_ctx(plan))

    assert (tmp_path / "app/calc.py").read_text(encoding="utf-8") == "# calc code"
    assert (tmp_path / "app/cli.py").read_text(encoding="utf-8") == "# cli code"
    # role=test は実装フェーズでは書かない（Phase 5 の責務・spec §4-2）
    assert not (tmp_path / "tests/test_calc.py").exists()
    # hello.py はもう作られない
    assert not (tmp_path / "hello.py").exists()
    assert ctx.implementation["files"] == {
        "app/calc.py": "# calc code",
        "app/cli.py": "# cli code",
    }
    assert ctx.implementation["degraded"] is False


def test_generated_files_are_passed_as_context_to_next_call(tmp_path):
    coder = MagicMock()
    coder.implement_code.side_effect = ["# first", "# second"]
    host = _Host(coder, tmp_path)
    plan = {
        "target_files": [
            {"path": "a.py", "role": "implementation"},
            {"path": "b.py", "role": "implementation"},
        ]
    }
    host.run_implementation_phase(_ctx(plan))

    first_kwargs = coder.implement_code.call_args_list[0].kwargs
    second_kwargs = coder.implement_code.call_args_list[1].kwargs
    assert first_kwargs["existing_code"] == ""
    assert "a.py" in second_kwargs["existing_code"]
    assert "# first" in second_kwargs["existing_code"]


def test_missing_target_files_uses_fallback_main_py(tmp_path):
    coder = MagicMock()
    coder.implement_code.return_value = "# fallback code"
    host = _Host(coder, tmp_path)
    ctx = host.run_implementation_phase(_ctx({"functions_to_implement": []}))

    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "# fallback code"
    assert ctx.implementation["degraded"] is True


def test_empty_coder_output_raises(tmp_path):
    coder = MagicMock()
    coder.implement_code.return_value = ""
    host = _Host(coder, tmp_path)
    plan = {"target_files": [{"path": "a.py", "role": "implementation"}]}
    with pytest.raises(RuntimeError, match="empty"):
        host.run_implementation_phase(_ctx(plan))


def test_readme_lists_actual_generated_files(tmp_path):
    coder = MagicMock()
    coder.implement_code.return_value = "# code"
    host = _Host(coder, tmp_path)
    plan = {"target_files": [{"path": "app/calc.py", "role": "implementation"}]}
    host.run_implementation_phase(_ctx(plan))

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "app/calc.py" in readme
    assert "Hello World" not in readme
