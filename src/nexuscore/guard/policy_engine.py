from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

# NexusEval の Verdict を参照（型のみ、実装依存なし）
EvalVerdict = Literal["GO", "CONDITIONAL_GO", "NO"]


class GuardDecision(StrEnum):
    """Guard判定結果"""

    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


@dataclass
class EvalInput:
    """Eval入力（NexusEval の EvaluationReport から必要な情報のみ）"""

    verdict: EvalVerdict | None = None  # GO / CONDITIONAL_GO / NO


@dataclass
class TestInput:
    """Test入力"""

    status: Literal["PASS", "FAIL", "UNKNOWN"] | None = None


@dataclass
class DiffInput:
    """Diff入力"""

    high_risk: bool = False  # high_risk_diff


@dataclass
class SecurityInput:
    """Security入力"""

    check_status: Literal["PASS", "UNKNOWN", "NOT_RUN"]  # セキュリティチェックの状態（必須）
    secret_found: bool = False  # secret_found


@dataclass
class GuardInput:
    """Guard判定への入力"""

    environment: Literal["production", "staging", "poc"]  # 環境（必須）
    security: SecurityInput  # セキュリティ入力（必須）
    eval: EvalInput | None = None
    test: TestInput | None = None
    diff: DiffInput | None = None
    override: bool = False  # デフォルト無効、BLOCK解除は禁止


@dataclass
class GuardResult:
    """Guard判定結果"""

    decision: GuardDecision
    reasons: list[str] = field(default_factory=list)  # ルールIDに基づく理由


def evaluate_guard_policy(input_data: GuardInput) -> GuardResult:
    """
    Guardポリシーを評価し、判定結果を返す。

    判定順序（優先度順）:
    1. Security R4.1: secret_found → BLOCK
    2. Security R4.2: check_status UNKNOWN/NOT_RUN + production → HOLD
    3. Security R4.3: check_status PASS → 次判定へ
    4. Eval: NO → BLOCK
    5. Test: FAIL → BLOCK
    6. Eval: CONDITIONAL_GO → HOLD
    7. Test: UNKNOWN → HOLD
    8. Diff: high_risk → HOLD
    9. 全通過 → ALLOW

    Args:
        input_data: Guard判定への入力

    Returns:
        GuardResult: 判定結果と理由
    """
    reasons: list[str] = []

    # Rule 4.1: Security check - secret_found (最高優先度)
    if input_data.security.secret_found:
        reasons.append("GUARD-RULE-001: secret_found=true")
        return GuardResult(decision=GuardDecision.BLOCK, reasons=reasons)

    # Rule 4.2: Security check - check_status UNKNOWN/NOT_RUN + production → HOLD
    if input_data.security.check_status in {"UNKNOWN", "NOT_RUN"}:
        if input_data.environment == "production":
            reasons.append(
                f"GUARD-RULE-001B: environment=production, security.check_status={input_data.security.check_status}"
            )
            return GuardResult(decision=GuardDecision.HOLD, reasons=reasons)
        # staging/poc の場合は次判定へ（理由に通過ログを入れない）

    # Rule 4.3: Security check - check_status PASS → 次判定へ
    # (明示的な処理は不要、次判定へ進む)

    # Rule 2: Eval verdict NO → BLOCK
    if input_data.eval and input_data.eval.verdict == "NO":
        reasons.append("GUARD-RULE-002: eval.verdict=NO")
        return GuardResult(decision=GuardDecision.BLOCK, reasons=reasons)

    # Rule 3: Test status FAIL → BLOCK
    if input_data.test and input_data.test.status == "FAIL":
        reasons.append("GUARD-RULE-003: test.status=FAIL")
        return GuardResult(decision=GuardDecision.BLOCK, reasons=reasons)

    # Rule 4: Eval verdict CONDITIONAL_GO → HOLD
    if input_data.eval and input_data.eval.verdict == "CONDITIONAL_GO":
        reasons.append("GUARD-RULE-004: eval.verdict=CONDITIONAL_GO")
        return GuardResult(decision=GuardDecision.HOLD, reasons=reasons)

    # Rule 5: Test status UNKNOWN → HOLD
    if input_data.test and input_data.test.status == "UNKNOWN":
        reasons.append("GUARD-RULE-005: test.status=UNKNOWN")
        return GuardResult(decision=GuardDecision.HOLD, reasons=reasons)

    # Rule 6: Diff high_risk → HOLD
    if input_data.diff and input_data.diff.high_risk:
        reasons.append("GUARD-RULE-006: diff.high_risk=true")
        return GuardResult(decision=GuardDecision.HOLD, reasons=reasons)

    # Rule 7: 全通過 → ALLOW
    # Eval: GO または未指定
    # Test: PASS または未指定
    # Diff: high_risk=false または未指定
    # Security: secret_found=false かつ check_status=PASS または未指定
    reasons.append("GUARD-RULE-007: all checks passed")
    return GuardResult(decision=GuardDecision.ALLOW, reasons=reasons)
