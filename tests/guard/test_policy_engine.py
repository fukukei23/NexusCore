"""
NexusGuard ポリシー判定器のテスト

T1-T14相当のテストケースを実装（外部依存なし）
"""

import pytest
from nexuscore.guard.policy_engine import (
    GuardDecision,
    GuardInput,
    GuardResult,
    EvalInput,
    TestInput,
    DiffInput,
    SecurityInput,
    evaluate_guard_policy,
)


class TestSecurityRule:
    """Security ルールのテスト（R4.1: secret_found → BLOCK, R4.2: check_status + environment, R4.3: PASS）"""

    def test_secret_found_blocks(self):
        """secret_found=true で BLOCK（R4.1）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(secret_found=True, check_status="PASS")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-001" in result.reasons[0]

    def test_secret_not_found_allows_other_checks(self):
        """secret_found=false の場合は他のチェックに進む"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(secret_found=False, check_status="PASS"),
            eval=EvalInput(verdict="NO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-002" in result.reasons[0]  # Eval NO が優先

    def test_production_unknown_holds(self):
        """production × UNKNOWN → HOLD（R4.2）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(secret_found=False, check_status="UNKNOWN")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-001B" in result.reasons[0]
        assert "environment=production" in result.reasons[0]
        assert "security.check_status=UNKNOWN" in result.reasons[0]

    def test_production_not_run_holds(self):
        """production × NOT_RUN → HOLD（R4.2）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(secret_found=False, check_status="NOT_RUN")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-001B" in result.reasons[0]
        assert "environment=production" in result.reasons[0]
        assert "security.check_status=NOT_RUN" in result.reasons[0]

    def test_staging_unknown_continues(self):
        """staging × UNKNOWN → 次判定へ（条件が揃えば ALLOW）"""
        input_data = GuardInput(
            environment="staging",
            security=SecurityInput(secret_found=False, check_status="UNKNOWN")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_poc_not_run_continues(self):
        """poc × NOT_RUN → 次判定へ（条件が揃えば ALLOW）"""
        input_data = GuardInput(
            environment="poc",
            security=SecurityInput(secret_found=False, check_status="NOT_RUN")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_all_env_pass_continues(self):
        """all env × PASS → 次判定へ（R4.3）"""
        for env in ["production", "staging", "poc"]:
            input_data = GuardInput(
                environment=env,
                security=SecurityInput(secret_found=False, check_status="PASS")
            )
            result = evaluate_guard_policy(input_data)
            assert result.decision == GuardDecision.ALLOW
            assert "GUARD-RULE-007" in result.reasons[0]

    def test_secret_found_always_blocks(self):
        """secret_found=true は常に BLOCK（check_status に関係なく）"""
        for check_status in ["PASS", "UNKNOWN", "NOT_RUN"]:
            for env in ["production", "staging", "poc"]:
                input_data = GuardInput(
                    environment=env,
                    security=SecurityInput(secret_found=True, check_status=check_status)
                )
                result = evaluate_guard_policy(input_data)
                assert result.decision == GuardDecision.BLOCK
                assert "GUARD-RULE-001" in result.reasons[0]


class TestEvalRule:
    """Eval ルールのテスト（Rule 2: NO→BLOCK, Rule 4: CONDITIONAL_GO→HOLD）"""

    def test_eval_no_blocks(self):
        """eval.verdict=NO で BLOCK"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="NO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-002" in result.reasons[0]

    def test_eval_conditional_go_holds(self):
        """eval.verdict=CONDITIONAL_GO で HOLD"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="CONDITIONAL_GO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-004" in result.reasons[0]

    def test_eval_go_continues(self):
        """eval.verdict=GO は次判定へ（ALLOW になる可能性）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="GO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_eval_none_continues(self):
        """eval 未指定は次判定へ"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW


class TestTestRule:
    """Test ルールのテスト（Rule 3: FAIL→BLOCK, Rule 5: UNKNOWN→HOLD）"""

    def test_test_fail_blocks(self):
        """test.status=FAIL で BLOCK"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            test=TestInput(status="FAIL")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-003" in result.reasons[0]

    def test_test_unknown_holds(self):
        """test.status=UNKNOWN で HOLD"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            test=TestInput(status="UNKNOWN")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-005" in result.reasons[0]

    def test_test_pass_continues(self):
        """test.status=PASS は次判定へ（ALLOW になる可能性）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            test=TestInput(status="PASS")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_test_none_continues(self):
        """test 未指定は次判定へ"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW


class TestDiffRule:
    """Diff ルールのテスト（Rule 6: high_risk→HOLD）"""

    def test_diff_high_risk_holds(self):
        """diff.high_risk=true で HOLD"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            diff=DiffInput(high_risk=True)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-006" in result.reasons[0]

    def test_diff_low_risk_continues(self):
        """diff.high_risk=false は次判定へ（ALLOW になる可能性）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            diff=DiffInput(high_risk=False)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_diff_none_continues(self):
        """diff 未指定は次判定へ"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW


class TestPriorityOrder:
    """優先順位のテスト"""

    def test_security_overrides_eval_no(self):
        """Security BLOCK が Eval NO より優先"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(secret_found=True, check_status="PASS"),
            eval=EvalInput(verdict="NO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-001" in result.reasons[0]

    def test_security_hold_overrides_eval_no(self):
        """Security HOLD (production × UNKNOWN) が Eval NO より優先"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(secret_found=False, check_status="UNKNOWN"),
            eval=EvalInput(verdict="NO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-001B" in result.reasons[0]

    def test_eval_no_overrides_test_fail(self):
        """Eval NO が Test FAIL より優先（実際は両方 BLOCK だが、Eval が先に評価）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="NO"),
            test=TestInput(status="FAIL")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-002" in result.reasons[0]

    def test_test_fail_overrides_conditional_go(self):
        """Test FAIL が Eval CONDITIONAL_GO より優先"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="CONDITIONAL_GO"),
            test=TestInput(status="FAIL")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.BLOCK
        assert "GUARD-RULE-003" in result.reasons[0]

    def test_conditional_go_overrides_unknown(self):
        """Eval CONDITIONAL_GO が Test UNKNOWN より優先"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="CONDITIONAL_GO"),
            test=TestInput(status="UNKNOWN")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-004" in result.reasons[0]

    def test_unknown_overrides_high_risk(self):
        """Test UNKNOWN が Diff high_risk より優先"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            test=TestInput(status="UNKNOWN"),
            diff=DiffInput(high_risk=True)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.HOLD
        assert "GUARD-RULE-005" in result.reasons[0]


class TestAllowCase:
    """ALLOW ケースのテスト（Rule 7: 全通過）"""

    def test_all_pass_allows(self):
        """すべてのチェックが通過で ALLOW"""
        input_data = GuardInput(
            environment="production",
            eval=EvalInput(verdict="GO"),
            test=TestInput(status="PASS"),
            diff=DiffInput(high_risk=False),
            security=SecurityInput(secret_found=False, check_status="PASS")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_all_none_allows(self):
        """すべて未指定で ALLOW（security は必須だが、check_status=PASS なら次判定へ）"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False)
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW
        assert "GUARD-RULE-007" in result.reasons[0]

    def test_partial_pass_allows(self):
        """一部のみ指定で通過すれば ALLOW"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
            eval=EvalInput(verdict="GO")
        )
        result = evaluate_guard_policy(input_data)
        assert result.decision == GuardDecision.ALLOW


class TestReasonsOutput:
    """reasons 出力のテスト"""

    def test_reasons_always_present(self):
        """reasons は常に出力される"""
        input_data = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=True)
        )
        result = evaluate_guard_policy(input_data)
        assert len(result.reasons) > 0
        assert result.reasons[0].startswith("GUARD-RULE-")

    def test_security_required_typeerror(self):
        """security を渡さない GuardInput が生成できないこと（TypeError）"""
        with pytest.raises(TypeError):
            GuardInput(environment="production")

    def test_reasons_contain_rule_id(self):
        """reasons にルールIDが含まれる"""
        test_cases = [
            (GuardInput(environment="production", security=SecurityInput(secret_found=True, check_status="PASS")), "GUARD-RULE-001"),
            (GuardInput(environment="production", security=SecurityInput(secret_found=False, check_status="UNKNOWN")), "GUARD-RULE-001B"),
            (GuardInput(environment="production", security=SecurityInput(check_status="PASS", secret_found=False), eval=EvalInput(verdict="NO")), "GUARD-RULE-002"),
            (GuardInput(environment="production", security=SecurityInput(check_status="PASS", secret_found=False), test=TestInput(status="FAIL")), "GUARD-RULE-003"),
            (GuardInput(environment="production", security=SecurityInput(check_status="PASS", secret_found=False), eval=EvalInput(verdict="CONDITIONAL_GO")), "GUARD-RULE-004"),
            (GuardInput(environment="production", security=SecurityInput(check_status="PASS", secret_found=False), test=TestInput(status="UNKNOWN")), "GUARD-RULE-005"),
            (GuardInput(environment="production", security=SecurityInput(check_status="PASS", secret_found=False), diff=DiffInput(high_risk=True)), "GUARD-RULE-006"),
            (GuardInput(environment="production", security=SecurityInput(check_status="PASS", secret_found=False)), "GUARD-RULE-007"),
        ]
        for input_data, expected_rule in test_cases:
            result = evaluate_guard_policy(input_data)
            assert any(expected_rule in reason for reason in result.reasons)
