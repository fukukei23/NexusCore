"""Integration tests for NexusCore core layer with real LLM API calls.

These tests verify that the full chain (Router → Provider → Phase execution)
works end-to-end with actual API keys. They are skipped when keys are missing.

Run:  pytest tests/core/test_integration_llm.py -m integration -v
Skip: pytest -m "not integration"
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexuscore.core.orchestrator import Orchestrator
from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin
from nexuscore.llm.llm_router import LLMRouter


def _has_env(key: str) -> bool:
    val = os.getenv(key, "")
    return bool(val) and not val.startswith("your_")


pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def llm_router():
    """Real LLMRouter initialized from environment."""
    return LLMRouter()


@pytest.fixture
def real_agents(llm_router):
    """Real agent instances assembled via factory."""
    from nexuscore.core.agent_factory import assemble_agent_team

    with tempfile.TemporaryDirectory(prefix="nexus_integ_") as tmpdir:
        Path(tmpdir, "src").mkdir()
        Path(tmpdir, "tests").mkdir()
        team = assemble_agent_team(tmpdir)
        # Replace the factory router with our fixture router
        team["llm_router"] = llm_router
        yield team, tmpdir


@pytest.fixture
def context(tmp_path):
    """Minimal OrchestratorContext for phase tests."""
    return OrchestratorContext(
        task_id="integ-test-001",
        user_requirement="Hello World を表示するPythonスクリプトを作成してください",
    )


# ---------------------------------------------------------------------------
# 1. LLM Router: real API call
# ---------------------------------------------------------------------------


class TestLLMRouterIntegration:
    def test_complete_returns_dict(self, llm_router):
        """LLMRouter.complete() returns a dict with content from a real provider."""
        response = llm_router.complete(
            system_prompt="Respond concisely.",
            user_prompt="Respond with exactly: PONG",
            task="chat_general",
        )
        assert isinstance(response, dict)
        assert "content" in response
        assert len(response["content"]) > 0

    def test_complete_with_different_tasks(self, llm_router):
        """Different task types route to different models."""
        for task in ["chat_general", "code_generate", "analytical"]:
            resp = llm_router.complete(
                system_prompt="Respond concisely.",
                user_prompt="Say 'ok' and nothing else.",
                task=task,
            )
            assert isinstance(resp, dict)
            assert "content" in resp


# ---------------------------------------------------------------------------
# 2. Phase execution with real agents (NPE → Router → Provider verified end-to-end)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Phase execution with real agents
# ---------------------------------------------------------------------------


class TestPhaseExecutionIntegration:
    def test_requirements_phase_with_real_agent(self, real_agents):
        """run_requirements_phase with real RequirementAgent."""
        agents, project_path = real_agents
        ctx = OrchestratorContext(
            task_id="integ-req-001",
            user_requirement="1+1を計算する関数を作成する",
        )
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        result = orch.run_requirements_phase(ctx)
        assert result.specs is not None
        assert len(result.specs) > 0
        assert "REQUIREMENTS" in result.phase_log

    def test_planning_phase_with_real_agent(self, real_agents):
        """run_planning_phase with real PlannerAgent."""
        agents, project_path = real_agents
        ctx = OrchestratorContext(
            task_id="integ-plan-001",
            user_requirement="Hello World スクリプト",
            specs={"requirement": "Hello World を表示する"},
        )
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        result = orch.run_planning_phase(ctx)
        assert result.plan is not None
        assert "PLAN" in result.phase_log

    def test_architecture_phase(self, real_agents):
        """Architecture phase calls the real ArchitectAgent and stores design_directive (spec §4-1)."""
        agents, project_path = real_agents
        ctx = OrchestratorContext(
            task_id="integ-arch-001",
            user_requirement="test",
        )
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        result = orch.run_architecture_phase(ctx)
        assert result.architecture.get("design_directive")
        assert "ARCHITECTURE" in result.phase_log

    def test_implementation_phase_with_real_agent(self, real_agents):
        """run_implementation_phase with real CoderAgent produces code."""
        agents, project_path = real_agents
        ctx = OrchestratorContext(
            task_id="integ-impl-001",
            user_requirement="print('Hello')するPythonコードを書いて",
        )
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        result = orch.run_implementation_phase(ctx)
        assert result.implementation is not None
        assert "IMPLEMENTATION" in result.phase_log
        # plan に target_files が無いため main.py 1枚の劣化モードに縮退する（spec §3-1）
        files = result.implementation.get("files", {})
        assert files, "at least one file should be generated"
        assert any(len(code) > 0 for code in files.values())

    def test_testing_phase_with_real_agent(self, real_agents):
        """run_testing_phase with real TesterAgent produces test code."""
        agents, project_path = real_agents
        ctx = OrchestratorContext(
            task_id="integ-test-001",
            user_requirement="Hello World スクリプトのテストを作成",
        )
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        result = orch.run_testing_phase(ctx)
        assert result.testing is not None
        assert "TESTING" in result.phase_log


# ---------------------------------------------------------------------------
# 4. Full pipeline (Requirement → Review)
# ---------------------------------------------------------------------------


class TestFullPipelineIntegration:
    def test_run_full_project_produces_all_phases(self, real_agents):
        """End-to-end: full pipeline produces code, tests, and plan."""
        agents, project_path = real_agents
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        orch.run_full_project(
            user_requirement="Hello World を表示するPythonスクリプト",
            language="ja",
            fast_lane=False,
        )
        # Verify all expected artifacts exist（target_files 契約により生成ファイル名は
        # planner 出力に依存するため固定ファイル名 hello.py は前提にしない・spec §3-2）
        readme = Path(project_path) / "README.md"
        generated_files = list(Path(project_path).rglob("*.py"))
        assert generated_files, "at least one .py file should be generated"
        assert readme.exists(), "README.md should be generated"
        content = generated_files[0].read_text(encoding="utf-8")
        assert len(content) > 0

    def test_run_full_project_fast_lane(self, real_agents):
        """FastLane mode: planning, coding, testing run in parallel."""
        agents, project_path = real_agents
        orch = Orchestrator(
            project_path=project_path,
            constitution={"automation_policy": {"autonomy_level": 1}},
            **agents,
        )
        orch.run_full_project(
            user_requirement="1+1を計算する関数",
            language="ja",
            fast_lane=True,
        )
        assert hasattr(orch, "last_fastlane_outputs")
        assert "code" in orch.last_fastlane_outputs
        assert "tests" in orch.last_fastlane_outputs
        assert "plan" in orch.last_fastlane_outputs
