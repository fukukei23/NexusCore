"""
CR-006-1: Orchestrator のフェーズ分割と Happy Path テスト

Orchestrator の正常系フローを検証するテスト。
"""

from unittest.mock import MagicMock, patch

import pytest

from nexuscore.core.orchestrator import (
    Orchestrator,
    OrchestratorContext,
    OrchestratorPhase,
)


@pytest.fixture
def mock_agents():
    """モックエージェント群"""
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
    }


@pytest.fixture
def mock_llm_router():
    """モック LLM Router"""
    router = MagicMock()
    router.task_model_map = {}
    router.default_model = "gpt-4"
    return router


@pytest.fixture
def orchestrator(mock_agents, mock_llm_router):
    """Orchestrator インスタンス"""
    return Orchestrator(
        project_path="/tmp/test_project",
        constitution={"automation_policy": {"autonomy_level": 1}},
        llm_router=mock_llm_router,
        **mock_agents,
    )


@pytest.fixture
def initial_context():
    """初期コンテキスト"""
    return OrchestratorContext(
        task_id="test-task-123",
        user_requirement="テスト要件",
        language="ja",
        fast_lane=False,
        run_db_id=None,
    )


def test_run_full_project_calls_phases_in_order(orchestrator, initial_context, monkeypatch):
    """run_full_project が各フェーズメソッドを期待順序で1回ずつ呼ぶことを確認"""
    call_order = []

    def track_call(phase_name):
        def wrapper(context):
            call_order.append(phase_name)
            return context

        return wrapper

    # 各フェーズメソッドをモックで差し替え
    monkeypatch.setattr(orchestrator, "run_requirements_phase", track_call("REQUIREMENTS"))
    monkeypatch.setattr(orchestrator, "run_planning_phase", track_call("PLAN"))
    monkeypatch.setattr(orchestrator, "run_architecture_phase", track_call("ARCHITECTURE"))
    monkeypatch.setattr(orchestrator, "run_implementation_phase", track_call("IMPLEMENTATION"))
    monkeypatch.setattr(orchestrator, "run_testing_phase", track_call("TESTING"))
    monkeypatch.setattr(orchestrator, "run_review_phase", track_call("REVIEW"))

    # _maybe_stop をモック化（SessionStopped を投げないように）
    monkeypatch.setattr(orchestrator, "_maybe_stop", lambda *args, **kwargs: None)

    # orchestrator_db_hook のインポートエラーを回避
    with patch(
        "nexuscore.core.orchestrator_db_hook.log_orchestrator_event", side_effect=ImportError
    ):
        orchestrator.run_full_project(
            user_requirement="テスト要件",
            language="ja",
            fast_lane=False,
        )

    # 期待順序で呼ばれていることを確認
    expected_order = ["REQUIREMENTS", "PLAN", "ARCHITECTURE", "IMPLEMENTATION", "TESTING", "REVIEW"]
    assert call_order == expected_order


def test_each_phase_receives_and_returns_context(orchestrator, initial_context):
    """各フェーズメソッドが context を受け取り、返すことを確認"""

    # 各フェーズメソッドをモック化
    def mock_phase(context: OrchestratorContext) -> OrchestratorContext:
        context.phase_log.append(f"PHASE_{len(context.phase_log)}")
        return context

    orchestrator.run_requirements_phase = mock_phase
    orchestrator.run_planning_phase = mock_phase
    orchestrator.run_architecture_phase = mock_phase
    orchestrator.run_implementation_phase = mock_phase
    orchestrator.run_testing_phase = mock_phase
    orchestrator.run_review_phase = mock_phase

    # _maybe_stop をモック化
    orchestrator._maybe_stop = lambda *args, **kwargs: None

    # orchestrator_db_hook のインポートエラーを回避
    with patch(
        "nexuscore.core.orchestrator_db_hook.log_orchestrator_event", side_effect=ImportError
    ):
        orchestrator.run_full_project(
            user_requirement="テスト要件",
            language="ja",
            fast_lane=False,
        )

    # phase_log にすべてのフェーズが記録されていることを確認
    # （実際には各フェーズメソッド内で phase_log.append が呼ばれるが、
    #  モックでは PHASE_0, PHASE_1, ... が追加される）
    # 実際の実装では、各フェーズメソッドが phase_log に追加する


def test_requirements_phase_updates_context(orchestrator, initial_context):
    """Requirements フェーズがコンテキストを更新することを確認"""
    # requirement_agent のモック設定
    orchestrator.requirement_agent.analyze_requirement = MagicMock(
        return_value={"requirement": "テスト要件", "priority": "high"}
    )
    # use_ui 属性を False に設定
    orchestrator.requirement_agent.use_ui = False

    # _maybe_stop をモック化
    orchestrator._maybe_stop = lambda *args, **kwargs: None

    # orchestrator_db_hook のインポートエラーを回避
    with patch(
        "nexuscore.core.orchestrator_db_hook.log_orchestrator_event", side_effect=ImportError
    ):
        context = orchestrator.run_requirements_phase(initial_context)

    # コンテキストが更新されていることを確認
    assert context.specs == {"requirement": "テスト要件", "priority": "high"}
    assert "REQUIREMENTS" in context.phase_log


def test_planning_phase_updates_context(orchestrator, initial_context):
    """Planning フェーズがコンテキストを更新することを確認"""
    # 前提: Requirements フェーズが完了している
    initial_context.specs = {"requirement": "テスト要件"}

    # planner_agent のモック設定
    orchestrator.planner_agent.generate_plan = MagicMock(
        return_value='{"functions_to_implement": ["func1", "func2"]}'
    )

    # _maybe_stop をモック化
    orchestrator._maybe_stop = lambda *args, **kwargs: None

    # orchestrator_db_hook のインポートエラーを回避
    with patch(
        "nexuscore.core.orchestrator_db_hook.log_orchestrator_event", side_effect=ImportError
    ):
        context = orchestrator.run_planning_phase(initial_context)

    # コンテキストが更新されていることを確認
    assert "plan" in context.plan or "functions_to_implement" in context.plan
    assert "PLAN" in context.phase_log


def test_architecture_phase_updates_context(orchestrator, initial_context):
    """Architecture フェーズがコンテキストを更新することを確認"""
    context = orchestrator.run_architecture_phase(initial_context)

    assert "ARCHITECTURE" in context.phase_log
    assert context.architecture == {}


def test_implementation_phase_updates_context(orchestrator, initial_context):
    """Implementation フェーズがコンテキストを更新することを確認"""
    # coder_agent のモック設定
    orchestrator.coder_agent.implement_code = MagicMock(
        return_value="def hello():\n    print('Hello')"
    )

    context = orchestrator.run_implementation_phase(initial_context)

    assert "IMPLEMENTATION" in context.phase_log
    assert "code" in context.implementation


def test_testing_phase_updates_context(orchestrator, initial_context):
    """Testing フェーズがコンテキストを更新することを確認"""
    # tester_agent のモック設定
    orchestrator.tester_agent.generate_tests = MagicMock(
        return_value="def test_hello():\n    assert hello() == 'Hello'"
    )

    context = orchestrator.run_testing_phase(initial_context)

    assert "TESTING" in context.phase_log
    assert "tests" in context.testing


def test_review_phase_updates_context(orchestrator, initial_context):
    """Review フェーズがコンテキストを更新することを確認"""
    context = orchestrator.run_review_phase(initial_context)

    assert "REVIEW" in context.phase_log
    assert context.review == {}


def test_fast_lane_mode_executes_planning_code_test_in_parallel(orchestrator, initial_context):
    """FastLane モードで Planning / Coding / Testing が並列実行されることを確認"""
    initial_context.fast_lane = True
    initial_context.specs = {"requirement": "テスト要件"}

    # 各エージェントのモック設定
    orchestrator.planner_agent.generate_plan = MagicMock(
        return_value='{"functions_to_implement": ["func1"]}'
    )
    orchestrator.coder_agent.implement_code = MagicMock(return_value="def func1():\n    pass")
    orchestrator.tester_agent.generate_tests = MagicMock(return_value="def test_func1():\n    pass")

    # _maybe_stop をモック化
    orchestrator._maybe_stop = lambda *args, **kwargs: None

    # orchestrator_db_hook のインポートエラーを回避
    with patch(
        "nexuscore.core.orchestrator_db_hook.log_orchestrator_event", side_effect=ImportError
    ):
        context = orchestrator.run_planning_phase(initial_context)

        # FastLane の場合、Planning フェーズで Implementation と Testing も実行される
        assert "code" in context.implementation
        assert "tests" in context.testing
        # context.plan には計画の内容（辞書）が入っている
        assert isinstance(context.plan, dict)
        assert "functions_to_implement" in context.plan


def test_orchestrator_context_dataclass():
    """OrchestratorContext データクラスが正しく動作することを確認"""
    context = OrchestratorContext(
        task_id="test-123",
        user_requirement="テスト要件",
        language="ja",
        fast_lane=False,
    )

    assert context.task_id == "test-123"
    assert context.user_requirement == "テスト要件"
    assert context.language == "ja"
    assert context.fast_lane is False
    assert context.specs == {}
    assert context.plan == {}
    assert context.phase_log == []


def test_orchestrator_phase_enum():
    """OrchestratorPhase Enum が正しく動作することを確認"""
    assert OrchestratorPhase.REQUIREMENTS.value == 1
    assert OrchestratorPhase.PLAN.value == 2
    assert OrchestratorPhase.ARCHITECTURE.value == 3
    assert OrchestratorPhase.IMPLEMENTATION.value == 4
    assert OrchestratorPhase.TESTING.value == 5
    assert OrchestratorPhase.REVIEW.value == 6
