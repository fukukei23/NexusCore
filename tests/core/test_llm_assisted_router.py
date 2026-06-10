"""CR-NEXUS-054 Phase B: llm_assisted_router のユニットテスト（MiniMax生成・Fable検証済み）。"""

from nexuscore.core.dynamic_router import ActionRegistry
from nexuscore.core.goal_spec import CriterionResult
from nexuscore.core.llm_assisted_router import LLMAssistedRouter


def _build_registry():
    registry = ActionRegistry()
    for name in ("requirements", "planning", "implementation", "testing", "review"):
        registry.register(name, lambda c: c)
    return registry


def _unsatisfied():
    return [CriterionResult(name="has_plan", satisfied=False, description="計画")]


class TestLLMAssistedRouterHappyPath:
    """LLMからの正常提案を処理する経路のテスト。"""

    def test_正常提案でplanningが選択されreasonにLLM提案プレフィックスが付く(self):
        """有効なJSON提案が採用され、reason が [LLM提案] で始まることを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            return '{"action": "planning", "reason": "計画必要"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action(_unsatisfied())

        assert decision.action == "planning"
        assert decision.reason.startswith("[LLM提案]")

    def test_正常提案1回でllm_calls_usedが1増加する(self):
        """LLM呼び出しごとに llm_calls_used カウンタが増えることを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            return '{"action": "implementation", "reason": "実装フェーズへ"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        router.next_action(_unsatisfied())

        assert router.llm_calls_used == 1


class TestLLMAssistedRouterParsing:
    """LLM出力のパースに関するテスト。"""

    def test_前置き混じりのテキストからJSONを救出できる(self):
        """コードブロックや前置きが混ざった応答でも {...} を抽出できることを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            return 'はい {"action": "planning", "reason": "x"} 以上'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action(_unsatisfied())

        assert decision.action == "planning"


class TestLLMAssistedRouterFallback:
    """LLM提案が無効だった際のフォールバック挙動のテスト。"""

    def test_未登録のアクションが提案された場合はフォールバック(self):
        """利用不能なアクション提案はルールベースの選択に置き換わることを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            return '{"action": "deploy", "reason": "x"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action(_unsatisfied())

        assert decision.action == "planning"
        assert "フォールバック" in decision.reason

    def test_JSONではないテキストの場合もフォールバック(self):
        """JSONとして解釈できない応答ではルールベースが選択されることを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            return "わかりません"

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action(_unsatisfied())

        assert decision.action == "planning"
        assert "フォールバック" in decision.reason

    def test_propose_fnが例外を投げてもフォールバックする(self):
        """LLM障害（例外）でもルーティングが止まらないことを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            raise RuntimeError("LLMエラー")

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action(_unsatisfied())

        assert decision.action == "planning"
        assert "フォールバック" in decision.reason

    def test_予算超過時はpropose_fnを呼ばずにフォールバック(self):
        """max_llm_calls 超過後はLLMを呼ばずルールベースで選択することを検証する。"""
        registry = _build_registry()
        calls = []

        def propose_fn(system_prompt, user_prompt):
            calls.append(1)
            return '{"action": "planning", "reason": "x"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
            max_llm_calls=0,
        )
        decision = router.next_action(_unsatisfied())

        assert len(calls) == 0
        assert decision.action == "planning"
        assert "予算超過" in decision.reason

    def test_skip_actionsのアクションを提案されたらフォールバックしactionはNone(self):
        """skip指定のアクションは available から除外され、提案されても採用されないことを検証する。"""
        registry = _build_registry()

        def propose_fn(system_prompt, user_prompt):
            return '{"action": "planning", "reason": "x"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
            skip_actions=frozenset({"planning"}),
        )
        decision = router.next_action(_unsatisfied())

        assert decision.action is None
        assert "フォールバック" in decision.reason


class TestLLMAssistedRouterDeterministicRetry:
    """決定的リトライ挙動のテスト。"""

    def test_前回失敗アクションのリトライではpropose_fnを呼ばない(self):
        """リトライ判断はLLMに委ねず決定的ルールで処理されることを検証する。"""
        registry = _build_registry()
        calls = []

        def propose_fn(system_prompt, user_prompt):
            calls.append(1)
            return '{"action": "implementation", "reason": "x"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action(
            _unsatisfied(),
            last_failed_action="planning",
            retries_left_for_failed=2,
        )

        assert len(calls) == 0
        assert decision.action == "planning"


class TestLLMAssistedRouterEmptyUnsatisfied:
    """未達条件が空の場合のテスト。"""

    def test_未達条件が空ならactionはNone(self):
        """全条件達成済みのときLLMを呼ばず action=None を返すことを検証する。"""
        registry = _build_registry()
        calls = []

        def propose_fn(system_prompt, user_prompt):
            calls.append(1)
            return '{"action": "planning", "reason": "x"}'

        router = LLMAssistedRouter(
            registry=registry,
            propose_fn=propose_fn,
            goal_description="ゴール",
        )
        decision = router.next_action([])

        assert decision.action is None
        assert len(calls) == 0
