# tests/core/test_planning_phase_parse.py
"""run_planning_phase の plan パース堅牢化テスト。spec §6-3"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from nexuscore.core.orchestrator_models import OrchestratorContext
from nexuscore.core.phase_runner_mixin import PhaseRunnerMixin


class _Host(PhaseRunnerMixin):
    """テスト用ホスト（Orchestrator の代役）。"""

    def __init__(self, planner):
        self.logger = logging.getLogger("test_host")
        self.session_controller = None
        self.llm_router = MagicMock()
        self.requirement_agent = MagicMock()
        self.planner_agent = planner
        self.coder_agent = MagicMock(spec=[])   # implement_code なし
        self.tester_agent = MagicMock(spec=[])  # generate_tests なし
        self.project_path = "/tmp/nexus_test"


def _ctx() -> OrchestratorContext:
    return OrchestratorContext(task_id="t1", user_requirement="電卓を作る")


def test_planner_returning_dict_is_used_directly():
    planner = MagicMock()
    planner.generate_plan.return_value = {"target_files": [], "functions_to_implement": []}
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"target_files": [], "functions_to_implement": []}


def test_planner_returning_json_string_is_parsed():
    planner = MagicMock()
    planner.generate_plan.return_value = '{"functions_to_implement": ["f1"]}'
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"functions_to_implement": ["f1"]}


def test_planner_returning_fenced_json_is_parsed():
    planner = MagicMock()
    planner.generate_plan.return_value = '```json\n{"functions_to_implement": ["f1"]}\n```'
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"functions_to_implement": ["f1"]}


def test_planner_returning_garbage_becomes_raw_plan():
    planner = MagicMock()
    planner.generate_plan.return_value = "これはJSONではない"
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"raw_plan": "これはJSONではない"}


def test_planner_returning_none_becomes_raw_plan():
    planner = MagicMock()
    planner.generate_plan.return_value = None
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"raw_plan": ""}


def test_planner_returning_empty_string_becomes_raw_plan():
    planner = MagicMock()
    planner.generate_plan.return_value = ""
    host = _Host(planner)
    ctx = host.run_planning_phase(_ctx())
    assert ctx.plan == {"raw_plan": ""}
